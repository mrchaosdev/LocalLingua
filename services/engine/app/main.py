from __future__ import annotations
import asyncio
import json
import os
import secrets
import time
import uuid
from pathlib import Path
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Literal
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field
from .audio import AudioFormat, AudioNormalizer
from .config import Settings
from .events import EventHub, caption
from .providers import Transcriber, Translator
from .stream import SpeechSession

settings = Settings()
hub = EventHub()
session_token = os.getenv('LOCALLINGUA_TOKEN') or secrets.token_urlsafe(32)
session_id = str(uuid.uuid4())
origins = {'http://127.0.0.1:5173', 'http://localhost:5173', 'http://127.0.0.1:8765'}

@dataclass
class State:
    mode: str = 'stop'
    capture_connected: bool = False
    capture_source: str = 'none'
    active_session: SpeechSession | None = None

state = State()
translator = Translator(settings)
transcriber = Transcriber(settings)
demo_task: asyncio.Task | None = None
controls = deque(maxlen=30)

async def status_heartbeat():
    while True:
        await asyncio.sleep(1)
        hub.publish(get_status())

@asynccontextmanager
async def lifespan(_app):
    global translator
    if translator.client.is_closed: translator = Translator(settings)
    heartbeat = asyncio.create_task(status_heartbeat())
    try: yield
    finally:
        heartbeat.cancel()
        if demo_task: demo_task.cancel()
        await asyncio.gather(heartbeat, *([demo_task] if demo_task else []), return_exceptions=True)
        if state.active_session: await state.active_session.close()
        await translator.close()
        transcriber._model = None

app = FastAPI(title='LocalLingua Engine', version='0.3.0-dev', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=sorted(origins), allow_credentials=False,
                   allow_methods=['GET','POST'], allow_headers=['Content-Type','Authorization'])
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost'])

def valid_token(value):
    return isinstance(value, str) and value.isascii() and len(value) <= 512 and secrets.compare_digest(value, session_token)

@app.middleware('http')
async def protect(request: Request, call_next):
    if request.url.path.startswith('/api/') and request.method != 'OPTIONS':
        if request.headers.get('origin') and request.headers['origin'] not in origins:
            return JSONResponse({'detail':'Origin rejected'}, status_code=403)
        if not valid_token(request.headers.get('authorization','').removeprefix('Bearer ')):
            return JSONResponse({'detail':'Session token required'}, status_code=401)
        try: length = int(request.headers.get('content-length','0'))
        except ValueError: return JSONResponse({'detail':'Invalid length'},status_code=400)
        if length > 16384: return JSONResponse({'detail':'Request too large'},status_code=413)
        if request.method == 'POST':
            now = time.monotonic()
            if len(controls) == controls.maxlen and now-controls[0] < 10:
                return JSONResponse({'detail':'Control rate limit'},status_code=429)
            controls.append(now)
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Content-Security-Policy'] = "default-src 'self'; connect-src 'self' ws://127.0.0.1:8765; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; frame-ancestors 'none'; base-uri 'none'"
    return response

class ModeInput(BaseModel):
    mode: Literal['start','pause','stop']

class GlossaryInput(BaseModel):
    term: str = Field(min_length=1, max_length=80)
    meaning: str = Field(min_length=1, max_length=160)

@app.post('/api/glossary')
async def glossary(body: GlossaryInput):
    term, meaning = body.term.strip(), body.meaning.strip()
    if not term or not meaning: raise HTTPException(422, 'Empty glossary entry')
    if len(translator.glossary) >= 100 and term not in translator.glossary:
        raise HTTPException(409, 'Session glossary limit reached')
    translator.glossary[term] = meaning
    return {'ok':True, 'entries':len(translator.glossary)}

def get_status():
    source = state.capture_source
    warning = ('Chẩn đoán: đang lấy toàn bộ âm thanh hệ thống.' if source == 'system-diagnostic' else
               'Discord process tree: chưa qua kiểm thử cô lập nguồn.' if source == 'discord-process-tree' else
               'Chưa kết nối AudioHost. Demo dùng dữ liệu mô phỏng.')
    return dict(type='status', session_id=session_id, mode=state.mode, capture_connected=state.capture_connected,
                capture_source=source, asr_backend=settings.asr_backend, translate_backend=settings.translate_backend,
                metrics=state.active_session.metrics if state.active_session else {}, warning=warning,
                acceptance_verified=False)

@app.get('/health')
async def health():
    return {'ok':True,'version':'0.3.0-dev','session_id':session_id}

@app.get('/api/status')
async def status(): return get_status()

@app.post('/api/shutdown')
async def shutdown():
    if not hasattr(app.state, 'shutdown'): raise HTTPException(409, 'Run packaged entry point for shutdown')
    state.mode = 'stop'
    app.state.shutdown()
    return {'ok':True}

