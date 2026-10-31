"""V6 module 1: overhead contact line (OCS) rebuilt from the track centrelines.

Why (round-6 feedback "导线的位置有点错误"):
  The V3 catenary was mapped vertex by vertex during the V5 re-layout.  The wires stayed on their tracks, but
  everything that should hold them did not follow:
    * every messenger hung 0.30 m below its suspension insulator (214 of 214 supports: nothing held the wire)
    * the slanted registration arms floated beside the contact wire (up to 0.23 m off it) and were attached
      to nothing at the top
    * every portal spanned one island only, so two masts stood side by side in the 4-5 m space between
      neighbouring islands, 1.85 m from the track centres
    * the portals ran under the new Shinkansen roofs although the roof girders are right above the wires
    * the contact wire and messenger of tracks 20-23 ran on for 36 m past the buffer stops
    * between supports the wire followed the curved track exactly (17 points per span); a real contact
      wire is straight between registration points, so on curves the supports have to come closer together

What this module does
  * retires all V3 catenary parts (wires, droppers, portals, lattice, insulators, arms) into a hidden collection
  * per track: registration points at the supports, straight contact wire between them, zig-zag stagger of
    +-0.20 m on straight track, pull-off to the outside on curves; spans are subdivided until the wire stays
    within 0.30 m of the track centre everywhere (pantograph working width)
  * messenger 1.10 m above the contact wire at the supports with a parabolic sag (0.30 m on a 44 m span),
    vertical droppers every 5 m
  * supports
      - conventional and Chuo tracks: steel masts (dia 0.35 m) on the island platforms (through the canopy) or
        in gaps wide enough for the structure gauge (>= 2.3 m from a conventional track centre, >= 2.6 m from a
        Shinkansen track centre), V-truss beams between masts, cantilever beams over outer tracks
      - track 3 under the Chuo viaduct: drop tubes from the viaduct soffit
      - Shinkansen tracks under the V5 roofs: drop tubes from the transverse roof girders
    each support carries a messenger suspension (rod, 3-disc insulator string, clamp ON the messenger) and a
    steady arm (drop tube, long-rod insulator, arm clamped ON the contact wire)
  * contact wire height per track = top of the raised pantograph shoes on that track (shoes touch the wire)
  * wires end at the buffer stops of tracks 20-23 (terminal support with strain insulators)

usage: blender -b in.blend --python-exit-code 1 -P mod6_catenary.py -- out.blend [report.json]
"""
import sys, os, json, math, re
import numpy as np
import bpy
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v5lib as L

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGV[0] if ARGV else None
REPORT = ARGV[1] if len(ARGV) > 1 else None

D = json.load(open(os.path.join(HERE, "targets.json")))
GX = np.array(D["X"], float)
ORDER = D["order"]
TGT = {k: np.array(D["target"][k], float) for k in ORDER}
ISL = D["islands"]
SHIN = {"14", "15", "16", "17", "18", "19", "20", "21", "22", "23"}
CHUO = {"01", "02"}
TERMINAL = {"20", "21", "22", "23"}          # Tohoku Shinkansen: buffer stops, wires end there

R_CW, R_MS = 0.0075, 0.0070                   # wire radii (12-15 mm real, drawn slightly thicker)
SYS_H = 1.10                                  # messenger above contact wire at the supports
SAG_44 = 0.30                                 # messenger sag on a 44 m span (scaled with span^2)
STAGGER = 0.20
MAX_DEV = 0.28                                # allowed wire offset from the track centre
CLR = {False: 2.30, True: 2.60}               # mast face clearance from track centre (conventional / Shinkansen)
MAST_R = 0.175
BEAM_H = 0.55                                 # V-truss depth
BEAM_ZB = 12.45                               # bottom chord, ground level (Chuo +10.30)
CHUO_DZ = 10.30
STATIONS0 = [-202.0 + 44.0 * i for i in range(11)]
STATS = {"retired_v3_parts": 0}


# ------------------------------------------------------------------------------------------------ track geometry
class Track:
    def __init__(self, k, x0, x1, zr):
        self.k, self.x0, self.x1, self.zr = k, x0, x1, zr
        self.shin = k in SHIN
        self.chuo = k in CHUO
        self.xs = np.arange(x0, x1 + 1e-6, 0.25)
        self.ys = np.interp(self.xs, GX, TGT[k])
        self.s = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(self.xs), np.diff(self.ys)))])
        self.th = np.unwrap(np.arctan2(np.gradient(self.ys), np.gradient(self.xs)))

    def y(self, x):
        return float(np.interp(x, GX, TGT[self.k]))

    def P(self, x):
        return np.array([x, self.y(x)])

    def ang(self, x):
        return float(np.interp(x, self.xs, self.th))

    def N(self, x):                          # left normal (toward +y when running toward +x)
        a = self.ang(x)
        return np.array([-math.sin(a), math.cos(a)])

    def kappa(self, x, h=12.0):
        xa, xb = max(self.x0, x - h), min(self.x1, x + h)
        sa, sb = np.interp([xa, xb], self.xs, self.s)
        if sb - sa < 1.0:
            return 0.0
        return (self.ang(xb) - self.ang(xa)) / (sb - sa)


def rails_extent():
    ext = {}
    for o in bpy.data.objects:
        m = re.match(r"V5 track \| Track (\d\d) rails", o.name)
        if m and o.type == 'MESH':
            V = world_verts(o)
            ext[m.group(1)] = (float(V[:, 0].min()), float(V[:, 0].max()), float(V[:, 2].max()))
    return ext


