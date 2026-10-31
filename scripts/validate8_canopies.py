"""V8 checks for the steel-framed conventional canopies (run on a V8 .blend after mod8_canopies.py).
usage: blender -b V8.blend --python-exit-code 1 -P validate8_canopies.py -- report.json

  headroom          lowest canopy member (beams, lattice, light fittings, trays) above the platform deck, per island
                    (columns, sign fixings and the hanging signs themselves excluded); >= 3.2 m
  over_tracks       canopy parts beyond the platform edges: height above the rail top (>= 4.6 m) and distance to the
                    contact wire / messenger surfaces (>= 0.30 m)
  columns           new columns: not inside a stair enclosure, no person standing within 0.35 m of a column axis
  retired           old slabs, light strips and posts are hidden in V8_Replaced_V7_hidden and not rendered
  roof_top          highest point of the roof deck (old slab top; on 07-08 the skylight rises 0.52 m above it)
  (over-track limit 4.2 m above rail = car roof edge about 3.7 m plus 0.5 m)
"""
import sys, os, json, re
import numpy as np
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else None
D = json.load(open(os.path.join(HERE, "targets.json")))
GX = np.array(D["X"]); TGT = {k: np.array(v) for k, v in D["target"].items()}
sc = bpy.context.scene
DECK = {"01-02": 16.51, "03-04": 6.21, "05-06": 6.21, "07-08": 6.21, "09-10": 6.21}
RAIL = {"01-02": 15.47}
TOP = {"01-02": 20.75}
res = {"islands": {}}


def vw(o):
    n = len(o.data.vertices); co = np.empty(n * 3); o.data.vertices.foreach_get("co", co)
    mw = np.array(o.matrix_world)
    return co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]


def tris(o):
    V = vw(o)
    T = []
    for p in o.data.polygons:
        vs = list(p.vertices)
        for k in range(1, len(vs) - 1):
            T.append((vs[0], vs[k], vs[k + 1]))
    return V, T


wires = bpy.data.objects.get("V6 OCS | contact wires and messengers")
WV, WT = tris(wires)
wb = BVHTree.FromPolygons([tuple(v) for v in WV], WT)
keep = [k for k in json.loads(sc.get("V6_platform_keepouts", "[]")) if k.get("kind") == "stairwell"]
people = [o for o in sc.objects if o.type == 'EMPTY' and re.match(r"V\d person", o.name)]
PP = np.array([list(o.matrix_world.translation) for o in people]) if people else np.zeros((0, 3))
allpass = True
for isl, deck in DECK.items():
    a, b = isl.split("-")
    obs = [o for o in sc.objects if o.get("V8_canopy") == isl and o.type == 'MESH']
    r = {}
    rail = RAIL.get(isl, 5.17)
    lows = []
    over = []
    mind = 1e9
    for o in obs:
        if o.name.endswith("columns"):
            continue
        V = vw(o)
        # sign-fixing blocks are 0.12 x 0.12 boxes at the old underside; they sit above 10.25 anyway
        lows.append(float(V[:, 2].min()))
        ya, yb_ = np.interp(V[:, 0], GX, TGT[a]), np.interp(V[:, 0], GX, TGT[b])
        ot = (np.abs(V[:, 1] - ya) < 1.75) | (np.abs(V[:, 1] - yb_) < 1.75)
        if ot.any():
            over.append(float(V[ot, 2].min()))
            for p in V[ot]:
                hit = wb.find_nearest(Vector(p), 2.0)
                if hit[0] is not None:
                    mind = min(mind, hit[3])
    r["lowest_member_above_deck_m"] = round(min(lows) - deck, 2) if lows else None
    r["over_track_min_above_rail_m"] = round(min(over) - rail, 2) if over else None
    r["min_distance_to_wires_m"] = round(mind, 2) if mind < 1e9 else None
    # columns
    co = [o for o in obs if o.name.endswith("columns")]
    bad_k, bad_p = 0, 0
    ncol = 0
    if co:
        V = vw(co[0])
        me = co[0].data
        lab = np.arange(len(V))
        ev = np.empty(len(me.edges) * 2, int); me.edges.foreach_get("vertices", ev); ev = ev.reshape(-1, 2)
        for _ in range(500):
            m = np.minimum(lab[ev[:, 0]], lab[ev[:, 1]]); old = lab.copy()
            np.minimum.at(lab, ev[:, 0], m); np.minimum.at(lab, ev[:, 1], m); lab = lab[lab]
            if np.array_equal(old, lab):
                break
        cent = []
        for i in np.unique(lab):
            P = V[lab == i]
            if P[:, 2].min() < deck + 0.05 and P[:, 2].max() - P[:, 2].min() > 2.5 and np.ptp(P[:, 0]) > 0.3:
                cent.append(P[:, :2].mean(0))      # column shaft (lathe), not the thin down-pipe
        cent = np.array(cent)
        ncol = len(cent)
        for c in cent:
            for k in keep:
                cc = np.array(k["c"]); uu = np.array(k["u"]); vv = np.array([-uu[1], uu[0]])
                d = c - cc
                # stair enclosure footprint (mod6_platforms: opening 7.40 m + end wall 0.12 m, half width 1.92 m)
                if -0.30 <= d @ uu <= 7.62 and abs(d @ vv) <= 1.97 and k["z0"] - 1 <= deck <= k["z1"] + 1:
                    bad_k += 1
                    r.setdefault("column_in_stairwell_at", []).append([round(float(c[0]), 2), round(float(c[1]), 2), k["pos"]])
            if len(PP):
                near = (np.hypot(PP[:, 0] - c[0], PP[:, 1] - c[1]) < 0.35) & (np.abs(PP[:, 2] - deck) < 0.3)
                bad_p += int(near.sum())
                if near.any():
                    r.setdefault("person_at_column", []).append([round(float(c[0]), 2), round(float(c[1]), 2)])
    r["columns"] = ncol
    r["columns_in_stairwells"] = bad_k
    r["people_at_columns"] = bad_p
    zt = max(float(vw(o)[:, 2].max()) for o in obs if "roof deck" in o.name)
    r["roof_top_z_incl_skylight"] = round(zt, 3)
    r["pass"] = (r["lowest_member_above_deck_m"] or 0) >= 3.2 and (r["over_track_min_above_rail_m"] or 9) >= 4.2 \
        and (r["min_distance_to_wires_m"] or 9) >= 0.30 and bad_k == 0 and bad_p == 0
    allpass &= r["pass"]
    res["islands"][isl] = r
hc = bpy.data.collections.get("V8_Replaced_V7_hidden")
ret = [o for o in bpy.data.objects if o.get("V8_retired")]
res["retired"] = {"n": len(ret), "all_hidden": all(o.hide_render and hc in o.users_collection for o in ret)}
allpass &= res["retired"]["all_hidden"]
res["pass"] = allpass
print(json.dumps(res, ensure_ascii=False))
if OUT:
    json.dump(res, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
