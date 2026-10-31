"""V8 module 1: the Shinkansen side sits higher than the conventional lines.

Why (round-8 feedback "新干线的铁道和平面明显是比地图高一截的，你现在做成一样高"):
  Up to V7 the Shinkansen rails (tracks 14-23) were at the same level as the conventional rails (5.17 m) and the
  Shinkansen platforms only 0.2-0.3 m higher than the conventional ones.  At the real station the Shinkansen
  viaducts are higher: when conventional platforms were converted for the Shinkansen, "新幹線のレール面は在来線に
  比べてさらに1.9 mほど高かった" (ja.wikipedia 東京駅の歴史), and the Shinkansen platforms look down on the
  conventional lines because of the different viaduct heights (Nikkei, 2023).  DZ = 1.90 m is used here.

What this module does (post-processing of the V7 file, nothing is rebuilt):
  * corridor = everything east of the line half-way between track 10 and track 20 (the gap between platform 9-10 and
    platform 20-21), up to 6 m beyond track 19.  Inside it every vertex above ZCUT = 0.5 m is raised by DZ; the
    pier foundations at ground level stay, so the pier shafts get longer.
  * objects lying completely inside (trains, people, escalators, roofs, cameras, ...) are moved as a whole
    (their children follow); merged meshes that straddle the line are edited per connected piece:
      - pieces completely inside are raised
      - short transverse members that cross the line (pier caps, cross girders, bracing and the three overhead-line
        portals north of the platforms) are cut at the line, the cut ends are capped and the east part is raised;
        each cut portal gets a new mast at the cut that carries both halves
      - long strips along the line (deck infill, the track-10 viaduct) stay at the conventional level and are
        trimmed back to the new side wall
      - small pieces that only touch the line (masts in the 10/20 gap, their arms) stay
  * a concrete side wall with a coping runs along the line, from the conventional deck up to the new
    Shinkansen deck
  * scene properties V5_shinkansen_roofs and V6_platform_keepouts (Shinkansen side): z values += DZ;
    V8_shinkansen_level written

usage: blender -b in.blend --python-exit-code 1 -P mod8_shinkansen_level.py -- out.blend [report.json]
"""
import sys, os, json, math, re
import numpy as np
import bpy
import bmesh
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v5lib as L

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGV[0] if ARGV else None
REPORT = ARGV[1] if len(ARGV) > 1 else None

DZ = 1.90
ZCUT = 0.50                  # vertices at or below this height (foundations, ground) stay
EAST_MARGIN = 6.0            # corridor ends this far beyond track 19
WALL_OFF = 0.30              # west face of the new side wall, east of the line
WALL_T = 0.40
CONV_DECK = 4.61             # conventional deck top (relayout infill)
SHIN_DECK = 4.60 + DZ        # top of the raised Shinkansen viaducts
WALL_Z0 = 3.50
MAST_R = 0.175
CLR = (2.30, 2.60)           # mast face clearance from a conventional / Shinkansen track centre (as in mod6_catenary)

D = json.load(open(os.path.join(HERE, "targets.json")))
GX = np.array(D["X"], float)
TGT = {k: np.array(v, float) for k, v in D["target"].items()}
REP = {"dz_m": DZ, "zcut_m": ZCUT, "moved_objects": {}, "edited_meshes": {}, "split_pieces": 0, "trimmed_pieces": 0,
       "kept_crossing_pieces": 0, "portal_masts": [], "warnings": []}


def ty(k, x):
    return np.interp(x, GX, TGT[k])


def yb(x):
    return 0.5 * (ty("10", x) + ty("20", x))


def yb_slope(x):
    return (yb(x + 0.5) - yb(x - 0.5)) / 1.0


def ye(x):
    return ty("19", x) + EAST_MARGIN


def signed(W):
    """distance east of the line (y - yb) and inside flag for world points W (n,3)"""
    d = W[:, 1] - yb(W[:, 0])
    inside = (d > 0) & (W[:, 1] < ye(W[:, 0]))
    return d, inside


# ------------------------------------------------------------------------------------------------ helpers
def hidden_collections():
    hid = set()

    def walk(lc):
        for c in lc.children:
            if c.exclude or c.hide_viewport or c.collection.hide_render:
                hid.add(c.collection.name)
            walk(c)
    walk(bpy.context.view_layer.layer_collection)
    return hid


