"""v2 assembly: beat compositions, root index.html with the camera timeline, the
music plan and the SFX event list (then run make_audio2.py and make_mix.sh).

  python scripts/build2.py     (from the project folder)
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hflib2 as H  # noqa: E402
import beats_v2  # noqa: E402,F401

ROOT = H.ROOT
DUR = H.DUR
FPS = 30
BEATS = sorted(H.BEATS, key=lambda b: b.start)
FULLS = [b for b in BEATS if b.cam == "full"]

# ------------------------------------------------------------------ chaining
for a in FULLS:
    if a.chain_out:
        nxt = [s for s in FULLS if s is not a and s.start > a.start + 0.5]
        n = min(nxt, key=lambda s: s.start)
        a.dur = round(n.start + 0.6 - a.start, 3)
for b in BEATS:
    assert b.dur and b.dur > 0.5, (b.id, b.dur)
    b.dur = round(min(b.dur, DUR - b.start), 3)

# ------------------------------------------------------------------ anchor self-check (validator rule)
problems = []
for b in BEATS:
    w = H.at(b.anchor, max(0.0, b.start - 10))
    slack = w - b.start
    if not (-0.2 <= slack <= 1.8):
        problems.append(f"{b.id}: anchor {b.anchor!r} @ {w:.2f}, start {b.start:.2f}, slack {slack:.2f}")
if problems:
    print("ANCHOR WINDOW PROBLEMS:\n  " + "\n  ".join(problems))

# ------------------------------------------------------------------ tracks + z
tracks = {}
for b in BEATS:
    t = 4
    while any(not (b.start >= o.start + o.dur or b.start + b.dur <= o.start) for o in tracks.get(t, [])):
        t += 1
    tracks.setdefault(t, []).append(b)
    b.track = t
for i, b in enumerate(BEATS):
    kind = "full" if b.cam == "full" else ("side" if b.cam in ("side_l", "side_r") else "cap")
    b.z = {"full": 300, "side": 200, "cap": 250}[kind] + i

# ------------------------------------------------------------------ write compositions
TPL = """<template id="{id}-template">
  <div data-composition-id="{id}" data-start="0" data-duration="{dur}" data-width="1920" data-height="1080"
       data-anchor="{anchor}">
    <div class="L">
{html}
    </div>
    <script>
      (() => {{
        window.__timelines = window.__timelines || {{}};
        const R = '[data-composition-id="{id}"]';
        const $ = (s) => s.split(',').map((x) => R + ' ' + x.trim()).join(',');
        const tl = gsap.timeline({{ paused: true }});
{js}
        tl.to({{}}, {{ duration: {dur} }}, 0);
        window.__timelines["{id}"] = tl;
      }})();
    </script>
  </div>
