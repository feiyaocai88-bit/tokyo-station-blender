"""V9 module 1: the JR Sobu / Yokosuka underground station (総武地下駅) under the Marunouchi plaza.

Builds (station frame and levels: see v9geo.py):
  * cut-and-cover box: base slab, diaphragm walls, end walls with four tunnel mouths and 30 m tunnel stubs; five levels
    (B5 platforms, B4 concourse, B3 / B2 machine floors, B1 concourse) in the middle part, only B5 + B4 where the
    Tokyo Metro Marunouchi Line passes above (south-west part) and at the north-east end (outside the plinth)
  * B5: two island platforms (10.6 m) and four tracks on concrete slab track, round columns with red / white guard
    bands and column numbers, cream spandrel ceilings with bulkheads and fluorescent rows, dark over-track soffit with
    transverse beams, rigid overhead conductor at the raised-pantograph height, track-wall panels, station-name signs
    and posters, departure boards with clocks, track-number and exit signs, stop boards, starting signals, benches,
    vending machines, platform-end fences
  * 12 stair + escalator groups B5 -> B4 (brick-tiled enclosures, parametric escalators), two lifts
  * B4 concourse with glazed balustrades around the stair wells, two long escalator / stair banks B4 -> B1 in
    inclined shafts, B1 concourse with ticket gates and the passage towards 丸の内地下中央口
  * B2 / B3 machine rooms (fans at the ventilation shaft, switchgear), the ventilation shaft up to the existing tower
  * context: the Marunouchi Line box tunnel crossing above the south-west part (simplified)
Every object is placed with its matrix_world = station frame; nothing is changed in the existing model.

usage: blender -b in.blend --python-exit-code 1 -P mod9_sobu_station.py -- out.blend report.json
"""
import sys, os, json, math
import numpy as np
import bpy
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v5lib as L
import v9geo as G

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGV[0] if ARGV else None
REPORT = ARGV[1] if len(ARGV) > 1 else None
TEX = os.path.join(HERE, "textures")
FR = G.frame_matrix()
TAN30 = math.tan(math.radians(30.0))
REP = {"objects": [], "counts": {}, "warnings": []}
RNG = np.random.default_rng(9)
Z = Vector((0, 0, 1))


def cnt(k, n=1):
    REP["counts"][k] = REP["counts"].get(k, 0) + n


# ====================================================================== materials
def _new(name):
    m = bpy.data.materials.get(name)
    if m is not None:
        return m, None
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    return m, m.node_tree


def basic(name, col, rough=0.6, metal=0.0, emit=None, strength=0.0, transmission=0.0, ior=1.45):
    m, nt = _new(name)
    if nt is None:
        return m
    b = nt.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*col, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit is not None:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = strength
    if transmission:
        b.inputs["Transmission Weight"].default_value = transmission
        b.inputs["IOR"].default_value = ior
    m.diffuse_color = (*col, 1)
    return m


def brick(name, c1, c2, mortar, w, h, msize, rough=0.6, bump=0.0, offset=0.5, metal=0.0):
    """Tiles / panel joints from a Brick texture on the metre UVs (u, v)."""
    m, nt = _new(name)
    if nt is None:
        return m
    b = nt.nodes.get("Principled BSDF")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    br = nt.nodes.new("ShaderNodeTexBrick")
    br.offset = offset
    br.inputs["Color1"].default_value = (*c1, 1)
    br.inputs["Color2"].default_value = (*c2, 1)
    br.inputs["Mortar"].default_value = (*mortar, 1)
    br.inputs["Scale"].default_value = 1.0
    br.inputs["Mortar Size"].default_value = msize
    br.inputs["Brick Width"].default_value = w
    br.inputs["Row Height"].default_value = h
    nt.links.new(tc.outputs["UV"], br.inputs["Vector"])
    nt.links.new(br.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if bump:
        bm = nt.nodes.new("ShaderNodeBump")
        bm.inputs["Strength"].default_value = bump
        nt.links.new(br.outputs["Fac"], bm.inputs["Height"])
        nt.links.new(bm.outputs["Normal"], b.inputs["Normal"])
    m.diffuse_color = (*c1, 1)
    return m


def noisy(name, c1, c2, scale=3.0, rough=0.85, bump=0.15):
    m, nt = _new(name)
    if nt is None:
        return m
    b = nt.nodes.get("Principled BSDF")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = 6.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*c1, 1)
    ramp.color_ramp.elements[1].color = (*c2, 1)
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    if bump:
        bm = nt.nodes.new("ShaderNodeBump")
        bm.inputs["Strength"].default_value = bump
        bm.inputs["Distance"].default_value = 0.02
        nt.links.new(nz.outputs["Fac"], bm.inputs["Height"])
        nt.links.new(bm.outputs["Normal"], b.inputs["Normal"])
    m.diffuse_color = (*c1, 1)
    return m


def image(name, png, strength=0.0, rough=0.45, scale=None):
    m, nt = _new(name)
    if nt is None:
        return m
    b = nt.nodes.get("Principled BSDF")
    path = os.path.join(TEX, png)
    img = bpy.data.images.get(png) or bpy.data.images.load(path)
    img.pack()
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = img; t.interpolation = 'Linear'
    if scale:
        tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (scale, scale, 1)
        nt.links.new(tc.outputs["UV"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], t.inputs["Vector"])
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    if strength:
        nt.links.new(t.outputs["Color"], b.inputs["Emission Color"])
        b.inputs["Emission Strength"].default_value = strength
    return m


def materials():
    M = {}
    M["conc"] = noisy("V9 | cast-in-place concrete (box structure)", (0.36, 0.355, 0.34), (0.47, 0.46, 0.44), 2.0)
    M["conc_floor"] = noisy("V9 | machine-room floor (sealed concrete)", (0.30, 0.33, 0.31), (0.36, 0.39, 0.37), 1.0, 0.6, 0.05)
    M["soffit"] = noisy("V9 | dark painted soffit (over the tracks)", (0.028, 0.029, 0.031), (0.05, 0.05, 0.052), 1.5, 0.8)
    M["invert"] = noisy("V9 | track-zone invert", (0.10, 0.10, 0.095), (0.17, 0.165, 0.155), 3.0)
    M["trackbed"] = noisy("V9 | concrete slab track", (0.20, 0.20, 0.19), (0.30, 0.29, 0.27), 4.0)
    M["sleeper"] = basic("V9 | concrete sleeper blocks", (0.40, 0.39, 0.37), 0.8)
    M["rail"] = basic("V9 | rail steel", (0.30, 0.30, 0.30), 0.35, 1.0)
    M["tile"] = brick("V9 | platform floor tiles (cream ceramic)", (0.60, 0.58, 0.52), (0.55, 0.535, 0.49), (0.40, 0.39, 0.36),
                      0.30, 0.30, 0.004, 0.35, 0.05)
    M["tactile"] = brick("V9 | tactile paving (yellow)", (0.78, 0.55, 0.04), (0.74, 0.52, 0.04), (0.55, 0.38, 0.03),
                         0.30, 0.30, 0.006, 0.55, 0.2)
    M["coping"] = basic("V9 | platform edge coping", (0.52, 0.52, 0.50), 0.6)
    M["plat_face"] = basic("V9 | under-platform recess (dark)", (0.025, 0.025, 0.025), 0.9)
    M["col"] = basic("V9 | column paint (cream)", (0.70, 0.66, 0.56), 0.45)
    M["col_base"] = basic("V9 | column skirting (dark grey)", (0.08, 0.08, 0.08), 0.5)
    M["stripe"] = image("V9 | column guard band (red / white)", "v9_column_stripes.png", 0.0, 0.4, 2.0)
    M["colnum"] = image("V9 | column number plates", "v9_column_numbers.png", 0.0, 0.4)
    M["ceil"] = brick("V9 | cream metal spandrel ceiling", (0.66, 0.62, 0.50), (0.66, 0.62, 0.50), (0.42, 0.39, 0.31),
                      60.0, 0.10, 0.012, 0.4, 0.15, 0.0)
    M["bulk"] = basic("V9 | ceiling bulkheads (cream)", (0.70, 0.66, 0.54), 0.5)
    M["fix_body"] = basic("V9 | light fitting housing (white)", (0.80, 0.80, 0.78), 0.4)
    M["lamp"] = basic("V9 | fluorescent lamp (lit)", (0.9, 0.9, 0.88), 0.3, 0.0, (1.0, 0.96, 0.90), 14.0)
    M["lamp_dim"] = basic("V9 | track-wall lamp (lit, dim)", (0.9, 0.9, 0.88), 0.3, 0.0, (1.0, 0.92, 0.80), 5.0)
    M["wall_pan"] = brick("V9 | track-wall panels (beige, vertical joints)", (0.50, 0.48, 0.41), (0.50, 0.48, 0.41),
                          (0.22, 0.21, 0.18), 1.5, 80.0, 0.015, 0.55, 0.1, 0.0)
    M["wall_low"] = basic("V9 | track-wall dado (dark)", (0.045, 0.045, 0.045), 0.7)
    M["brick"] = brick("V9 | brown brick tiles (stair enclosures)", (0.30, 0.14, 0.08), (0.26, 0.12, 0.07), (0.45, 0.42, 0.38),
                       0.227, 0.060, 0.004, 0.55, 0.05)
    M["stain"] = basic("V9 | brushed stainless", (0.62, 0.62, 0.63), 0.28, 1.0)
    M["steel_dk"] = basic("V9 | dark grey steel", (0.06, 0.065, 0.07), 0.5, 0.6)
    M["glass"] = basic("V9 | balustrade glass", (0.82, 0.88, 0.86), 0.02, 0.0, None, 0.0, 1.0, 1.5)
    M["frost"] = basic("V9 | frosted glass (lift shafts)", (0.80, 0.84, 0.84), 0.35, 0.0, None, 0.0, 0.9, 1.5)
    M["rubber"] = basic("V9 | handrail rubber (black)", (0.012, 0.012, 0.012), 0.35)
    M["step"] = brick("V9 | escalator step (grooved aluminium)", (0.20, 0.20, 0.21), (0.20, 0.20, 0.21), (0.05, 0.05, 0.05),
                      0.007, 80.0, 0.0025, 0.45, 0.3, 0.0, 0.8)
    M["step_edge"] = basic("V9 | escalator step demarcation (yellow)", (0.85, 0.62, 0.03), 0.5)
    M["plate"] = brick("V9 | escalator landing plate", (0.45, 0.45, 0.46), (0.45, 0.45, 0.46), (0.2, 0.2, 0.2),
                       0.06, 80.0, 0.006, 0.4, 0.2, 0.0, 0.9)
    M["tread"] = basic("V9 | stair treads (grey granite)", (0.38, 0.37, 0.35), 0.55)
    M["riser"] = basic("V9 | stair risers", (0.30, 0.29, 0.28), 0.6)
    M["nosing"] = basic("V9 | stair nosing (dark anti-slip)", (0.06, 0.06, 0.06), 0.7)
    M["terrazzo"] = brick("V9 | concourse floor (terrazzo tiles)", (0.40, 0.38, 0.34), (0.35, 0.33, 0.30), (0.24, 0.23, 0.21),
                          0.60, 0.60, 0.004, 0.3, 0.02)
    M["c_ceil"] = brick("V9 | concourse ceiling panels", (0.62, 0.61, 0.58), (0.62, 0.61, 0.58), (0.40, 0.40, 0.38),
                        0.60, 0.60, 0.006, 0.6, 0.0)
    M["c_wall"] = brick("V9 | concourse wall panels", (0.55, 0.50, 0.42), (0.52, 0.48, 0.40), (0.30, 0.28, 0.24),
                        1.20, 0.60, 0.004, 0.4, 0.0)
    M["door"] = basic("V9 | staff doors (grey)", (0.25, 0.26, 0.27), 0.5, 0.3)
    M["conductor"] = basic("V9 | aluminium conductor bar", (0.58, 0.58, 0.60), 0.35, 1.0)
    M["wire"] = basic("V9 | copper contact wire", (0.45, 0.22, 0.10), 0.3, 1.0)
    M["insul"] = basic("V9 | porcelain insulators (brown)", (0.22, 0.10, 0.05), 0.25)
    M["sign_sta"] = image("V9 | station name sign 東京 JO19 (backlit)", "v9_station_sign.png", 2.2)
    M["sign_trk"] = image("V9 | track number signs (backlit)", "v9_track_signs.png", 2.0)
    M["sign_dep"] = image("V9 | departure boards (LED)", "v9_departure_boards.png", 3.0)
    M["sign_way"] = image("V9 | wayfinding signs (backlit)", "v9_wayfinding.png", 2.2)
    M["poster"] = image("V9 | posters (lit)", "v9_posters.png", 1.0)
    M["stop"] = image("V9 | stop position board 15", "stop_15.png", 0.3)
    M["housing"] = basic("V9 | sign housings (black)", (0.015, 0.015, 0.016), 0.4, 0.3)
    M["clockface"] = basic("V9 | clock face", (0.85, 0.85, 0.83), 0.3, 0.0, (1, 1, 1), 0.6)
    M["sig_red"] = basic("V9 | signal lens red (lit)", (0.3, 0.0, 0.0), 0.2, 0.0, (1.0, 0.02, 0.01), 20.0)
    M["sig_green"] = basic("V9 | signal lens green (lit)", (0.0, 0.2, 0.1), 0.2, 0.0, (0.05, 1.0, 0.45), 20.0)
    M["sig_off"] = basic("V9 | signal lens (unlit)", (0.03, 0.03, 0.03), 0.15)
    M["bench_seat"] = basic("V9 | bench seats (blue plastic)", (0.02, 0.10, 0.30), 0.4)
    M["vend"] = basic("V9 | vending machine body", (0.75, 0.76, 0.78), 0.35, 0.4)
    M["vend_lit"] = basic("V9 | vending machine display (lit)", (0.5, 0.6, 0.7), 0.3, 0.0, (0.85, 0.92, 1.0), 3.0)
    M["gate"] = basic("V9 | ticket gate cabinets (white)", (0.82, 0.82, 0.80), 0.35)
    M["gate_top"] = basic("V9 | ticket gate top (dark blue)", (0.01, 0.05, 0.16), 0.3)
    M["gate_lit"] = basic("V9 | ticket gate indicator (lit)", (0.1, 0.4, 0.2), 0.3, 0.0, (0.2, 1.0, 0.4), 6.0)
    M["equip"] = basic("V9 | machinery (grey-green paint)", (0.22, 0.28, 0.25), 0.5, 0.2)
    M["cabinet"] = basic("V9 | switchgear cabinets (beige)", (0.55, 0.53, 0.46), 0.45)
    M["duct"] = basic("V9 | galvanised duct", (0.48, 0.49, 0.50), 0.4, 0.8)
    M["dark"] = basic("V9 | tunnel darkness", (0.0, 0.0, 0.0), 1.0)
    M["lift_car"] = basic("V9 | lift car interior (lit)", (0.7, 0.7, 0.68), 0.4, 0.0, (1.0, 0.97, 0.92), 2.0)
    M["locker"] = brick("V9 | coin lockers (grey steel doors)", (0.60, 0.62, 0.64), (0.58, 0.60, 0.62), (0.15, 0.15, 0.16),
                        0.32, 0.30, 0.006, 0.35, 0.1, 0.0, 0.5)
    M["hydrant"] = basic("V9 | fire hydrant cabinets (red)", (0.55, 0.02, 0.02), 0.35)
    M["maru"] = noisy("V9 | Marunouchi Line tunnel concrete (context)", (0.40, 0.39, 0.37), (0.50, 0.49, 0.47), 2.0)
    return M