def world_points(o):
    M = np.array(o.matrix_world)
    if o.type == 'MESH':
        me = o.data
        n = len(me.vertices)
        if n == 0:
            return np.array([M[:3, 3]])
        co = np.empty(n * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
        return co @ M[:3, :3].T + M[:3, 3]
    if o.type in ('CURVE', 'FONT', 'SURFACE', 'META'):
        bb = np.array([list(c) for c in o.bound_box])
        return bb @ M[:3, :3].T + M[:3, 3]
    return np.array([M[:3, 3]])


def mesh_islands(me):
    n = len(me.vertices); lab = np.arange(n)
    ev = np.empty(len(me.edges) * 2, int); me.edges.foreach_get("vertices", ev); ev = ev.reshape(-1, 2)
    for _ in range(4000):
        if len(ev) == 0:
            break
        m = np.minimum(lab[ev[:, 0]], lab[ev[:, 1]])
        old = lab.copy(); np.minimum.at(lab, ev[:, 0], m); np.minimum.at(lab, ev[:, 1], m); lab = lab[lab]
        if np.array_equal(old, lab):
            break
    return lab


def ancestors(o):
    p = o.parent
    while p is not None:
        yield p
        p = p.parent


# ------------------------------------------------------------------------------------------------ mesh editing
def split_piece(bm, vids, Minv, M3T, W):
    """Cut one connected piece with a vertical plane along the line (local tangent), cap the cut, return True."""
    P = W[vids]
    xc = float(P[:, 0].mean())
    pw = Vector((xc, float(yb(xc)), float(P[:, 2].mean())))
    nw = Vector((-float(yb_slope(xc)), 1.0, 0.0)).normalized()
    pl = Minv @ pw
    nl = (M3T @ nw).normalized()
    vset = [bm.verts[i] for i in vids]
    faces = list({f for v in vset for f in v.link_faces})
    edges = list({e for v in vset for e in v.link_edges})
    res = bmesh.ops.bisect_plane(bm, geom=vset + edges + faces, dist=1e-5, plane_co=pl, plane_no=nl)
    cut = [g for g in res["geom_cut"] if isinstance(g, bmesh.types.BMEdge)]
    if not cut:
        return False
    sp = bmesh.ops.split_edges(bm, edges=cut)
    on_plane = []
    for e in sp["edges"]:
        if e.is_boundary and all(abs((v.co - pl).dot(nl)) < 1e-3 for v in e.verts):
            on_plane.append(e)
    if on_plane:
        bmesh.ops.holes_fill(bm, edges=on_plane, sides=64)
    return True


def edit_mesh(o, stats, portal_cuts):
    """Raise / split / trim the pieces of a straddling mesh.  Returns number of raised vertices."""
    me = o.data
    if me.users > 1:
        o.data = me = me.copy()
    M = o.matrix_world.copy()
    Minv = M.inverted()
    M3T = M.to_3x3().transposed()
    W = world_points(o)
    d, inside = signed(W)
    lab = mesh_islands(me)
    u, inv = np.unique(lab, return_inverse=True)
    n_in = np.bincount(inv, weights=inside.astype(float))
    cnt = np.bincount(inv)
    crossing = np.where((n_in > 0) & (n_in < cnt))[0]
    to_split = []
    for i in crossing:
        sel = np.where(inv == i)[0]
        dd = d[sel]; P = W[sel]
        xext = float(P[:, 0].max() - P[:, 0].min())
        if len(sel) <= 24 and dd.max() > 1.0 and dd.min() < -1.0 and xext < 30.0:
            to_split.append(sel)
    if to_split:
        bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
        nsplit = 0
        is_portal = o.name.startswith("V6 OCS | V-truss")
        for sel in to_split:
            if split_piece(bm, list(sel), Minv, M3T, W):
                nsplit += 1
                if is_portal:
                    P = W[sel]
                    portal_cuts.append((float(P[:, 0].mean()), float(P[:, 2].max())))
            bm.verts.ensure_lookup_table()
        bm.to_mesh(me); bm.free(); me.update()
        stats["split_pieces"] += nsplit
        W = world_points(o)
        d, inside = signed(W)
        lab = mesh_islands(me)
        u, inv = np.unique(lab, return_inverse=True)
        n_in = np.bincount(inv, weights=((d > -0.02) & (W[:, 1] < ye(W[:, 0]))).astype(float))
        cnt = np.bincount(inv)
    lift = np.zeros(len(W), bool)
    trim = np.zeros(len(W), bool)
    stretch = np.zeros(len(W), bool)
    is_vtruss = o.name.startswith("V6 OCS | V-truss")
    is_masts = o.name == "V6 OCS | masts"
    order = np.argsort(inv, kind="stable")
    bounds = np.concatenate([[0], np.cumsum(cnt)])
    for i in range(len(cnt)):
        idx = order[bounds[i]:bounds[i + 1]]
        dd = d[idx]
        xc = float(W[idx, 0].mean())
        near = [z0 for xs, z0, dm in TOUCH if abs(xc - xs) < 0.6]
        dlim = min([dm for xs, z0, dm in TOUCH if abs(xc - xs) < 0.6], default=0.0) - 0.08
        if near and is_vtruss and dd.min() >= dlim and n_in[i] < cnt[i]:
            lift[idx] = True                       # end plates / diagonals of a portal that starts at the line
            continue
        if near and is_masts and abs(float(dd.mean())) < 0.7 and n_in[i] < cnt[i]:
            stretch[idx] = W[idx, 2] > min(near) - 0.6      # mast on the line carries the raised portal: longer
            continue
        if n_in[i] == 0:
            continue
        if n_in[i] >= cnt[i]:
            lift[idx] = True
            continue
        xext = float(W[idx, 0].max() - W[idx, 0].min())
        if xext >= 30.0:
            trim[idx] = dd > WALL_OFF
            stats["trimmed_pieces"] += 1
            if (dd > WALL_OFF + 0.05).any():
                EAST_COPIES.append(east_copy(o, idx, W))
        else:
            stats["kept_crossing_pieces"] += 1
    lift &= W[:, 2] > ZCUT
    lift |= stretch
    stats["stretched_mast_vertices"] = stats.get("stretched_mast_vertices", 0) + int(stretch.sum())
    if not lift.any() and not trim.any():
        return 0
    Wn = W.copy()
    Wn[lift, 2] += DZ
    if trim.any():
        Wn[trim, 1] = yb(Wn[trim, 0]) + WALL_OFF
    loc = (np.array(Minv) @ np.hstack([Wn, np.ones((len(Wn), 1))]).T).T[:, :3]
    me.vertices.foreach_set("co", loc.astype(np.float32).ravel())
    me.update()
    return int(lift.sum())


TOUCH = []          # (x, beam bottom z) of portals that start at a mast standing on the line
EAST_COPIES = []    # raised copies of the parts of long strips that lay east of the step


def east_copy(o, idx, W):
    """Raised copy of the part of a long deck strip that lies east of the new side wall."""
    me = o.data
    keep = np.zeros(len(W), bool); keep[idx] = True
    P = W.copy()
    P[:, 1] = np.maximum(P[:, 1], yb(P[:, 0]) + WALL_OFF)
    P[P[:, 2] > ZCUT, 2] += DZ
    faces, mats = [], []
    for poly in me.polygons:
        vs = list(poly.vertices)
        if not keep[vs].all():
            continue
        Q = P[vs]
        a = np.zeros(3)
        for k in range(1, len(vs) - 1):
            a += np.cross(Q[k] - Q[0], Q[k + 1] - Q[0])
        if np.linalg.norm(a) < 2e-4:
            continue
        faces.append(vs); mats.append(poly.material_index)
    used = sorted({v for f in faces for v in f})
    remap = {v: i for i, v in enumerate(used)}
    return {"src": o.name, "verts": P[used], "faces": [[remap[v] for v in f] for f in faces], "mi": mats,
            "mats": [m for m in me.materials]}


def find_touch_stations():
    o = bpy.data.objects.get("V6 OCS | V-truss beams and cantilevers")
    if o is None:
        return []
    W = world_points(o)
    d, inside = signed(W)
    lab = mesh_islands(o.data)
    u, inv = np.unique(lab, return_inverse=True)
    out = []
    for i in range(len(u)):
        sel = inv == i
        dd = d[sel]
        if sel.sum() <= 24 and dd.max() > 1.0 and -0.6 < dd.min() < 0.0:
            out.append((float(W[sel, 0].mean()), float(W[sel, 2].min()), float(dd.min())))
    st = []
    for x, z, dm in sorted(out):
        if st and abs(x - st[-1][0]) < 1.0:
            st[-1] = (st[-1][0], min(st[-1][1], z), min(st[-1][2], dm))
        else:
            st.append((x, z, dm))
    return st


# ------------------------------------------------------------------------------------------------ new geometry
def side_wall(xs, mat):
    mb = L.MeshBuilder()
    xs = np.asarray(xs)
    y0 = yb(xs) + WALL_OFF
    sl = np.gradient(y0, xs)
    nrm = np.stack([-sl, np.ones_like(sl)], 1); nrm /= np.linalg.norm(nrm, axis=1)[:, None]
    ztop = SHIN_DECK + 0.10
    prof = [(0.0, WALL_Z0), (0.0, ztop), (WALL_T, ztop), (WALL_T, WALL_Z0)]          # (offset east, z)
    cop = [(-0.06, ztop), (-0.06, ztop + 0.12), (WALL_T + 0.02, ztop + 0.12), (WALL_T + 0.02, ztop)]
    for P, m in ((prof, 0), (cop, 1)):
        n = len(P)
        V = []
        for x, y, (nx, ny) in zip(xs, y0, nrm):
            for off, z in P:
                V.append((x + nx * off, y + ny * off, z))
        F = []
        for i in range(len(xs) - 1):
            a, b = i * n, (i + 1) * n
            for j in range(n):
                k = (j + 1) % n
                F.append((a + j, b + j, b + k, a + k))
        F.append(tuple(range(n - 1, -1, -1)))
        last = (len(xs) - 1) * n
        F.append(tuple(last + j for j in range(n)))
        mb.add(V, F, m)
    return mb


def portal_masts(cuts, mat_mast):
    mb = L.MeshBuilder()
    xs = []
    for x, ztop in sorted(cuts):
        if xs and abs(x - xs[-1][0]) < 1.5:
            xs[-1] = (xs[-1][0], max(xs[-1][1], ztop))
            continue
        xs.append((x, ztop))
    out = []
    for x, ztop in xs:
        y = float(yb(x))
        lo = float(ty("10", x)) + CLR[0] + MAST_R
        hi = float(ty("20", x)) - CLR[1] - MAST_R
        ok = lo <= y <= hi
        if not ok:
            REP["warnings"].append(f"portal mast at x={x:.1f}: gap {lo:.2f}..{hi:.2f} does not contain the cut y={y:.2f}")
        top = ztop + DZ + 0.15
        prof = [(MAST_R * 1.6, CONV_DECK), (MAST_R * 1.6, CONV_DECK + 0.05), (MAST_R, CONV_DECK + 0.05), (MAST_R, top),
                (MAST_R * 1.15, top), (MAST_R * 1.15, top + 0.04)]
        L.lathe(mb, prof, (x, y), segments=16, mat=0, cap_top=True, cap_bottom=True)
        out.append({"x": round(x, 2), "y": round(y, 2), "z_top": round(top + 0.04, 2), "clear": ok,
                    "gap_m": round(float(ty("20", x) - ty("10", x)), 2)})
    return mb, out


def bump_roof_property(sc):
    raw = sc.get("V5_shinkansen_roofs")
    if not raw:
        return 0
    info = json.loads(raw)
    n = 0
    for k, v in info.items():
        if not isinstance(v, dict) or k.startswith("_"):
            continue
        for kk in list(v.keys()):
            if kk.startswith("z_"):
                v[kk] = round(v[kk] + DZ, 3); n += 1
    sc["V5_shinkansen_roofs"] = json.dumps(info)
    return n


def bump_keepouts(sc):
    """V6_platform_keepouts (stairwells, signs, clocks): z values of entries on the Shinkansen side += DZ"""
    raw = sc.get("V6_platform_keepouts")
    if not raw:
        return 0
    K = json.loads(raw)
    n = 0
    for k in K:
        c = k.get("c")
        if not c:
            continue
        d, inside = signed(np.array([[c[0], c[1], 0.0]]))
        if inside[0]:
            for kk in list(k.keys()):
                if kk.startswith("z") and isinstance(k[kk], (int, float)):
                    k[kk] = round(k[kk] + DZ, 3)
            n += 1
    sc["V6_platform_keepouts"] = json.dumps(K)
    return n


# ------------------------------------------------------------------------------------------------ main
def run():
    sc = bpy.context.scene
    hid = hidden_collections()
    objs = [o for o in sc.objects if o.users_collection and not all(c.name in hid for c in o.users_collection)]
    movers, editors = [], []
    for o in objs:
        W = world_points(o)
        d, inside = signed(W)
        if not inside.any():
            continue
        above = W[:, 2] > ZCUT
        if (inside & above).all():
            movers.append(o)
        elif o.type == 'MESH' and (inside & above).any():
            editors.append(o)
    mover_set = set(movers)
    movers = [o for o in movers if not any(a in mover_set for a in ancestors(o))]
    editors = [o for o in editors if not any(a in mover_set for a in ancestors(o))]
    # meshes first (world positions of their pieces are read before anything moves)
    TOUCH.extend(find_touch_stations())
    REP["portals_starting_at_the_line"] = [round(x, 2) for x, z, dm in TOUCH]
    portal_cuts = []
    for o in editors:
        nv = edit_mesh(o, REP, portal_cuts)
        if nv:
            REP["edited_meshes"][o.name] = nv
    for o in movers:
        mw = o.matrix_world.copy()
        mw.translation.z += DZ
        o.matrix_world = mw
        REP["moved_objects"][o.type] = REP["moved_objects"].get(o.type, 0) + 1
    # side wall along the line, over the length of the raised viaducts
    via = [o for o in sc.objects if re.match(r"V3 Track (1[4-9]|2[0-3]) curved viaduct", o.name)]
    xs_all = np.concatenate([world_points(o)[:, 0] for o in via])
    x0, x1 = float(xs_all.min()), float(xs_all.max())
    xs = np.arange(x0, x1 + 1e-6, 2.0)
    if xs[-1] < x1:
        xs = np.append(xs, x1)
    col = L.collection("V8_Shinkansen_Level")
    conc = via[0].data.materials[0] if via and via[0].data.materials else L.principled("V8 | concrete", (0.55, 0.55, 0.53))
    coping = L.principled("V8 | side wall coping (pale concrete)", (0.66, 0.66, 0.63), rough=0.8)
    wall = side_wall(xs, conc).build("V8 Shinkansen level | side wall along the step", col, [conc, coping])
    wall["V8_shinkansen_level"] = True
    REP["side_wall"] = {"x": [round(x0, 1), round(x1, 1)], "length_m": round(float(np.sum(np.hypot(np.diff(xs), np.diff(yb(xs) + WALL_OFF)))), 1),
                        "z": [WALL_Z0, round(SHIN_DECK + 0.22, 2)]}
    if portal_cuts:
        mastsrc = bpy.data.objects.get("V6 OCS | masts")
        mmat = mastsrc.data.materials[0] if mastsrc and mastsrc.data.materials else L.principled("V8 | mast steel", (0.5, 0.5, 0.5), metal=0.6)
        mb, info = portal_masts(portal_cuts, mmat)
        ocs = mastsrc.users_collection[0] if mastsrc else col
        ob = mb.build("V8 OCS | masts at the level change", ocs, [mmat])
        REP["portal_masts"] = info
    for k, c in enumerate(EAST_COPIES):
        if not c["faces"]:
            continue
        ob = L.mesh_object(f"V8 Shinkansen level | deck east of the step ({c['src'][:40]})", c["verts"], c["faces"], col,
                           mats=c["mats"], face_mats=c["mi"])
        REP.setdefault("east_copies", []).append({"src": c["src"], "faces": len(c["faces"])})
    REP["roof_property_z_fields"] = bump_roof_property(sc)
    REP["keepouts_raised"] = bump_keepouts(sc)
    REP["n_movers"] = len(movers); REP["n_edited"] = len(REP["edited_meshes"])
    sc["V8_shinkansen_level"] = json.dumps({"dz_m": DZ, "line": "half-way between tracks 10 and 20",
                                            "source": "ja.wikipedia 東京駅の歴史 (rail level ~1.9 m higher); Nikkei 2023",
                                            "side_wall": REP["side_wall"], "portal_masts": REP["portal_masts"]})
    return REP


rep = run()
L.log("moved", rep["moved_objects"], "edited", rep["n_edited"], "split", rep["split_pieces"], "trimmed",
      rep["trimmed_pieces"], "kept", rep["kept_crossing_pieces"], "masts", rep["portal_masts"], "warn", rep["warnings"])
if REPORT:
    json.dump(rep, open(REPORT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
if OUT:
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=True)
    L.log("saved", OUT)
