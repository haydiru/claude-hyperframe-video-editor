"""Portrait retouch for thumbnail cut-outs (local, no AI generation): gentle skin
smoothing that keeps texture (frequency separation on a skin mask), brighter and
crisper eyes, a soft key light on the face, clarity and sharpening.

  python thumbnail/retouch.py s144.8 s7.9   -> thumbnail/work/cut_<tag>_rt.png (+ before/after preview)
"""
import sys
from pathlib import Path

import cv2
import numpy as np

W = Path(__file__).resolve().parent / "work"


def find_face(bgr, a):
    """face box from the skin pixels in the head part of the matte (no detector model needed)."""
    ycc = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb).astype(np.float32)
    skin = ((ycc[..., 1] > 133) & (ycc[..., 1] < 178) & (ycc[..., 2] > 80) & (ycc[..., 2] < 132) & (a > 0.5))
    top = int(np.where(a.max(1) > 0.5)[0][0])
    band = skin[top:top + 900]
    ys, xs = np.where(band)
    cx = int(np.median(xs))
    keep = np.abs(xs - cx) < 330                     # drop shoulders / hands at the sides
    ys, xs = ys[keep], xs[keep]
    x0, x1 = np.percentile(xs, [1, 99]).astype(int)
    y0, y1 = int(np.percentile(ys, 1)) + top, int(np.percentile(ys, 99)) + top
    return x0, y0, x1 - x0, y1 - y0


def find_eyes(bgr, fx, fy, fw, fh):
    """darkest blob in the eye band, then its partner on the other side at a similar height."""
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    g = cv2.GaussianBlur(g, (0, 0), 7)
    y0, y1 = fy + int(fh * 0.24), fy + int(fh * 0.50)
    halves = [(fx + int(fw * 0.12), fx + fw // 2), (fx + fw // 2, fx + int(fw * 0.88))]
    best = []
    for xa, xb in halves:
        sub = g[y0:y1, xa:xb]
        yy, xx = np.unravel_index(np.argmin(sub), sub.shape)
        best.append((float(sub[yy, xx]), xa + xx, y0 + yy))
    k = int(np.argmin([b[0] for b in best]))       # the more certain eye
    _, ex, ey = best[k]
    xa, xb = halves[1 - k]
    ya, yb = ey - int(fh * 0.07), ey + int(fh * 0.07)
    sub = g[ya:yb, xa:xb]
    yy, xx = np.unravel_index(np.argmin(sub), sub.shape)
    other = (xa + xx, ya + yy)
    return [(ex, ey), other] if k == 0 else [other, (ex, ey)]


def soft_ellipse(shape, cx, cy, rx, ry, feather):
    m = np.zeros(shape[:2], np.float32)
    cv2.ellipse(m, (int(cx), int(cy)), (int(rx), int(ry)), 0, 0, 360, 1.0, -1)
    return cv2.GaussianBlur(m, (0, 0), feather)


for tag in sys.argv[1:]:
    rgba = cv2.imread(str(W / f"cut_{tag}.png"), cv2.IMREAD_UNCHANGED)
    bgr, a = rgba[..., :3], rgba[..., 3].astype(np.float32) / 255
    img = bgr.astype(np.float32) / 255
    fx, fy, fw, fh = find_face(bgr, a)
    print(tag, "face", fx, fy, fw, fh)

    # ---- skin smoothing (frequency separation, texture kept at 45 %)
    ycc = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb).astype(np.float32)
    skin = ((ycc[..., 1] > 133) & (ycc[..., 1] < 178) & (ycc[..., 2] > 80) & (ycc[..., 2] < 132)).astype(np.float32)
    region = soft_ellipse(img.shape, fx + fw / 2, fy + fh * 0.55, fw * 0.62, fh * 0.80, 25)
    skin = cv2.GaussianBlur(skin, (0, 0), 6) * region * a
    smooth = cv2.bilateralFilter(bgr, 0, 22, 9).astype(np.float32) / 255
    detail = img - cv2.GaussianBlur(img, (0, 0), 2.2)
    skin_rt = smooth + 0.45 * detail
    out = img * (1 - 0.75 * skin[..., None]) + skin_rt * (0.75 * skin[..., None])

    # ---- eyes: a touch brighter, more contrast, crisper
    eyes = find_eyes(bgr, fx, fy, fw, fh)
    ew = fw * 0.20
    for cx, cy in eyes:
        m = soft_ellipse(img.shape, cx, cy, ew * 0.55, ew * 0.26, 6)[..., None]
        loc = out ** 0.86
        sharp = loc + 0.8 * (loc - cv2.GaussianBlur(loc, (0, 0), 1.6))
        out = out * (1 - m) + sharp * m
    print(tag, "eyes", eyes)

    # ---- soft key light on the face, slight burn toward the edges of the subject
    key = soft_ellipse(img.shape, fx + fw * 0.5, fy + fh * 0.45, fw * 0.75, fh * 0.9, fw * 0.25)[..., None]
    out = out * (1 + 0.07 * key)
    # ---- clarity + sharpen + a little warmth / vibrance on the subject
    lum = cv2.cvtColor(np.clip(out, 0, 1), cv2.COLOR_BGR2GRAY)[..., None]
    out = out + 0.18 * (out - cv2.GaussianBlur(out, (0, 0), 14)) * (1 - skin[..., None] * 0.6)
    out = out + 0.55 * (out - cv2.GaussianBlur(out, (0, 0), 1.1))
    sat = out - lum
    out = lum + sat * 0.96
    out = out * np.array([1.01, 1.0, 0.99], np.float32)
    res = (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)
    # outside the subject keep the original pixels (the room behind)
    m3 = (a > 0.02)[..., None]
    res = np.where(m3, res, bgr)
    cv2.imwrite(str(W / f"cut_{tag}_rt.png"), np.dstack([res, rgba[..., 3]]))
    x0, y0 = max(0, fx - fw // 3), max(0, fy - fh // 3)
    x1, y1 = fx + fw + fw // 3, fy + fh + fh // 3
    dbg = bgr.copy()
    cv2.rectangle(dbg, (fx, fy), (fx + fw, fy + fh), (0, 255, 255), 3)
    for cx, cy in eyes:
        cv2.circle(dbg, (int(cx), int(cy)), 18, (0, 0, 255), 3)
    pv = np.hstack([dbg[y0:y1, x0:x1], bgr[y0:y1, x0:x1], res[y0:y1, x0:x1]])
    cv2.imwrite(str(W / f"retouch_{tag}.jpg"), cv2.resize(pv, None, fx=0.6, fy=0.6, interpolation=cv2.INTER_AREA),
                [cv2.IMWRITE_JPEG_QUALITY, 92])
