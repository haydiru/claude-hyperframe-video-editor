"""Apply the frame-grid EDL to the full plate: decode every frame, keep only
EDL frames, re-encode. Frame-exact, matching the audio master sample-for-sample
(1600 samples per frame)."""
import json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
W, H = 2560, 1440
FB = W * H * 3 // 2
edl = json.loads((ROOT / "work/edl/edl.json").read_text())
keep = set()
hold_after = {}
for sg in edl.get("segments", [{"t": "src", "a": a, "b": b} for a, b in edl["keep_frames"]]):
    if sg["t"] == "src":
        keep.update(range(sg["a"], sg["b"]))
    else:
        hold_after[sg["f"]] = hold_after.get(sg["f"], 0) + sg["n"]
src = ROOT / "work/plate/plate_full.mp4"
out = ROOT / sys.argv[1] if len(sys.argv) > 1 else ROOT / "work/plate/plate_cut_video.mp4"
dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(src), "-f", "rawvideo", "-pix_fmt", "yuv420p", "-"],
                       stdout=subprocess.PIPE, bufsize=FB * 4)
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "yuv420p",
                        "-s", f"{W}x{H}", "-r", "30", "-color_range", "tv", "-colorspace", "bt709", "-i", "-",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-tune", "film",
                        "-pix_fmt", "yuv420p", "-g", "30", "-color_primaries", "bt709", "-color_trc", "bt709",
                        "-colorspace", "bt709", "-color_range", "tv", "-movflags", "+faststart", str(out)],
                       stdin=subprocess.PIPE, bufsize=FB * 4)
n = kept = 0
while True:
    b = dec.stdout.read(FB)
    if len(b) < FB:
        break
    if n in keep:
        enc.stdin.write(b)
        kept += 1
    for _ in range(hold_after.get(n, 0)):      # breather: hold this frame
        enc.stdin.write(b)
        kept += 1
    n += 1
enc.stdin.close(); enc.wait(); dec.wait()
print("read", n, "written", kept, "expected", len(keep) + sum(hold_after.values()), "edl frames", edl.get("output_frames"))
