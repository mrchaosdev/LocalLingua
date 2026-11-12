import {useEffect, useState} from 'react';
import {Button} from '@astryxdesign/core/Button';
import {VStack} from '@astryxdesign/core/VStack';
import {HStack} from '@astryxdesign/core/HStack';
import {Text} from '@astryxdesign/core/Text';
import {Heading} from '@astryxdesign/core/Heading';
import {TextInput} from '@astryxdesign/core/TextInput';
import {Theme} from '@astryxdesign/core/theme';
import {neutralTheme} from '@astryxdesign/theme-neutral/built';
import {mergeCaption} from './captions';
import {API, request, sessionToken} from './api';
import type {Caption, Event, Mode, Status} from './types';
const initial: Status = {type:'status',mode:'stop',capture_connected:false,asr_backend:'mock',translate_backend:'mock',metrics:{},warning:''};

function useLive() {
  const [status,setStatus] = useState(initial);
  const [connected,setConnected] = useState(false);
  const [captions,setCaptions] = useState<Caption[]>([]);
  const [error,setError] = useState('');
  useEffect(() => {
    let socket: WebSocket, closed = false, retry: number;
    function connect() {
      socket = new WebSocket(API.replace('http','ws') + '/ws/events');
      socket.onopen = () => socket.send(JSON.stringify({type:'auth',token:sessionToken}));
      socket.onclose = () => {setConnected(false); if (!closed) retry = window.setTimeout(connect,1800);};
      socket.onerror = () => setError('Không kết nối được engine local.');
      socket.onmessage = e => {
        let data: Event;
        try {data = JSON.parse(e.data);} catch {return;}
        if (data.type === 'status') {setConnected(true); setStatus(data); return;}
        if (data.type === 'error') {setError(data.message); return;}
        setCaptions(old => mergeCaption(old,data));
      };
    }
    connect();
    return () => {closed = true; clearTimeout(retry); socket?.close();};
  },[]);
  async function action(path: string, body: unknown) {
    try {
      const response = await request(path,body);
      if (!response.ok) throw new Error(String(response.status));
      setError('');
    } catch (e) {setError('Thao tác thất bại: ' + String(e));}
  }
  const mode = (value: Mode) => action('/api/control',{mode:value});
  return {status,connected,captions,error,mode,action};
}

