import {test} from 'node:test';
import assert from 'node:assert/strict';
import {followIndicatorReadout} from '../src/indicator-readout.ts';
test('readout refresh follows asynchronous indicator computation without hover',()=>{
 const listeners=new Set<()=>void>();const h={on:(_:'ready',cb:()=>void)=>{listeners.add(cb);return ()=>{listeners.delete(cb);};}};
 const frames:(()=>void)[]=[];let computed=false,readout='Volume';
 const stop=followIndicatorReadout([h],()=>true,()=>{readout=computed?'Volume SMA MACD':'Volume';},cb=>frames.push(cb));
 frames.shift()!();assert.equal(readout,'Volume');computed=true;listeners.forEach(cb=>cb());frames.shift()!();assert.equal(readout,'Volume SMA MACD');stop();assert.equal(listeners.size,0);
});
test('superseded chart or configuration cannot update readout from pending frame',()=>{
 const frames:(()=>void)[]=[];let current=true,calls=0;
 followIndicatorReadout([],()=>current,()=>calls++,cb=>frames.push(cb));current=false;frames.shift()!();assert.equal(calls,0);
});
