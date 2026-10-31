"""V6 platform sign textures (run once with any Python that has Pillow; no Blender needed).

Draws, in the JR East sign style (black boards with white text, yellow exit panels, line-colour number tiles):
- 番線案内 platform/direction boards for each island and each viewing side
- 出口・通路 exit / passage / transfer signs over the stair entrances
- 停車駅のご案内 stop-pattern boards for every line that departs from these platforms
- one schematic route map of the JR lines around Tokyo (major stations only, illustrative, not the official map)
- Shinkansen car-number boards, a platform clock face, the emergency-stop button label
and packs everything into 4096 px atlas pages + a JSON manifest that mod6_platforms.py reads.

usage: python make6_sign_textures.py [out_dir]
Fonts: Noto Sans JP Bold/Medium (SIL OFL, shipped in scripts/fonts/; the closest free match to the Shin Go gothic of the
JR East signs and the same family as the V5 station-name boards) for Japanese, Segoe UI (Frutiger-like) for English;
Yu Gothic / Noto Sans CJK / DejaVu are fallbacks.
Line colours / codes: JR East station-numbering colours. Platform assignments: JR East Tokyo station page
(https://www.jreast.co.jp/estation/stations/1039.html); the exact wording of the boards is illustrative.
"""
import os, sys, json, math
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "textures")
os.makedirs(OUT, exist_ok=True)


def _first(paths):
    for p in paths:
        if os.path.exists(p):
            return p
    raise FileNotFoundError(paths[0])


JP_B = _first([os.path.join(HERE, "fonts", "NotoSansJP-Bold.otf"), "C:/Windows/Fonts/YuGothB.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"])
JP_M = _first([os.path.join(HERE, "fonts", "NotoSansJP-Medium.otf"), "C:/Windows/Fonts/YuGothM.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc",
               "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"])
EN_B = _first(["C:/Windows/Fonts/segoeuib.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"])
EN_R = _first(["C:/Windows/Fonts/segoeui.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"])
_F = {}


def F(path, size):
    key = (path, int(size))
    if key not in _F:
        _F[key] = ImageFont.truetype(path, int(size))
    return _F[key]


def tw(d, s, font):
    b = d.textbbox((0, 0), s, font=font)
    return b[2] - b[0]


def fit(d, s, path, size, max_w, min_size=10):
    while size > min_size and tw(d, s, F(path, size)) > max_w:
        size -= 1
    return F(path, size)


def text(d, xy, s, path, size, fill, anchor="lm", max_w=None):
    f = fit(d, s, path, size, max_w) if max_w else F(path, size)
    d.text(xy, s, font=f, fill=fill, anchor=anchor)
    return tw(d, s, f)


def arrow(d, cx, cy, size, direction, fill):
    """Solid sign arrow (shaft + head) pointing left/right/up/down, centred at (cx, cy)."""
    s = size / 2
    pts = [(-s, -0.18 * s), (0.05 * s, -0.18 * s), (0.05 * s, -0.62 * s), (s, 0), (0.05 * s, 0.62 * s), (0.05 * s, 0.18 * s), (-s, 0.18 * s)]
    rot = {"right": 0, "down": 90, "left": 180, "up": 270}[direction]
    c, sn = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    d.polygon([(cx + x * c - y * sn, cy + x * sn + y * c) for x, y in pts], fill=fill)


BLACK = (34, 35, 38)
WHITE = (255, 255, 255)
YELLOW = (255, 210, 0)
INK = (26, 26, 26)
GREY = (150, 150, 150)

# ------------------------------------------------------------------ line data
LINE = {  # code: (jp, en, colour)
    "JC": ("中央線（快速）", "Chūō Line (Rapid)", (241, 90, 34)),
    "JK": ("京浜東北線", "Keihin-Tōhoku Line", (0, 178, 229)),
    "JY": ("山手線", "Yamanote Line", (128, 194, 65)),
    "JU": ("上野東京ライン", "Ueno-Tokyo Line", (246, 139, 30)),
    "JT": ("東海道線", "Tōkaidō Line", (246, 139, 30)),
    "JO": ("総武快速線・横須賀線", "Sōbu (Rapid) / Yokosuka Line", (0, 103, 192)),
    "JE": ("京葉線", "Keiyō Line", (201, 37, 47)),
    "JB": ("中央・総武線（各停）", "Chūō-Sōbu Line", (255, 212, 0)),
    "JA": ("埼京線", "Saikyō Line", (0, 172, 154)),
    "JJ": ("常磐線（快速）", "Jōban Line (Rapid)", (0, 178, 97)),
    "M": ("丸ノ内線", "Marunouchi Line", (246, 46, 54)),
    "SK": ("東海道・山陽新幹線", "Tōkaidō & San'yō Shinkansen", (0, 114, 186)),
    "SE": ("東北・北海道・山形・秋田新幹線", "Tōhoku, Hokkaidō, Yamagata & Akita Shinkansen", (0, 154, 68)),
    "SJ": ("上越・北陸新幹線", "Jōetsu & Hokuriku Shinkansen", (0, 154, 68)),
    "SH": ("新幹線", "Shinkansen", (0, 114, 186)),
    "JR": ("在来線", "JR Lines", (0, 136, 3)),
}
# platform number -> (code, direction JP, direction EN, departs toward -X (north) ?)
TRACK = {
    1: ("JC", "神田・新宿・高尾方面", "for Kanda, Shinjuku & Takao", True),
    2: ("JC", "神田・新宿・高尾方面", "for Kanda, Shinjuku & Takao", True),
    3: ("JK", "上野・赤羽・大宮方面", "for Ueno, Akabane & Ōmiya", True),
    4: ("JY", "上野・池袋方面", "for Ueno & Ikebukuro", True),
    5: ("JY", "品川・渋谷方面", "for Shinagawa & Shibuya", False),
    6: ("JK", "品川・横浜・大船方面", "for Shinagawa, Yokohama & Ōfuna", False),
    7: ("JU", "宇都宮・高崎・常磐線方面", "for Utsunomiya, Takasaki & Jōban Lines", True),
    8: ("JU", "宇都宮・高崎・常磐線方面", "for Utsunomiya, Takasaki & Jōban Lines", True),
    9: ("JT", "品川・横浜・小田原・熱海方面", "for Yokohama, Odawara & Atami", False),
    10: ("JT", "品川・横浜・小田原・熱海方面", "for Yokohama, Odawara & Atami", False),
}
for _t in range(14, 20):
    TRACK[_t] = ("SK", "新横浜・名古屋・京都・新大阪方面", "for Nagoya, Kyōto & Shin-Ōsaka", False)
