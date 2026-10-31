"""Generate the V5.1 textures: dot-matrix LED destination / run-number displays of the commuter trains,
platform door-position floor markers, stop-position boards and signal identification plates.
Run once with any Python that has Pillow and a CJK font; the PNGs are shipped in scripts/textures/ and loaded
(and packed) by mod_train_bodies.py.

usage: python3 make_led_textures.py [out_dir]
"""
import os, sys
from PIL import Image, ImageDraw, ImageFont

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "textures")
FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
DOT = 5                                     # pixels per LED dot

WHITE = (255, 236, 200)
ORANGE = (255, 120, 20)
SKY = (70, 190, 255)
GREEN = (120, 230, 60)
YAMANOTE = (150, 230, 40)
AMBER = (255, 170, 40)

# line -> variant -> (type text, type colour, destination text)
LINES = {
    "chuo":     [("快速", ORANGE, "高尾"), ("快速", ORANGE, "高尾")],
    "kt":       [("各駅停車", SKY, "大宮"), ("各駅停車", SKY, "大船")],
    "tokaido":  [("普通", GREEN, "熱海"), ("普通", GREEN, "宇都宮")],
    "yamanote": [("山手線", YAMANOTE, "上野・池袋方面"), ("山手線", YAMANOTE, "品川・渋谷方面")],
}
RUNNO = {"chuo": ("1215T", "1215T"), "kt": ("1305A", "1342A"), "tokaido": ("1523E", "1608M"),
         "yamanote": ("1418G", "1527G")}
# dot grid (columns x rows) per display kind, matching the panel aspect ratios in the model
GRID = {"front": (200, 30), "front_e235": (224, 32), "side": (176, 28), "runno": (64, 18)}


