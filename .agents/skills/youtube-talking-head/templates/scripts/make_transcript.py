"""Transcript of the CUT audio (final timeline) for anchors, captions and SRT.

Text: plain faster-whisper large-v3 on work/audio/cut_48k.wav.
Timing: literal wav2vec2 CTC pass on the same audio (Whisper starts run ~0.2 s
early); matched words take CTC start - 50 ms, unmatched take Whisper + 180 ms.
Brand names and verified mishearings are corrected by token-sequence rules.
"""
import difflib
import json
import re
import sys
from pathlib import Path

import numpy as np
import scipy.signal as ss
import soundfile as sf
import torch  # noqa: F401
from faster_whisper import WhisperModel

import ctc_check as C

ROOT = Path(__file__).resolve().parents[1]
a, _ = sf.read(ROOT / "work/audio/cut_48k.wav", dtype="float32", always_2d=True)
x16 = ss.resample_poly(a.mean(1), 1, 3).astype(np.float32)
dur = len(x16) / 16000

CACHE = ROOT / "work/asr_cache_v2.json"
if "--reuse" in sys.argv and CACHE.exists():
    # text rules only: reuse the Whisper + CTC words of the same cut audio
    ww, cw = (lambda c: (c["whisper"], c["ctc"]))(json.loads(CACHE.read_text(encoding="utf-8")))
