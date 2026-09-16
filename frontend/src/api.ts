export type User={id:string;email:string;role:string;forceReset:boolean};
let token=sessionStorage.getItem('agentflow-token')||'';
export function setToken(value:string){token=value; if(value)sessionStorage.setItem('agentflow-token',value);else sessionStorage.removeItem('agentflow-token');}
export async function api<T=any>(path:string,body?:unknown,method?:string):Promise<T>{
 const response=await fetch('/api'+path,{method:method||(body?'POST':'GET'),headers:{'Content-Type':'application/json',...(token?{Authorization:'Bearer '+token}:{})},body:body?JSON.stringify(body):undefined});
 if(!response.ok){const error=await response.json().catch(()=>({}));throw new Error(error.message||error.detail||('Request failed ('+response.status+')'));}
 return response.json();
}
export async function stateStream(id:string,signal:AbortSignal){
 const r=await fetch('/api/runs/'+id+'/events',{headers:{Authorization:'Bearer '+token},signal});
 if(!r.ok)throw new Error('Live connection unavailable');
 const text=await r.text(); const data=text.split('\n').find(line=>line.startsWith('data: '));
 if(!data)throw new Error('No state event received');return JSON.parse(data.slice(6));
}
export async function exportReport(id:string){
 const r=await fetch('/api/runs/'+id+'/report',{headers:{Authorization:'Bearer '+token}});
 if(!r.ok)throw new Error('Report unavailable');
 const url=URL.createObjectURL(await r.blob());const a=document.createElement('a');a.href=url;a.download='agentflow-'+id+'.md';a.click();URL.revokeObjectURL(url);
}
