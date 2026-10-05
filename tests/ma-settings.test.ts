import {test} from 'node:test';
import assert from 'node:assert/strict';
import {defaultMA,validateMA,loadMA,maValues,MA_MAX_LINES} from '../src/ma-settings.ts';
test('MA defaults and legacy absent configuration are 5/10/20 without migration writes',()=>{
 assert.deepEqual(defaultMA().lines.map(l=>l.period),[5,10,20]);assert.deepEqual(loadMA(null),{config:defaultMA(),warning:''});
 const a=defaultMA();a.lines[0].period=30;assert.equal(defaultMA().lines[0].period,5);
});
test('MA bounds, duplicate and malformed records reject instead of coercing',()=>{
 for(const period of [0,-1,1.5,501,NaN,Infinity,'5',null])assert.throws(()=>validateMA({version:1,lines:[{period,enabled:true,color:'#78a9ef'}]}));
 for(const value of [null,{},[],{version:2,lines:[]},{version:1,lines:[]},{version:1,lines:[{period:1,enabled:'true',color:'#78a9ef'}]},{version:1,lines:[{period:1,enabled:true,color:'red'}]}])assert.throws(()=>validateMA(value));
 const d=defaultMA();d.lines[1].period=5;assert.throws(()=>validateMA(d),/重复/);
 assert.throws(()=>validateMA({version:1,lines:Array.from({length:MA_MAX_LINES+1},(_,i)=>({period:i+1,enabled:true,color:'#abcdef'}))}));
 assert.deepEqual(validateMA({version:1,lines:[{period:500,enabled:false,color:'#ABCDEF'}]}).lines,[{period:500,enabled:false,color:'#abcdef'}]);
});
test('MA corrupted storage falls back without replacing supplied bytes; round trip preserves settings',()=>{
 for(const raw of ['{bad','null','{"version":1,"lines":[]}']){const r=loadMA(raw);assert.deepEqual(r.config,defaultMA());assert.match(r.warning,/原记录保留/);}
 const c=defaultMA();c.lines[0]={period:30,enabled:false,color:'#12abcd'};assert.deepEqual(loadMA(JSON.stringify(c)),{config:c,warning:''});
});
test('custom MA uses supplied current-period closes and hides insufficient or disabled lines',()=>{
 const config={version:1 as const,lines:[{period:2,enabled:true,color:'#abcdef'},{period:3,enabled:true,color:'#123456'},{period:5,enabled:true,color:'#654321'},{period:1,enabled:false,color:'#654321'}]};
 assert.deepEqual(maValues([2,4,8,10],config).map(l=>[l.period,l.value]),[[2,9],[3,22/3],[5,null]]);
 assert.deepEqual(maValues([12,18,30],config).map(l=>[l.period,l.value]),[[2,24],[3,20],[5,null]]);
 assert.deepEqual(maValues([],config).map(l=>l.value),[null,null,null]);
});
