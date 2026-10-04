export const FIB_RATIOS=[0,0.236,0.382,0.5,0.618,0.786,1] as const;
export type Anchor={time:number,price:number};
// Matches Vela 0.8.1 FibLevels: first click = 0, second click = 1.
export function fibPrices(a:Anchor,b:Anchor,ratios:readonly number[]=FIB_RATIOS){
 if(![a.time,a.price,b.time,b.price,...ratios].every(Number.isFinite))throw Error('锚点或比例无效');
 return ratios.map(ratio=>({ratio,price:a.price+ratio*(b.price-a.price)}));
}
export function reverseAnchors(anchors:Anchor[]):Anchor[]{if(anchors.length!==2)throw Error('斐波那契回撤需要两个锚点');return [{...anchors[1]},{...anchors[0]}];}
export function drawingKey(code:string){return 'shiri.drawings.v1:'+code;}
export type FibLevel={ratio:number,color:string,enabled:boolean};
export const FIB_COLORS=['#b2b5be','#ef737d','#e8bc67','#78c47d','#5ac5b5','#78a9ef','#b2b5be'];
export function defaultLevels():FibLevel[]{return FIB_RATIOS.map((ratio,i)=>({ratio,color:FIB_COLORS[i],enabled:true}));}
export function parseRatios(value:string):number[]{const tokens=value.trim().split(/[，,;；\s]+/);if(!value.trim()||/[，,;；]\s*[，,;；]/.test(value)||tokens.some(t=>!t))throw Error('请输入比例，以逗号或空格分隔');if(tokens.length>24)throw Error('最多24个比例');const n=tokens.map(t=>{if(!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(t))throw Error('比例必须是有限数字');return Number(t);});if(n.some(v=>!Number.isFinite(v)||Math.abs(v)>100))throw Error('比例范围为 -100 到 100');if(new Set(n).size!==n.length)throw Error('比例不能重复');return n;}
export function levelsFrom(props:Record<string,unknown>|undefined):FibLevel[]{return Array.isArray(props?.levels)?props.levels as FibLevel[]:defaultLevels();}
