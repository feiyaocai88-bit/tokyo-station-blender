"""V5 finalize: plaza pedestrians, review cameras, embedded change log / README, orphan purge, save."""
import sys, os, json, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
import v5lib as L

PKG = os.environ.get("V5_PKG_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pkg"))


def plaza_people():
    rnd = random.Random(1914)
    var_cols = [bpy.data.collections[f"V5 pedestrian {i}"] for i in range(6)]
    col = L.collection("V5_People_instances")
    dg = bpy.context.evaluated_depsgraph_get()
    sc = bpy.context.scene
    ok_words = ("pavement", "plaza", "sidewalk", "apron", "island", "walkway")
    trees = [(-30, -45), (-30, -60), (-30, -75), (-30, -90), (-30, -106), (39, -45), (39, -60), (39, -75), (39, -90), (39, -106)]
    placed = []
    zones = [((-42, 52), (-120, -36), 70), ((-150, 175), (-31, -21.5), 55), ((-150, 175), (-18.8, -15.2), 25)]
    for (x0, x1), (y0, y1), n in zones:
        k = 0
        tries = 0
        while k < n and tries < n * 60:
            tries += 1
            x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
            if any(math.hypot(x - tx, y - ty) < 2.6 for tx, ty in trees):
                continue
            if any(math.hypot(x - px, y - py) < 0.9 for px, py in placed):
                continue
            hit, loc, nrm, idx, ob, mtx = sc.ray_cast(dg, Vector((x, y, 6.0)), Vector((0, 0, -1)))
            if not hit or ob is None:
                continue
            nm = ob.name.lower()
            if not any(w in nm for w in ok_words) or nrm.z < 0.95 or loc.z > 0.6:
                continue
            rot = rnd.uniform(0, 2 * math.pi)
            e = bpy.data.objects.new(f"V5 person plaza {len(placed):03d}", None)
            e.instance_type = 'COLLECTION'
            e.instance_collection = var_cols[rnd.randrange(6)]
            e.location = loc
            e.rotation_euler = (0, 0, rot)
            col.objects.link(e)
            placed.append((x, y))
            k += 1
    return len(placed)


def add_camera(name, loc, target, lens=None, ortho=None):
    col = L.collection("V5_Review_Cameras")
    cd = bpy.data.cameras.get(name) or bpy.data.cameras.new(name)
    if ortho:
        cd.type = 'ORTHO'; cd.ortho_scale = ortho
    else:
        cd.type = 'PERSP'; cd.lens = lens or 35
    cd.clip_start = 0.1; cd.clip_end = 3000
    co = bpy.data.objects.get(name) or bpy.data.objects.new(name, cd)
    co.location = loc
    co.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    if co.name not in col.objects:
        col.objects.link(co)
    return co


def platform_centre(deck_name, x, band=3.0):
    """Centre line (y) and deck top (z) of a re-laid platform at a given x."""
    o = bpy.data.objects.get(deck_name)
    if o is None:
        return None
    ws = [o.matrix_world @ v.co for v in o.data.vertices]
    zt = max(w.z for w in ws)
    sel = [w.y for w in ws if w.z > zt - 0.05 and abs(w.x - x) < band]
    if not sel:
        return None
    return (min(sel) + max(sel)) / 2, zt


def cab_camera(col_name="E233-1000 style cab | procedural", min_y=-1e9, local_cam=(16.0, 3.0, 2.55),
               local_tgt=(9.4, 0.3, 1.85)):
    """Camera in front of the southernmost cab of a given master (found from the instance, wherever the
    re-layout put it); the camera stands on the platform east of the train."""
    col = bpy.data.collections.get(col_name)
    inst = [o for o in bpy.data.objects if o.type == 'EMPTY' and o.instance_collection == col
            and o.matrix_world.translation.y > min_y]
    if not inst:
        return None
    e = max(inst, key=lambda o: (o.matrix_world @ Vector((10.0, 0, 0))).x)
    M = e.matrix_world
    side = 1.0 if (M @ Vector((0, 1, 0)) - M.translation).y > 0 else -1.0
    return (M @ Vector((local_cam[0], side * local_cam[1], local_cam[2])),
            M @ Vector((local_tgt[0], side * local_tgt[1], local_tgt[2])))