def world_verts(o):
    n = len(o.data.vertices)
    co = np.empty(n * 3); o.data.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    mw = np.array(o.matrix_world)
    return co @ mw[:3, :3].T + mw[:3, 3]


# ------------------------------------------------------------------------------------------------ scene helpers
OCS_V3 = re.compile(r"^V3 (Track \d\d (contact wire|messenger|catenary dropper)|catenary portal mast|catenary portal crossbeam|"
                    r"portal lattice web|catenary insulator stem|porcelain insulator disc|catenary registration arm)")


def retire_v3():
    hc = L.collection("V6_Replaced_V5_hidden", hide_render=True)
    hc.hide_viewport = True
    n = 0
    for o in list(bpy.data.objects):
        if OCS_V3.match(o.name):
            for c in list(o.users_collection):
                c.objects.unlink(o)
            hc.objects.link(o)
            o.hide_render = True; o.hide_viewport = True
            o["V6_retired"] = True
            n += 1
    STATS["retired_v3_parts"] = n


HIDDEN_FOR_RAYS = []


def hide_for_rays():
    """Trains, people and anything retired must not stop the support rays."""
    for o in bpy.data.objects:
        if o.hide_viewport:
            continue
        if (o.instance_type == 'COLLECTION' or o.get("V5_retired") or o.get("V6_retired")
                or o.type not in ('MESH',) or o.name.startswith("V6 OCS")):
            o.hide_viewport = True
            HIDDEN_FOR_RAYS.append(o)
    bpy.context.view_layer.update()


def restore_hidden():
    for o in HIDDEN_FOR_RAYS:
        o.hide_viewport = False
    for o in bpy.data.objects:                       # retired objects stay hidden
        if o.get("V6_retired") or o.get("V5_retired"):
            o.hide_viewport = True


def ray(origin, d, dist):
    dg = bpy.context.evaluated_depsgraph_get()
    hit, loc, nor, idx, ob, mw = bpy.context.scene.ray_cast(dg, Vector(origin), Vector(d), distance=dist)
    return (loc, ob) if hit else (None, None)


ROOFLIKE = re.compile(r"(?i)canopy|roof|hanger rods|furniture and signs|strip light")


def ceiling_above(x, y, z0, reach):
    """First structure above (x, y, z0) within reach that is not a platform canopy (z of its underside)."""
    z = z0
    while True:
        loc, ob = ray((x, y, z), (0, 0, 1), reach - (z - z0))
        if loc is None:
            return None, None
        if re.search(r"(?i)platform canopy|furniture and signs|strip light", ob.name):
            z = loc.z + 0.02
            continue
        return loc.z, ob.name


def solid_above(x, y, z0, reach):
    """First thing above (x, y, z0) that a mast may not pass through (only platform canopy roofs are skipped)."""
    z = z0
    while True:
        loc, ob = ray((x, y, z), (0, 0, 1), reach - (z - z0))
        if loc is None:
            return None, None
        if re.match(r"V3 platform canopy \d", ob.name):
            z = loc.z + 0.02
            continue
        return loc.z, ob.name


def ground_below(x, y, ztop, zmin):
    """Floor under a mast (skips canopies and hanging things); returns (z, object name) or (None, None)."""
    z = ztop
    for _ in range(12):
        loc, ob = ray((x, y, z), (0, 0, -1), z - zmin + 0.5)
        if loc is None:
            return None, None
        if ROOFLIKE.search(ob.name) or "signal" in ob.name.lower():
            z = loc.z - 0.02
            continue
        return loc.z, ob.name
    return None, None


class Obstacles:
    """Plan-view grid of static vertices (furniture, columns, signals, piers ...) with their heights."""

    def __init__(self):
        skip = re.compile(r"^V5 track \||ballast|sleeper|raised deck|Deck_infill|deck infill|Site ground|Display base|"
                          r"perimeter|walkway|curved viaduct|platform canopy \d|V5 Shinkansen roof \d|tactile|coping|"
                          r"Platform_longitudinal_risers|Piers_caps_foundations")
        pts = []
        for o in bpy.data.objects:
            if o.type != 'MESH' or not o.visible_get() or o.hide_render or skip.search(o.name):
                continue
            if len(o.data.vertices) == 0:
                continue
            V = world_verts(o)
            sel = (V[:, 0] > -215) & (V[:, 0] < 250) & (V[:, 1] > 5) & (V[:, 1] < 215) & (V[:, 2] > 3.0) & (V[:, 2] < 26)
            if sel.any():
                pts.append(V[sel])
        P = np.concatenate(pts)
        self.cell = 1.0
        keys = np.floor(P[:, :2] / self.cell).astype(np.int64)
        order = np.lexsort((keys[:, 1], keys[:, 0]))
        P, keys = P[order], keys[order]
        self.grid = {}
        uk, start = np.unique(keys, axis=0, return_index=True)
        ends = list(start[1:]) + [len(P)]
        for (a, b), s0, s1 in zip(uk, start, ends):
            self.grid[(int(a), int(b))] = P[s0:s1]
        L.log("obstacle points", len(P))
        # stairwells, hanging signs and clocks of mod6_platforms (a hole in the deck has no vertices to see)
        self.keep = json.loads(bpy.context.scene.get("V6_platform_keepouts", "[]"))
        L.log("platform keep-outs", len(self.keep))

    def in_keepout(self, x, y, z0, z1, r):
        for k in self.keep:
            if k["z1"] < z0 or k["z0"] > z1:
                continue
            ux, uy = k["u"]
            du = (x - k["c"][0]) * ux + (y - k["c"][1]) * uy
            dv = -(x - k["c"][0]) * uy + (y - k["c"][1]) * ux
            if k["u0"] - r <= du <= k["u1"] + r and abs(dv) <= k["hv"] + r:
                return True
        return False

    def clear(self, x, y, z0, z1, r):
        if self.in_keepout(x, y, z0 - 4.0, z1, r):
            return False
        cx, cy = int(math.floor(x / self.cell)), int(math.floor(y / self.cell))
        n = int(math.ceil(r / self.cell))
        for i in range(cx - n, cx + n + 1):
            for j in range(cy - n, cy + n + 1):
                Q = self.grid.get((i, j))
                if Q is None:
                    continue
                d = np.hypot(Q[:, 0] - x, Q[:, 1] - y)
                if np.any((d < r) & (Q[:, 2] > z0) & (Q[:, 2] < z1)):
                    return False
        return True