# ====================================================================== geometry helpers (local coordinates)
def new_obj(mb, name, col, mats, props=None):
    ob = mb.build(name, col, mats)
    ob.matrix_world = FR
    ob["V9_sobu"] = True
    if props:
        for k, v in props.items():
            ob[k] = v
    REP["objects"].append(name)
    return ob


class Mats:
    """Material slot list for one MeshBuilder object."""

    def __init__(self, M):
        self.M = M; self.lst = []; self.idx = {}

    def __call__(self, key):
        if key not in self.idx:
            self.idx[key] = len(self.lst); self.lst.append(self.M[key])
        return self.idx[key]


_PAR = {(0, 1, 2): 1, (1, 2, 0): 1, (2, 0, 1): 1, (0, 2, 1): -1, (1, 0, 2): -1, (2, 1, 0): -1}


def grid_solid(mb, axes, ur, vr, wr, holes, m_pos, m_neg, m_side):
    """Rectangular solid u x v x w (axes = indices of u, v, w in xyz) with rectangular holes (u0, u1, v0, v1)."""
    U, V, W = axes
    par = _PAR[axes]
    us = {ur[0], ur[1]}; vs = {vr[0], vr[1]}
    hs = []
    for h in holes:
        a, b, c, d = max(h[0], ur[0]), min(h[1], ur[1]), max(h[2], vr[0]), min(h[3], vr[1])
        if b - a > 1e-6 and d - c > 1e-6:
            hs.append((a, b, c, d)); us |= {a, b}; vs |= {c, d}
    us = sorted(us); vs = sorted(vs)
    nu, nv = len(us) - 1, len(vs) - 1
    fill = np.ones((nu, nv), bool)
    for i in range(nu):
        uc = (us[i] + us[i + 1]) / 2
        for j in range(nv):
            vc = (vs[j] + vs[j + 1]) / 2
            for a, b, c, d in hs:
                if a <= uc <= b and c <= vc <= d:
                    fill[i, j] = False
                    break

    def P(u, v, w):
        p = [0.0, 0.0, 0.0]; p[U] = u; p[V] = v; p[W] = w
        return tuple(p)

    def quad(pts, m):
        if par < 0:
            pts = pts[::-1]
        mb.add(pts, [(0, 1, 2, 3)], m)

    w0, w1 = wr
    for i in range(nu):
        for j in range(nv):
            if not fill[i, j]:
                continue
            u0, u1, v0, v1 = us[i], us[i + 1], vs[j], vs[j + 1]
            quad([P(u0, v0, w1), P(u1, v0, w1), P(u1, v1, w1), P(u0, v1, w1)], m_pos)
            quad([P(u0, v1, w0), P(u1, v1, w0), P(u1, v0, w0), P(u0, v0, w0)], m_neg)
            if i == nu - 1 or not fill[i + 1, j]:
                quad([P(u1, v0, w0), P(u1, v1, w0), P(u1, v1, w1), P(u1, v0, w1)], m_side)
            if i == 0 or not fill[i - 1, j]:
                quad([P(u0, v0, w1), P(u0, v1, w1), P(u0, v1, w0), P(u0, v0, w0)], m_side)
            if j == nv - 1 or not fill[i, j + 1]:
                quad([P(u0, v1, w0), P(u0, v1, w1), P(u1, v1, w1), P(u1, v1, w0)], m_side)
            if j == 0 or not fill[i, j - 1]:
                quad([P(u1, v0, w0), P(u1, v0, w1), P(u0, v0, w1), P(u0, v0, w0)], m_side)


def slab(mb, xr, yr, zr, holes, m_top, m_bot, m_side):
    grid_solid(mb, (0, 1, 2), xr, yr, zr, holes, m_top, m_bot, m_side)


def wall_x(mb, xr, yr, zr, holes_xz, m_ypos, m_yneg, m_side):
    """Wall along x (thickness in y) with openings (x0, x1, z0, z1)."""
    grid_solid(mb, (0, 2, 1), xr, zr, yr, holes_xz, m_ypos, m_yneg, m_side)


def wall_y(mb, yr, xr, zr, holes_yz, m_xpos, m_xneg, m_side):
    """Wall along y (thickness in x) with openings (y0, y1, z0, z1)."""
    grid_solid(mb, (1, 2, 0), yr, zr, xr, holes_yz, m_xpos, m_xneg, m_side)


def bx(mb, x0, x1, y0, y1, z0, z1, m):
    x0, x1 = min(x0, x1), max(x0, x1); y0, y1 = min(y0, y1), max(y0, y1)
    L.box(mb, (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2, x1 - x0, y1 - y0, z1 - z0, m)


class Fr:
    """Group frame: u along the rising direction s (+1 / -1 in x), w across (mirrored with s), z absolute."""

    def __init__(self, xf, yc, s):
        self.xf, self.yc, self.s = xf, yc, s

    def __call__(self, u, w, z):
        return (self.xf + self.s * u, self.yc + self.s * w, z)

    def box(self, mb, u0, u1, w0, w1, z0, z1, m):
        a = self(u0, w0, z0); b = self(u1, w1, z1)
        bx(mb, a[0], b[0], a[1], b[1], a[2], b[2], m)


def prism_uz(mb, fr, poly, w0, w1, m_cap, m_side_fn):
    """Extrude a CCW (u, z) polygon across w0..w1 in a group frame; side material chosen per edge."""
    n = len(poly)
    vs = [fr(u, w0, z) for u, z in poly] + [fr(u, w1, z) for u, z in poly]
    mb.add(vs, [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))], m_cap)
    for i in range(n):
        j = (i + 1) % n
        du, dz = poly[j][0] - poly[i][0], poly[j][1] - poly[i][1]
        mb.add([vs[n + i], vs[n + j], vs[j], vs[i]], [(0, 1, 2, 3)], m_side_fn(du, dz))


def extrude_x(mb, poly_yz, x0, x1, m):
    n = len(poly_yz)
    vs = [(x0, y, z) for y, z in poly_yz] + [(x1, y, z) for y, z in poly_yz]
    faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    mb.add(vs, faces, m)


def sign_quad(mb, c, n, W, H, uv, m):
    """Quad centred at c facing horizontal direction n (unit, local xy); uv = (u0, v0, u1, v1)."""
    r = Vector((-n[1], n[0], 0.0)); c = Vector(c)
    p0 = c - r * W / 2 - Z * H / 2; p1 = c + r * W / 2 - Z * H / 2
    p2 = c + r * W / 2 + Z * H / 2; p3 = c - r * W / 2 + Z * H / 2
    u0, v0, u1, v1 = uv
    mb.add([tuple(p0), tuple(p1), tuple(p2), tuple(p3)], [(0, 1, 2, 3)], m, uvs=[[(u0, v0), (u1, v0), (u1, v1), (u0, v1)]])


def atlas(i, cols, rows):
    c, r = i % cols, i // cols
    return (c / cols, 1 - (r + 1) / rows, (c + 1) / cols, 1 - r / rows)


def area_light(col, name, x, y, z, sx, sy, energy, color=(1.0, 0.96, 0.90)):
    ld = bpy.data.lights.new(name, 'AREA')
    ld.shape = 'RECTANGLE'; ld.size = sx; ld.size_y = sy; ld.energy = energy; ld.color = color
    ob = bpy.data.objects.new(name, ld)
    col.objects.link(ob)
    ob.matrix_world = FR @ Matrix.Translation((x, y, z))
    ob.visible_camera = False
    ob.visible_glossy = False
    ob["V9_sobu"] = True
    cnt("area_lights")
    return ob


# ====================================================================== layout queries
def enclosures():
    """[(x0, x1, y0, y1, isl, gx)] footprints of the 12 stair groups."""
    out = []
    for isl in G.ISL:
        for gx in G.GROUP_X:
            xf, s, yc = G.group_frame(gx, isl)
            a, b = sorted((xf, xf + s * G.GROUP_LEN))
            out.append((a, b, yc - G.ENCL_HALF, yc + G.ENCL_HALF, isl, gx))
    return out


ENCL = enclosures()


def elev_rect(isl, pad=0.0):
    x, y, _ = G.ELEV[isl]
    return (x - G.ELEV_SIZE[0] / 2 - pad, x + G.ELEV_SIZE[0] / 2 + pad, y - G.ELEV_SIZE[1] / 2 - pad, y + G.ELEV_SIZE[1] / 2 + pad)


def in_rect(x, y, r, pad=0.0):
    return r[0] - pad <= x <= r[1] + pad and r[2] - pad <= y <= r[3] + pad


# ---------------------------------------------------------------- B4 -> B1 banks
ESC_RISE_B = B4B1 = G.B1_FLOOR - G.B4_FLOOR       # 12.7
BANK_LANES = [("esc", -2.00), ("div", (-1.34, -1.22)), ("esc", -0.56), ("div", (0.10, 0.22)), ("stair", (0.22, 2.67))]
STAIR_B = dict(u0=0.6, tread=0.29, flights=(19, 19, 19, 20), landing=1.5)


def esc_line(u, z0, rise, u_start=0.3):
    ua = u_start + 2.4; run = rise / TAN30
    if u <= ua:
        return z0
    if u >= ua + run:
        return z0 + rise
    return z0 + (u - ua) * TAN30


def stair_profile(z0, rise, u0, tread, flights, landing):
    """Stepped top line [(u, z)] of a stair with landings, starting with a riser at u0."""
    n = sum(flights); h = rise / n
    pts = [(u0, z0)]
    u, z = u0, z0
    for fi, k in enumerate(flights):
        for i in range(k):
            z += h
            pts.append((u, z))
            if i < k - 1:
                u += tread
                pts.append((u, z))
        if fi < len(flights) - 1:
            u += landing
            pts.append((u, z))
    return pts, h


def stair_nose(pts, u):
    """Height of the stair's top surface at u (step function)."""
    z = pts[0][1]
    for (ua, za), (ub, zb) in zip(pts[:-1], pts[1:]):
        if ua <= u:
            z = max(z, zb if abs(ua - ub) < 1e-9 else za)
    return z


