"""V5 module 3a: one-piece ("monocoque") car bodies.
Replaces the V3 box-assembled bodies of the commuter cars (E233-0/1000/3000, E235, E233-0 Green) and the E5
intermediate cars with a single continuous shell per car:
- one extruded cross-section (wide body with lower taper, curved shoulders, arched roof; E5 Shinkansen section)
- window and door openings cut into that same surface; recessed glazing with black gaskets; inset door leaves
  that follow the body curvature, door-leaf windows; colour bands, roof paint and LED displays are material
  zones of the same surface rather than separate boxes
- chamfered car ends; raked, rounded cab nose with the front livery zones (black glass, bands, LED, lamps)
Window/door/band positions are read from the existing V3 parts (reviewed layout) before those parts are retired.
"""
import sys, os, math, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import bmesh
from mathutils import Vector
import v5lib as L
import e5_nose as EN

EPS = 1e-6

COMMUTER = {
    "E233-0 style ordinary car | procedural": ("E233", False),
    "E233-0 style cab | procedural": ("E233", True),
    "E233-0 style Green car | procedural": ("E233", False),
    "E233-1000 style intermediate | procedural": ("E233", False),
    "E233-1000 style cab | procedural": ("E233", True),
    "E233-3000 style intermediate | procedural": ("E233", False),
    "E233-3000 style cab | procedural": ("E233", True),
    "V3 E235-0 intermediate": ("E235", False),
    "V3 E235-0 cab": ("E235", True),
}
E5_MID = [f"V3 E5 car {i:02d}" for i in range(2, 10)]
E5_END = ["V4_Train_E5_car_01", "V4_Train_E5_car_10"]     # long-nose end cars (E523 / E514)

RETIRE_KEYS = ["stainless shell", "common stainless profile", "passenger window", "passenger glazing", "door glass",
               "door glazing", "door split", "double door surround", "green door panel", "window divider",
               "lower colour stripe", "upper green stripe", "upper waist band", "destination LED", "passenger LED",
               "front LED", "silver front mask", "wide sloping black cab mask", "black front mask",
               "panoramic inclined windscreen", "front glazing", "silver sloping side pillar",
               "continuous cab roof fairing", "central white front panel", "front orange corner", "front blue band",
               "lower green front band", "upper orange front band", "front dot gradient", "green rounded cab border",
               "high mounted headlamp", "upper headlight", "windscreen wiper", " wiper", "driver side door",
               "driver door window", "driver side window", "driver door", "driver window", "skirt cheek", " skirt",
               "double deck window",
               # E5
               "continuous green white pink shell", "door narrow glass", "door perimeter", "recessed passenger door",
               "full-perimeter flexible gangway",
               # E5 end cars (V4 nose shell and its separate parts)
               "shell_with_lamp_pockets", "conformed cockpit glass", "conformed cockpit gasket", "nose coupler-cover seam",
               "_black_recess", "_clear_protective_lens", "_perimeter_gasket", "_reflector", "_visible_headlamp"]


def bb(o):
    ws = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return Vector([min(w[i] for w in ws) for i in range(3)]), Vector([max(w[i] for w in ws) for i in range(3)])


# ------------------------------------------------------------------ profiles
def e233_side_y(z):
    if z <= 1.85:
        t = (1.85 - z) / 0.85
        return 1.475 - 0.17 * t * t
    return 1.475 - 0.02 * (min(z, 3.45) - 1.85) / 1.6


def e5_side_y(z):
    if z <= 1.50:
        t = (1.50 - z) / 0.88
        return 1.675 - 0.075 * t * t
    if z <= 3.0:
        return 1.675
    return 1.675


def half_profile(kind, breaks):
    """Half cross-section from bottom centre (y=0) around the side to roof centre (y=0)."""
    if kind == "E5":
        zb, ztop_side = 0.62, 3.0
        side = e5_side_y
        base = [0.62, 0.75, 0.95, 1.15, 1.35, 1.5, 1.8, 2.2, 2.6, 3.0]
        pts = [(0.0, 0.48), (1.50, 0.48), (1.58, 0.53)]
    else:
        zb, ztop_side = 1.00, 3.45
        side = e233_side_y
        base = [1.0, 1.1, 1.25, 1.4, 1.55, 1.7, 1.85, 2.05, 2.45, 2.85, 3.2, 3.45]
        pts = [(0.0, zb), (1.20, zb)]
    zs = sorted(set([round(z, 4) for z in base + [b for b in breaks if zb - EPS < b < ztop_side + EPS]]))
    clean = []
    for z in zs:                       # drop near-duplicates (< 8 mm) but keep zone edges exact
        if clean and z - clean[-1] < 0.008 and clean[-1] not in breaks:
            clean[-1] = z
        elif not clean or z - clean[-1] >= 0.004:
            clean.append(z)
    pts += [(side(z), z) for z in clean]
    if kind == "E5":
        # shoulder as a cubic Bezier from (1.675, 3.0) to (1.0, 3.66), roof parabola to (0, 3.705)
        P = [Vector((1.675, 3.0)), Vector((1.675, 3.30)), Vector((1.42, 3.58)), Vector((1.0, 3.66))]
        for i in range(1, 13):
            t = i / 12
            p = (1 - t) ** 3 * P[0] + 3 * (1 - t) ** 2 * t * P[1] + 3 * (1 - t) * t * t * P[2] + t ** 3 * P[3]
            pts.append((p.x, p.y))
        y0, z0, ztop = 1.0, 3.66, 3.705
    else:
        cx, cz, R = 1.455 - 0.32, 3.45, 0.32
        for i in range(1, 8):
            th = math.radians(84 * i / 7)
            pts.append((cx + R * math.cos(th), cz + R * math.sin(th)))
        y0, z0 = pts[-1]
        ztop = 3.83
    nr = 12 if kind == "E5" else 6
    for i in range(1, nr + 1):
        y = y0 * (1 - i / nr)
        pts.append((y, ztop - (ztop - z0) * (y / y0) ** 2))
    return pts