# ------------------------------------------------------------------------------------------------ roof girders
def roof_data():
    info = json.loads(bpy.context.scene["V5_shinkansen_roofs"])
    out = {}
    for isl, v in info.items():
        if isl.startswith("_"):
            continue
        w, e = ISL[isl]["west"], ISL[isl]["east"]
        x0, x1 = v["x_extent"]
        cols = v["columns"]
        girders = []
        for cx, cy in cols:
            yw = lambda x: float(np.interp(x, GX, TGT[w])); ye = lambda x: float(np.interp(x, GX, TGT[e]))
            c = lambda x: 0.5 * (yw(x) + ye(x))
            a = math.atan2(c(cx + 0.5) - c(cx - 0.5), 1.0)
            girders.append((cx, cy, a))
        out[isl] = {"x0": x0, "x1": x1, "zd": v["z_deck"], "girders": girders, "west": w, "east": e}
    return out


def line_track_x(T, p0, d, xlo, xhi):
    """x on track T where the line p0 + t*d (plan) crosses it; bisection on the signed side function."""
    def f(x):
        q = T.P(x) - p0
        return q[0] * d[1] - q[1] * d[0]
    a, b = max(T.x0, xlo), min(T.x1, xhi)
    fa, fb = f(a), f(b)
    if fa * fb > 0:
        return None
    for _ in range(60):
        m = 0.5 * (a + b); fm = f(m)
        if fa * fm <= 0:
            b, fb = m, fm
        else:
            a, fa = m, fm
    return 0.5 * (a + b)


# ------------------------------------------------------------------------------------------------ registration
def chord_dev(T, xa, xb, oa, ob, n=24):
    pa = T.P(xa) + oa * T.N(xa); pb = T.P(xb) + ob * T.N(xb)
    d = pb - pa; L_ = np.hypot(*d)
    if L_ < 1e-6:
        return 0.0
    u = d / L_
    worst = 0.0
    for t in np.linspace(0, 1, n):
        x = xa + (xb - xa) * t
        q = T.P(x) - pa
        s = q[0] * u[1] - q[1] * u[0]          # signed distance of the track point from the wire line
        worst = max(worst, abs(s))
    return worst


def registration(T, xs):
    """Offsets of the contact wire at the supports: zig-zag on straight track, pull-off outward on curves."""
    offs = []
    flip = 1.0
    for i, x in enumerate(xs):
        spans = []
        if i > 0:
            spans.append(xs[i] - xs[i - 1])
        if i < len(xs) - 1:
            spans.append(xs[i + 1] - xs[i])
        Lsp = max(spans) if spans else 44.0
        k = T.kappa(x)
        v = Lsp * Lsp * abs(k) / 8.0
        if v < 0.10:
            offs.append(flip * STAGGER); flip = -flip
        else:
            o = min(0.28, max(0.15, 0.5 * v + 0.03))
            offs.append(-math.copysign(o, k))
    return offs


def worst_spans(T, xs, offs):
    bad = []
    for i in range(len(xs) - 1):
        d = chord_dev(T, xs[i], xs[i + 1], offs[i], offs[i + 1])
        if d > MAX_DEV:
            bad.append((i, d))
    return bad


# ------------------------------------------------------------------------------------------------ geometry builders
class Parts:
    def __init__(self):
        self.mb = {k: L.MeshBuilder() for k in ("wire", "dropper", "mast", "beam", "fitting", "insulator")}


def tube(mb, a, b, r, sides=6, mat=0):
    L.tube(mb, [Vector(a), Vector(b)], r, sides=sides, mat=mat, smooth=True)


def frame_from(u):
    """Rotation whose x axis is the horizontal direction u (2D)."""
    a = math.atan2(u[1], u[0])
    return Matrix.Rotation(a, 4, 'Z')


def build_mast(P, x, y, zb, ztop, through=None):
    mb = P.mb["mast"]
    tube(mb, (x, y, zb), (x, y, ztop), MAST_R, sides=16)
    L.box(mb, x, y, zb + 0.03, 0.62, 0.62, 0.06)
    for dx, dy in ((0.24, 0.24), (-0.24, 0.24), (0.24, -0.24), (-0.24, -0.24)):
        tube(mb, (x + dx, y + dy, zb + 0.06), (x + dx, y + dy, zb + 0.13), 0.022, sides=6)
    tube(mb, (x, y, ztop), (x, y, ztop + 0.06), MAST_R + 0.03, sides=16)           # cap
    L.box(mb, x, y, zb + 1.9, 0.14, 0.012, 0.22)                                     # number plate (backing)
    if isinstance(through, tuple):                                                  # side-mounted on a viaduct deck
        inward = through[1]
        for z in (zb + 0.35, zb + 1.35):
            L.box(mb, x, y + inward * 0.55, z, 0.42, 1.0, 0.22)
    elif through is not None:                                                       # flashing collar on a canopy
        tube(mb, (x, y, through - 0.02), (x, y, through + 0.16), MAST_R + 0.07, sides=16)


