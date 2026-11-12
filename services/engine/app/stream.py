from __future__ import annotations
import asyncio
import time
import uuid
import os
from collections import deque
from dataclasses import dataclass
import numpy as np
from .audio import rms
from .events import caption
from .stability import stable_prefix

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

class SpeechSession:
    """Independent bounded capture, ASR and translation workers; no inference in ingest."""
    def __init__(self, hub, transcriber, translator, status, rms_threshold=0.006):
        self.hub, self.asr, self.translator, self.status = hub, transcriber, translator, status
        self.threshold = rms_threshold
        from .vad import SileroVad
        vad_path = os.getenv('VAD_MODEL_PATH', '')
        self.vad = SileroVad(vad_path) if vad_path else None
        self.block_size = 512 if self.vad else 320
        self.last_received = time.monotonic()
        self.audio = deque()
        self.audio_count = 0
        self.asr_finals = asyncio.Queue(maxsize=8)
        self.vi_finals = asyncio.Queue(maxsize=8)
        self.asr_partial = self.vi_partial = None
        self.asr_wake, self.vi_wake = asyncio.Event(), asyncio.Event()
        self.tasks = []
        self.closed = False
        self.generation = 0
        self.context = deque(maxlen=2)
        from collections import OrderedDict
        self.latest = OrderedDict()
        self.hypotheses = OrderedDict()
        self.last_partial_sent = 0
        self.timings = {name: deque(maxlen=2000) for name in ('asr_ms', 'translation_ms', 'final_age_ms')}
        self.metrics = dict(frames=0, dropped_samples=0, asr_calls=0, translate_calls=0,
                            asr_ms_last=0, translation_ms_last=0, rms=0, final_overflows=0)
        self._new_utterance()

    def _new_utterance(self):
        self.uid = str(uuid.uuid4())
        self.segment = []
        self.segment_size = self.onset = self.silence = 0
        self.active = False
        self.preroll = np.zeros(0, np.float32)
        self.last_snapshot = 0
        self.revision = 0

    def ingest(self, chunk):
        if not chunk.size or self.status.mode != 'start': return
        self.last_received = time.monotonic()
        self.metrics['frames'] += 1
        # Cap raw work at 800ms. Any loss invalidates the current tentative utterance.
        if chunk.size > 12800:
            self.metrics['dropped_samples'] += chunk.size - 12800
            chunk = chunk[-12800:]
        lost = False
        while self.audio and self.audio_count + chunk.size > 12800:
            lost = True
            self.metrics['dropped_samples'] += self.audio[0].size
            self.audio_count -= self.audio.popleft().size
        if lost:
            self._error('audio_gap')
            self._new_utterance()
        self.audio.append(chunk.copy())
        self.audio_count += chunk.size

    async def start(self):
        self.tasks = [asyncio.create_task(self._audio_worker()), asyncio.create_task(self._asr_worker()),
                      asyncio.create_task(self._translation_worker())]

    async def close(self):
        self.closed = True
        self.reset()
        for task in self.tasks: task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)

    def _error(self, code):
        self.hub.publish(dict(type='error', code=code,
                              message='Pipeline degraded: ' + code + '. Check local model/service and backlog.'))

    def _put_final(self, queue, job):
        try: queue.put_nowait(job)
        except asyncio.QueueFull:
            self.metrics['final_overflows'] += 1
            self.status.mode = 'pause'
            self._error('final_queue_overflow_speech_not_translated')

    async def _audio_worker(self):
        while True:
            await asyncio.sleep(0.02)
            if self.status.mode != 'start': continue
            while self.audio:
                chunk = self.audio.popleft(); self.audio_count -= chunk.size
                # Uniform 20ms blocks make onset/offset independent of transport chunk size.
                self.preroll = np.concatenate((self.preroll, chunk))
                while self.preroll.size >= self.block_size:
                    block, self.preroll = self.preroll[:self.block_size], self.preroll[self.block_size:]
                    self._block(block)
            if self.active and time.monotonic() - self.last_received > 0.72:
                self.revision += 1
                self._put_final(self.asr_finals, Job(self.uid, self.revision, True,
                    np.concatenate(self.segment), endpoint=self.last_received-self.silence/16000,
                    generation=self.generation))
                self.asr_partial = None
                self.asr_wake.set()
                self._new_utterance()
            self.metrics.update(audio_backlog_ms=self.audio_count/16,
                                asr_queue=self.asr_finals.qsize(), translation_queue=self.vi_finals.qsize())

    def _block(self, block):
        level = rms(block)
        self.metrics['rms'] = round(level, 5)
        voiced = self.vad.probability(block) >= (0.35 if self.active else 0.5) if self.vad else level > self.threshold
        if not self.active:
            self.onset = self.onset + block.size if voiced else 0
            self.segment.append(block)
            self.segment_size += block.size
            # 300ms pre-roll preserves consonants before onset confirmation.
            while self.segment_size > 4800:
                self.segment_size -= self.segment.pop(0).size
            if self.onset < 1920: return
            self.active = True
        else:
            self.segment.append(block)
            self.segment_size += block.size
        self.silence = 0 if voiced else self.silence + block.size
        final = self.silence >= 10400 or self.segment_size >= 160000
        if final or self.segment_size - self.last_snapshot >= 13600:
            self.revision += 1
            job = Job(self.uid, self.revision, final, np.concatenate(self.segment),
                      endpoint=time.monotonic() - self.silence/16000, generation=self.generation)
            if final:
                self.asr_partial = None
                self._put_final(self.asr_finals, job)
                self._new_utterance()
            else:
                self.asr_partial = job
                self.last_snapshot = self.segment_size
            self.asr_wake.set()

    async def _asr_worker(self):
        while True:
            await self.asr_wake.wait()
            self.asr_wake.clear()
            while not self.asr_finals.empty() or self.asr_partial:
                job = self.asr_finals.get_nowait() if not self.asr_finals.empty() else self.asr_partial
                if job is self.asr_partial: self.asr_partial = None
                if job.generation != self.generation: continue
                started = time.perf_counter()
                try: en = (await self.asr.transcribe(job.samples)).strip()
                except Exception:
                    self._error('asr_failure')
                    if job.final:
                        self.hypotheses.pop(job.uid, None)
                        self.latest.pop(job.uid, None)
                    continue
                if job.generation != self.generation or not en: continue
                elapsed = (time.perf_counter()-started)*1000
                self._timing('asr_ms', elapsed)
                self.metrics['asr_ms_last'] = round(elapsed)
                self.metrics['asr_calls'] += 1
                self.latest[job.uid] = job.revision
                while len(self.latest) > 140: self.latest.popitem(last=False)
                self.hub.publish(caption('transcript.final' if job.final else 'transcript.partial', job.uid,
                                         job.revision, en, source=self.asr.settings.asr_backend))
                stable = stable_prefix(self.hypotheses.get(job.uid, ''), en)
                self.hypotheses[job.uid] = en
                while len(self.hypotheses) > 140: self.hypotheses.popitem(last=False)
                job.english = en if job.final else stable
                job.samples = None
                job.context = tuple(self.context)
                if job.final:
                    self.hypotheses.pop(job.uid, None)
                    self.context.append(en)
                    self.vi_partial = None
                    self._put_final(self.vi_finals, job)
                    self.vi_wake.set()
                elif len(stable.split()) >= 5 and time.monotonic()-self.last_partial_sent >= 1.3:
                    self.last_partial_sent = time.monotonic()
                    self.vi_partial = job
                    self.vi_wake.set()

    async def _translation_worker(self):
        while True:
            await self.vi_wake.wait(); self.vi_wake.clear()
            while not self.vi_finals.empty() or self.vi_partial:
                job = self.vi_finals.get_nowait() if not self.vi_finals.empty() else self.vi_partial
                if job is self.vi_partial: self.vi_partial = None
                if job.generation != self.generation: continue
                started = time.perf_counter()
                try:
                    vi = await asyncio.wait_for(self.translator.translate(job.english, list(job.context)), timeout=25)
                except Exception:
                    self._error('final_translation_failure' if job.final else 'partial_translation_failure')
                    if job.final: self.latest.pop(job.uid, None)
                    continue
                if job.generation != self.generation: continue
                if not job.final and self.latest.get(job.uid) != job.revision: continue
                elapsed = (time.perf_counter()-started)*1000
                self._timing('translation_ms', elapsed)
                self.metrics['translation_ms_last'] = round(elapsed)
                self.metrics['translate_calls'] += 1
                self.hub.publish(caption('translation.final' if job.final else 'translation.partial', job.uid,
                                         job.revision, job.english, vi, source=self.translator.settings.translate_backend))
                if job.final:
                    self._timing('final_age_ms', (time.monotonic()-job.endpoint)*1000)
                    self.latest.pop(job.uid, None)

    def _timing(self, name, value):
        self.timings[name].append(value)
        values = np.array(self.timings[name])
        self.metrics[name + '_p50'] = round(float(np.percentile(values, 50)))
        self.metrics[name + '_p95'] = round(float(np.percentile(values, 95)))
        self.metrics[name + '_count'] = len(values)

    def reset(self):
        self.generation += 1
        self.audio.clear(); self.audio_count = 0
        self.asr_partial = self.vi_partial = None
        for q in (self.asr_finals, self.vi_finals):
            while not q.empty(): q.get_nowait()
        self.latest.clear(); self.hypotheses.clear(); self.context.clear()
        if self.vad: self.vad.reset()
        self._new_utterance()
