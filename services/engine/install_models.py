"""Explicit model installation. Contacts ONLY official model sources when invoked by the user."""
import argparse
import hashlib
import json
import re
import subprocess
import shutil
import os
from pathlib import Path
from datetime import datetime, timezone


def sha256(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        while data:=stream.read(1024*1024): digest.update(data)
    return digest.hexdigest()


def install(directory, asr_revision=None, qwen_revision=None, vad_revision=None):
    from huggingface_hub import HfApi, snapshot_download, hf_hub_download
    directory=Path(directory).resolve(); directory.mkdir(parents=True,exist_ok=True)
    ollama=shutil.which('ollama') or str(Path(os.getenv('LOCALAPPDATA',''))/'Programs/Ollama/ollama.exe')
    if not Path(ollama).is_file(): raise RuntimeError('Install Ollama from the official Windows installer first')
    if shutil.disk_usage(directory).free<8*1024**3: raise RuntimeError('At least 8 GiB free disk is required for weights and Ollama import')
    api=HfApi()
    inventory={'created_at':datetime.now(timezone.utc).isoformat(),'models':[]}
    paths={}
    for repo,revision,kind,license_name in (
        ('Systran/faster-whisper-small.en',asr_revision,'asr','MIT'),
        ('Qwen/Qwen3-4B-GGUF',qwen_revision,'translator','Apache-2.0'),
    ):
        # Resolve a mutable input once, then download by immutable SHA.
        info=api.model_info(repo,revision=revision or 'main',files_metadata=True)
        commit=info.sha
        declared=getattr(info.card_data,'license',None)
        if declared and str(declared).lower()!=license_name.lower(): raise RuntimeError('Upstream model license changed; review before installation')
        folder=directory/('whisper-small.en' if kind=='asr' else 'qwen3-4b')/commit
        paths[kind]=folder
        if kind=='asr':
            snapshot_download(repo,revision=commit,local_dir=folder,allow_patterns=['*.json','*.bin','*.txt','README.md','LICENSE*'])
            files=[p for p in folder.rglob('*') if p.is_file() and '.cache' not in p.parts]
        else:
            candidates=[s.rfilename for s in info.siblings if re.search(r'q4_k_m.*\.gguf$',s.rfilename,re.I)]
            if len(candidates)!=1:
                raise RuntimeError('Expected one official Q4_K_M GGUF; inspect model repository before installing split variants')
            files=[Path(hf_hub_download(repo,candidates[0],revision=commit,local_dir=folder))]
            for sibling in info.siblings:
                if Path(sibling.rfilename).name.lower() in ('license','license.txt','readme.md'):
                    files.append(Path(hf_hub_download(repo,sibling.rfilename,revision=commit,local_dir=folder)))
            gguf=next(p for p in files if p.suffix=='.gguf')
            modelfile=folder/'Modelfile'
            modelfile.write_text('FROM "'+str(gguf).replace('\\','/')+'"\nPARAMETER num_ctx 2048\nPARAMETER temperature 0\n',encoding='utf-8')
        recorded=[]
        for file in files:
            actual=sha256(file)
            sibling=next((s for s in info.siblings if s.rfilename==file.relative_to(folder).as_posix()),None)
            metadata=getattr(sibling,'lfs',None)
            expected=metadata.get('sha256') if isinstance(metadata,dict) else getattr(metadata,'sha256',None)
            if expected and actual!=expected: raise RuntimeError('Downloaded model hash differs from upstream LFS metadata')
            recorded.append(dict(path=str(file.relative_to(directory)),sha256=actual,upstream_lfs_sha256=expected))
        if kind=='translator':
            subprocess.run([ollama,'create','locallingua-qwen3-4b','-f',str(modelfile)],check=True,
                           creationflags=0x08000000 if os.name=='nt' else 0)
        inventory['models'].append(dict(role=kind,repo=repo,revision=commit,license=license_name,
            source='https://huggingface.co/'+repo,files=recorded))
    # Silero weights are taken from the upstream Git repository at an exact commit.
    import httpx
    with httpx.Client(timeout=120,follow_redirects=True,trust_env=False) as client:
        commit=vad_revision
        if not commit:
            response=client.get('https://api.github.com/repos/snakers4/silero-vad/commits/master')
            response.raise_for_status(); commit=response.json()['sha']
        if not re.fullmatch(r'[0-9a-f]{40}',commit): raise ValueError('Silero revision must be a Git commit SHA')
        folder=directory/'silero'/commit; folder.mkdir(parents=True,exist_ok=True)
        paths['vad']=folder
        files=[]
        for source,name in [('src/silero_vad/data/silero_vad.onnx','silero_vad.onnx'),('LICENSE','LICENSE')]:
            response=client.get(f'https://raw.githubusercontent.com/snakers4/silero-vad/{commit}/{source}')
            response.raise_for_status()
            target=folder/name; target.write_bytes(response.content); files.append(target)
        inventory['models'].append(dict(role='vad',repo='snakers4/silero-vad',revision=commit,license='MIT',
            source='https://github.com/snakers4/silero-vad',files=[dict(path=str(p.relative_to(directory)),sha256=sha256(p)) for p in files]))
        response=client.get('http://127.0.0.1:11434/api/tags'); response.raise_for_status()
        inventory['ollama']=next((m for m in response.json()['models'] if m['name']=='locallingua-qwen3-4b:latest'),{})
    (directory/'models.lock.json').write_text(json.dumps(inventory,indent=2,ensure_ascii=False),encoding='utf-8')
    # Configuration only; no account credential, audio or transcript.
    from app.runtime import Preferences, PreferenceStore
    from app.config import Settings
    store=PreferenceStore(Settings())
    store.save(store.value.model_copy(update=dict(asr_backend='whisper',translate_backend='ollama',
        whisper_device='cuda',whisper_compute='int8_float16',whisper_model=str(paths['asr']),
        ollama_model='locallingua-qwen3-4b:latest',vad_model_path=str(paths['vad']/'silero_vad.onnx'))))
    (store.directory/'models.lock.json').write_text(json.dumps(inventory,indent=2),encoding='utf-8')
    return inventory

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Download official pinned models and configure local GPU inference')
    parser.add_argument('--directory',required=True)
    parser.add_argument('--asr-revision'); parser.add_argument('--qwen-revision'); parser.add_argument('--vad-revision')
    args=parser.parse_args()
    install(args.directory,args.asr_revision,args.qwen_revision,args.vad_revision)
    print('Models installed, hashes/revisions/licenses recorded. GPU inference has not been verified.')
