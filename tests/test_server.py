import unittest,tempfile,pathlib,sys,datetime,concurrent.futures,time
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
from server import Store,listed,allowed,valid_rows,today
ROW={'date':'2026-09-30','code':'sz.300750','open':'290','high':'293','low':'285','close':'291','volume':'100','adjustflag':'3','tradestatus':'1'}
STOCKS=[{'code':'sz.300750','code_name':'宁德时代','type':'1','status':'1'},{'code':'sh.600519','code_name':'贵州茅台','type':'1','status':'1'}]
class Fake:
 def __init__(self):self.calls=[];self.fail=set();self.rows=[ROW]
 def query(self,method,**kwargs):
  self.calls.append((method,kwargs));time.sleep(.01)
  if kwargs.get('code') in self.fail:raise RuntimeError('模拟联网错误')
  if method=='query_stock_basic':return STOCKS
  if method=='query_trade_dates':return [{'calendar_date':'2026-09-30','is_trading_day':'1'},{'calendar_date':'2026-10-01','is_trading_day':'0'},{'calendar_date':today().isoformat(),'is_trading_day':'0'}]
  return [{**r,'code':kwargs['code']} for r in self.rows]
class ServiceTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.source=Fake();self.store=Store(pathlib.Path(self.tmp.name),self.source)
 def tearDown(self):self.tmp.cleanup()
 def old(self,code='sz.300750'):
  self.store.write(code+'.none',{'code':code,'rows':[{**ROW,'code':code}],'fetchedAt':'2025-01-01T00:00:00+00:00','adjustment':'none','volumeUnit':'shares','source':'BaoStock'})
 def test_directory_filters(self):
  bad=[{**STOCKS[0],'type':'2'},{**STOCKS[0],'status':'0'},{**STOCKS[0],'code':'bj.430047'},{**STOCKS[0],'code':'sh.900001'}]
  self.assertEqual(listed(STOCKS+bad),STOCKS);self.assertFalse(allowed('sz.00001'));self.assertEqual(self.store.directory()['stocks'],STOCKS)
 def test_cache_hit_and_restart(self):
  d=self.store.history('sz.300750');calls=len(self.source.calls);self.assertFalse(d['cacheHit']);self.assertTrue(self.store.history('sz.300750')['cacheHit']);other=Store(pathlib.Path(self.tmp.name),self.source);self.assertTrue(other.history('sz.300750')['cacheHit']);self.assertEqual(len(self.source.calls),calls)
 def test_repeated_concurrent_force_singleflight(self):
  with concurrent.futures.ThreadPoolExecutor(4) as ex:results=list(ex.map(lambda _:self.store.history('sz.300750',True),range(4)))
  self.assertEqual(len([m for m,_ in self.source.calls if m=='query_history_k_data_plus']),1);self.assertEqual(sum(not r['cacheHit'] for r in results),1)
 def test_holiday_empty_increment_keeps_cache_and_dates(self):
  self.old();self.source.rows=[];d=self.store.history('sz.300750',True);self.assertEqual(d['calendarLatest'],'2026-09-30');self.assertEqual(d['dataThrough'],'2026-09-30');self.assertFalse(d['stale']);self.assertEqual(len(d['data']['rows']),1);args=[a for m,a in self.source.calls if m=='query_history_k_data_plus'][0];self.assertEqual(args['start_date'],'2026-09-23');self.assertEqual(args['adjustflag'],'3')
 def test_batch_failure_isolation_and_old_cache(self):
  self.old();self.source.fail.add('sz.300750');r=self.store.batch(['sz.300750','sh.600519','bad','sh.600519'])['results'];self.assertEqual(len(r),3);self.assertTrue(r[0]['stale']);self.assertEqual(len(r[0]['data']['rows']),1);self.assertIn('data',r[1]);self.assertIn('error',r[2]);self.assertEqual(r[1]['data']['volumeUnit'],'shares')
 def test_missing_prices_preserve_old(self):
  self.old();self.source.rows=[{**ROW,'close':''}];r=self.store.history('sz.300750',True);self.assertTrue(r['stale']);self.assertEqual(r['data']['rows'][0]['close'],'291');self.assertIsNone(valid_rows([{**ROW,'tradestatus':'0','close':''}])[0].get('missing'))
 def test_no_history_is_valid_empty_state(self):
  self.source.rows=[];r=self.store.history('sz.300750');self.assertEqual(r['data']['rows'],[]);self.assertIsNone(r['dataThrough']);self.assertFalse(r['stale'])
if __name__=='__main__':unittest.main()

class RetryTests(unittest.TestCase):
 def test_transport_retry_once(self):
  from server import BaoSource
  from unittest.mock import patch
  s=BaoSource()
  with patch.object(s,'once',side_effect=[RuntimeError('BaoStock 10002007 网络接收错误'),[ROW]]) as f,patch('server.time.sleep'):
   self.assertEqual(s.query('query_history_k_data_plus'),[ROW]);self.assertEqual(f.call_count,2)
 def test_refusal_never_retry(self):
  from server import BaoSource
  from unittest.mock import patch
  s=BaoSource()
  def deny(*args,**kwargs):s.blocked=True;raise RuntimeError('403 Forbidden')
  with patch.object(s,'once',side_effect=deny) as f,patch('server.time.sleep'):
   with self.assertRaises(RuntimeError):s.query('query_history_k_data_plus')
   self.assertEqual(f.call_count,1)
 def test_retry_bounded(self):
  from server import BaoSource
  from unittest.mock import patch
  s=BaoSource()
  with patch.object(s,'once',side_effect=RuntimeError('10002007')) as f,patch('server.time.sleep'):
   with self.assertRaises(RuntimeError):s.query('query_history_k_data_plus')
   self.assertEqual(f.call_count,2)

