"""v2 component library ('scrapbook noir'). Beats live in beats_v2.py; assembly in
build2.py. Edit the generators, never the generated HTML."""
import json
import math
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TR = json.loads((ROOT / "assets/transcript.json").read_text(encoding="utf-8"))["words"]
EDL = json.loads((ROOT / "work/edl/edl.json").read_text())
DUR = round(EDL["output_duration"], 3)
HOLDS = {h["tag"]: h for h in EDL["holds"]}
OUT = ROOT / "compositions" / "beats"
OUT.mkdir(parents=True, exist_ok=True)

BEATS, SFX, CLOSEUPS = [], [], []


# ------------------------------------------------------------------ anchors (validator-compatible)
def _n(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9/.\-]", " ", s.lower())).strip()


def _find(phrase, after=0.0):
    """same rule as scripts/validate-beat-sync.mjs (window startsWith; one-token substring)."""
    toks = phrase.lower().split()
    norm = _n(phrase)
    for i, w in enumerate(TR):
        if w["start"] < after:
            continue
        if _n(" ".join(x["text"] for x in TR[i:i + len(toks)])).startswith(norm):
            return i, len(toks)
        if len(toks) == 1 and norm.replace(" ", "") and norm.replace(" ", "") in _n(w["text"]).replace(" ", ""):
            return i, 1
    raise SystemExit(f"anchor not found: {phrase!r} after {after:.2f}")


def anchor_near(start):
    """a 2-4 word phrase whose first word starts in [start-0.2, start+1.8] and that the
    validator resolves to that same word (search from start-10)."""
    for i, w in enumerate(TR):
        if w["start"] < start - 0.2:
            continue
        if w["start"] > start + 1.8:
            break
        for k in (2, 3, 4):
            ph = " ".join(x["text"] for x in TR[i:i + k])
            if _n(ph) and abs(at(ph, max(0.0, start - 10)) - w["start"]) < 1e-6:
                return ph
    raise SystemExit(f"no anchor word near {start:.2f}")


def at(phrase, after=0.0):
    i, _ = _find(phrase, after)
    return TR[i]["start"]


def end(phrase, after=0.0):
    i, k = _find(phrase, after)
    return TR[i + k - 1]["end"]


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Beat:
    def __init__(self, bid, anchor, after=0.0, lead=0.4, until=None, dur=None, start=None, cam=None):
        self.id = bid
        if anchor is None:                       # explicit start: pick the validator anchor
            anchor = anchor_near(start)
            after = max(0.0, start - 10)
        self.anchor = anchor
        self.anchor_t = at(anchor, after)
        self.start = round(max(0.0, self.anchor_t - lead) if start is None else start, 3)
        self.dur = round(until - self.start, 3) if until is not None else dur
        self.cam = cam
        self.html, self.js = [], []
        self.layer = None
        self.wrap = None
        self.chain_out = False
        BEATS.append(self)

    def t(self, phrase, lead=0.2):
        return round(max(0.05, at(phrase, self.start - 1.0) - self.start - lead), 3)

    def sfx(self, rel, kind, gain=1.0, extra=None):
        SFX.append((self, rel, kind, gain, extra))


# ------------------------------------------------------------------ hand-drawn paths
def _rng(seed):
    return random.Random(seed)


def rline(x1, y1, x2, y2, seed=1, rough=2.2):
    """two slightly different strokes, gentle bow + jitter: reads as a marker line."""
    r = _rng(seed)
    out = []
    for p in range(2):
        L = math.hypot(x2 - x1, y2 - y1) or 1
        nx, ny = -(y2 - y1) / L, (x2 - x1) / L
        bow = r.uniform(-1, 1) * min(8, L * 0.02)
        pts = []
        n = max(4, int(L / 60))
        for k in range(n + 1):
            u = k / n
            j = r.uniform(-rough, rough) * (0.4 if k in (0, n) else 1)
            b = bow * math.sin(math.pi * u)
            pts.append((x1 + (x2 - x1) * u + nx * (b + j), y1 + (y2 - y1) * u + ny * (b + j)))
        d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
        for k in range(1, len(pts)):
            mx, my = (pts[k - 1][0] + pts[k][0]) / 2, (pts[k - 1][1] + pts[k][1]) / 2
            d += f" Q{pts[k - 1][0]:.1f},{pts[k - 1][1]:.1f} {mx:.1f},{my:.1f}"
        d += f" L{pts[-1][0]:.1f},{pts[-1][1]:.1f}"
        out.append(d)
    return out


