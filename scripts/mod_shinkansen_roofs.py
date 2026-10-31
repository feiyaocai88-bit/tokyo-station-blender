"""V5.2 module: Shinkansen platform roofs (platforms 14-23).

What the GSI aerial photo shows (rectified, 0.25 m/px; checked over X -60..80):
  * each Shinkansen island has one large roof that covers the platform AND both of its tracks; between
    neighbouring roofs only a dark slot of roughly 2.5-3 m is left (it lies over the space between two tracks)
  * Tokaido Shinkansen roofs (14-19) are white (aerial ~ sRGB 224/227/217)
  * Tohoku Shinkansen roofs: 20-21 pale grey-green (~186/201/191), 22-23 a stronger mint green (~170/197/185)
  * a raised strip about 5.6-6.7 m wide runs along the middle of the Tokaido roofs (two thin lines in the photo)
V4 / V5.1 had the conventional-line canopy on these platforms as well (flat 20 cm slab 3.8-4.0 m above the
platform, platform width only).  That canopy, its diagonals, columns and strip lights on islands 14-23 are retired
and replaced by:
  * a row of columns on the platform centre line (every ~12 m) carrying tapered transverse girders
  * a roof that covers the tracks to OVER m beyond each track centre, sloping gently down to the eaves, with a
    raised central monitor (louvred sides) and fascia bands; standing-seam roofing; panelled soffit
  * a central spine beam and monitor edge beams (lighting lines, hanging points for signs and indicators)
  * hanger rods from the existing hanging platform-number signs up to the new soffit
The girders clear the catenary portals (underside 7.25 m above the deck, portal crossbeams reach 7.0 m).
Section, roof and column data are written to the scene property V5_shinkansen_roofs; hang_z() is used by
mod_platforms to hang its boards from the new roof.

The cross-section itself (heights, slope direction, column form) cannot be read from an aerial photo; it is a
plausible modern platform roof, not a survey.

usage: python -I mod_shinkansen_roofs.py <in.blend> <out.blend>
"""
import sys, os, json, re, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import numpy as np
from mathutils import Vector, Matrix
import v5lib as L
import mod_relayout as RL

SHIN = ("20-21", "22-23", "14-15", "16-17", "18-19")
TOKAIDO = ("14-15", "16-17", "18-19")
ROOF_COLOUR = {"14-15": "white", "16-17": "white", "18-19": "white", "20-21": "greygreen", "22-23": "mint"}
OVER = 1.1             # roof edge beyond each track centre (m)
COL_PITCH = 12.0       # column / girder spacing along the platform (m)
GIRDER_CLEAR = 7.25    # girder underside above the platform deck
EAVE = 8.0             # roof top at the eaves, above the deck
MON_HALF = 2.9         # half width of the raised central monitor
MON_BASE = 8.40        # roof top where it meets the monitor
MON_TOP = 9.20         # monitor roof (at its edges)
MON_OVER = 0.30        # monitor roof overhang
DECK_T = 0.15          # roof deck thickness
SPINE_H = 0.45         # central spine beam depth (framing into the girders)
EDGE_H = 0.40          # monitor edge beam depth below the soffit