def normals2d(H):
    """Outward normals of the half profile (right side, y>=0)."""
    N = []
    for j in range(len(H)):
        a = Vector(H[max(j - 1, 0)])
        b = Vector(H[min(j + 1, len(H) - 1)])
        t = (b - a)
        n = Vector((t.y, -t.x))
        if n.length < EPS:
            n = Vector((0, -1))
        N.append(n.normalized())
    N[0] = Vector((0, -1))
    N[-1] = Vector((0, 1))
    return N


# --------------------------------------------------------------- layout read
def read_layout(col, kind, cab):
    lay = {"windows": [], "door_windows": [], "doors": [], "stripes": [], "leds": [], "front": [], "lamps": []}
    objs = [o for o in col.objects if o.type in ('MESH', 'CURVE') and not o.get("V5_retired")]
    shell = [o for o in objs if any(k in o.name for k in ("stainless shell", "common stainless profile", "green white pink shell",
                                                          "shell_with_lamp_pockets"))]
    mn, mx = bb(shell[0])
    lay["L"] = round(mx.x, 4)
    if "shell_with_lamp_pockets" in shell[0].name:      # E5 end car: rear end at -L, nose tip at +x_tip
        lay["L"] = round(-mn.x, 4)
        lay["nose"] = {"x_tip": round(mx.x, 4), "x0": round(mx.x - EN.D_NOSE, 4)}
    for o in objs:
        n = o.name
        a, b = bb(o)
        s = 1 if (a.y + b.y) > 0 else -1
        rect = [s, round(a.x, 4), round(b.x, 4), round(a.z, 4), round(b.z, 4)]
        side = abs(a.y + b.y) / 2 > 1.2
        if any(k in n for k in ("passenger window", "passenger glazing", "driver side window", "driver window", "double deck window")) and side:
            lay["windows"].append(rect)
        elif any(k in n for k in ("door glass", "door glazing", "driver door window", "door narrow glass")) and side:
            lay["door_windows"].append(rect)
        elif any(k in n for k in ("double door surround", "green door panel")) and side:
            lay["doors"].append([s, round(a.x + 0.015, 4), round(b.x - 0.015, 4), round(b.z - 0.015, 4), "double"])
        elif any(k in n for k in ("driver side door", "driver door")) and "window" not in n and side:
            lay["doors"].append([s, round(a.x, 4), round(b.x, 4), round(b.z, 4), "single"])
        elif "door perimeter" in n and side:
            lay["doors"].append([s, round(a.x, 4), round(b.x, 4), round(b.z, 4), "single", round(a.z, 4)])
        elif any(k in n for k in ("lower colour stripe", "upper green stripe", "upper waist band")) and side:
            lay["stripes"].append([round(a.z, 4), round(b.z, 4), o.data.materials[0].name])
        elif any(k in n for k in ("destination LED", "passenger LED")) and side:
            lay["leds"].append(rect)
        elif cab and b.x > 9.5 and not side:
            mat = o.data.materials[0].name if getattr(o.data, "materials", None) and len(o.data.materials) else None
            for key, zone in (("front blue band", "band"), ("central white front panel", "white"), ("front orange corner", "corner"),
                              ("lower green front band", "band"), ("upper orange front band", "band"), ("front dot gradient", "green"),
                              ("destination LED", "led"), ("front LED", "led")):
                if key in n:
                    lay["front"].append([zone, round(a.y, 4), round(b.y, 4), round(a.z, 4), round(b.z, 4), mat])
            if "headlamp" in n or "upper headlight" in n:
                lay["lamps"].append([round(a.y, 4), round(b.y, 4), round(a.z, 4), round(b.z, 4)])
            if "front mask" in n:
                lay["x_front"] = max(lay.get("x_front", 0), round(b.x, 4))
    # dedupe stripes (one per side)
    st = {}
    for z0, z1, m in lay["stripes"]:
        st[(z0, z1)] = m
    lay["stripes"] = [[k[0], k[1], v] for k, v in sorted(st.items())]
    # windows overlapping a door are door windows; trim body windows that touch a door
    body_w = []
    for w in lay["windows"]:
        s, x0, x1, z0, z1 = w
        on_door = [d for d in lay["doors"] if d[0] == s and x0 >= d[1] - 1e-3 and x1 <= d[2] + 1e-3]
        if on_door:
            lay["door_windows"].append(w)
            continue
        for d in lay["doors"]:
            if d[0] == s and x0 < d[2] and x1 > d[1]:
                if x0 < d[1]:
                    x1 = min(x1, d[1] - 0.10)
                else:
                    x0 = max(x0, d[2] + 0.10)
        if x1 - x0 > 0.2:
            body_w.append([s, x0, x1, z0, z1])
    lay["windows"] = body_w
    return lay


# ------------------------------------------------------------------ builder
class Body:
    def __init__(self):
        self.v, self.f, self.m, self.cur = [], [], [], []

    def vert(self, p):
        self.v.append(tuple(p))
        return len(self.v) - 1

    def face(self, idx, mat, want=None, curved=False):
        if len(set(idx)) < 3:
            return
        idx = list(idx)
        if want is not None:
            n = Vector((0.0, 0.0, 0.0))
            P = [Vector(self.v[i]) for i in idx]
            for a in range(len(P)):
                p, q = P[a], P[(a + 1) % len(P)]
                n.x += (p.y - q.y) * (p.z + q.z)
                n.y += (p.z - q.z) * (p.x + q.x)
                n.z += (p.x - q.x) * (p.y + q.y)
            if n.dot(Vector(want)) < 0:
                idx.reverse()
        self.f.append(tuple(idx))
        self.m.append(mat)
        self.cur.append(1 if curved else 0)


