"""V6 module 0: platform stairs, escalators and signage (round-6 feedback "站台细节还可以添加吗" /
"参考站台的照片添加细节像是线路图和方向").

Real Tokyo-station platforms are reached by stairs and escalators from the passages below; V5 had neither, and its only
signs were the station-name boards and departure indicators.  This module adds, on all 10 island platforms:

  * three stairwells per island (towards the North / Central / South passages): an opening in the platform deck,
    a 24-riser stair (rise 0.167 m, tread 0.30 m) and a 30-degree escalator side by side down to a landing 4.0 m
    below the platform, tunnel walls, lit ceiling, end wall; enclosure walls, cap rails and tactile warning strips
    at platform level.  The deck, the viaduct infill and anything else in the way are cut (boolean / island removal)
    on copies; the originals are retired into V6_Replaced_V5_hidden.
  * signs drawn from a texture atlas made by make6_sign_textures.py (JR East style):
      - over every stair entrance: 出口・通路・のりかえ sign (black passage panel, yellow exit panel, transfer badges);
        its back carries the 番線案内 board for that viewing direction
      - free-hanging double-sided 番線案内 boards (platform number tile in the line colour, line name, 方面)
      - JR-lines route map (路線図) on the end wall of every stair enclosure
      - 停車駅のご案内 stop-pattern board of the adjacent line on both enclosure side walls
      - Shinkansen platforms: 号車 car-number boards over both platform edges at every car of the stopping train
      - platform clocks, emergency-stop buttons (非常停止ボタン) on the canopy / roof columns
  * the escalator itself is the CC BY 4.0 model "Escalator KONE TravelMaster 110" by Sergey Burov (Sketchfab, see
    ESC_CREDIT and sources_and_licenses), stored in assets/, merged into one mesh and placed by collection instancing;
    without the asset file a simple procedural escalator is built instead
  * people standing in the new openings are moved; a few people are put on the stairs and escalators
  * the plan footprints of everything new are written to scene["V6_platform_keepouts"] so that mod6_catenary.py
    keeps its masts out of the stairwells and away from the hanging signs

usage: blender -b in.blend --python-exit-code 1 -P mod6_platforms.py -- out.blend [report.json] [islands=03-04,...]
"""
import sys, os, json, math, re, random
import numpy as np
import bpy
import bmesh
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v5lib as L

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGV[0] if ARGV else None
REPORT = ARGV[1] if len(ARGV) > 1 and not ARGV[1].startswith("islands=") else None
ONLY = None
for a in ARGV:
    if a.startswith("islands="):
        ONLY = set(a.split("=", 1)[1].split(","))

TEX = os.path.join(HERE, "textures")
ATLAS = json.load(open(os.path.join(TEX, "v6_sign_atlas.json"), encoding="utf-8"))
PLAT = json.load(open(os.path.join(HERE, "platforms.json")))
COLS = json.load(open(os.path.join(HERE, "platforms_cols.json")))["columns"]

# ---- stairwell geometry, local frame: u along the descent, v to the left of u, w up from the deck top
W_IN = 3.60                 # clear width of the well (stair 2.05 + divider 0.10 + escalator 1.45)
WALL = 0.12
DEPTH = 4.00                # landing below the deck top (= rise of the escalator model: 1 m top+bottom modules + 3 x 1 m)
N_RISE = 24
RISE = DEPTH / N_RISE       # 0.165
TREAD = 0.30
U_STAIR0 = 0.30             # first nosing
U_STAIR1 = U_STAIR0 + (N_RISE - 1) * TREAD     # 6.0, foot of the stair
L_HOLE = 7.40               # opening in the deck; beyond it the stair/escalator run under the slab (headroom >= 2.1 m)
L_TUN = 13.40               # length of the well below the slab (end wall)
SLAB = 0.75                 # underside of the platform slab below the deck top
V_STAIR = (-1.80, 0.25)
V_DIV = (0.25, 0.35)
V_ESC = (0.35, 1.80)
ESC_U0, ESC_SLOPE = 2.24, math.tan(math.radians(30.0))   # start of the 30-degree run (from the escalator model)
ESC_U1 = ESC_U0 + DEPTH / ESC_SLOPE            # 9.17
ESC_END = 11.83                                # bottom comb-plate edge
ESC_UX = 4.871                                 # model x -> u = ESC_UX - x (top access plate edge at u = -0.2)
ESC_ASSET = os.path.join(HERE, "assets", "escalator_kone_tm110.blend")
ESC_CREDIT = ('"Escalator / Эскалатор KONE TravelMaster 110" by Sergey Burov (@s-burov), '
              'https://sketchfab.com/3d-models/escalator-kone-travelmaster-110-d1e9d7e1b80d42dc9872d5ba6d8e2307 , '
              'licensed CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). Changes: materials replaced, parts merged '
              'into one mesh, used as a 4 m-rise escalator by collection instancing.')
ESC_MATS = {"tm_110_main_metal": "steel", "tm110_black_plastic": "rubber", "tm110_glass": "glass",
            "tm110_steps_metal": "esc_step", "tm100_steps_yellow": "esc_yellow"}
KEEP_U = (-1.60, L_HOLE + WALL + 2.20)         # platform-level keep-out along u (route-map viewing space beyond the end wall)
KEEP_U_SHIN = (-2.20, L_HOLE + WALL + 0.25)    # Shinkansen islands: roof columns every 12 m; keep the entrance clear
HALF_OUT = W_IN / 2 + WALL                     # outer half width of the enclosure
TARGETS = {"N": -95.0, "C": -5.0, "S": 90.0}
GROUP = {"01-02": "conv", "03-04": "conv", "05-06": "conv", "07-08": "conv", "09-10": "conv",
         "14-15": "tokaido", "16-17": "tokaido", "18-19": "tokaido", "20-21": "tohoku", "22-23": "tohoku"}
REPORTD = {"islands": {}, "cuts": {}, "warnings": []}


def esc_line(u):
    if u <= ESC_U0:
        return 0.0
    if u >= ESC_U1:
        return -DEPTH
    return -(u - ESC_U0) * ESC_SLOPE


def stair_line(u):
    """pitch line through the nosings"""
    if u <= U_STAIR0:
        return 0.0
    if u >= U_STAIR1:
        return -DEPTH
    return -(u - U_STAIR0) / TREAD * RISE


# ----------------------------------------------------------------------------------------- scene helpers
def world_verts(o):
    n = len(o.data.vertices)
    co = np.empty(n * 3); o.data.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    mw = np.array(o.matrix_world)
    return co @ mw[:3, :3].T + mw[:3, 3]


def mesh_islands(me):
    n = len(me.vertices); lab = np.arange(n)
    ev = np.empty(len(me.edges) * 2, int); me.edges.foreach_get("vertices", ev); ev = ev.reshape(-1, 2)
    for _ in range(1000):
        if len(ev) == 0:
            break
        m = np.minimum(lab[ev[:, 0]], lab[ev[:, 1]])
        old = lab.copy(); np.minimum.at(lab, ev[:, 0], m); np.minimum.at(lab, ev[:, 1], m); lab = lab[lab]
        if np.array_equal(old, lab):
            break
    return lab


def island_boxes(o):
    V = world_verts(o)
    lab = mesh_islands(o.data)
    u, inv = np.unique(lab, return_inverse=True)
    mn = np.full((len(u), 3), 1e9); mx = np.full((len(u), 3), -1e9)
    for k in range(3):
        np.minimum.at(mn[:, k], inv, V[:, k]); np.maximum.at(mx[:, k], inv, V[:, k])
    return np.hstack([mn, mx])          # x0 y0 z0 x1 y1 z1


