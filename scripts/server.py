"""Local-only daily research service. No credentials, scheduler, or broker access."""
import datetime as dt,json,math,pathlib,re,socket,threading,time,urllib.parse,os,signal,logging
from logging.handlers import RotatingFileHandler
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from zoneinfo import ZoneInfo
ROOT=pathlib.Path(__file__).resolve().parents[1]
SH=ZoneInfo('Asia/Shanghai')
def now():return dt.datetime.now(dt.timezone.utc).isoformat()
def today():return dt.datetime.now(SH).date()
def age(stamp):
 try:return (dt.datetime.now(dt.timezone.utc)-dt.datetime.fromisoformat(stamp)).total_seconds()
 except (ValueError,TypeError):return float('inf')
def allowed(code):return bool(re.fullmatch(r'(sh\.(600|601|603|605|688|689)|sz\.(000|001|002|003|300|301))\d{3}',code))
def listed(rows):return [s for s in rows if s.get('type')=='1' and s.get('status')=='1' and allowed(s.get('code',''))]
def valid_rows(rows):
 out=[]
 for r in rows:
  dt.date.fromisoformat(r['date'])
  if r.get('tradestatus')=='0':out.append(r);continue
  try:o,h,l,c,v=[float(r[x]) for x in ['open','high','low','close','volume']]
  except (KeyError,ValueError):raise ValueError('来源返回缺失或无效 OHLCV，保留旧缓存')
  if not all(math.isfinite(x) for x in [o,h,l,c,v]) or min(o,l,c)<=0 or h<max(o,c,l) or l>min(o,c) or v<0:raise ValueError('来源返回非法价格或成交量，保留旧缓存')
  if r.get('adjustflag','3')!='3':raise ValueError('源复权口径不一致，保留旧缓存')
  if r.get('amount','').strip():
   try:amount=float(r['amount'])
   except ValueError:raise ValueError('来源返回无效成交额，保留旧缓存')
   if not math.isfinite(amount) or amount<0:raise ValueError('来源返回无效成交额，保留旧缓存')
  out.append(r)
 return out
class BaoSource:
 def __init__(self,refusal_file=None):self.connected=False;self.last=0;self.refusal_file=refusal_file;self.blocked=bool(refusal_file and refusal_file.exists())
 def reject(self,message):
  self.blocked=True
  if self.refusal_file:
   self.refusal_file.parent.mkdir(exist_ok=True);self.refusal_file.write_text(json.dumps({'stoppedAt':now(),'reason':message},ensure_ascii=False))
 def query(self,method,**args):
  if self.blocked:raise RuntimeError('数据源拒绝访问，已停止联网；请使用缓存或 CSV')
  for attempt in range(2):
   try:return self.once(method,**args)
   except Exception as e:
    # Only recognized transport errors get one reconnect; source refusal never retries.
    if self.blocked or attempt or not any(w in str(e).lower() for w in ['10002007','timed out','connection reset','broken pipe']):raise
    time.sleep(1)
 def once(self,method,**args):
  if self.blocked:raise RuntimeError('数据源拒绝访问，已停止联网；请使用缓存或 CSV')
  import baostock as bs
  socket.setdefaulttimeout(20)
  time.sleep(max(0,.6-(time.monotonic()-self.last)))
  try:
   if not self.connected:
    result=bs.login()
    if result.error_code!='0':raise RuntimeError('BaoStock 登录握手失败：'+result.error_msg)
    self.connected=True
   rs=getattr(bs,method)(**args);rows=[]
   while rs.error_code=='0' and rs.next():rows.append(dict(zip(rs.fields,rs.get_row_data())))
   if rs.error_code!='0':raise RuntimeError('BaoStock '+rs.error_code+'：'+rs.error_msg)
   return rows
  except Exception as e:
   self.connected=False
   # Close the failed library socket before its next official login handshake.
   from baostock.common import context
   sock=getattr(context,'default_socket',None)
   if sock is not None:
    try:sock.close()
    except OSError:pass
   context.default_socket=None
   if any(word in str(e).lower() for word in ['403','401','forbidden','拒绝','验证码','付费','unauthorized','认证','权限','denied']):self.reject(str(e))
   raise
  finally:self.last=time.monotonic()
