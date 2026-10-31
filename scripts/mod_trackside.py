"""V5.1 module: track, platform-edge and signalling details.

Track (all 20 tracks, rebuilt along the re-laid centrelines)
  * rails with a real cross-section (JIS 50N on the narrow-gauge lines, 60 kg on the Shinkansen): head, web, foot,
    polished running band on the head, weathered sides; replaces the V3 box head + web
  * PC sleepers every 0.62 m (Shinkansen 0.58 m) with rail pads, cast shoulders and spring clips, as geometry-node
    instances (one template per gauge); replaces the V3 1 m sleeper bed
  * ballast bed with crib and side slopes and a crushed-stone material; replaces the V3 flat ballast box
  * the Tohoku Shinkansen tracks 20-23 end at buffer stops 12 m past their platforms (at Tokyo the Tohoku and
    Tokaido Shinkansen are not connected); their wires beyond are removed
Signals and platform edge
  * departure signals (3-aspect LED heads with hoods and identification plates) on masts at the departure end of
    every conventional platform track; ATS-P transponders between the rails in rear of each signal
  * departure-indicator repeaters (出発反応標識) on the platforms
  * stop-position boards (停止位置目標) at the stopping point of each train (EMU: 1.2 m ahead of the front;
    Shinkansen: beside the driver's window), showing the number of cars
  * door-position floor markers (乗車位置目標) behind the tactile line at every passenger door: of the standing
    train, or - on tracks without one - of the same service stopping at the departure end (N700: 16 cars)
  * warning studs (60 mm pitch) on the platform-edge tactile strips (bump pattern on the existing material)
"""
import sys, os, json, re, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import numpy as np
from mathutils import Vector, Matrix
import v5lib as L
import mod_relayout as RL

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, "textures")
TOHOKU = ("20", "21", "22", "23")
DEPART_NORTH = {"01", "02", "03", "04", "09", "10", "20", "21", "22", "23"}
PROCEED = {"04": "G", "10": "Y"}                 # departure signals showing proceed (trains about to leave)
CONSIST = {"01": 12, "02": 12, "03": 10, "04": 11, "05": 11, "06": 10, "07": 15, "08": 15, "09": 15, "10": 15,
           "14": 16, "15": 16, "16": 16, "17": 16, "18": 16, "19": 16, "20": 17, "21": 17, "22": 17, "23": 17}
MARKER_LINE = {"01": "chuo", "02": "chuo", "03": "kt", "04": "yamanote", "05": "yamanote", "06": "kt",
               "07": "tokaido", "08": "tokaido", "09": "tokaido", "10": "tokaido",
               "14": "tokaido_shinkansen", "15": "tokaido_shinkansen", "16": "tokaido_shinkansen",
               "17": "tokaido_shinkansen", "18": "tokaido_shinkansen", "19": "tokaido_shinkansen",
               "20": "tohoku_shinkansen", "21": "tohoku_shinkansen", "22": "tohoku_shinkansen", "23": "tohoku_shinkansen"}
TOKAIDO_SHIN = ("14", "15", "16", "17", "18", "19")
# tracks without a standing train get the stopping layout of the same service on a neighbouring track:
# same platform and direction -> same stopping point (COPY_POS); otherwise the template is re-positioned
PAIR = {"02": "01", "06": "03", "07": "08", "09": "10", "21": "20", "22": "20", "23": "20"}
COPY_POS = {"02", "07", "09", "21", "22", "23"}
CAB_BEHIND_TIP = {"N700": 8.0, "E5": 11.0}       # Shinkansen stop boards stand beside the driver's window

RAIL = {   # half profile (y, z) from the head top centre, clockwise to the foot centre
    "50N": [(0.0, 0.0), (0.020, -0.0015), (0.0300, -0.0065), (0.0325, -0.016), (0.0325, -0.038), (0.0285, -0.046),
            (0.0075, -0.055), (0.0075, -0.112), (0.0150, -0.128), (0.0635, -0.141), (0.0635, -0.153), (0.0, -0.153)],
    "60": [(0.0, 0.0), (0.020, -0.0015), (0.0300, -0.0065), (0.0325, -0.016), (0.0325, -0.040), (0.0290, -0.048),
           (0.0085, -0.058), (0.0085, -0.128), (0.0170, -0.146), (0.0725, -0.160), (0.0725, -0.174), (0.0, -0.174)],
}
GAUGE = {False: dict(rail="50N", a=0.566, pad=0.006, sl_len=2.00, sl_w=(0.24, 0.19), sl_h=0.170, pitch=0.62, bw=1.18),
         True: dict(rail="60", a=0.750, pad=0.006, sl_len=2.40, sl_w=(0.30, 0.25), sl_h=0.200, pitch=0.58, bw=1.38)}
STATS = {}


# ------------------------------------------------------------------------------------------------ materials
def mat(name, color, rough=0.5, metal=0.0, emission=None, strength=0.0):
    return L.principled(name, color, rough=rough, metal=metal, emission=emission, strength=strength)


def ballast_material():
    m = bpy.data.materials.get("V5 | ballast crushed stone")
    if m:
        return m
    m = bpy.data.materials.new("V5 | ballast crushed stone")
    m.use_nodes = True
    nt = m.node_tree
    pr = nt.nodes.get("Principled BSDF")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    vor = nt.nodes.new("ShaderNodeTexVoronoi"); vor.inputs["Scale"].default_value = 26.0
    vor2 = nt.nodes.new("ShaderNodeTexVoronoi"); vor2.feature = 'DISTANCE_TO_EDGE'; vor2.inputs["Scale"].default_value = 26.0
    noi = nt.nodes.new("ShaderNodeTexNoise"); noi.inputs["Scale"].default_value = 3.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.16, 0.155, 0.15, 1); ramp.color_ramp.elements[1].color = (0.42, 0.40, 0.37, 1)
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
    mix.inputs[0].default_value = 0.35
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.8; bump.inputs["Distance"].default_value = 0.02
    for n_ in (vor, vor2, noi):
        nt.links.new(tc.outputs["Object"], n_.inputs["Vector"])
    nt.links.new(vor.outputs["Color"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], mix.inputs[6]); nt.links.new(noi.outputs["Color"], mix.inputs[7])
    nt.links.new(mix.outputs[2], pr.inputs["Base Color"])
    nt.links.new(vor2.outputs["Distance"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], pr.inputs["Normal"])
    pr.inputs["Roughness"].default_value = 0.92
    return m