def rpoly(points, seed=1, closed=False, rough=2.2):
    ds = []
    pts = list(points) + ([points[0]] if closed else [])
    for k in range(len(pts) - 1):
        ds += rline(*pts[k], *pts[k + 1], seed=seed * 31 + k, rough=rough)
    return ds


def rellipse(cx, cy, rx, ry, seed=1, overshoot=0.22):
    """loose marker circle that overshoots its start, like a real annotation."""
    r = _rng(seed)
    a0 = r.uniform(0, 2 * math.pi)
    n = 40
    pts = []
    for k in range(n + 1):
        a = a0 + (2 * math.pi + overshoot * 2 * math.pi) * k / n
        f = 1 + r.uniform(-0.04, 0.04) + 0.05 * math.sin(3 * a)
        pts.append((cx + rx * f * math.cos(a), cy + ry * f * math.sin(a)))
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}" + "".join(f" L{x:.1f},{y:.1f}" for x, y in pts[1:])
    return [d]


def rarrow(x1, y1, x2, y2, seed=1):
    ds = rline(x1, y1, x2, y2, seed)
    ang = math.atan2(y2 - y1, x2 - x1)
    for s in (-1, 1):
        a = ang + math.pi + s * 0.5
        ds += rline(x2, y2, x2 + 28 * math.cos(a), y2 + 28 * math.sin(a), seed + 7 + s)
    return ds


def rcheck(x, y, s=34, seed=1):
    return rline(x, y, x + s * 0.35, y + s * 0.4, seed) + rline(x + s * 0.35, y + s * 0.4, x + s, y - s * 0.55, seed + 3)


def rcross(x, y, s=30, seed=1):
    return rline(x, y, x + s, y + s, seed) + rline(x + s, y, x, y + s, seed + 5)


def svg(groups, cls="draw", w=1920, h=1080):
    """groups: [(class, [d...], stroke, width)] -> one svg; each path pathLength=1."""
    body = ""
    for gcls, ds, stroke, sw in groups:
        body += "".join(f'<path class="{gcls}" pathLength="1" d="{d}" stroke="{stroke}" stroke-width="{sw}"/>' for d in ds)
    return f'<svg class="{cls}" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{body}</svg>'


def draw(b, sel, rel, dur=0.6, stagger=0.0, ease="power1.inOut"):
    b.js.append(f"tl.fromTo($('{sel}'),{{strokeDasharray:1,strokeDashoffset:1}},"
                f"{{strokeDashoffset:0,duration:{dur},stagger:{stagger},ease:'{ease}'}},{rel});")


# ------------------------------------------------------------------ text helpers
def words(text, red=()):
    out = []
    for w in text.split(" "):
        cls = "w r" if w.strip(".,!?“”\"").upper() in {x.upper() for x in red} else "w"
        out.append(f'<span class="{cls}">{esc(w)}</span>')
    return " ".join(out)


def pop_words(b, sel, rel, stagger=0.07, mode=0):
    eases = ["back.out(1.5)", "expo.out", "power3.out"]
    if mode == 0:
        b.js.append(f"tl.from($('{sel} .w'),{{y:46,opacity:0,duration:.5,stagger:{stagger},ease:'{eases[0]}'}},{rel});")
    elif mode == 1:
        b.js.append(f"tl.from($('{sel} .w'),{{x:-30,opacity:0,duration:.45,stagger:{stagger},ease:'{eases[1]}'}},{rel});")
    else:
        b.js.append(f"tl.from($('{sel} .w'),{{scale:1.35,opacity:0,duration:.35,stagger:{stagger},ease:'{eases[2]}'}},{rel});")


