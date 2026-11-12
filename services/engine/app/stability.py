import re

def normalize_tokens(text: str) -> list[str]:
    return re.findall(r"[\w'-]+", text.lower(), re.UNICODE)

def stable_prefix(a: str, b: str) -> str:
    """Conservative two-hypothesis stable word prefix (prototype)."""
    wa, wb = a.split(), b.split()
    output = []
    for x, y in zip(wa, wb):
        if normalize_tokens(x) != normalize_tokens(y):
            break
        output.append(y)
    return " ".join(output)

class RevisionGate:
    def __init__(self):
        self.latest: dict[str,int] = {}
        self.final: set[str] = set()

    def allow(self, utterance_id: str, revision: int, is_final: bool) -> bool:
        if utterance_id in self.final: return False
        if revision <= self.latest.get(utterance_id, -1): return False
        self.latest[utterance_id] = revision
        if is_final: self.final.add(utterance_id)
        return True
