"""Reopen the delivered V5 file and record checks to JSON."""
import sys, json, math, hashlib, os
import bpy
from mathutils import Vector

path, out = sys.argv[1], sys.argv[2]
bpy.ops.wm.open_mainfile(filepath=path, load_ui=False, use_scripts=False)
sc = bpy.context.scene
res = {"file": os.path.basename(path), "blender": bpy.app.version_string}
res["objects_total"] = len(bpy.data.objects)
res["scene_objects"] = len(sc.objects)
inst = [o for o in sc.objects if o.instance_type == 'COLLECTION' and o.instance_collection]
res["collection_instancers"] = len(inst)
res["train_instancers"] = len([o for o in inst if not o.instance_collection.name.startswith(("V5 pedestrian", "Toyota"))])
res["people_instances"] = len([o for o in inst if o.instance_collection.name.startswith("V5 pedestrian")])
res["images"] = [(i.name, i.packed_file is not None) for i in bpy.data.images if i.users]
res["unpacked_images_in_use"] = [i.name for i in bpy.data.images if i.users and i.packed_file is None and i.source == 'FILE']
res["fonts"] = [(f.name, f.users, f.filepath) for f in bpy.data.fonts]
res["libraries"] = [l.filepath for l in bpy.data.libraries]


def zmax(name):
    o = bpy.data.objects.get(name)
    if not o:
        return None
    return round(max((o.matrix_world @ v.co).z for v in o.data.vertices), 3)


res["heights"] = {t: {"shell_top": zmax(f"V5 {t} dome curved octagonal slate shell"),
                      "lantern_and_spire_top": zmax(f"V5 {t} dome lantern orb and spire to 46.1m")} for t in ("SOUTH", "NORTH")}
res["retired_hidden"] = len(bpy.data.collections["V5_Replaced_V4_hidden"].objects)
res["retired_all_hidden_render"] = all(o.hide_render for o in bpy.data.collections["V5_Replaced_V4_hidden"].objects)
rings = [o.name for o in bpy.data.objects if o.name.endswith("| V5 hollow ring")]
res["hollow_rings"] = len(rings)
bad = []
for o in bpy.data.objects:
    if o.type == 'MESH' and o.name.startswith("V5"):
        for v in o.data.vertices:
            if any(math.isnan(c) or math.isinf(c) for c in v.co):
                bad.append(o.name); break
res["v5_meshes_with_nan"] = bad
res["v5_mesh_objects"] = len([o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith("V5")])
res["v5_new_vertices"] = sum(len(o.data.vertices) for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith("V5"))
res["train_detail_objects"] = sorted(o.name for o in bpy.data.objects if o.name.startswith("V5 detail |"))
# re-layout: platform deck centre / width at X = 0 against the GSI-derived target
here = os.path.dirname(os.path.abspath(__file__))
tj = None
for c in (os.path.join(here, "targets.json"), os.path.join(here, "..", "relayout", "targets.json")):
    if os.path.exists(c):
        tj = json.load(open(c)); break
if tj:
    pv = {}
    for isl, v in tj["islands"].items():
        o = bpy.data.objects.get(f"V3 Platform {isl} raised deck")
        if not o:
            continue
        ws = [o.matrix_world @ vv.co for vv in o.data.vertices]
        zt = max(w.z for w in ws)
        ys = [w.y for w in ws if w.z > zt - 0.05 and abs(w.x) < 4.0]
        xs = [w.x for w in ws if w.z > zt - 0.05]
        c_, w_ = (min(ys) + max(ys)) / 2, max(ys) - min(ys)
        pv[isl] = {"centre_y_at_x0": round(c_, 2), "gsi_target_centre_y": round(v["target_center0"], 2),
                   "error_m": round(c_ - v["target_center0"], 2), "width_m": round(w_, 2),
                   "gsi_target_width_m": round(v["target_width0"], 2), "deck_top_z": round(zt, 2),
                   "x_extent": [round(min(xs), 1), round(max(xs), 1)], "target_x_extent": v["P"]}
    res["platforms_vs_gsi"] = pv
    res["platform_centre_max_abs_error_m"] = max(abs(v["error_m"]) for v in pv.values()) if pv else None
