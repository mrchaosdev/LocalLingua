import asyncio
from types import SimpleNamespace
import numpy as np
from app.events import EventHub, caption
from app.stream import SpeechSession


def test_final_is_immutable_per_language():
    hub = EventHub()
    hub.publish(caption('transcript.final', 'u', 2, 'Do not launch.'))
    hub.publish(caption('translation.final', 'u', 3, 'Do not launch.', 'Không ra mắt.'))
    hub.publish(caption('translation.partial', 'u', 99, 'Launch.', 'Ra mắt.'))
    assert len(hub.history) == 2
    assert list(hub.history.values())[-1]['vietnamese'] == 'Không ra mắt.'


def test_slow_subscriber_gets_explicit_gap_and_replay():
    hub = EventHub()
    queue = hub.subscribe()
    for i in range(151):
        hub.publish(caption('translation.final', str(i), 1, 'test', 'thử'))
    assert queue.get_nowait()['code'] == 'subscriber_overflow'
    assert queue not in hub.subscribers
    replay = hub.subscribe()
    hub.replay(replay)
    assert replay.qsize() == 70


def test_silence_does_not_trigger_models(monkeypatch):
    monkeypatch.delenv('VAD_MODEL_PATH', raising=False)
    async def run():
        class Never:
            async def transcribe(self, _): raise AssertionError('silence ASR')
            async def translate(self, *_): raise AssertionError('silence translation')
        state = SimpleNamespace(mode='start')
        s = SpeechSession(EventHub(), Never(), Never(), state)
        await s.start()
        for _ in range(20):
            s.ingest(np.zeros(640, np.float32))
            await asyncio.sleep(0.005)
        await asyncio.sleep(0.05)
        assert not s.active and s.metrics['asr_calls'] == 0
        await s.close()
    asyncio.run(run())


def test_stop_invalidates_inflight_translation(monkeypatch):
    monkeypatch.delenv('VAD_MODEL_PATH', raising=False)
    async def run():
        from app.stream import Job
        ready, release = asyncio.Event(), asyncio.Event()
        class Translator:
            settings = SimpleNamespace(translate_backend='mock')
            async def translate(self, *_):
                ready.set(); await release.wait(); return 'Không ra mắt.'
        hub = EventHub()
        s = SpeechSession(hub, None, Translator(), SimpleNamespace(mode='start'))
        task = asyncio.create_task(s._translation_worker())
        s.vi_partial = Job('u', 1, False, english='Do not launch', generation=0)
        s.latest['u'] = 1
        s.vi_wake.set()
        await ready.wait()
        s.reset()
        release.set()
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert not hub.history
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    asyncio.run(run())
