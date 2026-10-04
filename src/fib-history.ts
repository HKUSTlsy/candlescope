export type Timeline<T>={version:2,states:T[],index:number};
const copy=<T>(v:T):T=>JSON.parse(JSON.stringify(v));
export function timeline<T>(raw:unknown,current:T):Timeline<T>{const r=raw as Partial<Timeline<T>>|null;if(r?.version===2&&Array.isArray(r.states)&&r.states.length&&Number.isInteger(r.index)&&r.index!>=0&&r.index!<r.states.length)return copy(r as Timeline<T>);return {version:2,states:[copy(current)],index:0};}
export function commit<T>(h:Timeline<T>,next:T):boolean{if(JSON.stringify(h.states[h.index])===JSON.stringify(next))return false;h.states=h.states.slice(0,h.index+1);h.states.push(copy(next));if(h.states.length>100)h.states.shift();h.index=h.states.length-1;return true;}
export function travel<T>(h:Timeline<T>,direction:-1|1):T|undefined{const i=h.index+direction;if(i<0||i>=h.states.length)return;h.index=i;return copy(h.states[i]);}
