export type Mode='start'|'pause'|'stop';
export interface Preferences {
  source:'discord-process-tree'|'system-diagnostic';endpoint_id:string;discord_pid:number;
  profile:'fast'|'balanced'|'quality';asr_backend:'mock'|'whisper';translate_backend:'mock'|'ollama';
  whisper_model:string;whisper_device:'cpu'|'cuda';whisper_compute:'int8'|'int8_float16'|'float16'|'float32';
  ollama_model:string;vad_model_path:string;overlay_font_size:number;overlay_opacity:number;overlay_english:boolean;
}
export interface Caption {
  type:'caption';phase:'transcript.partial'|'transcript.final'|'translation.partial'|'translation.final';
  utterance_id:string;revision:number;is_final:boolean;english:string;vietnamese:string;created_at_ms:number;source:string;
  trace_id?:string;audio_start_ms?:number;audio_end_ms?:number;clock_calibrated?:boolean;
  utterance_order_ms?:number;
}
export interface Status {
  type:'status';session_id?:string;mode:Mode;capture_connected:boolean;asr_backend:string;translate_backend:string;
  metrics:Record<string,number|string>;warning:string;host_available?:boolean;
  host?:{state:string;code:string;dropped:number;devices:{id:string;name:string}[];processes:{pid:number;name:string}[]};
  preferences?:Preferences;preference_revision?:number;profile?:string;
  model_install?:{state:string;code:string};asr_loaded?:boolean;
  history_limit?:number;history_evictions?:number;
  latency?:Record<string,{count:number;p50:number|null;p95:number|null}>;
  errors?:{code:string;component:string;at_ms:number}[];
}
export type Event=Caption|Status|{type:'error';code:string;message:string}|{type:'history.cleared'};