def build_truss(P, A, B, zb, h=BEAM_H, half=0.26, panel=0.75):
    """V-truss: two top chords, one bottom chord, zig-zag webs on both faces, lacing between the top chords."""
    mb = P.mb["beam"]
    A = np.array(A, float); B = np.array(B, float)
    d = B - A; Ln = float(np.hypot(*d))
    if Ln < 0.5:
        return
    u = d / Ln; w = np.array([-u[1], u[0]])
    zt = zb + h
    def p3(t, off, z):
        q = A + u * t + w * off
        return (float(q[0]), float(q[1]), z)
    tube(mb, p3(0, 0, zb), p3(Ln, 0, zb), 0.045, sides=8)
    tube(mb, p3(0, -half, zt), p3(Ln, -half, zt), 0.042, sides=8)
    tube(mb, p3(0, half, zt), p3(Ln, half, zt), 0.042, sides=8)
    n = max(2, int(round(Ln / panel)))
    step = Ln / n
    for i in range(n):
        t0, t1, tm = i * step, (i + 1) * step, (i + 0.5) * step
        for off in (-half, half):
            tube(mb, p3(t0, 0, zb), p3(tm, off, zt), 0.017, sides=5)
            tube(mb, p3(tm, off, zt), p3(t1, 0, zb), 0.017, sides=5)
        tube(mb, p3(tm, -half, zt), p3(tm, half, zt), 0.014, sides=5)
    for t in (0.0, Ln):                                                             # end plates
        q = A + u * t
        L.box(mb, 0, 0, 0, 0.10, 2 * half + 0.12, h + 0.12, frame=Matrix.Translation((float(q[0]), float(q[1]), zb + h / 2)) @ frame_from(u))


def build_cantilever(P, A, B, zb, ztie):
    """Cantilever beam from a mast at A out to B, with a tie rod from the mast head when it is long."""
    build_truss(P, A, B, zb, h=0.45, half=0.20)
    A = np.array(A); B = np.array(B)
    if np.hypot(*(B - A)) > 3.5:
        q = A + (B - A) * 0.85
        tube(P.mb["beam"], (A[0], A[1], ztie), (q[0], q[1], zb + 0.45), 0.022, sides=6)


def insulator_string(P, x, y, ztop, zbot, discs=3):
    """Suspension insulator: core rod with porcelain discs, from ztop down to zbot."""
    mbI = P.mb["insulator"]; mbF = P.mb["fitting"]
    tube(mbF, (x, y, ztop), (x, y, zbot), 0.010, sides=6)
    span = ztop - zbot
    for i in range(discs):
        zc = ztop - span * (i + 0.7) / (discs + 0.4)
        L.lathe(mbI, [(0.012, -0.035), (0.085, -0.028), (0.090, -0.012), (0.030, 0.012), (0.012, 0.03)], (x, y),
                segments=14, cap_top=True, cap_bottom=True, frame=Matrix.Translation((x, y, zc)))


def longrod_insulator(P, a, b):
    """Long-rod insulator along a->b (polymer sheds)."""
    a = np.array(a, float); b = np.array(b, float)
    tube(P.mb["insulator"], a, b, 0.022, sides=8)
    d = b - a; n = 5
    for i in range(1, n):
        c = a + d * i / n
        tube(P.mb["insulator"], c - d * 0.012, c + d * 0.012, 0.055, sides=12)


def support_fittings(P, R, n_pull, cw_z, ms_z, z_top, kind, terminal=False, track_dir=None):
    """Messenger suspension and steady arm at registration point R (plan), hanging from z_top."""
    mbF = P.mb["fitting"]
    x, y = float(R[0]), float(R[1])
    # messenger: rod -> 3-disc string -> clamp around the messenger
    z_ins_top = ms_z + 0.62
    if z_top > z_ins_top + 0.02:
        tube(mbF, (x, y, z_top + 0.02), (x, y, z_ins_top), 0.014, sides=6)
        L.box(mbF, x, y, z_top - 0.02, 0.16, 0.16, 0.05)
    insulator_string(P, x, y, z_ins_top, ms_z + 0.10)
    L.box(mbF, x, y, ms_z + 0.035, 0.14, 0.05, 0.09, frame=Matrix.Translation((x, y, ms_z + 0.035)) @ frame_from(track_dir))
    # steady arm: drop tube at Q, long-rod insulator, arm down to a clamp on the contact wire
    Q = np.array(R) + 0.95 * np.array(n_pull)
    zq = cw_z + 0.34
    tube(mbF, (Q[0], Q[1], z_top + 0.02), (Q[0], Q[1], zq - 0.05), 0.024, sides=8)
    L.box(mbF, float(Q[0]), float(Q[1]), z_top - 0.02, 0.14, 0.14, 0.05)
    a = np.array([Q[0], Q[1], zq]); I_end = np.array([Q[0] - 0.38 * n_pull[0], Q[1] - 0.38 * n_pull[1], zq - 0.04])
    tube(mbF, (Q[0], Q[1], zq + 0.02), a - np.array([0.06 * n_pull[0], 0.06 * n_pull[1], 0.0]), 0.018, sides=6)
    longrod_insulator(P, a - np.array([0.06 * n_pull[0], 0.06 * n_pull[1], 0.0]), I_end)
    tube(mbF, I_end, (x, y, cw_z + R_CW + 0.012), 0.013, sides=6)
    L.box(mbF, x, y, cw_z, 0.10, 0.035, 0.035, frame=Matrix.Translation((x, y, cw_z + 0.004)) @ frame_from(track_dir))
    if terminal:                                                                     # strain insulators at the wire ends
        dd = np.array([track_dir[0], track_dir[1], 0.0])
        for z in (cw_z, ms_z):
            longrod_insulator(P, (x, y, z), np.array([x, y, z]) + 0.9 * dd)
            tube(mbF, np.array([x, y, z]) + 0.9 * dd, (Q[0] + 0.9 * dd[0], Q[1] + 0.9 * dd[1], min(z_top, z + 0.5)), 0.014)