class Store:
 def __init__(self,path,source):self.path=path;path.mkdir(parents=True,exist_ok=True);self.source=source;self.lock=threading.RLock();self.errors={}
 def read(self,key):
  try:return json.loads((self.path/(key+'.json')).read_text())
  except (OSError,ValueError):return None
 def write(self,key,data):
  p=self.path/(key+'.json');tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False));tmp.replace(p)
 def directory(self,force=False):
  with self.lock:
   old=self.read('directory')
   if old and (age(old['fetchedAt'])<86400 if not force else age(old['fetchedAt'])<15):return {**old,'cacheHit':True,'stale':False}
   try:
    raw=self.source.query('query_stock_basic');stocks=listed(raw)
    if not stocks:raise RuntimeError('来源未返回有效沪深上市股票目录')
    d={'stocks':stocks,'fetchedAt':now(),'source':'BaoStock','coverage':['sh','sz'],'excluded':{'allRecords':len(raw),'activeAStocks':len(stocks)}};self.write('directory',d);return {**d,'cacheHit':False,'stale':False}
   except Exception as e:
    if old:return {**old,'cacheHit':True,'stale':True,'warning':str(e)}
    raise
 def calendar(self):
  with self.lock:
   old=self.read('calendar')
   if old and age(old['fetchedAt'])<86400 and max((r['calendar_date'] for r in old['rows']),default='')>=today().isoformat():return old
   try:
    rows=self.source.query('query_trade_dates',start_date=(today()-dt.timedelta(days=40)).isoformat(),end_date=today().isoformat())
    if not rows:raise RuntimeError('来源交易日历暂不可用')
    d={'rows':rows,'fetchedAt':now()};self.write('calendar',d);return d
   except Exception as e:return {**(old or {'rows':[]}), 'warning':str(e)}
 def history(self,code,force=False):
  if not allowed(code):raise ValueError('仅支持 BaoStock 已覆盖的沪深 A 股；北交所请导入 CSV')
  with self.lock:
   key=code+'.none';old=self.read(key);cal=self.calendar();days=[r['calendar_date'] for r in cal['rows'] if r['is_trading_day']=='1' and r['calendar_date']<=today().isoformat()];latest=max(days) if days else None
   def envelope(d,hit=False,stale=False,error=None):
    traded=[r for r in d['rows'] if r.get('tradestatus')!='0']
    return {'data':d,'cacheHit':hit,'stale':stale,'error':error,'calendarLatest':latest,'calendarWarning':cal.get('warning'),'dataThrough':max((r['date'] for r in traded),default=None),'checkedThrough':max((r['date'] for r in d['rows']),default=None),'failedAt':self.errors.get(code,(None,None,None))[2] if stale else None}
   # Repeated clicks and same-day checks reuse successful cache. A forced check is coalesced for 15 seconds.
   if old and age(old['fetchedAt'])<(15 if force else 21600):return envelope(old,True)
   if code in self.errors and time.monotonic()-self.errors[code][0]<10:
    err=self.errors[code][1]
    if old:return envelope(old,True,True,err)
    raise RuntimeError(err)
   try:
    directory=self.directory();entry=next((s for s in directory['stocks'] if s['code']==code),None)
    if entry is None:raise ValueError('该代码不在来源当前沪深上市 A 股目录内')
    start=today()-dt.timedelta(days=365*3)
    if old and old['rows']:start=max(start,dt.date.fromisoformat(max(r['date'] for r in old['rows']))-dt.timedelta(days=7))
    new=valid_rows(self.source.query('query_history_k_data_plus',code=code,fields='date,code,open,high,low,close,volume,amount,adjustflag,tradestatus',start_date=start.isoformat(),end_date=today().isoformat(),frequency='d',adjustflag='3'))
    if any(r.get('code')!=code or r['date']>today().isoformat() for r in new):raise ValueError('来源返回股票代码或日期不一致，保留旧缓存')
    merged={r['date']:r for r in (old or {}).get('rows',[])};merged.update({r['date']:r for r in new});rows=sorted(merged.values(),key=lambda r:r['date'])
    cutoff=(today()-dt.timedelta(days=365*3+31)).isoformat();rows=[r for r in rows if r['date']>=cutoff]
    d={'code':code,'name':entry['code_name'],'source':'BaoStock','adjustment':'none','volumeUnit':'shares','amountUnit':'CNY','fetchedAt':now(),'rows':rows,'queriedThrough':today().isoformat()};self.write(key,d);self.errors.pop(code,None);return envelope(d,False)
   except Exception as e:
    message=str(e);self.errors[code]=(time.monotonic(),message,now())
    if old:return envelope(old,True,True,message)
    raise
 def backfill_amount(self,code):
  """Fill only missing source amounts; never change dates, OHLCV or price fetch time."""
  if not allowed(code):raise ValueError('仅支持已有沪深真实行情缓存')
  with self.lock:
   old=self.read(code+'.none')
   if not old or old.get('source')!='BaoStock':raise ValueError('本股没有可回填的BaoStock缓存')
   missing={r['date'] for r in old['rows'] if r.get('tradestatus')!='0' and not r.get('amount','').strip()}
   if not missing:return {'code':code,'filled':0,'remaining':0,'cacheHit':True}
   raw=self.source.query('query_history_k_data_plus',code=code,fields='date,code,amount,tradestatus',start_date=min(missing),end_date=max(missing),frequency='d',adjustflag='3')
   values={}
   for r in raw:
    dt.date.fromisoformat(r['date'])
    if r.get('code')!=code or not min(missing)<=r['date']<=max(missing):raise ValueError('回填来源代码或日期不一致，原缓存未覆盖')
    if r['date'] in values:raise ValueError('回填来源日期重复，原缓存未覆盖')
    if r.get('tradestatus')=='0' or not r.get('amount','').strip():continue
    try:value=float(r['amount'])
    except ValueError:raise ValueError('回填来源成交额无效，原缓存未覆盖')
    if not math.isfinite(value) or value<0:raise ValueError('回填来源成交额无效，原缓存未覆盖')
    values[r['date']]=r['amount']
   filled=missing.intersection(values)
   if filled:
    rows=[{**r,'amount':values[r['date']]} if r['date'] in filled else dict(r) for r in old['rows']]
    self.write(code+'.none',{**old,'rows':rows,'amountUnit':'CNY','amountBackfilledAt':now()})
   logging.info('amount.backfill code=%s filled=%d remaining=%d',code,len(filled),len(missing-filled))
   return {'code':code,'filled':len(filled),'remaining':len(missing-filled),'complete':not bool(missing-filled)}
 def batch(self,codes):
  if not isinstance(codes,list) or len(codes)>30 or not all(isinstance(c,str) for c in codes):raise ValueError('每批最多30支股票')
  results=[]
  for code in dict.fromkeys(codes):
   try:results.append({'code':code,**self.history(code,True)})
   except Exception as e:results.append({'code':code,'error':str(e),'stale':True})
  return {'results':results,'finishedAt':now()}
