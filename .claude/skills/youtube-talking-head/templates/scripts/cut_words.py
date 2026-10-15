"""Literal CTC words + 20 ms envelope for windows of the CUT audio (final timeline)."""
import sys
import numpy as np, soundfile as sf, scipy.signal as ss, torch
import ctc_check as C
from pathlib import Path
R = Path(__file__).resolve().parents[1]
a, _ = sf.read(R / "work/audio/cut_48k.wav", dtype="float32", always_2d=True)
m48 = a.mean(1)
x16 = ss.resample_poly(m48, 1, 3).astype(np.float32)
blank = C.proc.tokenizer.pad_token_id
for arg in sys.argv[1:]:
    s, e = map(float, arg.split(":"))
    seg = x16[int(s * 16000):int(e * 16000)]
    inp = C.proc(seg, sampling_rate=16000, return_tensors="pt").input_values.to("cuda")
    with torch.no_grad():
        ids = C.model(inp).logits[0].argmax(-1).cpu().numpy()
    step = (e - s) / len(ids)
    words, cur, t0, prev = [], "", None, None
    for i, t in enumerate(ids):
        if t != prev and t != blank:
            c = C.proc.tokenizer.convert_ids_to_tokens(int(t))
            if c == "|":
                if cur: words.append(f"{cur}@{t0:.2f}")
                cur = ""
            else:
                if not cur: t0 = s + i * step
                cur += c
        prev = t
    if cur: words.append(f"{cur}@{t0:.2f}")
    print(f"== {s}-{e}: " + " ".join(words))
    line = ""
    for k in range(int((e - s) / 0.02)):
        y = m48[int((s + k * 0.02) * 48000):int((s + (k + 1) * 0.02) * 48000)]
        d = 20 * np.log10(np.sqrt((y ** 2).mean()) + 1e-9)
        line += " " if d < -56 else ("." if d < -45 else ("o" if d < -35 else "O"))
    for r in range(0, len(line), 100):
        print(f"   {s + r * 0.02:7.2f} |{line[r:r + 100]}|")
