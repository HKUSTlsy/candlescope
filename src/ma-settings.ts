import {sma} from './core.ts';
export type MALine={period:number;enabled:boolean;color:string};
export type MAConfig={version:1;lines:MALine[]};
export const MA_KEY='shiri.ma.v1';
export const MA_MAX_LINES=8;
export const MA_MAX_PERIOD=500;
export const MA_COLORS=['#e8bc67','#78a9ef','#b692dd','#58c6ab','#f27b85','#e3a9cf','#99b86e','#df9c65'];
export function defaultMA():MAConfig{return {version:1,lines:[5,10,20].map((period,i)=>({period,enabled:true,color:MA_COLORS[i]}))};}
export function validateMA(value:unknown):MAConfig{
 if(!value||typeof value!=='object'||!('version' in value)||value.version!==1||!('lines' in value)||!Array.isArray(value.lines))throw Error('均线配置格式无效');
 if(value.lines.length<1||value.lines.length>MA_MAX_LINES)throw Error('请保留 1～8 条均线；需要隐藏时关闭显示');
 const seen=new Set<number>();
 const lines=value.lines.map((line:unknown,i)=>{
  if(!line||typeof line!=='object'||!('period' in line)||!('enabled' in line)||!('color' in line))throw Error(`第 ${i+1} 条均线配置不完整`);
  const {period,enabled,color}=line;
  if(typeof period!=='number'||!Number.isSafeInteger(period)||period<1||period>MA_MAX_PERIOD)throw Error(`第 ${i+1} 条周期必须是 1～500 的正整数`);
  if(seen.has(period))throw Error(`周期 ${period} 重复，请设置不同周期`);seen.add(period);
  if(typeof enabled!=='boolean')throw Error(`第 ${i+1} 条显示开关无效`);
  if(typeof color!=='string'||!/^#[0-9a-f]{6}$/i.test(color))throw Error(`第 ${i+1} 条颜色无效`);
  return {period,enabled,color:color.toLowerCase()};
 });return {version:1,lines};
}
export function loadMA(raw:string|null):{config:MAConfig;warning:string}{
 if(raw===null)return {config:defaultMA(),warning:''};
 try{return {config:validateMA(JSON.parse(raw)),warning:''};}catch{return {config:defaultMA(),warning:'已存均线配置损坏，暂用 5/10/20；原记录保留，保存设置后才替换。'};}
}
export function maValues(closes:number[],config:MAConfig){return validateMA(config).lines.filter(l=>l.enabled).map(l=>({...l,value:sma(closes,l.period).at(-1)??null}));}