res["relayout_objects"] = len([o for o in bpy.data.objects if o.get("V5_relayout")])
bodies = [o for o in bpy.data.objects if o.name.startswith("V5 one-piece body")]
res["one_piece_bodies"] = len(bodies)
res["one_piece_bodies_with_profile_normals"] = len([o for o in bodies if o.data.has_custom_normals])
# E5 long-nose end cars: nose loft must be welded to the body (no open edges along the nose root / at the tip)
import bmesh
e5n = {}
for o in bodies:
    col = o.users_collection[0] if o.users_collection else None
    if col is None or "V5_nose_x_tip" not in col.keys():
        continue
    x_tip = float(col["V5_nose_x_tip"])
    bm = bmesh.new(); bm.from_mesh(o.data)
    root = [e for e in bm.edges if e.is_boundary and all(abs(v.co.x - (x_tip - 15.0)) < 2e-3 for v in e.verts)]
    tip = [e for e in bm.edges if e.is_boundary and all(v.co.x > x_tip - 0.08 for v in e.verts)]
    xs = [v.co.x for v in bm.verts]
    e5n[col.name] = {"nose_tip_x": round(max(xs), 3), "rear_x": round(min(xs), 3), "open_edges_nose_root": len(root),
                     "open_edges_tip": len(tip), "verts": len(bm.verts)}
    bm.free()
res["e5_nose_end_cars"] = e5n


def train_clashes(min_depth=0.02):
    """Rendered train geometry vs static scene geometry (V5.1).  Each car instance gives, per 0.2 m of world X,
    the plan interval and height range of its body; static vertices plus points every 0.15 m along static edges
    that fall inside a car interval deeper than min_depth are clashes (columns, piers, platform edges...)."""
    import numpy as np, re as _re
    dg = bpy.context.evaluated_depsgraph_get()
    cars, static, names = {}, [], []
    for ins in dg.object_instances:
        ob = ins.object
        if ob.type != 'MESH' or len(ob.data.vertices) == 0:
            continue
        me = ob.data
        co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
        M = np.array(ins.matrix_world); w = co @ M[:3, :3].T + M[:3, 3]
        if ins.is_instance:
            if ins.parent is not None and _re.match(r"Track \d\d", ins.parent.name):
                cars.setdefault(ins.parent.name, []).append(w)
            continue
        o = ob.original
        if o.get("V5_retired") or o.hide_render:
            continue
        if w[:, 0].max() < -215 or w[:, 0].min() > 250 or w[:, 1].max() < 10 or w[:, 2].max() < 5.3 or w[:, 2].min() > 21:
            continue
        ne = len(me.edges)
        pts = [w]
        if ne:
            ev = np.empty(ne * 2, int); me.edges.foreach_get("vertices", ev); ev = ev.reshape(-1, 2)
            a, b = w[ev[:, 0]], w[ev[:, 1]]
            k = (np.linalg.norm(b - a, axis=1) / 0.15).astype(int)
            sel = (k > 0) & (k < 2000)
            if sel.any():
                reps = np.repeat(np.arange(sel.sum()), k[sel])
                t = np.concatenate([np.arange(1, kk + 1) / (kk + 1) for kk in k[sel]])
                pts.append(a[sel][reps] + (b[sel] - a[sel])[reps] * t[:, None])
        P = np.concatenate(pts)
        names.append(o.name)
        static.append(np.column_stack([P, np.full(len(P), len(names) - 1)]))
    if not static:
        return []
    S = np.concatenate(static); S = S[np.argsort(S[:, 0])]
    out = {}
    for car, pl in cars.items():
        P = np.concatenate(pl)
        zr = P[:, 2].min()
        body = P[(P[:, 2] > zr + 0.35) & (P[:, 2] < zr + 3.95)]
        if not len(body):
            continue
        x0 = body[:, 0].min(); nb = int((body[:, 0].max() - x0) / 0.2) + 1
        bi = ((body[:, 0] - x0) / 0.2).astype(int)
        ylo = np.full(nb, np.inf); yhi = np.full(nb, -np.inf); zlo = np.full(nb, np.inf); zhi = np.full(nb, -np.inf)
        np.minimum.at(ylo, bi, body[:, 1]); np.maximum.at(yhi, bi, body[:, 1])
        np.minimum.at(zlo, bi, body[:, 2]); np.maximum.at(zhi, bi, body[:, 2])
        i0, i1 = np.searchsorted(S[:, 0], x0), np.searchsorted(S[:, 0], body[:, 0].max())
        C = S[i0:i1]
        if not len(C):
            continue
        cb = np.clip(((C[:, 0] - x0) / 0.2).astype(int), 0, nb - 1)
        depth = np.minimum(C[:, 1] - ylo[cb], yhi[cb] - C[:, 1])
        hit = np.isfinite(ylo[cb]) & (depth > min_depth) & (C[:, 2] > zlo[cb] + 0.02) & (C[:, 2] < zhi[cb] - 0.02)
        for row, d in zip(C[hit], depth[hit]):
            key = (names[int(row[3])], car)
            r = out.setdefault(key, {"static": key[0], "car": car, "points": 0, "max_depth_m": 0.0, "x": [1e9, -1e9]})
            r["points"] += 1; r["max_depth_m"] = round(max(r["max_depth_m"], float(d)), 3)
            r["x"] = [round(min(r["x"][0], float(row[0])), 1), round(max(r["x"][1], float(row[0])), 1)]
    return sorted(out.values(), key=lambda r: -r["max_depth_m"])


