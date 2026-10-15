"""Procedural textures for the v2 'scrapbook noir' look (deterministic).

assets/tex_dark.jpg   1920x1080 charcoal board: grain, mottling, faint 80 px grid,
                      sparse crosshair marks, scratches, vignette.
assets/tex_paper.png  1000x1300 off-white paper with fibres, soft creases and a
                      torn top edge (alpha).
"""
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
rng = np.random.default_rng(42)

# ---------------------------------------------------------------- dark board
W, H = 1920, 1080
base = np.full((H, W), 19.0, np.float32)
mott = cv2.resize(rng.normal(0, 1, (12, 20)).astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC)
base += cv2.GaussianBlur(mott, (0, 0), 60) * 4.0
base += rng.normal(0, 2.4, (H, W)).astype(np.float32)                    # grain
grid = np.zeros((H, W), np.float32)
for x in range(40, W, 80):
    grid[:, x] = 1
for y in range(20, H, 80):
    grid[y, :] = 1
base += grid * 6.0
for _ in range(60):                                                       # crosshair marks
    x, y = 40 + 80 * rng.integers(0, W // 80), 20 + 80 * rng.integers(0, H // 80)
    cv2.line(base, (int(x - 7), int(y)), (int(x + 7), int(y)), 70, 1)
    cv2.line(base, (int(x), int(y - 7)), (int(x), int(y + 7)), 70, 1)
for _ in range(40):                                                       # faint scratches
    x0, y0 = rng.integers(0, W), rng.integers(0, H)
    ang, L = rng.uniform(0, np.pi), rng.uniform(40, 260)
    cv2.line(base, (int(x0), int(y0)), (int(x0 + L * np.cos(ang)), int(y0 + L * np.sin(ang))), 28 + rng.uniform(0, 10), 1)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
vig = 1 - 0.55 * (((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
board = np.clip(base * np.clip(vig, 0.35, 1), 0, 255)
board = np.dstack([board * 0.97, board, board * 1.03])
cv2.imwrite(str(ROOT / "assets/tex_dark.jpg"), board.astype(np.uint8)[..., ::-1], [cv2.IMWRITE_JPEG_QUALITY, 93])

# ---------------------------------------------------------------- paper
PW, PH = 1000, 1300
p = np.full((PH, PW), 236.0, np.float32)
p += cv2.GaussianBlur(rng.normal(0, 1, (PH, PW)).astype(np.float32), (0, 0), 0.8) * 3.0
fib = np.zeros((PH, PW), np.float32)
for _ in range(900):                                                      # fibres
    x0, y0 = rng.integers(0, PW), rng.integers(0, PH)
    ang, L = rng.uniform(0, np.pi), rng.uniform(4, 22)
    cv2.line(fib, (int(x0), int(y0)), (int(x0 + L * np.cos(ang)), int(y0 + L * np.sin(ang))), 1.0, 1)
p -= cv2.GaussianBlur(fib, (0, 0), 0.6) * 7
cr = cv2.resize(rng.normal(0, 1, (6, 5)).astype(np.float32), (PW, PH), interpolation=cv2.INTER_CUBIC)
p += cv2.GaussianBlur(cr, (0, 0), 40) * 6                                  # soft creases
for _ in range(3):                                                        # fold lines
    y = rng.integers(200, PH - 200)
    p[y:y + 2, :] -= 9
    p[y + 2:y + 6, :] += 3
paper = np.dstack([p * 1.0, p * 0.985, p * 0.94])
alpha = np.full((PH, PW), 255, np.uint8)
low = cv2.resize(rng.normal(0, 1, (1, 18)).astype(np.float32), (PW, 1), interpolation=cv2.INTER_CUBIC)[0]
edge = 18 + low * 6 + rng.normal(0, 2.2, PW).astype(np.float32)          # torn top edge
edge = cv2.GaussianBlur(edge[None], (0, 0), 1.0)[0]
edge = np.clip(edge, 4, 34)
for x in range(PW):
    alpha[: int(edge[x]), x] = 0
    paper[int(edge[x]):int(edge[x]) + 3, x] *= 0.93
rgba = np.dstack([np.clip(paper, 0, 255).astype(np.uint8)[..., ::-1], alpha])
cv2.imwrite(str(ROOT / "assets/tex_paper.png"), rgba)
print("textures written")