def run():
    n_people = plaza_people()
    add_camera("V5 03 SOUTH DOME | fish-scale slate, lantern, 46.1 m spire", (150, -75, 14), (107, 0, 24), lens=40)
    add_camera("V5 04 DOME ELEVATION | heights check", (107, -120, 28), (107, 0, 28), ortho=40)
    p55 = platform_centre("V3 Platform 03-04 raised deck", 55.0) or (38.6, 6.21)
    p30 = platform_centre("V3 Platform 03-04 raised deck", 30.0) or (38.4, 6.21)
    add_camera("V5 11 PLATFORM 3-4 | signage, departure board, people", (55.0, p55[0] - 1.6, p55[1] + 1.8),
               (30.0, p30[0] + 0.6, p30[1] + 1.4), lens=26)
    cc = cab_camera()
    if cc:
        add_camera("V5 12 E233-1000 FRONT | cab detail", tuple(cc[0]), tuple(cc[1]), lens=35)
    add_camera("V5 13 TRAIN ROOFS | AC units, pantographs", (-26.0, 28.0, 34.0), (-48.0, 49.0, 6.5), lens=50)
    add_camera("V5 14 PLAZA | pedestrians and station front", (60.0, -150.0, 22.0), (10.0, -40.0, 10.0), lens=32)
    add_camera("V5 15 AERIAL | platform layout matched to GSI aerial photo", (300.0, 300.0, 230.0), (5.0, 110.0, 0.0), lens=30)
    add_camera("V5 16 CHUO LINE | elevated platform above track 3", (150.0, 75.0, 35.0), (95.0, 28.0, 11.0), lens=30)
    c235 = cab_camera("V3 E235-0 cab", min_y=47.5, local_cam=(15.0, 3.6, 2.6), local_tgt=(6.0, 0.2, 2.0))
    if c235:
        add_camera("V5 17 E235 CAB | one-piece body", tuple(c235[0]), tuple(c235[1]), lens=32)
    # E5 long nose seen from platform 20-21 (camera at eye height on the platform, ahead of the south nose)
    c5 = cab_camera("V4_Train_E5_car_01", min_y=0.0, local_cam=(19.5, 4.4, 2.85), local_tgt=(7.0, 0.0, 1.75))
    if c5:
        add_camera("V5 18 E5 NOSE | one-piece long nose, platform 20-21", tuple(c5[0]), tuple(c5[1]), lens=30)
    # V5.1 track / signalling details
    add_camera("V5 19 SIGNALS | departure signals at the north end of platforms 3-4", (-122.0, 39.5, 7.85), (-146.0, 42.0, 9.0), lens=45)
    add_camera("V5 20 TRACK DETAIL | rail profile, PC sleepers, fastenings, ballast (track 7)", (-20.0, 72.6, 7.5), (-12.0, 70.0, 5.05), lens=30)
    add_camera("V5 21 BUFFER STOPS | Tohoku Shinkansen tracks end south of platforms 20-23", (178.0, 125.5, 10.5), (200.0, 125.0, 5.6), lens=24)
    # V5.2 Shinkansen roofs
    q0 = platform_centre("V3 Platform 16-17 raised deck", -64.0) or (178.9, 6.504)
    q1 = platform_centre("V3 Platform 16-17 raised deck", 10.0) or (178.9, 6.504)
    add_camera("V5 22 SHINKANSEN ROOF | platform 16-17 under the new roof", (-64.0, q0[0] + 2.7, q0[1] + 1.65),
               (10.0, q1[0] + 1.5, q1[1] + 4.1), lens=20)
    add_camera("V5 23 SHINKANSEN ROOFS AERIAL | roofs over platforms 14-23 (compare GSI aerial)", (150.0, 330.0, 150.0),
               (-30.0, 150.0, 0.0), lens=28)
    sc = bpy.context.scene
    summaries = {}
    for k in ("V5_relayout_summary", "V5_domes_summary", "V5_dome_interior_summary", "V5_central_roof_summary",
              "V5_train_bodies_summary", "V5_trains_summary", "V5_shinkansen_roofs", "V5_platform_summary",
              "V5_trackside_summary"):
        if k in sc.keys():
            summaries[k] = json.loads(sc[k])
    summaries["plaza_people"] = n_people
    # small emissive parts (LED boards, lit displays, lamp lenses) should not be sampled as light sources:
    # they still read as lit, but Cycles no longer spends samples on thousands of tiny emitters
    n_em = 0
    for m in bpy.data.materials:
        if not m.name.startswith("V5 |") or "Shinkansen roof LED" in m.name:     # roof LED lines light the platforms
            continue
        b = m.node_tree.nodes.get("Principled BSDF") if m.node_tree else None
        if b and b.inputs["Emission Strength"].default_value > 0:
            m.cycles.emission_sampling = 'NONE'
            n_em += 1
    summaries["emissive_materials_not_light_sampled"] = n_em
    sc["V5_representation"] = ("V5 detail revision on top of V4: documented height/roofing corrections, rotunda interiors, "
                               "rolling-stock and platform detail. Interpretive diorama, not a measured survey.")
    changelog = os.path.join(PKG, "V5_Changes.json")
    readme = os.path.join(PKG, "README_CN.txt")
    os.makedirs(PKG, exist_ok=True)
    json.dump(summaries, open(changelog, "w"), ensure_ascii=False, indent=1)
    for tname, path in (("V5_CHANGELOG_JSON", changelog), ("V5_README_CN", readme)):
        if os.path.exists(path):
            t = bpy.data.texts.get(tname) or bpy.data.texts.new(tname)
            t.clear(); t.write(open(path, encoding="utf-8").read())
    sc.name = "TOKYO STATION | V5 detail revision"
    return summaries


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    bpy.ops.wm.open_mainfile(filepath=src, load_ui=False, use_scripts=False)
    info = run()
    before = len(bpy.data.objects)
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    print("[V5] objects", before, "->", len(bpy.data.objects), "plaza people", info["plaza_people"])
    bpy.ops.wm.save_as_mainfile(filepath=dst, compress=True)
    print("SAVED", dst)
