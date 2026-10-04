"""Project-local, explicitly started supervisor. No OS service installation."""
import fcntl,json,os,pathlib,signal,subprocess,sys,time,urllib.request,uuid
ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNTIME=ROOT/'.runtime'
STATE=RUNTIME/'service.json'
def health():
 try:
  with urllib.request.urlopen('http://127.0.0.1:5178/api/health',timeout=1) as r:return json.load(r)
 except Exception:return None
def state():
 try:return json.loads(STATE.read_text())
 except (OSError,ValueError):return {}
def save(value):
 temporary=STATE.with_suffix('.tmp');temporary.write_text(json.dumps(value));temporary.replace(STATE)
def supervise(token):
 RUNTIME.mkdir(exist_ok=True)
 with (RUNTIME/'service.lock').open('a') as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:return
  stop=RUNTIME/('stop-'+token)
  signal.signal(signal.SIGTERM,lambda *_:stop.touch())
  signal.signal(signal.SIGINT,lambda *_:stop.touch())
  record={'instance':token,'supervisorPid':os.getpid(),'startedAt':time.time(),'restarts':0}
  for attempt in range(4):
   if stop.exists():break
   child=subprocess.Popen([sys.executable,str(ROOT/'scripts/server.py')],cwd=ROOT,env={**os.environ,'SHIRI_INSTANCE':token},stdin=subprocess.DEVNULL)
   record.update(status='running',childPid=child.pid,restarts=attempt);save(record)
   while child.poll() is None and not stop.exists():time.sleep(.25)
   if stop.exists() and child.poll() is None:
    child.terminate()
    try:child.wait(timeout=8)
    except subprocess.TimeoutExpired:child.kill();child.wait()
   record.update(lastExitCode=child.returncode,lastExitAt=time.time());save(record)
   print(json.dumps(record),flush=True)
   if stop.exists():break
   record['status']='recovering' if attempt<3 else 'failed';save(record)
   if attempt<3:
    for _ in range((attempt+1)*8):
     if stop.exists():break
     time.sleep(.25)
  record['status']='stopped' if stop.exists() else 'failed';save(record)
  stop.unlink(missing_ok=True)
def main():
 RUNTIME.mkdir(exist_ok=True)
 action=sys.argv[1] if len(sys.argv)>1 else 'status'
 if action=='supervise':supervise(sys.argv[2]);return
 if action=='status':print(json.dumps({'health':health(),'service':state()},ensure_ascii=False));return
 if action=='stop':
  old=state()
  if old.get('status') not in ('running','recovering'):print('No managed service running');return
  (RUNTIME/('stop-'+old['instance'])).touch()
  for _ in range(40):
   if state().get('status') in ('stopped','failed'):print('Managed service stopped');return
   time.sleep(.25)
  raise SystemExit('Stop not confirmed; inspect .runtime logs')
 if action!='start':raise SystemExit('Usage: service.py start|stop|status')
 existing=health()
 if existing:
  if existing.get('application') in ('candlescope','shiri'):print('CandleScope already running: http://127.0.0.1:5178/');return
  raise SystemExit('Port occupied by another application')
 token=uuid.uuid4().hex
 with (RUNTIME/'supervisor.log').open('a') as log:
  subprocess.Popen([sys.executable,__file__,'supervise',token],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
 for _ in range(80):
  ready=health()
  if ready and ready.get('application') in ('candlescope','shiri') and ready.get('instance')==token:print('CandleScope ready: http://127.0.0.1:5178/');return
  time.sleep(.25)
 raise SystemExit('Start not confirmed; inspect .runtime/server.log and supervisor.log')
if __name__=='__main__':main()
