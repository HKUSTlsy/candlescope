export type Bar={date:string,time:number,open:number,high:number,low:number,close:number,volume:number,amount?:number,amountPartial?:boolean};
export type Period='d'|'w'|'m';
export type Dataset={code:string,source:string,adjustment:string,volumeUnit:string,amountUnit?:string,fetchedAt:string,rows:Record<string,string>[],name?:string};
export function dateTime(date:string):number {
 if(!/^\d{4}-\d{2}-\d{2}$/.test(date))throw Error('日期须为 YYYY-MM-DD');
 const t=Date.parse(date+'T00:00:00+08:00');
 if(!Number.isFinite(t)||new Date(t+8*3600000).toISOString().slice(0,10)!==date)throw Error('无效日期');
 return t;
}
export function normalize(rows:Record<string,string>[],unit='shares'):Bar[]{
 const seen=new Set<string>();const bars:Bar[]=[];
 if(!['shares','lots'].includes(unit))throw Error('成交量单位须为股或手');
 for(const row of rows){
  const time=dateTime(row.date);if(seen.has(row.date))throw Error('日期重复：'+row.date);seen.add(row.date);
  if(row.tradestatus==='0')continue;
  const b:Bar={date:row.date,time,open:Number(row.open),high:Number(row.high),low:Number(row.low),close:Number(row.close),volume:Number(row.volume)*(unit==='lots'?100:1)};
  if(['open','high','low','close','volume'].some(k=>row[k]?.trim()==='')||![b.open,b.high,b.low,b.close,b.volume].every(Number.isFinite)||Math.min(b.open,b.low,b.close)<=0||b.high<Math.max(b.open,b.close,b.low)||b.low>Math.min(b.open,b.close)||b.volume<0)throw Error('OHLCV 无效：'+row.date);
  const day=new Date(time+8*3600000).getUTCDay();if(day===0||day===6)throw Error('日线含周末日期：'+row.date);
  if(row.amount?.trim()){const amount=Number(row.amount);if(!Number.isFinite(amount)||amount<0)throw Error('成交额无效：'+row.date);b.amount=amount;}
  bars.push(b);
 }
 return bars.sort((a,b)=>a.time-b.time);
}
export function aggregate(bars:Bar[],period:Period):Bar[]{
 if(period==='d')return bars.map(b=>({...b}));
 const groups=new Map<string,Bar>();
 for(const b of bars){
  const d=new Date(b.time+8*3600000);const dow=d.getUTCDay()||7;
  const key=period==='m'?b.date.slice(0,7):new Date(d.getTime()-(dow-1)*86400000).toISOString().slice(0,10);
  const g=groups.get(key);
  if(!g)groups.set(key,{...b});else{g.high=Math.max(g.high,b.high);g.low=Math.min(g.low,b.low);g.close=b.close;g.volume+=b.volume;if(g.amount!==undefined||b.amount!==undefined){if(g.amountPartial||b.amountPartial||g.amount===undefined||b.amount===undefined)g.amountPartial=true;g.amount=(g.amount??0)+(b.amount??0);}g.time=b.time;g.date=b.date;}
 }
 return [...groups.values()];
}
export function sma(v:number[],n:number){return v.map((_,i)=>i<n-1?null:v.slice(i-n+1,i+1).reduce((a,b)=>a+b,0)/n);}
export function ema(v:number[],n:number){let p=NaN,run=0;return v.map((x,i)=>{if(!Number.isFinite(x)){p=NaN;run=0;return NaN;}run++;if(Number.isFinite(p))return p=x*2/(n+1)+p*(1-2/(n+1));if(run<n)return NaN;return p=v.slice(i-n+1,i+1).reduce((a,b)=>a+b,0)/n;});}
export function macd(v:number[]){const f=ema(v,12),s=ema(v,26),dif=f.map((x,i)=>x-s[i]),dea=ema(dif,9);return {dif,dea,hist:dif.map((x,i)=>x-dea[i])};}
export function rsi(v:number[],n=14):(number|null)[]{let gain=0,loss=0;return v.map((x,i)=>{if(i===0)return null;const d=x-v[i-1];if(i<=n){gain+=Math.max(d,0)/n;loss+=Math.max(-d,0)/n;}else{gain=(gain*(n-1)+Math.max(d,0))/n;loss=(loss*(n-1)+Math.max(-d,0))/n;}return i<n?null:loss===0?100:100-100/(1+gain/loss);});}
export function parseCSV(text:string,code:string,unit:string,source:string):Dataset{
 if(!/^(sh|sz|bj)\.\d{6}$/.test(code))throw Error('代码格式例如 sz.000001 / sh.600519 / bj.430047');
 const lines=text.replace(/^\uFEFF/,'').trim().split(/\r?\n/);const fields=lines.shift()?.split(',').map(s=>s.trim())??[];
 if(!['date','open','high','low','close','volume'].every(x=>fields.includes(x)))throw Error('缺少 CSV 列：date,open,high,low,close,volume');
 const rows=lines.filter(Boolean).map(line=>{const cells=line.split(',').map(s=>s.trim());if(cells.length!==fields.length)throw Error('CSV 列数不一致；不支持带逗号的引号字段');return Object.fromEntries(fields.map((f,i)=>[f,cells[i]]));});
 normalize(rows,unit);return {code,source,adjustment:'imported-unknown',volumeUnit:unit,amountUnit:'CNY',fetchedAt:new Date().toISOString(),rows};
}
export function example():Dataset{
 const rows:Record<string,string>[]=[];let p=100;for(let i=0;i<180;i++){const t=Date.UTC(2025,0,2+i),day=new Date(t).getUTCDay();if(!day||day===6)continue;const o=p;p=100+Math.sin(i/9)*8+i*.08;rows.push({date:new Date(t).toISOString().slice(0,10),open:o.toFixed(2),high:(Math.max(o,p)+2).toFixed(2),low:(Math.min(o,p)-2).toFixed(2),close:p.toFixed(2),volume:String(100000+i*113)});}return {code:'DEMO',source:'合成样例 · 非真实证券价格',adjustment:'synthetic',volumeUnit:'shares',fetchedAt:'2025-06-30',rows};
}

export function formatAmount(bar:Pick<Bar,'amount'|'amountPartial'>):string{if(bar.amount===undefined)return '—（缺失）';const n=bar.amount;const value=n>=1e8?(n/1e8).toFixed(2)+' 亿元':n>=1e4?(n/1e4).toFixed(2)+' 万元':n.toFixed(2)+' 元';return value+(bar.amountPartial?'（部分缺失）':'');}
export function barReadings(last:Bar,previous?:Bar):[string,string][]{return [['收盘',last.close.toFixed(2)],['周期涨跌',previous?((last.close/previous.close-1)*100).toFixed(2)+'%':'—'],['开盘',last.open.toFixed(2)],['最高',last.high.toFixed(2)],['最低',last.low.toFixed(2)],['成交量',(last.volume/1e4).toFixed(2)+' 万股'],['成交额',formatAmount(last)]];}