def door_skew():
    """Platform-door panels (mesh islands >= 0.8 m long) vs. the target track direction at their centre:
    largest angle per track, in degrees."""
    import numpy as np, re as _re
    if not tj:
        return {}
    GX = np.array(tj["X"]); TG = {k: np.array(v) for k, v in tj["target"].items()}
    out = {}
    for o in bpy.data.objects:
        m = _re.search(r"Platform_door_system_track_(\d\d)$", o.name)
        if not m or o.type != 'MESH' or o.get("V5_retired") or m.group(1) not in TG:
            continue
        k = m.group(1); me = o.data
        co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
        M = np.array(o.matrix_world); W = co @ M[:3, :3].T + M[:3, 3]
        lab = np.arange(len(W))
        ev = np.empty(len(me.edges) * 2, int); me.edges.foreach_get("vertices", ev); ev = ev.reshape(-1, 2)
        for _ in range(1000):
            la, lb = lab[ev[:, 0]], lab[ev[:, 1]]
            if not np.any(la != lb):
                break
            mm = np.minimum(la, lb); np.minimum.at(lab, ev[:, 0], mm); np.minimum.at(lab, ev[:, 1], mm)
            for _ in range(4):
                lab = lab[lab]
        worst = 0.0
        for u in np.unique(lab):
            P = W[lab == u]
            if len(P) < 8 or np.ptp(P[:, 0]) < 0.8:
                continue
            xy = P[:, :2] - P[:, :2].mean(0)
            d = np.linalg.eigh(xy.T @ xy)[1][:, -1]
            a = math.degrees(math.atan2(d[1], d[0]))
            a = (a + 90) % 180 - 90
            xc = P[:, 0].mean()
            t = math.degrees(math.atan2(np.interp(xc + 2, GX, TG[k]) - np.interp(xc - 2, GX, TG[k]), 4.0))
            worst = max(worst, abs(a - t))
        out[k] = round(worst, 2)
    return out