def retire(o):
    hc = L.collection("V6_Replaced_V5_hidden", hide_render=True)
    hc.hide_viewport = True
    for c in list(o.users_collection):
        c.objects.unlink(o)
    hc.objects.link(o)
    o.hide_render = True; o.hide_viewport = True
    o["V6_retired"] = True


def replace_copy(o, tag):
    """Copy o (with its own mesh), give the copy the original name, retire the original."""
    cols = list(o.users_collection)
    name = o.name
    new = o.copy(); new.data = o.data.copy()
    o.name = f"{name} [V5, before V6 {tag}]"
    new.name = name
    for c in cols:
        c.objects.link(new)
    retire(o)
    return new


def ray(origin, d, dist):
    dg = bpy.context.evaluated_depsgraph_get()
    hit, loc, nor, idx, ob, mw = bpy.context.scene.ray_cast(dg, Vector(origin), Vector(d), distance=dist)
    return (loc, ob) if hit else (None, None)


# ----------------------------------------------------------------------------------------- islands
class Island:
    def __init__(self, deck, d):
        m = re.search(r"Platform (\d\d)-(\d\d)", deck)
        self.tw, self.te = int(m.group(1)), int(m.group(2))
        self.name = f"{self.tw:02d}-{self.te:02d}"
        self.deck = deck
        self.z = d["ztop"]
        sl = sorted(d["slices"])
        self.sx = np.array([s[0] for s in sl], float)
        self.sc = np.array([(s[1] + s[2]) / 2 for s in sl], float)
        self.sw = np.array([s[2] - s[1] for s in sl], float)
        self.group = GROUP[self.name]
        self.shin = self.group != "conv"

    def yc(self, x):
        return float(np.interp(x, self.sx, self.sc))

    def w(self, x):
        if x < self.sx[0] or x > self.sx[-1]:
            return 0.0
        return float(np.interp(x, self.sx, self.sw))

    def tangent(self, x, h=4.0):
        t = Vector((2 * h, self.yc(x + h) - self.yc(x - h), 0.0))
        return t.normalized()


class Frame:
    """u along the descent, v = z x u (left), w up; origin on the island centre line at the entrance, deck top."""

    def __init__(self, isl, xa, s):
        self.isl, self.xa, self.s = isl, xa, s
        xb = xa + s * 8.0
        self.O = Vector((xa, isl.yc(xa), isl.z))
        d = Vector((xb - xa, isl.yc(xb) - isl.yc(xa), 0.0)).normalized()
        self.u = d
        self.v = Vector((-d.y, d.x, 0.0))
        self.zv = Vector((0, 0, 1))
        self.M = Matrix(((d.x, self.v.x, 0, self.O.x), (d.y, self.v.y, 0, self.O.y), (0, 0, 1, self.O.z), (0, 0, 0, 1)))

    def P(self, u, v, w=0.0):
        return self.O + self.u * u + self.v * v + self.zv * w

    def local(self, x, y):
        p = Vector((x, y, 0)) - Vector((self.O.x, self.O.y, 0))
        return p.dot(self.u), p.dot(self.v)

    def box(self, mb, u0, u1, v0, v1, w0, w1, mat):
        L.box(mb, 0, 0, 0, u1 - u0, v1 - v0, w1 - w0, mat,
              frame=self.M @ Matrix.Translation(((u0 + u1) / 2, (v0 + v1) / 2, (w0 + w1) / 2)))

    def prism_uw(self, mb, pts, v0, v1, mat):
        """polygon in the (u, w) plane extruded across v0..v1"""
        n = len(pts)
        verts = [tuple(self.P(u, v0, w)) for u, w in pts] + [tuple(self.P(u, v1, w)) for u, w in pts]
        faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
        faces += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
        mb.add(verts, faces, mat)


# ----------------------------------------------------------------------------------------- materials
def image_mat(name, page, strength):
    m = bpy.data.materials.get(name)
    if m:
        return m
    fn = os.path.join(TEX, ATLAS["pages"][page])
    img = bpy.data.images.get(os.path.basename(fn)) or bpy.data.images.load(fn)
    img.pack()
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = img; t.interpolation = 'Linear'
    uv = nt.nodes.new("ShaderNodeUVMap"); uv.uv_map = "V5 metre UV"
    nt.links.new(uv.outputs[0], t.inputs[0])
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(t.outputs["Color"], b.inputs["Emission Color"])
    b.inputs["Emission Strength"].default_value = strength
    b.inputs["Roughness"].default_value = 0.35
    m.diffuse_color = (0.5, 0.5, 0.5, 1)
    return m


def materials():
    granite = bpy.data.materials.get("V2 | white grey granite paving") or L.principled("V6 | platform granite", (0.55, 0.55, 0.53), rough=0.6)
    glass = bpy.data.materials.get("V6 | escalator balustrade glass")
    if glass is None:
        glass = L.principled("V6 | escalator balustrade glass", (0.80, 0.86, 0.86), rough=0.03)
        b = glass.node_tree.nodes.get("Principled BSDF")
        b.inputs["Transmission Weight"].default_value = 1.0
        b.inputs["IOR"].default_value = 1.5
        glass.diffuse_color = (0.6, 0.7, 0.72, 0.3)
    I = {
        "panel": L.principled("V6 | stair enclosure panel light grey", (0.58, 0.59, 0.58), rough=0.45),
        "tile": L.principled("V6 | stairwell wall tiles", (0.70, 0.70, 0.67), rough=0.30),
        "ceiling": L.principled("V6 | stairwell ceiling panel", (0.75, 0.75, 0.74), rough=0.6),
        "light": L.principled("V6 | stairwell light strip", (0.9, 0.9, 0.9), emission=(1.0, 0.97, 0.92), strength=12.0),
        "floor": granite,
        "tread": L.principled("V6 | stair tread terrazzo", (0.42, 0.42, 0.40), rough=0.55),
        "nosing": L.principled("V6 | stair nosing non-slip", (0.06, 0.06, 0.06), rough=0.8),
        "steel": L.principled("V6 | stainless steel", (0.62, 0.62, 0.62), rough=0.22, metal=1.0),
        "tactile": L.principled("V6 | tactile paving yellow", (0.78, 0.56, 0.02), rough=0.6),
        "esc_step": L.principled("V6 | escalator step aluminium", (0.16, 0.16, 0.17), rough=0.35, metal=0.85),
        "esc_yellow": L.principled("V6 | escalator step demarcation yellow", (0.85, 0.62, 0.02), rough=0.5),
        "rubber": L.principled("V6 | escalator handrail rubber", (0.02, 0.02, 0.02), rough=0.35),
        "glass": glass,
        "frame": L.principled("V5 | platform fittings dark grey", (0.07, 0.075, 0.08), rough=0.45, metal=0.5),
        "estop": L.principled("V6 | emergency stop box red", (0.55, 0.03, 0.02), rough=0.4),
        "sign0": image_mat("V6 | sign atlas page 0 (backlit)", 0, 1.6),
        "board0": image_mat("V6 | sign atlas page 0 (panel)", 0, 0.45),
    }
    if len(ATLAS["pages"]) > 1:
        I["sign1"] = image_mat("V6 | sign atlas page 1 (backlit)", 1, 1.6)
        I["board1"] = image_mat("V6 | sign atlas page 1 (panel)", 1, 0.45)
    mats = list(dict.fromkeys(I.values()))
    return mats, {k: mats.index(v) for k, v in I.items()}


