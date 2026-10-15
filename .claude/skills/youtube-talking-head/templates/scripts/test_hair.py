"""TEST ONLY (does not touch the v2 pipeline): 10 s of the final timeline
re-composited with a finer hair matte, true wall-colour decontamination and
background grain matched to the camera noise, next to the current v2 plate.

Outputs in work/test_hair/:
  A_v2_sekarang.mp4   current plate, same camera moves, final audio
  B_tes_baru.mp4      new composite, same camera moves, final audio
  AB_banding.mp4      split screen (left = sekarang, right = tes baru)
  hair_crops.png      still crops at 2x, close-up and medium

plate.py / plate_config.json are imported read-only; overrides live in TEST below.
"""
import copy
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plate as P  # noqa: E402
import edl_map as M  # noqa: E402

ROOT = P.ROOT
OUT = ROOT / "work" / "test_hair"
OUT.mkdir(parents=True, exist_ok=True)
dev = P.dev
W, H, FPS = P.W, P.H, P.FPS
T0, NF = 53.5, 300                       # final-timeline window (10 s)
F0 = int(round(T0 * FPS))

TEST = {
    "downsample_ratio": 0.5,             # v2: 0.3 -> finer hair matte
    "clip_low": 0.03, "clip_high": 0.97,  # v2: 0.06 / 0.92 (no hard cut-out edge)
    "neutral_darken_amount": 0.38,       # same as v2: removes the grey ceiling-light sheen (halo in a dark room)
    "edge_luma_cap": 1.08,               # edge pixels never brighter than the nearby interior (no light fringe)
    "light_wrap": 0.12,                  # v2: 0.08
}

# ---------------------------------------------------------------- 1. original wall (for decontamination)
bpath = OUT / "b_orig.npy"
model = torch.hub.load("PeterL1n/RobustVideoMatting", "resnet50", trust_repo=True).eval().to(dev)
if not bpath.exists():
    acc = torch.zeros(3, H, W, device=dev)
    wsum = torch.zeros(1, H, W, device=dev)
    p = P.decoder(fps="1/3")
    n = 0
    while True:
        f = P.read_frame(p)
        if f is None:
            break
        src = f.to(dev).permute(2, 0, 1).float().div(255)
        with torch.no_grad(), torch.autocast("cuda", dtype=torch.float16):
            _, pha, *_ = model(src[None], None, None, None, None, downsample_ratio=0.3)
        pha = pha[0].float()
        # only pixels clearly outside the person (and not near the edge)
        far = -F.max_pool2d(-(1 - pha)[None], 15, stride=1, padding=7)[0]
        wgt = (far > 0.98).float()
        acc += src * wgt
        wsum += wgt
        n += 1
    p.wait()
    b = acc / wsum.clamp(min=1)
    known = (wsum > 2).float()
    # fill the never-seen interior by repeated normalised blur (push-pull)
    fill, kw = b * known, known
    for r in (8, 16, 32, 64, 128):
        num = P.soft_blur((fill)[None], r, 4)[0]
        den = P.soft_blur(kw[None], r, 4)[0]
        est = num / den.clamp(min=1e-4)
        fill = torch.where(kw > 0.5, fill, est * (den > 1e-3))
        kw = torch.maximum(kw, (den > 1e-3).float())
    np.save(bpath, fill.permute(1, 2, 0).cpu().numpy().astype(np.float16))
    print("original wall estimated from", n, "frames", flush=True)
B_ORIG = torch.from_numpy(np.load(bpath).astype(np.float32)).to(dev).permute(2, 0, 1)

# ---------------------------------------------------------------- 2. camera noise -> background grain
NEW_BG = torch.from_numpy(np.load(ROOT / "work/bg/bg_plate.npy")).to(dev).permute(2, 0, 1).contiguous()
BG_SOFT = P.soft_blur(NEW_BG[None], 48)[0]

# ---------------------------------------------------------------- 3. which source frames
src_t = [M.out_to_src((F0 + k) / FPS) for k in range(NF)]
src_f = [int(round(t * FPS)) for t in src_t]
need = set(src_f)
s_lo, s_hi = min(src_f), max(src_f)
WARM = 45

cfg_grade = copy.deepcopy(P.CFG["grade"])
P.CFG["grade"]["neutral_darken"]["amount"] = TEST["neutral_darken_amount"]   # in memory only