for _t in (20, 21):
    TRACK[_t] = ("SE", "大宮・仙台・盛岡・新函館北斗方面", "for Sendai, Morioka & Shin-Hakodate-Hokuto", True)
for _t in (22, 23):
    TRACK[_t] = ("SJ", "大宮・高崎・新潟・長野・金沢方面", "for Niigata, Nagano & Kanazawa", True)
ISLANDS = [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (14, 15), (16, 17), (18, 19), (20, 21), (22, 23)]

ITEMS = {}      # key -> PIL image
META = {}       # key -> dict(size_m=(w, h), ...)


def new(key, w_m, h_m, ppm, bg=BLACK, mode="RGB"):
    W, H = int(round(w_m * ppm)), int(round(h_m * ppm))
    im = Image.new(mode, (W, H), bg)
    ITEMS[key] = im
    META[key] = {"size_m": [w_m, h_m]}
    return im, ImageDraw.Draw(im), W, H


def number_tile(d, x, y, s, t):
    code, _, _, _ = TRACK[t]
    col = LINE[code][2]
    d.rounded_rectangle([x, y, x + s, y + s], radius=int(s * 0.12), fill=col)
    num = str(t)
    light = sum(col) > 520
    text(d, (x + s / 2, y + s / 2 + 2), num, EN_B, int(s * (0.78 if len(num) == 1 else 0.62)), INK if light else WHITE, anchor="mm")


# ----------------------------------------------------------- 番線案内 boards
def platform_half(d, x0, x1, H, t, side):
    """One half of a direction board: side='left' (arrow at the left end) or 'right'."""
    code, djp, den, _ = TRACK[t]
    ljp, len_, col = LINE[code]
    pad = 14
    tile = H - 2 * pad - 8
    if side == "left":
        arrow(d, x0 + 52, H / 2, 72, "left", WHITE)
        tx = x0 + 100
    else:
        arrow(d, x1 - 52, H / 2, 72, "right", WHITE)
        tx = x0 + 18
    number_tile(d, tx, pad + 4, tile, t)
    bx = tx + tile + 18
    maxw = (x1 - 110 if side == "right" else x1 - 14) - bx
    # line-colour bar under the line name
    jw = text(d, (bx, 38), ljp, JP_B, 40, WHITE, max_w=maxw)
    rest = maxw - jw - 16
    if rest > 120:
        text(d, (bx + jw + 16, 42), len_, EN_R, 20, (220, 220, 220), max_w=rest)
    d.rectangle([bx, 64, bx + maxw, 69], fill=col)
    text(d, (bx, 108), djp, JP_B, 50, WHITE, max_w=maxw)
    text(d, (bx, 160), den, EN_R, 24, (230, 230, 230), max_w=maxw)