def image_material(name, png, emission=0.0, rough=0.5):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    pr = nt.nodes.get("Principled BSDF")
    img = bpy.data.images.get(os.path.basename(png)) or bpy.data.images.load(png)
    img.pack()
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = img
    nt.links.new(t.outputs["Color"], pr.inputs["Base Color"])
    pr.inputs["Roughness"].default_value = rough
    if emission > 0:
        nt.links.new(t.outputs["Color"], pr.inputs["Emission Color"])
        pr.inputs["Emission Strength"].default_value = emission
    return m


# ------------------------------------------------------------------------------------------------ geometry
def centreline(k, x0, x1, step):
    xs = np.arange(x0, x1 + 1e-6, 0.25)
    ys = np.interp(xs, RL.GX, RL.TGT[k])
    s = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(xs), np.diff(ys)))])
    n = max(2, int(round(s[-1] / step)) + 1)
    sq = np.linspace(0.0, s[-1], n)
    X = np.interp(sq, s, xs); Y = np.interp(sq, s, ys)
    ang = np.arctan2(np.gradient(Y), np.gradient(X))
    return X, Y, ang


def track_info():
    out = {}
    for k in RL.ORDER:
        heads = [o for o in bpy.data.objects if re.match(r"V3 Track %s rail head" % k, o.name) and not o.get("V5_retired")]
        if not heads:
            continue
        xs, zt = [], -1e9
        for o in heads:
            ws = [o.matrix_world @ Vector(c) for c in o.bound_box]
            xs += [w.x for w in ws]; zt = max(zt, max(w.z for w in ws))
        x0, x1 = min(xs), max(xs)
        if k in TOHOKU:
            x1 = min(x1, RL.ISL[RL.TRACK_ISLAND[k]]["P"][1] + 12.0)
        out[k] = {"x0": x0 + 0.05, "x1": x1 - 0.05, "z": zt, "shin": k in RL.SHINKANSEN}
    return out


def retire_old_track(k):
    n = 0
    for o in list(bpy.data.objects):
        if o.get("V5_retired"):
            continue
        if re.match(r"V3 Track %s (rail head|rail web|curved sleeper bed|curved ballast)" % k, o.name):
            L.retire(o); n += 1
    return n


def build_rails(k, info, col, m_shiny, m_side):
    g = GAUGE[info["shin"]]
    prof = RAIL[g["rail"]]
    loop = prof + [(-y, z) for (y, z) in reversed(prof[1:-1])]
    n = len(loop)
    X, Y, A = centreline(k, info["x0"], info["x1"], 1.5)
    verts, faces, mats = [], [], []
    for side in (-1, 1):
        base = len(verts)
        for x, y, a in zip(X, Y, A):
            nx, ny = -math.sin(a), math.cos(a)
            cx, cy = x + nx * side * g["a"], y + ny * side * g["a"]
            for py, pz in loop:
                verts.append((cx + nx * py, cy + ny * py, info["z"] + pz))
        ns = len(X)
        for i in range(ns - 1):
            for j in range(n):
                j2 = (j + 1) % n
                faces.append((base + i * n + j, base + (i + 1) * n + j, base + (i + 1) * n + j2, base + i * n + j2))
                mats.append(0 if j in (0, 1, n - 2, n - 1) else 1)
        for i in (0, ns - 1):                                   # end caps
            ring = [base + i * n + j for j in range(n)]
            faces.append(tuple(ring if i else ring[::-1])); mats.append(1)
    me = bpy.data.meshes.new(f"V5 track | Track {k} rails ({g['rail']})")
    me.from_pydata(verts, [], faces)
    me.materials.append(m_shiny); me.materials.append(m_side)
    me.polygons.foreach_set("material_index", mats)
    me.polygons.foreach_set("use_smooth", [True] * len(faces))
    try:
        me.set_sharpness_by_angle(angle=math.radians(40))
    except Exception:
        pass
    me.update()
    ob = bpy.data.objects.new(me.name, me); col.objects.link(ob)
    return len(verts)


def build_ballast(k, info, col, m_ballast):
    g = GAUGE[info["shin"]]
    z = info["z"]
    top = z - RAIL[g["rail"]][-1][1] * -1 - g["pad"] - 0.03               # crib level, just under the sleeper top
    deck = z - 0.57
    half = [(0.0, top), (g["bw"], top), (g["bw"] + 0.10, top - 0.035), (g["bw"] + 0.47, deck + 0.01), (g["bw"] + 0.47, deck - 0.08)]
    prof = [(-y, zz) for (y, zz) in reversed(half[1:])] + half
    X, Y, A = centreline(k, info["x0"] - 0.3, info["x1"] + 0.3, 2.0)
    verts, faces = [], []
    n = len(prof)
    for x, y, a in zip(X, Y, A):
        nx, ny = -math.sin(a), math.cos(a)
        for py, pz in prof:
            verts.append((x + nx * py, y + ny * py, pz))
    for i in range(len(X) - 1):
        for j in range(n - 1):
            faces.append((i * n + j, (i + 1) * n + j, (i + 1) * n + j + 1, i * n + j + 1))
    for i in (0, len(X) - 1):                                   # closed ends (buffer stops, site edge)
        ring = [i * n + j for j in range(n)]
        faces.append(tuple(ring if i == 0 else ring[::-1]))
    me = bpy.data.meshes.new(f"V5 track | Track {k} ballast bed")
    me.from_pydata(verts, [], faces)
    me.materials.append(m_ballast)
    me.update()
    ob = bpy.data.objects.new(me.name, me); col.objects.link(ob)
    return top