@torch.no_grad()
def composite(src, rec, idx, noise_std):
    with torch.autocast("cuda", dtype=torch.float16):
        fgr, pha, *rec = model(src[None], *rec, downsample_ratio=TEST["downsample_ratio"])
    pha = pha[0].float().clamp(0, 1)
    pha = ((pha - TEST["clip_low"]) / (TEST["clip_high"] - TEST["clip_low"])).clamp(0, 1)
    # true decontamination: F = (I - (1 - a) * B_orig) / a, stable where a is large enough
    a = pha.clamp(min=0.22)
    f_dec = ((src - (1 - pha) * B_ORIG) / a).clamp(0, 1)
    # where alpha is tiny, fall back to colour pulled from the subject interior
    core = (pha > 0.95).float()
    core = -F.max_pool2d(-core[None], 5, stride=1, padding=2)[0]
    num = P.box_blur(P.box_blur((src * core)[None], 9), 9)[0]
    den = P.box_blur(P.box_blur(core[None], 9), 9)[0]
    ext = torch.where(den > 1e-3, num / den.clamp(min=1e-3), fgr[0].float())
    w_dec = ((pha - 0.12) / 0.3).clamp(0, 1)
    fg = w_dec * f_dec + (1 - w_dec) * ext
    # light fringe guard: in the edge band, cap luminance at the interior colour's
    # luminance (keeps strand texture, removes any leftover wall brightness)
    band = (pha < 0.95).float()
    cap = P.luma(ext)[None] * TEST["edge_luma_cap"] + 0.01
    lum = P.luma(fg)[None].clamp(min=1e-4)
    fg = torch.where((band > 0) & (lum > cap), fg * (cap / lum), fg)
    fg = torch.where(pha > 0.985, src, fg)
    fg = P.grade_subject(fg)
    # background carries the same sensor noise as the footage (temporal, luma-weighted)
    gen = torch.Generator(device=dev).manual_seed(5000 + idx)
    nz = torch.randn((1, 1, H, W), generator=gen, device=dev)
    nz = F.avg_pool2d(F.pad(nz, (1, 1, 1, 1), mode="replicate"), 3, stride=1)[0] * 3.0
    chroma = torch.randn((3, H // 4, W // 4), generator=gen, device=dev)
    chroma = F.interpolate(chroma[None], size=(H, W), mode="bilinear", align_corners=False)[0] * 0.35
    bg = NEW_BG + (nz + chroma) * noise_std * (0.6 + 0.8 * P.luma(NEW_BG)[None]).sqrt()
    out = fg * pha + bg * (1 - pha)
    edge = P.soft_blur((1 - pha)[None], 24)[0] * pha
    out = out + TEST["light_wrap"] * edge * (BG_SOFT - out).clamp(-1, 1)
    rim = P.CFG["rim"]
    band = (P.soft_blur((1 - pha)[None], 16)[0] * pha).clamp(0, 1)
    xs = torch.linspace(0, 1, W, device=dev).view(1, 1, W)
    ramp = rim["left"] + (rim["right"] - rim["left"]) * xs
    out = out + band * ramp * torch.tensor(rim["color"], device=dev).view(3, 1, 1) * rim["strength"]
    return out.clamp(0, 1), rec


# ---------------------------------------------------------------- 5. same camera as the final edit
FR = {"WIDE": (1.0, 0, 0), "MED": (1.12, 0, 6), "CLOSE": (1.28, 0, 14), "SIDE_L": (1.25, -230, 0), "SIDE_R": (1.25, 230, 0)}
ops = json.loads((ROOT / "work/camera_ops_v2.json").read_text())


def p2io(u):
    return u * u * 2 if u < 0.5 else 1 - (-2 * u + 2) ** 2 / 2


def cam(t):
    st = FR["WIDE"]
    for t0, kind, fr, d, _ in ops:
        if t0 > t:
            break
        if kind == "set" or t >= t0 + d:
            st = FR[fr]
        else:
            u = p2io((t - t0) / d)
            st = tuple(a + (b - a) * u for a, b in zip(st, FR[fr]))
    return st


def frame_out(img, t):
    s, x, y = cam(t)
    k = 0.75 * s                                    # plate 2560 -> 1920, then camera scale
    ox, oy = 960, 0.32 * 1080
    sw, sh = 2560 * k, 1440 * k
    r = cv2.resize(img, (int(np.ceil(sw)), int(np.ceil(sh))),
                   interpolation=cv2.INTER_AREA if k < 1 else cv2.INTER_CUBIC)
    m = np.float32([[1, 0, ox * (1 - s) + x], [0, 1, oy * (1 - s) + y]])
    return cv2.warpAffine(r, m, (1920, 1080), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)


frames_b = {}
out_of = {}
for k, sf in enumerate(src_f):
    out_of.setdefault(sf, []).append(k)
p = P.decoder(start=max(0, (s_lo - WARM) / FPS), frames=(s_hi - s_lo) + WARM + 2)
fi = max(0, s_lo - WARM)
rec = [None] * 4
noise_std = None
while True:
    f = P.read_frame(p)
    if f is None:
        break
    src = f.to(dev).permute(2, 0, 1).float().div(255)
    if noise_std is None:
        # measure camera noise: high-pass std on the speaker's shirt (dark, flat)
        g = P.luma(src)[None, None]
        hp = g - F.avg_pool2d(F.pad(g, (2, 2, 2, 2), mode="replicate"), 5, stride=1)
        shirt = hp[0, 0, int(H * .78):int(H * .95), int(W * .40):int(W * .60)]
        noise_std = float(shirt.std()) * 1.15
        print("camera noise (shirt high-pass std):", round(noise_std, 4), flush=True)
    out, rec = composite(src, rec, fi, noise_std)
    if fi in need:
        img = (out * 255 + 0.5).clamp(0, 255).byte().permute(1, 2, 0).cpu().numpy()
        for k in out_of[fi]:
            frames_b[k] = frame_out(img, (F0 + k) / FPS)
    fi += 1
    if fi > s_hi:
        break
p.stdout.close()
p.wait()
P.CFG["grade"] = cfg_grade
missing = set(range(NF)) - set(frames_b)
assert not missing, sorted(missing)[:5]

def writer(path, extra_vf=""):
    return subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1920x1080", "-r", str(FPS),
         "-i", "-", "-ss", f"{T0:.3f}", "-t", f"{NF / FPS:.3f}", "-i", str(ROOT / "assets/audio/final_mix.wav"),
         "-map", "0:v", "-map", "1:a", "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p" + extra_vf,
         "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-c:a", "aac", "-b:a", "256k",
         "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-movflags", "+faststart",
         str(path)], stdin=subprocess.PIPE)


