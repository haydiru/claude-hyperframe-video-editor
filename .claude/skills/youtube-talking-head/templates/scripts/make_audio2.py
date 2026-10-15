"""v2 sound design, fully synthesized (no third-party audio).

music_bed.wav : dark lo-fi hip-hop, 84 BPM, D minor (Dm9 - Bbmaj9 - Gm9 - A7sus/A7).
                Sections from work/music_plan.json: 'intro' (pad + EP, no drums),
                'groove' (full kit), 'break' (breathers: pad swell, no drums),
                'outro'. Each section restarts the bar grid so drops land on the
                section start. Short 'stops' cut the music for a dramatic beat.
                Ducked ~6 dB under the voice.
sfx.wav       : events from work/sfx_events_v2.json.
"""
import json
import math
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt, sosfiltfilt, fftconvolve

ROOT = Path(__file__).resolve().parents[1]
SR = 48000
plan = json.loads((ROOT / "work/music_plan.json").read_text())
DUR = plan["duration"]
N = int(round(DUR * SR))
rng = np.random.default_rng(84)
BPM = 84.0
BEAT = 60 / BPM
BAR = 4 * BEAT
STEP = BEAT / 4


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def lp(x, f, o=2):
    return sosfilt(butter(o, f, "low", fs=SR, output="sos"), x, axis=0)


def hp(x, f, o=2):
    return sosfilt(butter(o, f, "high", fs=SR, output="sos"), x, axis=0)


def bp(x, lo, hi, o=2):
    return sosfilt(butter(o, [lo, hi], "band", fs=SR, output="sos"), x, axis=0)


def env_adsr(n, a, d, s, r, sus_len):
    t = np.arange(n) / SR
    e = np.where(t < a, t / max(a, 1e-4), s + (1 - s) * np.exp(-(t - a) / max(d, 1e-4)))
    rel_start = a + sus_len
    e = np.where(t > rel_start, e * np.exp(-(t - rel_start) / max(r, 1e-4)), e)
    return e.astype(np.float32)


def reverb_ir(sec=1.6, damp=3500, seed=1):
    r = np.random.default_rng(seed)
    n = int(sec * SR)
    ir = r.normal(0, 1, (n, 2)).astype(np.float32) * np.exp(-np.arange(n) / (SR * sec / 5.5))[:, None]
    ir = lp(ir, damp)
    ir[0] += 1.0
    return ir / np.abs(ir).sum(0).max() * 6


IR_ROOM = reverb_ir(1.1, 4500, 3)
IR_HALL = reverb_ir(2.4, 3000, 5)


def add(buf, x, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    if i >= len(buf) or i + len(x) <= 0:
        return
    if x.ndim == 1:
        x = np.stack([x * (1 - max(0, pan)), x * (1 + min(0, pan))], 1)
    a, b = max(0, i), min(len(buf), i + len(x))
    buf[a:b] += x[a - i:b - i] * gain


# ------------------------------------------------------------------ instruments
def kick(vel=1.0):
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    f = 45 + 75 * np.exp(-t / 0.035)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.16)
    x += bp(rng.normal(0, 1, n), 1500, 5000) * np.exp(-t / 0.004) * 0.25
    return (np.tanh(x * 1.6) * 0.8 * vel).astype(np.float32)


def snare(vel=1.0):
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    body = np.sin(2 * np.pi * 185 * t) * np.exp(-t / 0.05) * 0.5
    nz = bp(rng.normal(0, 1, n), 1200, 7000) * np.exp(-t / 0.11)
    x = (body + nz * 0.7) * vel
    return np.stack([x, x], 1).astype(np.float32) * 0.55


def hat(vel=1.0, open_=False):
    n = int((0.28 if open_ else 0.06) * SR)
    t = np.arange(n) / SR
    x = hp(rng.normal(0, 1, n), 7500) * np.exp(-t / (0.09 if open_ else 0.014))
    return (x * 0.22 * vel).astype(np.float32)


def ep_note(m, dur, vel=0.6):
    """FM electric piano."""
    n = int((dur + 1.6) * SR)
    t = np.arange(n) / SR
    f = hz(m)
    idx = 1.6 * np.exp(-t / 0.35) + 0.25
    mod = np.sin(2 * np.pi * f * t) * idx
    x = np.sin(2 * np.pi * f * t + mod) + 0.25 * np.sin(2 * np.pi * 2 * f * t + 0.5 * mod)
    e = env_adsr(n, 0.004, 0.9, 0.35, 0.45, dur)
    trem = 1 + 0.08 * np.sin(2 * np.pi * 4.6 * t)
    return (x * e * trem * vel * 0.16).astype(np.float32)