</template>
"""
H.OUT.mkdir(parents=True, exist_ok=True)
for old in H.OUT.glob("*.html"):
    old.unlink()
for b in BEATS:
    html = "\n".join("      " + h for h in b.html)
    if b.wrap == "full":
        html = f'      <div class="take" style="position:absolute;inset:0">\n{html}\n      </div>'
    html = re.sub(r"Rp(?=[\d&])", '<span class="rp">Rp</span>', html)
    js = "\n".join("        " + j for j in b.js)
    js = re.sub(r"__END-(\d+(?:\.\d+)?)__", lambda m: f"{b.dur - float(m.group(1)):.3f}", js)
    assert "__END" not in js and "__END" not in html, b.id
    (H.OUT / f"{b.id}.html").write_text(
        TPL.format(id=b.id, dur=b.dur, anchor=H.esc(b.anchor), html=html, js=js), encoding="utf-8")

# ------------------------------------------------------------------ camera
# The plate is 2560x1440 shown at 1920x1080, so every framing below up to 1.33x is
# still downsampled. Side framings keep the plate edge outside the frame.
FR = {"WIDE": (1.0, 0, 0), "MED": (1.12, 0, 6), "CLOSE": (1.28, 0, 14),
      "SIDE_L": (1.25, -230, 0), "SIDE_R": (1.25, 230, 0)}
JUMPS = json.loads((ROOT / "work/edl/join_jumps.json").read_text())["joins"]
covers = [(b.start + 0.52, b.start + b.dur - 0.5) for b in FULLS]


def cover_at(t, pad=0.0):
    for s, e in covers:
        if s - pad <= t <= e + pad:
            return (s, e)
    return None


def full_starting(t0, t1):
    for b in FULLS:
        if t0 <= b.start <= t1:
            return b
    return None


sides = []
for b in BEATS:
    if b.cam in ("side_l", "side_r"):
        sides.append([b.start, b.start + b.dur, "SIDE_L" if b.cam == "side_l" else "SIDE_R"])
merged = []
for s in sides:
    if merged and merged[-1][2] == s[2] and s[0] <= merged[-1][1] + 1.0:
        merged[-1][1] = max(merged[-1][1], s[1])
    else:
        merged.append(list(s))

ops = []          # (t, kind 'set'|'to', frame, dur, ease)
used_close = set()
busy = []         # intervals where the camera belongs to a side or full


def to(t, fr, d=0.75, ease="power2.inOut"):
    ops.append((round(t, 3), "to", fr, d, ease))


def setf(t, fr):
    ops.append((round(t, 3), "set", fr, 0, ""))


for i, (s, e, fr) in enumerate(merged):
    prev = merged[i - 1] if i else None
    nxt = merged[i + 1] if i + 1 < len(merged) else None
    # ---- enter
    if s < 0.5:
        setf(0, fr)
    elif prev and s - prev[1] < 1.0:
        to(s, fr, 0.9)                                   # pan across from the other side
    elif cover_at(s, 0.35):
        c = cover_at(s, 0.35)
        setf(min(max(s, c[0]), c[1] - 0.02), fr)
    else:
        to(s, fr, 0.75)
    # ---- leave
    if nxt and nxt[0] - e < 1.0:
        busy.append((s, nxt[0]))
        continue
    cl = [c for c in H.CLOSEUPS if e - 0.8 <= c[0] <= e + 1.0]
    fb = full_starting(e - 1.2, e + 0.2)
    if cl and not fb:
        c, hold = cl[0]                                  # cut straight from the side framing into a punch-in
        setf(c - 0.05, "CLOSE")
        to(c + hold, "WIDE", 0.6)
        used_close.add(c)
        busy.append((s, c + hold + 0.6))
    elif fb:
        setf(fb.start + 0.55, "WIDE")
        busy.append((s, fb.start + 0.55))
    else:
        to(e - 0.62, "WIDE", 0.62)
        busy.append((s, e + 0.1))


def is_busy(t):
    return any(a - 0.2 <= t <= b for a, b in busy) or cover_at(t) is not None


def near_op(t, gap):
    """another framing change (or a move still running) within gap seconds"""
    return any(o[0] - gap <= t <= o[0] + o[3] + gap for o in ops)


# after every full card the speaker comes back in a new framing (varies the shots)
for n, b in enumerate(FULLS):
    c = (b.start + 0.52, b.start + b.dur - 0.5)
    if c[1] - c[0] < 0.2:
        continue
    after = c[1] + 0.6
    if any(s - 0.2 <= after <= e for s, e, _ in merged) or near_op(c[1], 0.3):
        continue
    setf(c[1] - 0.05, "MED" if n % 2 == 0 else "WIDE")


def base_before(t):
    cands = [o for o in ops if o[0] <= t and o[2] in ("WIDE", "MED")]
    return max(cands, key=lambda o: o[0])[2] if cands else "WIDE"


# punch-ins on emphasis words: cut in on a join when one is close, else a hard punch
for c, hold in H.CLOSEUPS:
    if c in used_close or is_busy(c) or is_busy(c + hold):
        continue
    joins = [j["t"] for j in JUMPS if c - 0.8 <= j["t"] <= c + 0.3 and not is_busy(j["t"])]
    tc = joins[0] if joins else c - 0.05
    if near_op(tc, 1.2) or near_op(tc + hold, 1.0):
        continue
    back = base_before(tc)
    setf(tc, "CLOSE")
    rel = [j["t"] for j in JUMPS if tc + hold <= j["t"] <= tc + hold + 2.5 and not is_busy(j["t"])]
    if rel:
        setf(rel[0], "MED" if back == "WIDE" else "WIDE")
    else:
        to(tc + hold, back, 0.6, "power2.inOut")
    busy.append((tc - 0.5, (rel[0] if rel else tc + hold + 0.6) + 0.5))

# framing changes hide the larger jump cuts; never closer than 2 s to another change
for j in JUMPS:
    t = j["t"]
    if j["jump"] < 2.6 or is_busy(t) or is_busy(t + 0.3) or near_op(t, 2.0):
        continue
    setf(t, "MED" if base_before(t) == "WIDE" else "WIDE")

ops.sort(key=lambda o: o[0])
cam_js = []
for t, kind, fr, d, ease in ops:
    sc, x, y = FR[fr]
    props = f"scale:{sc},x:{x},y:{y}"
    if kind == "set":
        cam_js.append(f"mainTl.set('#cam',{{{props}}},{t:.3f});")
    else:
        cam_js.append(f"mainTl.to('#cam',{{{props},duration:{d},ease:'{ease}'}},{t:.3f});")

# ------------------------------------------------------------------ root index.html
CB = json.loads((ROOT / "work/plate/chunk_bounds.json").read_text())
PLATES = "\n".join(
    f'        <video id="plate{i + 1}" class="plate" data-start="{CB[i] / FPS:.4f}" '
    f'data-duration="{round(CB[i + 1] / FPS, 4) - round(CB[i] / FPS, 4):.4f}" data-track-index="0" '
    f'src="assets/video/plate_{i + 1}.mp4" muted playsinline></video>'
    for i in range(len(CB) - 1))
mounts = "\n".join(
    f'      <div id="m-{b.id}" class="L" style="z-index:{b.z}" data-composition-id="{b.id}" '
    f'data-composition-src="compositions/beats/{b.id}.html" data-start="{b.start}" data-duration="{b.dur}" '
    f'data-track-index="{b.track}" data-width="1920" data-height="1080"></div>'
    for b in BEATS)
INDEX = f"""<!doctype html>
<html lang="id">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <title>Nota yang Bocor: ide software untuk toko retail</title>
    <link rel="stylesheet" href="assets/fonts2.css" />
    <link rel="stylesheet" href="assets/ui2.css" />
    <script src="assets/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: 1920px; height: 1080px; overflow: hidden; background: #0d0d0e; }}
      #root {{ position: relative; width: 1920px; height: 1080px; overflow: hidden; background: #0d0d0e; }}
      /* non-timed wrapper: the camera. GSAP moves this, never the video. */
      #cam {{ position: absolute; left: 0; top: 0; width: 1920px; height: 1080px; transform-origin: 50% 32%; }}
      .plate {{ position: absolute; left: 0; top: 0; width: 1920px; height: 1080px; object-fit: cover; display: block; }}
      #fade {{ position: absolute; inset: 0; background: #000; opacity: 0; z-index: 2000; pointer-events: none; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="nota-bocor" data-start="0" data-duration="{DUR}" data-width="1920" data-height="1080">
      <div id="cam">
{PLATES}
      </div>
{mounts}
      <div id="fade"></div>
      <!-- one premixed track: voice master + music bed + SFX, -14 LUFS / -1.5 dBTP (scripts/make_mix.sh) -->
      <audio id="mix" data-start="0" data-duration="{DUR}" data-track-index="50" data-volume="1" src="assets/audio/final_mix.wav"></audio>
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      const mainTl = gsap.timeline({{ paused: true }});
      mainTl.set('#cam', {{ scale: 1, x: 0, y: 0 }}, 0);
      {chr(10).join('      ' + j for j in cam_js).lstrip()}
      mainTl.to('#fade', {{ opacity: 1, duration: 0.8, ease: 'power1.in' }}, {DUR - 0.85:.3f});
      mainTl.set({{}}, {{}}, {DUR});
      window.__timelines["nota-bocor"] = mainTl;
    </script>
  </body>