# ----------------------------------------------------------------------------------------- sign primitives
def quad(mb, C, R, U, w, h, key, mat):
    u0, v0, u1, v1 = ATLAS["items"][key]["uv"]
    cs = [C - R * (w / 2) - U * (h / 2), C + R * (w / 2) - U * (h / 2), C + R * (w / 2) + U * (h / 2), C - R * (w / 2) + U * (h / 2)]
    mb.add([tuple(c) for c in cs], [(0, 1, 2, 3)], mat, uvs=[[(u0, v0), (u1, v0), (u1, v1), (u0, v1)]])


def mat_for(key, I, kind="sign"):
    return I[f"{kind}{ATLAS['items'][key]['page']}"]


def board(mb, C, f, w, h, key_front, key_back, I, kind="sign", thick=0.08):
    """Double-sided board centred at C; key_front is seen by a viewer looking along f (horizontal unit vector)."""
    f = Vector((f.x, f.y, 0)).normalized()
    R = f.cross(Vector((0, 0, 1)))
    U = Vector((0, 0, 1))
    N = -f
    M = Matrix(((R.x, N.x, U.x, C.x), (R.y, N.y, U.y, C.y), (R.z, N.z, U.z, C.z), (0, 0, 0, 1)))
    L.box(mb, 0, 0, 0, w + 0.06, thick, h + 0.06, I["frame"], frame=M)
    quad(mb, C + N * (thick / 2 + 0.002), R, U, w, h, key_front, mat_for(key_front, I, kind))
    if key_back:
        quad(mb, C - N * (thick / 2 + 0.002), -R, U, w, h, key_back, mat_for(key_back, I, kind))
    return R, N


class Hanger:
    """Fixing points above a sign: platform canopy (ray) or the V5 Shinkansen roof structure."""

    def __init__(self):
        self.SR = None
        if bpy.context.scene.get("V5_shinkansen_roofs"):
            import mod_shinkansen_roofs as SR
            self.SR = SR

    def top(self, isl, p):
        if isl.shin and self.SR is not None:
            x2, y2, z2 = self.SR.hang_point(isl.name, p.x, p.y, isl.z)
            if z2 is None or z2 < p.z + 0.1:
                return None
            return Vector((x2, y2, z2))
        z = p.z + 0.01
        for _ in range(6):
            loc, ob = ray((p.x, p.y, z), (0, 0, 1), 6.5 - (z - p.z))
            if loc is None:
                return None
            if ob.instance_type == 'COLLECTION' or re.match(r"V5 (person|pedestrian)", ob.name):
                z = loc.z + 0.01
                continue
            return Vector((p.x, p.y, loc.z))
        return None

    def rods(self, mb, isl, pts, mat):
        tops = [self.top(isl, p) for p in pts]
        if any(t is None for t in tops):
            return False
        for p, t in zip(pts, tops):
            if math.hypot(t.x - p.x, t.y - p.y) < 0.03:
                L.box(mb, p.x, p.y, (p.z + t.z) / 2, 0.035, 0.035, t.z - p.z, mat)
            else:
                L.tube(mb, [Vector(p), t], 0.018, sides=6, mat=mat, smooth=False)
        return True


# ----------------------------------------------------------------------------------------- obstacles
class Obst:
    def __init__(self, islands):
        self.furn = {}
        for isl in islands:
            o = bpy.data.objects.get(f"V5 platform {isl.name} furniture and signs")
            self.furn[isl.name] = island_boxes(o) if o else np.zeros((0, 6))
        # canopy / roof columns standing on the islands
        self.cols = []
        for bb in COLS:
            xs = [c[0] for c in bb]; ys = [c[1] for c in bb]; zs = [c[2] for c in bb]
            self.cols.append(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, min(zs), max(max(xs) - min(xs), max(ys) - min(ys)) / 2))
        roofs = json.loads(bpy.context.scene.get("V5_shinkansen_roofs", "{}"))
        self.roof_isl = set()
        for k, r in roofs.items():
            if isinstance(r, dict) and "columns" in r:
                self.roof_isl.add(k)
                for c in r["columns"]:
                    self.cols.append((c[0], c[1], r.get("z_deck", 6.5), 0.42))
        self.cols = np.array(self.cols)
        po = bpy.data.objects.get("V4_Structure_Piers_caps_foundations")
        self.piers = island_boxes(po) if po else np.zeros((0, 6))

    def columns_near(self, isl):
        c = self.cols
        if isl.name in self.roof_isl:          # V3 columns of the Shinkansen islands are retired (V5 roofs)
            pass
        sel = []
        for row in c:
            x, y, z, r = row
            if abs(z - isl.z) > 0.6:
                continue
            if isl.w(x) <= 0 or abs(y - isl.yc(x)) > isl.w(x) / 2 + 0.3:
                continue
            if isl.shin and r < 0.3:
                continue
            sel.append(row)
        return np.array(sel) if sel else np.zeros((0, 4))


def rect_hits(F, boxes, u0, u1, hv, pad=0.0):
    """axis-aligned boxes (x0 y0 z0 x1 y1 z1) against the frame rectangle u0..u1 x -hv..hv (plan only)."""
    if len(boxes) == 0:
        return np.zeros(0, bool)
    cx = (boxes[:, 0] + boxes[:, 3]) / 2; cy = (boxes[:, 1] + boxes[:, 4]) / 2
    hx = (boxes[:, 3] - boxes[:, 0]) / 2; hy = (boxes[:, 4] - boxes[:, 1]) / 2
    du = (cx - F.O.x) * F.u.x + (cy - F.O.y) * F.u.y
    dv = (cx - F.O.x) * F.v.x + (cy - F.O.y) * F.v.y
    ru = hx * abs(F.u.x) + hy * abs(F.u.y)          # box half-extent projected on u / v
    rv = hx * abs(F.v.x) + hy * abs(F.v.y)
    return (du + ru > u0 - pad) & (du - ru < u1 + pad) & (np.abs(dv) - rv < hv + pad)


