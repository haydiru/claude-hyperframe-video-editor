"""v2 story beats ('scrapbook noir'), modelled on the user's reference edit:
red-label captions, negative-space side text, typewriter chapter cards on the
breather holds, taped screenshots with highlighter, hand-drawn marks. Variety is
deliberate: talking stretches are left clean between graphic moments.

Times come from assets/transcript.json (cut timeline). Edit here, then
  python scripts/build2.py
"""
from hflib2 import *  # noqa: F401,F403

INK, RED = "#F4F1EA", "#E3262F"


# ================================================================ assets + helpers
def _store_svg():
    ds = (rpoly([(16, 36), (84, 36), (78, 18), (22, 18)], seed=3, closed=True, rough=1.0)
          + rpoly([(22, 36), (22, 86), (78, 86), (78, 36)], seed=5, rough=1.0)
          + rpoly([(42, 86), (42, 60), (58, 60), (58, 86)], seed=7, rough=0.8)
          + rline(34, 18, 31, 36, seed=9, rough=.6) + rline(50, 18, 50, 36, seed=10, rough=.6)
          + rline(66, 18, 69, 36, seed=11, rough=.6))
    body = "".join(f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="4" stroke-linecap="round" '
                   f'stroke-linejoin="round"/>' for d in ds)
    (ROOT / "assets/store.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">{body}</svg>', encoding="utf-8")


_store_svg()


def ick(cls, seed=1, color="#FF4A4F"):
    """inline hand-drawn check (draw it with draw(b, '.cls path', rel))."""
    return (f'<svg class="{cls}" width="44" height="44" viewBox="0 0 44 44" style="overflow:visible;flex:none">'
            + "".join(f'<path pathLength="1" d="{d}" fill="none" stroke="{color}" stroke-width="5" '
                      f'stroke-linecap="round"/>' for d in rcheck(5, 24, 33, seed)) + '</svg>')


def icx(cls, seed=1, color="#FF4A4F"):
    return (f'<svg class="{cls}" width="44" height="44" viewBox="0 0 44 44" style="overflow:visible;flex:none">'
            + "".join(f'<path pathLength="1" d="{d}" fill="none" stroke="{color}" stroke-width="5" '
                      f'stroke-linecap="round"/>' for d in rcross(8, 8, 28, seed)) + '</svg>')


def side_free(b, html, where="right"):
    """absolutely positioned side content (frame coordinates); camera moves the speaker away."""
    b.html.append(f'<div class="sf" style="position:absolute;inset:0">{html}</div>')
    b.cam = "side_l" if where == "right" else "side_r"
    b.js.append("tl.to($('.sf'),{x:" + ("40" if where == "right" else "-40") +
                ",opacity:0,duration:.35,ease:'power2.in'},__END-0.42__);")


def reveal(b, sel, rel, kind="up"):
    tw = {"up": "{y:34,opacity:0,duration:.5,ease:'expo.out'}",
          "clip": "{clipPath:'inset(0 100% 0 0)',duration:.55,ease:'power2.out'}",
          "pop": "{scale:.7,opacity:0,duration:.4,ease:'back.out(1.8)'}",
          "left": "{x:-40,opacity:0,duration:.45,ease:'power3.out'}",
          "fade": "{opacity:0,duration:.35,ease:'power1.out'}",
          "drop": "{y:-60,rotation:-4,opacity:0,duration:.55,ease:'expo.out'}"}[kind]
    b.js.append(f"tl.from($('{sel}'),{tw},{rel:.3f});")


def hand_at(b, cls, text, left, top, rel, size=58, red=True, rot=-2):
    b.html.append(f'<div class="hand {"red " if red else ""}{cls}" style="position:absolute;left:{left}px;top:{top}px;'
                  f'font-size:{size}px;transform:rotate({rot}deg);white-space:nowrap">{esc(text)}</div>')
    reveal(b, f".{cls}", rel, "clip")
    b.sfx(rel, "scribble", 0.45)


def card_start(tag):
    h0 = HOLDS[tag]["start"]
    last = max((w for w in TR if w["start"] < h0 - 0.05), key=lambda w: w["start"])
    return round(min(h0 - 0.1, last["start"] + 0.18), 3)


def hold_card(tag, idx, title, sub=None, label=None, tail=0.6):
    """chapter card over a breather hold: enters on the last word, leaves as speech resumes."""
    h = HOLDS[tag]
    st = card_start(tag)
    b = Beat(f"k-{tag}", None, start=st)
    b.dur = round(h["start"] + h["dur"] + tail - st, 3)
    chapter_card(b, idx, title, sub, label)
    b.sfx(0.0, "riser", 0.34, 1.3)
    b.hold = (h["start"], h["start"] + h["dur"])
    return b


def li_rows(rows, size=46):
    """rows: [(cls, icon_html_or_text, text)]"""
    return ('<div class="lst">' + "".join(
        f'<div class="li {c}" style="font-size:{size}px;position:relative"><span class="n">{n}</span>'
        f'<span class="tx">{esc(t)}</span></div>' for c, n, t in rows) + '</div>')


# ---------------------------------------------------------------- the 5-step staircase
STEPS = [("KODE", "claude", 38, "≈Rp300 rb"), ("WEBSITE", "vercel", 40, "Rp0"),
         ("DATABASE", "supabase", 36, "Rp0"), ("BACA NOTA", "gemini", 36, "±Rp1 rb/bln"),
         ("PEMBAYARAN", "xendit", 30, "per transaksi")]
SX, SW, SY, SR = 170, 316, 880, 112


def _step_xy(k):
    return SX + k * SW + 22, SY - (k + 1) * SR


def stair(b, active=None, done=(), header=None, intro=False, costs=False):
    """hand-drawn staircase; active step circled in red, done steps ticked, later steps dim."""
    pts = [(SX, SY), (SX, SY - SR)]
    for k in range(5):
        xe, y = SX + (k + 1) * SW, SY - (k + 1) * SR
        pts.append((xe, y))
        if k < 4:
            pts.append((xe, y - SR))
    pts.append((SX + 5 * SW, SY))
    groups = [("ol", rpoly(pts, seed=21, closed=True, rough=2.4), INK, 5)]
    if active is not None:
        x, y = _step_xy(active)
        groups.append(("ea", rellipse(x + 130, y - 92, 172, 92, seed=active + 3), RED, 9))
    for k in done:
        x, y = _step_xy(k)
        groups.append((f"ck{k}", rcheck(x + 232, y - 120, 42, seed=k + 40), RED, 8))
    labels = ""
    for k, (lab, lg, lh, cost) in enumerate(STEPS):
        x, y = _step_xy(k)
        logos = logo(lg, lh) if k != 4 else logo("xendit", lh) + logo("midtrans", lh - 4, navy=True)
        labels += (f'<div class="stp s{k}" style="left:{x}px;top:{y - 186}px"><div class="sn">LANGKAH {k + 1}</div>'
                   f'<div class="sl">{lab}</div><div style="display:flex;gap:8px">{logos}</div></div>')
        if costs:
            labels += f'<div class="stp cs{k}" style="left:{x}px;top:{y + 26}px"><div class="sc">{esc(cost)}</div></div>'
    head = ""
    if header:
        head = (f'<div style="position:absolute;left:96px;top:66px"><div class="kick">5 langkah bikin aplikasinya</div>'
                f'<div class="hl2" style="margin-top:12px;font-size:92px">LANGKAH {header}<span class="dim">/5</span></div></div>')
    b.html.append(f'<div class="stair" style="position:absolute;inset:0">{svg(groups)}{labels}{head}</div>')
    if intro:
        draw(b, ".stair .ol", 0.35, 0.2, 0.045)
        b.js.append("tl.from($('.stair .stp'),{y:24,opacity:0,duration:.45,stagger:.16,ease:'expo.out'},.9);")
        for k in range(5):
            b.sfx(0.9 + 0.16 * k, "pop", 0.4)
        b.sfx(0.35, "scribble", 0.5, None)
    else:
        draw(b, ".stair .ol", 0.12, 0.18, 0.012)
        b.js.append("tl.from($('.stair .stp'),{opacity:0,duration:.3,stagger:.04},.18);")
        if header:
            reveal(b, ".stair .hl2", 0.25, "clip")
    for n, k in enumerate(done):
        draw(b, f".stair .ck{k}", 0.55 + 0.12 * n, 0.25)
    return b


def activate(b, k, rel, dim_later=True):
    draw(b, ".stair .ea", rel, 0.55)
    b.js.append(f"tl.to($('.stair .s{k} .sl'),{{color:'#FF4A4F',duration:.2}},{rel:.3f});")
    b.sfx(rel, "scribble", 0.6)
    if dim_later:
        for j in range(k + 1, 5):
            b.js.append(f"tl.to($('.stair .s{j}'),{{opacity:.28,duration:.3}},{rel:.3f});")


def board(kick=None, extra=""):
    k = f'<div class="kick" style="position:absolute;left:96px;top:62px">{kick}</div>' if kick else ""
    return f'<div class="full">{k}{extra}</div>'


def phone(cls, notifs, left, top, extra=""):
    ns = "".join(f'<div class="notif {c}" style="top:{t}px"><div class="app"><i class="ico" style="background:{col}"></i>'
                 f'{esc(app)}</div>{body}{f"<div class=btn>{esc(btn)}</div>" if btn else ""}</div>'
                 for c, t, app, col, body, btn in notifs)
    return (f'<div class="phone {cls}" style="left:{left}px;top:{top}px"><div class="scr"></div>'
            f'<div class="clock">09.41</div>{ns}{extra}</div>')


NOTA_LINES = [("MINYAK GORENG 2L", "36.500"), ("MIE INSTAN / DUS", "112.000"), ("GULA PASIR 1KG", "17.800"),
              ("KECAP MANIS 520ML", "19.900"), "-", ("TOTAL", "2.481.200")]


# ================================================================ HOOK
b = Beat("h01-who", "Kalau lo punya usaha", lead=0.27, until=at("ini video buat lo") - 0.12)
side(b, '<div class="kick k0">kalau lo punya usaha</div>'
        + li_rows([("l0", "&mdash;", "Minimarket"), ("l1", "&mdash;", "Toko kelontong"), ("l2", "&mdash;", "Grosir")])
        + '<div class="sm s1" style="margin-top:10px">atau lagi cari</div><div class="xl x1">IDE SOFTWARE</div>'
          '<div class="hand red h1">pasarnya jutaan orang.</div>', "right")
reveal(b, ".k0", 0.15, "fade")
for k, ph in enumerate(["minimarket,", "toko kelontong,", "grosir,"]):
    r = b.t(ph, 0.15)
    reveal(b, f".l{k}", r, "left")
    b.sfx(r, "tick", 0.5)
reveal(b, ".s1", b.t("atau lo lagi", 0.15), "fade")
r = b.t("ide software", 0.15)
reveal(b, ".x1", r, "clip")
b.sfx(r, "swish", 0.5)
reveal(b, ".h1", b.t("jutaan orang", 0.1), "clip")
b.sfx(b.t("jutaan orang", 0.1), "scribble", 0.45)
CLOSEUPS.append((at("ini video buat lo"), 2.0))

b = Beat("h02-kas", "100 -200 ribu", lead=0.6, until=at("satu hal sepele") - 0.12)
full(b, board(None, '<div class="ctr" style="top:330px"><div class="kick k1">uang kas toko</div>'
                    '<div class="num n1" style="font-size:200px;margin-top:30px">Rp100&ndash;200 RB</div>'
                    '<div class="unit u1" style="margin-top:24px">menguap <span class="redt">setiap hari.</span></div></div>'
                    + svg([("ar", rarrow(205, 380, 205, 640, seed=4), RED, 9)])))
reveal(b, ".k1", 0.3, "fade")
r = 0.45
reveal(b, ".n1", r, "clip")
b.sfx(r, "impact", 0.6)
draw(b, ".ar", r + 0.2, 0.45)
reveal(b, ".u1", b.t("ribu per hari", 0.1), "up")

b = Beat("h03-sepele", "satu hal sepele", lead=0.3, until=at("yaitu pemasok") - 0.12)
caption(b, "PENYEBABNYA?", "SATU HAL SEPELE.", red=("SEPELE",), rel_big=b.t("satu hal", 0.1), mode=2)

b = Beat("h04-pemasok", "yaitu pemasok", lead=0.3, until=card_start("title") + 0.45)
nota = nota_html("hn", NOTA_LINES, 170, 200, -4, 460, False, "FAKTUR PEMASOK")
nota = nota[:-6] + svg([("hc", rellipse(390, 110, 72, 27, seed=6), RED, 7)], w=460, h=330) + nota[-6:]
side_free(b, nota + svg([("ha", rarrow(330, 640, 420, 560, seed=12), RED, 7)]), "left")
reveal(b, ".hn", 0.2, "drop")
b.sfx(0.2, "paper", 0.7)
r = b.t("diam -diam naik", 0.1)
draw(b, ".hc", r, 0.55)
b.sfx(r, "scribble", 0.6)
hand_at(b, "hd1", "naik diam-diam!", 190, 650, r + 0.3, 66)
draw(b, ".ha", r + 0.55, 0.35)
hand_at(b, "hd2", "...nggak sempat dicek.", 190, 730, b.t("tanpa sempat", 0.1), 52, red=False)

hold_card("title", -1, "NOTA YANG BOCOR", "& cara bikin aplikasinya", label="IDE SOFTWARE")

# ================================================================ OVERVIEW
b = Beat("o01-four", "di video ini kita", lead=0.35, until=card_start("ch1") + 0.45)
side(b, '<div class="kick k1">di video ini</div><div class="xl x1">4 HAL PENTING</div><div style="height:8px"></div>'
        + li_rows([("l0", "01", "Sumber kebocoran kas"), ("l1", "02", "Bikin aplikasinya pakai AI"),
                   ("l2", "03", "Potensi cuan langganan"), ("l3", "04", "Lapangan vs programmer")], 40), "right")
reveal(b, ".k1", 0.2, "fade")
reveal(b, ".x1", 0.35, "clip")
b.sfx(0.35, "swish", 0.5)
prev = None
for k, ph in enumerate(["Yang pertama,", "Kedua,", "Ketiga,", "Dan yang terakhir,"]):
    r = b.t(ph, 0.2)
    reveal(b, f".l{k}", r, "left")
    b.js.append(f"tl.to($('.l{k} .n'),{{color:'#FF4A4F',duration:.2}},{r:.3f});")
    if prev is not None:
        b.js.append(f"tl.to($('.l{prev}'),{{opacity:.42,duration:.3}},{r:.3f});")
    prev = k
    b.sfx(r, "tick", 0.55)

hold_card("ch1", 0, "SUMBER KEBOCORAN", "yang sering nggak disadari")

# ================================================================ CHAPTER 1
CLOSEUPS.append((at("tahu persis masalahnya"), 1.8))

b = Beat("c1a-jam11", "Jam 11 siang", lead=0.35, until=at("Mereka kasih kertas") - 0.2)
caption(b, "JAM 11 SIANG", "TOKO LAGI RAME-RAMENYA.", red=("RAME-RAMENYA",), rel_big=b.t("toko lagi rame", 0.1))

b = Beat("c1b-nota", "Mereka kasih kertas nota", lead=0.3, until=at("padahal margin retail") - 0.3)
full(b, board("nota supplier &middot; rangkap 3"))
b.html.append('<div class="stk" style="position:absolute;inset:0">'
              + nota_html("na", NOTA_LINES, 250, 250, -8, 430, False, "NOTA / FAKTUR")
              + nota_html("nb", NOTA_LINES, 430, 225, -1.5, 430, False, "NOTA / FAKTUR")
              + nota_html("nc", NOTA_LINES, 610, 245, 5, 430, False, "NOTA / FAKTUR")
              + '<div class="tape" style="left:740px;top:222px;transform:rotate(4deg)"></div></div>')
b.js.append("tl.set($('.na'),{background:'#F3D9DE'},0);tl.set($('.nb'),{background:'#F2E6B8'},0);")
r0 = b.t("rangkap", 0.35)
for k, c in enumerate(["na", "nb", "nc"]):
    r = 0.45 if k == 0 else r0 + 0.22 * (k - 1)
    reveal(b, f".{c}", r, "drop")
    b.sfx(r, "paper", 0.55)
b.html.append(svg([("ra", rarrow(300, 205, 420, 260, seed=14), RED, 7)]))
hand_at(b, "rk", "rangkap 3", 110, 140, r0 + 0.7, 62)
draw(b, ".ra", r0 + 1.0, 0.35)
r = b.t("tipis dan buram", 0.05)
b.js.append(f"tl.to($('.stk .ln'),{{filter:'blur(2.4px)',opacity:.5,duration:1.1,ease:'power1.inOut'}},{r:.3f});")
b.html.append('<div class="rt" style="position:absolute;left:1180px;top:300px">'
              '<div class="num j1">2 JAM</div><div class="unit j2" style="margin-top:12px">tiap malam</div>'
              '<div class="hand red j3" style="margin-top:26px;font-size:62px">buat nyocokin 50 barang</div></div>')
r = b.t("2 jam tiap", 0.15)
reveal(b, ".j1", r, "clip")
b.sfx(r, "thud", 0.5)
reveal(b, ".j2", r + 0.35, "up")
r = b.t("50 barang", 0.2)
reveal(b, ".j3", r, "clip")
b.sfx(r, "scribble", 0.45)
b.html.append('<div class="drw" style="position:absolute;left:200px;top:850px;width:900px;height:240px;'
              'background:linear-gradient(#1f1f21,#141415);border-top:3px solid rgba(244,241,234,.55);'
              'box-shadow:0 -14px 30px rgba(0,0,0,.45)"><div class="kick" style="position:absolute;left:0;right:0;'
              'top:42px;text-align:center;color:rgba(244,241,234,.75)">laci kasir</div></div>')
r = b.t("dikumpulkan di laci", 0.3)
reveal(b, ".drw", r, "up")
b.js.append(f"tl.to($('.rt'),{{opacity:0,duration:.3}},{r:.3f});"
            f"tl.to($('.stk'),{{y:640,duration:.85,ease:'power2.in'}},{r + 0.35:.3f});")
b.sfx(r + 1.15, "thud", 0.6)
hand_at(b, "lc", "...numpuk di laci.", 1180, 520, r + 1.0, 70, red=False)

b = Beat("c1c-margin", "padahal margin retail", lead=0.3, until=at("Kalau supplier naikin") - 0.25)
side(b, '<div class="kick k1">margin kebutuhan pokok</div>'
        '<div class="stamp s1" style="align-self:flex-start;margin-top:8px">SANGAT TIPIS.</div>'
        '<div class="num p1" style="margin-top:22px">8&ndash;10%</div><div class="unit u1">rata-rata</div>', "right")
reveal(b, ".k1", 0.2, "fade")
r = b.t("sangat tipis", 0.1)
reveal(b, ".s1", r, "pop")
b.sfx(r, "thud", 0.55)
r = b.t("cuma 8", 0.1)
reveal(b, ".p1", r, "clip")
reveal(b, ".u1", r + 0.3, "up")
b.sfx(r, "tick", 0.5)

CLOSEUPS.append((at("lu telat ngupdate"), 1.8))
b = Beat("c1d-nombok", "tapi sebenarnya kalian", lead=0.25, until=at("untuk toko dengan omset") - 0.45)
caption(b, "TANPA SADAR", "LO NOMBOKIN MODAL SUPPLIER.", red=("NOMBOKIN",), rel_big=b.t("lagi nombokin", 0.1))

b = Beat("c1e-calc", "untuk toko dengan omset", lead=0.3, until=at("setahun bisa nembus") - 0.2)
side(b, '<div class="kick k1">toko dengan omset</div>'
        '<div class="xl o1">Rp300 JT<span class="unit" style="margin-left:16px">/ bulan</span></div>'
        '<div class="hl2 dim o2" style="margin-top:6px">&times; 1,5&ndash;2,5%</div>'
        '<div class="hl2 o3" style="margin-top:10px"><span class="blk">= Rp4,5&ndash;7,5 JT</span></div>'
        '<div class="hand red o4" style="margin-top:6px">bocor tiap bulan.</div>', "left")
reveal(b, ".k1", 0.2, "fade")
r = b.t("omset 300", 0.1)
reveal(b, ".o1", r, "clip")
b.sfx(r, "swish", 0.4)
r = b.t("total 1", 0.1)
reveal(b, ".o2", r, "left")
b.sfx(r, "tick", 0.5)
r = b.t("setara 4", 0.1)
reveal(b, ".o3", r, "pop")
b.sfx(r, "cash", 0.5)
reveal(b, ".o4", r + 1.3, "clip")

b = Beat("c1f-year", "setahun bisa nembus", lead=0.15, until=at("ini gara -gara kertas") - 0.3)
full(b, board(None, '<div class="ctr" style="top:270px"><div class="kick k1">kalau dihitung setahun</div>'
                    '<div class="num y1" style="font-size:210px;margin-top:30px">Rp54&ndash;90 JT</div>'
                    '<div class="unit y2" style="margin-top:26px">hilang dari kas. <span class="redt">diam-diam.</span></div></div>'
                    + svg([("ul", rline(600, 640, 1320, 650, seed=8), RED, 10)])))
reveal(b, ".k1", 0.3, "fade")
r = max(0.5, b.t("nembus 54", 0.45))
reveal(b, ".y1", r, "clip")
b.sfx(r, "riser", 0.4, 1.1)
b.sfx(r, "impact", 0.8)
b.sfx(r + 0.15, "cash", 0.55)
reveal(b, ".y2", r + 0.6, "up")
draw(b, ".ul", r + 1.1, 0.45)
b.sfx(r + 1.1, "marker", 0.5)

b = Beat("c1g-root", "ini gara -gara kertas", lead=0.25, until=card_start("ch2") + 0.45)
caption(b, "AKAR MASALAHNYA", "NOTA NGGAK KEBACA.", red=("KEBACA",), rel_big=b.t("nggak kebaca", 0.1), impact=True)

hold_card("ch2", 1, "BIKIN APLIKASINYA", "dari nol, pakai AI")

# ================================================================ CHAPTER 2
b = Beat("c2a-dulu", "pilihannya sebenarnya cuma", lead=0.3, until=at("biar kebayang dan") - 0.35)
strike = lambda c, s: svg([(c, rline(56, 26, 700, 70, seed=s, rough=3), RED, 9)], w=740, h=100)
side(b, '<div class="kick k1">dulu, pilihannya cuma dua:</div>'
        '<div class="lst">'
        f'<div class="li l0" style="position:relative"><span class="n">01</span><span>Belajar coding bertahun-tahun</span>{strike("sk0", 3)}</div>'
        f'<div class="li l1" style="position:relative"><span class="n">02</span><span>Bayar engineer puluhan juta</span>{strike("sk1", 5)}</div>'
        '</div><div class="stamp s1" style="align-self:flex-start;margin-top:26px;font-size:54px">SEKARANG: SENDIRI.</div>', "right")
reveal(b, ".k1", 0.2, "fade")
for k, ph in enumerate(["belajar coding", "keluar modal"]):
    r = b.t(ph, 0.15)
    reveal(b, f".l{k}", r, "left")
    b.sfx(r, "tick", 0.5)
r = b.t("Tapi sekarang kamu", 0.0)
draw(b, ".sk0", r, 0.35)
draw(b, ".sk1", r + 0.3, 0.35)
b.sfx(r, "scribble", 0.6)
b.sfx(r + 0.3, "scribble", 0.5)
b.js.append(f"tl.to($('.l0,.l1'),{{opacity:.55,duration:.3}},{r + 0.5:.3f});")
r = b.t("sendiri dari nol", 0.1)
reveal(b, ".s1", r, "pop")
b.sfx(r, "impact", 0.55)

b = Beat("c2b-steps", "cuma butuh 5", lead=0.4, until=at("di sini kita pakai") - 0.2)
full(b, board(None, '<div style="position:absolute;left:96px;top:66px"><div class="kick">5 langkah praktis</div>'
                    '<div class="hl2" style="margin-top:12px;font-size:92px">BIKIN APLIKASINYA</div></div>'))
stair(b, active=0, intro=True)
activate(b, 0, b.t("Langkah pertama,", 0.1))

b = Beat("c2c-tools", "di sini kita pakai", lead=0.3, until=at("Ceritain alur kerja") - 0.3)
side(b, '<div class="kick k1">langkah 1 &middot; nulis kodenya</div>'
        '<div class="g1" style="align-self:flex-start;position:relative;transform:rotate(-3deg);margin-top:18px">'
        + logo("claude", 66) + '<div class="tape" style="left:110px;top:-22px;transform:rotate(-5deg)"></div></div>'
        '<div class="hand o1" style="margin:8px 0 0 40px">atau</div>'
        '<div class="g2" style="align-self:flex-start;position:relative;transform:rotate(2deg);margin-left:70px">'
        + logo("cursor", 62) + '<div class="tape" style="left:90px;top:-22px;transform:rotate(6deg)"></div></div>', "right")
reveal(b, ".k1", 0.2, "fade")
r = b.t("Claude atau", 0.15)
reveal(b, ".g1", r, "drop")
b.sfx(r, "paper", 0.6)
reveal(b, ".o1", r + 0.35, "fade")
r = b.t("Cursor.", 0.15)
reveal(b, ".g2", r, "drop")
b.sfx(r, "paper", 0.55)

b = Beat("c2d-prompt", "Ceritain alur kerja", lead=0.35, until=at("modalnya cuma satu") - 0.3)
html = ('<div class="paper pp" style="left:110px;top:160px;width:800px;height:620px;transform:rotate(-1.4deg)">'
        + PAPERCLIP.format(pos="left:64px;top:-40px")
        + '<div class="typ tred" style="position:absolute;left:70px;top:72px;font-size:28px;letter-spacing:.08em">CHAT KE AI:</div>')
checks = []
for k, (ph, txt) in enumerate([("Ceritain alur kerja", "> CERITAIN ALUR KERJA TOKO"),
                               ("rencana fitur", "> BIKININ RENCANA FITUR"),
                               ("memilih alat", "> PILIH ALAT PALING MURAH"),
                               ("suruh AI full", "> KETIK KODENYA SAMPAI JADI")]):
    rel = 1.05 if k == 0 else b.t(ph, 0.1)
    spans, t_end = typewriter(b, txt, f"p{k}", rel, cps=24, sfx_gain=0.3)
    html += f'<div class="typ" style="position:absolute;left:70px;top:{140 + k * 105}px;font-size:36px">{spans}</div>'
    checks.append((f"pc{k}", rcheck(712, 150 + k * 105, 40, seed=k + 60), RED, 7))
    draw(b, f".pc{k}", t_end + 0.1, 0.3)
    b.sfx(t_end + 0.1, "marker", 0.35)
html += svg(checks, w=800, h=620) + '</div>'
side_free(b, html, "left")
reveal(b, ".pp", 0.75, "drop")
b.sfx(0.75, "paper", 0.7)

b = Beat("c2e-claude", "modalnya cuma satu", lead=0.3, until=at("begitu aplikasinya udah") - 0.3)
full(b, board("claude.com/pricing"))
r_pro, r20 = b.t("versi Pro", 0.1), b.t("$20", 0.05)
shot(b, "sc", "claude-pricing-crop", 260, 140, 1400, 790, -1.2,
     moves=[(0, None, 0), (r_pro, (1080, 690, 2120, 1600), 1.2)],
     marks=[(r20, (1412, 1262, 1738, 1338))], circles=[(r20 + 0.5, (1412, 1262, 1738, 1338))])
b.js.append("tl.from($('.sc'),{y:90,rotation:3,opacity:0,duration:.65,ease:'expo.out'},.3);")
b.sfx(0.3, "paper", 0.6)
hand_at(b, "rp", "≈ Rp300 ribu", 1360, 935, b.t("300 ribuan", 0.1), 70)

b = Beat("c2f-stop", "begitu aplikasinya udah", lead=0.25, until=at("langkah kedua") - 0.3)
caption(b, "BEGITU APLIKASINYA JADI", "STOP LANGGANAN AI.", red=("STOP",), rel_big=b.t("nggak perlu lagi", 0.1))

b = Beat("c2g-web", "langkah kedua website", lead=0.35, until=at("langsung jadi website") - 0.2)
full(b, board())
stair(b, active=1, done=[0], header=2)
activate(b, 1, 0.55)
r_v = b.t("layanan gratis", 0.2)
b.js.append(f"tl.to($('.stair'),{{x:-80,opacity:0,duration:.45,ease:'power2.in'}},{r_v:.3f});")
r_m = b.t("namanya Vercel", 0.0)
shot(b, "sv", "vercel-pricing", 260, 150, 1400, 790, 1.2, moves=[(0, (150, 700, 1250, 1900), 0)],
     marks=[(r_v + 0.9, (240, 880, 520, 1040))])
b.js.append(f"tl.from($('.sv'),{{y:90,rotation:-3,opacity:0,duration:.6,ease:'expo.out'}},{r_v + 0.2:.3f});")
b.sfx(r_v + 0.2, "paper", 0.6)
hand_at(b, "vg", "Hobby: gratis.", 1300, 950, r_m + 0.2, 76)

b = Beat("c2h-chrome", "langsung jadi website", lead=0.25, until=at("langkah ketiga yaitu") - 0.3)
side(b, '<div class="kick k1">langsung jadi website</div><div class="xl x1" style="font-size:84px">BUKA DI CHROME</div>'
        '<div style="height:10px"></div>'
        + li_rows([("l0", ick("q0", 1), "HP kasir"), ("l1", ick("q1", 2), "Laptop"), ("l2", ick("q2", 3), "Komputer"),
                   ("l3", icx("q3", 4), "Nggak perlu instal")]), "left")
reveal(b, ".k1", 0.2, "fade")
r = b.t("Google Chrome", 0.15)
reveal(b, ".x1", r, "clip")
b.sfx(r, "swish", 0.45)
for k, ph in enumerate(["HP kasir", "di laptop", "di komputer", "mendownload aplikasi"]):
    r = b.t(ph, 0.15)
    reveal(b, f".l{k}", r, "left")
    draw(b, f".q{k} path", r + 0.2, 0.3)
    b.sfx(r + 0.2, "marker", 0.4)

b = Beat("c2i-db", "langkah ketiga yaitu", lead=0.35, until=at("toko kan punya") - 0.25)
full(b, board())
stair(b, active=2, done=[0, 1], header=3)
activate(b, 2, 0.6)

b = Beat("c2j-data", "toko kan punya ratusan", lead=0.25, until=at("biar datanya aman") - 0.1)
caption(b, "YANG DISIMPAN", "RATUSAN BARANG + HARGA BELI", red=("HARGA", "BELI"), rel_big=b.t("ratusan daftar", 0.1))
CLOSEUPS.append((at("aman dan gak hilang"), 1.8))

b = Beat("c2k-supa", "namanya Supabase", lead=0.6, until=at("langkah keempat") - 0.35)
full(b, board("supabase.com/pricing"), chain_out=True)
shot(b, "ss", "supabase-pricing", 260, 150, 1400, 790, -1.0, moves=[(0, (200, 600, 1700, 1500), 0)],
     marks=[(b.t("gratis untuk awal", 0.1), (260, 1010, 560, 1190))])
b.js.append("tl.from($('.ss'),{y:90,rotation:3,opacity:0,duration:.6,ease:'expo.out'},.3);")
b.sfx(0.3, "paper", 0.6)
hand_at(b, "pt", "cukup buat puluhan toko", 1060, 950, b.t("puluhan toko", 0.15), 64)

b = Beat("c2l-ocr", "langkah keempat adalah", lead=0.35, until=at("pas kasir foto") - 0.25)
full(b, board())
stair(b, active=3, done=[0, 1, 2], header=4)
activate(b, 3, 0.6)

b = Beat("c2m-scan", "pas kasir foto", lead=0.3, until=at("sekitar 10 perak") - 0.35)
corners = []
for (x, y, dx, dy) in [(1150, 180, 1, 1), (1600, 180, -1, 1), (1150, 600, 1, -1), (1600, 600, -1, -1)]:
    corners += rpoly([(x, y + dy * 60), (x, y), (x + dx * 60, y)], seed=x + y, rough=1.2)
nota = nota_html("sn", NOTA_LINES, 1190, 215, 4, 380, False, "NOTA SUPPLIER")
side_free(b, nota + svg([("vf", corners, INK, 6)])
          + '<div class="scan" style="position:absolute;left:1150px;top:180px;width:450px;height:4px;'
            'background:#FF4A4F;box-shadow:0 0 24px 6px rgba(255,74,79,.55);opacity:0"></div>'
          + '<div class="gm" style="position:absolute;left:1640px;top:500px;transform:rotate(3deg)">'
          + logo("gemini", 34) + '</div>'
          + '<div class="ex" style="position:absolute;left:1180px;top:690px;font:400 34px/1.45 var(--type);color:#F4F1EA">'
            '<div class="e0">MINYAK 2L ..... 36.500</div><div class="e1">MIE / DUS ..... 112.000</div>'
            '<div class="e2">GULA 1KG ...... 17.800</div></div>', "right")
reveal(b, ".sn", 0.15, "drop")
b.sfx(0.15, "paper", 0.6)
draw(b, ".vf", 0.4, 0.25, 0.03)
b.sfx(0.5, "shutter", 0.6)
r = b.t("tintanya pudar", 0.1)
b.js.append(f"tl.to($('.sn .ln'),{{filter:'blur(1.8px)',opacity:.55,duration:.6}},{r:.3f});")
hand_at(b, "t1", "pudar", 1640, 230, r, 54)
r = b.t("atau miring", 0.1)
b.js.append(f"tl.to($('.sn'),{{rotation:12,duration:.5,ease:'back.out(1.6)'}},{r:.3f});")
hand_at(b, "t2", "miring", 1640, 310, r, 54)
hand_at(b, "t3", "susah dibaca", 1640, 390, b.t("susah dibaca", 0.1), 46)
r = b.t("Gemini Flash", 0.15)
reveal(b, ".gm", r, "drop")
b.sfx(r, "pop", 0.5)
b.js.append(f"tl.set($('.scan'),{{opacity:1}},{r + 0.3:.3f});"
            f"tl.to($('.scan'),{{y:416,duration:.9,ease:'power1.inOut',yoyo:true,repeat:1}},{r + 0.3:.3f});"
            f"tl.set($('.scan'),{{opacity:0}},{r + 2.1:.3f});")
r = b.t("mengeluarkan angka", 0.1)
for k in range(3):
    reveal(b, f".e{k}", r + 0.35 * k, "clip")
    b.sfx(r + 0.35 * k, "tick", 0.45)

b = Beat("c2n-cost", "sekitar 10 perak", lead=0.6, until=at("langkah kelima") - 0.35)
full(b, board(None, '<div class="ctr" style="top:200px"><div class="kick k1">biaya baca 1 nota</div>'
                    '<div class="num c1" style="font-size:240px;margin-top:26px">Rp10</div>'
                    '<div class="unit c2" style="margin-top:20px">per lembar</div>'
                    '<div class="hl2 c3" style="margin-top:70px">100 NOTA/BULAN &asymp; <span class="blk">Rp1.000</span></div></div>'),
     chain_out=True)
reveal(b, ".k1", 0.3, "fade")
r = 0.5
reveal(b, ".c1", r, "pop")
b.sfx(r, "cash", 0.55)
reveal(b, ".c2", r + 0.3, "up")
r = b.t("100 nota", 0.1)
reveal(b, ".c3", r, "clip")
b.sfx(r, "swish", 0.4)
b.sfx(b.t("seribuan rupiah", 0.0), "cash", 0.45)

b = Beat("c2o-pay", "langkah kelima, cara", lead=0.35, until=at("aplikasi ini dapat kita") - 0.3)
full(b, board())
stair(b, active=4, done=[0, 1, 2, 3], header=5)
activate(b, 4, 0.6)

b = Beat("c2p-sewa", "aplikasi ini dapat kita", lead=0.25, until=at("biar tiap bulan pemilik") - 0.3)
caption(b, "MODEL BISNISNYA", "SEWAKAN KE TOKO LAIN.", red=("SEWAKAN",), rel_big=b.t("kita sewakan", 0.1))

b = Beat("c2q-gate", "namanya Xendit", lead=0.6, until=at("lalu nanti tiap bulan") - 0.3)
full(b, board(None, '<div class="ctr" style="top:80px"><div class="kick">payment gateway indonesia</div>'
                    '<div class="hl2 g0" style="margin-top:14px">PILIH SALAH SATU</div></div>'))
shot(b, "sx", "xendit-home-hero", 120, 330, 820, 369, -2.4)
shot(b, "sm", "midtrans-home-hero", 980, 400, 820, 369, 2.0)
r = 0.45
b.js.append(f"tl.from($('.sx'),{{y:90,rotation:-6,opacity:0,duration:.6,ease:'expo.out'}},{r:.3f});")
b.sfx(r, "paper", 0.6)
hand_at(b, "nx", "Xendit", 420, 740, r + 0.4, 62, red=False)
r = b.t("Midtrans", 0.15)
b.js.append(f"tl.from($('.sm'),{{y:90,rotation:6,opacity:0,duration:.6,ease:'expo.out'}},{r:.3f});")
b.sfx(r, "paper", 0.6)
hand_at(b, "nm", "Midtrans", 1270, 810, r + 0.4, 62, red=False)
reveal(b, ".g0", b.t("salah satunya", 0.2), "clip")

b = Beat("c2r-bill", "tiap bulan sistem akan", lead=0.35, until=at("jadi kalau di total") - 0.3)
side_free(b, '<div class="kick kb" style="position:absolute;left:1300px;top:78px">otomatis, tiap bulan</div>'
          + phone("ph", [("n1", 230, "Aplikasi lo · tagihan", RED,
                          "<b>Tagihan langganan bulan ini</b><br>Rp150.000 / bulan", "BAYAR VIA QRIS"),
                         ("n2", 470, "Aplikasi lo", "#1F1E1C",
                          "<b>Pembayaran diterima.</b><br>Aplikasi aktif sampai bulan depan.", None)], 1290, 120),
          "right")
reveal(b, ".ph", 0.15, "up")
reveal(b, ".kb", 0.3, "fade")
r = b.t("kirim link tagihannya", 0.1)
b.js.append(f"tl.from($('.n1'),{{y:-90,opacity:0,duration:.5,ease:'back.out(1.4)'}},{r:.3f});")
b.sfx(r, "chime", 0.6)
r = b.t("bayar aplikasi", 0.1)
b.js.append(f"tl.from($('.n2'),{{y:-60,opacity:0,duration:.5,ease:'back.out(1.4)'}},{r:.3f});")
b.sfx(r, "ding", 0.55)

b = Beat("c2s-total", "jadi kalau di total", lead=0.3, until=at("di bawah 50") - 0.3)
full(b, board(None, '<div class="kick" style="position:absolute;left:96px;top:62px">total modal</div>'))
stair(b, None, [], costs=True)
for k in range(5):
    reveal(b, f".cs{k}", 0.9 + 0.35 * k, "clip")
    b.sfx(0.9 + 0.35 * k, "scribble", 0.3)
b.html.append('<div class="stamp tm" style="position:absolute;left:96px;top:112px;transform:rotate(-2deg)">'
              'MODAL AWAL &asymp; Rp300 RB</div>')
r = b.t("300 ribu di bulan", 0.1)
reveal(b, ".tm", r, "pop")
b.sfx(r, "impact", 0.6)
hand_at(b, "hg", "operasional: hampir gratis", 110, 240, b.t("hampir gratis", 0.1), 56)

b = Beat("c2t-ops", "di bawah 50", lead=0.3, until=card_start("ch3") + 0.45)
caption(b, "OPERASIONAL / BULAN", "DI BAWAH Rp50–100 RB", rel_big=0.3)

hold_card("ch3", 2, "HITUNG CUAN", "logika pebisnis")

# ================================================================ CHAPTER 3
b = Beat("c3a-vs", "tadi rugi", lead=0.6, until=at("pemilik toko bakal mikir") - 0.35)
full(b, board(None, '<div style="position:absolute;left:0;width:960px;top:300px;text-align:center" class="vl">'
                    '<div class="kick">rugi tiap bulan</div><div class="num redt" style="margin-top:26px">Rp3&ndash;7 JT</div></div>'
                    '<div style="position:absolute;left:960px;width:960px;top:300px;text-align:center" class="vr">'
                    '<div class="kick">langganan software</div><div class="num" style="margin-top:26px">Rp150 RB</div></div>'
                    '<div class="hand vs" style="position:absolute;left:0;right:0;top:380px;text-align:center;font-size:96px">vs</div>'
                    '<div class="hand red vq" style="position:absolute;left:0;right:0;top:720px;text-align:center;font-size:72px">'
                    'hemat berapa persen?</div>'))
r = 0.45
reveal(b, ".vl", r, "up")
b.sfx(r, "thud", 0.6)
r = b.t("150 ribu.", 0.15)
reveal(b, ".vs", r - 0.3, "pop")
reveal(b, ".vr", r, "up")
b.sfx(r, "cash", 0.5)
r = b.t("berapa persen", 0.1)
reveal(b, ".vq", r, "clip")
b.sfx(r, "scribble", 0.5)

b = Beat("c3b-mikir", "pemilik toko bakal mikir", lead=0.3, until=at("why not") - 0.1)
side(b, '<div class="kick k1">di kepala pemilik toko:</div>'
        '<div class="hl2 m1" style="margin-top:12px">KELUAR <span class="dim">Rp150 RB</span></div>'
        '<div class="hl2 m2" style="margin-top:8px"><span class="blk">SELAMAT Rp5 JT</span></div>', "left")
reveal(b, ".k1", 0.2, "fade")
r = b.t("cuma keluar", 0.1)
reveal(b, ".m1", r, "left")
b.sfx(r, "tick", 0.5)
r = b.t("buat nyelamatin", 0.1)
reveal(b, ".m2", r, "pop")
b.sfx(r, "cash", 0.55)
b.sfx("END-0.0", "riser", 0.45, 1.0)

b = Beat("c3c-whynot", "why not", lead=0.06, until=at("ini sangat murah") - 0.04)
full(b, '<div class="full"><div class="ctr" style="top:390px"><div class="stamp wn" style="font-size:150px;'
        'padding:28px 48px 20px;transform:rotate(-3deg)">WHY NOT?</div></div></div>', cut=True)
b.js.append("tl.from($('.wn'),{scale:1.7,opacity:0,duration:.22,ease:'power3.out'},0.02);")
b.sfx(0.02, "impact", 1.0)
b.whynot = True

b = Beat("c3d-20", "lo dapat 20 toko", lead=0.4, until=at("ini sudah nutup") - 0.25)
full(b, board(None, '<div class="grid g20" style="left:200px;top:290px;grid-template-columns:repeat(5,116px);'
                    'grid-auto-rows:116px">' + "<i></i>" * 20 + '</div>'
                    '<div style="position:absolute;left:1000px;top:330px"><div class="kick k1">20 toko langganan</div>'
                    '<div class="num cnt" style="font-size:132px;margin-top:22px">Rp0</div>'
                    '<div class="unit u1" style="margin-top:18px">per bulan</div></div>'))
r = b.t("20 toko", 0.15)
b.js.append(f"tl.from($('.g20 i'),{{scale:.3,opacity:0,duration:.3,stagger:.045,ease:'back.out(2)'}},{r:.3f});")
for k in range(4):
    b.sfx(r + 0.22 * k, "tick", 0.35)
reveal(b, ".k1", r + 0.3, "fade")
r = b.t("udah ngantongin", 0.1)
counter(b, ".cnt", 0, 2900000, r, 1.5, "(v=>'Rp'+String(Math.round(v/1000)*1000).replace(/\\B(?=(\\d{3})+(?!\\d))/g,'.'))")
b.sfx(r + 1.5, "cash", 0.6)
reveal(b, ".u1", r + 0.5, "up")

b = Beat("c3e-100", "bisa temukan 100 toko", lead=0.4, until=at("biaya server paling") - 0.25)
full(b, board(None, '<div class="grid g100" style="left:180px;top:230px;grid-template-columns:repeat(10,62px);'
                    'grid-auto-rows:62px">' + "<i></i>" * 100 + '</div>'
                    '<div style="position:absolute;left:1000px;top:300px"><div class="kick k1">100 toko langganan</div>'
                    '<div class="num cnt" style="font-size:132px;margin-top:22px">Rp0</div>'
                    '<div class="unit u1" style="margin-top:18px">per bulan</div>'
                    '<div class="stamp pb" style="margin-top:46px;font-size:54px;transform:rotate(-2deg)">PENDAPATAN BERULANG</div></div>'))
r = b.t("100 toko", 0.15)
b.js.append(f"tl.from($('.g100 i'),{{scale:.3,opacity:0,duration:.25,stagger:.012,ease:'back.out(2)'}},{r:.3f});")
for k in range(5):
    b.sfx(r + 0.25 * k, "tick", 0.3)
reveal(b, ".k1", r + 0.3, "fade")
r = b.t("sekitar 14", 0.1)
counter(b, ".cnt", 0, 14900000, r, 1.6, "(v=>'Rp'+String(Math.round(v/1000)*1000).replace(/\\B(?=(\\d{3})+(?!\\d))/g,'.'))")
b.sfx(r + 1.6, "cash", 0.7)
reveal(b, ".u1", r + 0.5, "up")
r = b.t("pendapatan berulang", 0.1)
reveal(b, ".pb", r, "pop")
b.sfx(r, "impact", 0.6)

b = Beat("c3f-margin", "biaya server paling", lead=0.3, until=card_start("ch4") + 0.45)
side(b, '<div class="kick k1">biaya server</div><div class="hl2 a1">+Rp500 RB <span class="dim">/ bulan</span></div>'
        '<div class="kick k2" style="margin-top:34px">profit margin</div><div class="num redt a2">&gt;90%</div>'
        '<div class="hand a3">uangnya masuk terus.</div>', "right")
reveal(b, ".k1", 0.2, "fade")
r = b.t("500ribuan", 0.1)
reveal(b, ".a1", r, "left")
b.sfx(r, "tick", 0.5)
r = b.t("profit margin", 0.1)
reveal(b, ".k2", r, "fade")
reveal(b, ".a2", r + 0.3, "clip")
b.sfx(r + 0.3, "impact", 0.55)
reveal(b, ".a3", b.t("uangnya masuk", 0.1), "clip")

hold_card("ch4", 3, "ORANG LAPANGAN", "vs programmer")

# ================================================================ CHAPTER 4
b = Beat("c4a-why", "memang ide sesimpel", lead=0.3, until=at("Jawabannya sederhana") - 0.15)
caption(b, "LO MUNGKIN NANYA", "KENAPA PROGRAMMER NGGAK BIKIN?", red=("PROGRAMMER",),
        rel_big=b.t("kenapa programmer", 0.1))
b.html[-1] = b.html[-1].replace('class="big cb"', 'class="big cb" style="font-size:74px"', 1)
CLOSEUPS.append((at("Jawabannya sederhana"), 1.5))

b = Beat("c4b-split", "Programmer itu biasa", lead=0.35, until=at("Jam 12 siang") - 0.3)
full(b, board(None, svg([("dv", rline(962, 120, 958, 960, seed=31, rough=3), "rgba(244,241,234,.55)", 4)])
              + '<div class="kick" style="position:absolute;left:150px;top:150px">programmer</div>'
                '<div class="kick redt" style="position:absolute;left:1070px;top:150px">orang lapangan</div>'))
draw(b, ".dv", 0.35, 0.5)
lines, rows = "", [("secara teknis,", "TEKNIS."), ("coding, aplikasi,", "CODING."), ("aplikasi, dan", "APLIKASI."),
                   ("depan laptop.", "DEPAN LAPTOP.")]
for k, (ph, txt) in enumerate(rows):
    spans, _ = typewriter(b, txt, f"w{k}", b.t(ph, 0.05), cps=22, sfx_gain=0.35)
    lines += f'<div class="typ" style="position:absolute;left:80px;top:{90 + k * 100}px;font-size:52px">{spans}</div>'
b.html.append('<div class="paper pw" style="left:130px;top:230px;width:700px;height:520px;transform:rotate(-1.6deg)">'
              + lines + '</div>')
reveal(b, ".pw", 0.3, "drop")
b.sfx(0.3, "paper", 0.6)
hand_at(b, "rf", "nggak pernah ngerasain", 1070, 300, b.t("nggak pernah paham", 0.1), 62, red=False, rot=-1)
hand_at(b, "rb", "ribetnya berdiri", 1070, 420, b.t("ngerasain ribetnya", 0.1), 92, rot=-2)
hand_at(b, "rk", "di depan kasir.", 1070, 540, b.t("depan kasir.", 0.15), 92, rot=-2)

b = Beat("c4c-jam12", "Jam 12 siang", lead=0.35, until=at("mereka nggak tahu kalau") - 0.2)
b.html.append('<div class="cap"><div class="lab cl">JAM 12 SIANG</div><div class="big cb" style="font-size:70px">'
              '<span class="w q0">LAYANI PEMBELI.</span> <span class="w q1">SALES DATANG.</span> '
              '<span class="w q2">NURUNIN <span class="r">KARDUS.</span></span></div></div>')
b.js.append("tl.from($('.cl'),{clipPath:'inset(0 100% 0 0)',duration:.35,ease:'power2.out'},.05);")
b.sfx(0.04, "swish", 0.5)
for k, ph in enumerate(["layani pembeli,", "pas sales", "nurunin kardus,"]):
    r = b.t(ph, 0.1)
    b.js.append(f"tl.from($('.q{k}'),{{y:40,opacity:0,duration:.4,ease:'back.out(1.5)'}},{r:.3f});")
    b.sfx(r, "tick", 0.5)
b.js.append("tl.to($('.cap'),{y:26,opacity:0,duration:.3,ease:'power2.in'},__END-0.36__);")

b = Beat("c4d-lecek", "nota di warung itu", lead=0.4, until=at("rasa sakit ini") + 0.2)
nota = nota_html("nl", NOTA_LINES, 170, 200, -9, 420, False, "NOTA WARUNG")
nota = nota[:-6] + ('<div style="position:absolute;left:170px;top:110px;width:200px;height:170px;border-radius:50%;'
                    'background:radial-gradient(closest-side,rgba(170,120,30,.42),rgba(170,120,30,.2) 60%,transparent);'
                    'mix-blend-mode:multiply"></div>') + nota[-6:]
side_free(b, nota + '<div class="hl2 nm" style="position:absolute;left:180px;top:660px">NGETIK MANUAL?</div>'
          + svg([("nx", rline(160, 640, 720, 760, seed=34, rough=3) + rline(720, 640, 170, 760, seed=35, rough=3), RED, 10)]),
          "left")
reveal(b, ".nl", 0.15, "drop")
b.sfx(0.15, "paper", 0.7)
hand_at(b, "lk", "lecek", 640, 250, b.t("sering lecek", 0.1), 70)
hand_at(b, "km", "kena minyak", 640, 350, b.t("kena minyak", 0.1), 64)
r = b.t("ngetik manual", 0.15)
reveal(b, ".nm", r, "clip")
draw(b, ".nx", r + 0.4, 0.3, 0.12)
b.sfx(r + 0.4, "scribble", 0.6)

b = Beat("c4e-lo", "bukan anak IT", lead=0.3, until=at("Dan pemilik toko") - 0.25)
b.html.append('<div class="cap"><div class="big cb" style="font-size:96px"><span class="w g0">BUKAN</span> '
              '<span class="w g0">ANAK</span> <span class="w g0">IT.</span> <span class="w g1">TAPI</span> '
              '<span class="w r g1">LO.</span></div></div>')
b.js.append("tl.from($('.g0'),{scale:1.6,opacity:0,duration:.32,stagger:.08,ease:'power3.out'},.2);")
r = b.t("tapi lu yang", 0.05)
b.js.append(f"tl.from($('.g1'),{{scale:1.8,opacity:0,duration:.3,stagger:.1,ease:'power3.out'}},{r:.3f});")
b.js.append("tl.to($('.cap'),{y:26,opacity:0,duration:.3,ease:'power2.in'},__END-0.36__);")
b.sfx(0.2, "swish", 0.5)
b.sfx(r + 0.1, "impact", 0.85)

b = Beat("c4f-who", "Dan pemilik toko", lead=0.3, until=at("dulu idenya lu") - 0.3)
side(b, '<div class="kick k1">yang paling paham masalahnya:</div>'
        + li_rows([("l0", ick("q0", 7), "Pemilik toko"), ("l1", ick("q1", 8), "Manager minimarket"),
                   ("l2", ick("q2", 9), "Siapapun di lapangan")]), "right")
reveal(b, ".k1", 0.2, "fade")
for k, ph in enumerate(["Dan pemilik toko", "manager,", "atau siapapun"]):
    r = b.t(ph, 0.1 if k else -0.3)
    reveal(b, f".l{k}", r, "left")
    draw(b, f".q{k} path", r + 0.2, 0.3)
    b.sfx(r + 0.2, "marker", 0.4)

b = Beat("c4g-dulu", "dulu idenya lu", lead=0.3, until=at("Tapi sekarang lu nggak") - 0.15)
caption(b, "DULU", "IDE MANDEK. NGGAK BISA CODING.", red=("MANDEK",), rel_big=b.t("lu mandek", 0.1))

b = Beat("c4h-skrg", "Tapi sekarang lu nggak", lead=0.2, until=at("Modal utama lu") - 0.3)
caption(b, "SEKARANG", "AI YANG NGERJAIN CODENYA.", red=("AI",), rel_big=b.t("AI yang ngerjain", 0.1), impact=True)

b = Beat("c4i-modal", "Modal utama lu", lead=0.3, until=at("lalu buat eksekusinya") - 0.1)
spans, t_end = typewriter(b, "PAHAM MASALAH NYATA", "mw", b.t("pemahaman masalah", 0.1), cps=20)
full(b, board(None, '<div class="sheet paper" style="left:430px;top:250px;width:1060px;height:600px;transform:rotate(-1.8deg)">'
                    + PAPERCLIP.format(pos="left:70px;top:-38px")
                    + '<div class="typ tred" style="position:absolute;left:120px;top:88px;font-size:34px;letter-spacing:.08em">'
                      'MODAL UTAMA LO SEKARANG:</div>'
                    f'<div class="typ" style="position:absolute;left:120px;top:170px;right:90px">{spans}</div>'
                    '<div class="hand red ld" style="position:absolute;left:120px;top:330px;font-size:70px">'
                    'di lapangan, sedetail mungkin.</div>'
                    + svg([("lu", rline(120, 430, 820, 438, seed=41), RED, 8)], w=1060, h=600) + '</div>'))
b.js.append("tl.from($('.sheet'),{y:520,rotation:7,duration:.75,ease:'expo.out'},.12);")
b.sfx(0.12, "paper", 0.8)
b.sfx(t_end + 0.05, "ding", 0.55)
r = b.t("di lapangan sedetail", 0.1)
reveal(b, ".ld", r, "clip")
b.sfx(r, "scribble", 0.55)
draw(b, ".lu", r + 0.7, 0.4)

b = Beat("c4j-play", "buat eksekusinya, lo", lead=0.3, until=at("notifikasi warning") - 0.35)
side(b, '<div class="kick k1">cara eksekusinya</div>'
        + li_rows([("l0", icx("q0", 11), "Bakar duit iklan"), ("l1", ick("q1", 12), "Bawa HP lo"),
                   ("l2", ick("q2", 13), "Datang ke 5 toko"), ("l3", ick("q3", 14), "Demo 30 detik"),
                   ("l4", ick("q4", 15), "Jepret nota kemarin")], 44), "right")
reveal(b, ".k1", 0.2, "fade")
for k, ph in enumerate(["bakar duit", "bawa hp", "datang ke 5", "tunjukin demo", "jepret nota"]):
    r = b.t(ph, 0.1)
    reveal(b, f".l{k}", r, "left")
    draw(b, f".q{k} path", r + 0.2, 0.3)
    b.sfx(r + 0.2, "marker", 0.4)
b.js.append(f"tl.to($('.l0 .tx'),{{opacity:.5,duration:.3}},{b.t('cukup bawa', 0.0):.3f});")

b = Beat("c4k-warn", "notifikasi warning", lead=0.35, until=at("kalau mereka kebantu") - 0.25)
side_free(b, phone("pw", [("w1", 230, "Aplikasi lo · warning", RED,
                           "<b>Harga SABUN naik Rp600</b><br>Bu, dibanding minggu lalu. Update harga jual?", "UPDATE HARGA")],
                   300, 110, svg([("wc", rellipse(212, 294, 196, 38, seed=19), RED, 7)], w=440, h=840)), "left")
reveal(b, ".pw", 0.7, "up")
r = max(1.15, b.t("notifikasi warning", 0.0) + 0.25)
b.js.append(f"tl.from($('.w1'),{{y:-90,opacity:0,duration:.5,ease:'back.out(1.4)'}},{r:.3f});")
b.sfx(r, "chime", 0.7)
r = b.t("naik 600", 0.1)
draw(b, ".wc", r, 0.5)
b.sfx(r, "scribble", 0.55)

b = Beat("c4l-trial", "kalau mereka kebantu", lead=0.3, until=at("Kemudian jika merasa") - 0.15)
caption(b, "KALAU MEREKA KEBANTU", "UJI COBA GRATIS 2 MINGGU.", red=("GRATIS",), rel_big=b.t("uji coba", 0.1))
CLOSEUPS.append((at("otomatis akan membayar"), 1.8))

b = Beat("c4m-ask", "Menurut kalian berapa", lead=0.3, until=at("Coba tulis pendapat") - 0.2)
caption(b, "PERTANYAAN BUAT LO", "BERAPA TOKO DI SEKITAR LO?", red=("LO",), rel_big=b.t("di sekitar rumah", 0.4))

b = Beat("c4n-cta", "Coba tulis pendapat", lead=0.3, until=DUR - 0.25)
side(b, '<div class="hand c1" style="font-size:66px">tulis jawaban lo di komentar.</div>'
        '<div class="kick k2" style="margin-top:40px">video berikutnya?</div>'
        '<div class="xl c2" style="font-size:80px">IDE SOFTWARE SEKTOR LAIN</div>'
        '<div class="c3" style="margin-top:30px"><span class="sub-btn">SUBSCRIBE</span></div>', "right")
reveal(b, ".c1", 0.2, "clip")
b.sfx(0.2, "scribble", 0.5)
r = b.t("ide software di", 0.15)
reveal(b, ".k2", r, "fade")
reveal(b, ".c2", r + 0.15, "clip")
b.sfx(r + 0.15, "swish", 0.45)
r = b.t("untuk subscribe", 0.1)
reveal(b, ".c3", r, "pop")
b.sfx(r, "pop", 0.6)
b.sfx(r + 0.35, "tick", 0.6)