def bass_note(m, dur, vel=0.9):
    n = int((dur + 0.3) * SR)
    t = np.arange(n) / SR
    f = hz(m)
    x = np.sin(2 * np.pi * f * t) + 0.18 * np.sin(2 * np.pi * 2 * f * t)
    e = env_adsr(n, 0.008, 0.4, 0.55, 0.12, dur)
    return (np.tanh(x * 1.3) * e * vel * 0.42).astype(np.float32)


def pad_chord(notes, dur):
    n = int((dur + 1.5) * SR)
    t = np.arange(n) / SR
    x = np.zeros((n, 2), np.float32)
    for k, m in enumerate(notes):
        for ch, det in ((0, -0.12), (1, 0.14)):
            f = hz(m) * (1 + det / 100)
            ph = rng.uniform(0, 6.28)
            saw = sum(np.sin(2 * np.pi * f * h * t + ph * h) / h for h in range(1, 7))
            x[:, ch] += saw * 0.06
    e = env_adsr(n, 1.2, 2.0, 0.85, 1.2, dur)
    return lp(x * e[:, None], 1100).astype(np.float32)


CHORDS = [[50, 53, 57, 60, 64], [46, 50, 53, 57, 60], [43, 46, 50, 53, 57], [45, 50, 52, 55, 61]]
ROOTS = [38, 34, 31, 33]
KICK = {0: 1.0, 7: 0.75, 10: 0.9}
SNARE = {4: 1.0, 12: 1.0}


def section(buf, s, e, mode):
    """render one section on its own bar grid starting at s."""
    bars = int(math.ceil((e - s) / BAR)) + 1
    for bi in range(bars):
        t0 = s + bi * BAR
        if t0 >= e:
            break
        ch = CHORDS[bi % 4]
        if mode in ("intro", "break", "outro", "groove"):
            if mode != "groove" or bi % 2 == 0:
                add(buf, pad_chord(ch, BAR * (2 if mode == "groove" else 1)), t0,
                    0.55 if mode == "groove" else 0.9)
        # EP comping (swung): beat 1 and the 'and' of 2
        if mode in ("intro", "groove", "outro"):
            for hit, ln in ((0, 1.2), (6, 0.9)):
                tt = t0 + hit * STEP + (STEP * 0.16 if hit % 2 else 0)
                if tt >= e:
                    continue
                for k, m in enumerate(ch):
                    add(buf, ep_note(m + 12, ln, 0.5 + 0.1 * (k == len(ch) - 1)), tt + k * 0.012,
                        0.75 if mode == "intro" else 1.0, pan=(k - 2) * 0.12)
        if mode == "groove":
            r = ROOTS[bi % 4]
            for st, ln in ((0, 1.6), (7, 0.5), (10, 1.2)):
                tt = t0 + st * STEP
                if tt < e:
                    add(buf, bass_note(r, ln * BEAT), tt, 1.0)
            for st in range(16):
                tt = t0 + st * STEP + (STEP * 0.18 if st % 2 else 0)
                if tt >= e - 0.05:
                    continue
                if st in KICK:
                    add(buf, kick(KICK[st]), tt, 1.0)
                if st in SNARE:
                    add(buf, snare(SNARE[st]), tt, 1.0)
                if st % 2 == 0:
                    add(buf, hat(0.7 + 0.3 * (st % 4 == 0)), tt, 1.0, pan=0.15)
                if st == 14 and bi % 2 == 1:
                    add(buf, hat(0.6, True), tt, 1.0, pan=0.15)
        if mode == "intro":
            for st in (0, 8):                        # heartbeat sub pulse for tension
                tt = t0 + st * STEP
                if tt < e:
                    add(buf, bass_note(ROOTS[bi % 4], 0.5, 0.6), tt, 0.8)


music = np.zeros((N, 2), np.float32)
for sec in plan["sections"]:
    section(music, sec["start"], sec["end"], sec["mode"])
# vinyl bed
crackle = np.zeros(N, np.float32)
for t in rng.uniform(0, DUR, int(DUR * 7)):
    i = int(t * SR)
    crackle[i:i + 30] += rng.normal(0, 1, len(crackle[i:i + 30])) * rng.uniform(0.02, 0.08)
music += np.stack([crackle, crackle], 1)
music += (bp(rng.normal(0, 1, (N, 2)), 2000, 8000) * 0.0025).astype(np.float32)
music = (music + fftconvolve(music, IR_ROOM, axes=0)[:N] * 0.25).astype(np.float32)
music = lp(hp(music, 35), 9000)
# section-level shaping: gentle fade-in, stops, outro fade
t = np.arange(N) / SR
gainc = np.clip(t / 2.0, 0, 1) * np.clip((DUR - t) / 4.0, 0, 1)
# breathers (chapter cards, no voice): the bed swells so the pause carries motion
for sec in plan["sections"]:
    if sec["mode"] == "break":
        w = np.clip((t - sec["start"]) / 0.35, 0, 1) * np.clip((sec["end"] + 0.25 - t) / 0.35, 0, 1)
        gainc *= 1 + (10 ** (5 / 20) - 1) * w