def bank_stair():
    return stair_profile(G.B4_FLOOR, B4B1, STAIR_B["u0"], STAIR_B["tread"], STAIR_B["flights"], STAIR_B["landing"])


def bank_top_line(u):
    """Highest walking surface across the bank lanes at u (escalators, stair)."""
    pts, _ = bank_stair()
    return max(esc_line(u, G.B4_FLOOR, B4B1), stair_nose(pts, u) if u >= STAIR_B["u0"] else G.B4_FLOOR)


def bank_low_line(u):
    pts, _ = bank_stair()
    return min(esc_line(u, G.B4_FLOOR, B4B1), stair_nose(pts, u) if u >= STAIR_B["u0"] else G.B4_FLOOR)


SOFFIT_CLEAR = 2.6


def bank_slab_hole(bank, zb, zt):
    xf, s = G.BANKS[bank]
    us = np.arange(-1.0, G.BANK_LEN + 0.01, 0.05)
    ok = [u for u in us if bank_top_line(u) + SOFFIT_CLEAR >= zb and bank_low_line(u) <= zt + 0.02]
    if not ok:
        return None
    u0, u1 = min(ok) - 0.2, max(ok) + 0.2
    a, b = sorted((xf + s * u0, xf + s * u1))
    return (a, b, -2.67, 2.67)


def bank_rect(bank, u0=-1.0, u1=None):
    xf, s = G.BANKS[bank]
    u1 = G.BANK_LEN if u1 is None else u1
    a, b = sorted((xf + s * u0, xf + s * u1))
    return (a, b, -G.BANK_HALF, G.BANK_HALF)


VENT_L = G.to_local(*G.VENT_XY_MODEL)
VENT_RECT = (VENT_L[0] - G.VENT_HALF, VENT_L[0] + G.VENT_HALF, VENT_L[1] - G.VENT_HALF, VENT_L[1] + G.VENT_HALF)


# ====================================================================== 1. box structure
def build_structure(M, col):
    mb = L.MeshBuilder(); K = Mats(M)
    mbw = L.MeshBuilder(); KW = Mats(M)
    x0, x1 = G.BOX_X
    xo0, xo1 = x0 - G.END_T, x1 + G.END_T
    yi, yo = G.WALL_IN, G.WALL_OUT
    ux0, ux1 = G.UPPER_X
    # base slab
    slab(mb, (xo0, xo1), (-yo, yo), (G.BASE_BOT, G.INVERT), [], K("invert"), K("conc"), K("conc"))
    # side walls: lower part full length, upper part only in the five-level middle part
    corridor = (G.B1_CORRIDOR_X[0], G.B1_CORRIDOR_X[1], G.B1_FLOOR, G.B1_CEIL)
    wall_x(mb, (xo0, xo1), (-yo, -yi), (G.INVERT, G.LOWROOF_TOP), [], K("conc"), K("conc"), K("conc"))
    wall_x(mb, (ux0 - G.END_T, ux1 + G.END_T), (-yo, -yi), (G.LOWROOF_TOP, G.ROOF_TOP), [corridor], K("conc"), K("conc"), K("conc"))
    wall_x(mbw, (xo0, xo1), (yi, yo), (G.INVERT, G.LOWROOF_TOP), [], KW("conc"), KW("conc"), KW("conc"))
    wall_x(mbw, (ux0 - G.END_T, ux1 + G.END_T), (yi, yo), (G.LOWROOF_TOP, G.ROOF_TOP), [], KW("conc"), KW("conc"), KW("conc"))
    # end walls with four tunnel mouths
    mouths = [(G.TRK[t] - 2.3, G.TRK[t] + 2.3, G.INVERT, -22.0) for t in G.TRK]
    wall_y(mb, (-yi, yi), (x1, xo1), (G.INVERT, G.LOWROOF_TOP), mouths, K("conc"), K("conc"), K("conc"))
    wall_y(mb, (-yi, yi), (xo0, x0), (G.INVERT, G.LOWROOF_TOP), mouths, K("conc"), K("conc"), K("conc"))
    # end walls of the upper part
    wall_y(mb, (-yi, yi), (ux0 - G.END_T, ux0), (G.B3_SOFFIT, G.ROOF_TOP), [], K("conc"), K("conc"), K("conc"))
    wall_y(mb, (-yi, yi), (ux1, ux1 + G.END_T), (G.B3_SOFFIT, G.ROOF_TOP), [], K("conc"), K("conc"), K("conc"))
    # B4 slab (spans the whole box) with the 12 stair wells and both lift shafts
    holes = [G.group_opening(gx, isl) for isl in G.ISL for gx in G.GROUP_X] + [elev_rect(i) for i in G.ISL]
    slab(mb, (x0, x1), (-yi, yi), (G.B4_SOFFIT, G.B4_FLOOR), holes, K("terrazzo"), K("soffit"), K("conc"))
    # low roofs (two-level parts)
    slab(mb, (x0, ux0), (-yi, yi), (G.B3_SOFFIT, G.LOWROOF_TOP), [], K("conc"), K("conc"), K("conc"))
    slab(mb, (ux1, x1), (-yi, yi), (G.B3_SOFFIT, G.LOWROOF_TOP), [], K("conc"), K("conc"), K("conc"))
    # upper slabs B3 / B2 / B1 floors and roof
    lift12 = elev_rect("1-2")
    for zb, zt, top, vent in ((G.B3_SOFFIT, G.B3_FLOOR, "conc_floor", False), (G.B2_SOFFIT, G.B2_FLOOR, "conc_floor", False),
                              (G.B1_SOFFIT, G.B1_FLOOR, "terrazzo", True), (G.ROOF_SOFFIT, G.ROOF_TOP, "conc", True)):
        hs = [lift12] if zt <= G.B1_FLOOR + 0.01 else []
        for bk in G.BANKS:
            h = bank_slab_hole(bk, zb, zt)
            if h and zt <= G.B1_FLOOR + 0.01:
                hs.append(h)
        if vent:
            hs.append(VENT_RECT)
        slab(mb, (ux0, ux1), (-yi, yi), (zb, zt), hs, K(top), K("conc"), K("conc"))
    # ventilation shaft (B2 floor -> just under the plaza), walls 0.4 m
    vx0, vx1, vy0, vy1 = VENT_RECT
    for a, b in (((vx0 - 0.4, vx0), (vy0 - 0.4, vy1 + 0.4)), ((vx1, vx1 + 0.4), (vy0 - 0.4, vy1 + 0.4)),
                 ((vx0, vx1), (vy0 - 0.4, vy0)), ((vx0, vx1), (vy1, vy1 + 0.4))):
        holes = []
        if a == (vx0 - 0.4, vx0):
            pass
        slab(mb, a, b, (G.B2_FLOOR, G.VENT_TOP), [], K("conc"), K("conc"), K("c_wall"))
    # grille at the top of the shaft (seen from inside only)
    slab(mb, (vx0, vx1), (vy0, vy1), (G.VENT_TOP - 0.25, G.VENT_TOP - 0.2), [], K("steel_dk"), K("steel_dk"), K("steel_dk"))
    # B1 passage towards 丸の内地下中央口 (east side)
    cx0, cx1 = G.B1_CORRIDOR_X
    slab(mb, (cx0 - 0.15, cx1 + 0.15), (G.B1_CORRIDOR_Y - 0.15, -yo), (G.B1_SOFFIT, G.B1_FLOOR), [], K("terrazzo"), K("conc"), K("conc"))
    slab(mb, (cx0 - 0.15, cx1 + 0.15), (G.B1_CORRIDOR_Y - 0.15, -yo), (G.ROOF_SOFFIT, G.ROOF_TOP), [], K("conc"), K("conc"), K("conc"))
    slab(mb, (cx0, cx1), (G.B1_CORRIDOR_Y, -yo), (G.B1_CEIL, G.B1_CEIL + 0.03), [], K("conc"), K("c_ceil"), K("conc"))
    wall_x(mb, (cx0 - 0.15, cx0), (G.B1_CORRIDOR_Y, -yo), (G.B1_FLOOR, G.ROOF_SOFFIT), [], K("c_wall"), K("c_wall"), K("c_wall"))
    wall_y(mb, (G.B1_CORRIDOR_Y, -yo), (cx0 - 0.15, cx0), (G.B1_FLOOR, G.ROOF_SOFFIT), [], K("c_wall"), K("conc"), K("conc"))
    wall_y(mb, (G.B1_CORRIDOR_Y, -yo), (cx1, cx1 + 0.15), (G.B1_FLOOR, G.ROOF_SOFFIT), [], K("conc"), K("c_wall"), K("conc"))
    wall_x(mb, (cx0, cx1), (G.B1_CORRIDOR_Y - 0.15, G.B1_CORRIDOR_Y), (G.B1_FLOOR, G.ROOF_SOFFIT), [], K("c_wall"), K("conc"), K("conc"))
    # tunnel stubs (30 m) beyond both end walls
    for sgn, xe in ((-1, xo0), (1, xo1)):
        xa, xb = sorted((xe, xe + sgn * 30.0))
        for t, yt in G.TRK.items():
            slab(mb, (xa, xb), (yt - 2.9, yt + 2.9), (G.BASE_BOT + 1.0, G.INVERT), [], K("invert"), K("conc"), K("conc"))
            slab(mb, (xa, xb), (yt - 2.9, yt + 2.9), (-22.0, -21.4), [], K("conc"), K("soffit"), K("conc"))
            wall_x(mb, (xa, xb), (yt - 2.9, yt - 2.3), (G.INVERT, -22.0), [], K("conc"), K("soffit"), K("conc"))
            wall_x(mb, (xa, xb), (yt + 2.3, yt + 2.9), (G.INVERT, -22.0), [], K("soffit"), K("conc"), K("conc"))
            far = xb if sgn > 0 else xa
            slab(mb, (far - 0.3, far + 0.3), (yt - 2.3, yt + 2.3), (G.INVERT, -22.0), [], K("dark"), K("dark"), K("dark"))
    o1 = new_obj(mb, "V9 Sobu | box structure (slabs, walls, end walls, tunnel stubs, ventilation shaft)", col, K.lst)
    o2 = new_obj(mbw, "V9 Sobu | box west wall (hide for the cutaway view)", col, KW.lst, {"V9_cutaway_hide": True})
    return o1, o2


# ====================================================================== 2. platforms, tracks
def build_platforms(M, col):
    mb = L.MeshBuilder(); K = Mats(M)
    x0, x1 = G.PLAT_X
    for isl, (ya, yb) in G.ISL.items():
        bx(mb, x0, x1, ya + 0.35, yb - 0.35, G.INVERT, G.DECK - 0.25, K("plat_face"))
        strips = [(ya, ya + 0.40, "coping"), (ya + 0.40, ya + 0.80, "tile"), (ya + 0.80, ya + 1.10, "tactile"),
                  (ya + 1.10, yb - 1.10, "tile"), (yb - 1.10, yb - 0.80, "tactile"), (yb - 0.80, yb - 0.40, "tile"),
                  (yb - 0.40, yb, "coping")]
        for a, b, m in strips:
            bx(mb, x0, x1, a, b, G.DECK - 0.25, G.DECK, K(m))
        # end fences
        for xe, sg in ((x0, 1), (x1, -1)):
            xf = xe + sg * 0.15
            for y in np.arange(ya + 0.6, yb - 0.55, 1.2):
                L.tube(mb, [Vector((xf, y, G.DECK)), Vector((xf, y, G.DECK + 1.1))], 0.025, 8, K("stain"))
            for zz in (G.DECK + 0.55, G.DECK + 1.1):
                L.tube(mb, [Vector((xf, ya + 0.6, zz)), Vector((xf, yb - 0.6, zz))], 0.025, 8, K("stain"))
    new_obj(mb, "V9 Sobu | B5 island platforms 1-2 and 3-4", col, K.lst)

    mb = L.MeshBuilder(); K = Mats(M)
    xa, xb = G.BOX_X[0] - G.END_T - 30.0, G.BOX_X[1] + G.END_T + 30.0
    rail = [(-0.0635, 0.0), (0.0635, 0.0), (0.0635, 0.012), (0.008, 0.030), (0.008, 0.108), (0.0325, 0.115),
            (0.0325, 0.153), (-0.0325, 0.153), (-0.0325, 0.115), (-0.008, 0.108), (-0.008, 0.030), (-0.0635, 0.012)]
    for t, yt in G.TRK.items():
        bx(mb, xa, xb, yt - 1.35, yt + 1.35, G.INVERT, G.TRACKBED, K("trackbed"))
        for x in np.arange(xa + 0.3, xb - 0.2, 0.625):
            for sy in (-1, 1):
                bx(mb, x - 0.13, x + 0.13, yt + sy * 0.5685 - 0.31, yt + sy * 0.5685 + 0.31, G.TRACKBED, G.TRACKBED + 0.15, K("sleeper"))
                cnt("sleeper_blocks")
        for sy in (-1, 1):
            yr = yt + sy * 0.5685
            extrude_x(mb, [(yr + a, G.RAIL - 0.153 + b) for a, b in rail], xa, xb, K("rail"))
    new_obj(mb, "V9 Sobu | B5 tracks 1-4 (slab track, 50N rails)", col, K.lst)


