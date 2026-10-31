"""V6 train-marking textures (any Python with Pillow; no Blender needed).

- Shinkansen side LED displays (one per car, as shown beside the doors): train name, destination, car number and seat
  class in a full-colour dot-matrix look.  N700 on track 14 (のぞみ 新大阪) and track 18 (のぞみ 博多), E5 on track 20
  (はやぶさ 新函館北斗).  Seat classes follow the platform car boards: Tokaido 1-3 自由席, 8-10 グリーン車, others 指定席;
  Tohoku はやぶさ all reserved, 9 グリーン車, 10 グランクラス.
- 号車 plates for the commuter cars (1-15) and a 優先席 (priority seat) window sticker.
Packs everything into one atlas page + JSON manifest read by mod6_trains.py.  Wording and layout are illustrative.

usage: python make6_train_textures.py [out_dir]
"""
import os, sys, json
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "textures")
os.makedirs(OUT, exist_ok=True)
JP_B = os.path.join(HERE, "fonts", "NotoSansJP-Bold.otf")
JP_M = os.path.join(HERE, "fonts", "NotoSansJP-Medium.otf")
EN_B = next(p for p in ["C:/Windows/Fonts/segoeuib.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"] if os.path.exists(p))
_F = {}


def F(path, size):
    k = (path, int(size))
    if k not in _F:
        _F[k] = ImageFont.truetype(path, int(size))
    return _F[k]


ITEMS, META = {}, {}

# ---------------------------------------------------------------- LED side displays
LED_W, LED_H = 168, 32          # dot-matrix resolution
PITCH = 4                       # output pixels per LED dot
YEL, ORA, WHT, GRN = (255, 205, 40), (255, 140, 30), (240, 240, 240), (60, 220, 90)
SEAT = {"自由席": (90, 170, 255), "指定席": (255, 120, 40), "グリーン車": (60, 220, 90), "グランクラス": (230, 190, 90)}


