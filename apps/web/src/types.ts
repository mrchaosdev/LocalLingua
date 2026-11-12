export type Mode = 'start'|'pause'|'stop';
export interface Caption {
  type:'caption'; phase:'transcript.partial'|'transcript.final'|'translation.partial'|'translation.final';
  utterance_id:string; revision:number; is_final:boolean; english:string; vietnamese:string;
  created_at_ms:number; source:string;
}
export interface Status {type:'status';session_id?:string;mode:Mode;capture_connected:boolean;asr_backend:string;translate_backend:string;metrics:Record<string,number>;warning:string;}
export type Event=Caption|Status|{type:'error';code:string;message:string};