# ====================================================================== 3. columns
def column(mb, K, x, y, r, z0, z1, deck_band=True, plate_dirs=(), num=None, base=True):
    zb0, zb1 = G.DECK + 1.55, G.DECK + 2.05
    if base and z0 <= G.DECK + 0.01 <= z1:
        L.lathe(mb, [(r + 0.02, G.DECK), (r + 0.02, G.DECK + 0.10)], (x, y), 24, K("col_base"), cap_top=True)
    if deck_band and z0 < zb0 and z1 > zb1:
        L.lathe(mb, [(r, z0), (r, zb0)], (x, y), 24, K("col"))
        L.lathe(mb, [(r + 0.003, zb0), (r + 0.003, zb1)], (x, y), 24, K("stripe"))
        L.lathe(mb, [(r, zb1), (r, z1)], (x, y), 24, K("col"))
    else:
        L.lathe(mb, [(r, z0), (r, z1)], (x, y), 24, K("col"))
    if num is not None:
        uv = atlas(num - 1, 8, 6)
        for d in plate_dirs:            # curved plate (4 facets) on the column surface
            a0 = math.atan2(d[1], d[0]); half = 0.44 / 2 / (r + 0.012)
            pts_b, pts_t = [], []
            for k in range(5):
                a = a0 - half + 2 * half * k / 4          # increasing angle: outward normal, text reads left to right
                p = (x + (r + 0.012) * math.cos(a), y + (r + 0.012) * math.sin(a))
                pts_b.append((p[0], p[1], G.DECK + 2.12)); pts_t.append((p[0], p[1], G.DECK + 2.44))
            for k in range(4):
                fu0 = uv[0] + (uv[2] - uv[0]) * k / 4; fu1 = uv[0] + (uv[2] - uv[0]) * (k + 1) / 4
                mb.add([pts_b[k], pts_b[k + 1], pts_t[k + 1], pts_t[k]], [(0, 1, 2, 3)], K("colnum"),
                       uvs=[[(fu0, uv[1]), (fu1, uv[1]), (fu1, uv[3]), (fu0, uv[3])]])


def build_columns_b5(M, col):
    mb = L.MeshBuilder(); K = Mats(M)
    n = 0
    for x in G.COL_X:
        num = G.col_number(x) if G.PLAT_X[0] < x < G.PLAT_X[1] else None
        if G.PLAT_X[0] < x < G.PLAT_X[1]:
            for isl, yc in G.ISL_C.items():
                for dy in (-G.COL_ROW_OFF, G.COL_ROW_OFF):
                    column(mb, K, x, yc + dy, G.COL_R_ISL, G.DECK, G.B4_SOFFIT, True, ((1, 0), (-1, 0)), num)
                    n += 1
            column(mb, K, x, 0.0, G.COL_R_MID, G.INVERT, G.B4_SOFFIT, True, ((0, 1), (0, -1)), num, base=False)
            n += 1
        elif abs(x) > G.PLAT_X[1] + 2:
            for y in (-9.39, 0.0, 9.39):
                L.lathe(mb, [(G.COL_R_MID, G.INVERT), (G.COL_R_MID, G.B4_SOFFIT)], (x, y), 20, K("conc"))
                n += 1
    cnt("b5_columns", n)
    new_obj(mb, "V9 Sobu | B5 columns (guard bands, numbers)", col, K.lst)


def build_columns_upper(M, col):
    """Columns of B4 (hall and machine rooms), B3, B2, B1 on the same grid; omitted inside wells and shafts."""
    mb = L.MeshBuilder(); K = Mats(M)
    blocked = [r for r in (bank_rect("A", -2.0, G.BANK_LEN + 3.0), bank_rect("B", -2.0, G.BANK_LEN + 3.0))]
    n = 0
    levels = [("B4", G.B4_FLOOR, G.B3_SOFFIT, G.BOX_X)]
    levels += [("B3", G.B3_FLOOR, G.B2_SOFFIT, G.UPPER_X), ("B2", G.B2_FLOOR, G.B1_SOFFIT, G.UPPER_X),
               ("B1", G.B1_FLOOR, G.ROOF_SOFFIT, G.UPPER_X)]
    for lev, z0, z1, xr in levels:
        for x in G.COL_X:
            if not (xr[0] + 1.0 < x < xr[1] - 1.0):
                continue
            for y in (-11.99, -6.79, 0.0, 6.79, 11.99):
                bad = any(in_rect(x, y, r, 0.6) for r in blocked)
                bad |= any(in_rect(x, y, elev_rect(i), 0.6) for i in G.ISL)
                bad |= in_rect(x, y, VENT_RECT, 0.9)
                if lev == "B4":
                    bad |= any(in_rect(x, y, G.group_opening(gx, isl), 0.55) for isl in G.ISL for gx in G.GROUP_X)
                if lev == "B1" and abs(x - G.B1_GATES_X) < 1.2:
                    bad = True
                if bad:
                    continue
                finish = "col" if lev in ("B4", "B1") and (lev != "B4" or G.B4_HALL_X[0] < x < G.B4_HALL_X[1]) else "conc"
                L.lathe(mb, [(0.45, z0), (0.45, z1)], (x, y), 20, K(finish))
                n += 1
    cnt("upper_columns", n)
    new_obj(mb, "V9 Sobu | B4-B1 columns", col, K.lst)


# ====================================================================== 4. B5 ceilings, beams, lights, walls
def build_b5_ceilings(M, col, lcol):
    mb = L.MeshBuilder(); K = Mats(M)
    mbl = L.MeshBuilder(); KL = Mats(M)
    x0, x1 = G.PLAT_X
    for isl, (ya, yb) in G.ISL.items():
        yc = G.ISL_C[isl]
        holes = []
        for (a, b, c, d, i2, gx) in ENCL:
            if i2 != isl:
                continue
            xf, s, _ = G.group_frame(gx, isl)
            u0 = 1.5                         # ceiling stops where the stair starts (headroom)
            ha, hb = sorted((xf + s * u0, xf + s * G.GROUP_LEN))
            holes.append((ha, hb, c, d))
        holes.append(elev_rect(isl))
        slab(mb, (x0, x1), (ya, yb), (G.B5_CEIL, G.B5_CEIL + 0.03), holes, K("conc"), K("ceil"), K("bulk"))
        for dy in (-G.COL_ROW_OFF, G.COL_ROW_OFF):
            bx(mb, x0, x1, yc + dy - 0.45, yc + dy + 0.45, G.B5_CEIL - 0.40, G.B5_CEIL, K("bulk"))
        for ye in (ya, yb):
            bx(mb, x0, x1, ye - 0.025, ye + 0.025, G.B5_CEIL - 0.35, G.B5_CEIL, K("bulk"))
        # fluorescent rows
        for dy in (-1.25, 1.25, -4.1, 4.1):
            y = yc + dy
            for x in np.arange(x0 + 1.0, x1 - 0.9, 1.30):
                if any(in_rect(x, y, h, 0.7) for h in holes):
                    continue
                bx(mbl, x - 0.60, x + 0.60, y - 0.10, y + 0.10, G.B5_CEIL - 0.06, G.B5_CEIL, KL("fix_body"))
                bx(mbl, x - 0.57, x + 0.57, y - 0.07, y + 0.07, G.B5_CEIL - 0.065, G.B5_CEIL - 0.06, KL("lamp"))
                cnt("b5_fittings")
        # fill lights (not seen by the camera)
        for xa in np.arange(x0, x1 - 1, 21.0):
            area_light(lcol, f"V9 light | B5 {isl} x{int(xa)}", xa + 10.5, yc, G.B5_CEIL - 0.45, 19.0, 9.0, 1600.0)
    # track walls: dado, beige panels; small wall lamps
    for sg in (-1, 1):
        yw = sg * (G.WALL_IN - 0.02)
        a, b = sorted((yw, yw - sg * 0.04))
        bx(mb, G.BOX_X[0], G.BOX_X[1], a, b, G.INVERT, G.RAIL + 0.9, K("wall_low"))
        bx(mb, G.BOX_X[0], G.BOX_X[1], a, b, G.RAIL + 0.9, G.B4_SOFFIT, K("wall_pan"))
        for x in np.arange(G.BOX_X[0] + 7.0, G.BOX_X[1] - 3, 14.0):
            c, d = sorted((yw - sg * 0.04, yw - sg * 0.22))
            bx(mbl, x - 0.6, x + 0.6, c, d, G.RAIL + 4.60, G.RAIL + 4.75, KL("fix_body"))
            bx(mbl, x - 0.55, x + 0.55, c + 0.02, d - 0.02, G.RAIL + 4.595, G.RAIL + 4.60, KL("lamp_dim"))
    # transverse beams under the B4 slab (over-track soffit), skipped over stair wells and lifts
    blocks = [(a, b, c, d) for (a, b, c, d, i2, gx) in ENCL] + [elev_rect(i) for i in G.ISL]
    for x in G.COL_X:
        ys = [-G.WALL_IN, G.WALL_IN]
        cuts = []
        for (a, b, c, d) in blocks:
            if a - 0.4 <= x <= b + 0.4:
                cuts.append((c - 0.05, d + 0.05))
        segs = [(-G.WALL_IN, G.WALL_IN)]
        for c, d in cuts:
            nxt = []
            for p, q in segs:
                if d <= p or c >= q:
                    nxt.append((p, q))
                else:
                    if c > p:
                        nxt.append((p, c))
                    if d < q:
                        nxt.append((d, q))
            segs = nxt
        for p, q in segs:
            if q - p > 0.2:
                bx(mb, x - 0.3, x + 0.3, p, q, G.B4_BEAM, G.B4_SOFFIT, K("soffit"))
    bx(mb, G.BOX_X[0], G.BOX_X[1], -0.45, 0.45, G.B4_BEAM, G.B4_SOFFIT, K("soffit"))
    new_obj(mb, "V9 Sobu | B5 ceilings, bulkheads, track walls, soffit beams", col, K.lst)
    new_obj(mbl, "V9 Sobu | B5 light fittings", col, KL.lst)


# ====================================================================== 5. rigid overhead conductor
def build_conductor(M, col):
    mb = L.MeshBuilder(); K = Mats(M)
    xa, xb = G.BOX_X[0] - 28.0, G.BOX_X[1] + 28.0
    REP["conductor"] = {"wire_bottom_above_rail": round(G.WIRE_BOTTOM - G.RAIL, 3), "stagger_m": 0.15}
    for t, yt in G.TRK.items():
        xs = np.arange(xa, xb + 0.01, 4.0)
        ys = yt + 0.15 * np.sin(2 * math.pi * xs / 80.0 + t)
        path_w = [Vector((x, y, G.WIRE_BOTTOM + 0.0065)) for x, y in zip(xs, ys)]
        L.tube(mb, path_w, 0.0065, 6, K("wire"), smooth=True)
        for i in range(len(xs) - 1):
            xm = (xs[i] + xs[i + 1]) / 2; ym = (ys[i] + ys[i + 1]) / 2
            ang = math.atan2(ys[i + 1] - ys[i], xs[i + 1] - xs[i])
            L.box(mb, xm, ym, G.WIRE_BOTTOM + 0.035, 4.02, 0.035, 0.045, K("conductor"), rotz=ang)
            L.box(mb, xm, ym, G.WIRE_BOTTOM + 0.08, 4.02, 0.11, 0.05, K("conductor"), rotz=ang)
            L.box(mb, xm, ym, G.WIRE_BOTTOM + 0.17, 4.02, 0.02, 0.13, K("conductor"), rotz=ang)
        top = lambda x: -22.0 if abs(x) > G.BOX_X[1] + G.END_T else G.B4_SOFFIT
        for x in np.arange(math.ceil(xa / 7.0) * 7.0, xb, 7.0):
            if abs(x) > G.BOX_X[1] and abs(x) < G.BOX_X[1] + G.END_T + 0.5:
                continue
            y = yt + 0.15 * math.sin(2 * math.pi * x / 80.0 + t)
            zt = top(x)
            L.box(mb, x, y, (zt + G.BAR_TOP + 0.30) / 2, 0.05, 0.05, zt - G.BAR_TOP - 0.30, K("steel_dk"))
            L.lathe(mb, [(0.0, G.BAR_TOP + 0.05), (0.07, G.BAR_TOP + 0.08), (0.07, G.BAR_TOP + 0.26), (0.0, G.BAR_TOP + 0.30)],
                    (x, y), 12, K("insul"))
            L.box(mb, x, y, G.BAR_TOP + 0.025, 0.22, 0.16, 0.05, K("steel_dk"))
            cnt("conductor_hangers")
    new_obj(mb, "V9 Sobu | rigid overhead conductor (tracks 1-4)", col, K.lst)


