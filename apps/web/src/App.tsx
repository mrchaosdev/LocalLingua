import {useEffect,useState} from 'react';
import {Button} from '@astryxdesign/core/Button';
import {VStack} from '@astryxdesign/core/VStack';
import {HStack} from '@astryxdesign/core/HStack';
import {Text} from '@astryxdesign/core/Text';
import {Heading} from '@astryxdesign/core/Heading';
import {TextInput} from '@astryxdesign/core/TextInput';
import {Theme} from '@astryxdesign/core/theme';
import {neutralTheme} from '@astryxdesign/theme-neutral/built';
import {useLive,download} from './useLive';
import Settings from './Settings';
import {request} from './api';
export default function App() {
  const {status,connected,captions,error,busy,mode,action}=useLive();
  const [theme,setTheme]=useState<'dark'|'light'>('dark'),[large,setLarge]=useState(true);
  const [term,setTerm]=useState(''),[meaning,setMeaning]=useState(''),[filter,setFilter]=useState('');
  const [glossary,setGlossary]=useState<Record<string,string>>({}),[diagnostics,setDiagnostics]=useState(''),[localError,setLocalError]=useState('');
  const [page,setPage]=useState<'live'|'settings'|'diagnostics'>('live');
  const en=[...captions].reverse().find(x=>x.phase.startsWith('transcript'));
  const vi=[...captions].reverse().find(x=>x.phase.startsWith('translation')&&(!en||x.utterance_id===en.utterance_id));
  const finals=captions.filter(x=>x.phase==='translation.final');
  useEffect(()=>{
    const key=(e:KeyboardEvent)=>{
      if(e.ctrlKey&&e.key==='Enter'&&!(e.target instanceof HTMLInputElement)){
        e.preventDefault();if(connected)void mode(status.mode==='start'?'pause':'start');
      }
    };window.addEventListener('keydown',key);return()=>window.removeEventListener('keydown',key);
  },[connected,status.mode]);
  async function exportFile(format:'txt'|'md'|'srt'|'json') {
    try {await download(format==='json'?'/api/metrics/export':`/api/export/${format}`,`LocalLingua.${format}`);setLocalError('');}
    catch(e){setLocalError(String(e));}
  }
  async function refreshGlossary() {const r=await request('/api/glossary');if(r.ok)setGlossary(await r.json());}
  async function inspect() {
    try {const r=await request('/api/diagnostics');if(!r.ok)throw new Error(String(r.status));setDiagnostics(JSON.stringify(await r.json(),null,2));setLocalError('');}
    catch(e){setLocalError(String(e));}
  }
  const age=status.latency?.final_to_render_ms;
  return <Theme theme={neutralTheme} mode={theme}>
    <VStack as="main" padding={6} gap={6} maxWidth="70rem" minHeight="100vh">
      <HStack wrap="wrap" gap={4} justify="between" vAlign="center">
        <VStack gap={1}><Heading level={1}>LocalLingua</Heading><Text type="supporting">English → Tiếng Việt · AI trên máy</Text></VStack>
        <Button label={theme==='dark'?'Giao diện sáng':'Giao diện tối'} onClick={()=>setTheme(theme==='dark'?'light':'dark')}/>
      </HStack>
      <HStack as="nav" gap={2} wrap="wrap">
        <Button label="Phụ đề trực tiếp" onClick={()=>setPage('live')}/>
        <Button label="Nguồn và model" onClick={()=>setPage('settings')}/>
        <Button label="Chẩn đoán" onClick={()=>{setPage('diagnostics');void inspect();}}/>
      </HStack>
      <section aria-label="Trạng thái" aria-live="polite">
        <Text type="label">{connected?'● Engine kết nối':'○ Engine mất kết nối'} · {status.mode==='start'?(status.capture_connected?'Đang thu audio':'Đang chờ nguồn audio'):status.capture_connected?'Đang dừng nguồn audio':status.mode==='pause'?'Tạm dừng thu audio':'Đã dừng thu audio'}</Text>
        <Text as="p" type="supporting">{status.host_available?'AudioHost sẵn sàng':'AudioHost chưa phản hồi'} · ASR {status.asr_backend} · Dịch {status.translate_backend} · Profile {status.profile||'balanced'}</Text>
        <Text as="p" type="supporting">{status.warning}</Text>
        {status.host?.code && <Text as="p">Nguồn audio: {status.host.code}</Text>}
      </section>
      <HStack gap={2} wrap="wrap">
        <Button label="Bắt đầu" variant="primary" isDisabled={!connected||!!busy} onClick={()=>void mode('start')}/>
        <Button label="Tạm dừng" isDisabled={!connected||!!busy} onClick={()=>void mode('pause')}/>
        <Button label="Dừng" isDisabled={!connected||!!busy} onClick={()=>void mode('stop')}/>
        <Button label="Chạy demo" isDisabled={!connected||!!busy} onClick={()=>void action('/api/demo',{})}/>
      </HStack>
      {(error||localError)&&<section role="alert"><Text>{localError||error}</Text></section>}
      {page==='live' && <>
        <section aria-label="Phụ đề trực tiếp" aria-live="polite" aria-atomic="true">
          <VStack gap={3} minHeight="14rem">
            <Text type="label">{vi?.source==='demo'||vi?.source==='mock'?'MÔ PHỎNG · ':''}{vi?.is_final?'Bản dịch hoàn chỉnh':'Đang dịch · Có thể thay đổi'}</Text>
            <Text type={large?'display-3':'large'} maxLines={3}>{vi?.vietnamese||'Phụ đề tiếng Việt sẽ xuất hiện tại đây.'}</Text>
            <Text type="supporting">{en?.english||'Đang chờ lời nói tiếng Anh…'}</Text>
          </VStack>
        </section>
        <HStack gap={2} wrap="wrap">
          <Button label={large?'Chữ nhỏ hơn':'Chữ lớn hơn'} onClick={()=>setLarge(!large)}/>
          {(['txt','md','srt'] as const).map(f=><Button key={f} label={`Xuất ${f.toUpperCase()}`} isDisabled={!finals.length} onClick={()=>void exportFile(f)}/>)}
          <Button label="Xóa lịch sử trong RAM" isDisabled={status.mode!=='stop'||!!busy} onClick={()=>void action('/api/history/clear',{})}/>
        </HStack>
        <section aria-label="Chẩn đoán audio">
          <Heading level={2}>Tín hiệu và độ trễ</Heading>
          <meter aria-label="Mức âm thanh RMS" min={0} max={0.2} value={Math.min(Number(status.metrics.rms)||0,0.2)}/>
          <Text as="p" type="supporting">ASR {status.metrics.asr_ms_last??'—'} ms · Dịch {status.metrics.translation_ms_last??'—'} ms · Queue final {status.metrics.pending_finals??0} · Frame mất {status.host?.dropped??0}</Text>
          <Text as="p" type="supporting">Từ cuối lời nói đến UI (ước lượng đã hiệu chỉnh clock): P50 {age?.p50??'—'} / P95 {age?.p95??'—'} ms · {age?.count??0} mẫu trong RAM.</Text>
        </section>
        <section aria-label="Thuật ngữ">
          <VStack gap={3}>
            <Heading level={2}>Thuật ngữ trong phiên</Heading>
            <HStack gap={3} wrap="wrap">
              <TextInput label="Tiếng Anh" value={term} onChange={setTerm}/><TextInput label="Tiếng Việt" value={meaning} onChange={setMeaning}/>
              <Button label="Thêm gợi ý" isDisabled={!connected||!term.trim()||!meaning.trim()||!!busy} onClick={()=>void action('/api/glossary',{term,meaning}).then(ok=>{if(ok)void refreshGlossary();})}/>
              <Button label="Xem thuật ngữ" onClick={()=>void refreshGlossary()}/>
            </HStack>
            {Object.entries(glossary).map(([key,value])=><HStack key={key} gap={2}><Text>{key}: {value}</Text><Button label={`Xóa ${key}`} onClick={()=>void action('/api/glossary/delete',{term:key,meaning:value}).then(()=>refreshGlossary())}/></HStack>)}
          </VStack>
        </section>
        <section aria-label="Lịch sử phụ đề">
          <VStack gap={4}>
            <Heading level={2}>Phụ đề hoàn chỉnh</Heading>
            <Text type="supporting">Chỉ giữ RAM; bấm Xuất để lưu file. Có thể dịch sai số, tên riêng hoặc phủ định. Ctrl+Enter: bắt đầu / tạm dừng.</Text>
            <Text type="supporting">Server giữ {status.history_limit??70} sự kiện EN/VI gần nhất để xuất. {status.history_evictions?`${status.history_evictions} sự kiện cũ đã rời cửa sổ lưu RAM.`:''}</Text>
            <TextInput label="Tìm trong lịch sử RAM" value={filter} onChange={setFilter}/>
            {finals.filter(x=>(x.english+' '+x.vietnamese).toLocaleLowerCase().includes(filter.toLocaleLowerCase())).slice(-35).reverse().map(x=><VStack as="article" key={x.utterance_id} gap={1}>
              <Text type="supporting">{new Date(x.created_at_ms).toLocaleTimeString('vi-VN')}</Text><Text>{x.vietnamese}</Text><Text type="supporting">{x.english}</Text>
            </VStack>)}
          </VStack>
        </section>
      </>}
      {page==='settings'&&<Settings status={status} action={action} busy={busy}/>}
      {page==='diagnostics'&&<VStack gap={3}>
        <Heading level={2}>Chẩn đoán local</Heading>
        <Text type="supporting">Phiên bản dependency, GPU/VRAM, model inventory và trace thời gian. Không có audio hay nội dung lời nói trong trace export.</Text>
        <HStack gap={2}><Button label="Đọc lại chẩn đoán" onClick={()=>void inspect()}/><Button label="Xuất trace JSON" onClick={()=>void exportFile('json')}/></HStack>
        <VStack isScrollable maxWidth="100%"><pre aria-label="Chi tiết chẩn đoán">{diagnostics}</pre></VStack>
        {(status.errors||[]).map((e,i)=><Text key={i}>{new Date(e.at_ms).toLocaleTimeString('vi-VN')} · {e.component}: {e.code}</Text>)}
      </VStack>}
    </VStack>
  </Theme>;
}
