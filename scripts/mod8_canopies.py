"""V8 module 2: steel-framed platform canopies on the conventional islands (01-02 ... 09-10).

Why (round-8 feedback "把站台天花板也还原成与现实一样的，现在的太简化了"):
  Since V3 every conventional canopy was a flat 20 cm slab on single 0.24 m posts every 28 m, with flat light strips
  stuck to its underside.  Seen from the platform it was a plain grey ceiling.  The real canopies (photos on Wikimedia
  Commons: platforms 7-8 and 9-10 from the platform, 7-8 seen across track 8, 3-4 panorama, 8/9 at night) show the
  structure from below:
    * transverse main beams on round steel columns at roughly 9-10 m, cantilevering over both platform edges
      (plain H-beams on 7-8, deep riveted lattice girders on 9-10, haunched beams sloping to the eaves on 3-4)
    * secondary beams between them, longitudinal purlins and the profiled roof deck visible above
    * deep edge girders with fascia and gutter; on 7-8 a translucent barrel skylight along the middle
    * linear light fittings hung below in two rows, cable trays along both sides, loudspeakers, CCTV cameras
    * cream / beige painted steel; columns with red-white guard bands and a rainwater down-pipe
This module retires the slabs, the light strips and the 0.24 m posts and builds that structure under the same top
surface (aerial views keep the same roof outline and height).  Hanging signs keep their fixing level: their rods end
at the old slab underside, so a fixing block is added above each rod.  Columns are added between the old ones where
the platform is free (stairwells, signs, furniture and overhead-line masts are checked).

usage: blender -b in.blend --python-exit-code 1 -P mod8_canopies.py -- out.blend [report.json]
"""
import sys, os, json, math, re
import numpy as np
import bpy
from mathutils import Vector, Matrix
from mathutils.kdtree import KDTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v5lib as L

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGV[0] if ARGV else None
REPORT = ARGV[1] if len(ARGV) > 1 else None

ISLANDS = ["01-02", "03-04", "05-06", "07-08", "09-10"]
STYLE = {"01-02": "plain", "03-04": "haunched", "05-06": "haunched", "07-08": "skylight", "09-10": "lattice"}
COL_SUB = 3                  # main frames per old 28 m column bay (-> ~9.3 m)
SEC_SUB = 4                  # secondary beams per main bay (-> ~2.3 m)
PURLIN_STEP = 1.25
DECK_T = 0.06
PURLIN_D = 0.15
MAIN_D = {"plain": 0.45, "skylight": 0.45, "haunched": (0.78, 0.34), "lattice": 0.66}
SEC_D = 0.30
EDGE_D = 0.42
COL_R = 0.17
SKY_W = 1.80
REP = {"islands": {}, "warnings": []}