# ====================================================================== 6. escalators and stairs
def escalator(mb, K, fr, wc, z0, rise, u_start=0.3, flat=2.4):
    run = rise / TAN30
    ua = u_start + flat; ub = ua + run; ue = ub + flat
    zs = lambda u: esc_line(u, z0, rise, u_start)
    # steps (sawtooth) on the incline
    n = int(round(run / 0.4)); du = run / n; dz = rise / n
    for k in range(n):
        u0, u1 = ua + k * du, ua + (k + 1) * du
        zt = z0 + (k + 1) * dz
        mb.add([fr(u0, wc - 0.5, zt - dz), fr(u0, wc + 0.5, zt - dz), fr(u0, wc + 0.5, zt), fr(u0, wc - 0.5, zt)][::1],
               [(0, 3, 2, 1)] if fr.s > 0 else [(0, 1, 2, 3)], K("step"))
        mb.add([fr(u0, wc - 0.5, zt), fr(u1, wc - 0.5, zt), fr(u1, wc + 0.5, zt), fr(u0, wc + 0.5, zt)], [(0, 1, 2, 3)], K("step"))
        mb.add([fr(u0, wc - 0.5, zt + 0.002), fr(u0 + 0.045, wc - 0.5, zt + 0.002), fr(u0 + 0.045, wc + 0.5, zt + 0.002),
                fr(u0, wc + 0.5, zt + 0.002)], [(0, 1, 2, 3)], K("step_edge"))
    cnt("escalator_steps", n)
    # landing plates (0.3 m thick, flush with the floors)
    fr.box(mb, u_start - 0.6, ua, wc - 0.62, wc + 0.62, z0 - 0.3, z0 + 0.012, K("plate"))
    fr.box(mb, ub, ue + 0.6, wc - 0.62, wc + 0.62, z0 + rise - 0.3, z0 + rise + 0.012, K("plate"))
    # side panels / skirts (u-z polygon), glass, handrails
    us = [u_start - 0.6, ua, ua + 0.5 * run, ub, ue + 0.6]
    for sg in (-1, 1):
        w0, w1 = sorted((wc + sg * 0.50, wc + sg * 0.66))
        top = [(u, zs(u) + 0.12) for u in us]
        bot = [(u, max(z0, zs(u) - 1.0) if u < ub else z0 + rise - 1.0) for u in us]
        bot[-1] = (us[-1], z0 + rise - 0.3); bot[-2] = (us[-2], z0 + rise - 1.0)
        poly = [bot[0]] + bot[1:] + top[::-1]
        poly = [(u, z) for u, z in poly]
        # make CCW in (u, z): bottom left -> bottom right -> top right -> top left
        poly = [(us[0], z0)] + [(u, z) for u, z in bot[1:]] + [(u, z) for u, z in top[::-1]]
        prism_uz(mb, fr, poly, w0, w1, K("stain"), lambda a, b: K("stain"))
        wg = wc + sg * 0.575
        gpoly = [(u_start + 0.25, z0 + 0.12)] + [(u, zs(u) + 0.12) for u in us[1:4]] + [(ue + 0.05, z0 + rise + 0.12),
                 (ue + 0.05, z0 + rise + 0.95)] + [(u, zs(u) + 0.95) for u in us[3:0:-1]] + [(u_start + 0.25, z0 + 0.95)]
        prism_uz(mb, fr, gpoly, wg - 0.008, wg + 0.008, K("glass"), lambda a, b: K("stain"))
        # handrail loop: newel arcs at both ends
        path = []
        uc0, zc0 = u_start + 0.25, z0 + 0.60
        for k in range(9):
            a = -math.pi / 2 + math.pi * k / 8
            path.append(Vector(fr(uc0 - 0.38 * math.cos(a), wg, zc0 + 0.38 * math.sin(a))))
        for u in (ua, ua + 0.25 * run, ua + 0.5 * run, ua + 0.75 * run, ub):
            path.append(Vector(fr(u, wg, zs(u) + 0.98)))
        uc1, zc1 = ue + 0.05, z0 + rise + 0.60
        for k in range(9):
            a = math.pi / 2 - math.pi * k / 8
            path.append(Vector(fr(uc1 + 0.38 * math.cos(a), wg, zc1 + 0.38 * math.sin(a))))
        L.tube(mb, path, 0.04, 8, K("rubber"))
    cnt("escalators")
    return ue


def stair(mb, K, fr, w0, w1, pts, z_base, u_end, z_top, soffit=None):
    """Solid stair: stepped top line pts [(u, z)], top landing to u_end at z_top; base flat at z_base or sloped soffit."""
    top = list(pts) + [(u_end, z_top)]
    if soffit is None:
        poly = [(pts[0][0], z_base), (u_end, z_base)] + top[::-1]
    else:
        poly = [(pts[0][0], z_base)] + [(u_end, z_top - 0.35)] + top[::-1]
        poly = [(pts[0][0], z_base), (pts[0][0] + 0.6, z_base), (u_end - 1.2, z_top - 0.45), (u_end, z_top - 0.35)] + top[::-1]
    # dedupe consecutive duplicates
    clean = []
    for p in poly:
        if not clean or abs(clean[-1][0] - p[0]) > 1e-6 or abs(clean[-1][1] - p[1]) > 1e-6:
            clean.append(p)
    if abs(clean[0][0] - clean[-1][0]) < 1e-6 and abs(clean[0][1] - clean[-1][1]) < 1e-6:
        clean.pop()

    def side(du, dz):
        if abs(dz) < 1e-6 and du < 0:
            return K("tread")
        return K("riser")
    prism_uz(mb, fr, clean, w0, w1, K("brick"), side)
    # nosings
    for (ua, za), (ub, zb) in zip(pts[:-1], pts[1:]):
        if abs(ua - ub) < 1e-6 and zb > za:
            mb.add([fr(ua, w0, zb + 0.003), fr(ua + 0.05, w0, zb + 0.003), fr(ua + 0.05, w1, zb + 0.003), fr(ua, w1, zb + 0.003)],
                   [(0, 1, 2, 3)], K("nosing"))
            cnt("stair_steps")


def handrail(mb, K, fr, w, pts, u_end, z_top, h=0.85, u_pre=0.3):
    path = [Vector(fr(pts[0][0] - u_pre, w, pts[0][1] + h))]
    risers = [(u, z) for (u, z), (u2, z2) in zip(pts[:-1], pts[1:]) if abs(u - u2) < 1e-6]
    keyp = []
    zprev = pts[0][1]
    for (ua, za), (ub, zb) in zip(pts[:-1], pts[1:]):
        if abs(ua - ub) < 1e-6:
            keyp.append((ua, zb))
    # break points at flight ends
    out = [keyp[0]]
    for a, b, c in zip(keyp[:-2], keyp[1:-1], keyp[2:]):
        s1 = (b[1] - a[1]) / max(b[0] - a[0], 1e-6); s2 = (c[1] - b[1]) / max(c[0] - b[0], 1e-6)
        if abs(s1 - s2) > 0.05:
            out.append(b)
    out.append(keyp[-1])
    for u, z in out:
        path.append(Vector(fr(u, w, z + h)))
    path.append(Vector(fr(min(u_end, keyp[-1][0] + 0.3), w, z_top + h)))
    L.tube(mb, path, 0.022, 8, K("stain"))
    # brackets every ~1.5 m
    for i in range(len(path) - 1):
        a, b = path[i], path[i + 1]
        nseg = max(1, int((b - a).length / 1.5))
        for k in range(nseg):
            p = a + (b - a) * (k / nseg)
            L.box(mb, p.x, p.y, p.z - 0.05, 0.03, 0.03, 0.10, K("stain"))


def build_b5_groups(M, col):
    out = []
    for isl in G.ISL:
        mb = L.MeshBuilder(); K = Mats(M)
        pts, h = stair_profile(G.DECK, G.STAIR_RISE, 1.6, 0.30, (19, 19), 1.8)
        for gx in G.GROUP_X:
            xf, s, yc = G.group_frame(gx, isl)
            fr = Fr(xf, yc, s)
            # enclosure: side walls and end wall (brick tiles), up to the B4 soffit
            for sg in (-1, 1):
                fr.box(mb, 0.0, G.GROUP_LEN, sg * G.ENCL_IN, sg * G.ENCL_HALF, G.DECK, G.B4_SOFFIT, K("brick"))
                fr.box(mb, -0.02, 0.10, sg * (G.ENCL_IN - 0.02), sg * (G.ENCL_HALF + 0.02), G.DECK, G.B4_SOFFIT, K("stain"))
            fr.box(mb, G.GROUP_LEN - 0.12, G.GROUP_LEN, -G.ENCL_HALF, G.ENCL_HALF, G.DECK, G.B4_SOFFIT, K("brick"))
            fr.box(mb, 0.0, 1.5, -G.ENCL_HALF, G.ENCL_HALF, G.B5_CEIL - 0.40, G.B5_CEIL, K("bulk"))      # header over the entrance
            # escalator (up), divider, stair
            escalator(mb, K, fr, -1.255, G.DECK, G.STAIR_RISE)
            dz = lambda u: stair_nose(pts, u) if u >= 1.6 else G.DECK
            dpoly = [(0.9, G.DECK), (13.0, G.DECK), (13.0, dz(13.0) + 0.95), (8.8, dz(8.8) + 0.95), (7.0, dz(7.0) + 0.95),
                     (1.6, dz(1.6) + 0.95), (0.9, G.DECK + 0.95)]
            prism_uz(mb, fr, dpoly, -0.58, -0.46, K("stain"), lambda a, b: K("stain"))
            stair(mb, K, fr, -0.46, G.ENCL_IN, pts, G.DECK, 15.6, G.B4_FLOOR)
            fr.box(mb, 13.2, 15.6, -0.58, -0.46, G.B4_FLOOR - 0.3, G.B4_FLOOR, K("terrazzo"))
            handrail(mb, K, fr, G.ENCL_IN - 0.07, pts, 15.6, G.B4_FLOOR)
            handrail(mb, K, fr, -0.52, pts, 13.0, G.B4_FLOOR, 0.98)
            # B4 balustrade round the well (floor side)
            for sg in (-1, 1):
                wg = sg * (G.ENCL_IN + 0.06)
                prism_uz(mb, fr, [(6.45, G.B4_FLOOR), (14.2, G.B4_FLOOR), (14.2, G.B4_FLOOR + 1.1), (6.45, G.B4_FLOOR + 1.1)],
                         wg - 0.008, wg + 0.008, K("glass"), lambda a, b: K("stain"))
                L.tube(mb, [Vector(fr(6.45, wg, G.B4_FLOOR + 1.12)), Vector(fr(14.2, wg, G.B4_FLOOR + 1.12))], 0.03, 8, K("stain"))
            prism_uz(mb, fr, [(6.45 - 0.008, G.B4_FLOOR), (6.45 + 0.008, G.B4_FLOOR), (6.45 + 0.008, G.B4_FLOOR + 1.1),
                              (6.45 - 0.008, G.B4_FLOOR + 1.1)], -G.ENCL_IN - 0.06, G.ENCL_IN + 0.06, K("glass"), lambda a, b: K("stain"))
            L.tube(mb, [Vector(fr(6.45, -G.ENCL_IN - 0.06, G.B4_FLOOR + 1.12)), Vector(fr(6.45, G.ENCL_IN + 0.06, G.B4_FLOOR + 1.12))],
                   0.03, 8, K("stain"))
            cnt("stair_groups")
        out.append(new_obj(mb, f"V9 Sobu | B5-B4 stairs and escalators (island {isl})", col, K.lst))
    return out