class AmountTests(unittest.TestCase):
 setUp=ServiceTests.setUp
 tearDown=ServiceTests.tearDown
 old=ServiceTests.old
 def test_amount_source_fields_and_legacy_overlap(self):
  self.old();self.source.rows=[{**ROW,'amount':'29001.25'}]
  r=self.store.history('sz.300750',True)
  self.assertEqual(r['data']['rows'][0]['amount'],'29001.25')
  self.assertEqual(r['data']['amountUnit'],'CNY')
  args=[a for m,a in self.source.calls if m=='query_history_k_data_plus'][0]
  self.assertIn('amount',args['fields'].split(','));self.assertEqual(args['start_date'],'2026-09-23')
 def test_invalid_amount_keeps_previous_cache(self):
  self.old();self.source.rows=[{**ROW,'amount':'NaN'}]
  r=self.store.history('sz.300750',True);self.assertTrue(r['stale']);self.assertNotIn('amount',r['data']['rows'][0])

class BackfillTests(unittest.TestCase):
 setUp=ServiceTests.setUp
 tearDown=ServiceTests.tearDown
 old=ServiceTests.old
 def test_fill_preserves_prices_fetch_time_and_existing_amount(self):
  self.old();old=self.store.read('sz.300750.none');self.source.rows=[{**ROW,'amount':'123.45'}]
  self.assertEqual(self.store.backfill_amount('sz.300750')['filled'],1)
  new=self.store.read('sz.300750.none');self.assertEqual(new['fetchedAt'],old['fetchedAt']);self.assertEqual({k:v for k,v in new['rows'][0].items() if k!='amount'},old['rows'][0])
  calls=len(self.source.calls);self.assertTrue(self.store.backfill_amount('sz.300750')['cacheHit']);self.assertEqual(len(self.source.calls),calls)
 def test_bad_source_never_overwrites_cache(self):
  for amount in ['NaN','-1','bad']:
   self.old();original=(self.store.path/'sz.300750.none.json').read_bytes();self.source.rows=[{**ROW,'amount':amount}]
   with self.assertRaises(ValueError):self.store.backfill_amount('sz.300750')
   self.assertEqual((self.store.path/'sz.300750.none.json').read_bytes(),original)
 def test_omission_reports_incomplete_without_fabrication(self):
  self.old();self.source.rows=[];original=self.store.read('sz.300750.none');r=self.store.backfill_amount('sz.300750');self.assertEqual(r['remaining'],1);self.assertFalse(r['complete']);self.assertEqual(self.store.read('sz.300750.none'),original)
 def test_failure_and_missing_cache_are_safe(self):
  self.old();self.source.fail.add('sz.300750');original=self.store.read('sz.300750.none')
  with self.assertRaises(RuntimeError):self.store.backfill_amount('sz.300750')
  self.assertEqual(self.store.read('sz.300750.none'),original)
  with self.assertRaises(ValueError):self.store.backfill_amount('sh.600519')

class SupervisorTests(unittest.TestCase):
 def run_supervisor(self,stop=False):
  import service,signal,contextlib,io
  from unittest.mock import patch,Mock
  with tempfile.TemporaryDirectory() as temporary:
   runtime=pathlib.Path(temporary);child=Mock();child.pid=123;child.returncode=7;child.poll.return_value=7
   if stop:(runtime/'stop-test').touch()
   with patch.object(service,'RUNTIME',runtime),patch.object(service,'STATE',runtime/'service.json'),patch.object(service.subprocess,'Popen',return_value=child) as launch,patch.object(service.time,'sleep'),patch.object(service.signal,'signal'),contextlib.redirect_stdout(io.StringIO()):
    service.supervise('test');return launch.call_count,service.state()
 def test_crash_retry_limit_records_terminal_failure(self):
  calls,record=self.run_supervisor();self.assertEqual(calls,4);self.assertEqual(record['status'],'failed');self.assertEqual(record['lastExitCode'],7);self.assertEqual(record['restarts'],3)
 def test_explicit_stop_never_launches_or_restarts(self):
  calls,record=self.run_supervisor(True);self.assertEqual(calls,0);self.assertEqual(record['status'],'stopped')

class PersistentRefusalTests(unittest.TestCase):
 def test_restart_cannot_clear_source_refusal(self):
  from server import BaoSource
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as tmp:
   marker=pathlib.Path(tmp)/'source-refusal.json';original=BaoSource(marker);original.reject('403 Forbidden');restarted=BaoSource(marker)
   with patch.object(restarted,'once') as query:
    with self.assertRaises(RuntimeError):restarted.query('query_history_k_data_plus')
    query.assert_not_called()
