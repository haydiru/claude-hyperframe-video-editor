"""Visual jump at every src->src join of the v2 cut plate, and 4 chunk bounds.

work/edl/join_jumps.json   {"median_motion", "joins": [{frame, t, jump, ratio}]}
work/plate/chunk_bounds.json   [0, b1, b2, b3, total]

Chunk bounds sit in the middle of a breather hold where possible (a chapter card
covers the frozen frame, so the hand-over between two <video> chunks is unseen);
otherwise on the join nearest to the quarter mark.
"""
import json
import subprocess
from pathlib import Path

import numpy as np

import edl_map as M

ROOT = Path(__file__).resolve().parents[1]
E = M.E
FPS = M.FPS
W, H = 320, 180
p = subprocess.Popen(["ffmpeg", "-v", "error", "-hwaccel", "cuda", "-i", str(ROOT / "work/plate/plate_cut_video.mp4"),
                      "-vf", f"scale={W}:{H},format=gray", "-f", "rawvideo", "-"], stdout=subprocess.PIPE)
frames = []
while True:
    b = p.stdout.read(W * H)
    if len(b) < W * H:
        break
    frames.append(np.frombuffer(b, np.uint8).astype(np.float32))
F = np.stack(frames)
total = len(F)
assert total == E["output_frames"], (total, E["output_frames"])
d = np.abs(np.diff(F, axis=0)).mean(1)          # d[i] = change between frame i and i+1
res = []
for t in M.joins():
    j = int(round(t * FPS))
    jump = d[j - 1]
    local = np.median(d[max(0, j - 15):j - 2])
    res.append({"frame": j, "t": round(j / FPS, 3), "jump": round(float(jump), 2),
                "ratio": round(float(jump / (local + 1e-3)), 1)})
(ROOT / "work/edl/join_jumps.json").write_text(json.dumps({"median_motion": float(np.median(d)), "joins": res}, indent=1))

holds = [int(round((h["start"] + h["dur"] / 2) * FPS)) for h in E["holds"]]
cands = holds + [r["frame"] for r in res]
bounds = [0]
for q in (1, 2, 3):
    target = total * q / 4
    near_hold = [h for h in holds if abs(h - target) < total * 0.09]
    pick = min(near_hold, key=lambda f: abs(f - target)) if near_hold else min(cands, key=lambda f: abs(f - target))
    bounds.append(pick)
bounds.append(total)
(ROOT / "work/plate/chunk_bounds.json").write_text(json.dumps(bounds))
print("frames", total, "joins", len(res), "bounds", bounds, [round((b - a) / FPS, 2) for a, b in zip(bounds, bounds[1:])])
big = sorted(res, key=lambda r: -r["jump"])[:8]
print("largest jumps:", [(r["t"], r["jump"]) for r in big])
