"""V9 module 2: two 15-car E235-1000 style Yokosuka / Sobu Rapid trains at the B5 platforms, and people.

Trains (approximation, see README): the model's E235-0 (Yamanote) cab and intermediate cars are copied into new
template collections and re-liveried:
  * the Yamanote-green faces become stainless door leaves (sides) or Yokosuka blue (front wrap of the cab)
  * the stainless body gets the Yokosuka belt (blue with a cream line above, under the windows) in the shader
  * the destination / run-number LEDs show 横須賀線 普通 久里浜 (V5_dest 0) or 総武線快速 千葉 (V5_dest 1)
  * cars 3, 7, 9, 13 get a raised single-arm pantograph copied from the model's E233 pantograph car
  * Green cars 4 and 5 use the model's E233-3000 double-deck Green cars with blue / cream instead of orange / green
Formation (car 1 at the Kurihama / -x end): 1 cab, 2, 3P, 4G, 5G, 6, 7P, 8, 9P, 10, 11 cab | 12 cab, 13P, 14, 15 cab.
Track 1: Yokosuka Line train towards Shinagawa / Kurihama (head at car 1); track 4: Sobu Rapid train towards Chiba
(head at car 15).  Tracks 2 and 3 stay empty so the platforms and the track zone can be seen.
People: instances of the model's own "V5 pedestrian N" collections on the B5 platforms and in the B4 / B1 concourses.

usage: blender -b in.blend --python-exit-code 1 -P mod9_trains_people.py -- out.blend report.json
"""
import sys, os, json, math
import numpy as np
import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v5lib as L
import v9geo as G

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGV[0] if ARGV else None
REPORT = ARGV[1] if len(ARGV) > 1 else None
TEX = os.path.join(HERE, "textures")
FR = G.frame_matrix()
REP = {"templates": {}, "cars": [], "people": {}, "warnings": []}
BLUE = (0.010, 0.040, 0.32)
CREAM = (0.83, 0.71, 0.39)
BELT = {"blue": (1.88, 2.04), "cream": (2.04, 2.12)}      # rail-relative heights (collection space)
RNG = np.random.default_rng(19)


# ---------------------------------------------------------------- materials
def paint(name, col, rough=0.32):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*col, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Coat Weight"].default_value = 0.3
    m.diffuse_color = (*col, 1)
    return m


def belt_material(src, zoff, tag):
    """Copy of the stainless body material with the Yokosuka belt from object-space z (zoff = object origin height)."""
    name = f"V9 | stainless body with Yokosuka belt ({tag})"
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = src.copy(); m.name = name
    nt = m.node_tree; b = [n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'][0]
    base = tuple(b.inputs["Base Color"].default_value)
    rough0 = b.inputs["Roughness"].default_value; metal0 = b.inputs["Metallic"].default_value
    tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])

    def band(z0, z1):
        g = nt.nodes.new("ShaderNodeMath"); g.operation = 'GREATER_THAN'; g.inputs[1].default_value = z0 - zoff
        l = nt.nodes.new("ShaderNodeMath"); l.operation = 'LESS_THAN'; l.inputs[1].default_value = z1 - zoff
        mu = nt.nodes.new("ShaderNodeMath"); mu.operation = 'MULTIPLY'
        nt.links.new(sep.outputs["Z"], g.inputs[0]); nt.links.new(sep.outputs["Z"], l.inputs[0])
        nt.links.new(g.outputs[0], mu.inputs[0]); nt.links.new(l.outputs[0], mu.inputs[1])
        return mu
    mb_, mc_ = band(*BELT["blue"]), band(*BELT["cream"])
    mix1 = nt.nodes.new("ShaderNodeMix"); mix1.data_type = 'RGBA'
    mix1.inputs[6].default_value = base; mix1.inputs[7].default_value = (*BLUE, 1)
    nt.links.new(mb_.outputs[0], mix1.inputs[0])
    mix2 = nt.nodes.new("ShaderNodeMix"); mix2.data_type = 'RGBA'
    nt.links.new(mix1.outputs[2], mix2.inputs[6]); mix2.inputs[7].default_value = (*CREAM, 1)
    nt.links.new(mc_.outputs[0], mix2.inputs[0])
    nt.links.new(mix2.outputs[2], b.inputs["Base Color"])
    add = nt.nodes.new("ShaderNodeMath"); add.operation = 'ADD'
    nt.links.new(mb_.outputs[0], add.inputs[0]); nt.links.new(mc_.outputs[0], add.inputs[1])
    met = nt.nodes.new("ShaderNodeMapRange"); met.inputs["To Min"].default_value = metal0; met.inputs["To Max"].default_value = 0.0
    nt.links.new(add.outputs[0], met.inputs["Value"]); nt.links.new(met.outputs["Result"], b.inputs["Metallic"])
    ro = nt.nodes.new("ShaderNodeMapRange"); ro.inputs["To Min"].default_value = rough0; ro.inputs["To Max"].default_value = 0.30
    nt.links.new(add.outputs[0], ro.inputs["Value"]); nt.links.new(ro.outputs["Result"], b.inputs["Roughness"])
    return m