def text_mask(txt, cols, rows, size_px, x0, colour, img, y_off=0):
    """Render txt at dot resolution into img (an RGB dot-grid image), left-aligned at column x0."""
    f = ImageFont.truetype(FONT, size_px)
    tmp = Image.new("L", (cols, rows), 0)
    d = ImageDraw.Draw(tmp)
    bb = d.textbbox((0, 0), txt, font=f)
    h = bb[3] - bb[1]
    d.text((x0 - bb[0], (rows - h) // 2 - bb[1] + y_off), txt, font=f, fill=255)
    px = tmp.load(); out = img.load()
    for y in range(rows):
        for x in range(cols):
            if px[x, y] > 110:
                out[x, y] = colour
    return bb[2] - bb[0]


def fit_size(txt, max_w, max_h):
    for s in range(max_h, 6, -1):
        f = ImageFont.truetype(FONT, s)
        bb = ImageDraw.Draw(Image.new("L", (1, 1))).textbbox((0, 0), txt, font=f)
        if bb[2] - bb[0] <= max_w and bb[3] - bb[1] <= max_h:
            return s
    return 7


def dots(grid_img):
    """Upscale a dot-grid image to round LED dots on a black panel (unlit dots faintly visible)."""
    cols, rows = grid_img.size
    out = Image.new("RGB", (cols * DOT, rows * DOT), (6, 6, 7))
    d = ImageDraw.Draw(out)
    gp = grid_img.load()
    for y in range(rows):
        for x in range(cols):
            c = gp[x, y]
            lit = c != (0, 0, 0)
            col = c if lit else (22, 20, 18)
            r = DOT * (0.42 if lit else 0.34)
            cx, cy = x * DOT + DOT / 2, y * DOT + DOT / 2
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    return out


def destination(kind, line, variant):
    cols, rows = GRID[kind]
    typ, tcol, dest = LINES[line][variant]
    g = Image.new("RGB", (cols, rows), (0, 0, 0))
    # type block on the left (about 38 % of the width), destination centred in the rest
    tw = int(cols * (0.40 if len(typ) > 2 else 0.30))
    s = fit_size(typ, tw - 6, rows - 6)
    w = text_mask(typ, cols, rows, s, 3, tcol, g)
    rest0 = max(w + 10, tw + 2)
    s2 = fit_size(dest, cols - rest0 - 4, rows - 4)
    f = ImageFont.truetype(FONT, s2)
    dw = ImageDraw.Draw(Image.new("L", (1, 1))).textbbox((0, 0), dest, font=f)
    dwid = dw[2] - dw[0]
    text_mask(dest, cols, rows, s2, rest0 + (cols - rest0 - dwid) // 2, WHITE, g)
    # thin separator between type and destination
    gp = g.load()
    for y in range(3, rows - 3):
        gp[rest0 - 5, y] = (60, 60, 60)
    return dots(g)


def runno(line, variant):
    cols, rows = GRID["runno"]
    g = Image.new("RGB", (cols, rows), (0, 0, 0))
    txt = RUNNO[line][variant]
    s = fit_size(txt, cols - 4, rows - 2)
    f = ImageFont.truetype(FONT, s)
    bb = ImageDraw.Draw(Image.new("L", (1, 1))).textbbox((0, 0), txt, font=f)
    text_mask(txt, cols, rows, s, (cols - (bb[2] - bb[0])) // 2, AMBER, g)
    return dots(g)


# ------------------------------------------------------------------ platform signs (V5.1)
MARKER_LINES = {"chuo": (235, 110, 20), "kt": (0, 160, 220), "yamanote": (120, 185, 30), "tokaido": (240, 120, 20),
                "tokaido_shinkansen": (20, 70, 160), "tohoku_shinkansen": (0, 140, 90)}


def door_marker_atlas(line):
    """4 x 4 atlas: car numbers 1-16, floor marker (乗車位置目標) in the line colour."""
    cw, ch = 192, 128
    im = Image.new("RGB", (cw * 4, ch * 4), (40, 40, 40))
    d = ImageDraw.Draw(im)
    col = MARKER_LINES[line]
    f_big = ImageFont.truetype(FONT, 64); f_small = ImageFont.truetype(FONT, 26)
    for n in range(16):
        cx, cy = (n % 4) * cw, (n // 4) * ch
        d.rounded_rectangle([cx + 6, cy + 6, cx + cw - 6, cy + ch - 6], radius=18, fill=col)
        num = str(n + 1)
        bb = d.textbbox((0, 0), num, font=f_big)
        d.text((cx + 22 - bb[0], cy + (ch - (bb[3] - bb[1])) // 2 - bb[1] - 8), num, font=f_big, fill=(255, 255, 255))
        d.text((cx + 22 + (bb[2] - bb[0]) + 6, cy + 54), "号車", font=f_small, fill=(255, 255, 255))
        for k in (0, 1):                                  # door arrows
            x0 = cx + 120 + k * 32
            d.polygon([(x0, cy + 46), (x0 + 24, cy + 46), (x0 + 12, cy + 26)], fill=(255, 255, 255))   # towards the track
        d.rectangle([cx + 118, cy + 92, cx + 178, cy + 98], fill=(255, 255, 255))
    return im


def stop_board(n, shinkansen=False):
    """停止位置目標: white board, black frame, number of cars (Shinkansen: blue numerals)."""
    w, h = 240, 300
    im = Image.new("RGB", (w, h), (250, 250, 248))
    d = ImageDraw.Draw(im)
    d.rectangle([4, 4, w - 5, h - 5], outline=(15, 15, 15), width=10)
    f = ImageFont.truetype(FONT, 150 if n < 10 else 128)
    txt = str(n)
    bb = d.textbbox((0, 0), txt, font=f)
    d.text(((w - (bb[2] - bb[0])) // 2 - bb[0], (h - (bb[3] - bb[1])) // 2 - bb[1] - 6), txt, font=f,
           fill=(20, 60, 170) if shinkansen else (10, 10, 10))
    return im


def signal_plate(txt):
    """Signal identification plate (white on black), e.g. 出4."""
    w, h = 200, 90
    im = Image.new("RGB", (w, h), (10, 10, 10))
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(FONT, 62)
    bb = d.textbbox((0, 0), txt, font=f)
    d.text(((w - (bb[2] - bb[0])) // 2 - bb[0], (h - (bb[3] - bb[1])) // 2 - bb[1]), txt, font=f, fill=(245, 245, 245))
    return im


def main():
    os.makedirs(OUT, exist_ok=True)
    n = 0
    for line in MARKER_LINES:
        door_marker_atlas(line).save(os.path.join(OUT, f"door_markers_{line}.png"), optimize=True); n += 1
    for k in (8, 10, 11, 12, 15, 16, 17):
        stop_board(k).save(os.path.join(OUT, f"stop_{k}.png"), optimize=True)
        stop_board(k, True).save(os.path.join(OUT, f"stop_{k}_shinkansen.png"), optimize=True); n += 2
    for t in range(1, 11):
        signal_plate(f"出{t}").save(os.path.join(OUT, f"signal_plate_{t:02d}.png"), optimize=True); n += 1
    for line in LINES:
        for v in (0, 1):
            for kind in (("front_e235", "side") if line == "yamanote" else ("front", "side")):
                im = destination(kind, line, v)
                im.save(os.path.join(OUT, f"led_{line}_{kind.split('_')[0]}_{v}.png"), optimize=True)
                n += 1
            runno(line, v).save(os.path.join(OUT, f"led_{line}_runno_{v}.png"), optimize=True)
            n += 1
    print("wrote", n, "textures to", OUT)


if __name__ == "__main__":
    main()
