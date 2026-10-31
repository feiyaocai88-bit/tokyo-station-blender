"""Generate the V9 textures for the Sobu / Yokosuka underground station (B5) and its trains.
Run once with any Python that has Pillow; the PNGs go to scripts/textures/ and are loaded (and packed) by
mod9_sobu_underground.py.  Fonts: scripts/fonts/NotoSansJP-*.otf (SIL OFL).

usage: python make9_textures.py [out_dir]

  v9_led_yokosuka_{front,side,runno}_{0,1}.png   destination / run-number LEDs (0 = 横須賀線 普通 久里浜, 1 = 総武線快速 千葉)
  v9_door_markers_yokosuka.png                   乗車位置目標 1-16 in the line colour (JO blue)
  v9_station_sign.png                            駅名標 東京 JO19 with the neighbours 新橋 JO18 / 新日本橋 JO20
  v9_track_signs.png                             番線表示 1-4 (2 x 2 atlas)
  v9_departure_boards.png                        発車標 for tracks 1-4, arrow left / right (1 x 8 atlas)
  v9_wayfinding.png                              出口 / のりば / 丸の内地下中央口 signs (1 x 4 atlas)
  v9_column_numbers.png                          column number plates 1-48 (8 x 6 atlas)
  v9_column_stripes.png                          red / white diagonal guard band
  v9_posters.png                                 four generic travel posters (2 x 2 atlas, no real brands)
"""
import os, sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "textures")
FB = os.path.join(HERE, "fonts", "NotoSansJP-Bold.otf")
FM = os.path.join(HERE, "fonts", "NotoSansJP-Medium.otf")
sys.path.insert(0, HERE)
import make_led_textures as M          # noqa: E402  (V5.1 LED / marker generator, reused)

M.FONT = FB
JO = (0, 103, 192)                     # Yokosuka / Sobu Rapid line colour (JO)
M.LINES["yokosuka"] = [("普通", M.SKY, "久里浜"), ("快速", M.ORANGE, "千葉")]
M.RUNNO["yokosuka"] = ("1219F", "1252F")
M.MARKER_LINES["yokosuka"] = JO


def font(path, size):
    return ImageFont.truetype(path, size)


def text_c(d, xy, txt, f, fill, anchor="mm"):
    d.text(xy, txt, font=f, fill=fill, anchor=anchor)


def fit(d, txt, path, max_w, max_h, start=200):
    s = start
    while s > 8:
        f = font(path, s)
        bb = d.textbbox((0, 0), txt, font=f)
        if bb[2] - bb[0] <= max_w and bb[3] - bb[1] <= max_h:
            return f
        s -= 2
    return font(path, 8)