def led_material(src_name, kind):
    name = f"V9 | LED yokosuka {kind}"
    m = bpy.data.materials.get(name)
    if m:
        return m
    src = bpy.data.materials[src_name]
    m = src.copy(); m.name = name
    for n in m.node_tree.nodes:
        if n.type == 'TEX_IMAGE' and n.image:
            k = n.image.name.rsplit("_", 1)[-1]            # "0.png" / "1.png"
            fn = f"v9_led_yokosuka_{kind}_{k}"
            img = bpy.data.images.get(fn) or bpy.data.images.load(os.path.join(TEX, fn))
            img.pack()
            n.image = img
    return m


# ---------------------------------------------------------------- template collections
def copy_collection(src_name, dst_name, select=None):
    src = bpy.data.collections[src_name]
    dst = bpy.data.collections.get(dst_name)
    if dst is not None:
        return dst, None
    dst = bpy.data.collections.new(dst_name)
    dst.instance_offset = src.instance_offset
    mp = {}
    for ob in src.all_objects:
        if select and not select(ob):
            continue
        nob = ob.copy()
        nob.name = "V9 " + ob.name[:55]
        dst.objects.link(nob)
        mp[ob] = nob
    for ob, nob in mp.items():
        if ob.parent in mp:
            nob.parent = mp[ob.parent]
            nob.matrix_parent_inverse = ob.matrix_parent_inverse.copy()
    return dst, mp


def relivery_body(nob, tag, mats):
    """Copy the one-piece body mesh and swap the Yamanote livery for the Yokosuka one."""
    me = nob.data.copy(); me.name = "V9 " + nob.data.name[:50]
    nob.data = me
    names = [m.name if m else "" for m in me.materials]
    zoff = nob.matrix_world.translation.z
    idx = {}

    def slot(m):
        for i, x in enumerate(me.materials):
            if x == m:
                return i
        me.materials.append(m)
        return len(me.materials) - 1
    for i, n in enumerate(names):
        if n == "V2 | stainless commuter body":
            me.materials[i] = belt_material(bpy.data.materials[n], zoff, tag)
        elif n.startswith("V5 | LED yamanote "):
            me.materials[i] = led_material(n, n.rsplit(" ", 1)[-1])
    gi = names.index("V2 | Yamanote green") if "V2 | Yamanote green" in names else None
    moved = {"blue": 0, "door": 0}
    if gi is not None:
        i_blue = slot(mats["blue"]); i_door = slot(bpy.data.materials["V5 | EMU door leaf stainless"])
        mw = nob.matrix_world
        mi = np.empty(len(me.polygons), int); me.polygons.foreach_get("material_index", mi)
        ctr = np.empty(len(me.polygons) * 3); me.polygons.foreach_get("center", ctr); ctr = ctr.reshape(-1, 3)
        W = ctr @ np.array(mw)[:3, :3].T + np.array(mw)[:3, 3]
        sel = mi == gi
        front = sel & (W[:, 0] > 9.0)
        mi[front] = i_blue; mi[sel & ~front] = i_door
        moved = {"blue": int(front.sum()), "door": int((sel & ~front).sum())}
        me.polygons.foreach_set("material_index", mi)
        me.update()
    REP["templates"].setdefault(tag, {})["green_faces_moved"] = moved


