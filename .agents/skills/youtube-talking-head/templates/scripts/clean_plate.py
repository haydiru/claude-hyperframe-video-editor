"""Per-pixel temporal median of the chair-ear zones (the chair behind the
speaker's shoulders). The camera and chair are static, so the median of frames
sampled across the whole take is the empty chair. plate.py removes only pixels
that still look like this clean plate AND are chair-coloured, so a hand or the
shirt moving through the zone is never keyed out.
"""
import json
from pathlib import Path

import numpy as np

import plate as P

ROOT = Path(__file__).resolve().parents[1]
zones = P.CFG["chair_zones"]
stacks = {z["name"]: [] for z in zones}
p = P.decoder(fps="1/1.5")
i = 0
while True:
    f = P.read_frame(p)
    if f is None:
        break
    if True:                              # decoder already samples 1 per 1.5 s
        a = f.numpy()
        for z in zones:
            x0, y0, x1, y1 = z["box"]
            stacks[z["name"]].append(a[y0:y1, x0:x1].copy())
    i += 1
p.wait()
out = ROOT / "work" / "bg"
for name, s in stacks.items():
    med = np.median(np.stack(s), axis=0).astype(np.uint8)
    np.save(out / f"clean_{name}.npy", med)
    import cv2
    cv2.imwrite(str(out / f"clean_{name}.png"), med[..., ::-1])
    print(name, len(s), "samples")