def profile_normal_fn(H, sharp_deg=30.0):
    """Analytic outward normal of the half profile at any (y>=0, z) point near it.
    Normals are interpolated along each segment and averaged across a vertex only where the
    profile turns by less than sharp_deg (real creases such as the body bottom edge stay crisp)."""
    import numpy as np
    P = np.array(H, float)
    seg = P[1:] - P[:-1]
    ln = np.linalg.norm(seg, axis=1) + 1e-12
    sn = np.stack([seg[:, 1], -seg[:, 0]], 1) / ln[:, None]          # outward (right side)
    ns = len(sn)
    cosmax = math.cos(math.radians(sharp_deg))
    n_start = sn.copy(); n_end = sn.copy()
    for k in range(ns):
        if k > 0 and float(sn[k - 1] @ sn[k]) > cosmax:
            v = sn[k - 1] + sn[k]; n_start[k] = v / np.linalg.norm(v)
        if k < ns - 1 and float(sn[k] @ sn[k + 1]) > cosmax:
            v = sn[k] + sn[k + 1]; n_end[k] = v / np.linalg.norm(v)
    A = P[:-1]; AB = seg; L2 = (AB ** 2).sum(1) + 1e-12

    def fn(yz):
        yz = np.asarray(yz, float)
        t = ((yz[:, None, :] - A[None]) * AB[None]).sum(2) / L2[None]
        t = np.clip(t, 0.0, 1.0)
        proj = A[None] + t[..., None] * AB[None]
        d2 = ((yz[:, None, :] - proj) ** 2).sum(2)
        k = d2.argmin(1)
        tk = t[np.arange(len(k)), k][:, None]
        n = n_start[k] * (1 - tk) + n_end[k] * tk
        return n / np.linalg.norm(n, axis=1)[:, None]
    return fn


def apply_profile_normals(me, H):
    """Custom split normals: every face flagged 'curved' gets the exact normal of the car-body cross-section,
    so the shell shades as one smooth surface (no pillowing around the window and door cut-outs)."""
    import numpy as np
    if "V5_curved" not in me.attributes:
        return 0
    nl = len(me.loops)
    cn = np.empty(nl * 3); me.corner_normals.foreach_get("vector", cn); cn = cn.reshape(-1, 3)
    lv = np.empty(nl, int); me.loops.foreach_get("vertex_index", lv)
    co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    lt = np.empty(len(me.polygons), int); me.polygons.foreach_get("loop_total", lt)
    cur = np.empty(len(me.polygons), int); me.attributes["V5_curved"].data.foreach_get("value", cur)
    lf = np.repeat(np.arange(len(me.polygons)), lt)
    mask = cur[lf] == 1
    p = co[lv[mask]]
    s = np.where(p[:, 1] < 0, -1.0, 1.0)
    fn = profile_normal_fn(H)
    n2 = fn(np.stack([np.abs(p[:, 1]), p[:, 2]], 1))
    new = cn.copy()
    new[mask] = np.stack([np.zeros(len(p)), s * n2[:, 0], n2[:, 1]], 1)
    me.normals_split_custom_set([tuple(v) for v in new])
    return int(mask.sum())


