"""V6 checks for the rebuilt overhead line (run on a V6 .blend).
usage: blender -b V6.blend --python-exit-code 1 -P validate6_catenary.py -- report.json"""
import sys, os, json, re, math
import numpy as np
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[sys.argv.index("--") + 1]
D = json.load(open(os.path.join(HERE, "targets.json")))
GX = np.array(D["X"]); TGT = {k: np.array(v) for k, v in D["target"].items()}; ORDER = D["order"]
CHUO = {"01", "02"}
SHIN = {"14", "15", "16", "17", "18", "19", "20", "21", "22", "23"}
res = {}


def ty(k, x):
    return float(np.interp(x, GX, TGT[k]))


def vw(o):
    n = len(o.data.vertices); co = np.empty(n * 3); o.data.vertices.foreach_get("co", co)
    mw = np.array(o.matrix_world)
    return co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]


def islands(o):
    me = o.data; n = len(me.vertices); lab = np.arange(n)
    ev = np.empty(len(me.edges) * 2, int); me.edges.foreach_get("vertices", ev); ev = ev.reshape(-1, 2)
    for _ in range(500):
        m = np.minimum(lab[ev[:, 0]], lab[ev[:, 1]])
        old = lab.copy(); np.minimum.at(lab, ev[:, 0], m); np.minimum.at(lab, ev[:, 1], m); lab = lab[lab]
        if np.array_equal(old, lab):
            break
    return lab


# ---- contact-wire segments from the mesh (each tube = 2 rings of 6 vertices)
wo = bpy.data.objects["V6 OCS | contact wires and messengers"]
V = vw(wo)
mi = np.empty(len(wo.data.polygons), int); wo.data.polygons.foreach_get("material_index", mi)
cw_verts = set()
for p, m in zip(wo.data.polygons, mi):
    if m == 0:
        cw_verts.update(p.vertices)
lab = islands(wo)
segs = []
for l in np.unique(lab):
    idx = np.where(lab == l)[0]
    if idx[0] not in cw_verts or len(idx) != 12:
        continue
    segs.append((V[idx[:6]].mean(axis=0), V[idx[6:]].mean(axis=0)))
res["contact_wire_segments"] = len(segs)


def wire_at(x, y, z):
    best = None
    for a, b in segs:
        if not (min(a[0], b[0]) - 0.5 <= x <= max(a[0], b[0]) + 0.5):
            continue
        d = b - a; t = np.clip(((np.array([x, y, z]) - a) @ d) / (d @ d), 0, 1); q = a + d * t
        dist = math.hypot(q[0] - x, q[1] - y)
        if best is None or dist < best[0]:
            best = (dist, q)
    return best


# ---- 1. pantograph shoes against the wire
dg = bpy.context.evaluated_depsgraph_get()
shoes = []
for inst in dg.object_instances:
    ob = inst.object
    if inst.parent and inst.parent.get("V9_train"):
        continue                                    # V9 underground trains: checked against their own conductor by validate9_sobu.py
    if ob.type == 'MESH' and re.search(r"(?i)carbon_shoe|pantograph contact shoe", ob.name):
        bb = [inst.matrix_world @ Vector(c) for c in ob.bound_box]
        c = sum(bb, Vector()) / 8; zt = max(v.z for v in bb)
        w = wire_at(c.x, c.y, zt)
        shoes.append({"instance": inst.parent.name if inst.parent else ob.name, "x": round(c.x, 2),
                      "wire_plan_offset_from_shoe_centre_m": round(w[0], 3) if w else None,
                      "gap_shoe_top_to_wire_bottom_m": round(float(w[1][2]) - 0.0075 - zt, 4) if w else None})
res["pantographs"] = {"count": len(shoes),
                      "max_plan_offset_m": max(s["wire_plan_offset_from_shoe_centre_m"] for s in shoes),
                      "max_abs_gap_m": max(abs(s["gap_shoe_top_to_wire_bottom_m"]) for s in shoes),
                      "detail": shoes}

# ---- 2. wire offset from the track centre (every ~1 m along every segment)
worst = {}
for a, b in segs:
    chuo = a[2] > 15
    cand = [k for k in ORDER if (k in CHUO) == chuo]
    for t in np.linspace(0, 1, max(2, int(np.hypot(*(b - a)[:2])) + 1)):
        q = a + (b - a) * t
        k = min(cand, key=lambda kk: abs(q[1] - ty(kk, q[0])))
        worst[k] = max(worst.get(k, 0.0), abs(q[1] - ty(k, q[0])))
res["max_contact_wire_offset_from_track_centre_m"] = {k: round(v, 3) for k, v in sorted(worst.items())}

# ---- 3. wire extents vs rails
rails = {}
for o in bpy.data.objects:
    m = re.match(r"V5 track \| Track (\d\d) rails", o.name)
    if m:
        R = vw(o); rails[m.group(1)] = (float(R[:, 0].min()), float(R[:, 0].max()))
wx = {}
for a, b in segs:
    chuo = a[2] > 15
    cand = [k for k in ORDER if (k in CHUO) == chuo]
    m = 0.5 * (a + b); k = min(cand, key=lambda kk: abs(m[1] - ty(kk, m[0])))
    lo, hi = wx.get(k, (1e9, -1e9)); wx[k] = (min(lo, a[0], b[0]), max(hi, a[0], b[0]))
