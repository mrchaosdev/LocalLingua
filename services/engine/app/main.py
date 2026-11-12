from __future__ import annotations
import asyncio
import json
import os
import secrets
import time
import uuid
import math
from pathlib import Path
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, replace
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
from .runtime import PreferenceStore, Preferences, PROFILES
from .telemetry import Telemetry
from .transport import CaptureFrame
from .models import inspect_models
from .export import export_captions
from fastapi.responses import PlainTextResponse

settings = Settings()
base_settings = settings
preferences = PreferenceStore(settings)
def apply_preferences():
    global settings
    p = preferences.value
    settings = replace(base_settings, **{key:getattr(p,key) for key in ('asr_backend','translate_backend','whisper_model','whisper_device','whisper_compute','ollama_model')})
apply_preferences()
telemetry = Telemetry()
host_heartbeat = {}
model_install = {'state':'idle'}
installation_task = None
configuration_guard = asyncio.Lock()
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
    normalizer: AudioNormalizer | None = None
    capture_end_ms: float = 0
    clock_uncertainty_ms: float = 1000
    framed: bool = False

state = State()
translator = Translator(settings)
transcriber = Transcriber(settings)
demo_task: asyncio.Task | None = None
controls = deque(maxlen=30)

async def status_heartbeat():
    while True:
        await asyncio.sleep(1)
        hub.publish(get_status())

def report_error(code,component='engine'):
    telemetry.error(code,component)
    hub.publish(dict(type='error',code=code,message='Lỗi '+component+': '+code))

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
        if state.active_session:
            await state.active_session.close();state.active_session=None
        state.mode='stop'
        if installation_task: await installation_task
        await translator.close()
        transcriber._model = None

app = FastAPI(title='LocalLingua Engine', version='0.4.0-dev', lifespan=lifespan)
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

@app.get('/api/clock')
async def clock(): return {'mono_ms':time.perf_counter()*1000}

@app.get('/api/preferences')
async def read_preferences():
    return dict(value=preferences.value.model_dump(),revision=preferences.revision,profiles=PROFILES)

@app.post('/api/preferences')
async def write_preferences(body: Preferences):
    global transcriber,translator
    async with configuration_guard:
        if model_install['state']=='running': raise HTTPException(409,'Đang cài model; chờ hoàn tất trước khi lưu cấu hình.')
        visual_fields={'overlay_font_size','overlay_opacity','overlay_english'}
        changed={k for k,v in body.model_dump().items() if v!=getattr(preferences.value,k)}
        if changed.issubset(visual_fields):
            preferences.save(body); hub.publish(get_status())
            return await read_preferences()
        if state.mode != 'stop' or state.capture_connected or model_install['state']=='running':
            raise HTTPException(409,'Dừng capture và chờ tác vụ model hoàn tất trước khi đổi cấu hình.')
        if state.active_session:
            if state.active_session.pending_finals: raise HTTPException(409,'Đang hoàn tất các câu đã chốt.')
            await state.active_session.close(); state.active_session=None
        glossary=translator.glossary.copy()
        await translator.close()
        transcriber._model=None
        preferences.save(body); apply_preferences()
        transcriber=Transcriber(settings); translator=Translator(settings); translator.glossary=glossary
        hub.publish(get_status())
    return await read_preferences()

@app.get('/api/capture/config')
async def capture_config():
    p=preferences.value
    return dict(mode=state.mode,source=p.source,endpoint_id=p.endpoint_id,discord_pid=p.discord_pid,revision=preferences.revision)

@app.post('/api/capture/heartbeat')
async def capture_heartbeat(request: Request):
    data=await request.json()
    if not isinstance(data,dict): raise HTTPException(422,'Invalid heartbeat')
    # Metadata only; never accept arbitrary log strings or private process paths.
    host_heartbeat.update(at=time.monotonic(),state=str(data.get('state','unknown'))[:40],
                          code=str(data.get('code',''))[:80],pid=int(data.get('pid',0)),
                          dropped=int(data.get('dropped',0)),devices=data.get('devices',[])[:32],
                          processes=data.get('processes',[])[:32])
    return {'ok':True}

@app.get('/api/diagnostics')
async def diagnostics():
    return dict(models=await inspect_models(settings,preferences.directory),telemetry=telemetry.export(),
                errors=list(telemetry.errors),capture=host_heartbeat,preferences_warning=preferences.warning,
                asr_loaded=transcriber._model is not None,
                pipeline=state.active_session.metrics if state.active_session else {})

@app.get('/api/metrics/export')
async def metrics_export():
    return dict(**telemetry.export(),models=await inspect_models(settings,preferences.directory),
                configuration=preferences.value.model_dump(),acceptance_verified=False)

@app.get('/api/export/{format}')
async def export(format: Literal['txt','md','srt']):
    try: content=export_captions(hub.history.values(),format)
    except ValueError as exc: raise HTTPException(409,str(exc))
    return PlainTextResponse(content,headers={'Content-Disposition':f'attachment; filename="LocalLingua.{format}"'})