STORE=Store(ROOT/'cache',BaoSource(ROOT/'.runtime/source-refusal.json'))
class Handler(SimpleHTTPRequestHandler):
 def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT/'dist'),**kwargs)
 def trusted(self):
  host=self.headers.get('Host','');origin=self.headers.get('Origin');return host in ['127.0.0.1:5178','localhost:5178'] and (not origin or origin in ['http://127.0.0.1:5178','http://localhost:5178'])
 def json(self,data,status=200):
  body=json.dumps(data,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)));self.send_header('X-Content-Type-Options','nosniff');self.end_headers()
  try:self.wfile.write(body)
  except (BrokenPipeError,ConnectionResetError):logging.info('client.disconnected %s',self.path)
 def log_message(self,format,*args):logging.info('http '+format,*args)
 def do_GET(self):
  if not self.trusted():self.json({'error':'仅允许本机同源访问'},403);return
  p=urllib.parse.urlsplit(self.path)
  try:
   if p.path=='/api/directory':self.json(STORE.directory());return
   if p.path=='/api/history':self.json(STORE.history(urllib.parse.parse_qs(p.query).get('code',[''])[0]));return
   if p.path=='/api/health':self.json({'status':'ok','application':'candlescope','pid':os.getpid(),'instance':os.environ.get('SHIRI_INSTANCE','foreground'),'source':'BaoStock','adjustment':'none'});return
   if p.path.startswith('/api/'):self.json({'error':'未知 API'},404);return
   super().do_GET()
  except ValueError as e:self.json({'error':str(e)},400)
  except Exception as e:
   logging.exception('request.failed %s',self.path)
   self.json({'error':str(e),'networkStopped':getattr(STORE.source,'blocked',False)},502)
 def do_POST(self):
  if not self.trusted():self.json({'error':'仅允许本机同源访问'},403);return
  try:
   size=int(self.headers.get('Content-Length','0'))
   if size>8192:raise ValueError('请求过大')
   body=json.loads(self.rfile.read(size) or '{}')
   if self.path=='/api/refresh':self.json(STORE.history(body.get('code',''),True))
   elif self.path=='/api/amount/backfill':self.json(STORE.backfill_amount(body.get('code','')))
   elif self.path=='/api/batch':self.json(STORE.batch(body.get('codes',[])))
   elif self.path=='/api/directory/refresh':self.json(STORE.directory(True))
   else:self.json({'error':'未知 API'},404)
  except (ValueError,TypeError) as e:self.json({'error':str(e)},400)
  except Exception as e:
   logging.exception('request.failed %s',self.path)
   self.json({'error':str(e),'networkStopped':getattr(STORE.source,'blocked',False)},502)
if __name__=='__main__':
 runtime=ROOT/'.runtime';runtime.mkdir(exist_ok=True)
 logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s',handlers=[RotatingFileHandler(runtime/'server.log',maxBytes=1000000,backupCount=3),logging.StreamHandler()])
 if not (ROOT/'dist/index.html').exists():raise SystemExit('请先 npm run build')
 server=None
 try:
  server=ThreadingHTTPServer(('127.0.0.1',5178),Handler)
  def stop(signum,_frame):
   logging.info('server.stop_requested pid=%s signal=%s',os.getpid(),signum)
   threading.Thread(target=server.shutdown,daemon=True).start()
  signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
  logging.info('server.started pid=%s instance=%s url=http://127.0.0.1:5178/',os.getpid(),os.environ.get('SHIRI_INSTANCE','foreground'))
  print('CandleScope http://127.0.0.1:5178/ · Ctrl+C 停止；仅本机，无自动任务',flush=True)
  server.serve_forever()
  logging.info('server.stopped pid=%s',os.getpid())
 except Exception:
  logging.exception('server.fatal pid=%s',os.getpid());raise
 finally:
  if server:server.server_close()
