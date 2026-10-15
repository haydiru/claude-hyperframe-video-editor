"""EDL v2 (after the user's review): tighter, review-driven.

Changes from v1:
- Pauses are found down to 0.20 s and classified by the punctuation of the word
  before them (plain Whisper on the source). Hesitations INSIDE a phrase are cut to
  ~0.11 s (they read as "macet"); commas keep ~0.20 s; sentence ends 0.30-0.42 s.
- Reviewed false starts/stammers from the literal CTC pass are added to
  work/edl/approved_cuts.json.
- "Breather" HOLD segments are inserted at section turns: the picture holds the last
  frame (hidden under a full-screen chapter card) and the audio gets room tone, so
  music and SFX can carry a beat of motion before the next point, like the reference.

Writes work/edl/edl.json with ordered `segments` ({t:src,a,b} frames | {t:hold,f,n}),
work/audio/cut_48k.wav, work/edl/decisions.md.
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
FPS, SR = 30, 48000
SPF = SR // FPS

P = {"silence_db": -52.0, "min_pause": 0.20,
     "mid": (0.15, 0.08), "comma": (0.24, 0.13), "sentence": (0.32, 0.19),
     "long_bonus": 0.12, "head_pad": 0.30, "tail_pad": 0.80, "xfade": 0.010}

# section-turn breathers: (source time inside the pause, seconds, tag)
# keyed by the END of the last word before the turn (CTC); the hold goes into the
# first silent run after it, so it never splits a phrase
INSERTS = [(37.41, 2.2, "title"), (59.99, 2.8, "ch1"), (144.26, 2.8, "ch2"),
           (380.99, 2.8, "ch3"), (464.26, 2.8, "ch4")]


def envelope_db(x, hop=0.005, win=0.020):
    h, w = int(SR * hop), int(SR * win)
    n = 1 + (len(x) - w) // h
    idx = np.arange(w)[None, :] + h * np.arange(n)[:, None]
    return 20 * np.log10(np.sqrt(np.mean(x[idx] ** 2, axis=1) + 1e-12)), hop


def pauses(db, hop):
    q = db < P["silence_db"]
    out, i = [], 0
    while i < len(q):
        if q[i]:
            j = i
            while j < len(q) and q[j]:
                j += 1
            s, e = i * hop, j * hop + 0.020
            if e - s >= P["min_pause"]:
                out.append((s, e))
            i = j
        else:
            i += 1
    return out


def snap_min(db, hop, t, radius=0.06):
    i0, i1 = max(0, int((t - radius) / hop)), min(len(db) - 1, int((t + radius) / hop))
    return (i0 + int(np.argmin(db[i0:i1 + 1]))) * hop + 0.010


def main():
    audio, sr = sf.read(ROOT / "work/audio/raw_48k.wav", dtype="float32", always_2d=True)
    mono = audio.mean(1)
    dur = len(mono) / SR
    db, hop = envelope_db(mono)
    wp = json.loads((ROOT / "work/asr_plain_source.json").read_text(encoding="utf-8"))   # punctuation
    ctc = json.loads((ROOT / "work/ctc_source_words.json").read_text())                   # timing
    first, last = ctc[0][1], ctc[-1][2]

    # punctuation from every transcript we have (each alone is sparse), on the
    # source timeline; v1 cut transcript is mapped back through the v1 EDL
    marks = []
    for f, off in (("work/transcript_raw.json", 0.2), ):
        for w in json.loads((ROOT / f).read_text(encoding="utf-8"))["words"]:
            marks.append((w["start"] + off, w["text"].strip()))
    for w in wp:
        marks.append((w["s"] + 0.2, w["w"].strip()))
    v1 = json.loads((ROOT / "work/archive/edl_v1.json").read_text())
    ks = v1["keep_seconds"]

    def o2s(t):
        acc = 0.0
        for a, b in ks:
            if t <= acc + (b - a):
                return a + (t - acc)
            acc += b - a
        return None
    for w in json.loads((ROOT / "work/asr_plain_cut.json").read_text(encoding="utf-8")):   # v1 cut timeline
        st = o2s(w["s"] + 0.2)
        if st is not None:
            marks.append((st, w["w"].strip()))
    marks.sort()
    MARKERS = ("nah", "na", "kalau", "tapi", "lalu", "jadi", "yuk", "kedua", "ketiga", "mungkin", "sekarang",
               "artinya", "padahal", "kemudian", "setelah", "misalnya", "contoh", "karena", "jawabannya", "langkah")

    def kind(ps, pe):
        before = [t for s0, t in marks if ps - 1.2 < s0 < ps]
        tail = [t for t in before[-3:]]
        if any(t.endswith((".", "?", "!")) for t in tail[-2:]):
            return "sentence", tail[-1] if tail else ""
        if any(t.endswith(",") for t in tail[-2:]):
            return "comma", tail[-1]
        nxt = [t for s0, t in marks if pe - 0.1 < s0 < pe + 0.6]
        if nxt and nxt[0].lower().strip(",.") in MARKERS:
            return "comma", (tail[-1] if tail else "") + " | " + nxt[0]
        return "mid", tail[-1] if tail else ""

    deletes, stats = [(0.0, first - P["head_pad"], "head")], {"mid": 0, "comma": 0, "sentence": 0}
    deletes.append((min(dur, last + P["tail_pad"]), dur, "tail"))
    for s, e in pauses(db, hop):
        if e <= first or s >= last:
            continue
        L = e - s
        k, txt = kind(s, e)
        keep, tail = P[k]
        if k == "sentence":
            keep = min(keep + P["long_bonus"], keep + 0.06 * max(0, L - 0.4))
            tail = keep * 0.6
        if L <= keep + 0.04:
            continue
        a, b = s + tail, e - (keep - tail)
        if b - a > 0.03:
            deletes.append((a, b, f"{k} pause {L:.2f}->{keep:.2f} after '{txt}'"))
            stats[k] += 1

    approved = json.loads((ROOT / "work/edl/approved_cuts.json").read_text(encoding="utf-8"))
    notes = []
    for c in approved["cuts"]:
        a = snap_min(db, hop, c["start"]) if c.get("snap", True) else c["start"]
        b = snap_min(db, hop, c["end"]) if c.get("snap", True) else c["end"]
        deletes.append((a, b, "mistake: " + c["reason"]))
        notes.append({**c, "snapped_start": round(a, 3), "snapped_end": round(b, 3)})

    deletes.sort()
    merged = []
    for a, b, why in deletes:
        if merged and a <= merged[-1][1] + 0.02:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b), merged[-1][2] + " + " + why)
        else:
            merged.append((a, b, why))
    keeps, t = [], 0.0
    for a, b, _ in merged:
        if a > t:
            keeps.append([t, a])
        t = max(t, b)
    if t < dur:
        keeps.append([t, dur])

    fk = []
    for s, e in keeps:
        fs, fe = int(np.floor(s * FPS + 1e-6)), int(np.ceil(e * FPS - 1e-6))
        if fk and fs <= fk[-1][1]:
            fk[-1][1] = max(fk[-1][1], fe)
        elif fe - fs >= 2:
            fk.append([fs, fe])
    fk[-1][1] = min(fk[-1][1], int(np.floor(dur * FPS)))

    # ordered segments with breather holds
    segs = [{"t": "src", "a": a, "b": b} for a, b in fk]
    pz = pauses(db, hop)
    for t_word_end, secs, tag in INSERTS:
        run = next((p for p in pz if p[1] > t_word_end + 0.05 and p[0] >= t_word_end - 0.15), None)
        t_ins = (run[0] + 0.08) if run else t_word_end + 0.1
        f = int(round(t_ins * FPS))
        n = int(round(secs * FPS))
        for i, sg in enumerate(segs):
            if sg["t"] == "src" and sg["a"] < f < sg["b"]:
                segs[i:i + 1] = [{"t": "src", "a": sg["a"], "b": f}, {"t": "hold", "f": f - 1, "n": n, "tag": tag},
                                 {"t": "src", "a": f, "b": sg["b"]}]
                break
        else:   # the point was trimmed away: hold at the join that replaced it
            srcs = [i for i, sg in enumerate(segs) if sg["t"] == "src"]
            for j, i in enumerate(srcs[:-1]):
                if segs[i]["b"] <= f <= segs[srcs[j + 1]]["a"]:
                    segs.insert(i + 1, {"t": "hold", "f": segs[i]["b"] - 1, "n": n, "tag": tag})
                    break

    # room tone: quietest 1 s inside the speech span
    w = SR
    best, bi = 1e9, None
    for k0 in range(int((first + 5) * SR), int((last - 5) * SR) - w, SR // 4):
        r = float(np.sqrt(np.mean(mono[k0:k0 + w] ** 2)))
        if r < best and r > 1e-6:
            best, bi = r, k0
    tone = audio[bi:bi + w]

    def room(n):
        out = np.zeros((n, audio.shape[1]), np.float32)
        pos, fade = 0, int(0.05 * SR)
        ramp = np.linspace(0, 1, fade, dtype=np.float32)[:, None]
        while pos < n:
            chunk = tone.copy()
            chunk[:fade] *= ramp
            chunk[-fade:] *= ramp[::-1]
            m = min(len(chunk), n - pos)
            out[pos:pos + m] += chunk[:m]
            pos += len(chunk) - fade
        return out

    parts = []
    for sg in segs:
        if sg["t"] == "src":
            parts.append(audio[sg["a"] * SPF:sg["b"] * SPF])
        else:
            parts.append(room(sg["n"] * SPF))
    out = np.concatenate(parts).astype(np.float32)
    # 10 ms centred crossfades at src->src joins (holds already fade in/out)
    hx = int(P["xfade"] * SR) // 2
    th = np.linspace(0, np.pi / 2, 2 * hx, dtype=np.float32)
    f_in, f_out = np.sin(th)[:, None], np.cos(th)[:, None]
    pos = 0
    for i in range(len(segs) - 1):
        a, b = segs[i], segs[i + 1]
        pos += (a["b"] - a["a"] if a["t"] == "src" else a["n"]) * SPF
        if a["t"] == "src" and b["t"] == "src":
            A = audio[a["b"] * SPF - hx:a["b"] * SPF + hx]
            B = audio[b["a"] * SPF - hx:b["a"] * SPF + hx]
            if len(A) == len(B) == 2 * hx:
                out[pos - hx:pos + hx] = A * f_out + B * f_in
        elif a["t"] == "src" and b["t"] == "hold":     # fade speech tail into room tone
            out[pos - hx:pos] *= np.linspace(1, 0, hx, dtype=np.float32)[:, None]
        elif a["t"] == "hold" and b["t"] == "src":
            out[pos:pos + hx] *= np.linspace(0, 1, hx, dtype=np.float32)[:, None]
    sf.write(ROOT / "work/audio/cut_48k.wav", out, SR, subtype="PCM_24")

    out_frames = sum((s["b"] - s["a"]) if s["t"] == "src" else s["n"] for s in segs)
    holds, t_out = [], 0
    for s in segs:
        if s["t"] == "hold":
            holds.append({"tag": s["tag"], "start": round(t_out / FPS, 3), "dur": round(s["n"] / FPS, 3)})
        t_out += (s["b"] - s["a"]) if s["t"] == "src" else s["n"]
    edl = {"version": 2, "fps": FPS, "source": "raw/A001_10032154_C025_landscape.mov",
           "source_duration": round(dur, 3), "output_frames": out_frames,
           "output_duration": round(out_frames / FPS, 3), "segments": segs, "holds": holds,
           "keep_frames": [[s["a"], s["b"]] for s in segs if s["t"] == "src"],
           "deletes": [{"start": round(a, 3), "end": round(b, 3), "why": why} for a, b, why in merged],
           "params": {k: v for k, v in P.items()}, "mistake_cuts": notes, "pause_trims": stats}
    (ROOT / "work/edl/edl.json").write_text(json.dumps(edl, indent=1), encoding="utf-8")
    md = ["# Edit decisions (v2)\n",
          f"- Source {dur:.2f}s -> output {out_frames / FPS:.2f}s ({len([s for s in segs if s['t'] == 'src'])} source segments, {len(holds)} breathers)",
          f"- Pause trims: {stats}  mistake cuts: {len(notes)}",
          "- Breathers (output time): " + ", ".join(f"{h['tag']} @{h['start']}s {h['dur']}s" for h in holds) + "\n",
          "## Mistake cuts (source time)\n"] + [f"- {n['snapped_start']:.2f}-{n['snapped_end']:.2f}  {n['reason']}" for n in notes]
    (ROOT / "work/edl/decisions.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md[:4]))


if __name__ == "__main__":
    main()