res["wire_vs_rail_extent"] = {k: {"wire": [round(v, 1) for v in wx[k]], "rail": [round(v, 1) for v in rails[k]],
                                  "inside": bool(wx[k][0] >= rails[k][0] - 0.01 and wx[k][1] <= rails[k][1] + 0.01)}
                              for k in sorted(wx)}

# ---- 4. masts: clearance to track centres at their level
mo = bpy.data.objects["V6 OCS | masts"]; MV = vw(mo); lab = islands(mo)
mc = []
for l in np.unique(lab):
    Pm = MV[lab == l]
    if Pm[:, 2].max() - Pm[:, 2].min() > 4.0 and (Pm[:, 0].max() - Pm[:, 0].min()) < 0.5:
        mc.append((Pm[:, 0].mean(), Pm[:, 1].mean(), Pm[:, 2].min()))
clear = []
for x, y, z in mc:
    chuo = z > 12.0
    d = min((abs(y - ty(k, x)), k) for k in ORDER
            if ((k in CHUO) == chuo) and rails[k][0] - 1 <= x <= rails[k][1] + 1)
    clear.append((round(d[0], 2), d[1], round(x, 1), round(y, 2)))
clear.sort()
res["masts"] = {"count": len(mc), "min_clearance_to_track_centre_m": clear[0][0], "closest5": clear[:5],
                "below_2.3m_conventional": [c for c in clear if c[0] < 2.30 and c[1] not in SHIN],
                "below_2.6m_shinkansen": [c for c in clear if c[0] < 2.60 and c[1] in SHIN]}

# ---- 5. contact wire against everything else (rays along every segment)
skip = re.compile(r"^V6 OCS|V5 Shinkansen roof|curved viaduct")
hits = {}
segb = np.array([[min(a[0], b[0]), max(a[0], b[0]), min(a[1], b[1]), max(a[1], b[1])] for a, b in segs])
for o in bpy.data.objects:
    if o.type != 'MESH' or not o.visible_get() or o.hide_render or skip.search(o.name):
        continue
    bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
    x0, x1 = min(v.x for v in bb), max(v.x for v in bb); y0, y1 = min(v.y for v in bb), max(v.y for v in bb)
    z0, z1 = min(v.z for v in bb), max(v.z for v in bb)
    if z1 < 10.3 or (12.0 < z0 < 20.0) or z0 > 22.5:
        continue
    sel = np.where((segb[:, 1] >= x0) & (segb[:, 0] <= x1) & (segb[:, 3] >= y0) & (segb[:, 2] <= y1))[0]
    if len(sel) == 0:
        continue
    W = vw(o); polys = [tuple(p.vertices) for p in o.data.polygons]
    if not polys:
        continue
    bvh = BVHTree.FromPolygons([Vector(v) for v in W], polys)
    for i in sel:
        a, b = segs[i]; d = Vector(b - a); Ln = d.length
        loc, n_, idx, dist = bvh.ray_cast(Vector(a), d.normalized(), Ln)
        if loc is not None:
            hits.setdefault(o.name, []).append([round(loc.x, 1), round(loc.y, 1), round(loc.z, 2)])
res["contact_wire_hits_other_geometry"] = {k: v[:3] for k, v in hits.items()}
res["contact_wire_hit_count"] = sum(len(v) for v in hits.values())

# ---- 6. car bodies against the new masts
car_hits = []
for inst in dg.object_instances:
    if not inst.is_instance or not inst.parent or not re.match(r"Track \d\d", inst.parent.name):
        continue
    ob = inst.object
    if ob.type != 'MESH' or len(ob.data.vertices) < 200:
        continue
    mw = inst.matrix_world
    bb = [mw @ Vector(c) for c in ob.bound_box]
    cx = sum(v.x for v in bb) / 8; cy = sum(v.y for v in bb) / 8
    for x, y, z in mc:
        if abs(x - cx) < 16 and abs(y - cy) < 4:
            nv = len(ob.data.vertices); co = np.empty(nv * 3); ob.data.vertices.foreach_get("co", co)
            M4 = np.array(mw); Wm = co.reshape(-1, 3)[::5] @ M4[:3, :3].T + M4[:3, 3]
            near = Wm[(Wm[:, 2] > z) & (Wm[:, 2] < z + 12)]
            if len(near) == 0:
                continue
            dmin = float(np.min(np.hypot(near[:, 0] - x, near[:, 1] - y)) - 0.175)
            if dmin < 0.05:
                car_hits.append((inst.parent.name, ob.name, round(dmin, 3)))
res["train_vs_mast_overlaps"] = car_hits

json.dump(res, open(OUT, "w"), indent=1, ensure_ascii=False)
print("SUMMARY", json.dumps({k: v for k, v in res.items() if k not in ("pantographs", "wire_vs_rail_extent", "masts")}, ensure_ascii=False)[:2500])
print("PANTO", {k: v for k, v in res["pantographs"].items() if k != "detail"})
print("MASTS", res["masts"])
print("EXTENT", {k: v for k, v in res["wire_vs_rail_extent"].items() if (not v["inside"]) or k in ("20", "21", "22", "23")})
