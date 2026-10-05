// Readouts must follow computed models, not synchronous handle creation.
export type ReadyIndicator={on(event:'ready',handler:()=>void):()=>void};
export function followIndicatorReadout(handles:ReadyIndicator[],isCurrent:()=>boolean,refresh:()=>void,schedule:(callback:()=>void)=>void){
 const update=()=>schedule(()=>{if(isCurrent())refresh();});
 const off=handles.map(h=>h.on('ready',update));
 update();
 return ()=>off.forEach(dispose=>dispose());
}
