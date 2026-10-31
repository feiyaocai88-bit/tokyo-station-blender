import sys, bpy, json, math, re
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=sys.argv[1], load_ui=False, use_scripts=False)
out = {"tracks": {}, "platforms": {}, "building": [], "canopies": {}}
for o in bpy.data.objects:
    m = re.match(r"V3 Track (\d\d) curved sleeper bed", o.name)
    if m and o.type == 'MESH':
        ws = [o.matrix_world @ v.co for v in o.data.vertices]
        bins = {}
        for w in ws:
            b = int(math.floor(w.x / 2.0))
            bins.setdefault(b, []).append(w.y)
        pts = [(b * 2 + 1, (min(v) + max(v)) / 2) for b, v in sorted(bins.items())]
        out["tracks"][m.group(1)] = pts
    m = re.match(r"V3 Platform (\d\d)-(\d\d) raised deck", o.name)
    if m and o.type == 'MESH':
        ws = [o.matrix_world @ v.co for v in o.data.vertices]
        zt = max(w.z for w in ws)
        bins = {}
        for w in ws:
            if w.z > zt - 0.05:
                b = int(math.floor(w.x / 2.0))
                lo, hi = bins.get(b, (1e9, -1e9)); bins[b] = (min(lo, w.y), max(hi, w.y))
        out["platforms"][m.group(1) + "-" + m.group(2)] = [(b * 2 + 1, lo, hi) for b, (lo, hi) in sorted(bins.items())]
    m = re.match(r"V3 platform canopy (\d\d)-(\d\d)", o.name)
    if m and o.type == 'MESH':
        ws = [o.matrix_world @ v.co for v in o.data.vertices]
        bins = {}
        for w in ws:
            b = int(math.floor(w.x / 4.0))
            lo, hi = bins.get(b, (1e9, -1e9)); bins[b] = (min(lo, w.y), max(hi, w.y))
        out["canopies"].setdefault(m.group(1) + "-" + m.group(2), []).extend([(b * 4 + 2, lo, hi) for b, (lo, hi) in sorted(bins.items())])
o = bpy.data.objects.get("V3 OSM projected outline | community reference")
if o:
    sp = o.data.splines[0]
    out["building_osm"] = [((o.matrix_world @ p.co.xyz).x, (o.matrix_world @ p.co.xyz).y) for p in sp.points]
json.dump(out, open(sys.argv[2], "w"))
print("tracks", len(out["tracks"]), "platforms", len(out["platforms"]), "canopies", len(out["canopies"]))