def build_templates():
    mats = {"blue": paint("V9 | Yokosuka blue (E235-1000 front)", BLUE), "cream": paint("V9 | Yokosuka cream", CREAM, 0.35)}
    T = {}
    for kind, src in (("cab", "V3 E235-0 cab"), ("int", "V3 E235-0 intermediate")):
        dst, mp = copy_collection(src, f"V9 E235-1000 style {('cab' if kind == 'cab' else 'intermediate')} (Yokosuka livery)")
        if mp:
            for ob, nob in mp.items():
                if ob.type == 'MESH' and ob.name.startswith("V5 one-piece body"):
                    relivery_body(nob, kind, mats)
        T[kind] = dst
    # intermediate with pantograph: same objects + the raised single-arm pantograph of the model's E233 car
    dst, mp = copy_collection("V3 E235-0 intermediate", "V9 E235-1000 style intermediate with pantograph (Yokosuka livery)")
    if mp:
        base = T["int"]
        body_new = [o for o in base.all_objects if o.name.startswith("V9 V5 one-piece body")][0]
        for ob, nob in mp.items():
            if ob.type == 'MESH' and ob.name.startswith("V5 one-piece body"):
                nob.data = body_new.data
        pan_src = bpy.data.collections["V4_Train_Track_08_actual_car_03_pantograph"]
        n = 0
        for ob in pan_src.all_objects:
            if "_raised_" in ob.name:
                nob = ob.copy(); nob.name = "V9 E235-1000 pantograph " + ob.name.split("_raised_")[-1]
                dst.objects.link(nob); n += 1
        REP["templates"]["pantograph_parts"] = n
    T["pan"] = dst
    # Green cars: E233-3000 double-deck shells, orange / green -> cream / blue (object-level material slots)
    for k in ("04", "05"):
        dst, mp = copy_collection(f"V4_Train_Green_E233_3000_car_{k}", f"V9 Green car {k} (E233-3000 double-deck shell, Yokosuka colours)")
        if mp:
            nsw = 0
            for ob, nob in mp.items():
                if ob.type not in ('MESH', 'CURVE'):
                    continue
                for si, sl in enumerate(nob.material_slots):
                    m = sl.material
                    if m and m.name in ("V4_Train_Shonan_green", "V4_Train_Shonan_orange"):
                        new = mats["blue"] if m.name.endswith("green") else mats["cream"]
                        sl.link = 'OBJECT'; sl.material = new; nsw += 1
            REP["templates"][f"green_{k}_slots_switched"] = nsw
        T["g" + k[-1]] = dst
    for k, c in T.items():
        c["V9_template"] = True
    return T


# ---------------------------------------------------------------- trains
FORMATION = [(1, "cab", math.pi), (2, "int", 0.0), (3, "pan", 0.0), (4, "g4", 0.0), (5, "g5", 0.0), (6, "int", 0.0),
             (7, "pan", 0.0), (8, "int", 0.0), (9, "pan", 0.0), (10, "int", 0.0), (11, "cab", 0.0),
             (12, "cab", math.pi), (13, "pan", math.pi), (14, "int", 0.0), (15, "cab", 0.0)]
TRAINS = {1: {"line": "横須賀線 Yokosuka Line (for Kurihama)", "heading": -1, "dest": 0.0},
          4: {"line": "総武線快速 Sobu Rapid (for Chiba)", "heading": 1, "dest": 1.0}}


