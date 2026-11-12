import {useEffect,useRef,useState} from 'react';
import {Button} from '@astryxdesign/core/Button';
import type {Caption,Event,Mode,Status} from './types';
const API='http://127.0.0.1:8765';
const WS='ws://127.0.0.1:8765/ws/events';
const initial:Status={type:'status',mode:'stop',capture_connected:false,asr_backend:'mock',translate_backend:'mock',metrics:{},warning:''};

function useLive() {
  const [status,setStatus]=useState<Status>(initial);
  const [connected,setConnected]=useState(false);
  const [captions,setCaptions]=useState<Caption[]>([]);
  const [error,setError]=useState('');
  const order=useRef(new Map<string,number>());
  useEffect(()=>{
    let socket:WebSocket|null=null,closed=false,retry:number|undefined;
    function connect(){
      socket=new WebSocket(WS);
      socket.onopen=()=>{setConnected(true);setError('');};
      socket.onclose=()=>{setConnected(false);if(!closed)retry=window.setTimeout(connect,1800);};
      socket.onerror=()=>setError('Không kết nối được AI Engine.');
      socket.onmessage=e=>{
        let data:Event;try{data=JSON.parse(e.data);}catch{return;}
        if(data.type==='status'){setStatus(data);return;}
        if(data.type==='error'){setError(`${data.code}: ${data.message}`);return;}
        // Separate latest revision by phase family (English/VI), allowing EN and VI events of same utterance.
        const key=`${data.utterance_id}:${data.phase.startsWith('translation')?'vi':'en'}`;
        const last=order.current.get(key)??-1;
        if(data.revision<last)return;
        order.current.set(key,data.revision);
        setCaptions(old=>{
          const next=old.filter(x=>!(x.utterance_id===data.utterance_id &&
             x.phase.startsWith('translation')===data.phase.startsWith('translation')));
          next.push(data);return next.slice(-70);
        });
      };
    }
    connect();return()=>{closed=true;window.clearTimeout(retry);socket?.close();};
  },[]);
  async function mode(value:Mode){
    try{const r=await fetch(`${API}/api/control`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode:value})});if(!r.ok)throw new Error(String(r.status));setStatus(await r.json());}
    catch(e){setError('Không điều khiển được engine: '+String(e));}
  }
  async function demo(){try{const r=await fetch(`${API}/api/demo`,{method:'POST'});if(!r.ok)throw new Error(String(r.status));}catch(e){setError('Demo lỗi: '+String(e));}}
  return {status,connected,captions,error,mode,demo};
}

export default function App(){
 const {status,connected,captions,error,mode,demo}=useLive();
 const en=[...captions].reverse().find(x=>x.phase.startsWith('transcript'));
 const vi=[...captions].reverse().find(x=>x.phase.startsWith('translation'));
 const recent=[...captions].filter(x=>x.phase.startsWith('translation')&&x.is_final).reverse().slice(0,8);
 const isDemo=vi?.source==='demo';
 return <div className="shell">
    <aside className="sidebar">
      <div className="brand"><span className="brandmark">◉</span><div><b>LocalLingua</b><small>Live Subtitle AI</small></div></div>
      <div className="navgroup">WORKSPACE</div>
      <div className="navitem selected">◉ &nbsp; Live translation</div>
      <div className="navitem muted">▤ &nbsp; History (P1)</div>
      <div className="navitem muted">◈ &nbsp; Glossary (P1)</div>
      <div className="navitem muted">⚙ &nbsp; Settings (P1)</div>
      <div className="sidefoot">Local-first · EN → VI<br/><span>Không có cloud inference</span></div>
    </aside>
    <main className="main">
      <header className="topbar"><div><h1>Live translation</h1><p>Nghe tiếng Anh. Đọc phụ đề tiếng Việt.</p></div><span className={`pill ${connected?'online':'offline'}`}>{connected?'● Engine connected':'○ Engine offline'}</span></header>
      <section className="summary">
        <div><span className="eyebrow">AUDIO SOURCE</span><b>System loopback <em>diagnostic</em></b><small>Discord-only capture: Milestone M2</small></div>
        <div><span className="eyebrow">ENGLISH ASR</span><b>{status.asr_backend}</b><small>{status.capture_connected?'Audio host connected':'Audio host not connected'}</small></div>
        <div><span className="eyebrow">VIETNAMESE ENGINE</span><b>{status.translate_backend}</b><small>Không lưu transcript mặc định</small></div>
      </section>
      <section className="livepanel">
        <div className="livehead"><span><i className="dot"/> CURRENT SUBTITLE</span><small>{vi?.is_final?'Final':vi?'Đang dịch / tentative':'Chưa có lời nói'}</small></div>
        <div className="caption-view">
          <div className="label">BẢN DỊCH TIẾNG VIỆT {isDemo&&<span className="demo-label">DEMO</span>}</div>
          <div className={`vi-text ${!vi?'empty':''}`}>{vi?.vietnamese||'Bản dịch trực tiếp sẽ xuất hiện ở đây khi có tiếng nói tiếng Anh.'}</div>
          <div className="divider"/>
          <div className="label">ORIGINAL ENGLISH</div>
          <div className="en-text">{en?.english||vi?.english||'Waiting for English audio…'}</div>
        </div>
        <div className="transport">
          <span className={`stream-status ${status.mode==='start'?'active':''}`}>● {status.mode==='start'?'Listening':status.mode==='pause'?'Paused':'Stopped'}</span>
          <div className="buttonrow">
            <Button label="▶ Start" variant="primary" onClick={()=>mode('start')}/>
            <Button label="Pause" variant="secondary" onClick={()=>mode('pause')}/>
            <Button label="Stop" variant="secondary" onClick={()=>mode('stop')}/>
            <Button label="▶ Demo" variant="secondary" onClick={demo}/>
          </div>
        </div>
      </section>
      {error&&<div className="error" role="alert">{error}</div>}
      <section className="history"><h2>Latest finalized translations</h2><span className="helper">Chỉ giữ RAM · {recent.length} sự kiện gần nhất</span>
        {recent.length?recent.map(item=><article key={item.utterance_id} className="line"><span className="time">{new Date(item.created_at_ms).toLocaleTimeString('vi-VN')}</span><div><strong>{item.vietnamese}</strong><p>{item.english}</p></div></article>):<p className="placeholder">Chưa có bản dịch hoàn chỉnh. Bấm Demo để xem giao diện với dữ liệu mô phỏng.</p>}
      </section>
    </main>
    <aside className="inspector"><div className="ins-title">SYSTEM MONITOR</div><div className="mini"><span>Capture</span><b>{status.capture_connected?'Connected':'Offline'}</b></div><div className="mini"><span>Engine</span><b>{connected?'Ready':'Disconnected'}</b></div>
      <div className="mini"><span>ASR last</span><b>{status.metrics?.asr_ms_last??'—'} ms</b></div><div className="mini"><span>Translation last</span><b>{status.metrics?.translation_ms_last??'—'} ms</b></div><div className="mini"><span>Captured frames</span><b>{status.metrics?.frames??0}</b></div>
      <div className="info">⚠ Chế độ capture hiện tại lấy toàn bộ âm thanh thiết bị. Không coi là nguồn Discord riêng cho đến khi M2 được triển khai.</div>
      <small className="insfoot">Đây là ứng dụng scaffold. Không khẳng định đã chạy inference thật nếu backend = mock.</small>
    </aside>
  </div>;
}
