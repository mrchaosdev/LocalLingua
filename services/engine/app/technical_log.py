"""Rotating technical metadata only; deliberately excludes log messages and transcript text."""
import json
import logging
import logging.handlers
import os
from datetime import datetime,timezone
from pathlib import Path

class MetadataFormatter(logging.Formatter):
    def format(self,record):
        return json.dumps(dict(at=datetime.now(timezone.utc).isoformat(),level=record.levelname,
            component=record.name[:80],exception=record.exc_info[0].__name__ if record.exc_info else None))

def configure():
    directory=Path(os.getenv('LOCALLINGUA_DATA_DIR',str(Path(os.getenv('LOCALAPPDATA',str(Path.home())))/'LocalLingua')))/'runtime'
    directory.mkdir(parents=True,exist_ok=True)
    handler=logging.handlers.RotatingFileHandler(directory/'engine.jsonl',maxBytes=131072,backupCount=2,encoding='utf-8')
    handler.setFormatter(MetadataFormatter());handler.setLevel(logging.WARNING)
    logging.getLogger().addHandler(handler)
    for name in ('uvicorn.error','uvicorn'):
        logger=logging.getLogger(name);logger.handlers=[handler];logger.propagate=False