# ----------------------------------------------------------------------------------------- opening search
def find_openings(isl, ob, hanger):
    fb = ob.furn[isl.name]
    low = fb[fb[:, 2] < isl.z + 2.40] if len(fb) else fb
    high = fb[fb[:, 2] >= isl.z + 2.40] if len(fb) else fb
    cols = ob.columns_near(isl)
    colbox = np.column_stack([cols[:, 0] - cols[:, 3], cols[:, 1] - cols[:, 3], cols[:, 2],
                              cols[:, 0] + cols[:, 3], cols[:, 1] + cols[:, 3], cols[:, 2] + 4]) if len(cols) else np.zeros((0, 6))
    piers = ob.piers
    if len(piers):
        piers = piers[(piers[:, 5] > isl.z - DEPTH - 1.3) & (piers[:, 2] < isl.z - 0.5)]
    chosen = []
    for pos in ("N", "C", "S"):
        T = TARGETS[pos]
        cands = []
        KU = KEEP_U_SHIN if isl.shin else KEEP_U
        cpad = 0.30 if isl.shin else 0.45
        for xa in np.arange(T - 32.0, T + 32.01, 0.25):
            for s in (1, -1):
                F = Frame(isl, float(xa), s)
                ends = [F.P(KEEP_U[0], 0), F.P(L_TUN + WALL, 0)]
                xmid = (ends[0].x + ends[1].x) / 2
                # inside the platform, wide enough (walkway >= 1.8 m beside the enclosure)
                ok = True
                for uu in np.arange(KU[0], L_HOLE + WALL + 0.31, 0.5):
                    for vv in (-HALF_OUT, HALF_OUT):
                        p = F.P(float(uu), vv)
                        wv = isl.w(p.x)
                        if wv <= 0 or abs(p.y - isl.yc(p.x)) > wv / 2 - 1.8:
                            ok = False; break
                    if not ok:
                        break
                if not ok:
                    continue
                if any(abs(xmid - c[0]) < 24.0 for c in chosen_x(chosen)):
                    continue
                if rect_hits(F, colbox, KU[0], KU[1], HALF_OUT, cpad).any():
                    continue
                if rect_hits(F, low, KU[0], KU[1], HALF_OUT, 0.35).any():
                    continue
                if rect_hits(F, high, -1.2, 0.3, 2.1, 0.2).any():
                    continue
                npier = int(rect_hits(F, piers, -0.2, L_TUN + WALL + 0.2, HALF_OUT + 0.1).sum()) if len(piers) else 0
                cands.append((npier > 0, abs(xmid - T), float(xa), s, npier))
        cands.sort()
        got = None
        for has_pier, score, xa, s, npier in cands[:400]:
            F = Frame(isl, xa, s)
            # the entrance sign needs something to hang from
            pts = [F.P(-0.45, -1.55, 2.88), F.P(-0.45, 1.55, 2.88)]
            if all(hanger.top(isl, p) is not None for p in pts):
                got = (F, pos, npier)
                break
        if got is None:
            REPORTD["warnings"].append(f"{isl.name}: no stairwell position near {pos} (x {T})")
            continue
        chosen.append(got)
    return chosen


def chosen_x(chosen):
    return [((F.P(KEEP_U[0], 0).x + F.P(L_TUN, 0).x) / 2,) for F, _p, _n in chosen]


# ----------------------------------------------------------------------------------------- cutting
def cutter_object(frames):
    prof = [(0.0, 0.40), (L_HOLE, 0.40), (L_HOLE, -SLAB - 0.03), (L_TUN, -SLAB - 0.03), (L_TUN, -DEPTH - 1.22), (0.0, -DEPTH - 1.22)]
    mb = L.MeshBuilder()
    for F in frames:
        F.prism_uw(mb, prof, -W_IN / 2, W_IN / 2, 0)
    ob = mb.build("V6 TEMP stairwell cutter", bpy.context.scene.collection, [])
    ob.hide_render = True
    return ob


def up_area(me):
    return sum(p.area for p in me.polygons if p.normal.z > 0.9)


def cut_scene(frames):
    cutter = cutter_object(frames)
    CV = world_verts(cutter)
    cpolys = [tuple(p.vertices) for p in cutter.data.polygons]
    cbvh = BVHTree.FromPolygons([Vector(v) for v in CV], cpolys)
    lo, hi = CV.min(0) - 0.05, CV.max(0) + 0.05
    foot = len(frames) * L_TUN * W_IN

    def inside(P):
        """points inside any cutter prism (frame-local test)"""
        res = np.zeros(len(P), bool)
        for F in frames:
            du = (P[:, 0] - F.O.x) * F.u.x + (P[:, 1] - F.O.y) * F.u.y
            dv = (P[:, 0] - F.O.x) * F.v.x + (P[:, 1] - F.O.y) * F.v.y
            dw = P[:, 2] - F.O.z
            a = (du > 0.02) & (du < L_TUN - 0.02) & (np.abs(dv) < W_IN / 2 - 0.02) & (dw > -DEPTH - 1.20)
            top = np.where(du < L_HOLE, 0.38, -SLAB - 0.05)
            res |= a & (dw < top)
        return res
    skip = re.compile(r"^V6 |^V5 person|V5 pedestrian")
    island_mode = re.compile(r"risers_and_ribs|Piers_caps|furniture and signs|door_system|sleeper|fastening|"
                             r"marker|tactile|strip light|signal")
    done = {}
    for o in list(bpy.data.objects):
        if o.type != 'MESH' or o.hide_render or not o.visible_get() or skip.search(o.name) or o.get("V6_retired"):
            continue
        if len(o.data.vertices) == 0 or len(o.data.polygons) == 0:
            continue
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        bmin = np.array([min(v[i] for v in bb) for i in range(3)]); bmax = np.array([max(v[i] for v in bb) for i in range(3)])
        if (bmax < lo).any() or (bmin > hi).any():
            continue
        V = world_verts(o)
        ins = inside(V)
        polys = [tuple(p.vertices) for p in o.data.polygons]
        obvh = BVHTree.FromPolygons([Vector(v) for v in V], polys)
        pairs = obvh.overlap(cbvh)
        if not ins.any() and not pairs:
            continue
        lab = mesh_islands(o.data)
        bmc = bmesh.new(); bmc.from_mesh(o.data)
        manifold = all(e.is_manifold for e in bmc.edges); bmc.free()
        if island_mode.search(o.name) or not manifold:
            hit = set(np.unique(lab[ins]).tolist())
            for a, _b in pairs:
                hit.add(int(lab[polys[a][0]]))
            new = replace_copy(o, "stairwells")
            bm = bmesh.new(); bm.from_mesh(new.data); bm.verts.ensure_lookup_table()
            kill = [bm.verts[i] for i in np.where(np.isin(lab, list(hit)))[0]]
            bmesh.ops.delete(bm, geom=kill, context='VERTS')
            bm.to_mesh(new.data); bm.free(); new.data.update()
            done[o.name] = {"mode": "islands removed", "islands": len(hit)}
        else:
            new = replace_copy(o, "stairwells")
            md = new.modifiers.new("V6 stairwell cut", 'BOOLEAN')
            md.operation = 'DIFFERENCE'; md.solver = 'EXACT'; md.object = cutter
            md.use_self = True            # several V4 structure meshes are unions of overlapping closed shells
            dg = bpy.context.evaluated_depsgraph_get()
            me = bpy.data.meshes.new_from_object(new.evaluated_get(dg))
            new.modifiers.remove(md)
            oldme = new.data
            me.name = oldme.name
            new.data = me
            nf0, nf1 = len(oldme.polygons), len(me.polygons)
            a0, a1 = up_area(oldme), up_area(me)
            done[o.name] = {"mode": "boolean", "faces_before": nf0, "faces_after": nf1, "top_area_removed_m2": round(a0 - a1, 1)}
            if a0 - a1 > foot * 1.15 + 1.0:
                REPORTD["warnings"].append(f"boolean on {o.name} removed {a0 - a1:.0f} m2 of top faces (footprint {foot:.0f})")
        L.log("cut", o.name, done[o.name])
    bpy.data.objects.remove(cutter)
    return done