def build_body(name, col, kind, cab, lay, M):
    """M: dict of material indices."""
    L_ = lay["L"]
    doors = lay["doors"]
    # z breakpoints
    zb = []
    for w in lay["windows"] + lay["door_windows"] + lay["leds"]:
        zb += [w[3], w[4]]
    for d in doors:
        zb.append(d[3])
        if len(d) > 5:
            zb.append(d[5])
    for s in lay["stripes"]:
        zb += [s[0], s[1]]
    for fz in lay["front"]:
        zb += [fz[3], fz[4]]
    for lp in lay["lamps"]:
        zb += [lp[2], lp[3]]
    if kind == "E5":
        zb += [1.86, 1.99]
    if cab:
        zb += [1.95, 2.0, 3.60, 3.62] if kind == "E233" else [1.63, 3.63]
    zb = sorted(set(round(z, 4) for z in zb))
    H = half_profile(kind, zb)
    N = normals2d(H)
    nH = len(H)
    jz = {round(H[j][1], 4): j for j in range(2, nH) if H[j][0] > 1.0}   # side-wall index by z

    def J(z):
        z = round(z, 4)
        if z in jz:
            return jz[z]
        return min(jz.items(), key=lambda kv: abs(kv[0] - z))[1]

    def is_roof(j):
        return H[j][1] > (3.62 if kind != "E5" else 9.0) and H[j][0] < 1.35

    # zone material for the body surface
    def body_mat(zc, j, s, xc):
        for led in lay["leds"]:
            if led[0] == s and led[1] - EPS <= xc <= led[2] + EPS and led[3] - EPS <= zc <= led[4] + EPS:
                return M.get("led_side", M["led"])
        if kind == "E5":
            if zc < 1.86:
                return M["e5_white"]
            if zc < 1.99:
                return M["e5_pink"]
            return M["e5_green"]
        if is_roof(j) or (H[j][1] > 3.70 and H[min(j + 1, nH - 1)][1] > 3.70):
            return M["roof"]
        for z0, z1, mname in lay["stripes"]:
            if z0 - EPS <= zc <= z1 + EPS:
                return M.get("mat:" + mname, M["body"])
        return M["body"]

    B = Body()
    nose = lay.get("nose")
    straight_x0 = -L_ + 0.07
    straight_x1 = (lay["x_front"] - 0.34) if cab else (nose["x0"] if nose else (L_ - 0.07))
    xs = {straight_x0, straight_x1}
    for w in lay["windows"] + lay["leds"]:
        xs.update([w[1], w[2]])
    for d in doors:
        xs.update([d[1], d[2]])
    xs = sorted(x for x in xs if straight_x0 - EPS <= x <= straight_x1 + EPS)
    # body surface with holes ------------------------------------------------
    holes = []   # (s, x0, x1, z0, z1, kind)
    for w in lay["windows"]:
        holes.append((w[0], w[1], w[2], w[3], w[4], "win"))
    for d in doors:
        holes.append((d[0], d[1], d[2], (d[5] if len(d) > 5 else None), d[3], "door"))

    def in_hole(s, xa, xb, za, zb_):
        for h in holes:
            hz0 = h[3] if h[3] is not None else -1.0
            if h[0] == s and xa >= h[1] - EPS and xb <= h[2] + EPS and za >= hz0 - EPS and zb_ <= h[4] + EPS:
                return h
        return None

    vid = {}

    def V(s, xi, j, x=None):
        key = (s, xi, j)
        if key not in vid:
            y, z = H[j]
            vid[key] = B.vert((xs[xi] if x is None else x, s * y, z))
        return vid[key]

    for s in (1, -1):
        for xi in range(len(xs) - 1):
            xa, xb = xs[xi], xs[xi + 1]
            for j in range(nH - 1):
                za, zb2 = sorted((H[j][1], H[j + 1][1]))
                if H[j][0] > 1.0 and H[j + 1][0] > 1.0 and abs(H[j + 1][1] - H[j][1]) > EPS and in_hole(s, xa, xb, za, zb2):
                    continue
                q = [V(s, xi, j), V(s, xi + 1, j), V(s, xi + 1, j + 1), V(s, xi, j + 1)]
                nn = (N[j] + N[j + 1])
                B.face(q, body_mat((za + zb2) / 2, j, s, (xa + xb) / 2), want=(0, s * nn.x, nn.y), curved=True)

    # jambs, recessed glazing, door leaves ----------------------------------
    def yprof(z):
        # interpolate the side-wall y at height z
        for j in range(2, nH - 1):
            z0, z1 = H[j][1], H[j + 1][1]
            if z0 - EPS <= z <= z1 + EPS and H[j][0] > 1.0:
                t = 0 if abs(z1 - z0) < EPS else (z - z0) / (z1 - z0)
                return H[j][0] + t * (H[j + 1][0] - H[j][0])
        return H[J(z)][0]

    def jamb_ring(s, x0, x1, z0, z1, depth, mat, base_off=0.0):
        """Faces from the opening edge on the surface (offset base_off) inward by depth; returns inner loop verts."""
        j0, j1 = J(z0), J(z1)
        ring = []                       # boundary points in order (CCW seen from outside)
        cols = [x for x in xs if x0 - EPS <= x <= x1 + EPS] if base_off == 0.0 else [x0, x1]
        for x in cols:
            ring.append((x, j0))
        for j in range(j0 + 1, j1 + 1):
            ring.append((x1, j))
        for x in reversed(cols[:-1]):
            ring.append((x, j1))
        for j in range(j1 - 1, j0, -1):
            ring.append((x0, j))
        outer, inner = [], []
        for x, j in ring:
            y, z = H[j]
            outer.append(B.vert((x, s * (y - base_off), z)))
            inner.append(B.vert((x, s * (y - base_off - depth), z)))
        n = len(ring)
        cxh, czh = (x0 + x1) / 2, (z0 + z1) / 2
        for i in range(n):
            a, b2 = i, (i + 1) % n
            q = [outer[a], outer[b2], inner[b2], inner[a]]
            pa, pb = B.v[outer[a]], B.v[outer[b2]]
            mxp, mzp = (pa[0] + pb[0]) / 2, (pa[2] + pb[2]) / 2
            B.face(q, mat, want=(cxh - mxp, 0.0, czh - mzp))
        return inner, ring

    def glazing(s, x0, x1, z0, z1, depth, panes, base_off=0.0, gasket=0.035):
        inner, ring = jamb_ring(s, x0, x1, z0, z1, depth, M["rubber"], base_off)
        B.face(list(inner), M["rubber"], want=(0, s, 0))
        # glass panes slightly in front of the gasket back
        edges = [x0] + panes + [x1]
        for k in range(len(edges) - 1):
            a = edges[k] + (gasket if k == 0 else 0.018)
            b2 = edges[k + 1] - (gasket if k == len(edges) - 2 else 0.018)
            za, zt = z0 + gasket, z1 - gasket
            ya, yt = yprof(za) - base_off - depth + 0.004, yprof(zt) - base_off - depth + 0.004
            q = [B.vert((a, s * ya, za)), B.vert((b2, s * ya, za)), B.vert((b2, s * yt, zt)), B.vert((a, s * yt, zt))]
            B.face(q, M["glass"], want=(0, s, 0))

    for (s, x0, x1, z0, z1, kind_h) in holes:
        if kind_h == "win":
            w = x1 - x0
            panes = [x0 + w / 2] if w > 1.6 else ([x0 + w / 2] if (w > 0.9 and kind != "E5") else [])
            glazing(s, x0, x1, z0, z1, 0.035, panes)
    for d in doors:
        s, x0, x1, zt, typ = d[0], d[1], d[2], d[3], d[4]
        z0 = d[5] if len(d) > 5 else H[J(H[2][1])][1]
        # dark jamb around the door opening (from the surface inward 0.04)
        jamb_ring(s, x0, x1, z0, zt, 0.045, M["dark"])
        # door leaves (follow the profile, inset 0.014)
        leaves = [(x0 + 0.006, (x0 + x1) / 2 - 0.007), ((x0 + x1) / 2 + 0.007, x1 - 0.006)] if typ == "double" else [(x0 + 0.006, x1 - 0.006)]
        j0, j1 = J(z0), J(zt)
        for (lx0, lx1) in leaves:
            dws = [w for w in lay["door_windows"] if w[0] == s and w[1] >= lx0 - 0.02 and w[2] <= lx1 + 0.02]
            cols = sorted(set([lx0, lx1] + [c for w in dws for c in (max(w[1], lx0 + 0.03), min(w[2], lx1 - 0.03))]))
            lv = {}

            def LV(ci, j):
                if (ci, j) not in lv:
                    y, z = H[j]
                    lv[(ci, j)] = B.vert((cols[ci], s * (y - 0.014), z))
                return lv[(ci, j)]
            for ci in range(len(cols) - 1):
                for j in range(j0, j1):
                    xa, xb = cols[ci], cols[ci + 1]
                    zc = (H[j][1] + H[j + 1][1]) / 2
                    if any(xa >= max(w[1], lx0 + 0.03) - EPS and xb <= min(w[2], lx1 - 0.03) + EPS and w[3] - EPS <= H[j][1] and H[j + 1][1] <= w[4] + EPS for w in dws):
                        continue
                    q = [LV(ci, j), LV(ci + 1, j), LV(ci + 1, j + 1), LV(ci, j + 1)]
                    nn = (N[j] + N[j + 1])
                    if kind == "E5":
                        mat = M["e5_white"] if zc < 1.86 else (M["e5_pink"] if zc < 1.99 else M["e5_green"])
                    else:
                        mat = M["door"]
                    B.face(q, mat, want=(0, s * nn.x, nn.y), curved=True)
            # leaf edges (thickness) so the inset reads as a separate leaf
            for (xx, sgn) in ((lx0, -1), (lx1, 1)):
                for j in range(j0, j1):
                    y0_, z0_ = H[j]
                    y1_, z1_ = H[j + 1]
                    q = [B.vert((xx, s * (y0_ - 0.014), z0_)), B.vert((xx, s * (y1_ - 0.014), z1_)),
                         B.vert((xx, s * (y1_ - 0.05), z1_)), B.vert((xx, s * (y0_ - 0.05), z0_))]
                    B.face(q, M["dark"], want=(sgn, 0, 0))
            for w in dws:
                gx0, gx1 = max(w[1], lx0 + 0.03), min(w[2], lx1 - 0.03)
                glazing(s, gx0, gx1, w[3], w[4], 0.025, [], base_off=0.014, gasket=0.03)

    # ends -----------------------------------------------------------------------
    def ring_pts(x_of_z, shrink):
        pts = []
        for j in range(nH):
            y, z = H[j]
            n = N[j]
            pts.append((y - n.x * shrink, z - n.y * shrink))
        return pts

    def loop_verts(x_of_z, pts):
        right = [B.vert((x_of_z(z), y, z)) for (y, z) in pts]
        left = [B.vert((x_of_z(z), -y, z)) for (y, z) in pts]
        return right, left

    def bridge(A, Bv, flip, matfn):
        (Ar, Al), (Br, Bl) = A, Bv
        for j in range(nH - 1):
            for side, (a, b2) in ((1, (Ar, Br)), (-1, (Al, Bl))):
                q = [a[j], b2[j], b2[j + 1], a[j + 1]]
                nn = (N[j] + N[j + 1])
                B.face(q, matfn(j, side), want=(0.35 if flip else -0.35, side * nn.x, nn.y))

    def side_mat(j, side, x):
        zc = (H[j][1] + H[j + 1][1]) / 2
        return body_mat(zc, j, side, x)

    # rear (and, for intermediates, front) chamfered ends
    ends = (-1,) if (cab or nose) else (-1, 1)
    for end in ends:
        xe = end * L_
        xa = straight_x0 if end < 0 else straight_x1
        A = loop_verts(lambda z: xa, ring_pts(None, 0.0))
        E_pts = ring_pts(None, 0.04)
        Bv = loop_verts(lambda z: xe, E_pts)
        bridge(A, Bv, end > 0, lambda j, sd: side_mat(j, sd, xe) if M.get("chamfer_body") is None else M["chamfer_body"])
        # end cap (ladder between mirrored vertices)
        Br, Bl = Bv
        for j in range(nH - 1):
            q = [Bl[j], Br[j], Br[j + 1], Bl[j + 1]]
            B.face(q, M["end"], want=(end, 0, 0))

    if kind == "E5":
        # full-perimeter gangway bellows, flush with the body (the train reads as one continuous tube)
        for end in ends:
            EN.bellows(B, H, N, end * L_, end, M["rubber"])
    if nose:
        lay["nose_stats"] = EN.build_nose(B, H, M, nose["x_tip"])

    # cab nose -------------------------------------------------------------------
    if cab:
        XF = lay["x_front"] + 0.015
        rake = 0.075

        def xf(z, back=0.0):
            return XF - back - rake * max(0.0, z - 1.95) / 1.7

        A = loop_verts(lambda z: straight_x1, ring_pts(None, 0.0))
        rings = [(0.11, 0.012), (0.035, 0.045), (0.0, 0.075)]
        prev = A
        prev_pts = ring_pts(None, 0.0)
        for back, shr in rings:
            pts = ring_pts(None, shr)
            cur = loop_verts(lambda z, b=back: xf(z, b), pts)
            if kind == "E235" and shr > 0.04:
                bridge(prev, cur, True, lambda j, sd: M["e235_green"] if (1.0 < H[j][1] < 3.7) else side_mat(j, sd, XF))
            else:
                bridge(prev, cur, True, lambda j, sd: side_mat(j, sd, XF))
            prev, prev_pts = cur, pts
        cap_pts = prev_pts
        # front cap grid with livery zones
        ybreaks = set()
        for fz in lay["front"]:
            ybreaks.update([fz[1], fz[2]])
        for lp in lay["lamps"]:
            ybreaks.update([lp[0], lp[1]])
        ybreaks.update([-1.27, 1.27] if kind == "E233" else [-1.31, 1.31])
        ybreaks = sorted(ybreaks)

        def front_mat(yc, zc):
            for fz in lay["front"]:
                zone, y0, y1, z0, z1, mname = fz
                if y0 - EPS <= yc <= y1 + EPS and z0 - EPS <= zc <= z1 + EPS:
                    if zone == "led":
                        return M.get("led_front", M["led"])
                    if zone in ("band", "corner", "green", "white"):
                        return M.get("mat:" + str(mname), M["body"])
            if kind == "E233":
                ztop_black = 3.60
                zlow_black = 2.0 if any(fz[0] == "band" and fz[4] > 1.97 for fz in lay["front"]) else 1.95
                if zlow_black <= zc <= ztop_black and abs(yc) < 1.27:
                    return M["black"]
            else:
                if 1.63 <= zc <= 3.63 and abs(yc) < 1.31:
                    return M["black"]
            return M["body"]

        for j in range(nH - 1):
            (ya, za), (yb2, zb3) = cap_pts[j], cap_pts[j + 1]
            if abs(zb3 - za) < 1e-5:
                continue
            wmin = min(ya, yb2)
            inner = [b for b in ybreaks if abs(b) < wmin - 0.004]
            bot = [-ya] + inner + [ya]
            top = [-yb2] + inner + [yb2]
            bv = [B.vert((xf(za), y, za)) for y in bot]
            tv = [B.vert((xf(zb3), y, zb3)) for y in top]
            for c in range(len(bot) - 1):
                yc = (bot[c] + bot[c + 1] + top[c] + top[c + 1]) / 4
                q = [bv[c], tv[c], tv[c + 1], bv[c + 1]]
                B.face(q, front_mat(yc, (za + zb3) / 2), want=(1, 0, 0))
        # head / tail lamp units (V5.1): framed unit with a dark backing, a round HID head lamp (reflector bowl +
        # lit core) on the outside and an LED tail lamp on the inside; which of the two glows is decided per
        # instance (V5_head / V5_tail on the instancing empty)
        def fpoly(pts_yz, off):
            return [B.vert((xf(z) + off, y, z)) for y, z in pts_yz]

        def rrect(ya, yb, za, zb, r, n=4):
            ya, yb = min(ya, yb), max(ya, yb)
            r = min(r, (yb - ya) / 2 - 1e-4, (zb - za) / 2 - 1e-4)
            pts = []
            for cy, cz, a0 in ((yb - r, zb - r, 0.0), (ya + r, zb - r, 90.0), (ya + r, za + r, 180.0), (yb - r, za + r, 270.0)):
                for i in range(n + 1):
                    a = math.radians(a0 + 90.0 * i / n)
                    pts.append((cy + r * math.cos(a), cz + r * math.sin(a)))
            return pts

        def disc(yc_, zc_, r, n=16):
            return [(yc_ + r * math.cos(2 * math.pi * i / n), zc_ + r * math.sin(2 * math.pi * i / n)) for i in range(n)]

        for lp in lay["lamps"]:
            y0, y1, z0, z1 = lp
            yc, zc = (y0 + y1) / 2, (z0 + z1) / 2
            hw, hh = (y1 - y0) / 2, (z1 - z0) / 2
            s = 1 if yc > 0 else -1
            ya, yb = yc - s * (hw + 0.21), yc + s * (hw + 0.025)          # inner (tail) .. outer (head)
            za, zb = zc - hh - 0.025, zc + hh + 0.025
            outer = rrect(ya - s * 0.012, yb + s * 0.012, za - 0.012, zb + 0.012, 0.05)
            inner = rrect(ya, yb, za, zb, 0.04)
            ov, iv = fpoly(outer, 0.004), fpoly(inner, 0.004)
            for k_ in range(len(ov)):
                k2 = (k_ + 1) % len(ov)
                B.face([ov[k_], ov[k2], iv[k2], iv[k_]], M["rubber"], want=(1, 0, 0))
            B.face(fpoly(inner, 0.003), M.get("lamp_back", M["black"]), want=(1, 0, 0))
            rr_ = min(hw, hh) * 1.05
            B.face(fpoly(disc(yc, zc, rr_), 0.005), M.get("hl_reflector", M["lamp"]), want=(1, 0, 0))
            B.face(fpoly(disc(yc, zc, rr_ * 0.48), 0.007), M.get("head_lit", M["lamp"]), want=(1, 0, 0))
            yt0, yt1 = yc - s * (hw + 0.19), yc - s * (hw + 0.05)
            B.face(fpoly(rrect(yt0, yt1, zc - hh * 0.62, zc + hh * 0.62, 0.025), 0.006), M.get("tail_lit", M["tail"]), want=(1, 0, 0))
        for s in (-1, 1):
            z0, z1 = 2.25, 2.85
            x0, x1 = xf(z0) + 0.008, xf(z1) + 0.008
            y = s * 0.42
            q = [B.vert((x0, y - 0.018, z0)), B.vert((x0, y + 0.018, z0)), B.vert((x1, y + 0.018, z1)), B.vert((x1, y - 0.018, z1))]
            B.face(q, M["rubber"], want=(1, 0, 0))
        # run-number display (lower corner of the windscreen)
        zc = 2.12 if kind == "E233" else 2.30
        x = xf(zc) + 0.007
        q = [B.vert((x, 0.58, zc - 0.06)), B.vert((x, 0.98, zc - 0.06)), B.vert((x, 0.98, zc + 0.06)), B.vert((x, 0.58, zc + 0.06))]
        B.face(q, M["runno"], want=(1, 0, 0))

    # drip rails along the shoulders
    me_extra = L.MeshBuilder()
    zr = 3.48 if kind != "E5" else 3.10
    x_end = (lay["x_front"] - 0.40) if cab else ((nose["x0"] - 0.30) if nose else (L_ - 0.12))
    for s in ((-1, 1) if kind != "E5" else ()):          # Shinkansen bodies have no external drip rails
        y = e233_side_y(zr) if kind != "E5" else 1.66
        L.tube(me_extra, [Vector((-L_ + 0.12, s * (y + 0.01), zr)), Vector((x_end, s * (y + 0.01), zr))], 0.014, sides=6, mat=0)
    o = len(B.v)
    B.v.extend(me_extra.v)
    for f_ in me_extra.f:
        B.face([o + i for i in f_], M["body"] if kind != "E5" else M["e5_green"])

    # mesh ----------------------------------------------------------------------
    me = bpy.data.meshes.new(name)
    me.from_pydata(B.v, [], B.f)
    me.polygons.foreach_set("material_index", B.m)
    at = me.attributes.new("V5_curved", 'INT', 'FACE')
    at.data.foreach_set("value", B.cur)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bm.to_mesh(me)
    bm.free()
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    try:
        me.set_sharpness_by_angle(angle=math.radians(32.0))
    except Exception:
        pass
    me.update()
    apply_profile_normals(me, H)
    me.update()
    led_uvs(me, lay, M, kind)
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    return ob