def build_banks(M, col, lcol):
    mb = L.MeshBuilder(); K = Mats(M)
    mbl = L.MeshBuilder(); KL = Mats(M)
    pts, h = bank_stair()
    for bank, (xf, s) in G.BANKS.items():
        fr = Fr(xf, 0.0, s)
        for kind, a in BANK_LANES:
            if kind == "esc":
                escalator(mb, K, fr, a, G.B4_FLOOR, B4B1)
            elif kind == "div":
                top = [(u, bank_top_line(u) + 0.95) for u in np.arange(0.4, 25.0, 1.0)]
                poly = [(0.4, G.B4_FLOOR), (24.6, G.B1_FLOOR - 1.0)] + top[::-1]
                poly = [(0.4, G.B4_FLOOR)] + [(u, bank_low_line(u) - 0.6) for u in np.arange(1.4, 25.0, 1.0)] + top[::-1]
                prism_uz(mb, fr, poly, a[0], a[1], K("stain"), lambda d1, d2: K("stain"))
            else:
                stair(mb, K, fr, a[0], a[1], pts, G.B4_FLOOR, G.BANK_LEN - 0.3, G.B1_FLOOR, soffit=True)
                handrail(mb, K, fr, a[1] - 0.07, pts, G.BANK_LEN - 0.3, G.B1_FLOOR)
                handrail(mb, K, fr, a[0] + 0.06, pts, G.BANK_LEN - 0.3, G.B1_FLOOR, 0.98)
        # shaft walls (B4 floor -> B1 ceiling), the closed low end above the B4 ceiling, and the sloped soffit
        for sg in (-1, 1):
            fr.box(mb, -1.0, G.BANK_LEN, sg * 2.67, sg * G.BANK_HALF, G.B4_FLOOR, G.B1_CEIL, K("c_wall"))
        fr.box(mb, -1.15, -1.0, -G.BANK_HALF, G.BANK_HALF, G.B4_CEIL, G.B1_CEIL, K("c_wall"))
        us = np.arange(0.0, G.BANK_LEN + 0.01, 0.5)
        line = [(u, min(bank_top_line(u) + SOFFIT_CLEAR, G.B1_CEIL - 0.6)) for u in us]
        line = [(u, z) for u, z in line if z >= G.B4_CEIL - 0.001] or line
        u_first = line[0][0]
        poly = [(u, z) for u, z in line] + [(u, z + 0.25) for u, z in line[::-1]]
        prism_uz(mb, fr, poly, -2.67, 2.67, K("c_wall"), lambda a, b: K("c_ceil"))
        # strip lights on the soffit
        for w in (-1.3, 1.4):
            for (ua, za), (ub, zb) in zip(line[:-1], line[1:]):
                mbl.add([fr(ua, w - 0.08, za - 0.01), fr(ub, w - 0.08, zb - 0.01), fr(ub, w + 0.08, zb - 0.01), fr(ua, w + 0.08, za - 0.01)],
                        [(0, 3, 2, 1)] if s > 0 else [(0, 1, 2, 3)], KL("lamp"))
        REP.setdefault("banks", {})[bank] = {"foot_x": xf, "dir": s, "rise_m": round(B4B1, 2),
                                             "soffit_starts_u": round(u_first, 2)}
        # fill light inside the shaft (two lights along the incline)
        for u in (8.0, 19.0):
            x, y, zz = fr(u, 0.0, bank_top_line(u) + SOFFIT_CLEAR - 0.3)
            ob = area_light(lcol, f"V9 light | bank {bank} u{int(u)}", x, y, zz, 4.5, 4.0, 900.0)
    new_obj(mb, "V9 Sobu | B4-B1 escalator and stair banks (shafts)", col, K.lst)
    new_obj(mbl, "V9 Sobu | B4-B1 bank light strips", col, KL.lst)


# ====================================================================== 7. lifts
def build_lifts(M, col):
    mb = L.MeshBuilder(); K = Mats(M)
    for isl, (x, y, top) in G.ELEV.items():
        sx, sy = G.ELEV_SIZE
        x0, x1, y0, y1 = x - sx / 2, x + sx / 2, y - sy / 2, y + sy / 2
        spans = [(G.DECK, G.B4_SOFFIT, "glass"), (G.B4_FLOOR, G.B3_SOFFIT, "glass")]
        if top == "B1":
            spans = [(G.DECK, G.B4_SOFFIT, "glass"), (G.B4_FLOOR, G.B4_CEIL, "glass"), (G.B4_CEIL, G.B1_FLOOR, "conc"),
                     (G.B1_FLOOR, G.ROOF_SOFFIT, "frost")]
        for z0, z1, m in spans:
            for (a, b, c, d) in ((x0, x1, y0, y0 + 0.02), (x0, x1, y1 - 0.02, y1), (x0, x0 + 0.02, y0, y1), (x1 - 0.02, x1, y0, y1)):
                bx(mb, a, b, c, d, z0, z1, K(m))
            for (px, py) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
                bx(mb, px - 0.05, px + 0.05, py - 0.05, py + 0.05, z0, z1, K("stain"))
            if m != "conc":
                for zz in (z0, z0 + 2.4):
                    bx(mb, x0, x1, y0 - 0.03, y0 + 0.03, zz, zz + 0.08, K("stain"))
                    bx(mb, x0, x1, y1 - 0.03, y1 + 0.03, zz, zz + 0.08, K("stain"))
                # doors on the +x face
                bx(mb, x1 + 0.0, x1 + 0.05, y - 0.55, y + 0.55, z0, z0 + 2.1, K("stain"))
                bx(mb, x1 + 0.0, x1 + 0.06, y - 0.65, y + 0.65, z0 + 2.1, z0 + 2.3, K("steel_dk"))
        # car parked at B5 (lit)
        bx(mb, x0 + 0.15, x1 - 0.15, y0 + 0.15, y1 - 0.15, G.DECK, G.DECK + 0.05, K("steel_dk"))
        bx(mb, x0 + 0.15, x1 - 0.15, y0 + 0.15, y1 - 0.15, G.DECK + 2.40, G.DECK + 2.50, K("lift_car"))
        for (a, b, c, d) in ((x0 + 0.15, x0 + 0.2, y0 + 0.15, y1 - 0.15), (x0 + 0.15, x1 - 0.15, y0 + 0.15, y0 + 0.2),
                             (x0 + 0.15, x1 - 0.15, y1 - 0.2, y1 - 0.15)):
            bx(mb, a, b, c, d, G.DECK + 0.05, G.DECK + 2.40, K("stain"))
        cnt("lifts")
    new_obj(mb, "V9 Sobu | lifts (B5-B4, B5-B1)", col, K.lst)


# ====================================================================== 8. B4 concourse, B1 concourse, B2 / B3
def build_b4(M, col, lcol):
    mb = L.MeshBuilder(); K = Mats(M)
    mbl = L.MeshBuilder(); KL = Mats(M)
    hx0, hx1 = G.B4_HALL_X; hy = G.B4_HALL_Y
    holes = []
    for bank in G.BANKS:
        line_u = [u for u in np.arange(0, G.BANK_LEN, 0.05) if bank_top_line(u) + SOFFIT_CLEAR >= G.B4_CEIL]
        u0 = min(line_u) if line_u else 3.4
        holes.append(bank_rect(bank, u0 - 0.05))
    holes.append(elev_rect("1-2"))
    slab(mb, (hx0, hx1), (-hy, hy), (G.B4_CEIL, G.B4_CEIL + 0.03), holes, K("conc"), K("c_ceil"), K("c_ceil"))
    doors = []
    for xd in np.arange(hx0 + 12.0, hx1 - 8.0, 28.0):
        doors.append((xd, xd + 1.8, G.B4_FLOOR, G.B4_FLOOR + 2.2))
    for sg in (-1, 1):
        a, b = sorted((sg * hy, sg * (hy + 0.15)))
        wall_x(mb, (hx0, hx1), (a, b), (G.B4_FLOOR, G.B3_SOFFIT), doors, K("c_wall"), K("c_wall"), K("c_wall"))
        for d in doors:
            bx(mb, d[0], d[1], a + 0.05, b - 0.05, d[2], d[3], K("door"))
    for xe, xo in ((hx0, hx0 - 0.15), (hx1, hx1 + 0.15)):
        wall_y(mb, (-hy - 0.15, hy + 0.15), tuple(sorted((xe, xo))), (G.B4_FLOOR, G.B3_SOFFIT), [], K("c_wall"), K("c_wall"), K("c_wall"))
    # troffers (skip holes, wells)
    wells = [G.group_opening(gx, isl) for isl in G.ISL for gx in G.GROUP_X]
    for y in (-11.4, -6.0, -1.0, 1.0, 6.0, 11.4):
        for x in np.arange(hx0 + 1.5, hx1 - 1.0, 2.6):
            if any(in_rect(x, y, h, 0.4) for h in holes):
                continue
            bx(mbl, x - 0.6, x + 0.6, y - 0.15, y + 0.15, G.B4_CEIL - 0.02, G.B4_CEIL, KL("fix_body"))
            bx(mbl, x - 0.58, x + 0.58, y - 0.13, y + 0.13, G.B4_CEIL - 0.025, G.B4_CEIL - 0.02, KL("lamp"))
            cnt("b4_fittings")
    for xa in np.arange(hx0, hx1 - 1, 21.0):
        area_light(lcol, f"V9 light | B4 x{int(xa)}", xa + 10.5, 0.0, G.B4_CEIL - 0.3, 19.0, 26.0, 1000.0)
    new_obj(mb, "V9 Sobu | B4 concourse (ceiling, partitions, doors)", col, K.lst)
    new_obj(mbl, "V9 Sobu | B4 light fittings", col, KL.lst)


def build_b1(M, col, lcol):
    mb = L.MeshBuilder(); K = Mats(M)
    mbl = L.MeshBuilder(); KL = Mats(M)
    hx0, hx1 = G.B1_HALL_X; yi = G.WALL_IN
    slab(mb, (hx0, hx1), (-yi, yi), (G.B1_CEIL, G.B1_CEIL + 0.03), [VENT_RECT], K("conc"), K("c_ceil"), K("c_ceil"))
    for xe, xo in ((hx0, hx0 - 0.15), (hx1, hx1 + 0.15)):
        wall_y(mb, (-yi, yi), tuple(sorted((xe, xo))), (G.B1_FLOOR, G.ROOF_SOFFIT), [], K("c_wall"), K("c_wall"), K("c_wall"))
    for sg in (-1, 1):                          # wall finish on the diaphragm walls
        a, b = sorted((sg * (yi - 0.03), sg * yi))
        hs = [(G.B1_CORRIDOR_X[0], G.B1_CORRIDOR_X[1], G.B1_FLOOR, G.B1_CEIL)] if sg < 0 else []
        wall_x(mb, (hx0, hx1), (a, b), (G.B1_FLOOR, G.B1_CEIL), hs, K("c_wall"), K("c_wall"), K("c_wall"))
    # ventilation shaft cladding
    vx0, vx1, vy0, vy1 = VENT_RECT
    for (a, b, c, d) in ((vx0 - 0.45, vx1 + 0.45, vy0 - 0.45, vy0 - 0.4), (vx0 - 0.45, vx1 + 0.45, vy1 + 0.4, vy1 + 0.45),
                         (vx0 - 0.45, vx0 - 0.4, vy0 - 0.4, vy1 + 0.4), (vx1 + 0.4, vx1 + 0.45, vy0 - 0.4, vy1 + 0.4)):
        bx(mb, a, b, c, d, G.B1_FLOOR, G.B1_CEIL, K("c_wall"))
    # ticket gates
    gx = G.B1_GATES_X
    for y in np.arange(-6.3, 6.31, 0.9):
        bx(mb, gx - 0.65, gx + 0.65, y - 0.09, y + 0.09, G.B1_FLOOR, G.B1_FLOOR + 0.95, K("gate"))
        bx(mb, gx - 0.65, gx + 0.65, y - 0.10, y + 0.10, G.B1_FLOOR + 0.95, G.B1_FLOOR + 1.0, K("gate_top"))
        for xe in (gx - 0.66, gx + 0.66):
            bx(mb, xe - 0.005, xe + 0.005, y - 0.05, y + 0.05, G.B1_FLOOR + 0.8, G.B1_FLOOR + 0.9, K("gate_lit"))
        cnt("ticket_gates")
    for y0, y1 in ((-yi + 0.1, -6.5), (6.5, yi - 0.1)):
        bx(mb, gx - 0.03, gx + 0.03, y0, y1, G.B1_FLOOR, G.B1_FLOOR + 1.1, K("glass"))
        L.tube(mb, [Vector((gx, y0, G.B1_FLOOR + 1.12)), Vector((gx, y1, G.B1_FLOOR + 1.12))], 0.03, 8, K("stain"))
    for y in (-14.0, -9.5, -4.5, 0.0, 4.5, 9.5, 14.0):
        for x in np.arange(hx0 + 1.5, hx1 - 1.0, 2.6):
            if in_rect(x, y, VENT_RECT, 0.8):
                continue
            bx(mbl, x - 0.6, x + 0.6, y - 0.15, y + 0.15, G.B1_CEIL - 0.02, G.B1_CEIL, KL("fix_body"))
            bx(mbl, x - 0.58, x + 0.58, y - 0.13, y + 0.13, G.B1_CEIL - 0.025, G.B1_CEIL - 0.02, KL("lamp"))
            cnt("b1_fittings")
    for xa in np.arange(hx0, hx1 - 1, 21.0):
        area_light(lcol, f"V9 light | B1 x{int(xa)}", xa + 10.5, 0.0, G.B1_CEIL - 0.3, 19.0, 34.0, 1300.0)
    for y in (-28.0, -23.0):
        x = (G.B1_CORRIDOR_X[0] + G.B1_CORRIDOR_X[1]) / 2
        bx(mbl, x - 0.6, x + 0.6, y - 0.15, y + 0.15, G.B1_CEIL - 0.02, G.B1_CEIL, KL("fix_body"))
        bx(mbl, x - 0.58, x + 0.58, y - 0.13, y + 0.13, G.B1_CEIL - 0.025, G.B1_CEIL - 0.02, KL("lamp"))
    new_obj(mb, "V9 Sobu | B1 concourse (ceiling, walls, ticket gates, ventilation-shaft cladding)", col, K.lst)
    new_obj(mbl, "V9 Sobu | B1 light fittings", col, KL.lst)