def direction_board(isl, view):
    """view 'N': seen by a person looking +X (south); right = west track. view 'S': looking -X; right = east track."""
    tw_, te_ = isl
    key = f"dir_{tw_:02d}-{te_:02d}_{view}"
    im, d, W, H = new(key, 3.8, 0.5, 400)
    right, left = (tw_, te_) if view == "N" else (te_, tw_)
    platform_half(d, 0, W // 2 - 4, H, left, "left")
    platform_half(d, W // 2 + 4, W, H, right, "right")
    d.rectangle([W // 2 - 2, 14, W // 2 + 2, H - 14], fill=(90, 90, 92))
    META[key].update({"left_track": left, "right_track": right, "view": view})


# --------------------------------------------------------- 出口・通路 signs
PASSAGE = {"N": ("北通路", "North Passage"), "C": ("中央通路", "Central Passage"), "S": ("南通路", "South Passage")}
EXITS = {
    ("conv", "N"): [("丸の内北口", "Marunouchi North"), ("八重洲北口", "Yaesu North"), ("日本橋口", "Nihombashi")],
    ("conv", "C"): [("丸の内中央口", "Marunouchi Central"), ("八重洲中央口", "Yaesu Central")],
    ("conv", "S"): [("丸の内南口", "Marunouchi South"), ("八重洲南口", "Yaesu South")],
    ("tokaido", "N"): [("八重洲北口", "Yaesu North"), ("日本橋口", "Nihombashi")],
    ("tokaido", "C"): [("八重洲中央口", "Yaesu Central"), ("丸の内中央口", "Marunouchi Central")],
    ("tokaido", "S"): [("八重洲南口", "Yaesu South"), ("丸の内南口", "Marunouchi South")],
    ("tohoku", "N"): [("丸の内北口", "Marunouchi North"), ("八重洲北口", "Yaesu North")],
    ("tohoku", "C"): [("丸の内中央口", "Marunouchi Central"), ("八重洲中央口", "Yaesu Central")],
    ("tohoku", "S"): [("丸の内南口", "Marunouchi South"), ("八重洲南口", "Yaesu South")],
}
TRANSFER = {
    ("conv", "N"): [("SH", "新幹線"), ("M", "丸ノ内線")],
    ("conv", "C"): [("SH", "新幹線"), ("JO", "総武快速・横須賀線")],
    ("conv", "S"): [("JE", "京葉線"), ("SH", "新幹線")],
    ("tokaido", "N"): [("JR", "在来線"), ("SE", "東北・上越・北陸新幹線")],
    ("tokaido", "C"): [("JR", "在来線"), ("SE", "東北・上越・北陸新幹線")],
    ("tokaido", "S"): [("JR", "在来線"), ("JE", "京葉線")],
    ("tohoku", "N"): [("SK", "東海道新幹線"), ("JR", "在来線")],
    ("tohoku", "C"): [("SK", "東海道新幹線"), ("JR", "在来線")],
    ("tohoku", "S"): [("SK", "東海道新幹線"), ("JE", "京葉線")],
}
TR_EN = {"SH": "Shinkansen", "SK": "Tōkaidō Shinkansen", "SE": "Tōhoku, Jōetsu & Hokuriku Shinkansen", "JR": "JR Lines",
         "M": "Marunouchi Line (Tokyo Metro)", "JO": "Sōbu (Rapid) / Yokosuka Line", "JE": "Keiyō Line"}
BADGE = {"SH": "新", "SK": "新", "SE": "新", "JR": "JR", "M": "M", "JO": "JO", "JE": "JE"}


def exit_sign(group, pos, arrow_dir="down"):
    key = f"exit_{group}_{pos}_{arrow_dir}"
    im, d, W, H = new(key, 3.8, 0.5, 400)
    a1, a2 = 600, 1150
    # section A: passage (black)
    arrow(d, 66, H / 2, 104, arrow_dir, WHITE)
    if group == "conv":
        jp, en = PASSAGE[pos]
    else:
        jp, en = "出口・のりかえ", "Exit / Transfers"
    text(d, (138, 82), jp, JP_B, 66, WHITE, max_w=a1 - 150)
    text(d, (140, 150), en, EN_B, 30, WHITE, max_w=a1 - 150)
    # section B: exits (yellow)
    d.rectangle([a1, 0, a2, H], fill=YELLOW)
    text(d, (a1 + 22, 76), "出口", JP_B, 58, INK)
    text(d, (a1 + 24, 140), "Exit", EN_B, 30, INK)
    rows = EXITS[(group, pos)]
    rh = (H - 24) / len(rows)
    for i, (j, e) in enumerate(rows):
        cy = 12 + rh * (i + 0.5)
        text(d, (a1 + 150, cy - 10), j, JP_B, 36 if len(rows) < 3 else 30, INK, max_w=a2 - a1 - 160)
        text(d, (a1 + 152, cy + 22 if len(rows) < 3 else cy + 16), e, EN_R, 18 if len(rows) < 3 else 15, INK, max_w=a2 - a1 - 160)
    # section C: transfers (black)
    text(d, (a2 + 18, 30), "のりかえ", JP_B, 28, WHITE)
    text(d, (a2 + 150, 32), "Transfer", EN_R, 18, (220, 220, 220))
    for i, (code, jp2) in enumerate(TRANSFER[(group, pos)]):
        y = 66 + i * 62
        col = LINE[code][2]
        d.rounded_rectangle([a2 + 18, y, a2 + 70, y + 52], radius=7, fill=col)
        text(d, (a2 + 44, y + 27), BADGE[code], EN_B if code != "SH" and code not in ("SK", "SE") else JP_B, 26, WHITE, anchor="mm")
        text(d, (a2 + 82, y + 18), jp2, JP_B, 28, WHITE, max_w=W - a2 - 92)
        text(d, (a2 + 83, y + 44), TR_EN[code], EN_R, 14, (210, 210, 210), max_w=W - a2 - 92)
    META[key].update({"group": group, "pos": pos, "arrow": arrow_dir})


# ------------------------------------------------- 停車駅のご案内 stop boards
STOPS = {
    "JC_W": ("JC", "東京 神田 御茶ノ水 四ツ谷 新宿 中野 高円寺 阿佐ケ谷 荻窪 西荻窪 吉祥寺 三鷹 武蔵境 東小金井 武蔵小金井 国分寺 西国分寺 国立 立川 日野 豊田 八王子 西八王子 高尾", None),
    "JK_N": ("JK", "東京 神田 秋葉原 御徒町 上野 鶯谷 日暮里 西日暮里 田端 上中里 王子 東十条 赤羽 川口 西川口 蕨 南浦和 浦和 北浦和 与野 さいたま新都心 大宮", None),
    "JY_IN": ("JY", "東京 神田 秋葉原 御徒町 上野 鶯谷 日暮里 西日暮里 田端 駒込 巣鴨 大塚 池袋 目白 高田馬場 新大久保 新宿 代々木 原宿 渋谷 恵比寿 目黒 五反田 大崎 品川 高輪ゲートウェイ 田町 浜松町 新橋 有楽町 東京", "内回り"),
    "JY_OUT": ("JY", "東京 有楽町 新橋 浜松町 田町 高輪ゲートウェイ 品川 大崎 五反田 目黒 恵比寿 渋谷 原宿 代々木 新宿 新大久保 高田馬場 目白 池袋 大塚 巣鴨 駒込 田端 西日暮里 日暮里 鶯谷 上野 御徒町 秋葉原 神田 東京", "外回り"),
    "JK_S": ("JK", "東京 有楽町 新橋 浜松町 田町 高輪ゲートウェイ 品川 大井町 大森 蒲田 川崎 鶴見 新子安 東神奈川 横浜 桜木町 関内 石川町 山手 根岸 磯子 新杉田 洋光台 港南台 本郷台 大船", None),
    "JU_N": ("JU", "東京 上野 尾久 赤羽 浦和 さいたま新都心 大宮", "BRANCH"),
    "JT_S": ("JT", "東京 新橋 品川 川崎 横浜 戸塚 大船 藤沢 辻堂 茅ケ崎 平塚 大磯 二宮 国府津 鴨宮 小田原 早川 根府川 真鶴 湯河原 熱海", None),
    "SK": ("SK", "東京 品川 新横浜 小田原 熱海 三島 新富士 静岡 掛川 浜松 豊橋 三河安城 名古屋 岐阜羽島 米原 京都 新大阪", "のぞみ:東京 品川 新横浜 名古屋 京都 新大阪"),
    "SE": ("SE", "東京 上野 大宮 小山 宇都宮 那須塩原 新白河 郡山 福島 白石蔵王 仙台 古川 くりこま高原 一ノ関 水沢江刺 北上 新花巻 盛岡 いわて沼宮内 二戸 八戸 七戸十和田 新青森 新函館北斗", "はやぶさ:東京 上野 大宮 仙台 盛岡 八戸 新青森 新函館北斗"),
    "SJ": ("SJ", "東京 上野 大宮 熊谷 本庄早稲田 高崎 安中榛名 軽井沢 佐久平 上田 長野 飯山 上越妙高 糸魚川 黒部宇奈月温泉 富山 新高岡 金沢", "かがやき:東京 上野 大宮 長野 富山 金沢"),
}
TRACK_STOPS = {1: "JC_W", 2: "JC_W", 3: "JK_N", 4: "JY_IN", 5: "JY_OUT", 6: "JK_S", 7: "JU_N", 8: "JU_N", 9: "JT_S", 10: "JT_S",
               14: "SK", 15: "SK", 16: "SK", 17: "SK", 18: "SK", 19: "SK", 20: "SE", 21: "SE", 22: "SJ", 23: "SJ"}
VERT = {"ー": "｜", "（": "︵", "）": "︶"}


def vtext(d, x, y, s, size, fill):
    f = F(JP_B, size)
    for i, ch in enumerate(s):
        d.text((x, y + i * size * 1.02), VERT.get(ch, ch), font=f, fill=fill, anchor="mt")


def stop_board(key):
    code, line, extra = STOPS[key]
    st = line.split()
    ljp, len_, col = LINE[code]
    im, d, W, H = new(f"stops_{key}", 4.8, 0.6, 500, bg=(246, 246, 244))
    # title block in the line colour
    tbw = 470
    d.rectangle([0, 0, tbw, H], fill=col)
    light = sum(col) > 520
    fg = INK if light else WHITE
    text(d, (24, 50), "停車駅のご案内", JP_B, 40, fg)
    text(d, (26, 92), "Stops", EN_B, 24, fg)
    text(d, (24, 160), ljp, JP_B, 54, fg, max_w=tbw - 40)
    text(d, (26, 212), len_, EN_R, 24, fg, max_w=tbw - 40)
    if extra and extra in ("内回り", "外回り"):
        text(d, (24, 262), extra + ("（上野・池袋方面）" if extra == "内回り" else "（品川・渋谷方面）"), JP_B, 26, fg, max_w=tbw - 40)
    x0, x1 = tbw + 70, W - 80
    yb = 84
    if extra == "BRANCH":
        x1 = W - 700
    n = len(st)
    dx = (x1 - x0) / max(1, n - 1)
    d.rectangle([x0 - 20, yb - 9, x1 + 20, yb + 9], fill=col)
    arrow(d, x1 + 50, yb, 56, "right", col)
    fast = set(extra.split(":")[1].split()) if extra and ":" in extra else set()
    size = int(min(30, (H - yb - 40) / max(len(s) for s in st) / 1.02, dx * 0.62))
    for i, s in enumerate(st):
        x = x0 + i * dx
        big = (s in fast) or (i == 0)
        r = 15 if big else 11
        d.ellipse([x - r, yb - r, x + r, yb + r], fill=WHITE, outline=INK if (big and fast) else col, width=5 if big else 4)
        if s in fast:
            d.ellipse([x - 6, yb - 6, x + 6, yb + 6], fill=INK)
        vtext(d, x, yb + 26, s, size, INK)
    # 現在地 marker on Tokyo
    d.rounded_rectangle([x0 - 46, 8, x0 + 46, 46], radius=8, fill=(226, 0, 26))
    text(d, (x0, 28), "現在地", JP_B, 24, WHITE, anchor="mm")
    if fast:
        lab = extra.split(":")[0]
        d.ellipse([W - 330, H - 52, W - 306, H - 28], fill=WHITE, outline=INK, width=5)
        d.ellipse([W - 324, H - 46, W - 312, H - 34], fill=INK)
        text(d, (W - 296, H - 40), f"{lab} 停車駅", JP_B, 24, INK)
    if extra == "BRANCH":
        bx = x1 + 120
        rows = [("JU", "宇都宮線", "大宮から 宇都宮・黒磯方面"), ("JU", "高崎線", "大宮から 熊谷・高崎方面"), ("JJ", "常磐線", "上野から 取手・土浦方面")]
        for i, (c2, n2, t2) in enumerate(rows):
            y = 40 + i * 82
            d.rounded_rectangle([bx, y, bx + 56, y + 56], radius=8, fill=LINE[c2][2])
            text(d, (bx + 28, y + 29), c2, EN_B, 24, WHITE, anchor="mm")
            text(d, (bx + 72, y + 18), n2 + " 直通", JP_B, 30, INK)
            text(d, (bx + 72, y + 48), t2, JP_M, 22, (60, 60, 60), max_w=W - bx - 90)
    META[f"stops_{key}"].update({"line": code})


# --------------------------------------------------------- route map (illustrative)
def route_map():
    im, d, W, H = new("routemap", 2.6, 1.4, 1000, bg=(250, 250, 248))
    d.rectangle([0, 0, W, 104], fill=(0, 136, 3))
    text(d, (40, 52), "JR線路線図", JP_B, 58, WHITE)
    text(d, (400, 40), "JR Lines around Tokyo", EN_B, 34, WHITE)
    text(d, (402, 78), "主要駅のみ・概略図   major stations only, schematic", JP_M, 22, (220, 240, 220))
    # ---- Yamanote loop: rounded rectangle, stations spread between geographic anchors
    L0, R0, T0, B0, RAD = 700, 1500, 330, 930, 130
    ymid = 640
    pts = [(R0, ymid), (R0, B0 - RAD)]

    def arc(cx, cy, a0, a1, n=24):
        for i in range(1, n + 1):
            a = math.radians(a0 + (a1 - a0) * i / n)
            pts.append((cx + RAD * math.cos(a), cy + RAD * math.sin(a)))
    arc(R0 - RAD, B0 - RAD, 0, 90); pts.append((L0 + RAD, B0))
    arc(L0 + RAD, B0 - RAD, 90, 180); pts.append((L0, T0 + RAD))
    arc(L0 + RAD, T0 + RAD, 180, 270); pts.append((R0 - RAD, T0))
    arc(R0 - RAD, T0 + RAD, 270, 360); pts.append((R0, ymid))
    seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    tot = sum(seg)

    def at(s):
        s = (s % 1.0) * tot
        for i, L_ in enumerate(seg):
            if s <= L_ or i == len(seg) - 1:
                t = s / L_ if L_ else 0
                return (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t)
            s -= L_
    yam = ("東京 有楽町 新橋 浜松町 田町 高輪ゲートウェイ 品川 大崎 五反田 目黒 恵比寿 渋谷 原宿 代々木 新宿 新大久保 "
           "高田馬場 目白 池袋 大塚 巣鴨 駒込 田端 西日暮里 日暮里 鶯谷 上野 御徒町 秋葉原 神田").split()
    anchors = {0: 0.0, 6: 0.14, 11: 0.40, 14: 0.50, 18: 0.61, 22: 0.795, 26: 0.905, 29: 0.965, 30: 1.0}
    ks = sorted(anchors)
    S = {}
    for a, b in zip(ks[:-1], ks[1:]):
        for i in range(a, b):
            S[yam[i]] = at(anchors[a] + (anchors[b] - anchors[a]) * (i - a) / (b - a))
    P = dict(S)
    P.update({
        "中野": (570, 630), "吉祥寺": (450, 630), "三鷹": (370, 630), "国分寺": (290, 630), "立川": (210, 630),
        "八王子": (130, 690), "高尾": (70, 750), "四ツ谷": (990, 600), "御茶ノ水": (1270, 545),
        "馬喰町": (1650, 560), "錦糸町": (1810, 470), "船橋": (2080, 470), "千葉": (2330, 540),
        "王子": (1320, 276), "赤羽": (1240, 238), "浦和": (1240, 200), "大宮": (1240, 162), "武蔵浦和": (1120, 214),
        "宇都宮": (1470, 162), "高崎": (1000, 162),
        "北千住": (1650, 262), "松戸": (1830, 232), "柏": (2010, 207), "取手": (2190, 182),
        "八丁堀": (1700, 690), "新木場": (1810, 800), "舞浜": (1970, 840), "海浜幕張": (2180, 800), "蘇我": (2380, 740),
        "蒲田": (1560, 1005), "川崎": (1530, 1065), "横浜": (1400, 1130), "戸塚": (1300, 1180), "大船": (1210, 1225),
        "藤沢": (1030, 1255), "平塚": (830, 1270), "小田原": (600, 1285), "熱海": (360, 1305),
        "鎌倉": (1300, 1300), "横須賀": (1490, 1340), "新横浜": (1250, 1070),
    })

    def offset(path, o):
        out = []
        for i, p in enumerate(path):
            a = path[max(0, i - 1)]; b = path[min(len(path) - 1, i + 1)]
            dx, dy = b[0] - a[0], b[1] - a[1]
            n = math.hypot(dx, dy) or 1
            out.append((p[0] - dy / n * o, p[1] + dx / n * o))
        return out
    stops = {n: [p] for n, p in S.items()}      # station -> points of every line through it (for the pills)

    def line(items, col, w=10, o=0):
        names = [it if isinstance(it, str) else None for it in items]
        raw = [P[it] if isinstance(it, str) else (P[it[1]] if it[0] == "p" else it) for it in items]
        path = offset(raw, o)
        d.line(path, fill=col, width=w, joint="curve")
        for n, p in zip(names, path):
            if n:
                stops.setdefault(n, []).append(p)
    # Shinkansen (drawn first, underneath)
    def shink(path):
        d.line(path, fill=(90, 90, 96), width=9, joint="curve")
        d.line(path, fill=WHITE, width=3, joint="curve")
    shink([P["東京"], (1548, 650), (1548, 900), (1470, 965), (1330, 1035), P["新横浜"], (800, 1160), (90, 1195)])
    shink([P["東京"], (1548, 630), (1548, 420), (1440, 300), (1345, 205), (1300, 120)])
    text(d, (96, 1172), "東海道新幹線 → 名古屋・新大阪", JP_B, 20, (70, 70, 76), anchor="lb")
    text(d, (1318, 122), "東北・上越・北陸新幹線", JP_B, 20, (70, 70, 76), anchor="lt")
    # loop
    dense = [at(i / 600) for i in range(601)]
    d.line(dense, fill=LINE["JY"][2], width=14, joint="curve")
    # lines (offsets chosen so parallel lines stay in a fixed order: inside the loop on the east side)
    line(["高尾", "八王子", "立川", "国分寺", "三鷹", "吉祥寺", "中野", "新宿", "四ツ谷", "御茶ノ水", "神田", "東京"], LINE["JC"][2], 10, -6)
    line(["三鷹", "吉祥寺", "中野", "新宿", "四ツ谷", "御茶ノ水", "秋葉原", "錦糸町", "船橋", "千葉"], LINE["JB"][2], 9, 6)
    line(["大宮", "浦和", "赤羽", "王子", "田端", "西日暮里", "日暮里", "鶯谷", "上野", "御徒町", "秋葉原", "神田", "東京",
          "有楽町", "新橋", "浜松町", "田町", "高輪ゲートウェイ", "品川", "蒲田", "川崎", "横浜", "大船"], LINE["JK"][2], 9, 12)
    line(["熱海", "小田原", "平塚", "藤沢", "大船", "戸塚", "横浜", "川崎", "品川", ("p", "田町"), ("p", "浜松町"), "新橋",
          ("p", "有楽町"), "東京", ("p", "神田"), ("p", "秋葉原"), ("p", "御徒町"), "上野", ("p", "鶯谷"), ("p", "日暮里"),
          ("p", "西日暮里"), ("p", "田端"), ("p", "王子"), "赤羽", "浦和", "大宮"], LINE["JT"][2], 9, -24)
    line(["高崎", "大宮", "宇都宮"], LINE["JU"][2], 9, 0)
    line(["上野", "日暮里", "北千住", "松戸", "柏", "取手"], LINE["JJ"][2], 9, 10)
    line(["千葉", "船橋", "錦糸町", "馬喰町", "東京"], LINE["JO"][2], 9, 8)
    line(["東京", "新橋", ("p", "浜松町"), ("p", "田町"), "品川", "横浜", "大船", "鎌倉", "横須賀"], LINE["JO"][2], 9, 36)
    line(["東京", "八丁堀", "新木場", "舞浜", "海浜幕張", "蘇我"], LINE["JE"][2], 9, 0)
    line(["大崎", ("p", "五反田"), ("p", "目黒"), "恵比寿", "渋谷", ("p", "原宿"), ("p", "代々木"), "新宿", ("p", "新大久保"),
          ("p", "高田馬場"), ("p", "目白"), "池袋", (930, 262), "赤羽", "武蔵浦和", "大宮"], LINE["JA"][2], 9, 14)
    big = {"東京", "上野", "池袋", "新宿", "渋谷", "品川", "大宮", "横浜", "千葉", "立川", "八王子"}
    # station pills spanning every line through the station
    PC = {}
    for n, ps in stops.items():
        r = 12 if n in big else 8
        a, b = max(((p, q) for p in ps for q in ps), key=lambda pq: math.dist(*pq))
        PC[n] = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        d.line([a, b], fill=INK, width=2 * r + 6)
        for p in (a, b):
            d.ellipse([p[0] - r - 3, p[1] - r - 3, p[0] + r + 3, p[1] + r + 3], fill=INK)
        d.line([a, b], fill=WHITE, width=2 * r)
        for p in (a, b):
            d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=WHITE)
    # labels
    cx, cy = (L0 + R0) / 2, (T0 + B0) / 2
    LBL = {"東京": (-58, -26, "rb"), "神田": (34, 0, "lm"), "秋葉原": (34, 0, "lm"), "御徒町": (34, 0, "lm"),
           "上野": (64, 4, "lm"), "鶯谷": (30, -10, "lm"), "日暮里": (8, -26, "mb"), "西日暮里": (-14, -26, "mb"),
           "田端": (-30, -26, "mb"), "有楽町": (72, 0, "lm"), "新橋": (72, 0, "lm"), "浜松町": (72, 0, "lm"),
           "田町": (80, 0, "lm"), "高輪ゲートウェイ": (84, 4, "lm"), "品川": (-36, 30, "rt"),
           "中野": (0, 22, "mt"), "吉祥寺": (0, 22, "mt"), "三鷹": (0, 22, "mt"), "国分寺": (0, 22, "mt"),
           "立川": (0, -22, "mb"), "八王子": (18, -10, "lb"), "高尾": (18, 8, "lt"), "四ツ谷": (0, -22, "mb"),
           "御茶ノ水": (0, -24, "mb"), "馬喰町": (0, 24, "mt"), "錦糸町": (0, -22, "mb"), "船橋": (0, -22, "mb"),
           "千葉": (24, 0, "lm"), "大宮": (-40, -24, "rb"), "浦和": (22, 0, "lm"), "赤羽": (24, 4, "lm"),
           "王子": (20, -14, "lb"), "武蔵浦和": (-20, 0, "rm"), "宇都宮": (18, 0, "lm"), "高崎": (-18, 0, "rm"),
           "北千住": (0, -22, "mb"), "松戸": (0, -22, "mb"), "柏": (0, -22, "mb"), "取手": (20, 0, "lm"),
           "八丁堀": (0, -22, "mb"), "新木場": (0, 22, "mt"), "舞浜": (0, 22, "mt"), "海浜幕張": (0, -22, "mb"),
           "蘇我": (22, 0, "lm"), "蒲田": (22, 0, "lm"), "川崎": (22, 4, "lm"), "横浜": (24, -4, "lm"),
           "戸塚": (-18, -8, "rb"), "大船": (-20, 6, "rt"), "藤沢": (0, -22, "mb"), "平塚": (0, -22, "mb"),
           "小田原": (0, -22, "mb"), "熱海": (0, -22, "mb"), "鎌倉": (-20, 0, "rm"), "横須賀": (22, 0, "lm"),
           "新横浜": (-18, -8, "rb"), "大崎": (0, 36, "mt"), "渋谷": (-30, 26, "rt"), "池袋": (-26, -24, "rb"),
           "新宿": (-34, -18, "rb")}
    for n, p0 in P.items():
        size = 32 if n in big else 22
        p = PC.get(n, p0)
        if n in LBL:
            dx, dy, anc = LBL[n]
            q = (p[0] + dx, p[1] + dy)
        elif n in S:
            vx, vy = p0[0] - cx, p0[1] - cy
            if abs(vx) / (R0 - L0) > abs(vy) / (B0 - T0):
                q, anc = (p[0] + (30 if vx > 0 else -30), p[1]), ("lm" if vx > 0 else "rm")
            else:
                q, anc = (p[0], p[1] + (30 if vy > 0 else -30)), ("mt" if vy > 0 else "mb")
        else:
            q, anc = (p[0] + 16, p[1] - 14), "lb"
        text(d, q, n, JP_B, size, INK, anchor=anc)
    # 現在地 (you are here)
    tp = P["東京"]
    d.ellipse([tp[0] - 26, tp[1] - 26, tp[0] + 26, tp[1] + 26], outline=(226, 0, 26), width=7)
    bx0, by0 = tp[0] - 330, tp[1] + 40
    d.line([(tp[0] - 20, tp[1] + 18), (bx0 + 200, by0 + 6)], fill=(226, 0, 26), width=6)
    d.rounded_rectangle([bx0, by0, bx0 + 230, by0 + 58], radius=10, fill=(226, 0, 26))
    text(d, (bx0 + 115, by0 + 30), "現在地 東京", JP_B, 30, WHITE, anchor="mm")
    text(d, (bx0 + 115, by0 + 80), "You are here: Tokyo", EN_B, 20, (226, 0, 26), anchor="mm")
    # legend
    lx, ly = 1900, 905
    items = ["JY", "JC", "JB", "JK", "JT", "JU", "JJ", "JO", "JE", "JA"]
    d.rounded_rectangle([lx - 24, ly - 24, W - 24, H - 20], radius=14, fill=WHITE, outline=(200, 200, 200), width=3)
    for i, c in enumerate(items):
        x = lx + (i // 5) * 345
        y = ly + (i % 5) * 64
        d.rounded_rectangle([x, y, x + 52, y + 52], radius=8, fill=LINE[c][2])
        text(d, (x + 26, y + 27), c, EN_B, 24, INK if sum(LINE[c][2]) > 520 else WHITE, anchor="mm")
        text(d, (x + 64, y + 16), LINE[c][0], JP_B, 23, INK, max_w=265)
        text(d, (x + 65, y + 42), LINE[c][1], EN_R, 15, (80, 80, 80), max_w=265)
    yy = ly + 5 * 64 + 22
    d.line([(lx, yy), (lx + 52, yy)], fill=(90, 90, 96), width=9)
    d.line([(lx, yy), (lx + 52, yy)], fill=WHITE, width=3)
    text(d, (lx + 64, yy), "新幹線 Shinkansen", JP_B, 22, INK)


# ----------------------------------------------------------- small items
SEAT = {"自由席": ("Non-reserved", (0, 85, 165)), "指定席": ("Reserved", (214, 64, 0)),
        "グリーン車": ("Green Car", (0, 150, 64)), "グランクラス": ("GranClass", (120, 100, 40))}


def car_sign(group, n, seat):
    key = f"car_{group}_{n:02d}"
    im, d, W, H = new(key, 1.2, 0.4, 400)
    text(d, (150, 70), str(n), EN_B, 108, WHITE, anchor="rm")
    text(d, (160, 86), "号車", JP_B, 44, WHITE, anchor="lm")
    text(d, (30, 138), f"Car {n}", EN_R, 26, (220, 220, 220))
    en, col = SEAT[seat]
    d.rectangle([W - 200, 0, W, H], fill=col)
    text(d, (W - 100, 66), seat, JP_B, 40, WHITE, anchor="mm", max_w=184)
    text(d, (W - 100, 116), en, EN_B, 22, WHITE, anchor="mm", max_w=184)
    META[key].update({"group": group, "car": n, "seat": seat})


def clock_face():
    im, d, W, H = new("clock", 0.5, 0.5, 1024, bg=(255, 255, 255))
    c = W / 2
    d.ellipse([4, 4, W - 4, H - 4], fill=(252, 252, 250), outline=(30, 30, 30), width=14)
    for i in range(60):
        a = math.radians(i * 6)
        r0 = c - 34 - (40 if i % 5 == 0 else 14)
        r1 = c - 34
        w = 14 if i % 5 == 0 else 5
        d.line([(c + r0 * math.sin(a), c - r0 * math.cos(a)), (c + r1 * math.sin(a), c - r1 * math.cos(a))], fill=(20, 20, 20), width=w)
    for i in range(1, 13):
        a = math.radians(i * 30)
        r = c - 120
        text(d, (c + r * math.sin(a), c - r * math.cos(a)), str(i), EN_B, 50, (20, 20, 20), anchor="mm")
    def hand(deg, length, width, col):
        a = math.radians(deg)
        d.line([(c - 0.15 * length * math.sin(a), c + 0.15 * length * math.cos(a)), (c + length * math.sin(a), c - length * math.cos(a))], fill=col, width=width)
    hand(10 * 30 + 8 * 0.5, c * 0.48, 22, (20, 20, 20))     # 10:08
    hand(8 * 6, c * 0.74, 14, (20, 20, 20))
    hand(200, c * 0.78, 5, (210, 30, 30))
    d.ellipse([c - 16, c - 16, c + 16, c + 16], fill=(20, 20, 20))
    text(d, (c, c + 78), "JR", EN_B, 30, (0, 136, 3), anchor="mm")


def estop_label():
    im, d, W, H = new("estop", 0.16, 0.24, 1600, bg=(205, 20, 20))
    text(d, (W / 2, 36), "非常停止", JP_B, 46, WHITE, anchor="mm")
    text(d, (W / 2, 80), "ボタン", JP_B, 38, WHITE, anchor="mm")
    d.ellipse([W / 2 - 70, 120, W / 2 + 70, 260], fill=(240, 200, 0), outline=(60, 60, 60), width=6)
    d.ellipse([W / 2 - 44, 146, W / 2 + 44, 234], fill=(255, 225, 40))
    text(d, (W / 2, 300), "EMERGENCY", EN_B, 30, WHITE, anchor="mm")
    text(d, (W / 2, 336), "STOP", EN_B, 34, WHITE, anchor="mm")


# ------------------------------------------------------------------ build all
for isl in ISLANDS:
    for v in ("N", "S"):
        direction_board(isl, v)
for g in ("conv", "tokaido", "tohoku"):
    for p in ("N", "C", "S"):
        exit_sign(g, p, "down")
for k in STOPS:
    stop_board(k)
route_map()
for n in range(1, 17):
    car_sign("tokaido", n, "自由席" if n <= 3 else "グリーン車" if 8 <= n <= 10 else "指定席")
for n in range(1, 11):
    car_sign("tohoku", n, "グランクラス" if n == 10 else "グリーン車" if n == 9 else "指定席")
clock_face()
estop_label()

# ------------------------------------------------------------- atlas packing
PAGE = 4096
GAP = 6
order = sorted(ITEMS, key=lambda k: (-ITEMS[k].size[1], -ITEMS[k].size[0], k))
pages, shelves = [], []          # shelves: [page, y, h, x]
manifest = {"page_size": PAGE, "pages": [], "items": {}}
for k in order:
    w, h = ITEMS[k].size
    placed = False
    for sh in shelves:
        if h <= sh[2] and sh[3] + w + GAP <= PAGE:
            pg, y = sh[0], sh[1]
            x = sh[3]
            sh[3] += w + GAP
            placed = True
            break
    if not placed:
        pg = len(pages) - 1
        y = (shelves[-1][1] + shelves[-1][2] + GAP) if shelves and shelves[-1][0] == pg else 0
        if pg < 0 or y + h > PAGE:
            pages.append(Image.new("RGB", (PAGE, PAGE), (40, 40, 40)))
            pg, y = len(pages) - 1, 0
        shelves.append([pg, y, h, w + GAP])
        x = 0
    pages[pg].paste(ITEMS[k], (x, y))
    u0, u1 = x / PAGE, (x + w) / PAGE
    v1, v0 = 1 - y / PAGE, 1 - (y + h) / PAGE
    manifest["items"][k] = dict(META[k], page=pg, uv=[u0, v0, u1, v1], px=[x, y, w, h])
for i, im in enumerate(pages):
    fn = f"v6_sign_atlas_{i}.png"
    im.save(os.path.join(OUT, fn), optimize=True)
    manifest["pages"].append(fn)
    # half-size previews of the individual items are not written; the atlas itself is the deliverable
manifest["tracks"] = {str(t): {"code": v[0], "dir_jp": v[1], "dir_en": v[2], "departs_minus_x": v[3],
                               "line_jp": LINE[v[0]][0], "stops": TRACK_STOPS[t]} for t, v in TRACK.items()}
json.dump(manifest, open(os.path.join(OUT, "v6_sign_atlas.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("items", len(ITEMS), "pages", len(pages))