def led_uvs(me, lay, M, kind):
    """UVs for the destination / run-number displays so the dot-matrix textures read correctly from outside."""
    ids = {M.get("led_side"): "side", M.get("led_front"): "front", M.get("runno"): "runno"}
    ids.pop(None, None)
    if not any(p.material_index in ids for p in me.polygons):
        return 0
    uv = me.uv_layers.new(name="UVMap")
    co = [v.co for v in me.vertices]
    fronts = [f for f in lay["front"] if f[0] == "led"]
    zr = 2.12 if kind == "E233" else 2.30
    n = 0
    for p in me.polygons:
        k = ids.get(p.material_index)
        if k is None:
            continue
        c = p.center
        if k == "side":
            s = 1 if c.y > 0 else -1
            r = next((l for l in lay["leds"] if l[0] == s and l[1] - 0.01 <= c.x <= l[2] + 0.01), None)
            if r is None:
                continue
            x0, x1, z0, z1 = r[1], r[2], r[3], r[4]
            for li in p.loop_indices:
                v = co[me.loops[li].vertex_index]
                u = (x1 - v.x) / (x1 - x0) if s > 0 else (v.x - x0) / (x1 - x0)
                uv.data[li].uv = (u, (v.z - z0) / (z1 - z0))
        else:
            if k == "front" and fronts:
                y0, y1, z0, z1 = fronts[0][1], fronts[0][2], fronts[0][3], fronts[0][4]
            else:
                y0, y1, z0, z1 = 0.58, 0.98, zr - 0.06, zr + 0.06
            for li in p.loop_indices:
                v = co[me.loops[li].vertex_index]
                uv.data[li].uv = ((v.y - y0) / (y1 - y0), (v.z - z0) / (z1 - z0))
        n += 1
    return n