def jo_badge(d, x, y, s, num):
    """JR East station-number badge: rounded square, line-colour frame, 'JO' over the number."""
    d.rounded_rectangle([x, y, x + s, y + s], radius=s * 0.16, fill=(255, 255, 255), outline=JO, width=max(3, s // 12))
    d.rectangle([x + s * 0.12, y + s * 0.10, x + s * 0.88, y + s * 0.42], fill=(20, 20, 20))
    text_c(d, (x + s / 2, y + s * 0.26), "JO", font(FB, int(s * 0.27)), (255, 255, 255))
    text_c(d, (x + s / 2, y + s * 0.68), num, font(FB, int(s * 0.38)), (20, 20, 20))


def station_sign():
    W, H = 1800, 600
    im = Image.new("RGB", (W, H), (250, 250, 248))
    d = ImageDraw.Draw(im)
    jo_badge(d, 70, 70, 190, "19")
    text_c(d, (W / 2, 95), "とうきょう", font(FB, 70), (30, 30, 30))
    text_c(d, (W / 2, 245), "東京", font(FB, 200), (15, 15, 15))
    text_c(d, (W / 2, 395), "Tōkyō", font(FM, 66), (40, 40, 40))
    text_c(d, (W / 2 + 300, 245), "", font(FM, 30), (0, 0, 0))
    d.rectangle([0, 450, W, 600], fill=JO)
    # neighbours: left = towards Shimbashi (Yokosuka line), right = towards Shin-Nihombashi (Sobu line)
    d.polygon([(40, 525), (80, 490), (80, 560)], fill=(255, 255, 255))
    text_c(d, (110, 500), "しんばし", font(FB, 44), (255, 255, 255), "lm")
    text_c(d, (110, 560), "Shimbashi  JO 18", font(FM, 34), (255, 255, 255), "lm")
    d.polygon([(W - 40, 525), (W - 80, 490), (W - 80, 560)], fill=(255, 255, 255))
    text_c(d, (W - 110, 500), "しんにほんばし", font(FB, 44), (255, 255, 255), "rm")
    text_c(d, (W - 110, 560), "JO 20  Shin-Nihombashi", font(FM, 34), (255, 255, 255), "rm")
    text_c(d, (W / 2, 525), "横須賀線 ・ 総武線(快速)", font(FM, 40), (255, 255, 255))
    return im


TRACK_TXT = {1: ("横須賀線", "品川・横浜・久里浜方面", "Yokosuka Line  for Yokohama, Kurihama"),
             2: ("横須賀線", "品川・横浜・逗子方面", "Yokosuka Line  for Yokohama, Zushi"),
             3: ("総武線(快速)", "船橋・千葉方面", "Sobu Line (Rapid)  for Funabashi, Chiba"),
             4: ("総武線(快速)", "千葉・成田空港方面", "Sobu Line (Rapid)  for Chiba, Narita Airport")}


def track_sign(n):
    W, H = 1200, 300
    im = Image.new("RGB", (W, H), (28, 30, 34))
    d = ImageDraw.Draw(im)
    d.rectangle([24, 24, 276, 276], fill=JO)
    text_c(d, (150, 146), str(n), font(FB, 220), (255, 255, 255))
    line, dest, en = TRACK_TXT[n]
    d.rectangle([300, 40, 312, 260], fill=JO)
    text_c(d, (340, 85), line, font(FB, 64), (255, 255, 255), "lm")
    text_c(d, (340, 170), dest, font(FB, 64), (255, 255, 255), "lm")
    text_c(d, (340, 245), en, font(FM, 36), (210, 215, 220), "lm")
    return im


DEP = {1: [("横須賀線", "15両", "12:08", "久里浜"), ("横須賀線", "11両", "12:36", "逗子")],
       2: [("普通", "15両", "11:53", "逗子"), ("普通", "15両", "12:24", "大船")],
       3: [("快速", "15両", "12:02", "千葉"), ("快速", "11両", "12:17", "津田沼")],
       4: [("快速", "15両", "11:58", "成田空港"), ("快速", "15両", "12:21", "君津")]}


def departure_board(n, arrow):
    W, H = 1024, 256
    im = Image.new("RGB", (W, H), (12, 12, 14))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 64], fill=(36, 38, 42))
    text_c(d, (20, 32), f"{arrow} {n}番線からの発車は", font(FB, 38), (245, 245, 245), "lm")
    text_c(d, (W - 20, 32), f"Departures From Track {n}", font(FM, 26), (200, 200, 200), "rm")
    amber, green, red = (255, 170, 40), (120, 230, 60), (255, 80, 50)
    for i, (typ, cars, t, dest) in enumerate(DEP[n]):
        y = 110 + i * 80
        d.rectangle([10, y - 34, W - 10, y + 34], fill=(6, 6, 7))
        col = red if typ == "横須賀線" else (green if typ == "普通" else (255, 120, 20))
        text_c(d, (30, y), typ, font(FB, 46), col, "lm")
        text_c(d, (330, y), cars, font(FB, 46), amber, "lm")
        text_c(d, (520, y), t, font(FB, 52), amber, "lm")
        text_c(d, (W - 40, y), dest, font(FB, 52), amber, "rm")
    return im


def wayfinding(kind):
    W, H = 1200, 300
    if kind == "exit":
        im = Image.new("RGB", (W, H), (255, 214, 0)); d = ImageDraw.Draw(im)
        d.polygon([(70, 200), (150, 80), (230, 200), (180, 200), (180, 250), (120, 250), (120, 200)], fill=(20, 20, 20))
        text_c(d, (290, 105), "出口", font(FB, 110), (20, 20, 20), "lm")
        text_c(d, (560, 90), "丸の内地下中央口", font(FB, 56), (20, 20, 20), "lm")
        text_c(d, (290, 235), "Exit   Marunouchi Underground Central Exit", font(FM, 44), (20, 20, 20), "lm")
    elif kind == "transfer":
        im = Image.new("RGB", (W, H), (28, 30, 34)); d = ImageDraw.Draw(im)
        for i, (lab, col) in enumerate((("山手線", (120, 185, 30)), ("中央線", (235, 110, 20)), ("新幹線", (20, 70, 160)))):
            d.rectangle([40 + i * 250, 40, 270 + i * 250, 140], fill=col)
            text_c(d, (155 + i * 250, 90), lab, font(FB, 52), (255, 255, 255))
        text_c(d, (40, 225), "のりかえ  Transfer  ↑", font(FB, 64), (255, 255, 255), "lm")
    elif kind == "platforms":
        im = Image.new("RGB", (W, H), (28, 30, 34)); d = ImageDraw.Draw(im)
        d.rectangle([30, 40, 230, 260], fill=JO)
        text_c(d, (130, 150), "JO", font(FB, 110), (255, 255, 255))
        text_c(d, (270, 100), "総武線(快速)・横須賀線", font(FB, 64), (255, 255, 255), "lm")
        text_c(d, (270, 190), "Sobu Line (Rapid) / Yokosuka Line", font(FM, 42), (215, 220, 225), "lm")
        text_c(d, (270, 255), "地下5階 1～4番線  ↓", font(FB, 44), (255, 255, 255), "lm")
    else:  # "gates"
        im = Image.new("RGB", (W, H), (28, 30, 34)); d = ImageDraw.Draw(im)
        text_c(d, (60, 105), "← 丸の内地下中央口", font(FB, 70), (255, 255, 255), "lm")
        text_c(d, (60, 220), "Marunouchi Underground Central Exit", font(FM, 46), (215, 220, 225), "lm")
    return im


