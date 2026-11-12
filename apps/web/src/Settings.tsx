import {useEffect,useState} from 'react';
import {Button} from '@astryxdesign/core/Button';
import {Selector} from '@astryxdesign/core/Selector';
import {TextInput} from '@astryxdesign/core/TextInput';
import {Text} from '@astryxdesign/core/Text';
import {Heading} from '@astryxdesign/core/Heading';
import {VStack} from '@astryxdesign/core/VStack';
import {HStack} from '@astryxdesign/core/HStack';
import type {Preferences,Status} from './types';
export default function Settings({status,action,busy}:{status:Status;action:(path:string,body:unknown)=>Promise<boolean>;busy:string}) {
  const [draft,setDraft]=useState<Preferences|null>(null);
  useEffect(()=>{if(status.preferences)setDraft(status.preferences);},[status.preference_revision]);
  if(!draft)return <Text>Đang đọc cấu hình…</Text>;
  function field<K extends keyof Preferences>(key:K,value:Preferences[K]) {setDraft(old=>old?{...old,[key]:value}:old);}
  const stopped=status.mode==='stop';
  return <VStack gap={4}>
    <Heading level={2}>Nguồn audio và AI local</Heading>
    <Text type="supporting">Dừng phiên trước khi đổi nguồn hoặc model. Cấu hình lưu trên máy; nội dung cuộc nói chuyện chỉ giữ RAM.</Text>
    <HStack gap={2} wrap="wrap">
      <Button label="Discord process tree" variant={draft.source==='discord-process-tree'?'primary':'secondary'} onClick={()=>field('source','discord-process-tree')}/>
      <Button label="Toàn hệ thống · Chẩn đoán" variant={draft.source==='system-diagnostic'?'primary':'secondary'} onClick={()=>field('source','system-diagnostic')}/>
    </HStack>
    {draft.source==='system-diagnostic' && <Text>Chế độ này thu âm thanh của tất cả ứng dụng trên thiết bị đã chọn.</Text>}
    <HStack gap={3} wrap="wrap">
      <Selector label="Profile" value={draft.profile} options={[{value:'fast',label:'Nhanh'},{value:'balanced',label:'Cân bằng'},{value:'quality',label:'Chất lượng'}]} onChange={v=>field('profile',v as Preferences['profile'])}/>
      {draft.source==='system-diagnostic'?<Selector label="Thiết bị output" value={draft.endpoint_id} options={[{value:'',label:'Theo thiết bị mặc định'},...(status.host?.devices||[]).map(d=>({value:d.id,label:d.name}))]} onChange={v=>field('endpoint_id',v)}/>:
        <Selector label="Discord" value={String(draft.discord_pid)} options={[{value:'0',label:'Tự tìm process gốc'},...(status.host?.processes||[]).map(p=>({value:String(p.pid),label:`${p.name} · PID ${p.pid}`}))]} onChange={v=>field('discord_pid',Number(v))}/>}
    </HStack>
    <Text type="supporting">Các profile thay đổi lịch ASR, beam và giới hạn câu. Chưa có benchmark xác nhận profile nào đạt mục tiêu latency.</Text>
    <HStack gap={2} wrap="wrap">
      <Button label="Dùng AI local" onClick={()=>setDraft({...draft,asr_backend:'whisper',translate_backend:'ollama',whisper_device:'cuda',whisper_compute:'int8_float16'})}/>
      <Button label="Dùng mô phỏng" onClick={()=>setDraft({...draft,asr_backend:'mock',translate_backend:'mock'})}/>
    </HStack>
    <Text>ASR: {draft.asr_backend} · Dịch: {draft.translate_backend}</Text>
    <TextInput label="Thư mục Whisper local" value={draft.whisper_model} onChange={v=>field('whisper_model',v)}/>
    <TextInput label="File Silero VAD ONNX local" value={draft.vad_model_path} onChange={v=>field('vad_model_path',v)} description="Để trống dùng energy gate chẩn đoán; Silero dùng model local khi đã tải."/>
    <TextInput label="Tên model trong Ollama" value={draft.ollama_model} onChange={v=>field('ollama_model',v)}/>
    <HStack gap={3} wrap="wrap">
      <Selector label="Thiết bị ASR" value={draft.whisper_device} options={['cuda','cpu']} onChange={v=>field('whisper_device',v as Preferences['whisper_device'])}/>
      <Selector label="Kiểu tính toán" value={draft.whisper_compute} options={['int8_float16','float16','int8','float32']} onChange={v=>field('whisper_compute',v as Preferences['whisper_compute'])}/>
      <Button label="Lưu cấu hình" isDisabled={!stopped||!!busy} onClick={()=>void action('/api/preferences',draft)}/>
      <Button label="Nạp model local" isDisabled={!stopped||!!busy} onClick={()=>void action('/api/models/load',{})}/>
    </HStack>
    <Heading level={3}>Cài model lần đầu</Heading>
    <Text type="supporting">Tải Whisper small.en, Qwen3 4B Q4_K_M và Silero từ nguồn chính thức. Cần internet, vài GB trống và Ollama đã cài. Revision, SHA256 và license được lưu trong model inventory.</Text>
    <Button label="Tải và cài model chính thức" isDisabled={!stopped||status.model_install?.state==='running'||!!busy} onClick={()=>void action('/api/models/install',{})}/>
    <Text type="supporting">{status.model_install?.state} · {status.model_install?.code} {status.model_install?.state==='complete'?'— Thoát và mở lại LocalLingua để áp dụng.':''}</Text>
    <Heading level={3}>Overlay</Heading>
    <HStack gap={2} wrap="wrap">
      <Button label={`Chữ nhỏ (${draft.overlay_font_size})`} onClick={()=>field('overlay_font_size',Math.max(16,draft.overlay_font_size-2))}/>
      <Button label="Chữ lớn" onClick={()=>field('overlay_font_size',Math.min(48,draft.overlay_font_size+2))}/>
      <Button label={`Độ mờ ${Math.round(draft.overlay_opacity*100)}%`} onClick={()=>field('overlay_opacity',draft.overlay_opacity<=0.45?1:Math.max(0.35,draft.overlay_opacity-0.1))}/>
      <Button label={draft.overlay_english?'Ẩn tiếng Anh':'Hiện tiếng Anh'} onClick={()=>field('overlay_english',!draft.overlay_english)}/>
      <Button label="Áp dụng overlay" isDisabled={!!busy} onClick={()=>void action('/api/preferences',{...status.preferences,overlay_font_size:draft.overlay_font_size,overlay_opacity:draft.overlay_opacity,overlay_english:draft.overlay_english})}/>
    </HStack>
  </VStack>;
}