# ----------------------------------------------------------------------------------------- stairwell geometry
def build_stairwell(F, I, mb, me_esc, use_model=False):
    hv = W_IN / 2
    # ---- tunnel (below the deck): side walls, floor, end wall, ceiling under the slab, light strips
    for sgn in (-1, 1):
        v0 = sgn * hv; v1 = sgn * (hv + WALL)
        F.box(mb, 0.0, L_TUN + WALL, min(v0, v1), max(v0, v1), -DEPTH - 0.14, 0.0, I["tile"])
        F.box(mb, 0.40, L_TUN - 0.2, sgn * (hv - 0.012), sgn * (hv - 0.002), -0.32, -0.20, I["light"])
    F.box(mb, 0.0, L_TUN + WALL, -hv - WALL, hv + WALL, -DEPTH - 0.14, -DEPTH, I["floor"])
    F.box(mb, -WALL, 0.0, -hv - WALL, hv + WALL, -DEPTH - 0.14, -0.30, I["tile"])       # closes the space under the top landing
    F.box(mb, L_TUN, L_TUN + WALL, -hv, hv, -DEPTH, -SLAB, I["tile"])
    F.box(mb, L_HOLE, L_TUN, -hv, hv, -SLAB - 0.06, -SLAB, I["ceiling"])
    for vv in (-0.95, 0.95):
        F.box(mb, L_HOLE + 0.4, L_TUN - 0.4, vv - 0.07, vv + 0.07, -SLAB - 0.08, -SLAB - 0.06, I["light"])
    # ---- stair: top landing, 19 treads, landing; nosings; handrails
    vs0, vs1 = V_STAIR
    F.box(mb, 0.0, U_STAIR0, vs0, vs1, -0.30, 0.0, I["floor"])
    for k in range(1, N_RISE):
        ua = U_STAIR0 + (k - 1) * TREAD
        wt = -RISE * k
        F.box(mb, ua, ua + TREAD, vs0, vs1, wt - 0.45, wt, I["tread"])
        F.box(mb, ua, ua + 0.045, vs0, vs1, wt, wt + 0.004, I["nosing"])
    for vv in (vs0 + 0.07, vs1 - 0.07, (vs0 + vs1) / 2):
        path = [F.P(-0.10, vv, 0.85), F.P(U_STAIR0, vv, 0.85), F.P(U_STAIR1, vv, -DEPTH + 0.85), F.P(L_TUN - 0.4, vv, -DEPTH + 0.85)]
        L.tube(mb, path, 0.02, sides=8, mat=I["steel"], smooth=True)
    vm = (vs0 + vs1) / 2
    for uu in (0.15, 1.6, 3.2, 4.8, 6.3):
        wt = stair_line(uu + 0.01) if uu > U_STAIR0 else 0.0
        if uu > U_STAIR0:
            k = min(N_RISE - 1, int((uu - U_STAIR0) / TREAD) + 1)
            wt = -RISE * k
        wr = stair_line(uu) + 0.85
        F.box(mb, uu - 0.02, uu + 0.02, vm - 0.02, vm + 0.02, wt, wr, I["steel"])
    # ---- divider (escalator truss cladding) between stair and escalator
    samples = [-0.0, ESC_U0, ESC_U1, L_TUN]
    top = [(u, esc_line(u) + (0.05 if use_model else 0.12)) for u in samples]
    F.prism_uw(mb, top + [(L_TUN, -DEPTH), (0.0, -DEPTH)], V_DIV[0], V_DIV[1], I["steel"])
    if use_model:
        # pit under the lower truss of the escalator model (reaches 1.05 m below the landing)
        F.box(mb, 5.4, ESC_END + 0.4, V_ESC[0], V_ESC[1], -DEPTH - 1.18, -DEPTH - 0.14, I["tile"])
    else:
        procedural_escalator(F, I, me_esc)
    platform_enclosure(F, I, mb)


def procedural_escalator(F, I, me_esc):
    """fallback when assets/escalator_kone_tm110.blend is missing"""
    ve0, ve1 = V_ESC
    g0, g1 = ve0 + 0.155, ve1 - 0.155          # glass planes
    s0, s1 = g0 + 0.085, g1 - 0.085            # step band
    us = [-0.55, 0.0, ESC_U0 - 0.3, ESC_U0, ESC_U0 + 0.3] + list(np.linspace(ESC_U0 + 0.6, ESC_U1 - 0.6, 6)) + [ESC_U1 - 0.3, ESC_U1, ESC_U1 + 0.3, ESC_END + 0.4]

    def band(w_lo, w_hi, v0, v1, mat, u_from=-0.55, u_to=ESC_END + 0.4):
        uu = [u for u in us if u_from - 1e-6 <= u <= u_to + 1e-6]
        upper = [(u, esc_line(max(u, 0.0)) + w_hi) for u in uu]
        lower = [(u, esc_line(max(u, 0.0)) + w_lo) for u in reversed(uu)]
        F.prism_uw(me_esc, upper + lower, v0, v1, mat)
    band(0.12, 0.95, g0 - 0.006, g0 + 0.006, I["glass"])
    band(0.12, 0.95, g1 - 0.006, g1 + 0.006, I["glass"])
    band(0.95, 1.01, g0 - 0.04, g0 + 0.04, I["rubber"])
    band(0.95, 1.01, g1 - 0.04, g1 + 0.04, I["rubber"])
    band(0.0, 0.12, s0 - 0.085, s0, I["steel"], 0.0)          # skirt + inner decking
    band(0.0, 0.12, s1, s1 + 0.085, I["steel"], 0.0)
    band(0.10, 0.12, ve0, g0 - 0.006, I["steel"], -0.55)       # outer decking
    band(0.10, 0.12, g1 + 0.006, ve1, I["steel"], -0.55)
    band(-0.60, 0.10, ve0, ve0 + 0.02, I["steel"], -0.55)      # truss cladding on the divider side
    # newel ends (rounded handrail returns, approximated by short boxes)
    for gg in (g0, g1):
        F.box(me_esc, -0.62, -0.50, gg - 0.04, gg + 0.04, 0.12, 1.01, I["rubber"])
        F.box(me_esc, ESC_END + 0.35, ESC_END + 0.47, gg - 0.04, gg + 0.04, -DEPTH + 0.12, -DEPTH + 1.01, I["rubber"])
    # comb plates and steps with yellow demarcation
    F.box(me_esc, 0.0, 0.5, s0, s1, -0.05, 0.004, I["steel"])
    F.box(me_esc, ESC_END - 0.5, ESC_END, s0, s1, -DEPTH - 0.05, -DEPTH + 0.008, I["steel"])
    ua = 0.5
    while ua < ESC_END - 0.5 - 1e-6:
        ub = ua + 0.40
        h = esc_line(ub) if ESC_U0 < ub < ESC_U1 + 0.4 else esc_line(ua)
        h = max(h, -DEPTH + 0.005)
        F.box(me_esc, ua + 0.005, ub - 0.005, s0, s1, h - 0.24, h, I["esc_step"])
        for v0, v1 in ((s0, s0 + 0.04), (s1 - 0.04, s1)):
            F.box(me_esc, ua + 0.005, ub - 0.005, v0, v1, h, h + 0.003, I["esc_yellow"])
        F.box(me_esc, ub - 0.045, ub - 0.005, s0, s1, h, h + 0.003, I["esc_yellow"])
        ua = ub


def platform_enclosure(F, I, mb):
    hv = W_IN / 2
    vs0, vs1 = V_STAIR
    ve0, ve1 = V_ESC
    # ---- platform level: enclosure walls with stainless cap, end wall, tactile strip
    for sgn in (-1, 1):
        v0 = sgn * hv; v1 = sgn * (hv + WALL)
        F.box(mb, 0.0, L_HOLE + WALL, min(v0, v1), max(v0, v1), 0.0, 1.10, I["panel"])
        F.box(mb, 0.0, L_HOLE + WALL, min(v0, v1) - 0.02, max(v0, v1) + 0.02, 1.10, 1.14, I["steel"])
    F.box(mb, L_HOLE, L_HOLE + WALL, -hv - WALL, hv + WALL, 0.0, 2.40, I["panel"])
    F.box(mb, L_HOLE - 0.02, L_HOLE + WALL + 0.02, -hv - WALL - 0.02, hv + WALL + 0.02, 2.40, 2.44, I["steel"])
    F.box(mb, -0.62, -0.02, vs0, vs1, 0.0, 0.006, I["tactile"])
    F.box(mb, -0.90, -0.30, ve0 + 0.1, ve1 - 0.1, 0.0, 0.006, I["tactile"])