TEX_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "textures")
LINE_OF = {"E233-0": "chuo", "E233-1000": "kt", "E233-3000": "tokaido", "E235": "yamanote"}


def _instancer_attr(nt, name):
    a = nt.nodes.new("ShaderNodeAttribute")
    a.attribute_type = 'INSTANCER'
    a.attribute_name = name
    return a


def led_material(name, png0, png1, strength=2.6):
    """Emissive dot-matrix display; texture variant chosen per instance by the empty's V5_dest (0/1)."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n_ in list(nt.nodes):
        nt.nodes.remove(n_)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    pr = nt.nodes.new("ShaderNodeBsdfPrincipled")
    imgs = []
    for png in (png0, png1):
        img = bpy.data.images.get(os.path.basename(png)) or bpy.data.images.load(png)
        img.pack()
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = img; t.interpolation = 'Linear'
        imgs.append(t)
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'
    att = _instancer_attr(nt, "V5_dest")
    nt.links.new(att.outputs["Fac"], mix.inputs[0])
    nt.links.new(imgs[0].outputs["Color"], mix.inputs[6]); nt.links.new(imgs[1].outputs["Color"], mix.inputs[7])
    pr.inputs["Base Color"].default_value = (0.01, 0.01, 0.01, 1)
    pr.inputs["Roughness"].default_value = 0.25
    nt.links.new(mix.outputs[2], pr.inputs["Emission Color"])
    pr.inputs["Emission Strength"].default_value = strength
    nt.links.new(pr.outputs[0], out.inputs[0])
    return m


def lamp_material(name, base, emit, strength, attr):
    """Lamp lens that only glows on the instances whose empty has attr = 1 (V5_head / V5_tail)."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    pr = nt.nodes.get("Principled BSDF")
    pr.inputs["Base Color"].default_value = (*base, 1)
    pr.inputs["Roughness"].default_value = 0.08
    pr.inputs["Emission Color"].default_value = (*emit, 1)
    att = _instancer_attr(nt, attr)
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = 'MULTIPLY'
    mul.inputs[1].default_value = strength
    nt.links.new(att.outputs["Fac"], mul.inputs[0])
    nt.links.new(mul.outputs[0], pr.inputs["Emission Strength"])
    return m


