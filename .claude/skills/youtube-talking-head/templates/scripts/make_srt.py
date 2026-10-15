"""YouTube closed captions (Bahasa Indonesia) from assets/transcript.json, on the
final edited timeline. Max 2 lines x 42 chars, 1-6 s per cue, breaks at
punctuation where possible."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
W = json.loads((ROOT / "assets/transcript.json").read_text(encoding="utf-8"))["words"]

# merge ASR token splits: "gara -gara" -> "gara-gara", "1 ,5" -> "1,5", "10 %" -> "10%"
# text corrections live in make_transcript.py (SAFE/SEQ); only spelling leftovers here
FIX = {"sepeleh,": "sepele,", "sepeleh": "sepele", "klontong": "kelontong", "lecet,": "lecek,"}
for w in W:
    w["text"] = FIX.get(w["text"], w["text"])
W = [w for w in W if w["text"]]
toks = []
for w in W:
    t = w["text"]
    if toks and (re.match(r"^-\w", t) or re.match(r"^,\d", t) or t == "%"):
        toks[-1]["text"] += t
        toks[-1]["end"] = w["end"]
    else:
        toks.append(dict(w))

cues, cur = [], []


def flush():
    if cur:
        cues.append((cur[0]["start"], cur[-1]["end"], " ".join(x["text"] for x in cur)))
        cur.clear()


for w in toks:
    if cur:
        text = " ".join(x["text"] for x in cur + [w])
        long = len(text) > 84 or w["end"] - cur[0]["start"] > 6.0
        gap = w["start"] - cur[-1]["end"] > 0.6 and (len(cur) >= 4 or re.search(r"[.?!,]$", cur[-1]["text"]) and len(cur) >= 3)
        if long or gap:
            flush()
    cur.append(w)
    if re.search(r"[.?!]$", w["text"]) and w["end"] - cur[0]["start"] > 1.0:
        flush()
flush()


def wrap(s):
    if len(s) <= 42:
        return s
    words = s.split()
    best, bi = 1e9, 1
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        cost = abs(len(a) - len(b)) + (0 if a.endswith((",", ".")) else 6)
        if max(len(a), len(b)) <= 46 and cost < best:
            best, bi = cost, i
    return " ".join(words[:bi]) + "\n" + " ".join(words[bi:])


def ts(t):
    h, r = divmod(max(0, t), 3600)
    m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}"


out = []
for i, (s, e, text) in enumerate(cues, 1):
    e = max(e, s + 1.0)
    if i < len(cues):
        e = min(e, cues[i][0] - 0.02)
    prev = cues[i - 2][2] if i > 1 else "."
    if re.search(r"[.?!]$", prev):
        text = text[0].upper() + text[1:]
    out.append(f"{i}\n{ts(s)} --> {ts(e)}\n{wrap(text)}\n")
dst = ROOT / "renders" / "nota-bocor.id.srt"
dst.parent.mkdir(exist_ok=True)
dst.write_text("\n".join(out), encoding="utf-8")
print(len(cues), "cues ->", dst)
