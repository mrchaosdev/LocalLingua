from pathlib import Path
import json
root=Path(__file__).resolve().parents[1]
for p in ['README.md','AGENTS.md','CLAUDE.md','docs/04-REALTIME-ENGINE.md','docs/05-DESIGN-ASTRYX.md','contracts/events.schema.json','services/engine/app/main.py','apps/web/src/App.tsx','apps/windows/LocalLingua.AudioHost/Program.cs']:
    assert (root/p).exists(), p
json.loads((root/'contracts/events.schema.json').read_text(encoding='utf-8'))
json.loads((root/'apps/web/package.json').read_text(encoding='utf-8'))
print('Bundle structure and JSON validation PASS')
