import {useEffect,useRef,useState} from 'react';
import {API,request,sessionToken} from './api';
import {mergeCaption} from './captions';
import type {Caption,Event,Mode,Status} from './types';
const initial:Status={type:'status',mode:'stop',capture_connected:false,asr_backend:'mock',translate_backend:'mock',metrics:{},warning:''};
export function useLive() {
  const [status,setStatus]=useState(initial),[connected,setConnected]=useState(false);
  const [captions,setCaptions]=useState<Caption[]>([]),[error,setError]=useState(''),[busy,setBusy]=useState('');
  const socket=useRef<WebSocket|null>(null),clock=useRef<{offset:number;uncertainty:number}|null>(null);
  const acknowledgements=useRef(new Set<string>());
  useEffect(()=>{
    let closed=false,retry:number,engineSession:string|undefined;
    async function calibrate() {
      let best=Infinity;
      for(let i=0;i<3;i++) {
        const before=performance.now(),r=await request('/api/clock');
        if(!r.ok)return;
        const data=await r.json(),after=performance.now();
        if(after-before<best) {best=after-before;clock.current={offset:data.mono_ms-(before+after)/2,uncertainty:best/2+1};}
      }
    }
    function connect() {
      const ws=new WebSocket(API.replace('http','ws')+'/ws/events');socket.current=ws;
      ws.onopen=()=>{ws.send(JSON.stringify({type:'auth',token:sessionToken}));void calibrate().catch(()=>{clock.current=null;});};
      ws.onclose=()=>{setConnected(false);if(!closed)retry=window.setTimeout(connect,1800);};
      ws.onerror=()=>setError('Không kết nối được engine local. Mở lại dashboard từ khay LocalLingua nếu phiên đã đổi.');
      ws.onmessage=e=>{
        let data:Event;try{data=JSON.parse(e.data);}catch{return;}
        if(data.type==='status') {
          if(engineSession && engineSession!==data.session_id) {setCaptions([]);acknowledgements.current.clear();clock.current=null;void calibrate().catch(()=>{});}
          engineSession=data.session_id;setConnected(true);setStatus(data);return;
        }
        if(data.type==='history.cleared') {setCaptions([]);return;}
        if(data.type==='error') {setError(data.message);return;}
        setCaptions(old=>mergeCaption(old,data));
      };
    }
    connect();return()=>{closed=true;clearTimeout(retry);socket.current?.close();};
  },[]);
  useEffect(()=>{
    // After React commits, acknowledge on the next animation frame.
    const pending=captions.filter(c=>c.trace_id&&c.clock_calibrated&&!acknowledgements.current.has(c.trace_id));
    const frame=requestAnimationFrame(()=>{
      const ws=socket.current,calibration=clock.current;
      if(!ws||ws.readyState!==WebSocket.OPEN||!calibration)return;
      for(const caption of pending.slice(-2)) {
        ws.send(JSON.stringify({type:'render.ack',trace_id:caption.trace_id,
          render_mono_ms:performance.now()+calibration.offset,uncertainty_ms:calibration.uncertainty+16}));
        acknowledgements.current.add(caption.trace_id!);
      }
      while(acknowledgements.current.size>280) acknowledgements.current.delete(acknowledgements.current.values().next().value!);
    });
    return()=>cancelAnimationFrame(frame);
  },[captions]);
  async function action(path:string,body:unknown):Promise<boolean> {
    setBusy(path);
    try {
      const response=await request(path,body);
      if(!response.ok) {const failure=await response.json().catch(()=>({detail:String(response.status)}));throw new Error(String(failure.detail));}
      setError('');return true;
    }catch(e){setError(String(e));return false;}
    finally{setBusy('');}
  }
  return {status,connected,captions,error,busy,action,mode:(value:Mode)=>action('/api/control',{mode:value})};
}
export async function download(path:string,name:string) {
  const picker=(window as unknown as {showSaveFilePicker?:(options:{suggestedName:string})=>Promise<{createWritable:()=>Promise<{write:(blob:Blob)=>Promise<void>;close:()=>Promise<void>}>}>}).showSaveFilePicker;
  let handle:Awaited<ReturnType<NonNullable<typeof picker>>>|undefined;
  if(picker) {
    try{handle=await picker({suggestedName:name});}
    catch(e){if(e instanceof DOMException&&e.name==='AbortError')return;throw e;}
  }
  const response=await request(path);
  if(!response.ok) {const data=await response.json();throw new Error(data.detail||'Không xuất được file.');}
  if(handle){const stream=await handle.createWritable();await stream.write(await response.blob());await stream.close();return;}
  const url=URL.createObjectURL(await response.blob()),link=document.createElement('a');
  link.href=url;link.download=name;link.click();window.setTimeout(()=>URL.revokeObjectURL(url),1000);
}
