"""Speaker cut-outs for the YouTube thumbnail, from the raw 4K take through the
same v2 compositor (grade, room light, matte). Read-only use of plate.py.

  python thumbnail/make_cutouts.py 128.0 213.0 s144.8   (final-timeline seconds; s<sec> = raw source seconds)
-> thumbnail/work/cut_<t>.png  (RGBA, 2560x1440) and room_<t>.jpg (same frame with the room)
"""
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import plate as P  # noqa: E402
import edl_map as M  # noqa: E402

OUT = Path(__file__).resolve().parent / "work"
OUT.mkdir(exist_ok=True)
comp = P.Compositor()
for arg in sys.argv[1:]:
    if arg.startswith("s"):
        t_src = float(arg[1:])
        t_out = t_src
        tag = arg
    else:
        t_out = float(arg)
        t_src = M.out_to_src(t_out)
        tag = f"{t_out:.1f}"
    n = int(round(t_src * P.FPS))
    warm = 45
    comp.reset()
    p = P.decoder(start=(n - warm) / P.FPS, frames=warm + 1)
    last = None
    i = 0
    while True:
        f = P.read_frame(p)
        if f is None:
            break
        last = comp(f, n - warm + i)
        i += 1
    p.wait()
    out, pha = last
    rgb = P.to_u8(out)
    a = (pha[0].clamp(0, 1) * 255 + 0.5).byte().cpu().numpy()
    cv2.imwrite(str(OUT / f"room_{tag}.jpg"), rgb[..., ::-1], [cv2.IMWRITE_JPEG_QUALITY, 95])
    cv2.imwrite(str(OUT / f"cut_{tag}.png"), np.dstack([rgb[..., ::-1], a]))
    print("cut", t_out, "-> src", round(t_src, 2), flush=True)