export default function App() {
  const {status,connected,captions,error,mode,action} = useLive();
  const [theme,setTheme] = useState<'dark'|'light'>('dark');
  const [large,setLarge] = useState(true);
  const [term,setTerm] = useState('');
  const [meaning,setMeaning] = useState('');
  const vi = [...captions].reverse().find(x=>x.phase.startsWith('translation'));
  const en = [...captions].reverse().find(x=>x.phase.startsWith('transcript'));
  const finals = captions.filter(x=>x.phase==='translation.final');
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key==='Enter' && !(e.target instanceof HTMLInputElement)) {
        e.preventDefault(); if (connected) void mode(status.mode==='start'?'pause':'start');
      }
    };
    window.addEventListener('keydown',key);
    return () => window.removeEventListener('keydown',key);
  },[connected,status.mode]);
  function exportText() {
    const text = finals.map(x=>`${new Date(x.created_at_ms).toLocaleTimeString('vi-VN')}\n${x.english}\n${x.vietnamese}`).join('\n\n');
    const url = URL.createObjectURL(new Blob([text],{type:'text/plain;charset=utf-8'}));
    const link = document.createElement('a'); link.href=url; link.download='LocalLingua.txt'; link.click();
    window.setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  return <Theme theme={neutralTheme} mode={theme}>
    <VStack as="main" padding={6} gap={6} maxWidth="70rem" minHeight="100vh">
      <HStack wrap="wrap" gap={4} justify="between" vAlign="center">
        <VStack gap={1}><Heading level={1}>LocalLingua</Heading><Text type="supporting">Nghe tiếng Anh · Đọc phụ đề tiếng Việt · AI local</Text></VStack>
        <Button label={theme==='dark'?'Giao diện sáng':'Giao diện tối'} onClick={()=>setTheme(theme==='dark'?'light':'dark')}/>
      </HStack>
      <section aria-label="Trạng thái" aria-live="polite">
        <Text type="label">{connected?'● Đã kết nối engine':'○ Mất kết nối engine'}</Text>
        <Text as="p" type="supporting">{status.capture_connected?'Đã kết nối nguồn audio':'Chưa có nguồn audio'} · ASR: {status.asr_backend} · Dịch: {status.translate_backend}</Text>
        <Text as="p" type="supporting">{status.warning}</Text>
      </section>
      <section aria-label="Phụ đề trực tiếp" aria-live="polite" aria-atomic="true">
        <VStack gap={3} minHeight="14rem">
          <Text type="label">{vi?.source==='demo'?'DỮ LIỆU MÔ PHỎNG · ':''}{vi?.is_final?'Bản dịch hoàn chỉnh':'Đang dịch · Có thể thay đổi'}</Text>
          <Text type={large?'display-3':'large'} maxLines={3}>{vi?.vietnamese || 'Phụ đề tiếng Việt sẽ xuất hiện tại đây.'}</Text>
          <Text type="supporting">{en?.english || 'Đang chờ lời nói tiếng Anh…'}</Text>
        </VStack>
      </section>
      <HStack gap={2} wrap="wrap">
        <Button label="Bắt đầu" variant="primary" isDisabled={!connected || !status.capture_connected} onClick={()=>void mode('start')}/>
        <Button label="Tạm dừng" isDisabled={!connected} onClick={()=>void mode('pause')}/>
        <Button label="Dừng" isDisabled={!connected} onClick={()=>void mode('stop')}/>
        <Button label="Chạy demo" isDisabled={!connected} onClick={()=>void action('/api/demo',{})}/>
        <Button label={large?'Chữ nhỏ hơn':'Chữ lớn hơn'} onClick={()=>setLarge(!large)}/>
        <Button label="Xuất phụ đề TXT" isDisabled={!finals.length} onClick={exportText}/>
      </HStack>
      {error && <section role="alert"><Text>{error}</Text></section>}
      <section aria-label="Chẩn đoán audio">
        <Heading level={2}>Tín hiệu và xử lý</Heading>
        <meter aria-label="Mức âm thanh RMS" min={0} max={0.2} value={Math.min(status.metrics.rms||0,0.2)}/>
        <Text as="p" type="supporting">RMS {status.metrics.rms??0} · ASR {status.metrics.asr_ms_last??'—'} ms · Dịch {status.metrics.translation_ms_last??'—'} ms · Frame mất {status.metrics.dropped_samples??0} samples</Text>
        <Text as="p" type="supporting">P50/P95 dịch: {status.metrics.translation_ms_p50??'—'} / {status.metrics.translation_ms_p95??'—'} ms (thời gian xử lý; chưa phải độ trễ đầu cuối)</Text>
      </section>
      <section aria-label="Thuật ngữ">
        <VStack gap={3}>
          <Heading level={2}>Thuật ngữ trong phiên</Heading>
          <HStack gap={3} wrap="wrap">
            <TextInput label="Tiếng Anh" value={term} onChange={setTerm}/>
            <TextInput label="Tiếng Việt" value={meaning} onChange={setMeaning}/>
            <Button label="Thêm gợi ý dịch" isDisabled={!connected || !term.trim() || !meaning.trim()} onClick={()=>void action('/api/glossary',{term,meaning})}/>
          </HStack>
          <Text type="supporting">Gợi ý cho model, chỉ giữ RAM. Ctrl+Enter: bắt đầu / tạm dừng.</Text>
        </VStack>
      </section>
      <section aria-label="Lịch sử phụ đề">
        <VStack gap={4}>
          <Heading level={2}>Phụ đề hoàn chỉnh gần đây</Heading>
          <Text type="supporting">Chỉ giữ RAM; xuất file khi bạn bấm nút. Có thể dịch sai số, tên riêng hoặc phủ định.</Text>
          {finals.slice(-12).reverse().map(x=><VStack as="article" key={x.utterance_id} gap={1}>
            <Text type="supporting">{new Date(x.created_at_ms).toLocaleTimeString('vi-VN')}</Text>
            <Text>{x.vietnamese}</Text><Text type="supporting">{x.english}</Text>
          </VStack>)}
        </VStack>
      </section>
    </VStack>
  </Theme>;
}