# ------------------------------------------------------------------------------------------------ materials
def materials():
    cream = L.principled("V8 | canopy steel (cream paint)", (0.60, 0.55, 0.43), rough=0.55, metal=0.05)
    colp = L.principled("V8 | canopy column paint (light grey)", (0.66, 0.66, 0.63), rough=0.5, metal=0.05)
    red = L.principled("V8 | column guard band red", (0.55, 0.04, 0.03), rough=0.5)
    white = L.principled("V8 | column guard band white", (0.80, 0.80, 0.78), rough=0.5)
    pipe = L.principled("V8 | down-pipe grey", (0.35, 0.36, 0.36), rough=0.5, metal=0.2)
    dark = L.principled("V8 | fittings dark grey", (0.06, 0.065, 0.07), rough=0.45, metal=0.4)
    housing = L.principled("V8 | light fitting housing white", (0.80, 0.80, 0.78), rough=0.35)
    lamp = bpy.data.materials.get("V2 | lighting diffuser") or L.principled("V8 | lamp", (0.9, 0.9, 0.8), emission=(0.9, 0.9, 0.8), strength=1.5)
    sky = bpy.data.materials.get("V8 | skylight polycarbonate")
    if sky is None:
        sky = bpy.data.materials.new("V8 | skylight polycarbonate")
        nt = sky.node_tree; b = nt.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (0.86, 0.88, 0.86, 1.0)
        b.inputs["Roughness"].default_value = 0.35
        b.inputs["Transmission Weight"].default_value = 0.85
        sky.diffuse_color = (0.86, 0.88, 0.86, 1.0)
    # profiled deck seen from below: cream with fine ribs across the platform (world x)
    deck = bpy.data.materials.get("V8 | canopy deck underside (profiled steel, cream)")
    if deck is None:
        deck = bpy.data.materials.new("V8 | canopy deck underside (profiled steel, cream)")
        nt = deck.node_tree; b = nt.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (0.68, 0.63, 0.50, 1.0)
        b.inputs["Roughness"].default_value = 0.55
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        wave = nt.nodes.new("ShaderNodeMath"); wave.operation = 'SINE'
        mul = nt.nodes.new("ShaderNodeMath"); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = 2 * math.pi / 0.20
        bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.6; bump.inputs["Distance"].default_value = 0.02
        nt.links.new(geo.outputs["Position"], sep.inputs[0])
        nt.links.new(sep.outputs["X"], mul.inputs[0])
        nt.links.new(mul.outputs[0], wave.inputs[0])
        nt.links.new(wave.outputs[0], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
        deck.diffuse_color = (0.68, 0.63, 0.50, 1.0)
    roof = bpy.data.materials.get("V5 | platform canopy folded-plate steel roofing")
    M = {"cream": cream, "col": colp, "red": red, "white": white, "pipe": pipe, "dark": dark, "housing": housing,
         "lamp": lamp, "sky": sky, "deck": deck, "roof": roof}
    return M


# ------------------------------------------------------------------------------------------------ geometry helpers
def world_verts(o):
    me = o.data; n = len(me.vertices)
    co = np.empty(n * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    M = np.array(o.matrix_world)
    return co @ M[:3, :3].T + M[:3, 3]


class Outline:
    """Plan outline of one old slab: west/east edge y as functions of x, top/underside z."""

    def __init__(self, o, yc_fn):
        W = world_verts(o)
        self.zt = float(W[:, 2].max()); self.zu = float(W[:, 2].min())
        top = W[np.abs(W[:, 2] - self.zt) < 1e-3]
        c = yc_fn(top[:, 0])
        we, ea = top[top[:, 1] < c], top[top[:, 1] >= c]
        we = we[np.argsort(we[:, 0])]; ea = ea[np.argsort(ea[:, 0])]
        self.wx, self.wy = we[:, 0], we[:, 1]
        self.ex, self.ey = ea[:, 0], ea[:, 1]
        self.x0 = float(max(self.wx.min(), self.ex.min())); self.x1 = float(min(self.wx.max(), self.ex.max()))

    def yw(self, x):
        return np.interp(x, self.wx, self.wy)

    def ye(self, x):
        return np.interp(x, self.ex, self.ey)

    def at(self, x, f):
        """point across the canopy: f = 0 west edge, 1 east edge"""
        a, b = self.yw(x), self.ye(x)
        return a + (b - a) * f


def sweep(mb, xs, ys, z0, z1, hw, mat, cap=True):
    """Box section (half width hw, from z0 to z1) swept along the plan polyline (xs, ys)."""
    xs = np.asarray(xs, float); ys = np.asarray(ys, float)
    if len(xs) < 2:
        return
    tx = np.gradient(xs); ty_ = np.gradient(ys)
    ln = np.hypot(tx, ty_); nx, ny = -ty_ / ln, tx / ln
    z0 = np.broadcast_to(np.asarray(z0, float), xs.shape); z1 = np.broadcast_to(np.asarray(z1, float), xs.shape)
    V = []
    for i in range(len(xs)):
        for s, z in ((-1, z0[i]), (1, z0[i]), (1, z1[i]), (-1, z1[i])):
            V.append((xs[i] + nx[i] * hw * s, ys[i] + ny[i] * hw * s, z))
    F = []
    for i in range(len(xs) - 1):
        a, b = 4 * i, 4 * (i + 1)
        for j in range(4):
            k = (j + 1) % 4
            F.append((a + j, a + k, b + k, b + j))
    if cap:
        F.append((3, 2, 1, 0)); n = 4 * (len(xs) - 1); F.append((n, n + 1, n + 2, n + 3))
    mb.add(V, F, mat)


def hbox(mb, x, ya, yb_, z0, z1, wx, mat):
    """box spanning across the canopy at station x (from y=ya to y=yb_), thickness wx along x"""
    L.box(mb, x, (ya + yb_) / 2, (z0 + z1) / 2, wx, abs(yb_ - ya), z1 - z0, mat)


def prism_yz(mb, x, wx, pts_yz, mat):
    """extrude a convex polygon given in the (y, z) plane by wx along x"""
    n = len(pts_yz)
    V = [(x - wx / 2, y, z) for y, z in pts_yz] + [(x + wx / 2, y, z) for y, z in pts_yz]
    F = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    for j in range(n):
        k = (j + 1) % n
        F.append((j, k, n + k, n + j))
    mb.add(V, F, mat)


def rod(mb, p, q, r, mat, sides=6):
    L.tube(mb, [Vector(p), Vector(q)], r, sides=sides, mat=mat)


# ------------------------------------------------------------------------------------------------ obstacles
class Obstacles:
    def __init__(self, sc):
        self.keep = json.loads(sc.get("V6_platform_keepouts", "[]"))
        pts = []
        self.people = []
        for o in sc.objects:
            if not o.visible_get():
                continue
            if o.type == 'EMPTY' and re.match(r"V\d person", o.name):
                self.people.append(o)
                continue
            if o.type != 'MESH':
                continue
            if re.match(r"V5 platform \d\d-\d\d furniture|V6 platform|V6 OCS \| masts|V3 bench|V3 plaza granite bench", o.name):
                W = world_verts(o)
                pts.append(W)
        P = np.concatenate(pts) if pts else np.zeros((0, 3))
        self.P = P
        self.kd = KDTree(len(P))
        for i, p in enumerate(P):
            self.kd.insert(Vector((p[0], p[1], 0.0)), i)
        self.kd.balance()

    def free(self, x, y, z0, z1, r):
        for k in self.keep:
            c = np.array(k["c"]); u = np.array(k["u"]); v = np.array([-u[1], u[0]])
            d = np.array([x, y]) - c
            du, dv = d @ u, d @ v
            u0, u1 = k.get("u0", -1.0), k.get("u1", 1.0)
            hv = k.get("hv", 1.0)
            if u0 - r <= du <= u1 + r and abs(dv) <= hv + r:
                kz0, kz1 = k.get("z0", -1e9), k.get("z1", 1e9)
                if kz1 >= z0 - 0.5 and kz0 <= z1 + 0.5:
                    return False
        for (co, i, dist) in self.kd.find_range(Vector((x, y, 0.0)), r):
            if z0 <= self.P[i, 2] <= z1:
                return False
        for o in self.people:
            t = o.matrix_world.translation
            if math.hypot(t.x - x, t.y - y) < r + 0.25 and z0 - 0.5 <= t.z <= z1:
                return False
        return True


# ------------------------------------------------------------------------------------------------ one canopy
def build_canopy(isl, ol, cols_x, yc_fn, deck_z, M, obs, rep):
    style = STYLE[isl]
    zt = ol.zt
    zd = zt - DECK_T                     # underside of the deck
    zp = zd - PURLIN_D                   # underside of the purlins
    mb_s, mb_d, mb_l, mb_c = L.MeshBuilder(), L.MeshBuilder(), L.MeshBuilder(), L.MeshBuilder()
    I = {"cream": 0, "deck": 1, "roof": 2, "sky": 3, "dark": 4, "housing": 5, "pipe": 6}
    IC = {"col": 0, "red": 1, "white": 2, "pipe": 3, "cream": 4}
    xs = np.arange(ol.x0, ol.x1 + 1e-6, 1.0)
    if xs[-1] < ol.x1 - 1e-3:
        xs = np.append(xs, ol.x1)
    yw, ye = ol.yw(xs), ol.ye(xs)
    width = float(np.median(ye - yw))
    # ---- deck (top keeps the old roof surface; skylight gap on 7-8)
    gaps = [(0.0, 1.0)] if style != "skylight" else [(0.0, 0.5 - SKY_W / 2 / width), (0.5 + SKY_W / 2 / width, 1.0)]
    for fa, fb in gaps:
        V, F, FM = [], [], []
        for i, x in enumerate(xs):
            a = yw[i] + (ye[i] - yw[i]) * fa; b = yw[i] + (ye[i] - yw[i]) * fb
            V += [(x, a, zd), (x, b, zd), (x, b, zt), (x, a, zt)]
        for i in range(len(xs) - 1):
            p, q = 4 * i, 4 * (i + 1)
            mb_d.add([V[p], V[p + 1], V[q + 1], V[q]], [(0, 3, 2, 1)], I["deck"])        # underside (faces down)
            mb_d.add([V[p + 3], V[p + 2], V[q + 2], V[q + 3]], [(0, 1, 2, 3)], I["roof"])  # top
            mb_d.add([V[p], V[p + 3], V[q + 3], V[q]], [(0, 1, 2, 3)], I["cream"])         # west face
            mb_d.add([V[p + 1], V[q + 1], V[q + 2], V[p + 2]], [(0, 1, 2, 3)], I["cream"])  # east face
        n = 4 * (len(xs) - 1)
        mb_d.add([V[0], V[1], V[2], V[3]], [(0, 1, 2, 3)], I["cream"])
        mb_d.add([V[n + 3], V[n + 2], V[n + 1], V[n]], [(0, 1, 2, 3)], I["cream"])
    if style == "skylight":
        # translucent barrel over the gap, with upstands
        nseg = 8
        for i in range(len(xs) - 1):
            ring = []
            for x in (xs[i], xs[i + 1]):
                c = 0.5 * (ol.yw(x) + ol.ye(x))
                ring.append([(x, c + (SKY_W / 2 + 0.05) * math.cos(math.pi * k / nseg),
                              zt + 0.12 + 0.40 * math.sin(math.pi * k / nseg)) for k in range(nseg + 1)])
            V = ring[0] + ring[1]
            F = [(k, k + 1, nseg + 2 + k, nseg + 1 + k) for k in range(nseg)]
            mb_d.add(V, F, I["sky"])
        for s in (-1, 1):
            ys_ = 0.5 * (yw + ye) + s * (SKY_W / 2 + 0.05)
            sweep(mb_s, xs, ys_, zp, zt + 0.12, 0.04, I["cream"])
        # bright strip under the skylight seen from below
    # ---- purlins
    nP = max(2, int(round(width / PURLIN_STEP)))
    for j in range(1, nP):
        f = j / nP
        if style == "skylight" and abs(f - 0.5) * width < SKY_W / 2 + 0.1:
            continue
        sweep(mb_s, xs, yw + (ye - yw) * f, zp, zd, 0.035, I["cream"])
    # ---- edge girders, fascia, gutters
    for f, s in ((0.0, 1), (1.0, -1)):
        yy = yw + (ye - yw) * f
        tx = np.gradient(xs); ty_ = np.gradient(yy); ln = np.hypot(tx, ty_); nx, ny = -ty_ / ln, tx / ln
        sweep(mb_s, xs + nx * s * 0.14, yy + ny * s * 0.14, zd - EDGE_D, zd, 0.10, I["cream"])          # edge girder
        sweep(mb_s, xs - nx * s * 0.01, yy - ny * s * 0.01, zd - 0.10, zt + 0.05, 0.012, I["cream"])     # fascia
        sweep(mb_s, xs - nx * s * 0.11, yy - ny * s * 0.11, zd - 0.12, zd - 0.10, 0.09, I["pipe"])       # gutter sole
        sweep(mb_s, xs - nx * s * 0.20, yy - ny * s * 0.20, zd - 0.12, zt - 0.02, 0.008, I["pipe"])      # gutter lip
    # ---- main frames: every old column bay divided in COL_SUB
    cols_x = sorted(cols_x)
    stations = []
    for a, b in zip(cols_x[:-1], cols_x[1:]):
        for k in range(COL_SUB):
            stations.append((a + (b - a) * k / COL_SUB, k == 0))
    if cols_x:
        stations.append((cols_x[-1], True))
        # beyond the outer columns, continue at the same spacing to the slab ends
        step = (cols_x[1] - cols_x[0]) / COL_SUB if len(cols_x) > 1 else 9.33
        x = cols_x[0] - step
        while x > ol.x0 + 1.0:
            stations.append((x, False)); x -= step
        x = cols_x[-1] + step
        while x < ol.x1 - 1.0:
            stations.append((x, False)); x += step
    stations = sorted(s for s in stations if ol.x0 + 0.3 < s[0] < ol.x1 - 0.3)
    main_x = [s[0] for s in stations]
    for x, old in stations:
        a, b = float(ol.yw(x)), float(ol.ye(x))
        c = 0.5 * (a + b)
        if style in ("plain", "skylight"):
            d = MAIN_D[style]
            hbox(mb_s, x, a + 0.05, b - 0.05, zp - 0.02, zp, 0.22, I["cream"])          # top flange
            hbox(mb_s, x, a + 0.05, b - 0.05, zp - d, zp - d + 0.022, 0.22, I["cream"])  # bottom flange
            hbox(mb_s, x, a + 0.05, b - 0.05, zp - d, zp, 0.014, I["cream"])            # web
            for yy in np.linspace(a + 0.4, b - 0.4, 7):                                  # web stiffeners
                hbox(mb_s, x, yy - 0.006, yy + 0.006, zp - d, zp, 0.20, I["cream"])
        elif style == "haunched":
            dc, de = MAIN_D[style]
            prism_yz(mb_s, x, 0.014, [(a + 0.05, zp), (b - 0.05, zp), (b - 0.05, zp - de), (c, zp - dc), (a + 0.05, zp - de)],
                     I["cream"])
            hbox(mb_s, x, a + 0.05, b - 0.05, zp - 0.022, zp, 0.24, I["cream"])
            for s0, s1 in ((a + 0.05, c), (c, b - 0.05)):                                # sloping bottom flange
                z0 = zp - (de if s0 < c - 1e-6 else dc); z1 = zp - (dc if s0 < c - 1e-6 else de)
                p0 = Vector((x, s0, z0)); p1 = Vector((x, s1, z1))
                dirv = (p1 - p0); ln = dirv.length; dirv.normalize()
                up = Vector((0, -dirv.z, dirv.y))
                fr = Matrix(((1, 0, 0, x), (0, dirv.y, up.y, (p0.y + p1.y) / 2), (0, dirv.z, up.z, (p0.z + p1.z) / 2), (0, 0, 0, 1)))
                L.box(mb_s, 0, 0, 0, 0.24, ln, 0.022, I["cream"], frame=fr)
        elif style == "lattice":
            d = MAIN_D[style]
            hbox(mb_s, x, a + 0.05, b - 0.05, zp - 0.10, zp, 0.20, I["cream"])          # top chord
            hbox(mb_s, x, a + 0.25, b - 0.25, zp - d, zp - d + 0.10, 0.20, I["cream"])   # bottom chord
            n = max(4, int(round((b - a - 0.5) / 0.75)))
            ys_ = np.linspace(a + 0.25, b - 0.25, n + 1)
            for k in range(n + 1):
                hbox(mb_s, x, ys_[k] - 0.03, ys_[k] + 0.03, zp - d + 0.1, zp - 0.1, 0.12, I["cream"])   # verticals
            for k in range(n):
                p, q = (ys_[k], zp - d + 0.1), (ys_[k + 1], zp - 0.1)
                if k % 2:
                    p, q = (ys_[k], zp - 0.1), (ys_[k + 1], zp - d + 0.1)
                rod(mb_s, (x - 0.05, p[0], p[1]), (x - 0.05, q[0], q[1]), 0.025, I["cream"])
                rod(mb_s, (x + 0.05, p[0], p[1]), (x + 0.05, q[0], q[1]), 0.025, I["cream"])
            # rivet plates at the ends
            for yy in (a + 0.25, b - 0.25):
                hbox(mb_s, x, yy - 0.15, yy + 0.15, zp - d, zp, 0.22, I["cream"])
    # ---- secondary beams between main frames
    allx = sorted(main_x)
    sec_x = []
    for a, b in zip(allx[:-1], allx[1:]):
        for k in range(1, SEC_SUB):
            sec_x.append(a + (b - a) * k / SEC_SUB)
    for x in sec_x:
        a, b = float(ol.yw(x)), float(ol.ye(x))
        hbox(mb_s, x, a + 0.1, b - 0.1, zp - SEC_D, zp, 0.10, I["cream"])
    # ---- columns (old positions + free intermediate stations), knee braces, down-pipes, guard bands
    ncol, skipped = 0, 0
    col_stations = []
    for x, old in stations:
        y = float(yc_fn(x))
        if old:
            col_stations.append((x, y, True)); continue
        placed = False
        for dx in (0.0, 0.8, -0.8, 1.6, -1.6):
            if obs.free(x + dx, y, deck_z + 0.05, zp, 0.55):
                col_stations.append((x + dx, y, False)); placed = True
                break
        if not placed:
            skipped += 1
    beam_bot = zp - (MAIN_D[style] if style != "haunched" else MAIN_D[style][0])
    for x, y, old in col_stations:
        prof = [(COL_R + 0.10, deck_z), (COL_R + 0.10, deck_z + 0.025), (COL_R + 0.02, deck_z + 0.025),
                (COL_R + 0.02, deck_z + 0.10), (COL_R, deck_z + 0.12), (COL_R, beam_bot), (COL_R + 0.06, beam_bot),
                (COL_R + 0.06, beam_bot + 0.03)]
        L.lathe(mb_c, prof, (x, y), segments=20, mat=IC["col"], cap_top=True, cap_bottom=True)
        # red-white guard band (diagonal look approximated by short rings)
        for k in range(8):
            z0 = deck_z + 1.10 + k * 0.10
            L.lathe(mb_c, [(COL_R + 0.008, z0), (COL_R + 0.008, z0 + 0.10)], (x, y), segments=20,
                    mat=IC["red"] if k % 2 == 0 else IC["white"], smooth=True)
        # down-pipe beside the column, swept to the gutter line under the beam
        py = y + 0.32
        rod(mb_c, (x + 0.0, py, deck_z + 0.05), (x, py, beam_bot - 0.05), 0.05, IC["pipe"], sides=10)
        rod(mb_c, (x, py, beam_bot - 0.05), (x, py + 0.6, zd - 0.15), 0.05, IC["pipe"], sides=10)
        L.box(mb_c, x, py, deck_z + 0.10, 0.18, 0.18, 0.20, IC["pipe"])                 # shoe
        # knee braces to the main beam
        for s in (-1, 1):
            rod(mb_c, (x, y + s * COL_R, beam_bot - 0.9), (x, y + s * 1.5, beam_bot + 0.01), 0.045, IC["cream"], sides=8)
        ncol += 1
    # ---- light fittings in two rows, cable trays, loudspeakers, cameras
    masts = obs.mast_xy
    nlamp = 0
    zl = zp - 0.62 if style != "lattice" else zp - MAIN_D["lattice"] - 0.12
    for f in (0.27, 0.73):
        for a, b in zip(allx[:-1], allx[1:]):
            for k in range(SEC_SUB):
                x = a + (b - a) * (k + 0.5) / SEC_SUB
                y = float(ol.at(x, f))
                if masts is not None and len(masts) and np.min(np.hypot(masts[:, 0] - x, masts[:, 1] - y)) < 0.9:
                    continue
                L.box(mb_l, x, y, zl + 0.05, 1.25, 0.16, 0.07, I["housing"])
                L.box(mb_l, x, y, zl + 0.012, 1.18, 0.11, 0.02, 7)
                for dx in (-0.45, 0.45):
                    rod(mb_l, (x + dx, y, zl + 0.085), (x + dx, y, zp), 0.006, I["dark"], sides=4)
                nlamp += 1
    zt_tray = zp - 0.40 if style != "lattice" else zp - MAIN_D["lattice"] + 0.12
    for f in (0.11, 0.89):
        yy = yw + (ye - yw) * f
        sweep(mb_s, xs, yy, zt_tray - 0.01, zt_tray, 0.15, I["pipe"])
        tx = np.gradient(xs); ty_ = np.gradient(yy); ln = np.hypot(tx, ty_); nx, ny = -ty_ / ln, tx / ln
        for s in (-1, 1):
            sweep(mb_s, xs + nx * s * 0.15, yy + ny * s * 0.15, zt_tray - 0.01, zt_tray + 0.07, 0.006, I["pipe"])
        sweep(mb_s, xs, yy, zt_tray + 0.005, zt_tray + 0.05, 0.11, I["dark"])          # cables in the tray
        for x in sec_x[::2]:
            y = float(np.interp(x, xs, yy))
            for s in (-1, 1):
                rod(mb_s, (x, y + s * 0.16, zt_tray - 0.01), (x, y + s * 0.16, zp), 0.008, I["dark"], sides=4)
    nspk = 0
    for i, x in enumerate(allx):
        if i % 2:
            continue
        for f in (0.38, 0.62):
            y = float(ol.at(x, f)) + 0.0
            L.box(mb_s, x + 0.25, y, zp - 0.55, 0.22, 0.30, 0.20, I["dark"])          # loudspeaker
            rod(mb_s, (x + 0.25, y, zp - 0.45), (x + 0.25, y, zp), 0.01, I["dark"], sides=4)
            nspk += 1
        if i % 6 == 0:
            y = float(ol.at(x, 0.5))
            L.box(mb_s, x + 0.6, y, zp - 0.30, 0.16, 0.16, 0.10, I["dark"])           # CCTV camera
            L.lathe(mb_s, [(0.0, zp - 0.46), (0.07, zp - 0.42), (0.08, zp - 0.35), (0.0, zp - 0.35)], (x + 0.6, y),
                    segments=12, mat=I["dark"], smooth=True)
    rep.update({"style": style, "x": [round(ol.x0, 1), round(ol.x1, 1)], "width_m": round(width, 2),
                "main_frames": len(stations), "secondary_beams": len(sec_x), "purlins": nP - 1,
                "columns": ncol, "columns_old_positions": sum(1 for c in col_stations if c[2]),
                "intermediate_columns_skipped": skipped, "light_fittings": nlamp, "loudspeakers": nspk,
                "z_top": round(zt, 3), "z_lowest_member": round(min(zl, zp - (MAIN_D[style] if style != 'haunched' else MAIN_D[style][0])), 3),
                "headroom_m": round(min(zl, beam_bot) - deck_z, 2)})
    return mb_s, mb_d, mb_l, mb_c, I, IC


# ------------------------------------------------------------------------------------------------ main
def run():
    sc = bpy.context.scene
    M = materials()
    obs = Obstacles(sc)
    mo = bpy.data.objects.get("V6 OCS | masts")
    if mo is not None:
        W = world_verts(mo)
        # mast axes: cluster mast vertices in plan (0.5 m grid)
        key = np.round(W[:, :2] / 0.5).astype(int)
        u, inv = np.unique(key, axis=0, return_inverse=True)
        cnt = np.bincount(inv.ravel())
        obs.mast_xy = (u[cnt > 8] * 0.5).astype(float)
    else:
        obs.mast_xy = None
    hc = L.collection("V8_Replaced_V7_hidden", hide_render=True); hc.hide_viewport = True
    col = L.collection("V8_Platform_Canopies")
    retired = 0
    deck_of = {"01-02": 16.51}
    all_cols = [o for o in sc.objects if o.name.startswith("V3 platform column") and o.visible_get()]
    col_pos = []
    for o in all_cols:
        W = world_verts(o)
        col_pos.append((o, float(W[:, 0].mean()), float(W[:, 1].mean()), float(W[:, 2].min()), float(W[:, 2].max())))
    strips = [o for o in sc.objects if o.name.startswith("V3 platform strip light") and o.visible_get()]
    for isl in ISLANDS:
        slabs = [o for o in sc.objects if re.match(r"V3 platform canopy %s(\.\d+)?$" % isl, o.name) and o.visible_get()]
        if not slabs:
            REP["warnings"].append(f"{isl}: no canopy slab"); continue
        deck_z = deck_of.get(isl, 6.21)
        rep_i = {"parts": []}
        # columns of this island: inside any of its slabs' footprints
        ols0 = []
        for s in slabs:
            W = world_verts(s)
            ols0.append((float(W[:, 0].min()), float(W[:, 0].max()), float(W[:, 1].min()), float(W[:, 1].max())))
        zt_isl = float(world_verts(slabs[0])[:, 2].max())
        mine = [c for c in col_pos if any(a - 1 <= c[1] <= b + 1 and ya <= c[2] <= yb_ for a, b, ya, yb_ in ols0)
                and abs(c[4] - (zt_isl - 0.10)) < 0.5]
        if len(mine) < 2:
            REP["warnings"].append(f"{isl}: only {len(mine)} columns found"); continue
        mx = np.array([c[1] for c in mine]); my = np.array([c[2] for c in mine]); o_ = np.argsort(mx)
        mx, my = mx[o_], my[o_]

        def yc_fn(x, mx=mx, my=my):
            return np.interp(x, mx, my)
        mbs = []
        for s in slabs:
            ol = Outline(s, yc_fn)
            cx = [float(x) for x in mx if ol.x0 - 0.5 <= x <= ol.x1 + 0.5]
            rp = {}
            mbs.append(build_canopy(isl, ol, cx, yc_fn, deck_z, M, obs, rp))
            rep_i["parts"].append(rp)
            # sign fixing blocks above rods that ended at the old underside
            rp["sign_fixings"] = 0
            for o in sc.objects:
                if o.type != 'MESH' or not o.visible_get():
                    continue
                if not re.match(r"V5 platform %s furniture|V6 platform signs|V6 platform \| clocks" % isl, o.name):
                    continue
                W = world_verts(o)
                sel = (np.abs(W[:, 2] - ol.zu) < 0.02) & (W[:, 0] > ol.x0) & (W[:, 0] < ol.x1)
                if not sel.any():
                    continue
                P = W[sel]
                key = np.round(P[:, :2] / 0.15).astype(int)
                u = np.unique(key, axis=0)
                for k in u:
                    x, y = k * 0.15
                    L.box(mbs[-1][0], x, y, (ol.zu + ol.zt - DECK_T) / 2, 0.12, 0.12, ol.zt - DECK_T - ol.zu, mbs[-1][4]["dark"])
                    rp["sign_fixings"] += 1
            # retire the slab, its strip lights
            for c in list(s.users_collection):
                c.objects.unlink(s)
            hc.objects.link(s); s.hide_render = True; s.hide_viewport = True; s["V8_retired"] = True
            retired += 1
            for st in strips:
                W = world_verts(st)
                if ol.x0 - 1 <= W[:, 0].mean() <= ol.x1 + 1 and ol.yw(W[:, 0].mean()) - 0.5 <= W[:, 1].mean() <= ol.ye(W[:, 0].mean()) + 0.5 \
                        and abs(W[:, 2].max() - ol.zu) < 0.2 and st.users_collection and st.users_collection[0] != hc:
                    for c in list(st.users_collection):
                        c.objects.unlink(st)
                    hc.objects.link(st); st.hide_render = True; st.hide_viewport = True; st["V8_retired"] = True
                    retired += 1
        # old 0.24 m posts of this island
        for c in mine:
            o = c[0]
            for cc in list(o.users_collection):
                cc.objects.unlink(o)
            hc.objects.link(o); o.hide_render = True; o.hide_viewport = True; o["V8_retired"] = True
            retired += 1
        # build objects (one set per island)
        mats_s = [M["cream"], M["deck"], M["roof"], M["sky"], M["dark"], M["housing"], M["pipe"], M["lamp"]]
        mats_c = [M["col"], M["red"], M["white"], M["pipe"], M["cream"]]
        names = ("structure (beams, purlins, gutters, trays, speakers)", "roof deck and skylight", "light fittings", "columns")
        for k, nm in enumerate(names):
            mb = L.MeshBuilder()
            for part in mbs:
                src = part[k]
                o0 = len(mb.v)
                mb.v.extend(src.v); mb.uv.extend(src.uv); mb.mi.extend(src.mi); mb.sm.extend(src.sm)
                mb.f.extend([[i + o0 for i in f] for f in src.f])
            if not mb.f:
                continue
            ob = mb.build(f"V8 canopy {isl} | {nm}", col, mats_c if k == 3 else mats_s)
            ob["V8_canopy"] = isl
        rep_i["columns_found"] = len(mine)
        REP["islands"][isl] = rep_i
    REP["retired_objects"] = retired
    sc["V8_canopies"] = json.dumps({k: {kk: vv for kk, vv in v.items()} for k, v in REP["islands"].items()})
    return REP


rep = run()
for k, v in rep["islands"].items():
    L.log(k, [{kk: vv for kk, vv in p.items()} for p in v["parts"]])
L.log("retired", rep["retired_objects"], "warnings", rep["warnings"])
if REPORT:
    json.dump(rep, open(REPORT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
if OUT:
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=True)
    L.log("saved", OUT)
