from __future__ import annotations
import asyncio
import time
import uuid
import numpy as np
from .audio import rms
from .events import caption

class SpeechSession:
    """Baseline rolling-ASR session. NOT a finished native streaming engine."""
    def __init__(self, hub, transcriber, translator, status, rms_threshold=0.006):
        self.hub, self.asr, self.translator, self.status = hub, transcriber, translator, status
        self.threshold = rms_threshold
        self.samples = np.zeros(0, dtype=np.float32)
        self.last_sound = time.monotonic()
        self.speech_active = False
        self.id = str(uuid.uuid4())
        self.revision = 0
        self.last_en = ''
        self.previous_en = ''
        self.last_vi = ''
        self.final_context: list[str] = []
        self.last_partial_translation = 0.0
        self.translation_task: asyncio.Task | None = None  # tentative only
        self.final_tasks: set[asyncio.Task] = set()
        self.worker_task: asyncio.Task | None = None
        self.closed = False
        self.asr_guard = asyncio.Lock()
        self.metrics = {'frames':0,'dropped_samples':0,'asr_calls':0,'translate_calls':0,'asr_ms_last':0,'translation_ms_last':0,'rms':0.0}

    def ingest(self, chunk: np.ndarray):
        if chunk.size == 0 or self.status.mode != 'start': return
        self.metrics['frames'] += 1
        level = rms(chunk)
        self.metrics['rms'] = round(level, 5)
        if level > self.threshold:
            self.last_sound = time.monotonic()
            self.speech_active = True
        # Bounded to 11 sec; chunks may be native resampled independently in starter.
        self.samples = np.concatenate((self.samples,chunk))
        if self.samples.size > 176000:
            over = self.samples.size - 176000
            self.metrics['dropped_samples'] += over
            self.samples = self.samples[-176000:]

    async def start(self):
        self.worker_task = asyncio.create_task(self.run())

    async def close(self):
        self.closed = True
        if self.worker_task:
            self.worker_task.cancel()
            try: await self.worker_task
            except asyncio.CancelledError: pass
        if self.translation_task:
            self.translation_task.cancel()
            try: await self.translation_task
            except asyncio.CancelledError: pass
        if self.final_tasks:
            await asyncio.gather(*list(self.final_tasks), return_exceptions=True)

    async def run(self):
        while not self.closed:
            await asyncio.sleep(0.8)
            if self.status.mode != 'start' or not self.speech_active: continue
            if self.samples.size < 9600: continue
            silence = time.monotonic() - self.last_sound
            is_final = silence > 0.72 or self.samples.size >= 160000
            await self._asr_step(is_final)

    async def _asr_step(self, is_final: bool):
        if self.asr_guard.locked(): return
        async with self.asr_guard:
            window = self.samples.copy() if is_final else self.samples[-56000:].copy()
            ts = time.perf_counter()
            try:
                en = (await self.asr.transcribe(window)).strip()
            except Exception as exc:
                self.hub.publish({'type':'error','code':'asr_failure','message':str(exc)[:250]})
                if is_final: self.reset()
                return
            self.metrics['asr_ms_last'] = int((time.perf_counter() - ts)*1000)
            self.metrics['asr_calls'] += 1
            if not en and is_final:
                self.reset()
                return
            if not en: return
            if en != self.last_en or is_final:
                self.revision += 1
                self.hub.publish(caption('transcript.final' if is_final else 'transcript.partial', self.id,
                                         self.revision, en, source=self.asr.settings.asr_backend))
                self.previous_en, self.last_en = self.last_en, en
            if is_final:
                # A final translation must survive session reset; capture values first.
                uid, rev, final_en = self.id, self.revision, en
                self.final_context.append(en)
                self.final_context = self.final_context[-3:]
                ctx = self.final_context[:-1].copy()
                if self.translation_task: self.translation_task.cancel()
                task = asyncio.create_task(self._translate(uid, rev+1, final_en, True, ctx))
                self.final_tasks.add(task)
                task.add_done_callback(self.final_tasks.discard)
                self.translation_task = None
                self.reset()
            elif time.monotonic() - self.last_partial_translation > 1.5 and len(en.split()) >= 5:
                self.last_partial_translation = time.monotonic()
                uid, rev = self.id, self.revision
                if self.translation_task: self.translation_task.cancel()
                self.translation_task = asyncio.create_task(self._translate(uid, rev, en, False, self.final_context[:-1]))

    async def _translate(self, uid, rev, en, is_final, context):
        ts = time.perf_counter()
        try:
            vi = await self.translator.translate(en, context)
            self.metrics['translate_calls'] += 1
            self.metrics['translation_ms_last'] = int((time.perf_counter()-ts)*1000)
            # Captions must carry original utterance ID, final separate from partial.
            self.hub.publish(caption('translation.final' if is_final else 'translation.partial', uid,
                                     rev, en, vi, source=self.translator.settings.translate_backend))
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.hub.publish({'type':'error','code':'translation_failure','message':str(exc)[:250]})

    def reset(self):
        self.samples = np.zeros(0, dtype=np.float32)
        self.speech_active = False
        self.id = str(uuid.uuid4())
        self.revision = 0
        self.last_en, self.previous_en = '', ''
        self.last_partial_translation = 0.0