def place_trains(T, col):
    for trk, info in TRAINS.items():
        yt = G.TRK[trk]
        for (num, kind, yaw), x in zip(FORMATION, G.CAR_X):
            name = f"V9 B5 track {trk} car {num:02d} | {T[kind].name[:40]}"
            e = bpy.data.objects.new(name, None)
            e.instance_type = 'COLLECTION'; e.instance_collection = T[kind]
            col.objects.link(e)
            e.matrix_world = FR @ Matrix.Translation((x, yt, G.RAIL)) @ Matrix.Rotation(yaw, 4, 'Z')
            head = (info["heading"] < 0 and num == 1) or (info["heading"] > 0 and num == 15)
            tail = (info["heading"] < 0 and num == 15) or (info["heading"] > 0 and num == 1)
            e["V5_head"] = 1.0 if head else 0.0
            e["V5_tail"] = 1.0 if tail else 0.0
            e["V5_dest"] = info["dest"]
            e["track"] = f"B5-{trk}"; e["line"] = info["line"]; e["car_number"] = num
            e["Green_car"] = kind in ("g4", "g5"); e["cab"] = kind == "cab"
            e["rail_top_world_m"] = G.RAIL; e["V9_sobu"] = True; e["V9_train"] = True
            REP["cars"].append({"name": name, "track": trk, "car": num, "local_x": x, "kind": kind, "yaw_deg": round(math.degrees(yaw)),
                                "head": head, "tail": tail})


# ---------------------------------------------------------------- door-position floor markers (乗車位置目標)
def door_xs(col_name, fallback, key="door leaf"):
    """Door centres (collection-space x) from the faces of a door material on the +y side of a car
    (on the E235-0 the door areas are exactly the Yamanote-green faces)."""
    xs = []
    for ob in bpy.data.collections[col_name].all_objects:
        if ob.type != 'MESH':
            continue
        me = ob.data
        idx = [i for i, m in enumerate(me.materials) if m and all(k in m.name.lower() for k in key.split())]
        if not idx:
            continue
        mw = ob.matrix_world
        for p in me.polygons:
            if p.material_index in idx:
                c = mw @ p.center
                if c.y > 0.5:
                    xs.append(c.x)
    if not xs:
        return fallback, "fallback"
    xs = sorted(xs); groups = [[xs[0]]]
    for x in xs[1:]:
        (groups[-1] if x - groups[-1][-1] < 0.8 else groups.append([x]) or groups[-1]).append(x)
    cents = [round((min(g) + max(g)) / 2, 3) for g in groups if max(g) - min(g) > 0.6]
    return (cents if len(cents) >= 2 else fallback), "mesh"


