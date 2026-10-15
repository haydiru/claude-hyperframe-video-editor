"""YouTube thumbnails (1280x720) as HTML, rendered with the HyperFrames
headless Chrome. Three variants for YouTube 'Test & compare'.

  python thumbnail/make_thumbs.py  -> thumbnail/thumb_A.jpg, thumb_B.jpg, thumb_C.jpg
"""
import subprocess
from pathlib import Path

import cv2

HERE = Path(__file__).resolve().parent
CHROME = Path.home() / (".cache/hyperframes/chrome/chrome-headless-shell/win64-152.0.7928.2/"
                        "chrome-headless-shell-win64/chrome-headless-shell.exe")

BASE_CSS = """
@import url('../assets/fonts2.css');
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { width: 1280px; height: 720px; overflow: hidden; background: #0b0b0c; }
.T { position: relative; width: 1280px; height: 720px; overflow: hidden; }
.abs { position: absolute; }
.room { position: absolute; filter: brightness(.5) saturate(1.1) blur(2px); }
.cut { position: absolute; filter: brightness(1.12) contrast(1.12) saturate(1.12)
       drop-shadow(0 0 22px rgba(255,170,90,.28)) drop-shadow(0 10px 40px rgba(0,0,0,.6)); }
.shade { position: absolute; inset: 0;
         background: linear-gradient(90deg, rgba(0,0,0,.88) 0%, rgba(0,0,0,.7) 38%, rgba(0,0,0,0) 62%),
                     radial-gradient(120% 90% at 70% 40%, rgba(0,0,0,0) 40%, rgba(0,0,0,.55) 100%); }
.h { font-family: 'Archivo', sans-serif; font-weight: 900; text-transform: uppercase; line-height: .9;
     letter-spacing: -.01em; color: #fff; text-shadow: 0 6px 0 rgba(0,0,0,.35), 0 10px 40px rgba(0,0,0,.6); }
.y { color: #FFD43B; }
.lab { display: inline-block; background: #E3262F; color: #fff; font: 800 34px/1 'Archivo', sans-serif;
       font-stretch: 92%; text-transform: uppercase; padding: 10px 16px 8px; letter-spacing: .01em; }
.rp { text-transform: none; }
.hand { font: 700 54px/1 'Caveat', cursive; color: #FF4A4F; }
.nota { position: absolute; width: 300px; background: #F3EEE3; color: #3B3A38; font: 400 19px/1.5 'Special Elite', monospace;
        padding: 20px 22px 30px; box-shadow: 0 24px 40px rgba(0,0,0,.6); }
.nota .ln { display: flex; justify-content: space-between; }
.nota .hd { text-align: center; letter-spacing: .12em; margin-bottom: 6px; }
.nota .dash { border-top: 2px dashed rgba(59,58,56,.45); margin: 8px 0; }
.logo { display: inline-flex; align-items: center; background: #F7F5F0; padding: 10px 16px; box-shadow: 0 12px 26px rgba(0,0,0,.5); }
.logo img { display: block; }
.phone { position: absolute; width: 330px; height: 460px; border-radius: 42px; background: #0c0c0d;
         border: 8px solid #2b2b2e; box-shadow: 0 30px 60px rgba(0,0,0,.7); overflow: hidden; }
.notif { position: absolute; left: 14px; right: 14px; top: 120px; background: #F6F4EF; border-radius: 22px;
         padding: 16px 18px; color: #1F1E1C; font: 500 21px/1.25 'Archivo', sans-serif; }
.notif .app { font: 700 15px/1 'Archivo', sans-serif; letter-spacing: .1em; color: #77746d; text-transform: uppercase;
              margin-bottom: 8px; display: flex; gap: 8px; align-items: center; }
.notif .ico { width: 22px; height: 22px; border-radius: 6px; background: #E3262F; display: inline-block; }
"""


def person(name, k, left, top, cut_suffix=""):
    w, h = round(2560 * k), round(1440 * k)
    return (f'<img class="room" src="work/room_{name}.jpg" style="left:{left}px;top:{top}px;width:{w}px;height:{h}px">'
            '<div class="shade"></div>'
            f'<img class="cut" src="work/cut_{name}{cut_suffix}.png" style="left:{left}px;top:{top}px;width:{w}px;height:{h}px">')


def nota(left, top, rot):
    rows = [("MINYAK 2L", "36.500"), ("MIE / DUS", "112.000"), ("GULA 1KG", "17.800")]
    body = "".join(f'<div class="ln"><span>{a}</span><span>{b}</span></div>' for a, b in rows)
    return (f'<div class="nota" style="left:{left}px;top:{top}px;transform:rotate({rot}deg)">'
            f'<div class="hd">NOTA SUPPLIER</div><div class="dash"></div>{body}'
            '<svg width="300" height="200" style="position:absolute;left:0;top:0;overflow:visible">'
            '<path d="M196 62 C 246 50, 300 62, 292 82 C 284 102, 214 108, 188 92 C 168 78, 186 58, 232 56" '
            'fill="none" stroke="#E3262F" stroke-width="5" stroke-linecap="round"/></svg></div>')