def caption(b, label, big, red=(), rel_big=None, mode=0, impact=False):
    """reference-style caption: red label then heavy uppercase line, bottom centre."""
    lab = f'<div class="lab cl">{esc(label)}</div>' if label else ""
    b.html.append(f'<div class="cap">{lab}<div class="big cb">{words(big, red)}</div></div>')
    if label:
        b.js.append("tl.from($('.cl'),{clipPath:'inset(0 100% 0 0)',duration:.35,ease:'power2.out'},.05);")
    rb = 0.25 if rel_big is None else rel_big
    pop_words(b, ".cb", rb, 0.06, mode)
    b.js.append("tl.to($('.cap'),{y:26,opacity:0,duration:.3,ease:'power2.in'},__END-0.36__);")
    b.sfx(0.04, "swish", 0.5)
    if impact:
        b.sfx(rb, "impact", 0.7)


def side(b, html, where="right"):
    """negative-space text beside the speaker; camera slides the speaker the other way."""
    b.html.append(f'<div class="side {where}">{html}</div>')
    b.cam = "side_l" if where == "right" else "side_r"
    b.js.append("tl.to($('.side'),{x:" + ("30" if where == "right" else "-30") +
                ",opacity:0,duration:.35,ease:'power2.in'},__END-0.42__);")


def full(b, inner, chain_in=False, chain_out=False, cut=False):
    """full-screen board. build2 wraps the beat in .take, the element that wipes, so
    screenshots and notes placed beside the .full board are clipped with it.
    cut=True: hard cut in and out (a punch card such as 'why not?')."""
    b.html.append(inner)
    b.wrap = "full"
    b.cam = "full"
    b.chain_out = chain_out
    if cut:
        return
    if not chain_in:
        b.js.append("tl.fromTo($('.take'),{clipPath:'inset(0 0 0 100%)'},{clipPath:'inset(0 0 0 0%)',duration:.5,ease:'power3.inOut'},0);")
        b.sfx(0.0, "whoosh", 0.8)
    if not chain_out:
        b.js.append("tl.to($('.take'),{clipPath:'inset(0 100% 0 0%)',duration:.48,ease:'power3.inOut'},__END-0.5__);")
        b.sfx("END-0.5", "whoosh", 0.5)


def enter(b, sel, rel, k=0):
    E = ["{y:40,opacity:0,duration:.55,ease:'expo.out'}",
         "{x:60,opacity:0,duration:.5,ease:'power3.out'}",
         "{clipPath:'inset(0 100% 0 0)',duration:.6,ease:'power2.out'}",
         "{scale:.86,opacity:0,duration:.45,ease:'back.out(1.6)'}",
         "{rotation:-6,y:30,opacity:0,duration:.55,ease:'power3.out'}"]
    b.js.append(f"tl.from($('{sel}'),{E[k % len(E)]},{rel});")


def typewriter(b, text, cls, rel, cps=20, sfx_gain=0.55):
    """returns html of per-character spans; reveals them one by one with key clicks."""
    spans = "".join(f'<span class="{cls}-c" style="opacity:0">{esc(ch) if ch != " " else "&nbsp;"}</span>'
                    for ch in text)
    for k, ch in enumerate(text):
        t = round(rel + k / cps, 3)
        b.js.append(f"tl.set($('.{cls}-c:nth-child({k + 1})'),{{opacity:1}},{t});")
        if ch != " ":
            b.sfx(t, "key", sfx_gain * (0.8 + 0.4 * ((k * 37) % 7) / 7))
    return spans, rel + len(text) / cps


def counter(b, sel, frm, to, rel, dur, fmt):
    b.js.append(
        f"(()=>{{const el=document.querySelector($('{sel}'));const o={{v:{frm}}};"
        f"tl.to(o,{{v:{to},duration:{dur},ease:'power2.out',onUpdate(){{el.textContent={fmt}(o.v)}}}},{rel});}})();")
    for k in range(6):
        b.sfx(rel + k * dur / 7, "tick", 0.3)