@app.post('/api/control')
async def control(body: ModeInput):
    if body.mode == 'start' and not state.capture_connected:
        raise HTTPException(409,'Connect AudioHost first')
    state.mode = body.mode
    if body.mode in ('stop','pause') and state.active_session:
        state.active_session.reset()
    hub.publish(get_status())
    return get_status()

@app.post('/api/demo')
async def demo():
    global demo_task
    if demo_task and not demo_task.done(): raise HTTPException(409,'Demo already running')
    async def sample():
        uid = str(uuid.uuid4())
        hub.publish(caption('transcript.partial',uid,1,'We will launch...',source='demo'))
        await asyncio.sleep(0.6)
        hub.publish(caption('translation.partial',uid,2,'We will launch...','Chúng tôi sẽ ra mắt...',source='demo'))
        await asyncio.sleep(0.7)
        en = 'We will launch next week, but not on Monday.'
        hub.publish(caption('transcript.final',uid,3,en,source='demo'))
        hub.publish(caption('translation.final',uid,4,en,'Chúng tôi sẽ ra mắt tuần tới, nhưng không phải thứ Hai.',source='demo'))
    demo_task = asyncio.create_task(sample())
    return {'ok':True,'note':'Synthetic captions, not inference'}

async def authenticate(ws):
    if ws.headers.get('origin') and ws.headers['origin'] not in origins:
        await ws.close(code=1008); return False
    if ws.headers.get('host','').split(':')[0] not in ('127.0.0.1','localhost'):
        await ws.close(code=1008); return False
    await ws.accept()
    token = ws.headers.get('authorization','').removeprefix('Bearer ')
    if not token:
        try:
            raw = await asyncio.wait_for(ws.receive_text(),5)
            if len(raw) > 4096: raise ValueError('Auth too large')
            message = json.loads(raw)
            if not isinstance(message, dict): raise ValueError('Invalid auth')
            token = message.get('token','') if message.get('type') == 'auth' else ''
        except (ValueError, asyncio.TimeoutError, WebSocketDisconnect): token = ''
    if not valid_token(token):
        await ws.close(code=1008); return False
    return True

@app.websocket('/ws/events')
async def event_stream(ws: WebSocket):
    if not await authenticate(ws): return
    if len(hub.subscribers) >= 8:
        await ws.close(code=1013); return
    q = hub.subscribe()
    try:
        await ws.send_json(get_status())
        hub.replay(q)
        while True:
            event = await q.get()
            await asyncio.wait_for(ws.send_json(event),5)
            if event.get('code') == 'subscriber_overflow':
                await ws.close(code=1013); break
    except (WebSocketDisconnect, RuntimeError, ConnectionError, asyncio.TimeoutError): pass
    finally: hub.unsubscribe(q)

@app.websocket('/ws/ingest')
async def audio_ingest(ws: WebSocket):
    if not await authenticate(ws): return
    if state.capture_connected:
        await ws.close(code=1008,reason='Only one producer allowed'); return
    state.capture_connected = True
    session = None
    try:
        first = await asyncio.wait_for(ws.receive_text(),5)
        if len(first)>4096: raise ValueError('Format too large')
        info = json.loads(first)
        fmt = AudioFormat.from_message(info)
        source = info.get('source','system-diagnostic')
        if source not in ('system-diagnostic','discord-process-tree'): raise ValueError('Unknown source')
        state.capture_source = source
        normalizer = AudioNormalizer(fmt)
        session = SpeechSession(hub,transcriber,translator,state,settings.rms_threshold)
        state.active_session = session
        await session.start()
        hub.publish(get_status())
        last_rx = time.monotonic()
        budget = fmt.sample_rate * fmt.channels * (4 if fmt.sample_format=='float32' else 2)
        allowance = budget
        processing = False
        while True:
            raw = await ws.receive_bytes()
            now = time.monotonic()
            allowance = min(budget,allowance + (now-last_rx)*budget*1.1)
            last_rx = now
            allowance -= len(raw)
            if len(raw)>budget//5 or allowance < 0: raise ValueError('Audio rate/size exceeded')
            if state.mode == 'start':
                if not processing: normalizer = AudioNormalizer(fmt)
                processing = True
                session.ingest(normalizer.convert(raw))
            else: processing = False
    except WebSocketDisconnect: pass
    except Exception:
        hub.publish({'type':'error','code':'capture_error','message':'Nguồn audio không hợp lệ hoặc đã ngắt.'})
        try: await ws.close(code=1008)
        except RuntimeError: pass
    finally:
        if session: await session.close()
        state.active_session = None
        state.capture_connected = False
        state.capture_source = 'none'
        state.mode = 'stop'
        hub.publish(get_status())

web_dir = Path(os.getenv('LOCALLINGUA_WEB_DIR', str(Path(__file__).resolve().parents[3]/'apps/web/dist')))
if web_dir.is_dir(): app.mount('/',StaticFiles(directory=web_dir,html=True),name='dashboard')