for st in plan.get("stops", []):
    a, b = st
    w = np.clip((t - a) / 0.03, 0, 1) * np.clip((b - t) / 0.03, 0, 1)
    gainc *= 1 - w
# sidechain duck under the voice
voice, _ = sf.read(ROOT / "assets/audio/voice_master.wav", dtype="float32", always_2d=True)
v = np.abs(voice.mean(1))
v = np.pad(v, (0, max(0, N - len(v))))[:N]
hop = 480
envv = np.sqrt(np.convolve(v[: N // hop * hop].reshape(-1, hop).mean(1) ** 2, np.ones(15) / 15, "same"))
envv = np.pad(np.repeat(envv, hop), (0, N - N // hop * hop))
talk = np.clip((20 * np.log10(envv + 1e-6) + 40) / 10, 0, 1)
talk = sosfilt(butter(1, 2.0, "low", fs=SR, output="sos"), talk)
music *= (gainc * 10 ** (-6.5 * talk / 20))[:, None]
# level by the voice, not by the loudest peak: the bed sits 14 dB under speech
win = SR // 10
nwin = min(len(voice), N) // win


def wrms(x):
    x = x[: nwin * win].mean(1).reshape(nwin, win)
    return 20 * np.log10(np.sqrt((x ** 2).mean(1)) + 1e-9)


vr, mr = wrms(voice), wrms(music)
speech = vr > -35
music *= 10 ** ((np.median(vr[speech]) - 14.0 - np.median(mr[speech])) / 20)
pk = np.abs(music).max()
if pk > 0.5:                                    # soft-limit swells above -6 dBFS
    music = np.tanh(music / 0.5) * 0.5
sf.write(ROOT / "assets/audio/music_bed.wav", music, SR, subtype="PCM_16")


# ------------------------------------------------------------------ sfx
def nz(n):
    return rng.normal(0, 1, n).astype(np.float32)


def sweep_bp(x, f0, f1, q=1.6):
    out = np.zeros_like(x)
    seg = 512
    for i in range(0, len(x), seg):
        f = f0 * (f1 / f0) ** (i / len(x))
        lo, hi = max(60, f / q), min(20000, f * q)
        out[i:i + seg] = sosfilt(butter(2, [lo, hi], "band", fs=SR, output="sos"), x[i:i + seg])
    return out


def norm(x, peak):
    return (x / (np.abs(x).max() + 1e-9) * peak).astype(np.float32)


def s_whoosh(dur=0.6, f0=350, f1=2800, peak=0.35):
    n = int(dur * SR)
    x = sweep_bp(nz(n), f0, f1)
    x *= np.sin(np.linspace(0, np.pi, n)) ** 1.6
    pan = np.linspace(-0.6, 0.6, n)
    st = np.stack([x * (1 - np.clip(pan, 0, 1)), x * (1 + np.clip(pan, -1, 0))], 1)
    return norm(st, peak)


def s_impact():
    n = int(2.2 * SR)
    t = np.arange(n) / SR
    f = 32 + 30 * np.exp(-t / 0.18)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.55)
    thump = np.sin(2 * np.pi * 110 * t) * np.exp(-t / 0.06) * 0.6
    burst = lp(nz(n), 900) * np.exp(-t / 0.05) * 0.9
    x = np.tanh((sub + thump + burst) * 1.4)
    st = np.stack([x, x], 1)
    st = st + fftconvolve(st, IR_HALL, axes=0)[:n] * 0.35
    return norm(st, 0.62)


def s_riser(dur=2.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = sweep_bp(nz(n), 300, 7000, 1.4)
    x += np.sin(2 * np.pi * np.cumsum(200 * (6 ** (t / dur))) / SR) * 0.15
    x *= (t / dur) ** 2.2
    return norm(np.stack([x, x * 0.92], 1), 0.32)


def s_key():
    n = int(0.06 * SR)
    t = np.arange(n) / SR
    x = bp(nz(n), 1800, 6500) * np.exp(-t / 0.004) + np.sin(2 * np.pi * rng.uniform(120, 170) * t) * np.exp(-t / 0.012) * 0.5
    return norm(x, 0.30)


def s_ding():
    n = int(1.4 * SR)
    t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * 2093 * t) * np.exp(-t / 0.5) + 0.5 * np.sin(2 * np.pi * 4190 * t) * np.exp(-t / 0.3)
         + 0.25 * np.sin(2 * np.pi * 6280 * t) * np.exp(-t / 0.18))
    st = np.stack([x, x], 1)
    st = st + fftconvolve(st, IR_ROOM, axes=0)[:n] * 0.3
    return norm(st, 0.22)


def s_paper():
    n = int(0.5 * SR)
    x = lp(nz(n), 3500) * np.sin(np.linspace(0, np.pi, n)) * (0.6 + 0.4 * np.abs(lp(nz(n), 30) * 8))
    return norm(x, 0.22)


def s_scribble(dur=0.6):
    n = int(dur * SR)
    t = np.arange(n) / SR
    am = 0.5 + 0.5 * np.sin(2 * np.pi * 9 * t + 2 * np.sin(2 * np.pi * 2.3 * t)) ** 2
    x = bp(nz(n), 1500, 5000) * am * np.sin(np.linspace(0, np.pi, n)) ** 0.5
    return norm(x, 0.16)


def s_marker():
    n = int(0.38 * SR)
    t = np.arange(n) / SR
    x = sweep_bp(nz(n), 2200, 3400, 1.3) * (0.7 + 0.3 * np.sin(2 * np.pi * 14 * t)) * np.sin(np.linspace(0, np.pi, n))
    return norm(x, 0.14)


def s_cash():
    n = int(1.2 * SR)
    t = np.arange(n) / SR
    clack = bp(nz(n), 1000, 4000) * (np.exp(-t / 0.006) + 0.7 * np.exp(-np.clip(t - 0.07, 0, None) / 0.006) * (t > 0.07))
    bell = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-np.clip(t - 0.12, 0, None) / dcy) * (t > 0.12)
               for f, a, dcy in ((2637, 1, .45), (3520, .6, .35), (5274, .35, .25)))
    x = clack * 0.8 + bell * 0.6
    st = np.stack([x, x], 1)
    return norm(st + fftconvolve(st, IR_ROOM, axes=0)[:n] * 0.25, 0.3)


def s_shutter():
    n = int(0.18 * SR)
    t = np.arange(n) / SR
    x = bp(nz(n), 1200, 7000) * (np.exp(-t / 0.01) + 0.8 * np.exp(-np.clip(t - 0.07, 0, None) / 0.012) * (t > 0.07))
    return norm(x, 0.3)


def s_chime():
    n = int(1.3 * SR)
    t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * 1318.5 * t) * np.exp(-t / 0.35) +
         np.roll(np.sin(2 * np.pi * 1760 * t) * np.exp(-t / 0.45), int(0.11 * SR)) * 0.85)
    st = np.stack([x, x], 1)
    return norm(st + fftconvolve(st, IR_ROOM, axes=0)[:n] * 0.3, 0.3)