# ------------------------------------------------------------------ screenshots
SHOT = {"claude-pricing-crop": (3200, 1800), "cursor-home": (3200, 2000), "vercel-home": (3200, 2000),
        "vercel-pricing": (3200, 2000), "supabase-home": (3200, 2000), "supabase-pricing": (3200, 2000),
        "gemini-flash": (3200, 2000), "gemini-pricing": (3200, 2000),
        "xendit-home-hero": (3200, 1440), "midtrans-home-hero": (3200, 1440)}


def framing(shot, vw, vh, rect=None):
    iw, ih = SHOT[shot]
    if rect is None:
        return round(vw / iw, 4), 0.0, 0.0
    x0, y0, x1, y1 = rect
    s = max(min(vw / (x1 - x0), vh / (y1 - y0)), vw / iw)
    x = min(0, max(vw - iw * s, vw / 2 - (x0 + x1) / 2 * s))
    y = min(0, max(vh - ih * s, vh / 2 - (y0 + y1) / 2 * s))
    return round(s, 4), round(x, 1), round(y, 1)


def shot(b, cls, name, left, top, w, h, rot=-1.5, moves=((0, None, 0),), marks=(), circles=(), tape=True):
    """real screenshot taped to the board; marks = [(rel, rect)] yellow highlighter sweeps,
    circles = [(rel, rect)] red marker ellipses (both in screenshot pixel coords)."""
    iw, ih = SHOT[name]
    inner = "".join(f'<div class="mark m{k}" style="left:{r[0]}px;top:{r[1]}px;width:{r[2] - r[0]}px;height:{r[3] - r[1]}px"></div>'
                    for k, (_, r) in enumerate(marks))
    circ = ""
    for k, (_, r) in enumerate(circles):
        cx, cy, rx, ry = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2, (r[2] - r[0]) / 2 + 30, (r[3] - r[1]) / 2 + 26
        circ += svg([(f"c{k}", rellipse(cx, cy, rx, ry, seed=k + 11), "#E3262F", 12)], cls="draw", w=iw, h=ih)
    tapes = (f'<div class="tape" style="left:{w * 0.08:.0f}px;top:-18px;transform:rotate(-8deg)"></div>'
             f'<div class="tape" style="left:{w * 0.78:.0f}px;top:-16px;transform:rotate(6deg)"></div>') if tape else ""
    b.html.append(f'<div class="shotwrap {cls}" style="position:absolute;left:{left}px;top:{top}px;width:{w}px;height:{h}px;'
                  f'transform:rotate({rot}deg)"><div class="shot" style="left:0;top:0;width:{w}px;height:{h}px">'
                  f'<div class="img"><img src="assets/shots/{name}.jpg" width="{iw}" height="{ih}">{inner}{circ}</div></div>'
                  f'{tapes}</div>')
    s, x, y = framing(name, w, h, moves[0][1])
    b.js.append(f"tl.set($('.{cls} .img'),{{scale:{s},x:{x},y:{y}}},0);")
    for rel, rect, d in moves[1:]:
        s, x, y = framing(name, w, h, rect)
        b.js.append(f"tl.to($('.{cls} .img'),{{scale:{s},x:{x},y:{y},duration:{d},ease:'power2.inOut'}},{rel});")
    for k, (rel, _) in enumerate(marks):
        b.js.append(f"tl.from($('.{cls} .m{k}'),{{scaleX:0,duration:.45,ease:'power2.out'}},{rel});")
        b.sfx(rel, "marker", 0.6)
    for k, (rel, _) in enumerate(circles):
        draw(b, f".{cls} .c{k}", rel, 0.55)
        b.sfx(rel, "scribble", 0.6)


def logo(name, h, navy=False, cls=""):
    return f'<div class="logo{" navy" if navy else ""} {cls}"><img src="assets/logos/{name}.png" style="height:{h}px"></div>'