def wall_boards(F, isl, I, mb):
    """route map on the end wall, stop-pattern boards of the adjacent lines on the side walls, landing sign."""
    if isl.shin:      # a roof column stands just beyond the end wall: the map faces the stair entrance instead
        board(mb, F.P(L_HOLE - 0.02, 0.0, 1.55), F.u, 2.6, 1.4, "routemap", None, I, kind="board", thick=0.03)
    else:
        u_out = L_HOLE + WALL + 0.012
        board(mb, F.P(u_out + 0.02, 0.0, 1.55), -F.u, 2.6, 1.4, "routemap", None, I, kind="board", thick=0.03)
    east_is_plus_v = F.v.y > 0
    tracks = ATLAS["tracks"]
    for sgn in (-1, 1):
        t = isl.te if (sgn > 0) == east_is_plus_v else isl.tw
        key = "stops_" + tracks[str(t)]["stops"]
        n = F.v * sgn
        C = F.P(L_HOLE / 2, sgn * (HALF_OUT + 0.02), 0.62)
        board(mb, C, -n, 4.8, 0.6, key, None, I, kind="board", thick=0.03)


# ----------------------------------------------------------------------------------------- escalator model
def escalator_master(mats, I):
    """Append the CC BY escalator model, merge it into one mesh with the V6 materials, keep it in an excluded master
    collection (instanced at every stairwell)."""
    if not os.path.exists(ESC_ASSET):
        REPORTD["warnings"].append("escalator model missing, procedural escalators used")
        return None
    with bpy.data.libraries.load(ESC_ASSET, link=False) as (src, dst):
        dst.objects = list(src.objects)
    objs = [o for o in dst.objects if o is not None]
    order = list(dict.fromkeys(ESC_MATS.values()))
    bm = bmesh.new()
    nv = 0
    for o in objs:
        if o.type != 'MESH':
            continue
        me = o.data.copy()
        me.transform(o.matrix_world)
        n0 = len(bm.faces)
        bm.from_mesh(me)
        bm.faces.ensure_lookup_table()
        remap = [order.index(ESC_MATS.get(m.name if m else "", "steel")) for m in me.materials] or [0]
        for f in bm.faces[n0:]:
            f.material_index = remap[f.material_index] if f.material_index < len(remap) else 0
        nv += len(me.vertices)
        bpy.data.meshes.remove(me)
    me = bpy.data.meshes.new("V6 escalator KONE TravelMaster 110 (4 m rise)")
    bm.to_mesh(me); bm.free()
    for k in order:
        me.materials.append(mats[I[k]])
    for p in me.polygons:
        p.use_smooth = False
    ob = bpy.data.objects.new(me.name, me)
    ob["credit"] = ESC_CREDIT
    if len(me.vertices) != nv:
        REPORTD["warnings"].append(f"escalator merge: {len(me.vertices)} verts, expected {nv}")
    col = bpy.data.collections.get("V6 escalator master") or bpy.data.collections.new("V6 escalator master")
    if col.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(col)
    col.objects.link(ob)
    col["credit"] = ESC_CREDIT

    def find_lc(lc, name):
        if lc.collection.name == name:
            return lc
        for c in lc.children:
            r = find_lc(c, name)
            if r:
                return r
    lc = find_lc(bpy.context.view_layer.layer_collection, col.name)
    if lc:
        lc.exclude = True
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)
    L.log("escalator master", len(me.vertices), "verts")
    return col


# ----------------------------------------------------------------------------------------- main
LEGACY_SIGNS = re.compile(r"^V3 platform (numbered sign|number|route|route colour)(\.\d+)?$")


def fix_legacy_text():
    """The V3 platform-end boards (MS Gothic / Bahnschrift text, some wording wrong, positions from before the V5
    re-layout) are replaced by the new 番線案内 boards; the Roman numerals of the dome-gable clocks get a serif face."""
    n = 0
    for o in list(bpy.data.objects):
        if LEGACY_SIGNS.match(o.name) and not o.get("V5_retired") and not o.get("V6_retired"):
            retire(o); n += 1
    serif = None
    for fp in (os.path.join(HERE, "fonts", "texgyretermes-bold.otf"), "C:/Windows/Fonts/timesbd.ttf",
               "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"):
        if os.path.exists(fp):
            serif = bpy.data.fonts.load(fp, check_existing=True)
            serif.pack()
            break
    nc = 0
    if serif:
        for o in bpy.data.objects:
            if o.type == 'FONT' and re.match(r"V3 (NORTH|SOUTH) Roman clock", o.name):
                o.data.font = serif; nc += 1
    REPORTD["legacy_platform_signs_retired"] = n
    REPORTD["clock_numerals_serif"] = nc
    L.log("legacy text", n, "clock numerals", nc, serif.name if serif else None)


