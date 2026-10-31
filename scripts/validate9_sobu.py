"""Validate the V9 Sobu underground station.

Checks (all in the station frame; every V9 station mesh has matrix_world = station frame):
  1  vehicle envelope: rays along each track at |dy| <= 1.55 m, rail+0.25 .. rail+4.0 m, and at the centre up to the
     raised pantograph (|dy| <= 0.75 m, up to rail+5.40) hit nothing except the track and conductor objects
  2  fixed structure (columns, walls, signals) >= 1.9 m from the track centres between rail+1.3 and rail+4.0
  3  trains: 2 x 15 cars on tracks 1 and 4, origins on the rail top, raised pantograph shoes touch the contact wire
     (|gap| <= 0.02 m, wire within 0.30 m of the shoe centre)
  4  headroom >= 2.10 m over every stair and escalator (B5->B4 groups, B4->B1 banks)
  5  people stand on a floor and are not inside geometry
  6  everything of V9 above the studio floor (z > -4.2) lies inside the display plinth; nothing above z = -0.40
  7  clearance to the station building's west face (model Y = -12.3) and placement vs OpenStreetMap
  8  review cameras are not inside geometry and see at least 1.5 m ahead
usage: blender -b Tokyo_Station_V9.blend --python-exit-code 1 -P validate9_sobu.py -- report.json
"""
import sys, os, json, math
import numpy as np
import bpy
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v9geo as G

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
REPORT = ARGV[0] if ARGV else None
FR = G.frame_matrix(); FRI = FR.inverted()
R = {"checks": {}, "failures": []}


def fail(msg):
    R["failures"].append(msg)