def build_machine_floors(M, col, lcol):
    mb = L.MeshBuilder(); K = Mats(M)
    mbl = L.MeshBuilder(); KL = Mats(M)
    ux0, ux1 = G.UPPER_X
    yi = G.WALL_IN
    for lev, z0, z1 in (("B3", G.B3_FLOOR, G.B2_SOFFIT), ("B2", G.B2_FLOOR, G.B1_SOFFIT)):
        for sg in (-1, 1):
            a, b = sorted((sg * 10.0, sg * 10.15))
            doors = [(x, x + 1.2, z0, z0 + 2.1) for x in np.arange(ux0 + 8.0, ux1 - 5.0, 17.5)]
            wall_x(mb, (ux0, ux1), (a, b), (z0, z1), doors, K("conc"), K("conc"), K("conc"))
        for xw in np.arange(ux0 + 35.0, ux1 - 5.0, 35.0):
            for (ya, yb) in ((-yi, -10.0), (10.15, yi)):
                if any(in_rect(xw, (ya + yb) / 2, r, 1.0) for r in (bank_rect("A"), bank_rect("B"), VENT_RECT)):
                    continue
                wall_y(mb, (ya, yb), (xw, xw + 0.15), (z0, z1), [((ya + yb) / 2 - 0.6, (ya + yb) / 2 + 0.6, z0, z0 + 2.1)],
                       K("conc"), K("conc"), K("conc"))
        # equipment
        for x in np.arange(ux0 + 4.0, ux1 - 4.0, 9.0):
            for sg in (-1, 1):
                y = sg * 15.5
                if any(in_rect(x, y, r, 1.5) for r in (VENT_RECT, elev_rect("1-2"))):
                    continue
                if lev == "B3":
                    for k in range(4):
                        bx(mb, x - 2.0 + k * 1.0, x - 1.1 + k * 1.0, y - 0.4 * sg - 0.4, y - 0.4 * sg + 0.4, z0, z0 + 2.2, K("cabinet"))
                        cnt("switchgear_cabinets")
                else:
                    L.lathe(mb, [(0.0, z0 + 0.1), (0.9, z0 + 0.1), (0.9, z0 + 2.4), (0.0, z0 + 2.4)], (x, y), 20, K("equip"))
                    cnt("tanks_and_pumps")
        for x in np.arange(ux0 + 2.0, ux1 - 2.0, 7.0):
            for y in (-14.5, 0.0, 14.5):
                bx(mbl, x - 0.6, x + 0.6, y - 0.08, y + 0.08, z1 - 0.10, z1 - 0.04, KL("fix_body"))
                bx(mbl, x - 0.58, x + 0.58, y - 0.06, y + 0.06, z1 - 0.105, z1 - 0.10, KL("lamp_dim"))
        for xa in np.arange(ux0, ux1 - 1, 35.0):
            area_light(lcol, f"V9 light | {lev} x{int(xa)}", xa + 17.5, 0.0, z1 - 0.3, 30.0, 34.0, 1400.0)
    # ventilation fans at B2 next to the shaft, with ducts
    vx, vy = VENT_L
    for dx in (-9.0, 9.0):
        x = vx + dx
        path = [Vector((x, vy - 2.0, G.B2_FLOOR + 1.8)), Vector((x, vy + 2.0, G.B2_FLOOR + 1.8))]
        L.tube(mb, path, 1.45, 24, K("equip"))
        bx(mb, x - 1.5, x + 1.5, vy - 2.2, vy + 2.2, G.B2_FLOOR, G.B2_FLOOR + 0.3, K("steel_dk"))
        xa, xb = sorted((x + (1 if dx < 0 else -1) * 1.5, vx + (-1 if dx < 0 else 1) * (G.VENT_HALF + 0.4)))
        bx(mb, xa, xb, vy - 1.2, vy + 1.2, G.B2_FLOOR + 0.8, G.B2_FLOOR + 2.8, K("duct"))
        cnt("vent_fans")
    new_obj(mb, "V9 Sobu | B2-B3 machine rooms (partitions, switchgear, tanks, fans)", col, K.lst)
    new_obj(mbl, "V9 Sobu | B2-B3 light fittings", col, KL.lst)


def build_marunouchi(M, col):
    mb = L.MeshBuilder(); K = Mats(M)
    P = [np.array(G.to_local(*p)) for p in G.MARUNOUCHI_MODEL]
    zb, zt = G.MARU_Z; hw = G.MARU_HALF
    segs = 0
    for a, b in zip(P[:-1], P[1:]):
        d = b - a; Lg = float(np.linalg.norm(d)); ang = math.atan2(d[1], d[0]); m = (a + b) / 2
        e = Lg + 1.0
        for (cz, sz, wy) in (((zb + zb + 0.6) / 2, 0.6, 2 * hw), ((zt - 0.6 + zt) / 2, 0.6, 2 * hw)):
            L.box(mb, m[0], m[1], cz, e, wy, sz, K("maru"), rotz=ang)
        for off in (-hw + 0.25, hw - 0.25):
            ox, oy = -math.sin(ang) * off, math.cos(ang) * off
            L.box(mb, m[0] + ox, m[1] + oy, (zb + zt) / 2, e, 0.5, zt - zb, K("maru"), rotz=ang)
        for off in (-1.9, 1.9):
            ox, oy = -math.sin(ang) * off, math.cos(ang) * off
            L.box(mb, m[0] + ox, m[1] + oy, zb + 0.6 + 0.08, e, 1.0, 0.16, K("trackbed"), rotz=ang)
        segs += 1
    for p, q in ((P[0], P[1]), (P[-1], P[-2])):
        d = (q - p) / np.linalg.norm(q - p); ang = math.atan2(d[1], d[0])
        L.box(mb, p[0] - d[0] * 0.5, p[1] - d[1] * 0.5, (zb + zt) / 2, 0.4, 2 * hw, zt - zb, K("dark"), rotz=ang)
    REP["marunouchi_tunnel_segments"] = segs
    new_obj(mb, "V9 context | Tokyo Metro Marunouchi Line tunnel crossing (simplified)", col, K.lst)


# ====================================================================== 9. signs and furniture (B5, B4, B1)
DEP_ROW = lambda n, left: 2 * (n - 1) + (0 if left else 1)


def build_signs(M, col):
    mb = L.MeshBuilder(); K = Mats(M)
    for isl in G.ISL:
        ta, tb = G.ISL_TRACKS[isl]          # ta: east track (smaller y), tb: west track
        for gx in G.GROUP_X:
            xf, s, yc = G.group_frame(gx, isl)
            fr = Fr(xf, yc, s)
            # departure board pair with clock, hung over the island centre just before the enclosure
            u = -1.3
            hx = fr(u, 0, 0)[0]
            zc = G.DECK + 2.55
            bx(mb, hx - 0.07, hx + 0.07, yc - 1.85, yc + 1.85, zc - 0.31, zc + 0.31, K("housing"))
            for side in (-1, 1):            # face normal along +x (side=+1) or -x
                n = (side, 0.0)
                # viewer looks along -n: left = -r where r = (-n_y, n_x) = (0, side) -> left is -side*y
                left_track = tb if side < 0 else ta      # looking +x (side=-1 face): left = +y = tb
                right_track = ta if side < 0 else tb
                xs = hx + side * 0.072
                r = Vector((0.0, side, 0.0))
                for k, (trk, left) in enumerate(((left_track, True), (right_track, False))):
                    off = -0.98 if left else 0.98
                    c = (xs, yc + off * side, zc)
                    sign_quad(mb, c, n, 1.48, 0.37, (0, 1 - (DEP_ROW(trk, left) + 1) / 8, 1, 1 - DEP_ROW(trk, left) / 8), K("sign_dep"))
                # clock (disk facing +-x)
                cpts = [(xs + side * 0.005, yc + 0.17 * math.cos(a), zc + 0.17 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 25)[:-1]]
                mb.add(cpts, [tuple(range(24)) if side > 0 else tuple(range(23, -1, -1))], K("clockface"))
                for ang, ln in ((math.radians(60), 0.09), (math.radians(-12), 0.14)):
                    ex, ez = math.cos(ang) * ln, math.sin(ang) * ln
                    L.tube(mb, [Vector((xs + side * 0.01, yc, zc)), Vector((xs + side * 0.01, yc + ex * side, zc + ez))], 0.006, 4, K("housing"))
            for dy in (-1.5, 1.5):
                bx(mb, hx - 0.02, hx + 0.02, yc + dy - 0.02, yc + dy + 0.02, zc + 0.31, G.B5_CEIL - 0.40, K("stain"))
            # track signs (double sided) over each half of the island
            u2 = -4.5
            hx2 = fr(u2, 0, 0)[0]
            for trk, yy in ((ta, yc - 2.9 * (1 if isl == "1-2" else 1)), (tb, yc + 2.9)):
                yy = (yc - 2.9) if trk == ta else (yc + 2.9)
                uv = atlas(trk - 1, 2, 2)
                bx(mb, hx2 - 0.03, hx2 + 0.03, yy - 0.82, yy + 0.82, G.DECK + 2.42, G.DECK + 2.86, K("housing"))
                for side in (-1, 1):
                    sign_quad(mb, (hx2 + side * 0.032, yy, G.DECK + 2.64), (side, 0.0), 1.60, 0.40, uv, K("sign_trk"))
                bx(mb, hx2 - 0.015, hx2 + 0.015, yy - 0.015, yy + 0.015, G.DECK + 2.86, G.B5_CEIL, K("stain"))
            # yellow exit sign above the enclosure entrance, facing the platform
            hx3 = fr(0.15, 0, 0)[0]
            sign_quad(mb, (hx3 - s * 0.01, yc, G.B5_CEIL - 0.2), (-s, 0.0), 1.30, 0.325, atlas(0, 1, 4), K("sign_way"))
            cnt("departure_boards"); cnt("track_signs", 2)
        # stop boards for the 15-car trains (front of the train) and starting signals
        for trk in (ta, tb):
            dirn = -1 if trk in (1, 2) else 1            # Yokosuka line trains leave towards -x, Sobu towards +x
            ye = G.ISL[isl][0] if trk == ta else G.ISL[isl][1]
            yy = ye + (0.6 if trk == ta else -0.6)
            xb = dirn * 152.4
            bx(mb, xb - 0.03, xb + 0.03, yy - 0.03, yy + 0.03, G.DECK, G.DECK + 1.6, K("stain"))
            sign_quad(mb, (xb - dirn * 0.035, yy, G.DECK + 1.85), (-dirn, 0.0), 0.36, 0.45, (0, 0, 1, 1), K("stop"))
            bx(mb, xb - 0.03, xb + 0.03, yy - 0.2, yy + 0.2, G.DECK + 1.6, G.DECK + 2.1, K("housing"))
            cnt("stop_boards")
    # starting signals at the departure ends (hung beside the tracks)
    for trk, yt in G.TRK.items():
        dirn = -1 if trk in (1, 2) else 1
        xs = dirn * 160.0
        ysg = {1: yt - 2.12, 2: -0.40, 3: 0.40, 4: yt + 2.12}[trk]     # housings >= 1.9 m from the track centre
        zs0 = G.RAIL + 3.2
        bx(mb, xs - 0.13, xs + 0.13, ysg - 0.17, ysg + 0.17, zs0, zs0 + 1.0, K("housing"))
        lit = "sig_green" if trk == 1 else ("sig_green" if trk == 4 else "sig_red")
        for k, z in enumerate((zs0 + 0.82, zs0 + 0.5, zs0 + 0.18)):
            m = lit if (k == 0 and lit == "sig_red") or (k == 2 and lit == "sig_green") else "sig_off"
            cpts = [(xs - dirn * 0.135, ysg + 0.09 * math.cos(a), z + 0.09 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 17)[:-1]]
            mb.add(cpts, [tuple(range(16)) if dirn < 0 else tuple(range(15, -1, -1))], K(m))
        bx(mb, xs - 0.03, xs + 0.03, ysg - 0.03, ysg + 0.03, zs0 + 1.0, G.B4_SOFFIT, K("steel_dk"))
        cnt("starting_signals")
    # station name signs and posters on the track walls (facing the platforms) and on the middle column row
    for sg in (-1, 1):
        yw = sg * (G.WALL_IN - 0.07)
        n = (0.0, -sg)
        for x in np.arange(-140.0, 141.0, 35.0):
            bx(mb, x - 1.0, x + 1.0, *sorted((yw, yw + sg * 0.06)), G.DECK + 0.95, G.DECK + 1.75, K("housing"))
            sign_quad(mb, (x, yw - sg * 0.002, G.DECK + 1.35), n, 1.92, 0.64, (0, 0, 1, 1), K("sign_sta"))
            for k, dx in enumerate((-12.0, -7.0, 7.0, 12.0)):
                i = int(abs(x + dx * 3.1)) % 4
                bx(mb, x + dx - 0.75, x + dx + 0.75, *sorted((yw, yw + sg * 0.04)), G.DECK + 0.30, G.DECK + 2.40, K("housing"))
                sign_quad(mb, (x + dx, yw - sg * 0.002, G.DECK + 1.35), n, 1.36, 1.90, atlas(i, 2, 2), K("poster"))
                cnt("posters")
            cnt("station_name_signs")
    for x in np.arange(-129.5, 130.0, 28.0):
        bx(mb, x - 1.0, x + 1.0, -0.06, 0.06, G.DECK + 0.95, G.DECK + 1.75, K("housing"))
        for side in (-1, 1):
            sign_quad(mb, (x, side * 0.062, G.DECK + 1.35), (0.0, side), 1.92, 0.64, (0, 0, 1, 1), K("sign_sta"))
        cnt("station_name_signs", 2)
    # B4: hanging platform signs above each well's arrival end; B1: platform / exit signs at the bank tops
    for isl in G.ISL:
        ta, tb = G.ISL_TRACKS[isl]
        for gx in G.GROUP_X:
            xf, s, yc = G.group_frame(gx, isl)
            fr = Fr(xf, yc, s)
            hx = fr(17.0, 0, 0)[0]
            for trk, dy in ((ta, -0.85), (tb, 0.85)):
                for side in (-1, 1):
                    sign_quad(mb, (hx + side * 0.032, yc + dy, G.B4_FLOOR + 2.45), (side, 0.0), 1.60, 0.40, atlas(trk - 1, 2, 2), K("sign_trk"))
            bx(mb, hx - 0.03, hx + 0.03, yc - 1.67, yc + 1.67, G.B4_FLOOR + 2.24, G.B4_FLOOR + 2.66, K("housing"))
    for bank, (xf, s) in G.BANKS.items():
        fr = Fr(xf, 0.0, s)
        hx = fr(G.BANK_LEN + 2.5, 0, 0)[0]
        for side in (-1, 1):
            sign_quad(mb, (hx + side * 0.032, 0.0, G.B1_CEIL - 0.45), (side, 0.0), 2.4, 0.6, atlas(1 if side == s else 0, 1, 4), K("sign_way"))
        bx(mb, hx - 0.03, hx + 0.03, -1.22, 1.22, G.B1_CEIL - 0.76, G.B1_CEIL - 0.14, K("housing"))
        hx = fr(-1.5, 0, 0)[0]
        for side in (-1, 1):
            sign_quad(mb, (hx + side * 0.032, 0.0, G.B4_CEIL - 0.45), (side, 0.0), 2.4, 0.6, atlas(0 if side == s else 1, 1, 4), K("sign_way"))
        bx(mb, hx - 0.03, hx + 0.03, -1.22, 1.22, G.B4_CEIL - 0.76, G.B4_CEIL - 0.14, K("housing"))
    # sign at the end of the B1 passage
    xm = (G.B1_CORRIDOR_X[0] + G.B1_CORRIDOR_X[1]) / 2
    sign_quad(mb, (xm, G.B1_CORRIDOR_Y + 0.01, G.B1_FLOOR + 2.2), (0.0, 1.0), 4.0, 1.0, atlas(3, 1, 4), K("sign_way"))
    new_obj(mb, "V9 Sobu | signs (station names, departure boards, track numbers, exits, stop boards, signals)", col, K.lst)


