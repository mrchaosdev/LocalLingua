from __future__ import annotations
import asyncio
import time
from collections import OrderedDict

PHASES = {'transcript.partial', 'transcript.final', 'translation.partial', 'translation.final'}

def caption(phase, utterance_id, revision, english, vietnamese='', source='mock'):
    if phase not in PHASES or revision < 1:
        raise ValueError('Invalid caption phase/revision')
    return dict(type='caption', phase=phase, utterance_id=utterance_id,
                revision=revision, is_final=phase.endswith('.final'), english=english,
                vietnamese=vietnamese, created_at_ms=int(time.time()*1000), source=source)

class EventHub:
    """Bounded snapshot. Slow subscribers disconnect explicitly and replay on reconnect."""
    def __init__(self, max_history=70):
        self.subscribers: set[asyncio.Queue] = set()
        self.history = OrderedDict()
        self.max_history = max_history
        self.history_evictions = 0

    def subscribe(self):
        q = asyncio.Queue(maxsize=150)
        self.subscribers.add(q)
        return q

    def unsubscribe(self, q):
        self.subscribers.discard(q)

    def publish(self, event):
        if event.get('type') == 'caption':
            key = (event['utterance_id'], event['phase'].split('.')[0])
            previous = self.history.get(key)
            if previous and (previous['is_final'] or event['revision'] <= previous['revision']):
                return
            self.history[key] = event
            while len(self.history) > self.max_history:
                self.history.popitem(last=False)
                self.history_evictions += 1
        for q in list(self.subscribers):
            if q.full():
                self.unsubscribe(q)
                while not q.empty():
                    q.get_nowait()
                q.put_nowait({'type': 'error', 'code': 'subscriber_overflow',
                              'message': 'Caption stream overflow; reconnecting for snapshot.'})
            else:
                q.put_nowait(event)

    def replay(self, q):
        for event in self.history.values():
            if not q.full():
                q.put_nowait(event)