@app.post('/api/history/clear')
async def clear_history():
    if state.mode!='stop': raise HTTPException(409,'Dừng phiên trước khi xóa lịch sử.')
    if state.active_session and state.active_session.pending_finals: raise HTTPException(409,'Đang hoàn tất bản dịch final.')
    hub.history.clear();hub.history_evictions=0;hub.publish({'type':'history.cleared'})
    return {'ok':True}

@app.get('/api/glossary')
async def get_glossary(): return translator.glossary

@app.post('/api/glossary/delete')
async def delete_glossary(body: GlossaryInput):
    translator.glossary.pop(body.term,None)
    return {'ok':True}

@app.get('/api/models/install')
async def install_status(): return model_install

@app.post('/api/models/load')
async def load_models():
    async with configuration_guard: return await _load_models()

async def _load_models():
    if state.mode!='stop' or model_install['state']=='running': raise HTTPException(409,'Dừng phiên trước khi nạp model.')
    inspection=await inspect_models(settings,preferences.directory)
    if not inspection['asr_ready'] or not inspection['translation_ready']:
        raise HTTPException(409,'Thiếu dependency/model local hoặc Ollama chưa chạy. Mở Chẩn đoán để xem chi tiết.')
    if settings.asr_backend=='whisper':
        try:
            await transcriber.load()
        except Exception:
            report_error('model_load_failed','models')
            raise HTTPException(409,'Không nạp được model. Kiểm tra CUDA/cuDNN, VRAM và đường dẫn.')
    try: await translator.preload()
    except Exception: raise HTTPException(409,'Không nạp được model Ollama local.')
    return {'ok':True,'asr_loaded':transcriber._model is not None}

@app.post('/api/models/install')
async def install_models():
    global installation_task
    if state.mode!='stop' or state.capture_connected or model_install['state']=='running':
        raise HTTPException(409,'Dừng phiên trước khi tải model.')
    async def run():
        model_install.update(state='running',code='downloading_official_models')
        try:
            from install_models import install
            await asyncio.to_thread(install,preferences.directory/'models')
            model_install.update(state='complete',code='restart_to_apply_model_preferences')
        except Exception:
            model_install.update(state='failed',code='model_install_failed_check_network_disk_ollama')
            report_error('model_install_failed','models')
    model_install.update(state='running',code='downloading_official_models')
    installation_task=asyncio.create_task(run())
    return {'ok':True}

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
    host_available=time.monotonic()-host_heartbeat.get('at',0)<5
    warning = ('Chẩn đoán: đang lấy toàn bộ âm thanh hệ thống.' if source == 'system-diagnostic' else
               'Discord process tree: chưa qua kiểm thử cô lập nguồn.' if source == 'discord-process-tree' else
               'AudioHost đang chờ; chưa thu audio.' if host_available else
               'Chưa kết nối AudioHost. Demo dùng dữ liệu mô phỏng.')
    return dict(type='status', session_id=session_id, mode=state.mode, capture_connected=state.capture_connected,
                capture_source=source, asr_backend=settings.asr_backend, translate_backend=settings.translate_backend,
                metrics=state.active_session.metrics if state.active_session else {}, warning=warning,
                acceptance_verified=False,host_available=host_available,
                host=host_heartbeat,preferences=preferences.value.model_dump(),preference_revision=preferences.revision,
                profile=preferences.value.profile,model_install=model_install,latency=telemetry.summary(),
                errors=list(telemetry.errors),asr_loaded=transcriber._model is not None,
                history_limit=hub.max_history,history_evictions=hub.history_evictions)

@app.get('/health')
async def health():
    return {'ok':True,'version':'0.4.0-dev','session_id':session_id}

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
    async with configuration_guard: return await _control(body)