</html>
"""
(ROOT / "index.html").write_text(INDEX, encoding="utf-8")

# ------------------------------------------------------------------ sound: SFX list + music plan
SFX_ABS = []
for bb, rel, kind, gain, extra in H.SFX:
    r = bb.dur - float(rel[4:]) if isinstance(rel, str) else rel
    SFX_ABS.append([round(bb.start + r, 3), kind, gain, extra])
SFX_ABS.sort(key=lambda e: e[0])
(ROOT / "work/sfx_events_v2.json").write_text(json.dumps(SFX_ABS), encoding="utf-8")

cards = sorted([b for b in BEATS if b.id.startswith("k-")], key=lambda b: b.start)
sections, prev, mode = [], 0.0, "intro"
for c in cards:
    sections.append({"start": round(prev, 3), "end": c.start, "mode": mode})
    sections.append({"start": c.start, "end": round(c.hold[1], 3), "mode": "break"})
    prev, mode = c.hold[1], "groove"
outro = round(DUR - 10.5, 3)
sections.append({"start": round(prev, 3), "end": outro, "mode": "groove"})
sections.append({"start": outro, "end": DUR, "mode": "outro"})
stops = [[round(b.start - 0.03, 3), round(b.start + b.dur + 0.12, 3)] for b in BEATS if getattr(b, "whynot", False)]
(ROOT / "work/music_plan.json").write_text(json.dumps({"duration": DUR, "sections": sections, "stops": stops}, indent=1))

# ------------------------------------------------------------------ records
sheet = [{"id": b.id, "start": b.start, "dur": b.dur, "end": round(b.start + b.dur, 3), "anchor": b.anchor,
          "anchor_t": b.anchor_t, "cam": b.cam, "track": b.track} for b in BEATS]
(ROOT / "work/beats_v2.json").write_text(json.dumps(sheet, indent=1), encoding="utf-8")
(ROOT / "work/camera_ops_v2.json").write_text(json.dumps(ops), encoding="utf-8")
side_time = sum(e - s for s, e, _ in merged)
full_time = sum(e - s for s, e in covers)
print(f"beats {len(BEATS)}  side {side_time:.0f}s  full {full_time:.0f}s  camera ops {len(ops)}  "
      f"sfx {len(SFX_ABS)}  dur {DUR}")
gaps, last = [], 0
for b in BEATS:
    if b.start - last > 18:
        gaps.append((round(last, 1), round(b.start, 1)))
    last = max(last, b.start + b.dur)
print("stretches > 18 s without a graphic:", gaps)