def sleeper_template(shin, col, mats):
    """One PC sleeper with two rail seats (pad, shoulders, spring clips); origin = sleeper top at the track centre."""
    g = GAUGE[shin]
    i_conc, i_pad, i_shoulder, i_clip = mats
    mb = L.MeshBuilder()
    half = g["sl_len"] / 2
    wb, wt = g["sl_w"]
    h = g["sl_h"]
    ys = [-half, -half + 0.25, -0.40, 0.40, half - 0.25, half]
    hs = [h - 0.01, h, h - 0.025, h - 0.025, h, h - 0.01]
    tw = [wt - 0.02, wt, wt - 0.02, wt - 0.02, wt, wt - 0.02]
    V, F = [], []
    for y, hh, w in zip(ys, hs, tw):
        z0 = -hh + (h - hh) * 0.0
        top = -(h - hh)                       # rail seats are the highest part
        V += [(-wb / 2, y, -h), (wb / 2, y, -h), (w / 2, y, top), (-w / 2, y, top)]
    ns = len(ys)
    for i in range(ns - 1):
        for j in range(4):
            j2 = (j + 1) % 4
            F.append((i * 4 + j, (i + 1) * 4 + j, (i + 1) * 4 + j2, i * 4 + j2))
    F.append((0, 3, 2, 1)); F.append(((ns - 1) * 4, (ns - 1) * 4 + 1, (ns - 1) * 4 + 2, (ns - 1) * 4 + 3))
    mb.add(V, F, mat=i_conc)
    foot = RAIL[g["rail"]][-2][0]
    for s in (-1, 1):
        a = s * g["a"]
        L.box(mb, 0.0, a, g["pad"] / 2, 0.16, foot * 2 + 0.02, g["pad"], i_pad)
        for t in (-1, 1):
            ysh = a + t * (foot + 0.032)
            L.box(mb, 0.0, ysh, 0.028, 0.085, 0.045, 0.056, i_shoulder)
            p0 = Vector((-0.055, ysh + t * 0.012, 0.052)); p1 = Vector((0.0, a + t * (foot - 0.004), g["pad"] + 0.016))
            p2 = Vector((0.055, ysh + t * 0.012, 0.052))
            L.tube(mb, [p0, p1, p2], 0.0075, sides=6, mat=i_clip)
    ob = mb.build(f"V5 template | {'Shinkansen' if shin else 'narrow-gauge'} PC sleeper with fastenings", col,
                  [m for m in TEMPLATE_MATS])
    ob.hide_render = True
    ob.hide_viewport = True
    return ob


TEMPLATE_MATS = []


def instancer_group():
    ng = bpy.data.node_groups.get("V5 instance on track points")
    if ng:
        return ng
    ng = bpy.data.node_groups.new("V5 instance on track points", 'GeometryNodeTree')
    ng.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket("Template", in_out='INPUT', socket_type='NodeSocketObject')
    ng.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    N = ng.nodes
    gi = N.new("NodeGroupInput"); go = N.new("NodeGroupOutput")
    oi = N.new("GeometryNodeObjectInfo"); oi.transform_space = 'ORIGINAL'
    oi.inputs["As Instance"].default_value = True
    iop = N.new("GeometryNodeInstanceOnPoints")
    na = N.new("GeometryNodeInputNamedAttribute"); na.data_type = 'FLOAT'; na.inputs["Name"].default_value = "yaw"
    cx = N.new("ShaderNodeCombineXYZ")
    ng.links.new(gi.outputs["Geometry"], iop.inputs["Points"])
    ng.links.new(gi.outputs["Template"], oi.inputs["Object"])
    ng.links.new(oi.outputs["Geometry"], iop.inputs["Instance"])
    ng.links.new(na.outputs["Attribute"], cx.inputs["Z"])
    ng.links.new(cx.outputs["Vector"], iop.inputs["Rotation"])
    ng.links.new(iop.outputs["Instances"], go.inputs["Geometry"])
    return ng


def build_sleepers(k, info, col, template):
    g = GAUGE[info["shin"]]
    X, Y, A = centreline(k, info["x0"] + 0.4, info["x1"] - 0.4, g["pitch"])
    ztop = info["z"] + RAIL[g["rail"]][-1][1] - g["pad"]
    me = bpy.data.meshes.new(f"V5 track | Track {k} sleeper points")
    me.from_pydata([(float(x), float(y), ztop) for x, y in zip(X, Y)], [], [])
    at = me.attributes.new("yaw", 'FLOAT', 'POINT')
    at.data.foreach_set("value", [float(a) for a in A])
    me.update()
    ob = bpy.data.objects.new(f"V5 track | Track {k} PC sleepers + fastenings", me)
    col.objects.link(ob)
    mod = ob.modifiers.new("V5 sleepers", 'NODES')
    ng = instancer_group()
    mod.node_group = ng
    ident = ng.interface.items_tree["Template"].identifier
    try:                                    # Blender 5.x: inputs live on modifier.properties
        getattr(mod.properties.inputs, ident).value = template
    except AttributeError:                  # Blender 4.x: id-property on the modifier
        mod[ident] = template
    return len(X)


