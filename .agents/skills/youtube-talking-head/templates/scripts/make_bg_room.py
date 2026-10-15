"""Room backdrop from the user's reference image (background/room_ref.png).

Pushed back so it reads as a real room a few metres behind the speaker:
scaled to 92 % (edges extended by reflection, then hidden by blur), extra lens
blur, slight darken/desaturate for depth, soft bloom on the practical lamps.
Output: work/bg/bg_plate.npy (float32 sRGB 0..1, 1440x2560) + preview PNG.
"""
from pathlib import Path
import cv2
import numpy as np

W, H = 2560, 1440
ROOT = Path(__file__).resolve().parents[1]
img = cv2.imread(str(ROOT / "background/room_ref.png"))[..., ::-1].astype(np.float32) / 255
lin = np.where(img <= 0.04045, img / 12.92, ((img + 0.055) / 1.055) ** 2.4)

# cover-scale to the plate, then shrink to 92 % around the centre (room farther away)
s = max(W / lin.shape[1], H / lin.shape[0]) * 0.92
big = cv2.resize(lin, (round(lin.shape[1] * s), round(lin.shape[0] * s)), interpolation=cv2.INTER_LANCZOS4)
py, px = max(0, (H - big.shape[0]) // 2 + 1), max(0, (W - big.shape[1]) // 2 + 1)
big = cv2.copyMakeBorder(big, py, py, px, px, cv2.BORDER_REFLECT_101)
y0, x0 = (big.shape[0] - H) // 2, (big.shape[1] - W) // 2
bg = big[y0:y0 + H, x0:x0 + W]

# depth: extra defocus, a touch darker and less saturated (air between camera and wall)
bg = cv2.GaussianBlur(bg, (0, 0), 7)
lum = (0.2126 * bg[..., 0] + 0.7152 * bg[..., 1] + 0.0722 * bg[..., 2])[..., None]
bg = lum + (bg - lum) * 0.9
bg *= 0.86
# bloom on the lamps
hi = np.clip(bg - 0.35, 0, None)
bg += cv2.GaussianBlur(hi, (0, 0), 38) * 0.55 + cv2.GaussianBlur(hi, (0, 0), 12) * 0.25
srgb = np.where(bg <= 0.0031308, bg * 12.92, 1.055 * np.power(np.clip(bg, 0, None), 1 / 2.4) - 0.055)
srgb = np.clip(srgb, 0, 1).astype(np.float32)
np.save(ROOT / "work/bg/bg_plate.npy", srgb)
rng = np.random.default_rng(3)
cv2.imwrite(str(ROOT / "work/bg/bg_plate_preview.png"),
            np.clip(srgb * 255 + rng.uniform(-.5, .5, srgb.shape), 0, 255).astype(np.uint8)[..., ::-1])
cv2.imwrite(str(ROOT / "assets/bg_studio.jpg"),
            cv2.resize(np.clip(srgb * 255, 0, 255).astype(np.uint8), (1920, 1080), interpolation=cv2.INTER_AREA)[..., ::-1],
            [cv2.IMWRITE_JPEG_QUALITY, 94])
print("room plate", srgb.shape, "mean", srgb.mean().round(3))