def led_panel(key, name, name_col, dest, car, seat, size_m):
    g = Image.new("RGB", (LED_W, LED_H), (0, 0, 0))
    d = ImageDraw.Draw(g)

    def put(x, s, path, size, col, max_w):
        while size > 8 and d.textbbox((0, 0), s, font=F(path, size))[2] > max_w:
            size -= 1
        f = F(path, size)
        b = d.textbbox((0, 0), s, font=f)
        d.text((x - b[0], (LED_H - (b[3] - b[1])) // 2 - b[1]), s, font=f, fill=col)
        return b[2] - b[0]

    x = 2
    x += put(x, name, JP_B, 15, name_col, 44) + 3
    put(x, dest, JP_B, 20, ORA, 105 - x)
    d.rectangle([108, 2, 108, LED_H - 3], fill=(70, 70, 70))
    d.text((112, 0), f"{car}号車", font=F(JP_B, 13), fill=WHT)
    d.text((112, 17), seat, font=F(JP_B, 11 if len(seat) <= 3 else 10 if len(seat) <= 5 else 9), fill=SEAT[seat])
    g2 = g
    # dot-matrix upscale
    W, H = LED_W * PITCH, LED_H * PITCH
    im = Image.new("RGB", (W, H), (8, 8, 8))
    px = g2.load()
    dd = ImageDraw.Draw(im)
    for j in range(LED_H):
        for i in range(LED_W):
            c = px[i, j]
            if c != (0, 0, 0):
                dd.ellipse([i * PITCH, j * PITCH, i * PITCH + PITCH - 1, j * PITCH + PITCH - 1], fill=c)
            else:
                dd.point((i * PITCH + 1, j * PITCH + 1), fill=(22, 22, 22))
    ITEMS[key] = im
    META[key] = {"size_m": list(size_m), "emissive": True}


TOKAIDO = lambda n: "自由席" if n <= 3 else "グリーン車" if 8 <= n <= 10 else "指定席"
TOHOKU = lambda n: "グランクラス" if n == 10 else "グリーン車" if n == 9 else "指定席"
for n in range(1, 17):
    led_panel(f"led_14_{n:02d}", "のぞみ", YEL, "新大阪", n, TOKAIDO(n), (0.84, 0.16))
    led_panel(f"led_18_{n:02d}", "のぞみ", YEL, "博多", n, TOKAIDO(n), (0.84, 0.16))
for n in range(1, 11):
    led_panel(f"led_20_{n:02d}", "はやぶさ", GRN, "新函館北斗", n, TOHOKU(n), (0.84, 0.16))

# ---------------------------------------------------------------- 号車 plates
for n in range(1, 16):
    key = f"gosha_{n:02d}"
    W, H = 360, 180
    im = Image.new("RGB", (W, H), (250, 250, 250))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W - 1, H - 1], outline=(70, 70, 70), width=4)
    f = F(EN_B, 112)
    s = str(n)
    b = d.textbbox((0, 0), s, font=f)
    x0 = 30
    d.text((x0 - b[0], 92 - (b[3] + b[1]) // 2), s, font=f, fill=(20, 20, 20))
    d.text((x0 + (b[2] - b[0]) + 12, 100), "号車", font=F(JP_B, 54), fill=(20, 20, 20), anchor="lm")
    d.text((W - 16, H - 14), f"Car No.{n}", font=F(EN_B, 24), fill=(80, 80, 80), anchor="rb")
    ITEMS[key] = im
    META[key] = {"size_m": [0.16, 0.08]}

# ---------------------------------------------------------------- 優先席 sticker
W, H = 440, 440
im = Image.new("RGB", (W, H), (255, 255, 255))
d = ImageDraw.Draw(im)
d.rectangle([0, 0, W - 1, 150], fill=(235, 110, 20))
d.text((W // 2, 64), "優先席", font=F(JP_B, 92), fill=(255, 255, 255), anchor="mm")
d.text((W // 2, 128), "Priority Seat", font=F(EN_B, 34), fill=(255, 255, 255), anchor="mm")
# four simple pictograms (elderly, injured, pregnant, with child)
for i in range(4):
    cx = 62 + i * 105
    d.ellipse([cx - 16, 182, cx + 16, 214], fill=(60, 60, 60))
    d.rounded_rectangle([cx - 22, 220, cx + 22, 300], radius=12, fill=(60, 60, 60))
    d.rectangle([cx - 16, 300, cx - 4, 352], fill=(60, 60, 60))
    d.rectangle([cx + 4, 300, cx + 16, 352], fill=(60, 60, 60))
    if i == 0:
        d.line([(cx + 30, 240), (cx + 40, 352)], fill=(60, 60, 60), width=7)
    if i == 2:
        d.ellipse([cx + 4, 236, cx + 36, 290], fill=(60, 60, 60))
    if i == 3:
        d.ellipse([cx + 30, 252, cx + 50, 272], fill=(60, 60, 60))
        d.rounded_rectangle([cx + 28, 274, cx + 52, 320], radius=8, fill=(60, 60, 60))
d.text((W // 2, 400), "おゆずりください", font=F(JP_M, 40), fill=(60, 60, 60), anchor="mm")
ITEMS["yusen"] = im
META["yusen"] = {"size_m": [0.20, 0.20]}

# ---------------------------------------------------------------- pack (shelf)
PAGE_W, PAGE_H, GAP = 4096, 2048, 6
order = sorted(ITEMS, key=lambda k: (-ITEMS[k].size[1], -ITEMS[k].size[0], k))
page = Image.new("RGB", (PAGE_W, PAGE_H), (30, 30, 30))
shelves = []
man = {"page": "v6_train_atlas.png", "size": [PAGE_W, PAGE_H], "items": {}}
for k in order:
    w, h = ITEMS[k].size
    for sh in shelves:
        if h <= sh[1] and sh[2] + w + GAP <= PAGE_W:
            x, y = sh[2], sh[0]
            sh[2] += w + GAP
            break
    else:
        y = shelves[-1][0] + shelves[-1][1] + GAP if shelves else 0
        if y + h > PAGE_H:
            raise SystemExit("atlas page full")
        shelves.append([y, h, w + GAP])
        x = 0
    page.paste(ITEMS[k], (x, y))
    man["items"][k] = dict(META[k], uv=[x / PAGE_W, 1 - (y + h) / PAGE_H, (x + w) / PAGE_W, 1 - y / PAGE_H], px=[x, y, w, h])
page.save(os.path.join(OUT, man["page"]), optimize=True)
json.dump(man, open(os.path.join(OUT, "v6_train_atlas.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("train atlas items", len(ITEMS), "shelves", len(shelves), "height used", shelves[-1][0] + shelves[-1][1])