def nota_html(cls, lines, left, top, rot=0, w=400, blur=False, header="NOTA SUPPLIER"):
    rows = "".join(('<div class="dash"></div>' if ln == "-" else
                    f'<div class="ln {"blur" if blur else ""} r{k}"><span>{esc(ln[0])}</span><span>{esc(ln[1])}</span></div>')
                   for k, ln in enumerate(lines))
    return (f'<div class="nota {cls}" style="left:{left}px;top:{top}px;width:{w}px;transform:rotate({rot}deg)">'
            f'<div class="hd">{header}</div><div class="dash"></div>{rows}</div>')


PAPERCLIP = ('<svg width="70" height="150" viewBox="0 0 70 150" style="position:absolute;{pos}">'
             '<path d="M22 140 L22 30 Q22 8 40 8 Q58 8 58 30 L58 118 Q58 136 42 136 Q28 136 28 118 L28 40" '
             'fill="none" stroke="#9EA3A8" stroke-width="7" stroke-linecap="round"/></svg>')


# ------------------------------------------------------------------ chapter card (breather)
CHAPTERS = [("01", "Sumber kebocoran"), ("02", "Bikin aplikasinya"), ("03", "Hitung cuan"), ("04", "Orang lapangan")]


def chapter_card(b, idx, title, sub=None, chapter_label=None):
    """typewritten paper on the board, index of chapters on top (open loop re-show)."""
    idxs = "".join(
        f'<span style="margin-right:46px;color:{"#E3262F" if k == idx else ("rgba(244,241,234,.75)" if k < idx else "rgba(244,241,234,.32)")}">'
        f'{"&#10003; " if 0 <= k < idx else ""}{n} {esc(t.upper())}</span>' for k, (n, t) in enumerate(CHAPTERS))
    spans, t_end = typewriter(b, title.upper(), "tw", 0.75, cps=19)
    label = chapter_label or (f"CHAPTER {CHAPTERS[idx][0]}" if idx >= 0 else "")
    sub_html = f'<div class="hand red sub" style="margin-top:22px;font-size:58px">{esc(sub)}</div>' if sub else ""
    full(b, '<div class="full">'
            f'<div class="kick idx" style="position:absolute;left:96px;top:64px">{idxs}</div>'
            '<div class="sheet paper" style="left:430px;top:250px;width:1060px;height:600px;transform:rotate(-2.2deg)">'
            + PAPERCLIP.format(pos="left:70px;top:-38px") +
            f'<div class="typ tred lblc" style="position:absolute;left:120px;top:88px;font-size:34px;letter-spacing:.08em">{label}</div>'
            f'<div class="typ title" style="position:absolute;left:120px;top:170px;right:90px">{spans}'
            '<span class="cur" style="display:inline-block;width:.55em;height:.9em;background:#1F1E1C;vertical-align:-.08em;margin-left:4px"></span></div>'
            f'<div style="position:absolute;left:120px;top:430px;right:90px">{sub_html}</div>'
            '</div></div>')
    b.js.append("tl.from($('.idx'),{opacity:0,y:-12,duration:.4,ease:'power2.out'},.2);"
                "tl.from($('.sheet'),{y:520,rotation:7,duration:.75,ease:'expo.out'},.12);"
                "tl.from($('.lblc'),{opacity:0,duration:.01},.6);")
    b.js.append(f"tl.to($('.cur'),{{opacity:0,duration:.01,repeat:{int((b.dur) / 0.5)},yoyo:true,repeatDelay:.24}},.6);")
    if sub:
        b.js.append(f"tl.from($('.sub'),{{clipPath:'inset(0 100% 0 0)',duration:.6,ease:'power1.inOut'}},{t_end + 0.1:.3f});")
        b.sfx(t_end + 0.1, "scribble", 0.5)
    b.sfx(0.12, "paper", 0.8)
    b.sfx(t_end + 0.05, "ding", 0.6)
    b.sfx(0.0, "impact", 0.9)
