"""Metadata-only bounded traces. Source/client clocks are calibrated, never assumed equal."""
import time
from collections import OrderedDict, deque
import numpy as np

class Telemetry:
    def __init__(self):
        self.traces = OrderedDict()
        self.errors = deque(maxlen=30)
        self.started = time.monotonic()
        self.origin_ms = time.perf_counter()*1000
        self.baseline=deque(maxlen=600)
        self.recent=deque(maxlen=600)

    def error(self, code, component='engine'):
        self.errors.append(dict(code=code,component=component,at_ms=int(time.time()*1000)))

    def record(self, trace):
        self.traces[trace['trace_id']] = trace
        while len(self.traces)>2048: self.traces.popitem(last=False)

    def rendered(self, trace_id, rendered_ms, uncertainty_ms, client):
        trace = self.traces.get(trace_id)
        now = time.perf_counter()*1000
        if not trace or not np.isfinite(rendered_ms) or not 0<=uncertainty_ms<=1000 or abs(now-rendered_ms)>10000: return
        # Separate UI clients: a slow overlay cannot overwrite the dashboard measurement.
        first=not trace.get('renders')
        trace.setdefault('renders',{}).setdefault(client,dict(render_mono_ms=rendered_ms,uncertainty_ms=uncertainty_ms))
        if first and trace.get('phase')=='translation.final':
            age=rendered_ms-trace['speech_end_mono_ms']
            elapsed=time.monotonic()-self.started
            if age>=0:
                if elapsed<300:self.baseline.append(age)
                self.recent.append((elapsed,age))
        if len(trace['renders'])>8: trace['renders'].pop(next(iter(trace['renders'])))

    def summary(self):
        result = {}
        for name, extractor in {
            'capture_to_engine_ms':lambda t: t['ingest_mono_ms']-t['capture_end_mono_ms'],
            'final_to_render_ms':lambda t: min(r['render_mono_ms'] for r in t.get('renders',{}).values())-t['speech_end_mono_ms'] if t.get('is_final') else None,
            'first_vi_partial_ms':lambda t: min(r['render_mono_ms'] for r in t.get('renders',{}).values())-t['speech_start_mono_ms'] if t.get('phase')=='translation.partial' else None,
        }.items():
            values=[];first_partials={}
            for trace in self.traces.values():
                try: value=extractor(trace)
                except (KeyError,ValueError): continue
                if trace.get('phase','').startswith('translation') and value is not None and value>=0:
                    if name=='first_vi_partial_ms':
                        uid=trace.get('utterance_id',trace['trace_id'])
                        first_partials[uid]=min(value,first_partials.get(uid,float('inf')))
                    else:values.append(value)
            if name=='first_vi_partial_ms':values=list(first_partials.values())
            result[name] = dict(count=len(values),p50=round(float(np.percentile(values,50)),1) if values else None,
                                p95=round(float(np.percentile(values,95)),1) if values else None)
        return result

    def export(self):
        elapsed=time.monotonic()-self.started
        recent=[value for at,value in self.recent if at>=elapsed-300]
        trend=(float(np.mean(recent))-float(np.mean(self.baseline))) if elapsed>=1800 and self.baseline and recent else None
        return dict(duration_s=round(time.monotonic()-self.started,2),metrics=self.summary(),
                    lag_trend_ms=round(trend,1) if trend is not None else None,
                    lag_trend_scope='Mean of last 5 min minus first 5 min; available after 30 min with rendered finals in both windows.',
                    traces=list(self.traces.values()),errors=list(self.errors),
                    scope='Capture-clock-to-client-render estimate; uncertainty included. Not acoustic-to-photon ground truth.')