def run():
    random.seed(20261030)
    fix_legacy_text()
    hanger = Hanger()
    islands = [Island(k, v) for k, v in PLAT.items()]
    if ONLY:
        islands = [i for i in islands if i.name in ONLY]
    ob = Obst(islands)
    mats, I = materials()
    col = L.collection("V6_Platform_Stairs_and_Signs")
    esc_col = escalator_master(mats, I)
    n_esc = 0
    mb_well, mb_esc, mb_sign, mb_wall, mb_small = (L.MeshBuilder() for _ in range(5))
    keepouts = []
    all_frames = []
    plan = {}
    for isl in islands:
        ch = find_openings(isl, ob, hanger)
        plan[isl.name] = ch
        all_frames += [F for F, _p, _n in ch]
        REPORTD["islands"][isl.name] = {"openings": [{"pos": p, "x_entrance": round(F.xa, 2), "dir": F.s, "piers_hit": n}
                                                     for F, p, n in ch]}
        L.log(isl.name, REPORTD["islands"][isl.name])
    REPORTD["cuts"] = cut_scene(all_frames)
    # ---- build
    tracks = ATLAS["tracks"]
    for isl in islands:
        info = REPORTD["islands"][isl.name]
        hung = 0
        for F, pos, _n in plan[isl.name]:
            build_stairwell(F, I, mb_well, mb_esc, use_model=esc_col is not None)
            if esc_col is not None:
                e = bpy.data.objects.new(f"V6 escalator {isl.name} {pos}", None)
                e.instance_type = 'COLLECTION'
                e.instance_collection = esc_col
                vc = (V_ESC[0] + V_ESC[1]) / 2
                e.matrix_world = F.M @ Matrix(((-1, 0, 0, ESC_UX), (0, -1, 0, vc), (0, 0, 1, -DEPTH), (0, 0, 0, 1)))
                col.objects.link(e)
                n_esc += 1
            wall_boards(F, isl, I, mb_wall)
            # entrance sign: front = exit/passage sign for people walking towards the stairs, back = 番線案内
            back_view = "N" if (-F.u).x > 0 else "S"
            C = F.P(-0.45, 0.0, 2.60)
            board(mb_sign, C, F.u, 3.8, 0.5, f"exit_{isl.group}_{pos}_down", f"dir_{isl.name}_{back_view}", I)
            if hanger.rods(mb_sign, isl, [F.P(-0.45, -1.55, 2.88), F.P(-0.45, 1.55, 2.88)], I["frame"]):
                hung += 1
            else:
                REPORTD["warnings"].append(f"{isl.name} {pos}: entrance sign without hanger")
            # sign on the landing wall
            board(mb_sign, F.P(L_TUN - 0.06, 0.0, -DEPTH + 2.15), F.u, 3.2, 0.5 * 3.2 / 3.8, f"exit_{isl.group}_{pos}_down", None, I, thick=0.04)
            keepouts.append({"kind": "stairwell", "island": isl.name, "pos": pos, "c": [F.O.x, F.O.y], "u": [F.u.x, F.u.y],
                             "u0": KEEP_U[0], "u1": L_TUN + WALL + 0.2, "hv": HALF_OUT + 0.15,
                             "z0": isl.z - DEPTH - 0.3, "z1": isl.z + 3.0})
        info["entrance_signs_hung"] = hung
    # ---- free-hanging 番線案内 boards and clocks between the stairwells
    for isl in islands:
        info = REPORTD["islands"][isl.name]
        fb = ob.furn[isl.name]
        cols = ob.columns_near(isl)
        xs_open = [((F.P(KEEP_U[0], 0).x + F.P(L_TUN, 0).x) / 2) for F, _p, _n in plan[isl.name]]
        wants = []
        if len(xs_open) >= 2:
            xs_sorted = sorted(xs_open)
            wants = [(a + b) / 2 for a, b in zip(xs_sorted[:-1], xs_sorted[1:])]
        lo = max(isl.sx[0], -150) + 14; hi = min(isl.sx[-1], 150) - 14
        wants += [lo + 6, hi - 6]
        n_dir = n_clock = 0
        taken = []
        for xw in wants:
            placed = False
            for dx in [0.0] + [s * k * 0.75 for k in range(1, 20) for s in (1, -1)]:
                x = xw + dx
                if isl.w(x) < 6.0:
                    continue
                t = isl.tangent(x)
                y = isl.yc(x)
                if any(k_["kind"] == "stairwell" and k_["island"] == isl.name and in_keepout(k_, x, y, 4.0) for k_ in keepouts):
                    continue
                if len(cols) and np.any(np.abs(cols[:, 0] - x) < 1.4):
                    continue
                if len(fb):
                    near = fb[(np.abs((fb[:, 0] + fb[:, 3]) / 2 - x) < 1.3) & (fb[:, 5] > isl.z + 2.0)]
                    if len(near):
                        continue
                if any(abs(x - tx) < 8 for tx in taken):
                    continue
                C = Vector((x, y, isl.z + 2.62))
                R = t.cross(Vector((0, 0, 1)))
                pts = [C + R * 1.55 + Vector((0, 0, 0.28)), C - R * 1.55 + Vector((0, 0, 0.28))]
                if not all(hanger.top(isl, p) is not None for p in pts):
                    continue
                board(mb_sign, C, t, 3.8, 0.5, f"dir_{isl.name}_N", f"dir_{isl.name}_S", I)
                hanger.rods(mb_sign, isl, pts, I["frame"])
                keepouts.append({"kind": "sign", "island": isl.name, "c": [x, y], "u": [t.x, t.y], "u0": -0.4, "u1": 0.4,
                                 "hv": 2.1, "z0": isl.z + 2.2, "z1": isl.z + 9.0})
                taken.append(x)
                n_dir += 1
                placed = True
                # clock next to the board (on the centre line, 2.6 m further along)
                for cdx in (2.6, -2.6):
                    xc = x + cdx
                    if len(cols) and np.any(np.abs(cols[:, 0] - xc) < 0.8):
                        continue
                    yc = isl.yc(xc)
                    if any(k_["kind"] == "stairwell" and in_keepout(k_, xc, yc, 0.5) for k_ in keepouts):
                        continue
                    Cc = Vector((xc, yc, isl.z + 2.78))
                    if hanger.top(isl, Cc + Vector((0, 0, 0.30))) is None:
                        continue
                    clock(mb_small, Cc, isl.tangent(xc), I)
                    hanger.rods(mb_small, isl, [Cc + Vector((0, 0, 0.27))], I["frame"])
                    keepouts.append({"kind": "clock", "island": isl.name, "c": [xc, yc], "u": [1, 0], "u0": -0.4, "u1": 0.4,
                                     "hv": 0.4, "z0": isl.z + 2.4, "z1": isl.z + 9.0})
                    n_clock += 1
                    break
                break
            if not placed:
                REPORTD["warnings"].append(f"{isl.name}: no free spot for a direction board near x={xw:.0f}")
        info["direction_boards"] = n_dir
        info["clocks"] = n_clock
        # emergency-stop buttons on the columns (the V5 fire-extinguisher boxes are on the +x faces)
        n_stop = 0
        for x, y, z, r in cols:
            off = (0.12 if r < 0.3 else 0.27) + 0.05
            t = isl.tangent(x)
            C = Vector((x, y, isl.z + 1.37)) - t * off
            M = Matrix(((t.x, -t.y, 0, C.x), (t.y, t.x, 0, C.y), (0, 0, 1, C.z), (0, 0, 0, 1)))
            L.box(mb_small, 0, 0, 0, 0.10, 0.17, 0.26, I["estop"], frame=M)
            quad(mb_small, C - t * 0.052, t.cross(Vector((0, 0, 1))), Vector((0, 0, 1)), 0.16, 0.24, "estop", mat_for("estop", I))
            n_stop += 1
        info["emergency_stop_buttons"] = n_stop
    # ---- Shinkansen car-number boards
    cars = shinkansen_cars()
    for isl in islands:
        if not isl.shin:
            continue
        fb = ob.furn[isl.name]
        n_car = 0
        for t, side in ((isl.tw, -1), (isl.te, 1)):
            for n, x in cars.get(t, []):
                w = isl.w(x)
                if w < 6.0:
                    continue
                y = isl.yc(x) + side * (w / 2 - 1.55)
                if len(fb):
                    near = fb[(np.abs((fb[:, 0] + fb[:, 3]) / 2 - x) < 1.4) & (np.abs((fb[:, 1] + fb[:, 4]) / 2 - y) < 1.6)
                              & (fb[:, 5] > isl.z + 2.0)]
                    if len(near):
                        continue
                if any(in_keepout(k_, x, y, 0.8) for k_ in keepouts if k_["island"] == isl.name):
                    continue
                tg = isl.tangent(x)
                C = Vector((x, y, isl.z + 2.70))
                R = tg.cross(Vector((0, 0, 1)))
                pts = [C + R * 0.45 + Vector((0, 0, 0.23)), C - R * 0.45 + Vector((0, 0, 0.23))]
                if not all(hanger.top(isl, p) is not None for p in pts):
                    continue
                key = f"car_{isl.group}_{n:02d}"
                if key not in ATLAS["items"]:
                    continue
                board(mb_sign, C, tg, 1.2, 0.4, key, key, I, thick=0.06)
                hanger.rods(mb_sign, isl, pts, I["frame"])
                keepouts.append({"kind": "car sign", "island": isl.name, "c": [x, y], "u": [tg.x, tg.y], "u0": -0.3, "u1": 0.3,
                                 "hv": 0.8, "z0": isl.z + 2.3, "z1": isl.z + 9.0})
                n_car += 1
        REPORTD["islands"][isl.name]["car_number_boards"] = n_car
    # ---- objects
    objs = {}
    for nm, mbx in (("V6 platform stairs | stairwells, stairs and enclosures", mb_well),
                    ("V6 platform stairs | escalators", mb_esc),
                    ("V6 platform signs | hanging boards", mb_sign),
                    ("V6 platform signs | route maps and stop-pattern boards", mb_wall),
                    ("V6 platform | clocks and emergency-stop buttons", mb_small)):
        if mbx.v:
            objs[nm] = mbx.build(nm, col, mats)
            objs[nm]["V6_platforms"] = True
    REPORTD["verts"] = {k: len(o.data.vertices) for k, o in objs.items()}
    REPORTD["escalators"] = {"instances": n_esc, "model": ESC_CREDIT if esc_col else "procedural fallback",
                             "master_verts": len(esc_col.objects[0].data.vertices) if esc_col else 0}
    # ---- people
    REPORTD["people_moved"] = move_people(keepouts)
    REPORTD["people_added_on_stairs"] = people_on_stairs(plan, islands)
    bpy.context.scene["V6_platform_keepouts"] = json.dumps(keepouts)
    bpy.context.scene["V6_platform_summary"] = json.dumps({k: v for k, v in REPORTD.items() if k != "cuts"}, ensure_ascii=False)
    L.log(json.dumps({k: v for k, v in REPORTD.items()}, ensure_ascii=False)[:3000])
    if REPORT:
        json.dump(dict(REPORTD, keepouts=keepouts), open(REPORT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    if OUT:
        bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=True)
        L.log("saved", OUT)


def in_keepout(k, x, y, pad=0.0):
    ux, uy = k["u"]
    du = (x - k["c"][0]) * ux + (y - k["c"][1]) * uy
    dv = -(x - k["c"][0]) * uy + (y - k["c"][1]) * ux
    return k["u0"] - pad <= du <= k["u1"] + pad and abs(dv) <= k["hv"] + pad


def clock(mb, C, t, I):
    """double-sided round platform clock (faces along the platform)"""
    R = t.cross(Vector((0, 0, 1))); U = Vector((0, 0, 1))
    u0, v0, u1, v1 = ATLAS["items"]["clock"]["uv"]
    uc, vc, ru, rv = (u0 + u1) / 2, (v0 + v1) / 2, (u1 - u0) / 2, (v1 - v0) / 2
    r, n = 0.25, 32
    for sgn in (1, -1):
        N = -t * sgn
        Rs = R * sgn
        ctr = C + N * 0.045
        verts = [tuple(ctr)] + [tuple(ctr + Rs * (r * math.cos(2 * math.pi * i / n)) + U * (r * math.sin(2 * math.pi * i / n))) for i in range(n)]
        faces = [(0, 1 + i, 1 + (i + 1) % n) for i in range(n)]
        uvs = [[(uc, vc), (uc + ru * 0.985 * math.cos(2 * math.pi * i / n), vc + rv * 0.985 * math.sin(2 * math.pi * i / n)),
                (uc + ru * 0.985 * math.cos(2 * math.pi * ((i + 1) % n) / n), vc + rv * 0.985 * math.sin(2 * math.pi * ((i + 1) % n) / n))]
               for i in range(n)]
        mb.add(verts, faces, mat_for("clock", I), uvs=uvs)
    prof = [(0.0, -0.045), (r + 0.03, -0.045), (r + 0.03, 0.045), (0.0, 0.045)]
    M = Matrix(((R.x, U.x, t.x, C.x), (R.y, U.y, t.y, C.y), (R.z, U.z, t.z, C.z), (0, 0, 0, 1)))
    verts, faces = [], []
    for i in range(n):
        a0 = 2 * math.pi * i / n
        for (rr, zz) in ((r + 0.03, -0.044), (r + 0.03, 0.044)):
            verts.append(tuple(M @ Vector((rr * math.cos(a0), rr * math.sin(a0), zz))))
    for i in range(n):
        j = (i + 1) % n
        faces.append((2 * i, 2 * j, 2 * j + 1, 2 * i + 1))
    mb.add(verts, faces, I["frame"])


def shinkansen_cars():
    """car number -> x of the car centre for every Shinkansen track (from the stopping trains; copied to empty tracks)."""
    dg = bpy.context.evaluated_depsgraph_get()
    acc = {}
    for inst in dg.object_instances:
        if not inst.is_instance or inst.parent is None:
            continue
        m = re.match(r"Track (\d\d)", inst.parent.name)
        if not m or int(m.group(1)) < 14:
            continue
        t = int(m.group(1))
        ob = inst.object
        if ob.type != 'MESH':
            continue
        mc = re.search(r"N700 car (\d\d)", ob.name)
        if mc:
            n = int(mc.group(1))
        else:
            me5 = re.search(r"E5 car (\d\d)", inst.parent.name)
            if not me5:
                continue
            n = 11 - int(me5.group(1))              # V5 instance names count from the north end; real car 1 is the Tokyo (south) end
        bb = [inst.matrix_world @ Vector(c) for c in ob.bound_box]
        acc.setdefault(t, {}).setdefault(n, []).extend([min(v.x for v in bb), max(v.x for v in bb)])
    cars = {}
    for t, d in acc.items():
        cars[t] = sorted((n, (min(v) + max(v)) / 2) for n, v in d.items())
    for t in range(14, 24):
        if t not in cars:
            src = 14 if t in (15, 16, 17) else 18 if t == 19 else 20
            if src in cars:
                cars[t] = cars[src]
    L.log("shinkansen car positions", {t: [(n, round(x, 1)) for n, x in v] for t, v in cars.items()})
    return cars


def move_people(keepouts):
    moved = 0
    people = [o for o in bpy.data.objects if o.name.startswith("V5 person P") and o.instance_type == 'COLLECTION']
    for o in people:
        x, y = o.location.x, o.location.y
        for k in keepouts:
            if k["kind"] != "stairwell" or abs(o.location.z - (k["z1"] - 3.0)) > 1.0:
                continue
            if in_keepout(k, x, y, 0.45):
                ux, uy = k["u"]
                # walk them to just in front of the entrance
                du = (x - k["c"][0]) * ux + (y - k["c"][1]) * uy
                shift = (k["u0"] - 0.9 - random.uniform(0, 2.5)) - du
                nx, ny = x + ux * shift, y + uy * shift
                if not any(in_keepout(k2, nx, ny, 0.4) for k2 in keepouts if k2["kind"] == "stairwell"):
                    o.location.x, o.location.y = nx, ny
                    moved += 1
                break
    return moved


def people_on_stairs(plan, islands):
    cols = [c for c in bpy.data.collections if re.match(r"V5 pedestrian \d$", c.name)]
    if not cols:
        return 0
    pcol = L.collection("V5_People_instances")
    n = 0
    for isl in islands:
        for F, pos, _n in plan[isl.name]:
            spots = [(U_STAIR0 + TREAD * 4.5, -1.25, "stair", 1), (U_STAIR0 + TREAD * 12.5, -0.35, "stair", -1),
                     (ESC_U0 + 2.6, (V_ESC[0] + V_ESC[1]) / 2, "esc", 1)]
            for i, (u, v, kind, facing) in enumerate(spots):
                if random.random() < 0.25:
                    continue
                if kind == "stair":
                    k = int((u - U_STAIR0) / TREAD) + 1
                    w = -RISE * k
                else:
                    w = esc_line(u) + 0.02
                p = F.P(u, v, w)
                e = bpy.data.objects.new(f"V6 person stairs {isl.name} {pos} {i}", None)
                e.instance_type = 'COLLECTION'
                e.instance_collection = random.choice(cols)
                e.location = p
                ang = math.atan2(F.u.y, F.u.x) + (0.0 if facing > 0 else math.pi)
                e.rotation_euler = (0, 0, ang)
                pcol.objects.link(e)
                n += 1
    return n


run()