def mesh_local(o):
    """Vertices / polygons of a station object in station-local coordinates."""
    me = o.data
    n = len(me.vertices)
    co = np.empty(n * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    M = np.array(FRI @ o.matrix_world)
    co = co @ M[:3, :3].T + M[:3, 3]
    return co, [tuple(p.vertices) for p in me.polygons]


STATION = [o for o in bpy.data.objects if o.get("V9_sobu") and o.type == 'MESH']
TREES = {}
VERTS = {}
for o in STATION:
    co, polys = mesh_local(o)
    VERTS[o.name] = co
    TREES[o.name] = BVHTree.FromPolygons([tuple(v) for v in co], polys, all_triangles=False, epsilon=0.0)
R["station_objects"] = len(STATION)
TRACKISH = [n for n in TREES if "tracks 1-4" in n or "conductor" in n]


def cast(o, d, dist, skip=()):
    best = None
    for n, t in TREES.items():
        if n in skip:
            continue
        h = t.ray_cast(Vector(o), Vector(d), dist)
        if h[0] is not None and (best is None or h[3] < best[1]):
            best = (n, h[3], h[1])
    return best


# 1 + 2 ------------------------------------------------------------ envelopes along the tracks
def envelope():
    x0, x1 = G.BOX_X[0] - G.END_T - 29.0, G.BOX_X[1] + G.END_T + 29.0
    hits = []
    worst = {}
    for t, yt in G.TRK.items():
        rays = [(dy, G.RAIL + dz) for dy in (-1.55, -1.0, 0.0, 1.0, 1.55) for dz in (0.25, 1.2, 2.5, 3.9)]
        rays += [(dy, G.RAIL + dz) for dy in (-0.75, 0.0, 0.75) for dz in (4.3, 4.9, 5.38)]
        for dy, z in rays:
            h = cast((x0, yt + dy, z), (1, 0, 0), x1 - x0, TRACKISH)
            if h:
                hits.append({"track": t, "dy": dy, "z_above_rail": round(z - G.RAIL, 2), "object": h[0], "x": round(x0 + h[1], 2)})
        gauge = []
        for dy in (-1.9, 1.9):
            for dz in (1.3, 2.0, 3.0, 4.0):
                h = cast((x0, yt + dy, G.RAIL + dz), (1, 0, 0), x1 - x0, TRACKISH)
                if h and "platforms" not in h[0] and "ceilings" not in h[0]:
                    gauge.append({"dy": dy, "z_above_rail": dz, "object": h[0], "x": round(x0 + h[1], 2)})
        # nearest fixed structure across the track (lateral rays every 3.5 m)
        dmin = 99.0
        for x in np.arange(-170.0, 170.1, 1.75):
            for dz in (1.3, 2.0, 3.0, 4.0):
                for sg in (-1, 1):
                    h = cast((x, yt, G.RAIL + dz), (0, sg, 0), 6.0, TRACKISH)
                    if h and "platforms" not in h[0] and "ceilings" not in h[0]:
                        dmin = min(dmin, h[1])
        worst[t] = {"min_lateral_clearance_m": round(dmin, 3), "gauge_hits": gauge[:5]}
        if gauge:
            fail(f"track {t}: {len(gauge)} construction-gauge hits, e.g. {gauge[0]}")
        if dmin < 1.9:
            fail(f"track {t}: fixed structure only {dmin:.2f} m from the track centre")
    R["checks"]["envelope"] = {"hits": hits[:10], "n_hits": len(hits), "per_track": worst}
    if hits:
        fail(f"vehicle envelope: {len(hits)} ray hits, first {hits[0]}")


# 3 ---------------------------------------------------------------- trains and pantographs
def trains():
    cars = [o for o in bpy.data.objects if o.get("V9_train")]
    out = {"cars": len(cars), "per_track": {}}
    if len(cars) != 30:
        fail(f"expected 30 cars, found {len(cars)}")
    for o in cars:
        p = FRI @ o.matrix_world.translation
        trk = int(str(o["track"]).split("-")[1])
        if abs(p.z - G.RAIL) > 0.005 or abs(p.y - G.TRK[trk]) > 0.005:
            fail(f"{o.name}: not on the rail ({p.y:.3f}, {p.z:.3f})")
        if min(abs(p.x - x) for x in G.CAR_X) > 0.01:
            fail(f"{o.name}: x {p.x:.2f} not on the car pitch")
        out["per_track"].setdefault(trk, []).append(o["car_number"])
    for trk in out["per_track"]:
        out["per_track"][trk] = sorted(out["per_track"][trk])
        if out["per_track"][trk] != list(range(1, 16)):
            fail(f"track {trk}: car numbers {out['per_track'][trk]}")
    heads = {o["track"]: o["car_number"] for o in cars if o.get("V5_head") == 1.0}
    tails = {o["track"]: o["car_number"] for o in cars if o.get("V5_tail") == 1.0}
    out["heads"] = heads; out["tails"] = tails
    if heads != {"B5-1": 1, "B5-4": 15} or tails != {"B5-1": 15, "B5-4": 1}:
        fail(f"head / tail lamps wrong: {heads} {tails}")
    # pantograph shoes
    gaps = []
    for o in cars:
        col = o.instance_collection
        for ob in col.all_objects:
            if ob.type == 'MESH' and "contact_carbon_shoe" in ob.name:
                M = FRI @ o.matrix_world @ ob.matrix_world
                co = np.array([tuple(M @ v.co) for v in ob.data.vertices])
                top = co[:, 2].max(); cy = co[:, 1].mean(); cx = co[:, 0].mean()
                trk = int(str(o["track"]).split("-")[1])
                stagger = 0.15 * math.sin(2 * math.pi * cx / 80.0 + trk)
                gap = G.WIRE_BOTTOM - top
                off = abs(G.TRK[trk] + stagger - cy)
                gaps.append({"car": o.name[:28], "gap_m": round(gap, 4), "wire_offset_m": round(off, 3)})
                if abs(gap) > 0.02 or off > 0.30:
                    fail(f"{o.name}: pantograph gap {gap:.3f} m, wire offset {off:.2f} m")
    out["pantographs"] = gaps
    if len(gaps) != 8:
        fail(f"expected 8 raised pantographs, found {len(gaps)}")
    R["checks"]["trains"] = out


# 4 ---------------------------------------------------------------- headroom over stairs and escalators
def headroom():
    import importlib.util
    res = {"groups_min": 99.0, "banks_min": 99.0, "worst": None}
    TAN = math.tan(math.radians(30))

    def esc(u, z0, rise, us=0.3):
        ua = us + 2.4; run = rise / TAN
        return z0 if u <= ua else (z0 + rise if u >= ua + run else z0 + (u - ua) * TAN)

    def stair_pts(z0, rise, u0, tread, flights, landing):
        n = sum(flights); h = rise / n; pts = [(u0, z0)]; u, z = u0, z0
        for fi, k in enumerate(flights):
            for i in range(k):
                z += h; pts.append((u, z))
                if i < k - 1:
                    u += tread; pts.append((u, z))
            if fi < len(flights) - 1:
                u += landing; pts.append((u, z))
        return pts

    def nose(pts, u):
        z = pts[0][1]
        for (ua, za), (ub, zb) in zip(pts[:-1], pts[1:]):
            if ua <= u:
                z = max(z, zb if abs(ua - ub) < 1e-9 else za)
        return z
    def up_from_surface(x, y, z_est):
        """Find the walking surface below z_est + 0.6 (step tops lie up to ~0.25 m above the nose line), then measure up."""
        d = cast((x, y, z_est + 0.6), (0, 0, -1), 1.5)
        zs = z_est + 0.6 - d[1] if d else z_est
        h = cast((x, y, zs + 0.01), (0, 0, 1), 8.0)
        return (h[1] + 0.01 if h else 9.0), h
    gp = stair_pts(G.DECK, G.STAIR_RISE, 1.6, 0.30, (19, 19), 1.8)
    for isl in G.ISL:
        for gx in G.GROUP_X:
            xf, s, yc = G.group_frame(gx, isl)
            for w, kind in ((0.7, "stair"), (-1.255, "escalator")):
                for u in np.arange(0.4, 15.4, 0.1):
                    z = nose(gp, u) if kind == "stair" and u >= 1.6 else (esc(u, G.DECK, G.STAIR_RISE) if kind == "escalator" else G.DECK)
                    hr, h = up_from_surface(xf + s * u, yc + s * w, z)
                    if hr < res["groups_min"]:
                        res["groups_min"] = hr; res["worst_group"] = {"group": f"{isl} @ {gx}", "lane": kind, "u": round(u, 2), "hit": h[0] if h else None}
    bp = stair_pts(G.B4_FLOOR, G.B1_FLOOR - G.B4_FLOOR, 0.6, 0.29, (19, 19, 19, 20), 1.5)
    for bk, (xf, s) in G.BANKS.items():
        for w, kind in ((-2.0, "escalator"), (-0.56, "escalator"), (1.45, "stair")):
            for u in np.arange(-0.5, G.BANK_LEN - 0.5, 0.1):
                z = nose(bp, u) if kind == "stair" and u >= 0.6 else (esc(u, G.B4_FLOOR, G.B1_FLOOR - G.B4_FLOOR) if kind == "escalator" else G.B4_FLOOR)
                hr, h = up_from_surface(xf + s * u, s * w, z)
                if hr < res["banks_min"]:
                    res["banks_min"] = hr; res["worst_bank"] = {"bank": bk, "lane": kind, "w": w, "u": round(u, 2), "hit": h[0] if h else None}
    res["groups_min"] = round(res["groups_min"], 3); res["banks_min"] = round(res["banks_min"], 3)
    R["checks"]["headroom"] = res
    if res["groups_min"] < 2.10:
        fail(f"B5-B4 stair / escalator headroom {res['groups_min']:.2f} m ({res.get('worst_group')})")
    if res["banks_min"] < 2.10:
        fail(f"B4-B1 bank headroom {res['banks_min']:.2f} m ({res.get('worst_bank')})")


# 5 ---------------------------------------------------------------- people
def people():
    ps = [o for o in bpy.data.objects if o.get("V9_person")]
    bad = []
    for o in ps:
        p = FRI @ o.matrix_world.translation
        h = cast((p.x, p.y, p.z + 0.5), (0, 0, -1), 1.0)
        if not h or abs(h[1] - 0.5) > 0.03:
            bad.append((o.name, "no floor", round(h[1], 3) if h else None)); continue
        for dz in (0.3, 0.9, 1.5):
            near = min(((n, t.find_nearest(Vector((p.x, p.y, p.z + dz)), 0.25)) for n, t in TREES.items()),
                       key=lambda r: r[1][3] if r[1][0] is not None else 9e9)
            if near[1][0] is not None and near[1][3] < 0.2:
                bad.append((o.name, "touches " + near[0][:40], round(near[1][3], 3), [round(p.x, 2), round(p.y, 2)])); break
    R["checks"]["people"] = {"count": len(ps), "bad": bad[:10], "n_bad": len(bad)}
    if bad:
        fail(f"people: {len(bad)} badly placed, e.g. {bad[0]}")


# 6 + 7 ------------------------------------------------------------ plinth, building, OSM
def placement():
    px0, px1, py0, py1 = G.PLINTH
    out_pl = 0; zmax = -99.0; ymax = -999.0; n = 0
    for o in STATION:
        co = VERTS[o.name]
        W = np.c_[co[:, 0], co[:, 1], np.zeros(len(co))]
        X, Y, _ = G.to_world(co[:, 0], co[:, 1])
        up = co[:, 2] > G.STUDIO_FLOOR
        bad = up & ~((X > px0 + 0.3) & (X < px1 - 0.3) & (Y > py0 + 0.3) & (Y < py1 - 0.3))
        out_pl += int(bad.sum())
        zmax = max(zmax, float(co[:, 2].max()))
        if "context" not in o.name:
            ymax = max(ymax, float(Y.max()))
        n += len(co)
    R["checks"]["plinth"] = {"vertices": n, "above_studio_floor_outside_plinth": out_pl, "max_z": round(zmax, 3)}
    if out_pl:
        fail(f"{out_pl} V9 vertices above the studio floor lie outside the display plinth")
    if zmax > -0.40:
        fail(f"V9 geometry reaches z = {zmax:.2f} (above the site ground underside)")
    # west face of the station building: per 5 m band of model X, the smallest Y of the large, tall objects
    bands = {}
    for o in bpy.context.scene.objects:
        if o.type != 'MESH' or o.get("V9_sobu") or o.hide_render:
            continue
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        xs = [v.x for v in bb]; ys = [v.y for v in bb]; zs = [v.z for v in bb]
        if max(zs) - min(zs) < 8.0 or max(xs) - min(xs) < 20.0 or min(zs) > 3.0 or min(ys) < -40.0 or min(zs) < -1.0:
            continue
        for k in range(int(math.floor(min(xs) / 5.0)), int(math.floor(max(xs) / 5.0)) + 1):
            bands[k] = min(bands.get(k, 99.0), min(ys))
    clr = 99.0; where = None
    for o in STATION:
        if "context" in o.name:
            continue
        co = VERTS[o.name]
        X, Y, _ = G.to_world(co[:, 0], co[:, 1])
        k = np.floor(X / 5.0).astype(int)
        for kk in np.unique(k):
            if int(kk) in bands:
                m = k == kk
                c = bands[int(kk)] - float(Y[m].max())
                if c < clr:
                    clr = c; where = {"object": o.name[:50], "model_X_band": [int(kk) * 5, int(kk) * 5 + 5], "building_west_Y": round(bands[int(kk)], 2)}
    R["checks"]["building"] = {"min_clearance_to_building_m": round(clr, 2), "where": where, "bands": len(bands)}
    if clr < 3.0:
        fail(f"station only {clr:.2f} m from the station building ({where})")
    # OSM: island axis direction and the designed westward shift
    osm_mid = (np.array(G.NE_OSM) + np.array(G.SW_OSM)) / 2
    lx, ly = G.to_local(*osm_mid)
    R["checks"]["osm"] = {"osm_island_midpoint_local": [round(float(lx), 2), round(float(ly), 2)],
                          "designed_shift_west_m": G.SHIFT_W, "platform_length_m": G.PLAT_X[1] - G.PLAT_X[0],
                          "osm_island_length_m": round(float(np.linalg.norm(np.array(G.NE_OSM) - np.array(G.SW_OSM))), 1)}
    if abs(lx) > 1.0 or abs(ly + G.SHIFT_W) > 0.5:
        fail("frame does not match the OSM midline + shift")
    # vent tower over the shaft
    vl = G.to_local(*G.VENT_XY_MODEL)
    R["checks"]["vent_shaft_local"] = [round(float(vl[0]), 2), round(float(vl[1]), 2)]
    if not (G.UPPER_X[0] < vl[0] < G.UPPER_X[1] and abs(vl[1]) < G.WALL_IN - G.VENT_HALF):
        fail("ventilation tower not over the upper box")


# 8 ---------------------------------------------------------------- cameras
def cameras():
    out = []
    for name, cp, ct, lens in G.REVIEW_CAMS:
        o = bpy.data.objects.get(name)
        if o is None:
            fail(f"camera missing: {name}"); continue
        p = FRI @ o.matrix_world.translation
        d = (FRI.to_3x3() @ (o.matrix_world.to_3x3() @ Vector((0, 0, -1)))).normalized()
        near = min((t.find_nearest(p, 1.0) for t in TREES.values()), key=lambda r: r[3] if r[0] is not None else 9e9)
        ahead = cast(tuple(p), tuple(d), 500.0)
        inside = 0
        for v in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            h = cast(tuple(p), v, 400.0)
            if h and Vector(h[2]).dot(Vector(v)) > 0:
                inside += 1
        rec = {"camera": name[:40], "nearest_m": round(near[3], 3) if near[0] is not None else None,
               "first_hit_ahead_m": round(ahead[1], 2) if ahead else None, "backface_hits": inside}
        out.append(rec)
        if "CUTAWAY" in name:
            continue
        if (near[0] is not None and near[3] < 0.15) or inside >= 4 or (ahead and ahead[1] < 1.5):
            fail(f"camera {name[:30]}: {rec}")
    R["checks"]["cameras"] = out


for fn in (envelope, trains, headroom, people, placement, cameras):
    try:
        fn()
    except Exception as e:                          # report and keep going
        import traceback
        fail(f"{fn.__name__} crashed: {e!r}")
        traceback.print_exc()
R["ok"] = not R["failures"]
print("[V9 validate]", "OK" if R["ok"] else "FAIL", json.dumps(R["failures"][:8], ensure_ascii=False), flush=True)
if REPORT:
    json.dump(R, open(REPORT, "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=str)
if not R["ok"]:
    sys.exit(1)