else:
    m = WhisperModel("large-v3", device="cuda", compute_type="float16")
    segs, _ = m.transcribe(x16, language="id", word_timestamps=True, beam_size=5,
                           condition_on_previous_text=False, vad_filter=True)
    ww = [{"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3)} for sg in segs for w in sg.words]
    (ROOT / "work/asr_plain_cut_v2.json").write_text(json.dumps(ww, ensure_ascii=False), encoding="utf-8")

    blank = C.proc.tokenizer.pad_token_id
    cw, s = [], 0.0
    while s < dur:
        e = min(s + 20, dur)
        seg = x16[int(s * 16000):int(e * 16000)]
        inp = C.proc(seg, sampling_rate=16000, return_tensors="pt").input_values.to("cuda")
        with torch.no_grad():
            ids = C.model(inp).logits[0].argmax(-1).cpu().numpy()
        step = (e - s) / len(ids)
        cur, t0, tl, prev = "", None, None, None
        for i, t in enumerate(ids):
            if t != prev and t != blank:
                ch = C.proc.tokenizer.convert_ids_to_tokens(int(t))
                tt = s + i * step
                if ch == "|":
                    if cur:
                        cw.append({"w": cur, "s": t0, "e": tl + 0.04})
                    cur = ""
                else:
                    if not cur:
                        t0 = tt
                    cur += ch
                    tl = tt
            prev = t
        if cur:
            cw.append({"w": cur, "s": t0, "e": tl + 0.04})
        s = e

    # Whisper sometimes drops a whole phrase; CTC does not. Re-transcribe such gaps.
    patched = []
    for i in range(len(ww) - 1):
        g0, g1 = ww[i]["e"], ww[i + 1]["s"]
        if g1 - g0 > 2.5 and sum(1 for c in cw if g0 + 0.2 < c["s"] < g1 - 0.2) >= 4:
            w0, w1 = max(0, g0 - 0.3), g1 + 0.3
            ps, _ = m.transcribe(x16[int(w0 * 16000):int(w1 * 16000)], language="id", word_timestamps=True,
                                 beam_size=5, condition_on_previous_text=False, vad_filter=False)
            add = [{"w": w.word.strip(), "s": round(w0 + w.start, 3), "e": round(w0 + w.end, 3)}
                   for sg in ps for w in sg.words if g0 - 0.05 < w0 + w.start < g1]
            patched.append((g0, g1, " ".join(a["w"] for a in add)))
            ww.extend(add)
    ww.sort(key=lambda w: w["s"])
    for p in patched:
        print("patched gap %.2f-%.2f: %s" % p)
    CACHE.write_text(json.dumps({"whisper": ww, "ctc": cw}, ensure_ascii=False), encoding="utf-8")

norm = lambda t: "".join(ch for ch in t.lower() if ch.isalpha())
A, B = [norm(w["w"]) for w in ww], [norm(w["w"]) for w in cw]
match = {}
for blk in difflib.SequenceMatcher(a=A, b=B, autojunk=False).get_matching_blocks():
    for k in range(blk.size):
        match[blk.a + k] = blk.b + k

SAFE = {"Cloudy": "Claude", "Cloud": "Claude", "klode": "Claude", "Klode": "Claude", "versel": "Vercel",
        "Versel": "Vercel", "sendit": "Xendit", "Sendit": "Xendit", "Place": "Flash", "place": "Flash",
        "sebakau": "sembako", "Pohok": "pokok", "pohok": "pokok", "katon": "karton", "pemasuk": "pemasok",
        "sepeleh": "sepele", "sepeleh,": "sepele,", "rejainnya": "kerjainnya", "topo": "toko", "seles": "sales",
        "sarbu": "sabun", "sarbun": "sabun", "juaranya": "jualannya", "nocokin": "nyocokin", "dilamati": "nyelamatin",
        "ngerjai": "ngerjain", "hidupan": "di depan", "perutir": "operasional", "melurui": "merupakan",
        "brosir,": "grosir,", "brosir": "grosir", "Supabes": "Supabase", "kursor": "Cursor", "kursor.": "Cursor.",
        "lecet,": "lecek,", "buk": "Bu,", "klontong": "kelontong", "pembisnis.": "pebisnis.", "Model": "Modal",
        "Midtrends": "Midtrans", "Midtrend": "Midtrans", "topo.": "toko.", "sarbun,": "sabun,", "distribusor,": "distributor,"}
SEQ = [(["mid", "-range"], ["Midtrans"]), (["mid", "-trans"], ["Midtrans"]), (["Midtrend"], ["Midtrans"]),
       (["kertas", "not", "tak"], ["kertas", "nota"]), (["nafas", "kasir"], ["pas", "kasir"]),
       (["sama", "temukan", "kertas"], ["sama", "tumpukan", "kertas"]), (["seper", "bulanannya"], ["operasional", "bulanannya"]),
       (["kasir", "kasir", "jam"], ["kasir.", "Jam"]), (["pertama", "pertama"], ["pertama."]),
       # Whisper doubles a word at some joins; CTC on the cut audio hears it once (cut_words.py)
       (["kasir", "kasir", "padahal"], ["kasir,", "padahal"]), (["aplikasinya", "aplikasinya"], ["aplikasinya"]),
       (["paling", "paling"], ["paling"]), (["sekitar", "sekitar"], ["sekitar"]), (["saja", "saja"], ["saja"]),
       (["kalau", "kalau"], ["kalau"]), (["dulu", "dulu", "ceritain"], ["dulu.", "Ceritain"]),
       # verified mishearings
       (["kebocoran", "khas"], ["kebocoran", "kas"]), (["si", "jam"], ["Jam"]),
       (["lsd", "sub", "-store"], ["sales", "distributor,"]), (["ide", "sopir"], ["ide", "software"]),
       (["menuruti"], ["merupakan"]), (["seperut"], ["operasional"]), (["hadir", "hasil"], ["hasil"]),
       (["ngantungin"], ["ngantongin"]), (["tentu", "retail"], ["Kan", "toko", "retail"]),
       # re-checked with CTC + a windowed Whisper pass (unclear syllable before "kasir" dropped)
       (["ke", "om", "nah"], ["ke", "kasir.", "Nah,"]), (["kasir", "hasil", "foto"], ["kasir", "foto"]),
       (["katon"], ["karton,"])]

out = []
for i, w in enumerate(ww):
    t = SAFE.get(w["w"], w["w"])
    if i in match:
        c = cw[match[i]]
        st = max(0, c["s"] - 0.05)
        en = max(st + 0.08, c["e"])
    else:
        st, en = w["s"] + 0.18, w["e"] + 0.18
    out.append({"text": t, "start": round(st, 3), "end": round(en, 3)})
# words that ASR parked inside a silent breather (or just before it) belong after it:
# move them to the first voiced frames after the hold, in order
E = json.loads((ROOT / "work/edl/edl.json").read_text())
mono = a.mean(1)
def voiced(t):
    seg = mono[int(t * 48000):int((t + 0.12) * 48000)]
    return len(seg) and 20 * np.log10(np.sqrt((seg ** 2).mean()) + 1e-9) > -50
for h in E.get("holds", []):
    h0, h1 = h["start"], h["start"] + h["dur"]
    # verified by CTC + envelope: these words are spoken AFTER the breather
    names = {"title": ["Nah", "di"], "ch1": ["Yuk"], "ch2": ["Nah,"], "ch3": ["Nah,"], "ch4": ["mungkin", "Mungkin"]}
    idx = [k for k, o in enumerate(out) if h0 - 1.0 <= o["start"] < h1 + 0.5 and o["text"] in names.get(h["tag"], [])]
    idx = [k for k in idx if out[k]["start"] < h1 or not voiced(out[k]["start"])]
    if not idx:
        continue
    t = h1
    while t < h1 + 3 and not voiced(t):
        t += 0.01
    for n, k in enumerate(idx):
        out[k]["start"] = round(t + 0.12 * n, 3)
        out[k]["end"] = round(t + 0.12 * (n + 1), 3)
    print("moved", [out[k]["text"] for k in idx], "after", h["tag"], "to", round(t, 2))
out.sort(key=lambda o: o["start"])
for k in range(1, len(out)):
    if out[k]["start"] < out[k - 1]["start"]:
        out[k]["start"] = out[k - 1]["start"]
    if out[k - 1]["end"] > out[k]["start"]:
        out[k - 1]["end"] = out[k]["start"]
# token-sequence fixes run on the final order (gap-patched words interleave before the sort)
toks = [o["text"] for o in out]
for pat, rep in SEQ:
    i = 0
    while i <= len(toks) - len(pat):
        if [t.lower().strip(",.") for t in toks[i:i + len(pat)]] == [p.lower() for p in pat]:
            st, en = out[i]["start"], out[i + len(pat) - 1]["end"]
            new = [{"text": r, "start": st, "end": en} for r in rep]
            out[i:i + len(pat)] = new
            toks[i:i + len(pat)] = rep
        i += 1
(ROOT / "assets/transcript.json").write_text(json.dumps(
    {"text": " ".join(o["text"] for o in out), "language": "id", "audio_duration_secs": round(dur, 3),
     "timing": "plain faster-whisper large-v3 text on the cut audio; CTC (wav2vec2) starts for matched words",
     "words": out}, ensure_ascii=False, indent=0), encoding="utf-8")
print(len(out), "words; matched", len(match), "; duration", round(dur, 2))
line, t0 = [], None
for o in out:
    if t0 is None:
        t0 = o["start"]
    line.append(o["text"])
    if re.search(r"[.?!]$", o["text"]) or len(line) >= 18:
        print(f"{t0:6.1f} {' '.join(line)}")
        line, t0 = [], None
if line:
    print(f"{t0:6.1f} {' '.join(line)}")