def build_door_markers(col):
    import v5lib as LL
    png = os.path.join(TEX, "v9_door_markers_yokosuka.png")
    m = bpy.data.materials.get("V9 | door-position floor markers (JO)")
    if m is None:
        m = bpy.data.materials.new("V9 | door-position floor markers (JO)"); m.use_nodes = True
        nt = m.node_tree; bsdf = nt.nodes.get("Principled BSDF")
        img = bpy.data.images.get("v9_door_markers_yokosuka.png") or bpy.data.images.load(png); img.pack()
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = img
        nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"]); bsdf.inputs["Roughness"].default_value = 0.6
    d_e235, src1 = door_xs("V3 E235-0 intermediate", [-7.2, -2.4, 2.4, 7.2], "yamanote green")
    d_green, src2 = door_xs("V4_Train_Green_E233_3000_car_04", [-7.6, 7.6])
    REP["door_markers"] = {"e235_doors_x": d_e235, "source": src1, "green_doors_x": d_green, "green_source": src2}
    mb = LL.MeshBuilder(); hw = 0.30
    n = 0
    for t, yt in G.TRK.items():
        isl = "1-2" if t in (1, 2) else "3-4"
        sgn = 1.0 if G.ISL_C[isl] > yt else -1.0
        d0 = G.EDGE + 1.15; d1 = d0 + 0.40
        for (num, kind, yaw), xc in zip(FORMATION, G.CAR_X):
            for dx in (d_green if kind in ("g4", "g5") else d_e235):
                x = xc + dx
                cell = num - 1
                cu0, cv0 = (cell % 4) / 4.0, 1.0 - (cell // 4 + 1) / 4.0
                corner = [(d0, -hw), (d0, hw), (d1, hw), (d1, -hw)]
                pts = [(x + tt, yt + sgn * dd, G.DECK + 0.004) for dd, tt in corner]
                uv = [(cu0 + 0.25 * (0.5 - sgn * tt / (2 * hw)), cv0 + 0.25 * ((d1 - dd) / (d1 - d0))) for dd, tt in corner]
                order = [0, 1, 2, 3] if sgn > 0 else [3, 2, 1, 0]
                mb.add([pts[i] for i in order], [(0, 1, 2, 3)], 0, uvs=[[uv[i] for i in order]])
                n += 1
    ob = mb.build("V9 Sobu | door-position floor markers (15 cars, tracks 1-4)", col, [m])
    ob.matrix_world = FR; ob["V9_sobu"] = True
    REP["door_markers"]["count"] = n


# ---------------------------------------------------------------- people
def place_people(col):
    peds = sorted([c for c in bpy.data.collections if c.name.startswith("V5 pedestrian ") and c.name[-1].isdigit()], key=lambda c: c.name)
    if not peds:
        REP["warnings"].append("no pedestrian collections")
        return
    encl = []
    for isl in G.ISL:
        for gx in G.GROUP_X:
            xf, s, yc = G.group_frame(gx, isl)
            a, b = sorted((xf - s * 1.5, xf + s * (G.GROUP_LEN + 0.5)))
            encl.append((a, b, yc - G.ENCL_HALF - 0.3, yc + G.ENCL_HALF + 0.3))
    lifts = [(x - 1.6, x + 1.6, y - 1.7, y + 1.7) for (x, y, _) in G.ELEV.values()]
    banks = []
    for bk, (xf, s) in G.BANKS.items():
        a, b = sorted((xf - s * 2.5, xf + s * (G.BANK_LEN + 2.0)))
        banks.append((a, b, -G.BANK_HALF - 0.4, G.BANK_HALF + 0.4))
    vl = G.to_local(*G.VENT_XY_MODEL)
    vent = (vl[0] - G.VENT_HALF - 1.0, vl[0] + G.VENT_HALF + 1.0, vl[1] - G.VENT_HALF - 1.0, vl[1] + G.VENT_HALF + 1.0)
    wells = [G.group_opening(gx, isl) for isl in G.ISL for gx in G.GROUP_X]
    wells = [(a - 0.5, b + 0.5, c - 0.5, d + 0.5) for (a, b, c, d) in wells]

    cams = []
    for _, cp, ct, _ in G.REVIEW_CAMS:
        d = np.array(ct[:2]) - np.array(cp[:2])
        cams.append((np.array(cp[:2]), d / np.linalg.norm(d), cp[2]))

    def in_view(x, y, z):
        """Keep the first metres in front of each review camera clear of people."""
        for c, u, cz in cams:
            if abs(cz - z) > 4.0:
                continue
            v = np.array((x, y)) - c
            along = float(v @ u); lat = abs(float(v[0] * u[1] - v[1] * u[0]))
            if np.hypot(*v) < 1.5 or (0.0 < along < 8.0 and lat < 0.8 + 0.3 * along):
                return True
        return False

    def free(x, y, rects, circles, placed, z=None):
        if z is not None and in_view(x, y, z):
            return False
        if any(r[0] <= x <= r[1] and r[2] <= y <= r[3] for r in rects):
            return False
        if any(math.hypot(x - cx, y - cy) < rr for cx, cy, rr in circles):
            return False
        return all(math.hypot(x - px, y - py) > 0.9 for px, py in placed)
    # B5 platforms: keep behind the tactile line, away from columns, enclosures, benches / vending machines (column rows)
    b5_cols = [(x, yc + dy, G.COL_R_ISL + 0.45) for x in G.COL_X for yc in G.ISL_C.values() for dy in (-G.COL_ROW_OFF, G.COL_ROW_OFF)]
    furn = [(x - 1.8, x + 1.8, yc + dy - 0.5, yc + dy + 0.5) for x in np.arange(-150, 151, 3.5)
            for yc in G.ISL_C.values() for dy in (-G.COL_ROW_OFF, G.COL_ROW_OFF)]
    furn += [(x - 0.75, x + 0.75, yc - 1.05, yc + 1.05) for x in (-133.0, 133.0) for yc in G.ISL_C.values()]   # vending machines
    up_cols = [(x, y, 0.95) for x in G.COL_X for y in (-11.99, -6.79, 0.0, 6.79, 11.99)]
    jobs = []
    for isl, (ya, yb) in G.ISL.items():
        jobs.append(("B5 " + isl, 46, (-145.0, 145.0), (ya + 1.3, yb - 1.3), G.DECK, encl + lifts + furn, b5_cols))
    jobs.append(("B4", 34, (G.B4_HALL_X[0] + 3, G.B4_HALL_X[1] - 3), (-13.4, 13.4), G.B4_FLOOR, wells + lifts + banks, up_cols))
    jobs.append(("B1", 30, (G.B1_GATES_X + 2.0, G.B1_HALL_X[1] - 3), (-17.6, 17.6), G.B1_FLOOR,
                 banks + [vent, lifts[0]], up_cols))
    jobs.append(("B1 unpaid", 8, (G.B1_HALL_X[0] + 1.5, G.B1_GATES_X - 2.0), (-17.6, 17.6), G.B1_FLOOR, [vent], up_cols))
    n_all = 0
    for tag, n, xr, yr, z, rects, circ in jobs:
        placed = []
        tries = 0
        while len(placed) < n and tries < 20000:
            tries += 1
            x = float(RNG.uniform(*xr)); y = float(RNG.uniform(*yr))
            if not free(x, y, rects, circ, placed, z):
                continue
            placed.append((x, y))
        for i, (x, y) in enumerate(placed):
            c = peds[int(RNG.integers(len(peds)))]
            e = bpy.data.objects.new(f"V9 person {tag} {i:02d}", None)
            e.instance_type = 'COLLECTION'; e.instance_collection = c
            col.objects.link(e)
            if tag.startswith("B5"):
                yaw = float(RNG.choice([0.0, math.pi])) + float(RNG.normal(0, 0.35))
            else:
                yaw = float(RNG.uniform(0, 2 * math.pi))
            e.matrix_world = FR @ Matrix.Translation((x, y, z)) @ Matrix.Rotation(yaw, 4, 'Z')
            e["V9_sobu"] = True; e["V9_person"] = True; e["V9_level"] = tag.split()[0]
            e["V9_local_xy"] = (round(x, 2), round(y, 2))
        REP["people"][tag] = len(placed)
        n_all += len(placed)
    REP["people"]["total"] = n_all


def run():
    T = build_templates()
    col = L.collection("V9_Sobu_Trains", parent=bpy.data.collections["V9_Sobu_Underground_Station"])
    pcol = L.collection("V9_Sobu_People", parent=bpy.data.collections["V9_Sobu_Underground_Station"])
    place_trains(T, col)
    build_door_markers(bpy.data.collections["V9_Sobu_Underground_Station"])
    place_people(pcol)
    REP["templates"]["collections"] = {k: v.name for k, v in T.items()}


run()
L.log("V9 trains", len(REP["cars"]), "people", json.dumps(REP["people"]), json.dumps(REP["templates"], ensure_ascii=False))
if REPORT:
    json.dump(REP, open(REPORT, "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=str)
if OUT:
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=True)
    L.log("saved", OUT)