ARROW = ('<svg class="abs" style="left:{l}px;top:{t}px;overflow:visible" width="10" height="10">'
         '<path d="{d}" fill="none" stroke="#E3262F" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/></svg>')

VARIANTS = {
    # A: money transformation + the real object (supplier receipt)
    "A": person("213.0", 0.74, -40, -95, "_rt")
    + '<div class="abs" style="left:52px;top:54px"><span class="lab">Aplikasi AI &middot; modal <span class="rp">Rp</span>300 rb</span></div>'
    + '<div class="abs h y" style="left:46px;top:118px;font-size:156px;font-stretch:78%"><span class="rp">Rp</span>14,9 JT</div>'
    + '<div class="abs h" style="left:50px;top:262px;font-size:112px;font-stretch:80%">/BULAN</div>'
    + nota(70, 430, -7)
    + ARROW.format(l=0, t=0, d="M372 520 C 430 470, 450 420, 430 380 M430 380 L 410 404 M430 380 L 452 398")
    + '<div class="abs hand" style="left:396px;top:540px;transform:rotate(-6deg)">dari nota ini</div>',

    # B: transformation with numbers (capital -> monthly revenue), the format that works in this niche
    "B": person("128.0", 0.74, -10, -88, "_rt")
    + '<div class="abs" style="left:52px;top:52px"><span class="lab">Bisnis AI yang jarang dilirik</span></div>'
    + '<div class="abs h" style="left:52px;top:122px;font-size:70px;font-stretch:82%">MODAL <span class="rp">Rp</span>300 RB</div>'
    + ARROW.format(l=0, t=0, d="M150 205 C 120 250, 120 300, 160 330 M160 330 L 128 322 M160 330 L 152 298")
    + '<div class="abs hand" style="left:190px;top:236px;color:#FFD43B;transform:rotate(-4deg)">jadi...</div>'
    + '<div class="abs h y" style="left:46px;top:335px;font-size:156px;font-stretch:78%"><span class="rp">Rp</span>14,9 JT</div>'
    + '<div class="abs h" style="left:50px;top:478px;font-size:112px;font-stretch:80%">/BULAN</div>'
    + '<div class="abs hand" style="left:56px;top:610px;font-size:46px">dari toko kelontong</div>',

    # C: accessible how-to (build the app yourself) with the real AI tools
    "C": person("444.3", 0.74, 70, -92)
    + '<div class="abs h" style="left:50px;top:70px;font-size:112px;font-stretch:76%">BIKIN APLIKASI</div>'
    + '<div class="abs h y" style="left:48px;top:174px;font-size:112px;font-stretch:76%">MODAL <span class="rp">Rp</span>300RB</div>'
    + '<div class="abs" style="left:56px;top:320px"><span class="lab">tanpa jago coding</span></div>'
    + '<div class="abs" style="left:56px;top:420px;display:flex;gap:14px;flex-wrap:wrap;width:520px;transform:rotate(-2deg)">'
      '<span class="logo"><img src="../assets/logos/claude.png" style="height:40px"></span>'
      '<span class="logo"><img src="../assets/logos/gemini.png" style="height:36px"></span>'
      '<span class="logo"><img src="../assets/logos/supabase.png" style="height:34px"></span>'
      '<span class="logo" style="padding:10px 14px"><img src="../assets/logos/vercel.png" style="height:38px"></span></div>'
    + '<div class="abs hand" style="left:60px;top:570px;color:#FFD43B">jadi bisnis langganan</div>',
}

for key, body in VARIANTS.items():
    html = HERE / f"thumb_{key}.html"
    html.write_text(f'<!doctype html><html><head><meta charset="utf-8"><style>{BASE_CSS}</style></head>'
                    f'<body><div class="T">{body}</div></body></html>', encoding="utf-8")
    png = HERE / "work" / f"thumb_{key}.png"
    subprocess.run([str(CHROME), "--headless", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
                    "--force-device-scale-factor=1", "--window-size=1280,720", "--virtual-time-budget=4000",
                    f"--screenshot={png}", html.as_uri()], check=True, capture_output=True)
    img = cv2.imread(str(png))
    assert img is not None and img.shape[:2] == (720, 1280), (key, None if img is None else img.shape)
    cv2.imwrite(str(HERE / f"thumb_{key}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 92])
    print("thumb", key, (HERE / f"thumb_{key}.jpg").stat().st_size // 1024, "KB")
