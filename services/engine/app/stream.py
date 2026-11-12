from __future__ import annotations
import asyncio
import time
import uuid
import os
from collections import deque, OrderedDict
from dataclasses import dataclass
import numpy as np
from .audio import rms
from .events import caption
from .stability import stable_prefix
from .runtime import PROFILES

@dataclass
class Job:
    uid: str
    revision: int
    final: bool
    samples: np.ndarray | None = None
    english: str = ''
    context: tuple = ()
    endpoint: float = 0
    generation: int = 0
    start_ms: float = 0
    end_ms: float = 0
    ingest_ms: float = 0
    uncertainty_ms: float = 1000
    calibrated: bool = False
    asr_request_ms: float = 0
    asr_result_ms: float = 0
    capture_end_ms: float = 0

class SpeechSession:
    """Bounded audio and final FIFOs; one cancellable tentative translation; final results drain on pause."""
    def __init__(self, hub, transcriber, translator, status, rms_threshold=0.006, preferences=None, telemetry=None):
        self.hub,self.asr,self.translator,self.status=hub,transcriber,translator,status
        self.telemetry=telemetry
        self.threshold=rms_threshold
        self.profile=PROFILES[getattr(preferences,'profile','balanced')]
        from .vad import SileroVad
        path=getattr(preferences,'vad_model_path',os.getenv('VAD_MODEL_PATH',''))
        self.vad=SileroVad(path) if path else None
        self.block_size=512 if self.vad else 320
        if hasattr(self.asr,'beam_size'): self.asr.beam_size=self.profile['beam_size']
        if self.translator: self.translator.output_tokens=self.profile['output_tokens']
        self.last_received=time.monotonic()
        self.audio=deque(); self.audio_count=0
        self.pending=np.zeros(0,np.float32)
        self.pending_end_ms=0
        self.epoch_ms=telemetry.origin_ms if telemetry else None
        self.ingest_ms=0; self.uncertainty_ms=1000; self.calibrated=False; self.capture_end_ms=0
        self.asr_finals=asyncio.Queue(maxsize=8); self.vi_finals=asyncio.Queue(maxsize=8)
        self.asr_partial=self.vi_partial=None
        self.asr_wake,self.vi_wake=asyncio.Event(),asyncio.Event()
        self.tasks=[]; self.closed=False; self.generation=0
        self.context=deque(maxlen=2); self.latest=OrderedDict(); self.hypotheses=OrderedDict()
        self.last_partial_sent=0; self.partial_task=None; self.asr_busy=False; self.vi_busy=False
        self.closed_utterances=OrderedDict()
        self.timings={k:deque(maxlen=2000) for k in ('asr_ms','translation_ms','final_age_ms')}
        self.metrics=dict(frames=0,dropped_samples=0,asr_calls=0,translate_calls=0,
                          asr_ms_last=0,translation_ms_last=0,rms=0,final_overflows=0,
                          vad_backend='silero' if self.vad else 'energy-diagnostic',pipeline='idle')
        self._new_utterance()

    @property
    def pending_finals(self):
        return self.asr_finals.qsize()+self.vi_finals.qsize()+int(self.asr_busy)+int(self.vi_busy)

    @property
    def failed(self):
        return any(task.done() and not task.cancelled() and task.exception() is not None for task in self.tasks)

    def _new_utterance(self):
        self.uid=str(uuid.uuid4()); self.segment=[]
        self.segment_size=self.onset=self.silence=0
        self.active=False; self.last_snapshot=0; self.revision=0
        self.voiced_samples=0
        self.segment_clock_good=True;self.segment_uncertainty_ms=0
        self.segment_start_ms=0; self.last_voiced_end_ms=0

    def ingest(self, chunk, capture_end_ms=None, uncertainty_ms=1000, calibrated=False):
        if not chunk.size or self.status.mode!='start': return
        self.last_received=time.monotonic(); self.metrics['frames']+=1
        end=capture_end_ms if capture_end_ms is not None else time.perf_counter()*1000
        if self.epoch_ms is None: self.epoch_ms=end-chunk.size/16
        lost=chunk.size>12800
        if lost:
            self.metrics['dropped_samples']+=chunk.size-12800; chunk=chunk[-12800:]
        while self.audio and self.audio_count+chunk.size>12800:
            previous=self.audio.popleft(); self.audio_count-=previous[0].size
            self.metrics['dropped_samples']+=previous[0].size; lost=True
        if lost: self.discontinuity('audio_gap')
        self.audio.append((chunk.copy(),end,time.perf_counter()*1000,uncertainty_ms,calibrated))
        self.audio_count+=chunk.size

    async def start(self):
        self.tasks=[asyncio.create_task(self._audio_worker()),asyncio.create_task(self._asr_worker()),asyncio.create_task(self._translation_worker())]
        for task in self.tasks: task.add_done_callback(self._worker_done)

    def _worker_done(self, task):
        if not task.cancelled() and task.exception() is not None:
            self.status.mode='pause'; self._error('worker_failed')

    async def close(self):
        try: self.pause()
        except Exception: self._error('audio_finalize_failed')
        # Config changes are rejected while finals are pending. Shutdown may cancel explicitly.
        self.closed=True
        if self.pending_finals: self._error('shutdown_pending_finals')
        for task in self.tasks: task.cancel()
        await asyncio.gather(*self.tasks,return_exceptions=True)

    def _error(self, code):
        if self.telemetry: self.telemetry.error(code)
        self.metrics['pipeline']='degraded'
        self.hub.publish(dict(type='error',code=code,message='Pipeline: '+code))

    def _put_final(self, queue, job):
        try: queue.put_nowait(job)
        except asyncio.QueueFull:
            self.metrics['final_overflows']+=1; self.status.mode='pause'
            self._error('final_queue_overflow_speech_not_translated')

    def _job(self, final, end):
        self.revision+=1
        return Job(self.uid,self.revision,final,np.concatenate(self.segment),endpoint=end/1000,
                   generation=self.generation,start_ms=self.segment_start_ms,end_ms=end,
                   ingest_ms=self.ingest_ms,uncertainty_ms=max(self.uncertainty_ms,self.segment_uncertainty_ms),
                   calibrated=self.calibrated and self.segment_clock_good,
                   capture_end_ms=self.capture_end_ms)

    def _finish(self):
        self.closed_utterances[self.uid]=True
        while len(self.closed_utterances)>140: self.closed_utterances.popitem(last=False)
        if self.active and self.voiced_samples>=5600:
            self._put_final(self.asr_finals,self._job(True,self.last_voiced_end_ms))
            self.asr_wake.set()
        self.asr_partial=None; self.vi_partial=None
        if self.partial_task: self.partial_task.cancel()
        self._new_utterance()

    def pause(self):
        while self.audio:
            self._consume(self.audio.popleft())
        self._finish()
        self.audio.clear(); self.audio_count=0; self.pending=np.zeros(0,np.float32)
        if self.vad: self.vad.reset()
        self.metrics['rms']=0

    def _consume(self,item):
        chunk,end,self.ingest_ms,self.uncertainty_ms,self.calibrated=item
        self.capture_end_ms=end
        self.audio_count-=chunk.size
        self.pending=np.concatenate((self.pending,chunk));self.pending_end_ms=end
        while self.pending.size>=self.block_size:
            block,self.pending=self.pending[:self.block_size],self.pending[self.block_size:]
            self._block(block,end-self.pending.size/16)

    def discontinuity(self,code):
        self._finish(); self.pending=np.zeros(0,np.float32)
        if self.vad: self.vad.reset()
        self._error(code)

    async def _audio_worker(self):
        while True:
            await asyncio.sleep(0.02)
            if self.status.mode=='start':
                while self.audio:
                    if self.status.mode!='start':
                        self.audio.clear();self.audio_count=0;break
                    self._consume(self.audio.popleft())
                if self.active and time.monotonic()-self.last_received>0.72: self._finish()
            self.metrics.update(audio_backlog_ms=self.audio_count/16,asr_queue=self.asr_finals.qsize(),
                                translation_queue=self.vi_finals.qsize(),pending_finals=self.pending_finals)

    def _block(self,block,end):
        level=rms(block); self.metrics['rms']=round(level,5)
        voiced=self.vad.probability(block)>=(0.35 if self.active else 0.5) if self.vad else level>self.threshold
        if voiced:
            self.voiced_samples+=block.size
            self.segment_clock_good=self.segment_clock_good and self.calibrated
            self.segment_uncertainty_ms=max(self.segment_uncertainty_ms,self.uncertainty_ms)
        elif not self.active:self.voiced_samples=0
        if not self.active:
            self.onset=self.onset+block.size if voiced else 0
            self.segment.append(block); self.segment_size+=block.size
            while self.segment_size>4800: self.segment_size-=self.segment.pop(0).size
            self.segment_start_ms=end-self.segment_size/16
            if self.onset<1920: return
            self.active=True
        else:
            self.segment.append(block); self.segment_size+=block.size
        if voiced: self.last_voiced_end_ms=end
        self.silence=0 if voiced else self.silence+block.size
        if self.silence>=10400 or self.segment_size>=16000*self.profile['max_segment_s']:
            self._finish()
        elif self.segment_size-self.last_snapshot>=16000*self.profile['asr_interval']:
            self.asr_partial=self._job(False,self.last_voiced_end_ms)
            self.last_snapshot=self.segment_size; self.asr_wake.set()

    async def _asr_worker(self):
        while True:
            await self.asr_wake.wait(); self.asr_wake.clear()
            while not self.asr_finals.empty() or self.asr_partial:
                job=self.asr_finals.get_nowait() if not self.asr_finals.empty() else self.asr_partial
                if job is self.asr_partial: self.asr_partial=None
                if job.generation!=self.generation: continue
                self.asr_busy=job.final; self.metrics['pipeline']='transcribing'
                job.asr_request_ms=time.perf_counter()*1000
                try: en=(await self.asr.transcribe(job.samples)).strip()
                except Exception as exc:
                    self._error('gpu_out_of_memory' if 'out of memory' in str(exc).lower() else 'asr_failure')
                    self.status.mode='pause'
                    self.hypotheses.pop(job.uid,None); self.latest.pop(job.uid,None)
                    continue
                finally: self.asr_busy=False
                job.asr_result_ms=time.perf_counter()*1000
                if job.generation!=self.generation or not en:
                    if job.final: self.hypotheses.pop(job.uid,None); self.latest.pop(job.uid,None)
                    continue
                if not job.final and job.uid in self.closed_utterances: continue
                self._timing('asr_ms',job.asr_result_ms-job.asr_request_ms)
                self.metrics['asr_ms_last']=round(job.asr_result_ms-job.asr_request_ms); self.metrics['asr_calls']+=1
                self.latest[job.uid]=job.revision
                while len(self.latest)>140: self.latest.popitem(last=False)
                self._publish(job,en,'','transcript')
                stable=stable_prefix(self.hypotheses.get(job.uid,''),en)
                self.hypotheses[job.uid]=en
                while len(self.hypotheses)>140: self.hypotheses.popitem(last=False)
                job.english=en if job.final else stable
                job.samples=None; job.context=tuple(self.context)
                if job.final:
                    self.hypotheses.pop(job.uid,None); self.context.append(en)
                    self.vi_partial=None
                    if self.partial_task: self.partial_task.cancel()
                    self._put_final(self.vi_finals,job); self.vi_wake.set()
                elif len(stable.split())>=5 and time.monotonic()-self.last_partial_sent>=self.profile['partial_interval']:
                    self.last_partial_sent=time.monotonic()
                    self.vi_partial=job
                    if self.partial_task: self.partial_task.cancel()
                    self.vi_wake.set()

    async def _translation_worker(self):
        while True:
            await self.vi_wake.wait(); self.vi_wake.clear()
            while not self.vi_finals.empty() or self.vi_partial:
                job=self.vi_finals.get_nowait() if not self.vi_finals.empty() else self.vi_partial
                if job is self.vi_partial: self.vi_partial=None
                if job.generation!=self.generation: continue
                self.vi_busy=job.final; self.metrics['pipeline']='translating'
                started=time.perf_counter()*1000
                inference=asyncio.create_task(self.translator.translate(job.english,list(job.context)))
                if not job.final: self.partial_task=inference
                try: vi=await asyncio.wait_for(inference,25)
                except asyncio.CancelledError:
                    if asyncio.current_task().cancelling(): raise
                    continue
                except Exception:
                    self._error('final_translation_failure' if job.final else 'partial_translation_failure')
                    if job.final: self.latest.pop(job.uid,None)
                    continue
                finally:
                    self.vi_busy=False
                    if self.partial_task is inference: self.partial_task=None
                if job.generation!=self.generation: continue
                if not job.final and (self.latest.get(job.uid)!=job.revision or job.uid in self.closed_utterances): continue
                elapsed=time.perf_counter()*1000-started
                self._timing('translation_ms',elapsed); self.metrics['translation_ms_last']=round(elapsed)
                self.metrics['translate_calls']+=1
                self._publish(job,job.english,vi,'translation',started)
                if job.final:
                    self._timing('final_age_ms',time.perf_counter()*1000-job.end_ms)
                    self.latest.pop(job.uid,None)
                self.metrics['pipeline']='listening' if self.status.mode=='start' else 'idle'

    def _publish(self,job,en,vi,family,translate_request_ms=None):
        phase=family+('.final' if job.final else '.partial')
        source=self.asr.settings.asr_backend if family=='transcript' else self.translator.settings.translate_backend
        event=caption(phase,job.uid,job.revision,en,vi,source=source)
        event.update(trace_id=f'{job.uid}:{phase}:{job.revision}',audio_start_ms=job.start_ms-(self.epoch_ms or 0),
                     audio_end_ms=job.end_ms-(self.epoch_ms or 0),speech_end_mono_ms=job.end_ms,
                     emitted_mono_ms=time.perf_counter()*1000,clock_uncertainty_ms=job.uncertainty_ms,
                     clock_calibrated=job.calibrated)
        if self.telemetry and job.calibrated:
            self.telemetry.record(dict(trace_id=event['trace_id'],is_final=job.final,phase=phase,
                utterance_id=job.uid,speech_start_mono_ms=job.start_ms,
                capture_end_mono_ms=job.capture_end_ms,ingest_mono_ms=job.ingest_ms,speech_end_mono_ms=job.end_ms,
                asr_request_ms=job.asr_request_ms,asr_result_ms=job.asr_result_ms,translate_request_ms=translate_request_ms,
                emitted_mono_ms=event['emitted_mono_ms'],uncertainty_ms=job.uncertainty_ms))
        self.hub.publish(event)

    def _timing(self,name,value):
        self.timings[name].append(value); values=np.array(self.timings[name])
        self.metrics[name+'_p50']=round(float(np.percentile(values,50)))
        self.metrics[name+'_p95']=round(float(np.percentile(values,95)))
        self.metrics[name+'_count']=len(values)

    def reset(self):
        # Explicit destructive reset for model/session replacement only.
        self.pause(); self.generation+=1
        for q in (self.asr_finals,self.vi_finals):
            while not q.empty(): q.get_nowait()
        self.latest.clear(); self.hypotheses.clear(); self.context.clear()
