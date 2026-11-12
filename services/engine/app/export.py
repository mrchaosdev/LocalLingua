"""Explicit export only. Strings are subtitle data, not filesystem paths."""
import re

def stamp(milliseconds):
    value=max(0,round(milliseconds))
    hours,value=divmod(value,3600000)
    minutes,value=divmod(value,60000)
    seconds,millis=divmod(value,1000)
    return f'{hours:02}:{minutes:02}:{seconds:02},{millis:03}'

def export_captions(events,format):
    finals=[e for e in events if e.get('phase')=='translation.final']
    finals.sort(key=lambda e:(e.get('audio_start_ms',e['created_at_ms']),e['created_at_ms']))
    if format=='txt': return '\n\n'.join(f"{e['english']}\n{e['vietnamese']}" for e in finals)
    if format=='md':
        def escape(s): return re.sub(r'([\\`*_{}\[\]<>])',r'\\\1',s).replace('\n',' ')
        return '# LocalLingua\n\n'+'\n\n'.join(f"{escape(e['vietnamese'])}\n\n> {escape(e['english'])}" for e in finals)
    if format=='srt':
        timed=[e for e in finals if 'audio_start_ms' in e and 'audio_end_ms' in e]
        if len(timed)!=len(finals): raise ValueError('SRT requires timestamped live captions; clear demo history first')
        start=min((e['audio_start_ms'] for e in timed),default=0)
        return '\n\n'.join(f"{i}\n{stamp(e['audio_start_ms']-start)} --> {stamp(max(e['audio_end_ms']-start,e['audio_start_ms']-start+200))}\n{e['vietnamese'].replace(chr(10),' ')}" for i,e in enumerate(timed,1))+'\n'
    raise ValueError('Unknown export format')