# ---------------------------------------------------------------- 4. current v2 plate (A), streamed
pa = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(ROOT / "work/plate/plate_cut_video.mp4"),
                       "-vf", f"select=between(n\\,{F0}\\,{F0 + NF - 1}),format=rgb24", "-fps_mode", "passthrough",
                       "-f", "rawvideo", "-"], stdout=subprocess.PIPE)
wa, wb, wab = writer(OUT / "A_v2_sekarang.mp4"), writer(OUT / "B_tes_baru.mp4"), writer(OUT / "AB_banding.mp4")
font = cv2.FONT_HERSHEY_DUPLEX
crops = []
for k in range(NF):
    t = (F0 + k) / FPS
    buf = pa.stdout.read(W * H * 3)
    assert len(buf) == W * H * 3, k
    a = frame_out(np.frombuffer(buf, np.uint8).reshape(H, W, 3), t)
    b = frames_b[k]
    wa.stdin.write(a.tobytes())
    wb.stdin.write(b.tobytes())
    ab = a.copy()
    ab[:, 960:] = b[:, 960:]
    cv2.line(ab, (960, 0), (960, 1080), (255, 255, 255), 2)
    for txt, x in (("SEKARANG (v2)", 40), ("TES BARU", 1000)):
        cv2.putText(ab, txt, (x, 1040), font, 1.1, (0, 0, 0), 5, cv2.LINE_AA)
        cv2.putText(ab, txt, (x, 1040), font, 1.1, (255, 255, 255), 2, cv2.LINE_AA)
    wab.stdin.write(ab.tobytes())
    if k in (60, 255):                      # medium and close-up stills
        crops.append((a, b))
for w in (wa, wb, wab):
    w.stdin.close()
    w.wait()
pa.stdout.close()
pa.wait()

# ---------------------------------------------------------------- 6. still hair crops at 2x
rows = []
for a, b in crops:
    y0, x0 = 60, 640
    ca = cv2.resize(a[y0:y0 + 300, x0:x0 + 640], None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
    cb = cv2.resize(b[y0:y0 + 300, x0:x0 + 640], None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
    rows.append(np.hstack([ca, np.full((ca.shape[0], 8, 3), 255, np.uint8), cb]))
sheet = np.vstack([rows[0], np.full((8, rows[0].shape[1], 3), 255, np.uint8), rows[1]])
cv2.imwrite(str(OUT / "hair_crops.png"), sheet[..., ::-1])
print("done:", [p.name for p in sorted(OUT.glob("*.mp4"))], "hair_crops.png", flush=True)
