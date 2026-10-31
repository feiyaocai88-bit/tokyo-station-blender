import sys, bpy, json, math
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=sys.argv[1], load_ui=False, use_scripts=False)
out = {}
for o in bpy.data.objects:
    if "raised deck" in o.name and o.type == 'MESH' and "Platform" in o.name and not o.get("V5_retired"):
        ws = [o.matrix_world @ v.co for v in o.data.vertices]
        ztop = max(w.z for w in ws)
        top = [w for w in ws if w.z > ztop - 0.05]
        bins = {}
        for w in top:
            b = int(math.floor(w.x / 2.0))
            lo, hi = bins.get(b, (1e9, -1e9))
            bins[b] = (min(lo, w.y), max(hi, w.y))
        xs = sorted(bins)
        sl = [(b * 2 + 1, round(bins[b][0], 2), round(bins[b][1], 2)) for b in xs]
        out[o.name] = {"ztop": round(ztop, 3), "nverts": len(ws), "slices": sl}
        print(o.name, "ztop", round(ztop,3), "x", sl[0][0], sl[-1][0], "mid", [s for s in sl if abs(s[0]) < 3])
json.dump(out, open(sys.argv[2], "w"))
# columns, signs on platforms
cols = [o for o in bpy.data.objects if "platform column" in o.name and o.type == 'MESH' and not o.get("V5_retired")]
cc = [(round((o.matrix_world.translation.x),2), round(o.matrix_world.translation.y,2)) for o in cols]
print("columns", len(cc), cc[:10])
json.dump({"columns": [[ (o.matrix_world @ Vector(c)).to_tuple(2) for c in o.bound_box] for o in cols]}, open(sys.argv[2].replace('.json','_cols.json'), "w"))
for key in ["platform canopy", "platform numbered sign", "platform strip light", "Platform_door_system"]:
    obs = [o for o in bpy.data.objects if key in o.name and o.type == 'MESH']
    for o in obs[:3]:
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        print(key, o.name, [round(min(v[i] for v in bb),2) for i in range(3)], [round(max(v[i] for v in bb),2) for i in range(3)])