# ------------------------------------------------------------------------------------------------ materials
def _seamed(name, colour, pitch, axis, rough, metal, seam_depth=0.6, tint=0.90, spec=0.5):
    """Principled material with joints every `pitch` m along world `axis` (0 = X) and slight colour noise."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(geo.outputs["Position"], sep.inputs[0])
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = 1.0 / pitch
    nt.links.new(sep.outputs[axis], mul.inputs[0])
    fr = nt.nodes.new("ShaderNodeMath"); fr.operation = 'FRACT'; nt.links.new(mul.outputs[0], fr.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.interpolation_type = 'SMOOTHSTEP'
    mr.inputs["From Min"].default_value = 0.0; mr.inputs["From Max"].default_value = min(0.08, 0.05 / pitch * 4)
    mr.inputs["To Min"].default_value = 1.0; mr.inputs["To Max"].default_value = 0.0
    nt.links.new(fr.outputs[0], mr.inputs["Value"])
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = seam_depth
    bump.inputs["Distance"].default_value = 0.03
    nt.links.new(mr.outputs["Result"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    noise = nt.nodes.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 0.15
    nt.links.new(geo.outputs["Position"], noise.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (colour[0] * tint, colour[1] * tint, colour[2] * tint, 1)
    ramp.color_ramp.elements[1].color = (*colour, 1)
    nt.links.new(noise.outputs["Fac"], ramp.inputs[0]); nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Specular IOR Level"].default_value = spec
    m.diffuse_color = (*colour, 1)
    return m


def louvre_material():
    """Monitor side walls: horizontal aluminium slats every 0.12 m with open gaps (transparent), so daylight
    reaches the platform through the monitor."""
    name = "V5 | Shinkansen roof monitor louvres (open slats)"
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    out = nt.nodes.get("Material Output")
    b.inputs["Base Color"].default_value = (0.42, 0.45, 0.47, 1)
    b.inputs["Metallic"].default_value = 0.6
    b.inputs["Roughness"].default_value = 0.35
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(geo.outputs["Position"], sep.inputs[0])
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = 1.0 / 0.12
    nt.links.new(sep.outputs[2], mul.inputs[0])
    fr = nt.nodes.new("ShaderNodeMath"); fr.operation = 'FRACT'; nt.links.new(mul.outputs[0], fr.inputs[0])
    gt = nt.nodes.new("ShaderNodeMath"); gt.operation = 'LESS_THAN'; gt.inputs[1].default_value = 0.45
    nt.links.new(fr.outputs[0], gt.inputs[0])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(gt.outputs[0], mix.inputs[0])
    nt.links.new(b.outputs[0], mix.inputs[1]); nt.links.new(tr.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    m.diffuse_color = (0.42, 0.45, 0.47, 1)
    return m


def materials(isl):
    kind = ROOF_COLOUR[isl]
    # matte painted steel; colours calibrated so that a top view of the model under the scene lighting matches the
    # GSI aerial photo (20-21 ~ sRGB 184/197/187, 22-23 ~ 170/197/185, white roofs clearly the brightest)
    top_col = {"white": (0.86, 0.87, 0.80), "greygreen": (0.44, 0.60, 0.49), "mint": (0.27, 0.58, 0.43)}[kind]
    top = _seamed(f"V5 | Shinkansen roof standing seam ({kind})", top_col, 0.45, 0, 0.75, 0.0, tint=0.92, spec=0.25)
    if kind == "white":
        steel = L.principled("V5 | Shinkansen roof steel white", (0.74, 0.75, 0.74), rough=0.45, metal=0.2)
    else:
        steel = L.principled("V5 | Shinkansen roof steel light grey", (0.62, 0.65, 0.65), rough=0.45, metal=0.25)
    return {
        "top": top, "steel": steel, "column": steel,
        "fascia": steel,
        "soffit": _seamed("V5 | Shinkansen roof soffit panels", (0.70, 0.71, 0.70), 1.2, 0, 0.6, 0.0, seam_depth=0.35, tint=0.96),
        "louvre": louvre_material(),
        "light": L.principled("V5 | Shinkansen roof LED line", (0.9, 0.9, 0.88), rough=0.3, emission=(1.0, 0.96, 0.90), strength=3.0),
    }


# ------------------------------------------------------------------------------------------------ geometry
def deck_top(isl):
    o = bpy.data.objects.get(f"V3 Platform {isl} raised deck")
    if o is None:
        L.log("WARNING no deck object for", isl)
        return 6.45
    return max((o.matrix_world @ Vector(c)).z for c in o.bound_box)


def profile_top(d, dw, de):
    """Roof top height above the deck at lateral offset d (east +); the monitor zone returns MON_BASE."""
    if d < 0:
        t = (d - dw) / (-MON_HALF - dw)
    else:
        t = (de - d) / (de - MON_HALF)
    return EAVE + (MON_BASE - EAVE) * max(0.0, min(1.0, t))


def centre_line(isl, x0, x1, step=2.0):
    v = RL.ISL[isl]
    xs = np.arange(x0, x1 + 1e-6, 0.25)
    yw = np.interp(xs, RL.GX, RL.TGT[v["west"]]); ye = np.interp(xs, RL.GX, RL.TGT[v["east"]])
    yc = (yw + ye) / 2
    s = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(xs), np.diff(yc)))])
    n = max(2, int(round(s[-1] / step)) + 1)
    sq = np.linspace(0.0, s[-1], n)
    X = np.interp(sq, s, xs); C = np.interp(sq, s, yc)
    YW = np.interp(sq, s, yw); YE = np.interp(sq, s, ye)
    A = np.arctan2(np.gradient(C), np.gradient(X))
    return X, C, YW, YE, A, sq


class Roof:
    def __init__(self, isl, x0, x1):
        self.isl = isl
        self.x0, self.x1 = x0, x1
        self.zd = deck_top(isl)
        self.X, self.C, self.YW, self.YE, self.A, self.S = centre_line(isl, x0, x1)
        ca = np.cos(self.A)
        self.dw = -((self.C - self.YW) * ca + OVER)
        self.de = (self.YE - self.C) * ca + OVER

    def p(self, i, d, z):
        a = self.A[i]
        return (float(self.X[i] - math.sin(a) * d), float(self.C[i] + math.cos(a) * d), float(self.zd + z))

    def loft(self, mb, section, mat):
        """section: i -> list of (d, z) (same length for every i); quads between consecutive stations."""
        verts, faces = [], []
        prev = None
        for i in range(len(self.X)):
            pts = section(i)
            base = len(verts)
            verts += [self.p(i, d, z) for d, z in pts]
            if prev is not None:
                for j in range(len(pts) - 1):
                    faces.append((prev + j, base + j, base + j + 1, prev + j + 1))
            prev = base
        mb.add(verts, faces, mat=mat)


def build_roof(R, mb, I):
    n = len(R.X)
    soff = lambda d, i: profile_top(d, R.dw[i], R.de[i]) - DECK_T
    # roof deck: west and east slopes, each a closed strip (top / monitor-side edge / soffit / eave edge)
    for side in (-1, 1):
        def ring(i, side=side):
            dw, de = R.dw[i], R.de[i]
            a, b = (dw, -MON_HALF) if side < 0 else (MON_HALF, de)
            za, zb = profile_top(a, dw, de), profile_top(b, dw, de)
            return [(a, za), (b, zb), (b, zb - DECK_T), (a, za - DECK_T), (a, za)]
        for j, key in ((0, "top"), (2, "soffit"), (3, "fascia")):     # j=1 is covered by the monitor wall
            R.loft(mb, lambda i, j=j, ring=ring: ring(i)[j:j + 2], I[key])
    # monitor: louvred side walls, roof with overhang, fascia edges, underside of the overhang
    for sgn in (-1, 1):
        R.loft(mb, lambda i, s=sgn: [(s * MON_HALF, MON_BASE - DECK_T), (s * MON_HALF, MON_TOP - 0.06)], I["louvre"])
    mo = MON_HALF + MON_OVER
    R.loft(mb, lambda i: [(-mo, MON_TOP - 0.04), (0.0, MON_TOP + 0.10), (mo, MON_TOP - 0.04)], I["top"])
    R.loft(mb, lambda i: [(-mo, MON_TOP - 0.16), (-mo, MON_TOP - 0.04)], I["fascia"])
    R.loft(mb, lambda i: [(mo, MON_TOP - 0.04), (mo, MON_TOP - 0.16)], I["fascia"])
    R.loft(mb, lambda i: [(mo, MON_TOP - 0.16), (-mo, MON_TOP - 0.16)], I["soffit"])
    # eave fascia with a gutter lip
    R.loft(mb, lambda i: [(R.dw[i] + 0.05, EAVE + 0.14), (R.dw[i] - 0.06, EAVE + 0.14), (R.dw[i] - 0.06, EAVE - 0.50),
                          (R.dw[i] + 0.12, EAVE - 0.50), (R.dw[i] + 0.12, EAVE - DECK_T)], I["fascia"])
    R.loft(mb, lambda i: [(R.de[i] - 0.12, EAVE - DECK_T), (R.de[i] - 0.12, EAVE - 0.50), (R.de[i] + 0.06, EAVE - 0.50),
                          (R.de[i] + 0.06, EAVE + 0.14), (R.de[i] - 0.05, EAVE + 0.14)], I["fascia"])
    # roof ends: end plates over the roof thickness plus the monitor gable
    for i in (0, n - 1):
        dw, de = R.dw[i], R.de[i]
        sec = [(dw - 0.06, EAVE + 0.14), (-MON_HALF, MON_BASE + 0.06), (-mo, MON_TOP - 0.04), (0.0, MON_TOP + 0.12),
               (mo, MON_TOP - 0.04), (MON_HALF, MON_BASE + 0.06), (de + 0.06, EAVE + 0.14), (de + 0.06, EAVE - 0.50),
               (MON_HALF + 0.5, GIRDER_CLEAR), (-MON_HALF - 0.5, GIRDER_CLEAR), (dw - 0.06, EAVE - 0.50)]
        idx = list(range(len(sec)))
        mb.add([R.p(i, d, z) for d, z in sec], [tuple(idx if i else reversed(idx))], mat=I["fascia"])
    # monitor edge beams (deck edge at the monitor opening) and the central spine beam
    for sgn in (-1, 1):
        def edge_beam(i, s=sgn):
            z1 = MON_BASE - DECK_T; z0 = z1 - EDGE_H
            a, b = s * (MON_HALF - 0.02), s * (MON_HALF + 0.24)
            return [(a, z1), (a, z0), (b, z0), (b, z1)]
        R.loft(mb, edge_beam, I["steel"])
        R.loft(mb, lambda i, s=sgn: [(s * (MON_HALF + 0.03), MON_BASE - DECK_T - EDGE_H - 0.01),
                                     (s * (MON_HALF + 0.19), MON_BASE - DECK_T - EDGE_H - 0.01)], I["light"])
    R.loft(mb, lambda i: [(-0.15, GIRDER_CLEAR + SPINE_H), (-0.15, GIRDER_CLEAR), (0.15, GIRDER_CLEAR), (0.15, GIRDER_CLEAR + SPINE_H)], I["steel"])
    R.loft(mb, lambda i: [(-0.08, GIRDER_CLEAR - 0.01), (0.08, GIRDER_CLEAR - 0.01)], I["light"])
    # LED lines under the soffit over the platform edges
    for sgn in (-1, 1):
        dd = sgn * (MON_HALF + 1.7)
        R.loft(mb, lambda i, dd=dd: [(dd - 0.09, soff(dd, i) - 0.04), (dd + 0.09, soff(dd, i) - 0.04)], I["light"])
        R.loft(mb, lambda i, dd=dd: [(dd - 0.11, soff(dd, i)), (dd - 0.11, soff(dd, i) - 0.05), (dd + 0.11, soff(dd, i) - 0.05),
                                     (dd + 0.11, soff(dd, i))], I["steel"])
    # columns and tapered transverse girders
    cols = []
    total = R.S[-1]
    m = max(1, int(total // COL_PITCH))
    off = (total - m * COL_PITCH) / 2
    for k in range(m + 1):
        s = off + k * COL_PITCH
        if s < 3.0 or s > total - 3.0:
            continue
        cx = float(np.interp(s, R.S, R.X)); cy = float(np.interp(s, R.S, R.C)); a = float(np.interp(s, R.S, R.A))
        dw = float(np.interp(s, R.S, R.dw)); de = float(np.interp(s, R.S, R.de))
        cols.append((round(cx, 2), round(cy, 2)))
        zg = R.zd + GIRDER_CLEAR
        L.tube(mb, [Vector((cx, cy, R.zd)), Vector((cx, cy, zg - 0.30))], 0.25, sides=16, mat=I["column"])
        L.box(mb, 0, 0, 0, 0.80, 0.80, 0.05, I["column"], frame=_frame(cx, cy, R.zd + 0.025, a))
        L.box(mb, 0, 0, 0, 0.60, 0.60, 0.30, I["column"], frame=_frame(cx, cy, zg - 0.15, a))
        top = [(dw + 0.15, profile_top(dw + 0.15, dw, de) - DECK_T), (-MON_HALF, MON_BASE - DECK_T),
               (MON_HALF, MON_BASE - DECK_T), (de - 0.15, profile_top(de - 0.15, dw, de) - DECK_T)]
        sec = top + [(de - 0.15, EAVE - 0.50), (MON_HALF + 0.5, GIRDER_CLEAR), (-MON_HALF - 0.5, GIRDER_CLEAR), (dw + 0.15, EAVE - 0.50)]
        ca, sa = math.cos(a), math.sin(a)
        verts = []
        for t_off in (-0.16, 0.16):
            for d, z in sec:
                verts.append((cx - sa * d + ca * t_off, cy + ca * d + sa * t_off, R.zd + z))
        nn = len(sec)
        faces = [tuple(range(nn)), tuple(range(2 * nn - 1, nn - 1, -1))]
        faces += [(j, (j + 1) % nn, nn + (j + 1) % nn, nn + j) for j in range(nn)]
        mb.add(verts, faces, mat=I["steel"])
    return cols


def _frame(x, y, z, a):
    c, s = math.cos(a), math.sin(a)
    return Matrix(((c, -s, 0, x), (s, c, 0, y), (0, 0, 1, z), (0, 0, 0, 1)))


# ------------------------------------------------------------------------------------------------ hanging points
def _local(isl, x, y):
    """Lateral offset d of (x, y) from the island centre line, the eave offsets dw/de there, and the local angle."""
    v = RL.ISL[isl]
    xs = np.array([x - 0.5, x, x + 0.5])
    yw = np.interp(xs, RL.GX, RL.TGT[v["west"]]); ye = np.interp(xs, RL.GX, RL.TGT[v["east"]])
    c = (yw + ye) / 2
    a = math.atan2(c[2] - c[0], 1.0)
    d = (y - c[1]) * math.cos(a)
    dw = -((c[1] - yw[1]) * math.cos(a) + OVER); de = (ye[1] - c[1]) * math.cos(a) + OVER
    return d, dw, de, a


def island_of(x, y):
    for isl in SHIN:
        if isl not in RL.ISL:
            continue
        v = RL.ISL[isl]
        if not (v["Q"][0] - 0.5 <= x <= v["Q"][1] + 0.5):
            continue
        yw = float(np.interp(x, RL.GX, RL.TGT[v["west"]])); ye = float(np.interp(x, RL.GX, RL.TGT[v["east"]]))
        if yw - OVER < y < ye + OVER:
            return isl
    return None


def hang_z(isl, x, y, z_deck):
    """Height (world z) of the structure a hanger at plan point (x, y) can be fixed to, or None.
    Soffit outside the monitor, the monitor edge beams next to it, the spine beam on the centre line."""
    d, dw, de, _a = _local(isl, x, y)
    ad = abs(d)
    if ad >= MON_HALF + 0.25:
        return z_deck + profile_top(d, dw, de) - DECK_T
    if ad >= MON_HALF - 0.05:
        return z_deck + MON_BASE - DECK_T - EDGE_H
    if ad <= 0.15:
        return z_deck + GIRDER_CLEAR
    return None


def hang_point(isl, x, y, z_deck):
    """Fixing point for a hanger starting at plan point (x, y): straight above where the roof has structure,
    otherwise sideways on the spine beam (centre zone) or the monitor edge beam (outer part of the monitor zone)."""
    z = hang_z(isl, x, y, z_deck)
    if z is not None:
        return x, y, z
    d, dw, de, a = _local(isl, x, y)
    tgt = 0.0 if abs(d) < MON_HALF / 2 else math.copysign(MON_HALF + 0.1, d)
    nx, ny = -math.sin(a), math.cos(a)
    x2, y2 = x + (tgt - d) * nx, y + (tgt - d) * ny
    return x2, y2, hang_z(isl, x2, y2, z_deck)


# ------------------------------------------------------------------------------------------------ retire old
def in_band(isl, x, y, pad=2.5):
    v = RL.ISL[isl]
    yw = float(np.interp(x, RL.GX, RL.TGT[v["west"]])); ye = float(np.interp(x, RL.GX, RL.TGT[v["east"]]))
    return yw - pad < y < ye + pad


def retire_old(isl):
    n = 0
    signs = []
    for o in list(bpy.data.objects):
        if o.get("V5_retired") or o.type not in ('MESH', 'CURVE'):
            continue
        nm = o.name
        if re.match(r"V3 platform canopy %s(\.\d+)?$" % isl, nm):
            L.retire(o); n += 1
            continue
        kind = re.match(r"V3 platform (canopy diagonal|column|strip light|numbered sign|route colour)", nm)
        if not kind:
            continue
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        x = sum(v.x for v in bb) / 8; y = sum(v.y for v in bb) / 8
        if not in_band(isl, x, y):
            continue
        if kind.group(1) in ("numbered sign", "route colour"):
            if kind.group(1) == "numbered sign":
                signs.append(o)
            continue
        L.retire(o); n += 1
    return n, signs


def sign_hangers(mb, signs, roofs, mat):
    """Two rods from the top of every hanging platform-number sign up to the new roof."""
    n = 0
    for o in signs:
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        x = sum(v.x for v in bb) / 8; y = sum(v.y for v in bb) / 8; ztop = max(v.z for v in bb)
        R = next((r for r in roofs if r.X[0] - 1 <= x <= r.X[-1] + 1 and in_band(r.isl, x, y)), None)
        if R is None:
            continue
        i = int(np.argmin(np.abs(R.X - x)))
        a = float(R.A[i])
        half = (max(v.x for v in bb) - min(v.x for v in bb)) / 2 - 0.4
        for t in (-half, half):
            px, py = x + math.cos(a) * t, y + math.sin(a) * t
            zr = hang_z(R.isl, px, py, R.zd)
            if zr is None or zr <= ztop + 0.05:
                continue
            L.box(mb, px, py, (ztop + zr) / 2, 0.04, 0.04, zr - ztop, mat)
        n += 1
    return n


# ------------------------------------------------------------------------------------------------ run
def run():
    col = L.collection("V5_Shinkansen_Roofs")
    out, roofs, all_signs = {}, [], []
    for isl in SHIN:
        if isl not in RL.ISL:
            continue
        x0, x1 = RL.ISL[isl]["Q"]
        retired, signs = retire_old(isl)
        all_signs += signs
        R = Roof(isl, x0, x1)
        roofs.append(R)
        M = materials(isl)
        mats = list(dict.fromkeys(M.values()))
        I = {k: mats.index(v) for k, v in M.items()}
        mb = L.MeshBuilder()
        cols = build_roof(R, mb, I)
        ob = mb.build(f"V5 Shinkansen roof {isl} ({'Tokaido' if isl in TOKAIDO else 'Tohoku'})", col, mats)
        ob["V5_shinkansen_roof"] = isl
        w0 = R.de - R.dw
        out[isl] = {"retired_v3_parts": retired, "columns": cols, "z_deck": round(R.zd, 3),
                    "z_girder_underside": round(R.zd + GIRDER_CLEAR, 3), "z_eave": round(R.zd + EAVE, 3),
                    "z_monitor_top": round(R.zd + MON_TOP + 0.10, 3), "x_extent": [x0, x1],
                    "width_m": [round(float(w0.min()), 2), round(float(w0.max()), 2)],
                    "colour": ROOF_COLOUR[isl], "verts": len(ob.data.vertices)}
    if all_signs:
        mb = L.MeshBuilder()
        steel = L.principled("V5 | platform fittings dark grey", (0.07, 0.075, 0.08), rough=0.45, metal=0.5)
        n = sign_hangers(mb, all_signs, roofs, 0)
        if n:
            mb.build("V5 Shinkansen roofs | hanger rods for platform-number signs", col, [steel])
        out["_sign_hangers"] = n
    out["_section"] = {"over_track_m": OVER, "column_pitch_m": COL_PITCH, "girder_clear_m": GIRDER_CLEAR,
                       "eave_m": EAVE, "monitor_half_m": MON_HALF, "monitor_base_m": MON_BASE, "monitor_top_m": MON_TOP}
    for k, v in out.items():
        L.log(k, {kk: vv for kk, vv in v.items() if kk != "columns"} if isinstance(v, dict) else v)
    return out


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    bpy.ops.wm.open_mainfile(filepath=src, load_ui=False, use_scripts=False)
    info = run()
    bpy.context.scene["V5_shinkansen_roofs"] = json.dumps(info)
    bpy.ops.wm.save_as_mainfile(filepath=dst, compress=True)
    print("SAVED", dst)