def s_tick():
    n = int(0.04 * SR)
    t = np.arange(n) / SR
    return norm(np.sin(2 * np.pi * 2900 * t) * np.exp(-t / 0.007), 0.16)


def s_pop():
    n = int(0.12 * SR)
    f = np.linspace(760, 480, n)
    return norm(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-np.arange(n) / SR / 0.03), 0.22)


def s_thud():
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    return norm(np.sin(2 * np.pi * np.cumsum(np.linspace(100, 50, n)) / SR) * np.exp(-t / 0.09), 0.35)


MAKE = {"whoosh": lambda: s_whoosh(), "swish": lambda: s_whoosh(0.28, 900, 4200, 0.18), "impact": s_impact,
        "key": s_key, "ding": s_ding, "paper": s_paper, "scribble": s_scribble, "marker": s_marker,
        "cash": s_cash, "shutter": s_shutter, "chime": s_chime, "tick": s_tick, "pop": s_pop, "thud": s_thud}

events = json.loads((ROOT / "work/sfx_events_v2.json").read_text())
# measured against the voice master: impacts and paper hits sat 4-6 dB over speech
TRIM = {"impact": 0.6, "paper": 0.7}
sfx = np.zeros((N, 2), np.float32)
for ev in events:
    tm, kind, gain = ev[0], ev[1], ev[2]
    if kind == "riser":
        d = ev[3] or 2.0
        add(sfx, s_riser(d), tm - d, gain)
        continue
    x = MAKE[kind]()
    add(sfx, x, tm, gain * TRIM.get(kind, 1.0))
sfx = hp(sfx, 40)
pk = np.abs(sfx).max()
if pk > 0.7:
    sfx *= 0.7 / pk
sf.write(ROOT / "assets/audio/sfx.wav", sfx.astype(np.float32), SR, subtype="PCM_16")
print("music + sfx v2:", len(events), "events")