async def _control(body: ModeInput):
    if body.mode == 'start':
        if state.mode=='start' and state.active_session and not state.active_session.failed: return get_status()
        if model_install['state']=='running': raise HTTPException(409,'Đang tải model.')
        if settings.asr_backend=='whisper' and not Path(settings.whisper_model).is_dir():
            raise HTTPException(409,'Chọn thư mục model Whisper local hoặc tải model từ phần cài đặt.')
        if settings.asr_backend=='whisper' and transcriber._model is None:
            try: await transcriber.load()
            except Exception:
                report_error('model_load_failed','models')
                raise HTTPException(409,'Không nạp được Whisper. Kiểm tra CUDA/cuDNN, VRAM và model local.')
        try: await translator.preload()
        except Exception:
            report_error('ollama_model_unavailable','models')
            raise HTTPException(409,'Ollama/model local chưa sẵn sàng. Mở Chẩn đoán để kiểm tra.')
        if state.active_session and (state.active_session.failed or state.active_session.closed):
            await state.active_session.close();state.active_session=None
        if not state.active_session:
            try:
                state.active_session=SpeechSession(hub,transcriber,translator,state,settings.rms_threshold,
                    preferences=preferences.value,telemetry=telemetry)
                await state.active_session.start()
            except Exception:
                state.active_session=None; report_error('vad_or_model_unavailable','models')
                raise HTTPException(409,'Kiểm tra đường dẫn model/VAD và dependency local.')
    if body.mode in ('pause','stop') and state.mode=='start' and state.normalizer and state.active_session:
        state.active_session.ingest(state.normalizer.finish(),capture_end_ms=state.capture_end_ms,
            uncertainty_ms=state.clock_uncertainty_ms,calibrated=state.framed)
        state.normalizer=None
    state.mode = body.mode
    if body.mode in ('stop','pause') and state.active_session:
        state.active_session.pause()
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
        client=str(uuid.uuid4())
        async def send():
            while True:
                event=await q.get()
                await asyncio.wait_for(ws.send_json(event),5)
                if event.get('code')=='subscriber_overflow':
                    await ws.close(code=1013); return
        async def receive():
            while True:
                raw=await ws.receive_text()
                if len(raw)>4096: return
                message=json.loads(raw)
                if message.get('type')=='render.ack':
                    telemetry.rendered(str(message.get('trace_id',''))[:150],float(message.get('render_mono_ms',0)),
                                       float(message.get('uncertainty_ms',1000)),client)
        tasks=[asyncio.create_task(send()),asyncio.create_task(receive())]
        try: await asyncio.wait(tasks,return_when=asyncio.FIRST_COMPLETED)
        finally:
            for task in tasks: task.cancel()
            await asyncio.gather(*tasks,return_exceptions=True)
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
        state.normalizer=normalizer
        if not state.active_session:
            state.active_session=SpeechSession(hub,transcriber,translator,state,settings.rms_threshold,
                                               preferences=preferences.value,telemetry=telemetry)
            await state.active_session.start()
        session=state.active_session
        framed=info.get('protocol')==2
        state.framed=framed
        clock_offset=float(info.get('clock_offset_ms',0))
        clock_uncertainty=float(info.get('clock_uncertainty_ms',1000))
        state.clock_uncertainty_ms=clock_uncertainty
        if not math.isfinite(clock_offset) or abs(clock_offset)>86400000 or not 0<=clock_uncertainty<=1000: raise ValueError('Invalid clock calibration')
        sequence=None
        hub.publish(get_status())
        last_rx = time.monotonic()
        budget = fmt.sample_rate * fmt.channels * (4 if fmt.sample_format=='float32' else 2)
        allowance = budget
        processing = False
        last_capture_end_ms=0
        while True:
            try: raw=await asyncio.wait_for(ws.receive_bytes(),0.15)
            except asyncio.TimeoutError:
                if processing and state.mode=='start':
                    previous_receive=session.last_received
                    session.ingest(normalizer.finish(),capture_end_ms=last_capture_end_ms,
                                   uncertainty_ms=clock_uncertainty,calibrated=state.framed)
                    session.last_received=previous_receive
                    processing=False
                    state.normalizer=None
                continue
            metadata=CaptureFrame.parse(raw) if framed else None
            if metadata:
                if sequence is not None and metadata.sequence!=sequence+1:
                    session.discontinuity('capture_sequence_gap')
                sequence=metadata.sequence
                raw=metadata.pcm
                state.framed=not bool(metadata.dropped&(1<<63))
                session.metrics['capture_dropped_frames']=metadata.dropped&((1<<63)-1)
            now = time.monotonic()
            allowance = min(budget,allowance + (now-last_rx)*budget*1.1)
            last_rx = now
            allowance -= len(raw)
            if len(raw)>budget//5 or allowance < 0: raise ValueError('Audio rate/size exceeded')
            if state.mode == 'start':
                if not processing or state.normalizer is None:
                    normalizer=AudioNormalizer(fmt);state.normalizer=normalizer
                processing = True
                capture_end_ms=metadata.end_ns/1e6+clock_offset if metadata else time.perf_counter()*1000
                if abs(time.perf_counter()*1000-capture_end_ms)>10000: raise ValueError('Invalid source timestamp')
                converted=normalizer.convert(raw)
                last_capture_end_ms=capture_end_ms
                state.capture_end_ms=capture_end_ms
                session.ingest(converted,capture_end_ms=capture_end_ms-normalizer.delay_ms,
                               uncertainty_ms=clock_uncertainty,calibrated=framed and not (metadata and metadata.dropped&(1<<63)))
            else: processing = False
    except WebSocketDisconnect: pass
    except Exception:
        hub.publish({'type':'error','code':'capture_error','message':'Nguồn audio không hợp lệ hoặc đã ngắt.'})
        try: await ws.close(code=1008)
        except RuntimeError: pass
    finally:
        if session and state.mode=='start' and state.normalizer:
            try:
                session.ingest(state.normalizer.finish(),capture_end_ms=state.capture_end_ms,
                    uncertainty_ms=state.clock_uncertainty_ms,calibrated=state.framed)
            except ValueError: report_error('truncated_audio_frame','capture')
        state.normalizer=None
        if session: session.pause()
        state.capture_connected = False
        state.capture_source = 'none'
        if state.mode=='start': report_error('source_disconnected_retrying','capture')
        hub.publish(get_status())

web_dir = Path(os.getenv('LOCALLINGUA_WEB_DIR', str(Path(__file__).resolve().parents[3]/'apps/web/dist')))
if web_dir.is_dir(): app.mount('/',StaticFiles(directory=web_dir,html=True),name='dashboard')
