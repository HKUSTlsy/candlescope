"""One source query per existing cache; stop the batch on any failure."""
import json,pathlib,urllib.request,sys
root=pathlib.Path(__file__).resolve().parents[1]
codes=sorted(p.name.removesuffix('.none.json') for p in (root/'cache').glob('*.none.json'))
if '--all-cached' not in sys.argv:raise SystemExit('Explicit usage: backfill_amount.py --all-cached')
for code in codes:
 request=urllib.request.Request('http://127.0.0.1:5178/api/amount/backfill',data=json.dumps({'code':code}).encode(),headers={'Content-Type':'application/json'})
 try:
  with urllib.request.urlopen(request,timeout=90) as reply:result=json.load(reply)
 except Exception as error:raise SystemExit(f'{code}: stopped without continuing: {error}')
 print(json.dumps(result,ensure_ascii=False),flush=True)
