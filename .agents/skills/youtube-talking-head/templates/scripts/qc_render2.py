"""QC for a rendered MP4: black/empty frames, speaker presence vs. the plate,
contiguous strips over every transition window, audio loudness/true-peak, and
A/V sync (render audio vs. voice master cross-correlation).

  python scripts/qc_render2.py renders/nota-bocor_v2_final.mp4   (v2 beat/camera records)
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
REN = ROOT / sys.argv[1]
OUT = ROOT / "work" / "qc" / REN.stem
OUT.mkdir(parents=True, exist_ok=True)
beats = json.loads((ROOT / "work/beats_v2.json").read_text())
# v2 op = [t, kind, frame, dur, ease]
ops = [[o[1], o[0], o[2], o[3]] for o in json.loads((ROOT / "work/camera_ops_v2.json").read_text())]
report = {}

# --- 1. per-frame luma at low res (black frames / pops)
W, H = 160, 90
p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(REN), "-vf", f"scale={W}:{H},format=gray",
                      "-f", "rawvideo", "-"], stdout=subprocess.PIPE)
lum, prev, pops, edges = [], None, [], []
diffs = []
while True:
    b = p.stdout.read(W * H)
    if len(b) < W * H:
        break
    f = np.frombuffer(b, np.uint8).astype(np.float32)
    lum.append(float(f.mean()))
    g = f.reshape(H, W)
    if f.mean() > 20 and min(g[:, :2].mean(), g[:, -2:].mean(), g[:2, :].mean(), g[-2:, :].mean()) < 2.5:
        edges.append(len(lum) - 1)
    if prev is not None:
        diffs.append(float(np.abs(f - prev).mean()))
    prev = f
p.wait()
lum = np.array(lum)
diffs = np.array(diffs)
report["frames"] = len(lum)
report["black_frames(<12)"] = [round(i / 30, 2) for i in np.where(lum < 12)[0][:50]]
# a pop = a frame unlike both neighbours (spike up then back down)
for i in range(1, len(diffs) - 1):
    if diffs[i] > 14 and diffs[i + 1] > 14 and abs(lum[i + 1] - lum[i]) > 8 and abs(lum[i + 2] - lum[i]) < 3:
        pops.append(round((i + 1) / 30, 2))
report["single_frame_pops"] = pops[:50]
report["frames_with_black_edge"] = [round(i / 30, 2) for i in edges[:50]]

# --- 2. contiguous strips over transition windows
wins = set()
for b in beats:
    if b["cam"] in ("side_l", "side_r", "full"):
        wins.add(round(b["start"], 2))
        wins.add(round(b["end"] - 0.6, 2))
for o in ops:
    if o[0] == "to":
        wins.add(round(o[1], 2))
wins = sorted(w for w in wins if 0 < w < len(lum) / 30 - 1)
for k, t in enumerate(wins):
    a = max(0, int(t * 30) - 6)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a / 30:.3f}", "-i", str(REN), "-frames:v", "36",
                    "-vf", "scale=320:180,tile=6x6", "-frames:v", "1", str(OUT / f"strip_{k:03d}_{t:07.2f}.jpg")])
report["strip_windows"] = len(wins)

# --- 3. audio loudness / true peak
r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(REN), "-af", "ebur128=peak=true", "-f", "null", "-"],
                   capture_output=True, text=True).stderr
summ = r[r.rfind("Summary:"):]
report["loudness_summary"] = " ".join(summ.split())[:300]

# --- 4. A/V sync vs voice master
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(REN), "-vn", "-ac", "1", "-ar", "8000",
                str(OUT / "render_8k.wav")])
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(ROOT / "assets/audio/voice_master.wav"), "-ac", "1", "-ar", "8000",
                str(OUT / "voice_8k.wav")])
x, _ = sf.read(OUT / "render_8k.wav")
y, _ = sf.read(OUT / "voice_8k.wav")
offs = []
for c in (30, 150, 300, 450):
    seg_y = y[c * 8000:(c + 8) * 8000]
    seg_x = x[(c - 1) * 8000:(c + 9) * 8000]
    cc = np.correlate(seg_x - seg_x.mean(), seg_y - seg_y.mean(), "valid")
    offs.append(round((int(np.argmax(cc)) - 8000) / 8, 1))
report["av_offset_ms_at_30_150_300_450"] = offs

# --- 5. picture sync: render frame n vs plate frames n-3..n+3 (WIDE camera, no overlay)
def cam_at(t):
    st = "WIDE"
    for o in ops:
        if o[1] <= t:
            st = o[2]
    return st


def active(t):
    return any(b["start"] - 0.2 <= t <= b["end"] + 0.2 for b in beats)


cands = [t for t in np.arange(5, len(lum) / 30 - 5, 0.5) if cam_at(t) == "WIDE" and not active(t)
         and not any(abs(o[1] - t) < 1.0 for o in ops)]
picks = cands[:: max(1, len(cands) // 6)][:6]


def grab(path, n, scale_src):
    vf = f"select=eq(n\\,{n}),scale={scale_src},crop=240:150:120:30,format=gray"
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vf", vf, "-frames:v", "1", "-f", "rawvideo", "-"],
                       capture_output=True)
    return np.frombuffer(r.stdout, np.uint8).astype(np.float32)


sync = []
for t in picks:
    n = int(round(t * 30))
    rf = grab(REN, n, "480:270")
    errs = {}
    for d in range(-3, 4):
        pf = grab(ROOT / "work/plate/plate_cut_video.mp4", n + d, "480:270")
        if len(pf) == len(rf) and len(rf):
            errs[d] = float(np.abs(rf - pf).mean())
    if errs:
        sync.append((round(float(t), 1), min(errs, key=errs.get), round(min(errs.values()), 2)))
report["picture_sync(t, best_frame_offset, err)"] = sync

(OUT / "report.json").write_text(json.dumps(report, indent=1))
print(json.dumps(report, indent=1))