def build_furniture(M, col):
    mb = L.MeshBuilder(); K = Mats(M)
    nb = 0
    for isl, yc in G.ISL_C.items():
        for dy in (-G.COL_ROW_OFF, G.COL_ROW_OFF):
            y = yc + dy
            for x in G.COL_X[::2]:
                xm = x + G.BAY / 2
                if not (G.PLAT_X[0] + 6 < xm < G.PLAT_X[1] - 6):
                    continue
                if any(a - 1.5 < xm < b + 1.5 and c - 0.6 < y < d + 0.6 for (a, b, c, d, i2, gx) in ENCL):
                    continue
                if in_rect(xm, y, elev_rect(isl), 1.5):
                    continue
                bx(mb, xm - 0.9, xm + 0.9, y - 0.22, y + 0.22, G.DECK + 0.40, G.DECK + 0.44, K("bench_seat"))
                bx(mb, xm - 0.9, xm + 0.9, y - 0.03, y + 0.03, G.DECK + 0.44, G.DECK + 0.80, K("bench_seat"))
                for xl in (xm - 0.75, xm + 0.75):
                    bx(mb, xl - 0.03, xl + 0.03, y - 0.2, y + 0.2, G.DECK, G.DECK + 0.40, K("stain"))
                nb += 1
        for x in (-133.0, 133.0):
            for k, side in enumerate((-1, 1)):
                y0 = yc + side * 0.05
                a, b = sorted((y0, y0 + side * 0.72))
                bx(mb, x - 0.5, x + 0.5, a, b, G.DECK, G.DECK + 1.83, K("vend"))
                yf = b + 0.002 if side > 0 else a - 0.002
                sign_quad(mb, (x, yf, G.DECK + 1.2), (0.0, side), 0.86, 1.1, (0, 0, 1, 1), K("vend_lit"))
                cnt("vending_machines")
    cnt("benches", nb)
    new_obj(mb, "V9 Sobu | B5 furniture (benches, vending machines)", col, K.lst)


def build_concourse_details(M, col):
    """Tactile guide lines, coin lockers, hydrant cabinets and hanging signs in the B4 and B1 concourses."""
    mb = L.MeshBuilder(); K = Mats(M)

    def strip_x(x0, x1, y, z):
        bx(mb, min(x0, x1), max(x0, x1), y - 0.15, y + 0.15, z, z + 0.006, K("tactile"))

    def strip_y(y0, y1, x, z):
        bx(mb, x - 0.15, x + 0.15, min(y0, y1), max(y0, y1), z, z + 0.006, K("tactile"))
    zf = G.B4_FLOOR
    hx0, hx1 = G.B4_HALL_X
    for sg in (-1, 1):
        strip_x(hx0 + 3.0, hx1 - 3.0, sg * 4.0, zf)
    for isl in G.ISL:
        for gx in G.GROUP_X:
            xf, s, yc = G.group_frame(gx, isl)
            xb = xf + s * 16.6
            strip_y(yc, 4.0 * (1 if yc > 0 else -1), xb, zf)
            cnt("tactile_branches")
    for bank, (xf, s) in G.BANKS.items():
        xb = xf - s * 2.2
        strip_y(-4.0, 4.0, xb, zf)
    # lockers and hydrants against the B4 partitions
    for sg in (-1, 1):
        yw = sg * G.B4_HALL_Y
        for x in (-102.0, -46.0, 10.0, 66.0):
            a, b = sorted((yw, yw - sg * 0.55))
            bx(mb, x - 2.7, x + 2.7, a, b, zf, zf + 1.85, K("locker"))
            bx(mb, x - 2.75, x + 2.75, a - 0.02, b + 0.02, zf + 1.85, zf + 1.92, K("steel_dk"))
            cnt("coin_lockers", 6)
        for x in (-74.0, -18.0, 38.0, 94.0):
            a, b = sorted((yw, yw - sg * 0.2))
            bx(mb, x - 0.4, x + 0.4, a, b, zf + 0.5, zf + 1.55, K("hydrant"))
            cnt("hydrant_cabinets")
    # hanging signs along the B4 hall centre (exit / transfer, double sided)
    for x in np.arange(-119.0, 120.0, 21.0):
        if any(r[0] - 1.0 <= x <= r[1] + 1.0 for r in (bank_rect("A", -2.0, G.BANK_LEN + 3.0), bank_rect("B", -2.0, G.BANK_LEN + 3.0))):
            continue
        row = 0 if int(round(x / 21.0)) % 2 == 0 else 2
        bx(mb, x - 0.03, x + 0.03, -1.22, 1.22, G.B4_CEIL - 0.76, G.B4_CEIL - 0.14, K("housing"))
        for side in (-1, 1):
            sign_quad(mb, (x + side * 0.032, 0.0, G.B4_CEIL - 0.45), (side, 0.0), 2.4, 0.6, atlas(row, 1, 4), K("sign_way"))
        cnt("b4_hanging_signs")
    # B1: guide line from the passage through the gates to both bank tops
    zf = G.B1_FLOOR
    yl = -4.05
    xc = (G.B1_CORRIDOR_X[0] + G.B1_CORRIDOR_X[1]) / 2
    strip_y(G.B1_CORRIDOR_Y + 0.6, yl, xc, zf)
    strip_x(xc, 69.0, yl, zf)
    xa_top = G.BANKS["A"][0] - G.BANK_LEN
    xb_top = G.BANKS["B"][0] + G.BANK_LEN
    strip_y(yl, 0.0, xa_top - 1.6, zf); strip_x(xa_top - 1.6, xa_top - 0.2, 0.0, zf)
    strip_y(yl, 0.0, 69.0, zf); strip_x(xb_top + 0.2, 69.0, 0.0, zf)
    for x in (-20.0, 20.0, 80.0):
        for sg in (-1, 1):
            yw = sg * (G.WALL_IN - 0.03)
            a, b = sorted((yw, yw - sg * 0.55))
            if sg > 0 and x == 20.0:
                continue
            bx(mb, x - 2.7, x + 2.7, a, b, zf, zf + 1.85, K("locker"))
            cnt("coin_lockers", 6)
    new_obj(mb, "V9 Sobu | concourse details (tactile guide lines, lockers, hydrants, hanging signs)", col, K.lst)


# ====================================================================== run
def run():
    sc = bpy.context.scene
    M = materials()
    col = L.collection("V9_Sobu_Underground_Station")
    lcol = L.collection("V9_Sobu_Lights", parent=col)
    build_structure(M, col)
    build_platforms(M, col)
    build_columns_b5(M, col)
    build_columns_upper(M, col)
    build_b5_ceilings(M, col, lcol)
    build_conductor(M, col)
    build_b5_groups(M, col)
    build_banks(M, col, lcol)
    build_lifts(M, col)
    build_b4(M, col, lcol)
    build_b1(M, col, lcol)
    build_machine_floors(M, col, lcol)
    build_marunouchi(M, col)
    build_signs(M, col)
    build_furniture(M, col)
    build_concourse_details(M, col)
    frame = bpy.data.objects.new("V9 Sobu | station frame (local x = along the platforms towards Chiba, y = west)", None)
    frame.empty_display_type = 'ARROWS'; frame.empty_display_size = 20.0
    frame.matrix_world = FR @ Matrix.Translation((0, 0, G.DECK))
    col.objects.link(frame)
    info = {"frame_origin_model_xy": [round(float(v), 3) for v in G.C], "axis_x_model": [round(float(v), 4) for v in G.AX],
            "axis_y_model": [round(float(v), 4) for v in G.AY], "shift_west_of_osm_m": G.SHIFT_W,
            "rail_top_z": G.RAIL, "platform_z": G.DECK, "b4_floor_z": G.B4_FLOOR, "b1_floor_z": G.B1_FLOOR,
            "platform_x": list(G.PLAT_X), "tracks_y": G.TRK, "islands_y": G.ISL, "upper_part_x": list(G.UPPER_X),
            "groups_x": G.GROUP_X, "lifts": {k: list(v) for k, v in G.ELEV.items()}, "banks": G.BANKS,
            "vent_shaft_local": [round(float(VENT_L[0]), 2), round(float(VENT_L[1]), 2)]}
    sc["V9_sobu_station"] = json.dumps(info, ensure_ascii=False)
    REP["station"] = info
    return REP


rep = run()
L.log("V9 station objects", len(rep["objects"]), json.dumps(rep["counts"]))
if REPORT:
    json.dump(rep, open(REPORT, "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=str)
if OUT:
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=True)
    L.log("saved", OUT)