def shinkansen_roofs():
    """V5.2: the new Shinkansen roofs - extents, and static geometry that reaches into a roof: inside its plan
    footprint and either above the roof's underside there (deck soffit, or the monitor roof over the open monitor)
    or inside a transverse girder (girder underside up to the soffit, within 0.2 m of a girder line).  Hanger rods
    that end on the underside are not counted.  Both lists should be empty."""
    import numpy as np, re as _re, sys as _sys
    raw = sc.get("V5_shinkansen_roofs")
    if not raw or not tj:
        return None
    info = json.loads(raw)
    GX = np.array(tj["X"]); TG = {k: np.array(v) for k, v in tj["target"].items()}
    sec = info.get("_section", {})
    over = sec.get("over_track_m", 1.1)
    eave, mbase, mtop, mhalf, gcl = (sec.get("eave_m", 8.0), sec.get("monitor_base_m", 8.4), sec.get("monitor_top_m", 9.2),
                                     sec.get("monitor_half_m", 2.9), sec.get("girder_clear_m", 7.25))
    roofs = {k: v for k, v in info.items() if not k.startswith("_")}
    hits, ghits = {}, {}
    dg = bpy.context.evaluated_depsgraph_get()
    for ins in dg.object_instances:
        ob = ins.object
        if ob.type != 'MESH' or len(ob.data.vertices) == 0:
            continue
        o = ob.original
        if o.get("V5_retired") or o.hide_render or o.name.startswith("V5 Shinkansen roof"):
            continue
        me = ob.data
        co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
        M = np.array(ins.matrix_world); w = co @ M[:3, :3].T + M[:3, 3]
        if w[:, 2].max() < 13.0 or w[:, 1].max() < 95 or w[:, 1].min() > 215:
            continue
        for isl, v in roofs.items():
            x0, x1 = v["x_extent"]
            sel = (w[:, 0] >= x0) & (w[:, 0] <= x1) & (w[:, 2] > v["z_girder_underside"] - 0.02)
            if not sel.any():
                continue
            wt, et = tj["islands"][isl]["west"], tj["islands"][isl]["east"]
            P = w[sel]
            ywt = np.interp(P[:, 0], GX, TG[wt]); yet = np.interp(P[:, 0], GX, TG[et])
            inn = (P[:, 1] > ywt - over) & (P[:, 1] < yet + over)
            if not inn.any():
                continue
            P, ywt, yet = P[inn], ywt[inn], yet[inn]
            c = (ywt + yet) / 2; d = P[:, 1] - c
            dw = -(c - ywt + over); de = yet - c + over
            t = np.where(d < 0, (d - dw) / (-mhalf - dw), (de - d) / (de - mhalf))
            soffit = eave + (mbase - eave) * np.clip(t, 0, 1) - 0.15
            under = np.where(np.abs(d) < mhalf, mtop - 0.16, soffit) + v["z_deck"]
            n1 = int((P[:, 2] > under + 0.05).sum())
            colx = np.array([cc[0] for cc in v["columns"]])
            near = np.min(np.abs(P[:, 0][:, None] - colx[None, :]), axis=1) < 0.2 if len(colx) else np.zeros(len(P), bool)
            n2 = int((near & (P[:, 2] < soffit + v["z_deck"] - 0.02)).sum())
            base = _re.sub(r"[.][0-9]+$", "", o.name) + " | roof " + isl
            if n1:
                hits[base] = hits.get(base, 0) + n1
            if n2:
                ghits[base] = ghits.get(base, 0) + n2
    return {"roofs": {k: {kk: v[kk] for kk in ("x_extent", "width_m", "z_girder_underside", "z_eave", "colour")}
                      for k, v in roofs.items()},
            "columns": sum(len(v["columns"]) for v in roofs.values()),
            "static_geometry_through_roof_deck": hits, "static_geometry_in_girders": ghits}


def bogie_offsets():
    """Plan distance of each car's two bogie centres (mean of each axle pair of its master collection) from the
    target centreline of its track, over all single-car instances (4 axles).  The N700 formations are instanced as
    whole bent formations (V3 shells, many axles) and are only counted."""
    import numpy as np, re as _re
    if not tj:
        return None
    GX = np.array(tj["X"]); TG = {k: np.array(v) for k, v in tj["target"].items()}
    cache, worst, n, skipped = {}, 0.0, 0, 0
    for o in bpy.data.objects:
        m = _re.match(r"Track (\d\d) ", o.name)
        col = o.instance_collection
        if not m or o.type != 'EMPTY' or col is None or m.group(1) not in TG:
            continue
        if col.name not in cache:
            xs = sorted(sum((ob.matrix_basis @ Vector(c)).x for c in ob.bound_box) / 8
                        for ob in col.all_objects if "axle shaft" in ob.name and not ob.get("V5_retired"))
            cache[col.name] = ((xs[0] + xs[1]) / 2, (xs[-2] + xs[-1]) / 2) if len(xs) == 4 else None
        b = cache[col.name]
        if b is None:
            skipped += 1
            continue
        for bx in b:
            p = o.matrix_world @ Vector((bx, 0.0, 0.0))
            worst = max(worst, abs(p.y - float(np.interp(p.x, GX, TG[m.group(1)]))))
        n += 1
    return {"single_cars_checked": n, "max_offset_m": round(worst, 3), "formation_instances_not_checked": skipped}


res["train_bogie_offsets"] = bogie_offsets()
res["shinkansen_roofs"] = shinkansen_roofs()
res["platform_door_max_skew_vs_track_deg"] = door_skew()
cl = train_clashes()
res["train_vs_static_clashes_deeper_than_2cm"] = len(cl)
res["train_vs_static_clash_list"] = cl[:20]
res["cameras"] = sorted(o.name for o in sc.objects if o.type == 'CAMERA')
res["default_camera"] = sc.camera.name if sc.camera else None
res["render"] = {"engine": sc.render.engine, "res": [sc.render.resolution_x, sc.render.resolution_y], "samples": sc.cycles.samples}
h = hashlib.sha256(open(path, "rb").read()).hexdigest()
res["sha256"] = h
json.dump(res, open(out, "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in res.items() if k not in ("images", "train_detail_objects", "cameras")}, ensure_ascii=False))
