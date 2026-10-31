"""V7 validation: commuter-car interiors and see-through windows.

usage: blender -b Tokyo_Station_V7.blend --python-exit-code 1 -P validate7_interiors.py -- report.json
Checks
  * every commuter-car instance (except the Green cars) shows an interior (collection instance contains a V7 interior)
  * every interior vertex lies inside its car body cross-section: below the roof and inside the side wall / glass,
    both measured with rays cast from outside the body at the vertex's x
  * window glass on those bodies is the see-through material and no window back plate is left behind any glass pane
  * the Green cars, E5 and N700 keep their original dark glazing
"""
import bpy, sys, json
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGV[0] if ARGV else None
GLASS = "V7 | EMU side window glass (see-through)"
res = {}
used = {}
for ob in bpy.data.objects:
    if ob.instance_type == 'COLLECTION' and ob.instance_collection and ob.name.startswith("Track"):
        used.setdefault(ob.instance_collection.name, []).append(ob.name)
missing, with_int, green = [], 0, 0
for cname, insts in used.items():
    if "E5" in cname or "N700" in cname:
        continue
    objs = list(bpy.data.collections[cname].all_objects)
    has = any(o.name.startswith("V7 interior |") for o in objs)
    if "Green" in cname:
        green += len(insts)
        continue
    if has:
        with_int += len(insts)
    else:
        missing += insts
res["instances_with_interior"] = with_int
res["green_car_instances_without_interior"] = green
res["commuter_instances_missing_interior"] = missing

dg = bpy.context.evaluated_depsgraph_get()
bodies = {}
for o in bpy.data.objects:
    if o.name.startswith("V7 interior |") and o.type == 'MESH':
        col = o.users_collection[0]
        body = next(b for b in col.all_objects if b.name.startswith("V5 one-piece body") and b.type == 'MESH')
        bodies.setdefault(o.data.name, (o, body))
contain = {}
for iname, (io, body) in bodies.items():
    assert body.matrix_world == io.matrix_world, "interior and body frames differ"
    bvh = BVHTree.FromObject(body, dg)
    names = [m.name if m else "" for m in body.data.materials]
    bad_up, bad_side, worst = 0, 0, []
    for v in io.data.vertices:
        c = v.co
        top = bvh.ray_cast(Vector((c.x, c.y, 8.0)), Vector((0, 0, -1)), 6.0)[0]
        s = 1.0 if c.y >= 0 else -1.0
        side = None
        for dx in (0.0, 0.03, -0.03):     # door seams: retry beside the gap between the two door leaves
            side = bvh.ray_cast(Vector((c.x + dx, 3.0 * s, c.z)), Vector((0, -s, 0)), 3.0)[0]
            if side is not None and abs(side.y) > 1.3:
                break
        if top is None or c.z > top.z - 0.005:
            bad_up += 1
            if len(worst) < 6:
                worst.append(("roof", tuple(round(q, 3) for q in c)))
        if side is None or abs(c.y) > abs(side.y) - 0.005:
            bad_side += 1
            if len(worst) < 12:
                worst.append(("side", tuple(round(q, 3) for q in c)))
    contain[iname] = {"verts": len(io.data.vertices), "outside_roof": bad_up, "outside_side": bad_side, "examples": worst}
res["containment"] = contain

glass = {}
for iname, (io, body) in bodies.items():
    me = body.data
    names = [m.name if m else "" for m in me.materials]
    gl = [p for p in me.polygons if names[p.material_index] == GLASS]
    left = 0
    for p in me.polygons:
        if "rubber" in names[p.material_index] and abs(p.normal.y) > 0.9:
            c = p.center
            for g in gl:
                gc = g.center
                if (gc.y > 0) == (c.y > 0) and abs(abs(gc.y) - abs(c.y)) < 0.012 and abs(gc.x - c.x) < 0.05 and abs(gc.z - c.z) < 0.05:
                    left += 1
                    break
    glass[me.name] = {"glass_faces": len(gl), "plates_left_behind_glass": left}
res["windows"] = glass
dark_kept = {}
for cname in used:
    if "Green" in cname or "E5" in cname or "N700" in cname:
        n = sum(1 for o in bpy.data.collections[cname].all_objects if o.type == 'MESH'
                for s in o.material_slots if s.material and s.material.name == GLASS)
        dark_kept[cname] = n
res["see_through_glass_on_cars_without_interior"] = {k: v for k, v in dark_kept.items() if v}
res["pass"] = (not missing and with_int > 0 and all(c["outside_roof"] == 0 and c["outside_side"] == 0 for c in contain.values())
               and all(g["glass_faces"] > 0 and g["plates_left_behind_glass"] == 0 for g in glass.values())
               and not res["see_through_glass_on_cars_without_interior"])
print("SUMMARY", json.dumps(res, ensure_ascii=False)[:3000])
if OUT:
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
