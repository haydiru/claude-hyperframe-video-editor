"""Source <-> output time mapping for EDL v2 (src segments + hold breathers)."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
E = json.loads((ROOT / "work/edl/edl.json").read_text())
FPS = E["fps"]
SEGS = E["segments"]


def spans():
    """[(out_start, out_end, kind, src_start)] in seconds."""
    out, t = [], 0
    for s in SEGS:
        n = (s["b"] - s["a"]) if s["t"] == "src" else s["n"]
        out.append((t / FPS, (t + n) / FPS, s["t"], (s["a"] / FPS) if s["t"] == "src" else None))
        t += n
    return out


SP = spans()


def src_to_out(ts):
    for o0, o1, k, s0 in SP:
        if k == "src" and s0 <= ts <= s0 + (o1 - o0):
            return o0 + (ts - s0)
    return None


def out_to_src(to):
    for o0, o1, k, s0 in SP:
        if o0 <= to < o1:
            return (s0 + (to - o0)) if k == "src" else None
    return None


def joins():
    """output times where two source segments meet (src->src)."""
    return [SP[i][1] for i in range(len(SP) - 1) if SP[i][2] == "src" and SP[i + 1][2] == "src"]