# -------------------------------------------------------------------- run
def materials():
    mats = {}
    lst = []

    def add(key, m):
        if m.name not in [x.name for x in lst]:
            lst.append(m)
        mats[key] = [x.name for x in lst].index(m.name)
    add("body", bpy.data.materials["V2 | stainless commuter body"])
    add("door", L.principled("V5 | EMU door leaf stainless", (0.58, 0.61, 0.62), rough=0.26, metal=0.72))
    add("roof", L.principled("V5 | EMU roof grey anti-slip paint", (0.50, 0.52, 0.53), rough=0.62, metal=0.15))
    add("rubber", bpy.data.materials["V4_Train_rubber_and_gaskets"])
    add("glass", bpy.data.materials["V2 | train reflective dark glazing"])
    add("dark", bpy.data.materials["V2 | recessed room shadow"])
    add("led", L.principled("V5 | lit LED destination panel", (0.03, 0.02, 0.01), rough=0.3, emission=(1.0, 0.45, 0.08), strength=2.2))
    add("black", L.principled("V5 | E233 glossy black front", (0.008, 0.009, 0.011), rough=0.08, spec=0.7))
    add("lamp", L.principled("V5 | head lamp lens", (0.85, 0.88, 0.9), rough=0.05, spec=0.9))
    add("tail", L.principled("V5 | tail lamp red lens", (0.42, 0.02, 0.02), rough=0.12, spec=0.8))
    add("runno", L.principled("V5 | run-number LED", (0.03, 0.02, 0.01), rough=0.3, emission=(1.0, 0.32, 0.05), strength=3.0))
    add("end", bpy.data.materials["V2 | stainless commuter body"])
    add("e235_green", bpy.data.materials["V2 | Yamanote green"])
    add("e5_white", bpy.data.materials["V3 | E5 lower white"])
    add("e5_green", bpy.data.materials["V3 | E5 Tokiwa green"])
    add("e5_pink", bpy.data.materials["V3 | E5 pink waist band"])
    add("hl_optic", bpy.data.materials["V4_Train_headlight_optic"])
    add("hl_reflector", bpy.data.materials["V4_Train_lamp_reflector"])
    add("plow", L.principled("V5 | E5 obstacle deflector grey", (0.075, 0.08, 0.085), rough=0.5, metal=0.35))
    add("head_lit", lamp_material("V5 | head lamp (lit on leading cab)", (0.85, 0.87, 0.9), (1.0, 0.96, 0.88), 14.0, "V5_head"))
    add("tail_lit", lamp_material("V5 | tail lamp (lit on trailing cab)", (0.30, 0.01, 0.01), (1.0, 0.010, 0.004), 1.4, "V5_tail"))
    add("lamp_back", L.principled("V5 | lamp unit backing", (0.03, 0.032, 0.035), rough=0.3, metal=0.6))
    for line in ("chuo", "kt", "tokaido", "yamanote"):
        for part in ("front", "side", "runno"):
            png = [os.path.join(TEX_DIR, f"led_{line}_{part}_{v}.png") for v in (0, 1)]
            if all(os.path.exists(p_) for p_ in png):
                add(f"led_{line}_{part}", led_material(f"V5 | LED {line} {part}", png[0], png[1],
                                                        3.0 if part != "runno" else 3.4))
    for m in ("V2 | Chuo orange", "V2 | Keihin Tohoku sky blue", "V2 | Shonan green", "V2 | Yamanote green", "V2 | rail vehicle white"):
        add("mat:" + m, bpy.data.materials[m])
    return mats, lst