def column_numbers():
    cw, ch = 256, 192
    im = Image.new("RGB", (cw * 8, ch * 6), (245, 245, 240))
    d = ImageDraw.Draw(im)
    for n in range(48):
        x, y = (n % 8) * cw, (n // 8) * ch
        d.rectangle([x + 6, y + 6, x + cw - 6, y + ch - 6], fill=(250, 250, 246), outline=(40, 40, 40), width=6)
        text_c(d, (x + cw / 2, y + ch / 2 + 4), str(n + 1), font(FB, 130), (20, 20, 20))
    return im


def column_stripes():
    S = 512
    im = Image.new("RGB", (S, S), (245, 245, 242))
    d = ImageDraw.Draw(im)
    w = S // 4
    for k in range(-4, 9):
        x0 = k * 2 * w
        d.polygon([(x0, S), (x0 + w, S), (x0 + w + S, 0), (x0 + S, 0)], fill=(205, 30, 35))
    return im


def posters():
    cw, ch = 600, 840
    im = Image.new("RGB", (cw * 2, ch * 2), (255, 255, 255))
    d = ImageDraw.Draw(im)
    spec = [("鎌倉", "KAMAKURA", (36, 92, 140), (230, 190, 90)), ("房総", "BOSO", (20, 120, 150), (250, 240, 220)),
            ("横須賀", "YOKOSUKA", (25, 45, 90), (240, 120, 60)), ("成田", "NARITA", (110, 40, 60), (245, 225, 200))]
    for i, (jp, en, c1, c2) in enumerate(spec):
        x, y = (i % 2) * cw, (i // 2) * ch
        for r in range(ch):
            t = r / ch
            col = tuple(int(c1[k] * (1 - t) + c2[k] * t) for k in range(3))
            d.line([(x, y + r), (x + cw, y + r)], fill=col)
        d.ellipse([x + 150, y + 180, x + 450, y + 480], fill=(250, 245, 230))
        d.polygon([(x, y + 640), (x + 220, y + 470), (x + 400, y + 600), (x + cw, y + 430), (x + cw, y + ch), (x, y + ch)],
                  fill=tuple(int(v * 0.55) for v in c1))
        text_c(d, (x + cw / 2, y + 90), jp, font(FB, 110), (255, 255, 255))
        text_c(d, (x + cw / 2, y + 760), en, font(FM, 54), (255, 255, 255))
    return im


def main():
    os.makedirs(OUT, exist_ok=True)
    out = []
    for kind in ("front_e235", "side"):            # E235 cab: 224 x 32 dot front display (as led_yamanote_front)
        for v in (0, 1):
            p = os.path.join(OUT, f"v9_led_yokosuka_{kind.split('_')[0]}_{v}.png"); M.destination(kind, "yokosuka", v).save(p); out.append(p)
    for v in (0, 1):
        p = os.path.join(OUT, f"v9_led_yokosuka_runno_{v}.png"); M.runno("yokosuka", v).save(p); out.append(p)
    p = os.path.join(OUT, "v9_door_markers_yokosuka.png"); M.door_marker_atlas("yokosuka").save(p); out.append(p)
    p = os.path.join(OUT, "v9_station_sign.png"); station_sign().save(p); out.append(p)
    at = Image.new("RGB", (2400, 600))
    for n in range(1, 5):
        at.paste(track_sign(n), (((n - 1) % 2) * 1200, ((n - 1) // 2) * 300))
    p = os.path.join(OUT, "v9_track_signs.png"); at.save(p); out.append(p)
    at = Image.new("RGB", (1024, 2048))            # row 2(n-1): arrow left, row 2(n-1)+1: arrow right
    for n in range(1, 5):
        at.paste(departure_board(n, "←"), (0, (2 * n - 2) * 256))
        at.paste(departure_board(n, "→"), (0, (2 * n - 1) * 256))
    p = os.path.join(OUT, "v9_departure_boards.png"); at.save(p); out.append(p)
    at = Image.new("RGB", (1200, 1200))
    for i, k in enumerate(("exit", "platforms", "transfer", "gates")):
        at.paste(wayfinding(k), (0, i * 300))
    p = os.path.join(OUT, "v9_wayfinding.png"); at.save(p); out.append(p)
    p = os.path.join(OUT, "v9_column_numbers.png"); column_numbers().save(p); out.append(p)
    p = os.path.join(OUT, "v9_column_stripes.png"); column_stripes().save(p); out.append(p)
    p = os.path.join(OUT, "v9_posters.png"); posters().save(p); out.append(p)
    for q in out:
        print(os.path.basename(q), Image.open(q).size)


if __name__ == "__main__":
    main()
