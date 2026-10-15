"""Studio plate: reframe -> person matte (RVM) -> grade -> composite on the
procedural backdrop -> light wrap + grain -> high-quality intermediate.

Runs on the FULL raw timeline (no cuts), so the recurrent matte never spans an
edit point and the EDL can be applied to the plate afterwards, exactly as it is
applied to the audio.

  python plate.py preview --times 30,120,300   -> work/plate_preview/*.png
  python plate.py full                          -> work/plate/plate_full.mp4
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw" / "A001_10032154_C025_landscape.mov"
CFG = json.loads((ROOT / "scripts" / "plate_config.json").read_text())
W, H = CFG["out_w"], CFG["out_h"]
FPS = 30
dev = torch.device("cuda")


# ---------------------------------------------------------------- decode/encode
def decoder(start=None, frames=None, fps=FPS):
    c = CFG["crop"]
    vf = (f"fps={fps},crop={c['w']}:{c['h']}:{c['x']}:{c['y']},"
          f"scale={W}:{H}:flags=lanczos:in_range=tv:out_range=pc,format=rgb24")
    cmd = ["ffmpeg", "-v", "error", "-hwaccel", "cuda"]
    if start is not None:
        cmd += ["-ss", f"{start:.3f}"]
    cmd += ["-i", str(RAW)]
    if frames is not None:
        cmd += ["-frames:v", str(frames)]
    cmd += ["-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=W * H * 3 * 4)


def read_frame(p):
    buf = p.stdout.read(W * H * 3)
    if len(buf) < W * H * 3:
        return None
    return torch.frombuffer(bytearray(buf), dtype=torch.uint8).view(H, W, 3)


def encoder(path):
    cmd = ["ffmpeg", "-v", "error", "-y",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", str(RAW), "-map", "0:v", "-map", "1:a:0",
           "-vf", "scale=out_color_matrix=bt709:out_range=tv:in_range=pc,format=yuv420p",
           "-c:v", "libx264", "-preset", "faster", "-crf", "13", "-tune", "film",
           "-g", "30", "-bf", "2",
           "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
           "-c:a", "copy", "-movflags", "+faststart", str(path)]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


# Fast path: decode + crop + lanczos resize on the GPU, NV12 over the pipe
# (half the bytes of RGB), colour conversion in torch.
def decoder_nv12(start=None, frames=None):
    c = CFG["crop"]
    # crop is not honoured on CUDA frames, so scale the full frame on the GPU
    # with the crop's ratio, then crop the (cheap) NV12 result on the CPU.
    k = W / c["w"]
    sw, sh = round(3840 * k / 2) * 2, round(2160 * k / 2) * 2
    cx, cy = round(c["x"] * k / 2) * 2, round(c["y"] * k / 2) * 2
    vf = (f"fps={FPS},scale_cuda={sw}:{sh}:interp_algo=lanczos,hwdownload,format=nv12,"
          f"crop={W}:{H}:{cx}:{cy}")
    cmd = ["ffmpeg", "-v", "error", "-hwaccel", "cuda", "-hwaccel_output_format", "cuda"]
    if start is not None:
        cmd += ["-ss", f"{start:.3f}"]
    cmd += ["-i", str(RAW)]
    if frames is not None:
        cmd += ["-frames:v", str(frames)]
    cmd += ["-vf", vf, "-f", "rawvideo", "-pix_fmt", "nv12", "-"]
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=16 << 20)


NV12_BYTES = W * H * 3 // 2


def read_nv12(p):
    buf = bytearray(NV12_BYTES)
    view = memoryview(buf)
    got = 0
    while got < NV12_BYTES:
        n = p.stdout.readinto(view[got:])
        if not n:
            return None
        got += n
    return buf


def nv12_to_rgb(buf):
    """BT.709 limited-range NV12 bytes -> 3xHxW float RGB 0..1 on the GPU."""
    t = torch.frombuffer(buf, dtype=torch.uint8).to(dev, non_blocking=True).float()
    y = t[: W * H].view(1, 1, H, W)
    uv = t[W * H:].view(H // 2, W // 2, 2).permute(2, 0, 1)[None]
    uv = F.interpolate(uv, size=(H, W), mode="bilinear", align_corners=False)
    yy = (y[0, 0] - 16) / 219
    cb = (uv[0, 0] - 128) / 224
    cr = (uv[0, 1] - 128) / 224
    r = yy + 1.5748 * cr
    g = yy - 0.1873 * cb - 0.4681 * cr
    b = yy + 1.8556 * cb
    return torch.stack([r, g, b]).clamp(0, 1)


def rgb_to_yuv420(x):
    """3xHxW float RGB 0..1 -> BT.709 limited yuv420p bytes (planar)."""
    r, g, b = x[0], x[1], x[2]
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    cb = (b - y) / 1.8556
    cr = (r - y) / 1.5748
    Y = (16 + 219 * y).round().clamp(0, 255).byte()
    cbcr = torch.stack([cb, cr])[None]
    cbcr = F.avg_pool2d(cbcr, 2)[0]
    U = (128 + 224 * cbcr[0]).round().clamp(0, 255).byte()
    V = (128 + 224 * cbcr[1]).round().clamp(0, 255).byte()
    return torch.cat([Y.flatten(), U.flatten(), V.flatten()]).cpu().numpy().tobytes()


def encoder_yuv(path):
    cmd = ["ffmpeg", "-v", "error", "-y",
           "-f", "rawvideo", "-pix_fmt", "yuv420p", "-s", f"{W}x{H}", "-r", str(FPS),
           "-color_range", "tv", "-colorspace", "bt709", "-i", "-",
           "-i", str(RAW), "-map", "0:v", "-map", "1:a:0",
           "-c:v", "libx264", "-preset", "faster", "-crf", "13", "-tune", "film",
           "-g", "30", "-bf", "2", "-pix_fmt", "yuv420p",
           "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
           "-color_range", "tv", "-c:a", "copy", "-movflags", "+faststart", str(path)]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE, bufsize=16 << 20)


# ---------------------------------------------------------------- color
def s2l(x):
    return torch.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055).clamp(min=0) ** 2.4)


def l2s(x):
    x = x.clamp(min=0)
    return torch.where(x <= 0.0031308, x * 12.92, 1.055 * x.clamp(min=1e-8) ** (1 / 2.4) - 0.055)


def luma(x):
    return 0.2126 * x[0] + 0.7152 * x[1] + 0.0722 * x[2]


def grade_subject(rgb):
    """rgb: 3xHxW sRGB 0..1 -> graded sRGB. Correction then look."""
    g = CFG["grade"]
    lin = s2l(rgb)
    lin = lin * torch.tensor(g["wb_gains"], device=dev).view(3, 1, 1)
    lin = lin * (2 ** g["exposure_ev"])
    # filmic contrast in log2 space around mid grey, soft shoulder
    y = luma(lin).clamp(min=1e-5)
    ly = torch.log2(y / 0.18)
    ly2 = ly * g["contrast"]
    y2 = 0.18 * torch.pow(2.0, ly2)
    sh = g["shoulder"]
    y2 = y2 / (1 + y2 * sh)                          # highlight roll-off
    y2 = y2 * (1 + sh)                               # keep 1.0 near 1.0
    lin = lin * (y2 / y).unsqueeze(0)
    # saturation around luminance
    yl = luma(lin).unsqueeze(0)
    lin = yl + (lin - yl) * g["saturation"]
    # lift blacks a touch so the shirt keeps texture (in display space)
    out = l2s(lin)
    out = g["black_lift"] + out * (1 - g["black_lift"])
    nd = g.get("neutral_darken")
    if nd:   # grey hair sheen from the old ceiling light reads as a cut-out in a dark room
        mx, mn = out.max(0).values, out.min(0).values
        chroma = mx - mn
        y = luma(out)
        w = (1 - chroma / nd["chroma"]).clamp(0, 1) * ((y - 0.12) / 0.12).clamp(0, 1) * ((0.72 - y) / 0.15).clamp(0, 1)
        out = out * (1 - nd["amount"] * w).unsqueeze(0)
    st = g.get("shadow_tint")
    if st:   # cool the deep shadows (shirt, hair) to sit in the dark room
        w = (1 - luma(out)).clamp(0, 1).unsqueeze(0) ** 3
        out = out + torch.tensor(st, device=dev).view(3, 1, 1) * w
    return out.clamp(0, 1)


# ---------------------------------------------------------------- matte helpers
def box_blur(x, r):
    k = 2 * r + 1
    return F.avg_pool2d(F.pad(x, (r, r, r, r), mode="replicate"), k, stride=1)


def soft_blur(x, r, scale=8):
    """cheap large blur: downsample, box blur twice, upsample."""
    h, w = x.shape[-2:]
    s = F.interpolate(x, size=(h // scale, w // scale), mode="area")
    rr = max(1, r // scale)
    s = box_blur(box_blur(s, rr), rr)
    return F.interpolate(s, size=(h, w), mode="bilinear", align_corners=False)


class Compositor:
    def __init__(self):
        self.model = torch.hub.load("PeterL1n/RobustVideoMatting", "resnet50",
                                    trust_repo=True).eval().to(dev)
        bg = np.load(ROOT / "work" / "bg" / "bg_plate.npy")
        self.bg = torch.from_numpy(bg).to(dev).permute(2, 0, 1).contiguous()
        self.bg_soft = soft_blur(self.bg[None], 48)[0]
        self.rec = [None] * 4
        self.rim_ramp = None
        self.chair = []
        for z in CFG.get("chair_zones", []):
            cp = ROOT / "work" / "bg" / f"clean_{z['name']}.npy"
            if cp.exists():
                t = torch.from_numpy(np.load(cp)).to(dev).permute(2, 0, 1).float() / 255
                self.chair.append((z["box"], t))
        self.garbage = None
        gm = CFG.get("garbage_polys")
        if gm:
            import cv2
            m = np.zeros((H, W), np.uint8)
            for poly in gm:
                cv2.fillPoly(m, [np.array(poly, np.int32)], 255)
            m = cv2.GaussianBlur(m, (0, 0), 6).astype(np.float32) / 255
            self.garbage = torch.from_numpy(m).to(dev)

    def reset(self):
        self.rec = [None] * 4

    @torch.no_grad()
    def __call__(self, frame_u8, idx):
        if frame_u8.dtype == torch.uint8:
            src = frame_u8.to(dev).permute(2, 0, 1).float().div(255)   # 3xHxW
        else:
            src = frame_u8
        with torch.autocast("cuda", dtype=torch.float16):
            fgr, pha, *self.rec = self.model(src[None], *self.rec,
                                             downsample_ratio=CFG["downsample_ratio"])
        fgr, pha = fgr[0].float().clamp(0, 1), pha[0].float().clamp(0, 1)
        m = CFG["matte"]
        if self.garbage is not None:
            pha = pha * (1 - self.garbage)
        # chair ears: key out pixels that still match the empty-chair clean plate
        ck = CFG["chair_key"]
        for (x0, y0, x1, y1), clean in self.chair:
            s = src[:, y0:y1, x0:x1]
            diff = (s - clean).abs().mean(0, keepdim=True)
            same = ((ck["diff_hi"] - diff) / (ck["diff_hi"] - ck["diff_lo"])).clamp(0, 1)
            warm = ((clean[0:1] - clean[2:3] - ck["warm_lo"]) /
                    (ck["warm_hi"] - ck["warm_lo"])).clamp(0, 1)
            ly = luma(s)[None]
            bright = ((ly - ck["luma_lo"]) / (ck["luma_hi"] - ck["luma_lo"])).clamp(0, 1)
            kill = same * warm * bright
            g = ck.get("grow", 0)
            if g:
                kill = F.max_pool2d(kill[None], 2 * g + 1, stride=1, padding=g)[0]
            kill = box_blur(kill[None], 2)[0]
            pha = pha.clone()
            pha[:, y0:y1, x0:x1] = pha[:, y0:y1, x0:x1] * (1 - kill)
        # tighten the matte slightly: removes the faint wall veil RVM leaves
        pha = ((pha - m["clip_low"]) / (m["clip_high"] - m["clip_low"])).clamp(0, 1)
        if m.get("gamma", 1.0) != 1.0:
            pha = pha ** m["gamma"]
        # Interior uses the real pixels. Edge pixels still carry the old cream
        # wall, so their colour is pulled from the nearby solid interior instead
        # (edge extend), falling back to RVM's decontaminated estimate.
        # dark rooms show any cream-wall rim: choke the matte ~1 px and take edge
        # colour from deeper inside the subject (eroded core)
        ch = m.get("choke_px", 0)
        if ch:
            pha = -F.max_pool2d(-pha[None], 2 * ch + 1, stride=1, padding=ch)[0]
            pha = box_blur(pha[None], 1)[0]
        core = (pha > m["core"]).float()
        ce = m.get("core_erode_px", 0)
        if ce:
            core = -F.max_pool2d(-core[None], 2 * ce + 1, stride=1, padding=ce)[0]
        r = m["extend_px"]
        num = box_blur(box_blur((src * core)[None], r), r)[0]
        den = box_blur(box_blur(core[None], r), r)[0]
        ext = torch.where(den > 1e-3, num / den.clamp(min=1e-3), fgr)
        w = ((pha - m["core"]) / (0.995 - m["core"])).clamp(0, 1)
        fg = w * src + (1 - w) * ext
        fg = grade_subject(fg)
        out = fg * pha + self.bg * (1 - pha)
        # light wrap: backdrop light bleeding over the subject's edge
        lw = CFG["light_wrap"]
        if lw > 0:
            edge = soft_blur((1 - pha)[None], 24)[0] * pha
            out = out + lw * edge * (self.bg_soft - out).clamp(min=-1, max=1)
        # warm rim from the room's practicals, stronger on frame-right (slat lamp side)
        rim = CFG.get("rim")
        if rim:
            band = (soft_blur((1 - pha)[None], 16)[0] * pha).clamp(0, 1)
            if self.rim_ramp is None:
                xs = torch.linspace(0, 1, W, device=dev).view(1, 1, W)
                self.rim_ramp = (rim["left"] + (rim["right"] - rim["left"]) * xs).expand(1, H, W)
            col = torch.tensor(rim["color"], device=dev).view(3, 1, 1)
            out = out + band * self.rim_ramp * col * rim["strength"]
        # global finishing curve shared by subject and backdrop
        fin = CFG["finish"]
        out = out.clamp(0, 1) ** fin["gamma"]
        # temporal grain, seeded per frame (deterministic)
        gen = torch.Generator(device=dev).manual_seed(1000 + idx)
        n = torch.randn((1, 1, H, W), generator=gen, device=dev)
        n = F.avg_pool2d(F.pad(n, (1, 1, 1, 1), mode="replicate"), 3, stride=1)[0] * 2.2
        gs = fin["grain_bg"] * (1 - pha) + fin["grain_fg"] * pha
        out = out + n * gs
        return out.clamp(0, 1), pha


def to_u8(x):
    return (x * 255 + 0.5).clamp(0, 255).byte().permute(1, 2, 0).contiguous().cpu().numpy()


def preview(times):
    import cv2
    out_dir = ROOT / "work" / "plate_preview"
    out_dir.mkdir(parents=True, exist_ok=True)
    comp = Compositor()
    for t in times:
        comp.reset()
        warm = 45  # frames of recurrent warm-up before the inspected frame
        p = decoder(start=max(0, t - warm / FPS), frames=warm + 1)
        i, last = 0, None
        while True:
            f = read_frame(p)
            if f is None:
                break
            res = comp(f, int(t * FPS) - warm + i)
            last = (f, res)
            i += 1
        p.wait()
        f, (out, pha) = last
        cv2.imwrite(str(out_dir / f"t{t:06.1f}_src.png"), f.numpy()[..., ::-1])
        cv2.imwrite(str(out_dir / f"t{t:06.1f}_comp.png"), to_u8(out)[..., ::-1])
        cv2.imwrite(str(out_dir / f"t{t:06.1f}_alpha.png"), to_u8(pha.expand(3, -1, -1))[..., 0])
        print("preview", t, flush=True)


def full(limit=None, out_name="plate_full.mp4"):
    import queue
    import threading
    out_dir = ROOT / "work" / "plate"
    out_dir.mkdir(parents=True, exist_ok=True)
    comp = Compositor()
    p = decoder_nv12(frames=limit)
    enc = encoder_yuv(out_dir / out_name)
    q_in, q_out = queue.Queue(maxsize=12), queue.Queue(maxsize=12)

    def reader():
        while True:
            b = read_nv12(p)
            q_in.put(b)
            if b is None:
                return

    def writer():
        while True:
            b = q_out.get()
            if b is None:
                return
            enc.stdin.write(b)

    tr, tw = threading.Thread(target=reader, daemon=True), threading.Thread(target=writer, daemon=True)
    tr.start(); tw.start()
    alpha_stats = []
    t0, i = time.time(), 0
    while True:
        b = q_in.get()
        if b is None:
            break
        out, pha = comp(nv12_to_rgb(b), i)
        q_out.put(rgb_to_yuv420(out))
        if i % 30 == 0:
            alpha_stats.append(float(pha.mean()))
        i += 1
        if i % 300 == 0:
            el = time.time() - t0
            print(f"frame {i} {i / el:.1f} fps elapsed {el:.0f}s", flush=True)
    q_out.put(None)
    tw.join()
    enc.stdin.close()
    enc.wait()
    p.wait()
    (out_dir / "alpha_coverage.json").write_text(json.dumps(alpha_stats))
    print(f"done {i} frames in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["preview", "full"])
    ap.add_argument("--times", default="30,120,300,450,590")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--out", default="plate_full.mp4")
    a = ap.parse_args()
    if a.mode == "preview":
        preview([float(x) for x in a.times.split(",")])
    else:
        full(a.limit, a.out)
    sys.exit(0)
