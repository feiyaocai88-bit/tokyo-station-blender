"""V6 checks for the platform stairwells, escalators and signs (run on a V6 .blend after mod6_platforms.py
and mod6_catenary.py).
usage: blender -b V6.blend --python-exit-code 1 -P validate6_platforms.py -- report.json

  openings_clear        rays down through every stair opening (platform level to the landing) hit only V6 platform
                        geometry (stairs, escalator, enclosure) or people
  v5_people_in_openings V5 people still standing inside an opening (should be 0)
  headroom              smallest clear height above the stair treads, the escalator steps and the landing (>= 2.1 m)
  ocs_in_keepouts       overhead-line vertices (masts, beams) inside a stairwell or below/through a hanging sign
  escalators            instance count (expected 3 per island) and the master collection
  images_packed         every image / font used by V6 platform objects is packed into the .blend
  retired_hidden        every V6_retired original is hidden and sits in V6_Replaced_V5_hidden
"""
import sys, os, json, re, math
import numpy as np
import bpy
from mathutils import Vector

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGV[0] if ARGV else None
sc = bpy.context.scene
dg = bpy.context.evaluated_depsgraph_get()
KEEP = json.loads(sc.get("V6_platform_keepouts", "[]"))
res = {}

# geometry constants of mod6_platforms.py
DEPTH, L_HOLE, L_TUN, W_IN = 4.00, 7.40, 13.40, 3.60
N_RISE, TREAD, U_STAIR0 = 24, 0.30, 0.30
V_STAIR, V_ESC = (-1.80, 0.25), (0.35, 1.80)
ESC_U0, ESC_SLOPE = 2.24, math.tan(math.radians(30.0))

person_objs = set()
for c in bpy.data.collections:
    if re.match(r"V5 pedestrian", c.name):
        person_objs.update(o.name for o in c.all_objects)


def ok_name(n):
    return n.startswith(("V6 platform", "V6 escalator")) or n in person_objs


def frame(k):
    ux, uy = k["u"]
    O = Vector((k["c"][0], k["c"][1], k["z1"] - 3.0))
    u = Vector((ux, uy, 0.0)); v = Vector((-uy, ux, 0.0))
    return O, u, v


def P(F, uu, vv, ww):
    O, u, v = F
    return O + u * uu + v * vv + Vector((0, 0, ww))


def hits_down(p, dist):
    """all objects along a vertical ray down from p (up to dist)"""
    out = []
    z = p.z
    for _ in range(40):
        hit, loc, nor, idx, ob, mw = sc.ray_cast(dg, Vector((p.x, p.y, z)), Vector((0, 0, -1)), distance=dist - (p.z - z))
        if not hit:
            break
        out.append((ob.name, round(p.z - loc.z, 3)))
        z = loc.z - 0.002
    return out


def first(p, d, dist, skip_people=True):
    o = Vector(p)
    for _ in range(20):
        hit, loc, nor, idx, ob, mw = sc.ray_cast(dg, o, Vector(d), distance=dist - (o - Vector(p)).length)
        if not hit:
            return None, None
        if skip_people and ob.name in person_objs:
            o = loc + Vector(d) * 0.002
            continue
        return loc, ob.name
    return None, None


wells = [k for k in KEEP if k["kind"] == "stairwell"]
res["stairwells"] = len(wells)

# ---- openings clear + headroom
bad = []
head = []
for k in wells:
    F = frame(k)
    tag = f"{k['island']} {k['pos']}"
    for uu in np.arange(0.2, L_HOLE - 0.1, 0.6):
        for vv in (-1.6, -0.8, 0.0, 0.8, 1.6):
            p = P(F, uu, vv, 2.30)
            for name, d in hits_down(p, 2.30 + DEPTH + 0.05):
                if not ok_name(name):
                    bad.append((tag, round(float(uu), 2), vv, name, d))
                    break
    # headroom: stair (v = -0.8), escalator centre, landing
    vc = (V_ESC[0] + V_ESC[1]) / 2
    for vv, lab in ((-0.8, "stair"), (vc, "escalator")):
        for uu in np.arange(0.4, L_TUN - 0.3, 0.25):
            top = P(F, uu, vv, 0.5)
            loc, nm = first(top, (0, 0, -1), DEPTH + 1.0)
            if loc is None:
                continue
            surf = loc.z
            up, nm2 = first(Vector((top.x, top.y, surf + 0.05)), (0, 0, 1), 12.0)
            h = (up.z - surf) if up is not None else 99.0
            head.append((round(h, 3), tag, lab, round(float(uu), 2), nm2))
res["openings_clear"] = {"rays_with_foreign_geometry": len(bad), "examples": bad[:12]}
head.sort()
res["headroom"] = {"min_m": head[0][0] if head else None, "lowest5": head[:5],
                   "below_2.1m": [h for h in head if h[0] < 2.1][:10]}

