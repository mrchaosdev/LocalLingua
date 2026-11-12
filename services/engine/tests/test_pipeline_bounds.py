import asyncio
from types import SimpleNamespace
import numpy as np
from app.audio import AudioFormat, AudioNormalizer
from app.events import EventHub
from app.stream import SpeechSession, Job


def test_fragmented_pcm_keeps_resampler_state():
    signal = np.sin(2*np.pi*440*np.arange(48000)/48000).astype('<f4').tobytes()
    fmt = AudioFormat(48000,1,'float32')
    a, b = AudioNormalizer(fmt), AudioNormalizer(fmt)
    whole = np.concatenate((a.convert(signal),a.finish()))
    parts = [b.convert(signal[i:i+1031]) for i in range(0,len(signal),1031)]
    split = np.concatenate(parts+[b.finish()])
    assert whole.size == split.size == 16000
    assert np.max(np.abs(whole-split)) < 1e-5


def test_final_overflow_pauses_visibly(monkeypatch):
    monkeypatch.delenv('VAD_MODEL_PATH',raising=False)
    hub = EventHub()
    q = hub.subscribe()
    state = SimpleNamespace(mode='start')
    s = SpeechSession(hub,None,None,state)
    for i in range(9): s._put_final(s.asr_finals,Job(str(i),1,True))
    assert s.asr_finals.qsize() == 8
    assert state.mode == 'pause'
    assert q.get_nowait()['code'] == 'final_queue_overflow_speech_not_translated'


def test_stale_translation_cannot_replace_new_revision(monkeypatch):
    monkeypatch.delenv('VAD_MODEL_PATH',raising=False)
    async def run():
        entered, release, done = asyncio.Event(), asyncio.Event(), asyncio.Event()
        class Translator:
            settings = SimpleNamespace(translate_backend='mock')
            async def translate(self,en,*_):
                if en == 'old': entered.set(); await release.wait()
                else: done.set()
                return en
        hub = EventHub()
        s = SpeechSession(hub,None,Translator(),SimpleNamespace(mode='start'))
        task = asyncio.create_task(s._translation_worker())
        s.latest['u'] = 1
        s.vi_partial = Job('u',1,False,english='old')
        s.vi_wake.set()
        await entered.wait()
        s.latest['u'] = 2
        s.vi_partial = Job('u',2,False,english='new')
        s.vi_wake.set(); release.set()
        await done.wait()
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        values = list(hub.history.values())
        assert len(values) == 1 and values[0]['vietnamese'] == 'new'
        task.cancel(); await asyncio.gather(task,return_exceptions=True)
    asyncio.run(run())
