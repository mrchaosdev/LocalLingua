from __future__ import annotations
import asyncio
import time
import uuid
from collections import deque
from typing import Any


def caption(phase: str, utterance_id: str, revision: int, english: str, vietnamese: str = "", source: str = "mock") -> dict:
    return {
        "type": "caption", "phase": phase, "utterance_id": utterance_id,
        "revision": revision, "is_final": phase.endswith(".final"),
        "english": english, "vietnamese": vietnamese,
        "created_at_ms": int(time.time() * 1000), "source": source,
    }

class EventHub:
    def __init__(self, max_history: int = 70):
        self.subscribers: set[asyncio.Queue] = set()
        self.history: deque[dict[str, Any]] = deque(maxlen=max_history)

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=150)
        self.subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self.subscribers.discard(q)

    def publish(self, event: dict[str, Any]) -> None:
        if event.get("type") == "caption":
            self.history.append(event)
        for q in list(self.subscribers):
            if q.full():
                # PoC policy: drop oldest subscriber UI event, never block capture.
                # Release needs prioritized delivery of final events + reconnect replay.
                try: q.get_nowait()
                except asyncio.QueueEmpty: pass
            try: q.put_nowait(event)
            except asyncio.QueueFull: pass

    def replay(self, q: asyncio.Queue) -> None:
        for event in self.history:
            if q.full(): break
            q.put_nowait(event)