# ---- V5 people standing in an opening
inside = []
for o in bpy.data.objects:
    if o.instance_type != 'COLLECTION' or not o.instance_collection or not re.match(r"V5 pedestrian", o.instance_collection.name):
        continue
    if o.name.startswith("V6 person stairs") or o.hide_render:
        continue
    for k in wells:
        F = frame(k)
        p = o.matrix_world.translation
        d = p - F[0]
        du, dv = d.dot(F[1]), d.dot(F[2])
        if -0.3 <= du <= L_TUN + 0.2 and abs(dv) <= W_IN / 2 + 0.12 and abs(p.z - F[0].z) < 1.0:
            inside.append((o.name, k["island"], k["pos"], round(du, 2), round(dv, 2)))
res["v5_people_in_openings"] = inside

# ---- overhead line in the keep-outs
ocs = [o for o in bpy.data.objects if o.name.startswith("V6 OCS") and o.type == 'MESH' and not o.hide_render]
ocs_bad = []
if ocs:
    V = []
    for o in ocs:
        n = len(o.data.vertices); co = np.empty(n * 3); o.data.vertices.foreach_get("co", co)
        mw = np.array(o.matrix_world)
        W = co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]
        V.append((o.name, W))
    for k in KEEP:
        ux, uy = k["u"]; cx, cy = k["c"]
        isl_z = (k["z1"] - 3.0) if k["kind"] == "stairwell" else None
        for name, W in V:
            du = (W[:, 0] - cx) * ux + (W[:, 1] - cy) * uy
            dv = -(W[:, 0] - cx) * uy + (W[:, 1] - cy) * ux
            if k["kind"] == "stairwell":
                zlo, zhi = k["z0"], k["z1"]
            else:                       # a mast through a sign: vertices at sign height
                zlo, zhi = k["z0"], k["z0"] + 1.6
            m = (du >= k["u0"]) & (du <= k["u1"]) & (np.abs(dv) <= k["hv"]) & (W[:, 2] >= zlo) & (W[:, 2] <= zhi)
            if m.any():
                ocs_bad.append({"kind": k["kind"], "island": k["island"], "pos": k.get("pos"), "object": name,
                                "verts": int(m.sum()), "z": round(float(W[m, 2].min()), 2)})
res["ocs_in_keepouts"] = ocs_bad
res["ocs_objects_checked"] = len(ocs)

# ---- escalators
inst = [o for o in bpy.data.objects if o.name.startswith("V6 escalator ") and o.instance_type == 'COLLECTION']
master = bpy.data.collections.get("V6 escalator master")
res["escalators"] = {"instances": len(inst), "expected": 3 * len({k["island"] for k in wells}),
                     "all_use_master": all(o.instance_collection == master for o in inst),
                     "master_objects": len(master.objects) if master else 0,
                     "master_verts": sum(len(o.data.vertices) for o in master.objects if o.type == 'MESH') if master else 0,
                     "credit": master.get("credit", "")[:80] if master else ""}

# ---- packed images / fonts
v6 = [o for o in bpy.data.objects if o.type == 'MESH' and (o.name.startswith("V6 platform") or o.name.startswith("V6 escalator"))]
imgs = set()
for o in v6:
    for m in o.data.materials:
        if m and m.use_nodes:
            for n in m.node_tree.nodes:
                if n.type == 'TEX_IMAGE' and n.image:
                    imgs.add(n.image)
res["images"] = {i.name: {"packed": i.packed_file is not None, "size": list(i.size)} for i in imgs}
fonts = {}
for o in bpy.data.objects:
    if o.type == 'FONT' and not o.hide_render and o.data.font:
        f = o.data.font
        fonts.setdefault(f.name, {"packed": f.packed_file is not None or f.filepath == "<builtin>", "objects": 0})
        fonts[f.name]["objects"] += 1
res["fonts_visible_text"] = fonts
res["images_packed"] = all(v["packed"] for v in res["images"].values())

# ---- retired originals
ret = [o for o in bpy.data.objects if o.get("V6_retired")]
hc = bpy.data.collections.get("V6_Replaced_V5_hidden")
res["retired"] = {"count": len(ret),
                  "visible_in_render": [o.name for o in ret if not o.hide_render][:10],
                  "outside_hidden_collection": [o.name for o in ret if hc is None or o.name not in hc.objects][:10]}

res["pass"] = bool(not bad and not inside and not ocs_bad and head and head[0][0] >= 2.1
                   and res["escalators"]["instances"] == res["escalators"]["expected"] and res["escalators"]["all_use_master"]
                   and res["images_packed"] and not res["retired"]["visible_in_render"]
                   and not res["retired"]["outside_hidden_collection"]
                   and all(v["packed"] for f, v in fonts.items() if re.search(r"(?i)times", f)))
print("SUMMARY", json.dumps({k: v for k, v in res.items() if k not in ("images",)}, default=str)[:3000])
if OUT:
    json.dump(res, open(OUT, "w", encoding="utf-8"), indent=1, default=str, ensure_ascii=False)
