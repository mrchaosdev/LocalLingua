from __future__ import annotations
import asyncio
import json
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Literal
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from .audio import AudioFormat, AudioNormalizer
from .config import Settings
from .events import EventHub, caption
from .providers import Transcriber, Translator
from .stream import SpeechSession

settings = Settings()
hub = EventHub()

@dataclass
class State:
    mode: str = 'stop'
    capture_connected: bool = False
    active_session: SpeechSession | None = None

state = State()
translator = Translator(settings)
transcriber = Transcriber(settings)

async def status_heartbeat():
    while True:
        await asyncio.sleep(1.0)
        hub.publish(get_status())

@asynccontextmanager
async def lifespan(_app):
    heartbeat = asyncio.create_task(status_heartbeat())
    try:
        yield
    finally:
        heartbeat.cancel()
        try: await heartbeat
        except asyncio.CancelledError: pass
        if state.active_session:
            await state.active_session.close()
        await translator.close()

app = FastAPI(title='LocalLingua Engine', version='0.2.0-scaffold', lifespan=lifespan)
app.add_middleware(CORSMiddleware,
    allow_origins=['http://127.0.0.1:5173','http://localhost:5173'],
    allow_credentials=False, allow_methods=['GET','POST'],allow_headers=['Content-Type'])

class ModeInput(BaseModel):
    mode: Literal['start','pause','stop']

class GlossaryInput(BaseModel):
    term: str = Field(min_length=1, max_length=80)
    meaning: str = Field(min_length=1, max_length=160)

@app.post('/api/glossary')
async def glossary(body: GlossaryInput):
    if len(translator.glossary) >= 100 and body.term not in translator.glossary:
        raise HTTPException(409, 'Session glossary limit reached')
    if not body.term.strip() or not body.meaning.strip():
        raise HTTPException(422, 'Empty glossary entry')
    translator.glossary[body.term.strip()] = body.meaning.strip()
    return {'ok': True, 'entries': len(translator.glossary)}

def get_status():
    return {
        'type':'status', 'mode':state.mode, 'capture_connected':state.capture_connected,
        'asr_backend':settings.asr_backend, 'translate_backend':settings.translate_backend,
        'metrics':state.active_session.metrics if state.active_session else {},
        'warning':'Whole-system audio capture in starter; Discord-only isolation NOT implemented',
    }

@app.get('/health')
async def health():
    return {'ok':True,'version':'0.2.0-scaffold'}

@app.get('/api/status')
async def status():
    return get_status()

@app.post('/api/control')
async def control(body: ModeInput):
    state.mode = body.mode
    if body.mode == 'stop' and state.active_session:
        state.active_session.reset()
    hub.publish(get_status())
    return get_status()

@app.post('/api/demo')
async def demo():
    async def sample():
        from uuid import uuid4
        uid = str(uuid4())
        hub.publish(caption('transcript.partial',uid,1,'We are going to launch...',source='demo'))
        await asyncio.sleep(0.6)
        hub.publish(caption('translation.partial',uid,2,'We are going to launch...',
                             'Chúng tôi dự định ra mắt...',source='demo'))
        await asyncio.sleep(0.7)
        en='We are going to launch the next phase of the project next week.'
        hub.publish(caption('transcript.final',uid,3,en,source='demo'))
        hub.publish(caption('translation.final',uid,4,en,
                             'Chúng tôi dự định ra mắt giai đoạn tiếp theo của dự án vào tuần tới.',source='demo'))
    asyncio.create_task(sample())
    return {'ok':True,'note':'SYNTHETIC captions; not live model inference'}

@app.websocket('/ws/events')
async def event_stream(ws: WebSocket):
    # Security TODO release: bearer token + Origin validation.
    await ws.accept()
    q = hub.subscribe()
    try:
        await ws.send_json(get_status())
        hub.replay(q)
        while True:
            event = await q.get()
            await ws.send_json(event)
    except (WebSocketDisconnect, RuntimeError, ConnectionError):
        pass
    finally:
        hub.unsubscribe(q)

@app.websocket('/ws/ingest')
async def audio_ingest(ws: WebSocket):
    # Starter: one producer, loopback bound server only. No token/Origin yet.
    if state.capture_connected:
        await ws.close(code=1008, reason='Only one producer allowed')
        return
    await ws.accept()
    state.capture_connected = True
    hub.publish(get_status())
    session = None
    try:
        first = await ws.receive_text()
        fmt = AudioFormat.from_message(json.loads(first))
        normalizer = AudioNormalizer(fmt)
        session = SpeechSession(hub, transcriber, translator, state, settings.rms_threshold)
        state.active_session = session
        await session.start()
        while True:
            raw = await ws.receive_bytes()
            if state.mode == 'start':
                session.ingest(normalizer.convert(raw))
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        hub.publish({'type':'error','code':'capture_error','message':str(exc)[:250]})
    finally:
        if session:
            await session.close()
        state.active_session = None
        state.capture_connected = False
        hub.publish(get_status())
