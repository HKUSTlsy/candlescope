import {test} from 'node:test';
import assert from 'node:assert/strict';
import {normalize,aggregate,dateTime,parseCSV,sma,ema,macd,rsi} from '../src/core.ts';
const rows=[{date:'2024-01-02',open:'10',high:'12',low:'9',close:'11',volume:'100'},{date:'2024-01-05',open:'11',high:'13',low:'10',close:'12',volume:'200'},{date:'2024-01-08',open:'12',high:'14',low:'11',close:'13',volume:'300'},{date:'2024-02-01',open:'13',high:'15',low:'12',close:'14',volume:'400'}];
test('Shanghai calendar date and leading zero code',()=>{assert.equal(new Date(dateTime('2024-01-02')).toISOString(),'2024-01-01T16:00:00.000Z');assert.throws(()=>dateTime('2024-02-30'));assert.equal(parseCSV('date,open,high,low,close,volume\n2024-01-02,10,12,9,11,1','sz.000001','lots','test').code,'sz.000001');});
test('OHLCV validation, suspension gaps and lots conversion',()=>{assert.equal(normalize(rows,'lots')[0].volume,10000);assert.equal(normalize([...rows,{...rows[0],date:'2024-01-03',tradestatus:'0'}]).length,4);assert.throws(()=>normalize([...rows,rows[0]]));assert.throws(()=>normalize([{...rows[0],high:'8'}]));assert.throws(()=>normalize([{...rows[0],date:'2024-01-06'}]));assert.throws(()=>parseCSV('date,open','sz.000001','shares','test'));});
test('weekly/monthly aggregate only supplied trading bars',()=>{const b=normalize(rows),w=aggregate(b,'w'),m=aggregate(b,'m');assert.equal(w.length,3);assert.deepEqual(w[0],{date:'2024-01-05',time:dateTime('2024-01-05'),open:10,high:13,low:9,close:12,volume:300});assert.equal(m.length,2);assert.equal(m[0].volume,600);assert.equal(m[0].close,13);assert.equal(m[0].date,'2024-01-08');assert.equal(aggregate(b,'d').length,4);});
test('native convention indicator references and warm-up',()=>{assert.deepEqual(sma([1,2,3,4],3),[null,null,2,3]);const e=ema([1,2,3,4],3);assert(Number.isNaN(e[0]));assert.equal(e[2],2);assert.equal(e[3],3);const v=Array.from({length:60},(_,i)=>i+1);const m=macd(v);assert(Number.isNaN(m.dif[24]));assert.equal(m.dif[25],7);assert(Math.abs(m.hist[40])<1e-10);assert.equal(rsi(v)[14],100);assert.equal(rsi(v.reverse())[14],0);});


test('amount is source RMB and independent of shares/lots, with explicit missing CSV support',async()=>{
 const {formatAmount}=await import('../src/core.ts');
 const csv='date,open,high,low,close,volume,amount\n2024-01-02,10,12,9,11,2,123456.78';
 const d=parseCSV(csv,'sz.000001','lots','QA');const b=normalize(d.rows,d.volumeUnit)[0];
 assert.equal(b.volume,200);assert.equal(b.amount,123456.78);assert.equal(d.amountUnit,'CNY');
 assert.equal(formatAmount(b),'12.35 万元');assert.equal(formatAmount({amount:0}),'0.00 元');assert.equal(formatAmount({amount:100000000}),'1.00 亿元');assert.equal(formatAmount({}),'—（缺失）');
 assert.equal(normalize(rows)[0].amount,undefined);
 for(const amount of ['NaN','Infinity','-1'])assert.throws(()=>normalize([{...rows[0],amount}]));
 assert.equal(normalize([{...rows[0],amount:''}])[0].amount,undefined);
});
test('daily, weekly and monthly amount sums preserve missing coverage without estimation',async()=>{
 const {formatAmount}=await import('../src/core.ts');
 const complete=normalize(rows.map((r,i)=>({...r,amount:String((i+1)*100)})));
 assert.equal(aggregate(complete,'d')[0].amount,100);assert.equal(aggregate(complete,'w')[0].amount,300);assert.equal(aggregate(complete,'m')[0].amount,600);
 const partial=normalize(rows.map((r,i)=>i===0?r:{...r,amount:String((i+1)*100)}));
 const m=aggregate(partial,'m');assert.equal(m[0].amount,500);assert.equal(m[0].amountPartial,true);assert.equal(formatAmount(m[0]),'500.00 元（部分缺失）');assert.equal(m[1].amountPartial,undefined);
 assert.equal(aggregate(normalize(rows),'m')[0].amount,undefined);
 const reverseMissing=aggregate(normalize(rows.map((r,i)=>i===1?r:{...r,amount:'100'})),'w')[0];assert.equal(reverseMissing.amount,100);assert.equal(reverseMissing.amountPartial,true);
});
test('OHLCV and amount readings follow the supplied hover/latest/security bar',async()=>{
 const {barReadings}=await import('../src/core.ts');
 const a=normalize([{...rows[0],amount:'30000'},{...rows[1],amount:'100000000'}]);
 assert.deepEqual(barReadings(a[0]).slice(-2),[['成交量','0.01 万股'],['成交额','3.00 万元']]);
 assert.equal(barReadings(a[1],a[0]).at(-1)?.[1],'1.00 亿元');
 const other=normalize([{...rows[0],close:'10',amount:''}])[0];assert.equal(barReadings(other)[0][1],'10.00');assert.equal(barReadings(other).at(-1)?.[1],'—（缺失）');
});