# ------------------------------------------------------------------------------------------------ helpers
class Obstacles:
    """Plan-view hash of static geometry (vertices) to keep new posts and masts clear of existing structure."""

    def __init__(self, zlo, zhi, xwins=None):
        pts = []
        for o in bpy.data.objects:
            if o.type != 'MESH' or o.get("V5_retired") or o.hide_render or not o.users_scene:
                continue
            if xwins:
                bx = [(o.matrix_world @ Vector(c)).x for c in o.bound_box]
                if not any(min(bx) < b and max(bx) > a for a, b in xwins):
                    continue
            if o.name.startswith("V5 track |") or o.name.startswith("V5 template"):
                continue
            me = o.data
            n = len(me.vertices)
            if n == 0 or n > 400000:
                continue
            co = np.empty(n * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
            m = np.array(o.matrix_world); w = co @ m[:3, :3].T + m[:3, 3]
            w = w[(w[:, 2] > zlo) & (w[:, 2] < zhi)]
            if len(w):
                pts.append(w[:, :2])
        self.P = np.concatenate(pts) if pts else np.zeros((0, 2))

    def clear(self, x, y, r):
        if len(self.P) == 0:
            return True
        d = (self.P[:, 0] - x) ** 2 + (self.P[:, 1] - y) ** 2
        return not np.any(d < r * r)


def frame(x, y, z, fwd_ang):
    """Local frame: u = facing direction (fwd_ang in plan), v = 90 deg to the left of u, z up."""
    c, s = math.cos(fwd_ang), math.sin(fwd_ang)
    return Matrix(((c, -s, 0, x), (s, c, 0, y), (0, 0, 1, z), (0, 0, 0, 1)))


def fbox(mb, F, u, v, z, su, sv, sz, mat):
    """Box of size (su, sv, sz) centred at (u, v, z) in frame F.  (v5lib.box ignores its centre arguments
    when a frame is passed, so the centre is folded into the frame here.)"""
    L.box(mb, 0, 0, 0, su, sv, sz, mat, frame=F @ Matrix.Translation((u, v, z)))


def disc(mb, F, centre, r, mat, n=16, normal_u=True):
    cu, cv, cz = centre
    vs = [F @ Vector((cu, cv, cz))]
    for i in range(n):
        a = 2 * math.pi * i / n
        vs.append(F @ Vector((cu, cv + r * math.cos(a), cz + r * math.sin(a))))
    faces = [(0, 1 + i, 1 + (i + 1) % n) for i in range(n)]
    mb.add([tuple(v) for v in vs], faces, mat=mat)


def quad_uv(mb, F, u, v0, v1, z0, z1, mat, flip=False):
    """Vertical quad facing +u in frame F; seen from the front, +v is to the viewer's right, so texture u runs
    with v."""
    pts = [F @ Vector((u, v0, z0)), F @ Vector((u, v1, z0)), F @ Vector((u, v1, z1)), F @ Vector((u, v0, z1))]
    uvs = [(0, 0), (1, 0), (1, 1), (0, 1)]
    mb.add([tuple(p) for p in pts], [(0, 1, 2, 3)], mat=mat, uvs=[uvs])


def track_y(k, x):
    return float(np.interp(x, RL.GX, RL.TGT[k]))


def track_ang(k, x):
    return math.atan2(track_y(k, x + 1.0) - track_y(k, x - 1.0), 2.0)


def platform_side(k):
    isl = RL.TRACK_ISLAND.get(k)
    if not isl:
        return None, None
    v = RL.ISL[isl]
    return isl, (1 if v["west"] == k else -1)


def deck_top(isl):
    o = bpy.data.objects.get(f"V3 Platform {isl} raised deck")
    if o is None:
        return None
    return max((o.matrix_world @ Vector(c)).z for c in o.bound_box)


def edge_offset(k, x):
    isl, side = platform_side(k)
    w = float(np.interp(x, RL.GX, RL.CLEARANCE.get(k, np.zeros(len(RL.GX)))))
    return RL.ISL[isl]["edge"] + w


# ------------------------------------------------------------------------------------------------ signals
def build_signal(mb, k, x, z_rail, aspect, M, plate_mat, obstacles):
    """Departure signal on a mast on the left of the departing train; head above the car roofs facing the train."""
    north = k in DEPART_NORTH
    travel = math.pi if north else 0.0
    ang = track_ang(k, x) + (math.pi if north else 0.0)        # travel direction (with curve)
    face = ang + math.pi                                        # the head faces the approaching train
    left = ang + math.pi / 2
    lx, ly = math.cos(left), math.sin(left)
    yc = track_y(k, x)
    # neighbour track on the left: keep the mast in the middle of the gap, at most 2.2 m from the track
    gaps = []
    for k2 in RL.ORDER:
        if k2 == k or (k in ("01", "02")) != (k2 in ("01", "02")):
            continue
        d = (track_y(k2, x) - yc) * ly
        if d > 0.5:
            gaps.append(d)
    gap = min(gaps) if gaps else 6.0
    off = min(2.2, gap / 2.0)
    if off < 1.95:
        return None
    for dx in (0.0, 3.0, -3.0, 6.0, -6.0, 9.0, -9.0):
        xm = x + dx
        yt = track_y(k, xm)
        mx, my = xm + lx * off, yt + ly * off
        if obstacles.clear(mx, my, 0.55):
            break
    else:
        return None
    zd = z_rail - 0.57
    F = frame(mx, my, zd, face)
    # frame v axis (left of the facing direction) vs the direction from the mast to the track
    vax, vay = math.cos(face + math.pi / 2), math.sin(face + math.pi / 2)
    vt = 1.0 if (vax * (-lx) + vay * (-ly)) > 0 else -1.0
    hz = z_rail + 4.75 - zd                                     # head centre height
    L.tube(mb, [F @ Vector((0, 0, 0)), F @ Vector((0, 0, hz + 0.75))], 0.085, sides=10, mat=M["mast"])
    fbox(mb, F, 0, 0, 0.04, 0.5, 0.5, 0.08, M["mast"])
    arm = off - 1.55
    fbox(mb, F, 0.0, vt * arm / 2, hz + 0.62, 0.10, arm + 0.1, 0.10, M["mast"])
    fbox(mb, F, 0.0, vt * arm / 2, hz - 0.62, 0.08, arm + 0.1, 0.08, M["mast"])
    hv = vt * arm
    fbox(mb, F, 0.0, hv, hz, 0.12, 0.44, 1.18, M["head"])                       # case
    fbox(mb, F, 0.07, hv, hz, 0.02, 0.56, 1.30, M["head"])                      # backplate
    for i, (dz, col) in enumerate(((0.36, "G"), (0.0, "Y"), (-0.36, "R"))):
        lit = (aspect == col)
        disc(mb, F, (0.085, hv, hz + dz), 0.082, M["lit_" + col] if lit else M["lens_off"])
        # hood: top + sides of a short visor
        fbox(mb, F, 0.17, hv, hz + dz + 0.11, 0.17, 0.24, 0.015, M["head"])
        for t in (-1, 1):
            fbox(mb, F, 0.17, hv + t * 0.115, hz + dz + 0.02, 0.17, 0.012, 0.19, M["head"])
    quad_uv(mb, F, 0.085, hv - 0.18, hv + 0.18, hz - 0.84, hz - 0.68, plate_mat)
    fbox(mb, F, 0.06, hv, hz - 0.76, 0.02, 0.40, 0.20, M["head"])
    return (mx, my, ang)


def build_repeater(mb, k, x_plat_end, z_deck, proceed, M):
    """出発反応標識: small box with a white lamp on a post near the departure end of the platform."""
    isl, side = platform_side(k)
    north = k in DEPART_NORTH
    x = x_plat_end + (6.0 if north else -6.0)
    ang = track_ang(k, x) + (math.pi if north else 0.0)
    d = edge_offset(k, x) + 2.0
    yc = track_y(k, x)
    nx, ny = -math.sin(track_ang(k, x)), math.cos(track_ang(k, x))
    px, py = x + nx * side * d, yc + ny * side * d
    F = frame(px, py, z_deck, ang + math.pi)
    L.tube(mb, [F @ Vector((0, 0, 0)), F @ Vector((0, 0, 2.55))], 0.04, sides=8, mat=M["mast"])
    fbox(mb, F, 0.0, 0.0, 2.68, 0.16, 0.30, 0.26, M["head"])
    disc(mb, F, (0.085, 0.0, 2.68), 0.075, M["lit_W"] if proceed else M["lens_off"])
    fbox(mb, F, 0.14, 0.0, 2.77, 0.12, 0.20, 0.012, M["head"])


def build_stop_board(mb, k, x, z_deck, M, board_mat):
    isl, side = platform_side(k)
    north = k in DEPART_NORTH
    ang = track_ang(k, x) + (math.pi if north else 0.0)
    d = edge_offset(k, x) + 0.55
    yc = track_y(k, x)
    nx, ny = -math.sin(track_ang(k, x)), math.cos(track_ang(k, x))
    px, py = x + nx * side * d, yc + ny * side * d
    F = frame(px, py, z_deck, ang + math.pi)
    L.tube(mb, [F @ Vector((0, 0, 0)), F @ Vector((0, 0, 1.55))], 0.03, sides=8, mat=M["mast"])
    fbox(mb, F, -0.01, 0.0, 1.62, 0.02, 0.37, 0.45, M["mast"])                  # plain grey back
    quad_uv(mb, F, 0.002, -0.17, 0.17, 1.41, 1.83, board_mat)


def build_transponder(mb, k, x, z_rail, M):
    yc = track_y(k, x)
    a = track_ang(k, x)
    F = frame(x, yc, z_rail - 0.16, a)
    fbox(mb, F, 0.0, 0.0, 0.055, 0.52, 0.32, 0.11, M["ats"])
    fbox(mb, F, 0.0, 0.0, 0.004, 0.70, 0.40, 0.008, M["mast"])


def build_buffer_stop(mb, k, x, z_rail, M):
    """Steel buffer stop (第1種車止め) with a striped beam and a buffer-stop sign with its red lamp."""
    a = track_ang(k, x)
    yc = track_y(k, x)
    F = frame(x, yc, z_rail, a + math.pi)                      # faces the arriving train (-x travel)
    g = GAUGE[True]
    for s in (-1, 1):
        v = s * g["a"]
        fbox(mb, F, -0.6, v, 0.30, 1.6, 0.12, 0.10, M["mast"])                 # rail-mounted frame
        L.tube(mb, [F @ Vector((-1.3, v, 0.0)), F @ Vector((0.0, v, 0.95))], 0.06, sides=8, mat=M["mast"])
        L.tube(mb, [F @ Vector((0.4, v, 0.0)), F @ Vector((0.0, v, 0.95))], 0.06, sides=8, mat=M["mast"])
    fbox(mb, F, 0.02, 0.0, 0.98, 0.30, 2.2, 0.36, M["buffer_beam"])
    fbox(mb, F, 0.18, 0.0, 0.98, 0.02, 2.0, 0.24, M["stripe"])
    L.tube(mb, [F @ Vector((-0.35, 0.0, 1.15)), F @ Vector((-0.35, 0.0, 2.45))], 0.05, sides=8, mat=M["mast"])
    fbox(mb, F, -0.33, 0.0, 2.55, 0.04, 0.70, 0.30, M["sign_white"])
    fbox(mb, F, -0.31, 0.0, 2.55, 0.02, 0.64, 0.10, M["lit_R"])
    disc(mb, F, (-0.30, 0.0, 2.80), 0.07, M["lit_R"])


# ------------------------------------------------------------------------------------------------ door markers
def n700_doors():
    """16-car N700: (distance of each passenger-door centre from the north end, car number), total length.
    Cars 1 and 16 are 27.35 m with one passenger door at the inner end, cars 2-15 are 25 m with a door at each
    end.  Car 1 is the Hakata end, i.e. the south end at Tokyo."""
    lens = [27.35] + [25.0] * 14 + [27.35]
    out, x = [], 0.0
    for i, lc in enumerate(lens):
        car = 16 - i
        if i > 0:
            out.append((x + 1.2, car))
        if i < len(lens) - 1:
            out.append((x + lc - 1.2, car))
        x += lc
    return out, x


def standing_train(k):
    """Train standing at track k: passenger-door centres (world x, car number), north / south end x, car count,
    kind.  Commuter cars are numbered from the north end (illustrative); Shinkansen car 1 is at the south end
    (Tokaido: Hakata end, Tohoku: Tokyo end)."""
    shin = k in RL.SHINKANSEN
    cars = []
    for e in bpy.data.objects:
        if e.type != 'EMPTY' or not e.instance_collection or not re.match(r"Track %s " % k, e.name):
            continue
        col = e.instance_collection
        if col.name.startswith("V3 N700"):
            x0, x1 = RL.world_xspan(e)
            rel, length = n700_doors()
            return {"doors": [(x0 + r, c) for r, c in rel], "north": x0, "south": x0 + length, "cars": 16,
                    "kind": "N700"}
        base = col if "V5_doors" in col.keys() else next((c for c in col.children if "V5_doors" in c.keys()), None)
        cars.append((e.matrix_world.translation.x, e, base, RL.world_xspan(e)))
    if not cars:
        return None
    cars.sort(key=lambda c: c[0])
    n_cars = len(cars)
    out = []
    for i, (_, e, base, span) in enumerate(cars):
        car = (n_cars - i) if shin else (i + 1)
        if base is None:
            # cars without a one-piece master (V4 double-deck Green cars of the E233-3000): one door near each
            # car end; other EMU cars: the 4-door E233 pattern
            xc, half = (span[0] + span[1]) / 2, (span[1] - span[0]) / 2
            offs = (-(half - 1.6), half - 1.6) if ("Green" in e.instance_collection.name or shin) else (-6.7, -2.3, 2.3, 6.7)
            out += [(xc + o, car) for o in offs]
            continue
        seen = set()
        for s, a, b in json.loads(base["V5_doors"]):
            if (b - a) < 0.9 and not shin:              # cab crew doors get no boarding marker
                continue
            key = round((a + b) / 2, 2)
            if key in seen:
                continue
            seen.add(key)
            p = e.matrix_world @ Vector(((a + b) / 2, 0, 0))
            out.append((p.x, car))
    kind = "E5" if any("E5" in c[1].instance_collection.name for c in cars) else "EMU"
    return {"doors": out, "north": cars[0][3][0], "south": cars[-1][3][1], "cars": n_cars, "kind": kind}


def train_layout(k):
    """Stopping layout at track k: the standing train, or a virtual one (same service, stopping point at the
    departure end of the platform) so that every platform edge gets its boarding markers and stop board."""
    t = standing_train(k)
    if t:
        t["virtual"] = False
        return t
    isl, side = platform_side(k)
    if isl is None:
        return None
    A, B = RL.usable_range(k, *RL.ISL[isl]["P"])
    north = k in DEPART_NORTH
    if k in TOKAIDO_SHIN:
        rel, length = n700_doors()
        xn = (B - 1.0) - length
        return {"doors": [(xn + r, c) for r, c in rel], "north": xn, "south": xn + length, "cars": 16,
                "kind": "N700", "virtual": True}
    src = PAIR.get(k)
    t = standing_train(src) if src else None
    if t is None:
        return None
    if k in COPY_POS:
        return dict(t, virtual=True)
    length = t["south"] - t["north"]
    xn = (A + 4.2) if north else (B - 4.2 - length)
    return {"doors": [(xn + (x - t["north"]), c) for x, c in t["doors"]], "north": xn, "south": xn + length,
            "cars": t["cars"], "kind": t["kind"], "virtual": True}


def build_door_markers(k, z_deck, atlas_mat, col, lay):
    isl, side = platform_side(k)
    if not lay or isl is None:
        return 0
    A, B = RL.ISL[isl]["P"]
    doors = [(x, c) for x, c in lay["doors"] if A + 0.6 < x < B - 0.6]
    verts, faces, uvs = [], [], []
    for x, car in doors:
        a = track_ang(k, x)
        nx, ny = -math.sin(a), math.cos(a)
        tx, ty = math.cos(a), math.sin(a)
        d0 = edge_offset(k, x) + (1.00 if k in RL.SHINKANSEN else 0.88)
        d1 = d0 + 0.40
        hw = 0.30
        yc = track_y(k, x)
        cell = min(car, 16) - 1
        cu0, cv0 = (cell % 4) / 4.0, 1.0 - (cell // 4 + 1) / 4.0
        corner = [(d0, -hw), (d0, hw), (d1, hw), (d1, -hw)]
        pts, uv = [], []
        for dd, tt in corner:
            pts.append((x + tx * tt + nx * side * dd, yc + ty * tt + ny * side * dd, z_deck + 0.004))
            # read from the platform facing the track: top of the text toward the track, u to the reader's right
            u = 0.5 - side * tt / (2 * hw)
            v = (d1 - dd) / (d1 - d0)
            uv.append((cu0 + 0.25 * u, cv0 + 0.25 * v))
        o = len(verts)
        verts += pts
        order = [0, 1, 2, 3] if side > 0 else [3, 2, 1, 0]          # face normal up
        faces.append(tuple(o + i for i in order))
        uvs.append([uv[i] for i in order])
    if not faces:
        return 0
    me = bpy.data.meshes.new(f"V5 platform | Track {k} door-position floor markers")
    me.from_pydata(verts, [], faces)
    uvl = me.uv_layers.new(name="UVMap")
    for fi, poly in enumerate(me.polygons):
        for ci, li in enumerate(poly.loop_indices):
            uvl.data[li].uv = uvs[fi][ci]
    me.materials.append(atlas_mat)
    me.update()
    ob = bpy.data.objects.new(me.name, me); col.objects.link(ob)
    return len(faces)


def retire_tohoku_wires(x_end):
    n = 0
    for o in list(bpy.data.objects):
        if o.get("V5_retired") or not re.search(r"Track 2[0-3] (contact wire|messenger|catenary dropper)", o.name):
            continue
        ws = [o.matrix_world @ Vector(c) for c in o.bound_box]
        k = re.search(r"Track (2[0-3])", o.name).group(1)
        if min(w.x for w in ws) > x_end[k] + 3.0:
            L.retire(o); n += 1
    return n


def stop_board_x(k, lay, A, B):
    """Stopping point of the leading cab: 1.2 m ahead of an EMU's front, beside the driver's window of a
    Shinkansen (long nose); platform end when no layout is known."""
    north = k in DEPART_NORTH
    if lay is None:
        return (A + 3.0) if north else (B - 3.0)
    front = lay["north"] if north else lay["south"]
    back = CAB_BEHIND_TIP.get(lay["kind"])
    if back is not None:
        x = front + back if north else front - back
    else:
        x = front - 1.2 if north else front + 1.2
    return min(max(x, A + 1.0), B - 1.0)


def tactile_dots():
    """Warning-block studs (JIS T 9251 style, 60 mm pitch) as a bump pattern on the platform tactile strips."""
    m = bpy.data.materials.get("V2 | tactile paving")
    if m is None or m.get("V5_dots") or not m.node_tree:
        return 0
    nt = m.node_tree
    pr = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if pr is None:
        return 0
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    vm1 = nt.nodes.new("ShaderNodeVectorMath"); vm1.operation = 'MULTIPLY'
    vm1.inputs[1].default_value = (1 / 0.06, 1 / 0.06, 0.0)
    vm2 = nt.nodes.new("ShaderNodeVectorMath"); vm2.operation = 'FRACTION'
    vm3 = nt.nodes.new("ShaderNodeVectorMath"); vm3.operation = 'SUBTRACT'
    vm3.inputs[1].default_value = (0.5, 0.5, 0.0)
    vm4 = nt.nodes.new("ShaderNodeVectorMath"); vm4.operation = 'LENGTH'
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.interpolation_type = 'SMOOTHSTEP'
    mr.inputs["From Min"].default_value = 0.11; mr.inputs["From Max"].default_value = 0.19
    mr.inputs["To Min"].default_value = 1.0; mr.inputs["To Max"].default_value = 0.0
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 1.0
    bump.inputs["Distance"].default_value = 0.004
    nt.links.new(geo.outputs["Position"], vm1.inputs[0])
    nt.links.new(vm1.outputs["Vector"], vm2.inputs[0])
    nt.links.new(vm2.outputs["Vector"], vm3.inputs[0])
    nt.links.new(vm3.outputs["Vector"], vm4.inputs[0])
    nt.links.new(vm4.outputs["Value"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], bump.inputs["Height"])
    if not pr.inputs["Normal"].is_linked:
        nt.links.new(bump.outputs["Normal"], pr.inputs["Normal"])
    pr.inputs["Roughness"].default_value = max(pr.inputs["Roughness"].default_value, 0.6)
    m["V5_dots"] = True
    return m.users


# ------------------------------------------------------------------------------------------------ run
def run():
    col = L.collection("V5_Track_and_Signals")
    tcol = L.collection("V5 track templates", parent=col)
    info = track_info()
    m_shiny = mat("V5 | rail running band (polished)", (0.62, 0.63, 0.64), rough=0.18, metal=1.0)
    m_side = mat("V5 | rail weathered", (0.17, 0.10, 0.07), rough=0.75, metal=0.35)
    m_ballast = ballast_material()
    TEMPLATE_MATS[:] = [mat("V5 | PC sleeper concrete", (0.36, 0.35, 0.33), rough=0.85),
                        mat("V5 | rail pad rubber", (0.03, 0.03, 0.03), rough=0.7),
                        mat("V5 | fastening shoulder cast iron", (0.16, 0.16, 0.17), rough=0.6, metal=0.6),
                        mat("V5 | spring clip steel", (0.12, 0.11, 0.10), rough=0.55, metal=0.7)]
    tpl = {False: sleeper_template(False, tcol, (0, 1, 2, 3)), True: sleeper_template(True, tcol, (0, 1, 2, 3))}
    rec = {"tracks": {}}
    for k, inf in info.items():
        r = {"retired_v3_parts": retire_old_track(k)}
        r["rail_verts"] = build_rails(k, inf, col, m_shiny, m_side)
        build_ballast(k, inf, col, m_ballast)
        r["sleepers"] = build_sleepers(k, inf, col, tpl[inf["shin"]])
        r["x_range"] = [round(inf["x0"], 1), round(inf["x1"], 1)]
        rec["tracks"][k] = r
    x_end = {k: info[k]["x1"] for k in TOHOKU if k in info}
    rec["tohoku_wires_removed_beyond_buffer_stops"] = retire_tohoku_wires(x_end)

    # ---- signalling and platform-edge equipment
    M = {}
    mats = []

    def add(key, m):
        if m not in mats:
            mats.append(m)
        M[key] = mats.index(m)
    add("mast", mat("V5 | signal mast grey", (0.32, 0.33, 0.34), rough=0.55, metal=0.5))
    add("head", mat("V5 | signal head black", (0.010, 0.010, 0.011), rough=0.85))
    add("lens_off", mat("V5 | signal lens unlit", (0.05, 0.05, 0.055), rough=0.08))
    add("lit_R", mat("V5 | signal lamp red (lit)", (0.5, 0.01, 0.01), rough=0.1, emission=(1.0, 0.012, 0.006), strength=3.0))
    add("lit_Y", mat("V5 | signal lamp yellow (lit)", (0.6, 0.30, 0.01), rough=0.1, emission=(1.0, 0.42, 0.0), strength=3.0))
    add("lit_G", mat("V5 | signal lamp green (lit)", (0.01, 0.45, 0.22), rough=0.1, emission=(0.0, 1.0, 0.42), strength=3.0))
    add("lit_W", mat("V5 | repeater lamp white (lit)", (0.9, 0.9, 0.85), rough=0.1, emission=(1.0, 0.97, 0.9), strength=4.0))
    add("ats", mat("V5 | ATS-P transponder yellow", (0.75, 0.55, 0.05), rough=0.5))
    add("buffer_beam", mat("V5 | buffer stop beam red", (0.55, 0.04, 0.03), rough=0.5))
    add("stripe", mat("V5 | buffer stop stripes", (0.85, 0.85, 0.82), rough=0.5))
    add("sign_white", mat("V5 | sign white", (0.9, 0.9, 0.88), rough=0.5))
    plates = {}
    for t in range(1, 11):
        png = os.path.join(TEX, f"signal_plate_{t:02d}.png")
        if os.path.exists(png):
            add(f"plate{t}", image_material(f"V5 | signal plate 出{t}", png, rough=0.4))
    boards = {}
    for n_ in (8, 10, 11, 12, 15, 16, 17):
        for sh in (False, True):
            png = os.path.join(TEX, f"stop_{n_}{'_shinkansen' if sh else ''}.png")
            if os.path.exists(png):
                add(f"stop{n_}{'s' if sh else ''}", image_material(f"V5 | stop position board {n_}{' (Shinkansen)' if sh else ''}", png, rough=0.45))
    wins = []
    for k in RL.ORDER:
        isl, side = platform_side(k)
        if isl and k not in RL.SHINKANSEN:
            A, B = RL.ISL[isl]["P"]
            xs_ = (A - 6.0) if k in DEPART_NORTH else (B + 6.0)
            wins.append((xs_ - 12.0, xs_ + 12.0))
    obstacles = {"ground": Obstacles(5.5, 11.7, wins), "chuo": Obstacles(15.8, 21.6, wins)}
    layouts = {k: train_layout(k) for k in RL.ORDER if k in info}
    mb = L.MeshBuilder()
    sig, boards = {}, {}
    for k in RL.ORDER:
        if k not in info:
            continue
        isl, side = platform_side(k)
        if isl is None:
            continue
        A, B = RL.ISL[isl]["P"]
        north = k in DEPART_NORTH
        z_rail = info[k]["z"]
        zdeck = deck_top(isl) or (z_rail + 1.04)
        if not info[k]["shin"]:
            x_sig = (A - 6.0) if north else (B + 6.0)
            if info[k]["x0"] + 3 < x_sig < info[k]["x1"] - 3:
                t = int(k)
                res = build_signal(mb, k, x_sig, z_rail, PROCEED.get(k, "R"), M, M.get(f"plate{t}", M["head"]),
                                   obstacles["chuo" if k in ("01", "02") else "ground"])
                if res:
                    sig[k] = {"x": round(res[0], 1), "aspect": PROCEED.get(k, "R")}
                    for dd in (12.0, 30.0):
                        build_transponder(mb, k, x_sig + (dd if north else -dd), z_rail, M)
            build_repeater(mb, k, A if north else B, zdeck, k in PROCEED, M)
        # stop-position board at the stopping point of the leading cab (standing or virtual train)
        lay = layouts.get(k)
        x_stop = stop_board_x(k, lay, A, B)
        n_cars = lay["cars"] if lay else CONSIST.get(k, 10)
        key = f"stop{n_cars}{'s' if info[k]['shin'] else ''}"
        if key in M:
            build_stop_board(mb, k, x_stop, zdeck, M, M[key])
            boards[k] = {"x": round(x_stop, 1), "cars": n_cars, "virtual_train": bool(lay and lay["virtual"])}
    ob = mb.build("V5 trackside | signals, repeaters, stop boards, ATS transponders", col, mats)
    rec["departure_signals"] = sig
    rec["stop_boards"] = boards
    mb2 = L.MeshBuilder()
    n_bs = 0
    for k in TOHOKU:
        if k in info:
            build_buffer_stop(mb2, k, info[k]["x1"] - 0.4, info[k]["z"], M)
            n_bs += 1
    if n_bs:
        mb2.build("V5 trackside | Tohoku Shinkansen buffer stops (tracks 20-23)", col, mats)
    rec["buffer_stops"] = n_bs
    # ---- door-position floor markers
    nm, per = 0, {}
    for k in RL.ORDER:
        isl, side = platform_side(k)
        if isl is None or k not in info:
            continue
        png = os.path.join(TEX, f"door_markers_{MARKER_LINE[k]}.png")
        if not os.path.exists(png):
            continue
        am = image_material(f"V5 | door-position markers {MARKER_LINE[k]}", png, rough=0.6)
        n = build_door_markers(k, (deck_top(isl) or info[k]["z"] + 1.04), am, col, layouts.get(k))
        per[k] = n
        nm += n
    rec["door_position_markers"] = nm
    rec["door_position_markers_by_track"] = per
    rec["tactile_strips_with_studs"] = tactile_dots()
    for k, v in rec.items():
        L.log(k, v)
    return rec


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    bpy.ops.wm.open_mainfile(filepath=src, load_ui=False, use_scripts=False)
    info = run()
    bpy.context.scene["V5_trackside_summary"] = json.dumps(info)
    bpy.ops.wm.save_as_mainfile(filepath=dst, compress=True)
    print("SAVED", dst)
