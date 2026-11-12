"""Local readiness inspection does not load models, transcribe audio or download data."""
import asyncio
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import httpx

async def inspect_models(settings, directory):
    packages={}
    for name in ('faster-whisper','ctranslate2','onnxruntime','soxr','numpy'):
        try: packages[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError: packages[name]=None
    model=Path(settings.whisper_model)
    asr_ready = settings.asr_backend=='mock' or (packages['faster-whisper'] is not None and model.is_dir() and (model/'model.bin').is_file())
    ollama={}
    translation_ready=settings.translate_backend=='mock'
    try:
        async with httpx.AsyncClient(timeout=3,trust_env=False) as client:
            response=await client.get(settings.ollama_url.rstrip('/')+'/api/tags')
            response.raise_for_status()
            tags=response.json().get('models',[])
            ollama['models']=[dict(name=m.get('name'),digest=m.get('digest'),size=m.get('size')) for m in tags]
            running=await client.get(settings.ollama_url.rstrip('/')+'/api/ps')
            if running.is_success:
                ollama['running']=[dict(name=m.get('name'),size_vram=m.get('size_vram'),context_length=m.get('context_length')) for m in running.json().get('models',[])]
            names={m.get('name') for m in tags}
            if settings.translate_backend=='ollama': translation_ready=settings.ollama_model in names or settings.ollama_model+':latest' in names
    except (httpx.HTTPError,ValueError): ollama['error']='Ollama chưa chạy hoặc không phản hồi.'
    gpu=[]
    try:
        process=await asyncio.create_subprocess_exec('nvidia-smi','--query-gpu=name,driver_version,memory.total,memory.used','--format=csv,noheader,nounits',stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.DEVNULL,creationflags=0x08000000 if os.name=='nt' else 0)
        try: stdout,_=await asyncio.wait_for(process.communicate(),3)
        except asyncio.TimeoutError:
            process.kill(); await process.wait(); raise
        gpu=stdout.decode(errors='replace').strip().splitlines()
    except (OSError,asyncio.TimeoutError): pass
    inventory={}
    try: inventory=json.loads((Path(directory)/'models.lock.json').read_text(encoding='utf-8'))
    except (OSError,ValueError): pass
    return dict(asr_ready=asr_ready,translation_ready=translation_ready,packages=packages,ollama=ollama,gpu=gpu,
                model_inventory=inventory,
                note='Kiểm tra dependency/model local; không phải kết quả inference hay benchmark.')