def run():
    M, mlist = materials()
    out = {}
    jobs = [(n, k, c) for n, (k, c) in COMMUTER.items()] + [(n, "E5", False) for n in E5_MID + E5_END]
    only = os.environ.get("TB_ONLY")
    if only:
        jobs = [j for j in jobs if any(k.strip() in j[0] for k in only.split(","))]
    for name, kind, cab in jobs:
        col = bpy.data.collections.get(name)
        if col is None:
            continue
        lay = read_layout(col, kind, cab)
        Mk = dict(M)
        line = next((v for k_, v in LINE_OF.items() if k_ in name), None)
        if line and f"led_{line}_side" in M:
            Mk["led_side"] = M[f"led_{line}_side"]
            Mk["led_front"] = M[f"led_{line}_front"]
            Mk["runno"] = M[f"led_{line}_runno"]
        if kind == "E235":
            Mk["door"] = M["e235_green"]
        if kind == "E5":
            Mk["end"] = M["e5_white"]
        retired = 0
        for o in list(col.objects):
            if any(k in o.name for k in RETIRE_KEYS) or (o.name.endswith(" roof") and o.type == 'MESH'):
                L.retire(o)
                retired += 1
        ob = build_body(f"V5 one-piece body | {name}", col, kind, cab, lay, Mk)
        for m in mlist:
            ob.data.materials.append(m)
        col["V5_doors"] = json.dumps([[d[0], d[1], d[2]] for d in lay["doors"]])
        if cab:
            col["V5_cab_front_x"] = lay["x_front"] + 0.015
        col["V5_roof_z"] = 3.83 if kind != "E5" else 3.705
        moved = 0
        if kind == "E5":
            # car numbers sat 38 mm off the old V3 shell; put them on the body side
            for o in col.objects:
                if o.type == 'FONT' and "car number" in o.name and o.parent is None:
                    a, b = bb(o)
                    s = 1 if (a.y + b.y) > 0 else -1
                    inner = min(abs(a.y), abs(b.y))
                    if inner > 1.69:
                        o.location.y -= s * (inner - 1.679)
                        moved += 1
        out[name] = {"kind": kind, "cab": cab, "retired": retired, "windows": len(lay["windows"]),
                     "door_windows": len(lay["door_windows"]), "doors": len(lay["doors"]),
                     "verts": len(ob.data.vertices), "faces": len(ob.data.polygons), "car_numbers_moved": moved}
        if lay.get("nose"):
            col["V5_nose_x_tip"] = lay["nose"]["x_tip"]
            out[name]["nose"] = lay.get("nose_stats", {})
        L.log(name, out[name])
    return out


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    bpy.ops.wm.open_mainfile(filepath=src, load_ui=False, use_scripts=False)
    info = run()
    bpy.context.scene["V5_train_bodies_summary"] = json.dumps(info)
    bpy.ops.wm.save_as_mainfile(filepath=dst, compress=True)
    print("SAVED", dst)
