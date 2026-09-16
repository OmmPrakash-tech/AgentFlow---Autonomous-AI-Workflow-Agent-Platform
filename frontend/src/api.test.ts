import {describe,it,expect,vi,beforeEach} from 'vitest';
beforeEach(()=>{vi.resetModules();vi.stubGlobal('sessionStorage',{getItem:()=>null,setItem:vi.fn(),removeItem:vi.fn()})});
describe('authenticated API client',()=>{
 it('attaches bearer credentials and surfaces server rejection',async()=>{
  const fetch=vi.fn().mockResolvedValue({ok:false,status:403,json:async()=>({message:'Permission denied'})});vi.stubGlobal('fetch',fetch);
  const {api,setToken}=await import('./api');setToken('test-token');await expect(api('/agents',{})).rejects.toThrow('Permission denied');
  expect(fetch.mock.calls[0][1].headers.Authorization).toBe('Bearer test-token');
 });
 it('parses authenticated SSE state without URL tokens',async()=>{
  const fetch=vi.fn().mockResolvedValue({ok:true,text:async()=>'event: state\ndata: {"status":"COMPLETED"}\n\n'});vi.stubGlobal('fetch',fetch);
  const {stateStream}=await import('./api');expect(await stateStream('run-id',new AbortController().signal)).toEqual({status:'COMPLETED'});
  expect(fetch.mock.calls[0][0]).toBe('/api/runs/run-id/events');
 });
});
