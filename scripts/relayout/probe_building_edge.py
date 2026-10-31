"""East edge of the model's Marunouchi building per 1 m of X (after the V5.2 south-wing correction).
usage: python -I probe_building_edge.py <V4_source.blend> <building_edge.json>"""
import sys, os, bpy, json, numpy as np
_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_here, ".."))                # package layout: scripts/relayout/..
sys.path.insert(0, os.path.join(_here, "..", "scripts"))     # work layout: relayout/../scripts
import south_wing as SW
bpy.ops.wm.open_mainfile(filepath=sys.argv[1], load_ui=False, use_scripts=False)
cols = ["V3 01 | Architecture and real openings", "V3 02 | Windows stonework and porticos", "V3 03 | Slate roofs and domes",
        "V4_Architecture_Atrium", "V4_Architecture_CentralPortico", "V4_Architecture_ClockCopper", "V4_Architecture_EntranceHardware",
        "V4_Architecture_WindowProfiles"]
B = {}
for cn in cols:
    c = bpy.data.collections.get(cn)
    if not c: continue
    for o in c.all_objects:
        if o.type != 'MESH' or o.hide_render: continue
        mw = np.array(o.matrix_world)
        n = len(o.data.vertices)
        if n == 0: continue
        co = np.empty(n * 3); o.data.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
        w = co @ mw[:3, :3].T + mw[:3, 3]
        bx, by = SW.bend_xy(w[:, 0], w[:, 1])
        xb = np.floor(bx).astype(int)
        for xv, yv in zip(xb, by):
            if yv > B.get(int(xv), -1e9): B[int(xv)] = float(yv)
json.dump({str(k): v for k, v in sorted(B.items())}, open(sys.argv[2], "w"))
ks = sorted(B)
print("X range", ks[0], ks[-1])
for x in range(110, ks[-1] + 1, 5):
    print(x, round(B.get(x, -99), 2))
