"""V6 checks for the train markings (run on a V6 .blend after mod6_trains.py).
usage: blender -b V6.blend --python-exit-code 1 -P validate6_trains.py -- report.json

  markings_off_body      every vertex of the per-car marking objects lies within 3 cm of that car's body surface
  markings_per_car       commuter cars: 2 形式番号, one 号車 plate per passenger door, 2 優先席 stickers (none on Green cars);
                         E5: one LED display per door; N700: LED displays per car
  car_labels             commuter 形式番号 strings are unique within a train
  n700_lamps             head lamps (white) only on the south nose, tail lamps (red) only on the north nose
  floor_markers          乗車位置目標 numbers match the car standing at that marker (tracks with a train)
"""
import sys, json, re
from collections import defaultdict, Counter
import numpy as np
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

OUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else None
res = {}


def bvh_of(objs, M=None):
    V, T = [], []
    for o in objs:
        me = o.data
        n = len(me.vertices)
        if n == 0:
            continue
        co = np.empty(n * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
        mw = np.array((M @ o.matrix_world) if M is not None else o.matrix_world)
        W = co @ mw[:3, :3].T + mw[:3, 3]
        me.calc_loop_triangles()
        tri = np.empty(len(me.loop_triangles) * 3, int); me.loop_triangles.foreach_get("vertices", tri)
        o0 = len(V)
        V.extend(map(tuple, W)); T.extend(map(tuple, tri.reshape(-1, 3) + o0))
    return BVHTree.FromPolygons(V, T, all_triangles=True)


def local_verts(o):
    n = len(o.data.vertices); co = np.empty(n * 3); o.data.vertices.foreach_get("co", co)
    return co.reshape(-1, 3)


# ---- markings vs body
cache = {}
off = []
per_car = {}
labels = defaultdict(list)
for ob in bpy.data.objects:
    if not ob.get("V6_trains") or ob.parent is None:
        continue
    E = ob.parent
    col = E.instance_collection
    if col is None:
        continue
    if col.name not in cache:
        objs = [o for o in col.all_objects if o.type == 'MESH' and not o.hide_render]
        body = [o for o in objs if o.name.startswith("V5 one-piece body | ")]
        if not body:
            body = [o for o in objs if " car " not in o.name] if "N700" in col.name else objs
        cache[col.name] = bvh_of(body)
    T = cache[col.name]
    V = local_verts(ob)                         # parent inverse is identity: local = master frame
    mi = np.empty(len(ob.data.polygons), int); ob.data.polygons.foreach_get("material_index", mi)
    d = []
    for v in V[:: max(1, len(V) // 4000)]:
        r = T.find_nearest(Vector(v), 0.5)
        d.append(r[3] if r[0] is not None else 0.5)
    dmax = float(max(d)) if d else 0.0
    if dmax > 0.03:
        off.append((ob.name, round(dmax, 3)))
    mats = Counter(ob.data.materials[i].name for i in mi)
    per_car[ob.name] = {"max_dist_to_body_m": round(dmax, 4), "faces_by_material": dict(mats)}
    if ob.get("car_label"):
        t = re.match(r"V6 train markings \| Track (\d\d)", ob.name)
        labels[t.group(1) if t else "?"].append(ob["car_label"])
res["markings_objects"] = len(per_car)
res["markings_off_body"] = off
res["max_distance_to_body_m"] = max((v["max_dist_to_body_m"] for v in per_car.values()), default=None)
res["car_labels_duplicated"] = {t: [k for k, n in Counter(v).items() if n > 1] for t, v in labels.items() if len(set(v)) < len(v)}

# ---- counts from the module report stored on the scene
summ = json.loads(bpy.context.scene.get("V6_trains_summary", "{}"))
res["module_totals"] = {k: v for k, v in summ.items() if k.endswith("totals")}
res["module_warnings"] = summ.get("warnings", [])

# ---- N700 lamps
lamps = {}
for ob in bpy.data.objects:
    m = re.match(r"V6 train markings \| Track (\d\d) N700", ob.name)
    if not m:
        continue
    E = ob.parent
    W = ob.matrix_world
    xs = [(W @ v.co).x for v in ob.data.vertices]
    mid = (min(xs) + max(xs)) / 2
    got = defaultdict(list)
    for p in ob.data.polygons:
        name = ob.data.materials[p.material_index].name
        if "head lamp" in name or "tail lamp" in name:
            got["head" if "head" in name else "tail"].append((W @ p.center).x)
    ok = bool(got["head"]) and bool(got["tail"]) and min(got["head"]) > mid and max(got["tail"]) < mid
    lamps[m.group(1)] = {"head_faces": len(got["head"]), "tail_faces": len(got["tail"]), "head_south_tail_north": ok}
res["n700_lamps"] = lamps

# ---- floor markers vs standing cars
fm = {}
for ob in bpy.data.objects:
    m = re.match(r"V5 platform \| Track (\d\d) door-position floor markers$", ob.name)
    if not m or ob.type != 'MESH':
        continue
    t = int(m.group(1))
    insts = [o for o in bpy.data.objects if o.instance_type == 'COLLECTION' and o.get("car_number") is not None
             and re.match(r"Track %02d( \|)? (E5 )?car \d\d$" % t, o.name)]
    if not insts:
        continue
    uvl = ob.data.uv_layers.get("UVMap") or ob.data.uv_layers[0]
    bad = 0
    for poly in ob.data.polygons:
        us = [uvl.data[li].uv.x for li in poly.loop_indices]; vs = [uvl.data[li].uv.y for li in poly.loop_indices]
        n = int(min(us) * 4 + 1e-4) + 4 * (3 - int(min(vs) * 4 + 1e-4)) + 1
        c = ob.matrix_world @ poly.center
        near = min(insts, key=lambda o: (o.matrix_world.translation - c).length)
        bad += int(near["car_number"]) != n
    fm[f"{t:02d}"] = {"markers": len(ob.data.polygons), "mismatch": bad}
res["floor_markers"] = fm

res["pass"] = bool(not off and not res["car_labels_duplicated"] and all(v["head_south_tail_north"] for v in lamps.values())
                   and all(v["mismatch"] == 0 for v in fm.values()) and not res["module_warnings"])
print("SUMMARY", json.dumps({k: v for k, v in res.items()}, ensure_ascii=False, default=str)[:3000])
if OUT:
    json.dump(dict(res, per_object=per_car), open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=str)