# ------------------------------------------------------------------------------------------------ main
def run():
    retire_v3()
    ext = rails_extent()
    T = {}
    for k in ORDER:
        x0, x1, zr = ext[k]
        T[k] = Track(k, x0 + 0.2, x1 - 0.2, zr)
    # contact wire height per track: top of raised pantograph shoes on that track (shoes touch the wire)
    shoe = {}
    dg = bpy.context.evaluated_depsgraph_get()
    for inst in dg.object_instances:
        ob = inst.object
        if ob.type == 'MESH' and re.search(r"(?i)carbon_shoe|pantograph contact shoe", ob.name):
            mw = inst.matrix_world
            bb = [mw @ Vector(c) for c in ob.bound_box]
            c = sum(bb, Vector()) / 8; zt = max(v.z for v in bb)
            k = min(ORDER, key=lambda kk: abs(c.y - float(np.interp(c.x, GX, TGT[kk]))) + (0 if (zt > 15) == (kk in CHUO) else 99))
            shoe.setdefault(k, []).append(zt)
    CWZ = {}
    for k in ORDER:
        if k in shoe:
            CWZ[k] = round(max(shoe[k]) + R_CW, 4)
        else:
            CWZ[k] = (20.8725 if k in CHUO else (10.6075 if k in SHIN else 10.5725))
    L.log("contact wire heights", CWZ)

    roofs = roof_data()
    track_roof = {}
    for isl, r in roofs.items():
        track_roof[r["west"]] = isl; track_roof[r["east"]] = isl

    hide_for_rays()
    obst = Obstacles()

    def in_roof(k, x):
        isl = track_roof.get(k)
        return isl is not None and roofs[isl]["x0"] + 0.5 <= x <= roofs[isl]["x1"] - 0.5

    # ---- roof supports (girder intersections) per Shinkansen track
    roof_sup = {}
    for k, isl in track_roof.items():
        r = roofs[isl]; t = T[k]; pts = []
        for cx, cy, a in r["girders"]:
            d = np.array([-math.sin(a), math.cos(a)])
            x = line_track_x(t, np.array([cx, cy]), d, cx - 12, cx + 12)
            if x is None or not (r["x0"] + 0.5 <= x <= r["x1"] - 0.5) or not (t.x0 + 1 <= x <= t.x1 - 1):
                continue
            # girder underside at the track: linear from the monitor edge (7.25) to the eave (7.50)
            dw = abs((t.P(x) - np.array([cx, cy])) @ d)
            de = dw + 1.1
            fz = min(1.0, max(0.0, (dw - 3.4) / max(de - 0.15 - 3.4, 0.1)))
            zu = r["zd"] + 7.25 + 0.25 * fz
            pts.append((x, zu, (cx, cy, a)))
        pts.sort()
        roof_sup[k] = pts

    # ---- global stations for the beam / ceiling zones, refined until every span is within MAX_DEV
    stations = list(STATIONS0)

    def track_supports(k, stations):
        t = T[k]
        sup = []
        for X in stations:
            if t.x0 + 1.0 <= X <= t.x1 - 1.0 and not in_roof(k, X):
                sup.append(("st", X, None))
        if k in roof_sup:
            rs = roof_sup[k]
            if rs:
                # every 4th girder (48 m), subdivided later where curvature needs it
                chosen = set(range(0, len(rs), 4)) | {len(rs) - 1}
                for i in sorted(chosen):
                    sup.append(("roof", rs[i][0], i))
        sup.sort(key=lambda s: s[1])
        return sup

    SUP = {k: track_supports(k, stations) for k in ORDER}
    for it in range(8):
        add_st = []
        changed = False
        for k in ORDER:
            t = T[k]; sup = SUP[k]
            xs = [s[1] for s in sup]
            offs = registration(t, xs)
            for i, d in worst_spans(t, xs, offs):
                a, b = sup[i], sup[i + 1]
                if a[0] == "roof" and b[0] == "roof" and b[2] - a[2] > 1:
                    mid = (a[2] + b[2]) // 2
                    rs = roof_sup[k][mid]
                    SUP[k].append(("roof", rs[0], mid)); changed = True
                elif a[0] == "st" and b[0] == "st":
                    add_st.append(0.5 * (a[1] + b[1]))
                else:                                # mixed span at a roof edge: add the nearest girder or a station
                    if a[0] == "roof" and a[2] + 1 < len(roof_sup[k]) and roof_sup[k][a[2] + 1][0] < b[1] - 3:
                        rs = roof_sup[k][a[2] + 1]; SUP[k].append(("roof", rs[0], a[2] + 1)); changed = True
                    elif b[0] == "roof" and b[2] - 1 >= 0 and roof_sup[k][b[2] - 1][0] > a[1] + 3:
                        rs = roof_sup[k][b[2] - 1]; SUP[k].append(("roof", rs[0], b[2] - 1)); changed = True
            SUP[k] = sorted(set(SUP[k]), key=lambda s: s[1])
        new = [x for x in add_st if all(abs(x - s) > 4.0 for s in stations)]
        if new:
            merged = []
            for x in sorted(new):
                if merged and x - merged[-1] < 6.0:
                    merged[-1] = 0.5 * (merged[-1] + x)
                else:
                    merged.append(x)
            stations = sorted(stations + merged)
            for k in ORDER:
                keep_roof = [s for s in SUP[k] if s[0] == "roof"]
                SUP[k] = sorted(set(keep_roof + [s for s in track_supports(k, stations) if s[0] == "st"]), key=lambda s: s[1])
            changed = True
        if not changed:
            break
    L.log("stations", [round(s, 1) for s in stations])

    # ---- classify station supports: ceiling (structure above) or beam
    P = Parts()
    supports = {k: [] for k in ORDER}           # (x, kind, z_top, extra)
    for k in ORDER:
        t = T[k]
        for kind, x, gi in SUP[k]:
            if kind == "roof":
                rs = roof_sup[k][gi]
                supports[k].append([x, "roof", rs[1], None])
            else:
                z0 = CWZ[k] + SYS_H + 0.05
                zc, nm = ceiling_above(x, t.y(x), z0, 3.5)
                if zc is not None:
                    supports[k].append([x, "ceiling", zc, nm])
                else:
                    supports[k].append([x, "beam", None, None])

    # ---- masts and beams per station and level
    masts, beams, cants = [], [], []
    unsupported = []
    for X in stations:
        for level in ("ground", "chuo"):
            present = [k for k in ORDER if (k in CHUO) == (level == "chuo") and T[k].x0 - 0.5 <= X <= T[k].x1 + 0.5]
            if not present:
                continue
            present.sort(key=lambda k: T[k].y(X))
            need = {k for k in present if any(abs(s[0] - X) < 1e-6 and s[1] == "beam" for s in supports[k])}
            if not need:
                continue
            ys = [T[k].y(X) for k in present]
            zr = T[present[0]].zr
            zb = BEAM_ZB + (CHUO_DZ if level == "chuo" else 0.0)
            # candidate mast positions
            cands = []
            for i in range(len(present) - 1):
                ka, kb = present[i], present[i + 1]
                ya, yb = ys[i], ys[i + 1]
                need_w = CLR[T[ka].shin] + CLR[T[kb].shin] + 2 * MAST_R
                if yb - ya >= need_w:
                    lo, hi = ya + CLR[T[ka].shin] + MAST_R, yb - CLR[T[kb].shin] - MAST_R
                    cands.append((i + 0.5, lo, hi))
            ka, kb = present[0], present[-1]
            cands.append((-0.5, ys[0] - CLR[T[ka].shin] - MAST_R - 0.6, ys[0] - CLR[T[ka].shin] - MAST_R))
            cands.append((len(present) - 0.5, ys[-1] + CLR[T[kb].shin] + MAST_R, ys[-1] + CLR[T[kb].shin] + MAST_R + 0.6))
            placed = {}
            for pos, lo, hi in cands:
                ymid = 0.5 * (lo + hi)
                tries = [(0.0, 0.0)] + [(sg * dx, 0.0) for dx in range(1, 10) for sg in (1.0, -1.0)]
                if hi - lo > 1.0:
                    tries += [(dx, dy) for dx in (0.0, 1.5, -1.5) for dy in (-(hi - lo) / 3, (hi - lo) / 3)]
                for dx, dy in tries:
                    x, y = X + dx, ymid + dy
                    if not (lo - 1e-6 <= y <= hi + 1e-6):
                        continue
                    # structure-gauge clearance re-checked at the shifted position (tracks curve)
                    if any(T[kk].x0 - 1 <= x <= T[kk].x1 + 1 and abs(y - T[kk].y(x)) < CLR[T[kk].shin] + MAST_R - 1e-6
                           for kk in ORDER if (kk in CHUO) == (level == "chuo")):
                        continue
                    zg, gname = ground_below(x, y, zb - 0.5, zr - 3.0)
                    side = None
                    if (zg is None or not (zr - 1.3 <= zg <= zr + 1.6)) and level == "chuo" and pos in (-0.5, len(present) - 0.5):
                        # outer Chuo masts beyond the viaduct edge: mount on the side of the viaduct deck
                        inward = 1.0 if pos < 0 else -1.0
                        zd, dn = ground_below(x, y + inward * 1.1, zb - 0.5, zr - 3.0)
                        if zd is not None and zr - 1.3 <= zd <= zr + 0.2:
                            zg, gname, side = zd - 1.6, "side of " + dn, inward
                    if zg is None or not (zr - 1.3 - (1.6 if side else 0) <= zg <= zr + 1.6):
                        continue
                    if not obst.clear(x, y, zg + 0.15 + (1.6 if side else 0), zb + BEAM_H + 0.3, MAST_R + 0.35):
                        continue
                    # nothing solid in the mast's way (rays at the mast surface)
                    blocked = False
                    for ox, oy in ((0, 0), (MAST_R, 0), (-MAST_R, 0), (0, MAST_R), (0, -MAST_R)):
                        zc, nm = solid_above(x + ox, y + oy, zg + 0.2, zb + BEAM_H + 0.4 - zg)
                        if zc is not None:
                            blocked = True; break
                    if blocked:
                        continue
                    # canopy pierced by the mast?
                    loc, ob = ray((x, y, zg + 0.2), (0, 0, 1), zb - zg)
                    through = loc.z if (loc is not None and re.search(r"(?i)platform canopy", ob.name)) else None
                    placed[pos] = (x, y, zg, gname, through if side is None else ("side", side))
                    break
            # runs of consecutive beam-needing tracks (a ceiling/roof track in between breaks the run)
            runs, cur = [], []
            for i in range(len(present)):
                if present[i] in need:
                    cur.append(i)
                else:
                    if cur:
                        runs.append(cur); cur = []
            if cur:
                runs.append(cur)
            for run in runs:
                i0, i1 = run[0], run[-1]
                ms = sorted([p for p in placed if i0 - 0.5 <= p <= i1 + 0.5])
                if not ms:
                    for i in run:
                        unsupported.append((present[i], X));
                    continue
                used = set()
                for i in run:
                    k = present[i]
                    left = [p for p in ms if p < i]; right = [p for p in ms if p > i]
                    if left and right:
                        a, b = max(left), min(right)
                        beams.append((placed[a], placed[b], zb, level)); used |= {a, b}
                    else:
                        p = max(left) if left else min(right)
                        mx, my = placed[p][0], placed[p][1]
                        side = 1 if not right else -1          # cantilever direction in y
                        if abs(ys[i] - my) > 9.0:
                            unsupported.append((k, X)); continue
                        cants.append((placed[p], k, side, zb, level)); used.add(p)
                for p in used:
                    masts.append((placed[p], zb, level))

    # de-duplicate beams / masts
    def key3(m):
        return (round(m[0], 2), round(m[1], 2))
    mast_map = {}
    for (x, y, zg, gname, through), zb, level in masts:
        mast_map[key3((x, y))] = (x, y, zg, gname, through, zb, level)
    beam_set = {}
    for A, B, zb, level in beams:
        beam_set[(key3(A), key3(B))] = (A, B, zb, level)
    cant_ext = {}
    for Mm, k, side, zb, level in cants:
        kk = (key3(Mm), side)
        x = Mm[0]
        yk = T[k].y(x)
        cur = cant_ext.get(kk)
        reach = (yk + side * 1.0)
        if cur is None or (side > 0 and reach > cur[1]) or (side < 0 and reach < cur[1]):
            cant_ext[kk] = (Mm, reach, zb, level)

    # beams -> support points on each beam-supported track
    beam_lines = []
    for (A, B, zb, level) in beam_set.values():
        build_truss(P, (A[0], A[1]), (B[0], B[1]), zb)
        beam_lines.append(((A[0], A[1]), (B[0], B[1]), zb, level))
    for (Mm, reach, zb, level) in cant_ext.values():
        A = (Mm[0], Mm[1]); B = (Mm[0], reach)
        build_cantilever(P, A, B, zb, zb + BEAM_H + 1.2)
        beam_lines.append((A, B, zb, level))
    mast_top = {}
    for (Mm, reach, zb, level) in cant_ext.values():
        mast_top[key3((Mm[0], Mm[1]))] = zb + BEAM_H + 1.35
    for kq, (x, y, zg, gname, through, zb, level) in mast_map.items():
        build_mast(P, x, y, zg, mast_top.get(kq, zb + BEAM_H + 0.25), through)

    # resolve beam supports to exact points (beam line x track)
    final = {k: [] for k in ORDER}
    for k in ORDER:
        t = T[k]
        for x, kind, ztop, extra in supports[k]:
            if kind != "beam":
                final[k].append((x, kind, ztop))
                continue
            best = None
            for A, B, zb, level in beam_lines:
                if (level == "chuo") != t.chuo:
                    continue
                A_ = np.array(A); B_ = np.array(B)
                if abs(min(A_[0], B_[0]) - x) > 6.0 and abs(max(A_[0], B_[0]) - x) > 6.0:
                    continue
                d = B_ - A_
                xx = line_track_x(t, A_, d / np.hypot(*d), x - 6, x + 6)
                if xx is None:
                    continue
                q = t.P(xx)
                tt = ((q - A_) @ d) / (d @ d)
                if -0.02 <= tt <= 1.02 and (best is None or abs(xx - x) < abs(best[0] - x)):
                    best = (xx, zb)
            if best is None:
                unsupported.append((k, x))
                continue
            final[k].append((best[0], "beam", best[1]))
        final[k].sort()

    # ---- wires, droppers, fittings per track
    mbW, mbD = P.mb["wire"], P.mb["dropper"]
    dev_report = {}
    n_drop = 0
    for k in ORDER:
        t = T[k]
        sup = final[k]
        if not sup:
            continue
        xs = [s[0] for s in sup]
        offs = registration(t, xs)
        dev = [chord_dev(t, xs[i], xs[i + 1], offs[i], offs[i + 1]) for i in range(len(xs) - 1)]
        dev_report[k] = round(max(dev), 3) if dev else 0.0
        cw = CWZ[k]; ms0 = cw + SYS_H
        R = [t.P(x) + o * t.N(x) for x, o in zip(xs, offs)]
        # wire ends: to the track ends, except the terminal tracks (end at the last support before the buffer stop)
        pts = list(R)
        start = t.P(t.x0) + offs[0] * t.N(t.x0)
        pts = [start] + pts
        term = k in TERMINAL
        if not term:
            pts = pts + [t.P(t.x1) + offs[-1] * t.N(t.x1)]
        # contact wire: straight between registration points
        for a, b in zip(pts[:-1], pts[1:]):
            tube(mbW, (a[0], a[1], cw), (b[0], b[1], cw), R_CW, sides=6, mat=0)
        # messenger: parabolic sag between supports, straight to the ends
        for i, (a, b) in enumerate(zip(pts[:-1], pts[1:])):
            Lsp = float(np.hypot(*(b - a)))
            interior = (i >= 1) and (term or i < len(pts) - 2)
            sag = SAG_44 * (Lsp / 44.0) ** 2 if interior else 0.0
            n = max(2, int(Lsp / 2.5) + 1)
            path = []
            for j in range(n + 1):
                f = j / n
                q = a + (b - a) * f
                path.append(Vector((q[0], q[1], ms0 - 4 * sag * f * (1 - f))))
            L.tube(mbW, path, R_MS, sides=6, mat=1, smooth=True)
            # droppers every 5 m, at least 2 m from the supports
            m = int(Lsp // 5.0)
            for j in range(1, m + 1):
                f = j * 5.0 / Lsp
                if f * Lsp < 2.0 or (1 - f) * Lsp < 2.0:
                    continue
                q = a + (b - a) * f
                zm = ms0 - 4 * sag * f * (1 - f)
                tube(mbD, (q[0], q[1], cw + R_CW), (q[0], q[1], zm - R_MS), 0.0045, sides=4)
                L.box(mbD, float(q[0]), float(q[1]), cw + R_CW + 0.012, 0.05, 0.02, 0.024)
                n_drop += 1
        # fittings at every support
        for i, ((x, kind, ztop), o) in enumerate(zip(sup, offs)):
            Rp = R[i]
            nrm = t.N(x)
            pull = nrm * (1.0 if o >= 0 else -1.0)
            a = t.ang(x)
            support_fittings(P, Rp, pull, cw, ms0, ztop, kind, terminal=(term and i == len(sup) - 1),
                             track_dir=(math.cos(a), math.sin(a)))
            if kind == "ceiling":                                       # bracket plate on the soffit
                L.box(P.mb["fitting"], float(Rp[0] + 0.47 * pull[0]), float(Rp[1] + 0.47 * pull[1]), ztop - 0.03, 1.3, 0.25, 0.06,
                      frame=Matrix.Translation((float(Rp[0] + 0.47 * pull[0]), float(Rp[1] + 0.47 * pull[1]), ztop - 0.03)) @ frame_from(pull))

    restore_hidden()

    # ---- materials and objects
    col = L.collection("V6_Overhead_Line")
    M = {
        "cw": L.principled("V6 | OCS contact wire (hard-drawn copper)", (0.30, 0.20, 0.14), rough=0.38, metal=0.9),
        "ms": L.principled("V6 | OCS messenger (stranded steel)", (0.20, 0.21, 0.22), rough=0.5, metal=0.7),
        "steel": L.principled("V6 | OCS galvanised steel", (0.50, 0.52, 0.52), rough=0.48, metal=0.55),
        "mast": L.principled("V6 | OCS steel mast (grey paint)", (0.42, 0.45, 0.46), rough=0.55, metal=0.3),
        "fit": L.principled("V6 | OCS fittings (bronze / steel)", (0.33, 0.30, 0.26), rough=0.45, metal=0.75),
        "ins": L.principled("V6 | OCS insulator (glazed porcelain)", (0.80, 0.80, 0.77), rough=0.18, metal=0.0),
        "drop": L.principled("V6 | OCS dropper (bronze)", (0.36, 0.25, 0.16), rough=0.45, metal=0.85),
    }
    objs = {}
    objs["wire"] = P.mb["wire"].build("V6 OCS | contact wires and messengers", col, [M["cw"], M["ms"]])
    objs["dropper"] = P.mb["dropper"].build("V6 OCS | droppers", col, [M["drop"]])
    objs["mast"] = P.mb["mast"].build("V6 OCS | masts", col, [M["mast"]])
    objs["beam"] = P.mb["beam"].build("V6 OCS | V-truss beams and cantilevers", col, [M["steel"]])
    objs["fitting"] = P.mb["fitting"].build("V6 OCS | hangers, drop tubes, steady arms", col, [M["fit"]])
    objs["insulator"] = P.mb["insulator"].build("V6 OCS | insulators", col, [M["ins"]])
    for o in objs.values():
        o["V6_ocs"] = True

    # ---- people standing where a new mast is
    moved = 0
    pcol = bpy.data.collections.get("V5_People_instances")
    if pcol:
        for e in pcol.objects:
            p = e.matrix_world.translation
            for (x, y, zg, gname, through, zb, level) in mast_map.values():
                if abs(p.z - zg) < 1.0 and math.hypot(p.x - x, p.y - y) < 0.8:
                    e.location.x += 1.4 if p.x >= x else -1.4
                    moved += 1
                    break

    report = {
        "retired_v3_parts": STATS["retired_v3_parts"],
        "stations_x": [round(s, 2) for s in stations],
        "contact_wire_z": CWZ,
        "supports": {k: [(round(x, 2), kind) for x, kind, z in final[k]] for k in ORDER},
        "support_count": {k: len(final[k]) for k in ORDER},
        "support_kinds": {kd: sum(1 for k in ORDER for s in final[k] if s[1] == kd) for kd in ("beam", "ceiling", "roof")},
        "masts": len(mast_map), "beams": len(beam_set), "cantilevers": len(cant_ext),
        "max_wire_offset_from_track_m": dev_report,
        "droppers": n_drop,
        "unsupported_station_points": sorted(set((k, round(x, 1)) for k, x in unsupported)),
        "people_moved_off_masts": moved,
        "verts": {kk: len(o.data.vertices) for kk, o in objs.items()},
        "masts_detail": [(round(v[0], 2), round(v[1], 2), round(v[2], 2), v[3], v[6]) for v in mast_map.values()],
    }
    bpy.context.scene["V6_catenary_summary"] = json.dumps({k: v for k, v in report.items() if k not in ("supports", "masts_detail")})
    L.log(json.dumps({k: v for k, v in report.items() if k not in ("supports", "masts_detail")}, ensure_ascii=False))
    if REPORT:
        json.dump(report, open(REPORT, "w"), indent=1, ensure_ascii=False)
    if OUT:
        bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=True)
        L.log("saved", OUT)


run()
