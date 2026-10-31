"""V6 module 2: train markings and N700 lamps (round-6 feedback "火车和地铁的细节"; V5 README listed as not done:
car numbers / signs on the car bodies, N700 without lamp states or side displays).

  * commuter EMUs (E233-0 / -1000 / -3000, E235-0, Green cars), per car instance:
      - 形式番号 lettering (e.g. クハE233-3017) near one car end, below the windows, both sides.  Type prefixes follow the
        car's role (cab = クハ, pantograph car = モハ, its unit partner = モハ, Green = サロ, others = サハ); the running
        numbers are illustrative (set numbers per track, not checked against a real roster).
      - 号車 plate beside every passenger door, from the instance's car_number property
      - 優先席 (priority seat) sticker on the end window at one end of every car
    Each car gets one small object parented to its instance empty, so moving or re-ordering a train keeps the markings.
  * Shinkansen side LED displays (train name, destination, car number, seat class) beside the doors:
      - E5 on track 20 (はやぶさ 新函館北斗): at the inner edge of every door of every car, both sides
      - N700 on tracks 14 (のぞみ 新大阪) and 18 (のぞみ 博多): the downloaded N700 body has no separate doors, so the door
        zones are found from the window rows (rays along each car at window height); the display goes between the door
        zone and the first window, both sides
  * N700 head / tail lamps: the downloaded nose has no lamp parts.  Two lamp lenses per nose are placed on the nose
    surface just below the front corners of the windscreen (approximate position); Tokaido trains leave Tokyo southwards,
    so the south nose (car 1) shows white head lamps and the north nose (car 16) red tail lamps.
  * the E5 car-number lettering (Bahnschrift in V5) is switched to Noto Sans JP Bold (packed).

usage: blender -b in.blend --python-exit-code 1 -P mod6_trains.py -- out.blend [report.json]
"""
import sys, os, json, math, re
from collections import Counter, defaultdict
import numpy as np
import bpy
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v5lib as L

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGV[0] if ARGV else None
REPORT = ARGV[1] if len(ARGV) > 1 else None
TEX = os.path.join(HERE, "textures")
ATL = json.load(open(os.path.join(TEX, "v6_train_atlas.json"), encoding="utf-8"))
FONT_B = os.path.join(HERE, "fonts", "NotoSansJP-Bold.otf")
FONT_M = os.path.join(HERE, "fonts", "NotoSansJP-Medium.otf")
Z = Vector((0, 0, 1))
REP = {"commuter": {}, "e5": {}, "n700": {}, "warnings": []}

# illustrative set numbers per track (main unit, attached unit)
SETNO = {1: (41, None), 3: (21, None), 4: (15, None), 5: (32, None), 8: (17, 27), 10: (4, 14)}
SERIES_BASE = {"E233-0": ("E233", "E232", 0), "E233-1000": ("E233", "E232", 1000), "E233-3000": ("E233", "E232", 3000),
               "E235-0": ("E235", "E234", 0)}


# ------------------------------------------------------------------ materials
def materials():
    img_path = os.path.join(TEX, ATL["page"])
    img = bpy.data.images.get(os.path.basename(img_path)) or bpy.data.images.load(img_path)
    img.pack()

    def atlas_mat(name, strength, rough):
        m = bpy.data.materials.get(name)
        if m:
            return m
        m = bpy.data.materials.new(name)
        nt = m.node_tree
        b = nt.nodes.get("Principled BSDF")
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = img; t.interpolation = 'Linear'
        uv = nt.nodes.new("ShaderNodeUVMap"); uv.uv_map = "V5 metre UV"
        nt.links.new(uv.outputs[0], t.inputs[0])
        nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
        if strength > 0:
            nt.links.new(t.outputs["Color"], b.inputs["Emission Color"])
            b.inputs["Emission Strength"].default_value = strength
        b.inputs["Roughness"].default_value = rough
        m.diffuse_color = (0.5, 0.5, 0.5, 1)
        return m

    return {
        "sticker": atlas_mat("V6 | train stickers (atlas)", 0.0, 0.35),
        "led": atlas_mat("V6 | Shinkansen side LED display (atlas)", 2.2, 0.2),
        "ink": L.principled("V6 | train lettering black", (0.02, 0.02, 0.022), rough=0.4),
        "frame": L.principled("V6 | LED display frame", (0.05, 0.05, 0.055), rough=0.3, metal=0.4),
        "head": L.principled("V6 | N700 head lamp (lit)", (0.9, 0.92, 0.95), rough=0.05, emission=(1.0, 0.97, 0.9), strength=40.0),
        "tail": L.principled("V6 | N700 tail lamp (lit)", (0.3, 0.01, 0.01), rough=0.05, emission=(1.0, 0.01, 0.004), strength=1.4),
        "lamp_rim": L.principled("V6 | N700 lamp rim", (0.04, 0.04, 0.045), rough=0.25, metal=0.5),
    }


MATS = None
MLIST = []


def mi(key):
    m = MATS[key]
    if m not in MLIST:
        MLIST.append(m)
    return MLIST.index(m)


# ------------------------------------------------------------------ geometry helpers
def quad(mb, C, R, U, w, h, key, mat_key):
    u0, v0, u1, v1 = ATL["items"][key]["uv"]
    cs = [C - R * (w / 2) - U * (h / 2), C + R * (w / 2) - U * (h / 2), C + R * (w / 2) + U * (h / 2), C - R * (w / 2) + U * (h / 2)]
    mb.add([tuple(c) for c in cs], [(0, 1, 2, 3)], mi(mat_key), uvs=[[(u0, v0), (u1, v0), (u1, v1), (u0, v1)]])


def frame_box(mb, C, R, U, N, w, h, d, mat_key):
    """thin box behind a display: C on the body surface, N outward"""
    M = Matrix(((R.x, N.x, U.x, C.x), (R.y, N.y, U.y, C.y), (R.z, N.z, U.z, C.z), (0, 0, 0, 1)))
    L.box(mb, 0, d / 2, 0, w, d, h, mi(mat_key), frame=M)


_TEXT = {}


def text_mesh(s, font_path):
    """(verts, faces) of a string in the xy plane, centred, 1 unit = font size."""
    k = (s, font_path)
    if k in _TEXT:
        return _TEXT[k]
    font = None
    for f in bpy.data.fonts:
        if f.filepath and os.path.normcase(bpy.path.abspath(f.filepath)) == os.path.normcase(font_path):
            font = f
    if font is None:
        font = bpy.data.fonts.load(font_path)
        font.pack()
    cu = bpy.data.curves.new("v6 tmp text", 'FONT')
    cu.body = s
    cu.font = font
    cu.size = 1.0
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    cu.resolution_u = 3
    cu.fill_mode = 'FRONT'
    ob = bpy.data.objects.new("v6 tmp text", cu)
    bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    V = [tuple(v.co) for v in me.vertices]
    Fc = [tuple(p.vertices) for p in me.polygons]
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)
    bpy.data.meshes.remove(me)
    _TEXT[k] = (V, Fc)
    return V, Fc


def put_text(mb, s, C, R, U, height, mat_key, font=FONT_M):
    V, Fc = text_mesh(s, font)
    if not V:
        return 0.0
    xs = [v[0] for v in V]
    w = (max(xs) - min(xs)) * height
    P = [tuple(C + R * (v[0] * height) + U * (v[1] * height)) for v in V]
    mb.add(P, Fc, mi(mat_key))
    return w


class Surface:
    """BVH of a set of meshes in one coordinate frame, with the material name of every triangle."""

    def __init__(self, objs, M=Matrix.Identity(4)):
        V, T, mats = [], [], []
        for o in objs:
            me = o.data
            n = len(me.vertices)
            if n == 0:
                continue
            co = np.empty(n * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
            mw = np.array(M @ o.matrix_world)
            W = co @ mw[:3, :3].T + mw[:3, 3]
            me.calc_loop_triangles()
            nt = len(me.loop_triangles)
            tri = np.empty(nt * 3, int); me.loop_triangles.foreach_get("vertices", tri)
            pidx = np.empty(nt, int); me.loop_triangles.foreach_get("polygon_index", pidx)
            midx = np.empty(len(me.polygons), int); me.polygons.foreach_get("material_index", midx)
            names = [(me.materials[i].name if i < len(me.materials) and me.materials[i] else "") for i in range(max(1, len(me.materials)))]
            o0 = len(V)
            V.extend(map(tuple, W))
            T.extend(map(tuple, tri.reshape(-1, 3) + o0))
            mats.extend(names[min(m_, len(names) - 1)] for m_ in midx[pidx])
        self.mats = mats
        self.bvh = BVHTree.FromPolygons(V, T, all_triangles=True) if T else None

    def cast(self, p, d, dist=6.0):
        if self.bvh is None:
            return None
        loc, nor, idx, dd = self.bvh.ray_cast(Vector(p), Vector(d), dist)
        if loc is None:
            return None
        return loc, nor, self.mats[idx], dd


def side_patch(S, x, z, s, w, h, ok, y_out=3.0):
    """Find the body surface at (x, z) on side s (local frame, y across); all four corners and the centre must hit a
    material accepted by ok().  Returns (C on surface, R, U, N) or None."""
    pts = [(x, z), (x - w / 2, z - h / 2), (x + w / 2, z - h / 2), (x + w / 2, z + h / 2), (x - w / 2, z + h / 2)]
    hits = []
    for px, pz in pts:
        r = S.cast((px, s * y_out, pz), (0, -s, 0))
        if r is None or not ok(r[2]):
            return None
        hits.append(r)
    ys = [abs(h_[0].y) for h_ in hits]
    if max(ys) - min(ys) > 0.03:          # curved too much under the decal
        return None
    C = hits[0][0]
    N = Vector((0, s, 0))
    if hits[0][1].dot(N) > 0.5:
        N = Vector((hits[0][1].x * 0, hits[0][1].y, hits[0][1].z)).normalized()
    U = (Z - N * Z.dot(N)).normalized()
    R = U.cross(N)                         # viewer looking at -N: right = U x N
    C = Vector((C.x, max(ys) * s, C.z))   # sit on the outermost corner
    return C, R, U, N


# ------------------------------------------------------------------ commuter cars
def master_info(col):
    """series, body objects, doors (local) and car length of a commuter master (or a pantograph variant of one)."""
    objs = [o for o in col.all_objects if o.type == 'MESH' and not o.hide_render]
    body = [o for o in objs if o.name.startswith("V5 one-piece body | ")]
    name = body[0].name.split(" | ", 1)[1] if body else col.name
    base_col = bpy.data.collections.get(name) or col
    doors = json.loads(base_col.get("V5_doors", "[]")) if base_col.get("V5_doors") else []
    green_v4 = col.name.startswith("V4_Train_Green")
    if green_v4:
        series = "E233-3000"
        surf_objs = objs
        dz = defaultdict(list)
        for o in objs:
            if re.search(r"(?i)door", o.name) and "window" not in o.name.lower():
                ws = [o.matrix_world @ Vector(c) for c in o.bound_box]
                y = sum(v.y for v in ws) / 8
                if abs(y) > 1.2:
                    dz[1 if y > 0 else -1].append((min(v.x for v in ws), max(v.x for v in ws)))
        doors = []
        for s, ivs in dz.items():
            ivs.sort()
            cur = None
            for a, b in ivs:
                if cur and a <= cur[1] + 0.05:
                    cur[1] = max(cur[1], b)
                else:
                    if cur:
                        doors.append([s, cur[0], cur[1]])
                    cur = [a, b]
            if cur:
                doors.append([s, cur[0], cur[1]])
        doors = [d for d in doors if 0.5 < d[2] - d[1] < 1.6]
    else:
        m = re.search(r"(E233-0|E233-1000|E233-3000|E235-0)", name)
        series = m.group(1) if m else "E233-0"
        surf_objs = body
    xs = []
    for o in surf_objs:
        xs += [(o.matrix_world @ Vector(c)).x for c in o.bound_box]
    return {"series": series, "surf": Surface(surf_objs), "doors": [d for d in doors if d[2] - d[1] > 1.0 or green_v4],
            "half_len": (max(xs) - min(xs)) / 2, "x_mid": (max(xs) + min(xs)) / 2, "green_v4": green_v4,
            "panto": bool(re.search(r"panto", col.name, re.I)), "body_mat": "stainless" if not green_v4 else None}


def body_ok(mname):
    n = mname.lower()
    if any(k in n for k in ("glass", "glazing", "window", "rubber", "gasket", "shadow", "led", "band", "shonan", "orange",
                            "yamanote", "sky blue", "door leaf")):
        return False
    return "stainless" in n or "body" in n or "shell" in n


def glass_ok(mname):
    n = mname.lower()
    return "glazing" in n or "glass" in n


def car_designations(cars):
    """cars: list of dicts (car_number, cab, green, panto, unit) for one track -> {car_number: (prefix, form_index)}"""
    out = {}
    by_unit = defaultdict(list)
    for c in cars:
        by_unit[c["unit"]].append(c)
    for unit, cs in by_unit.items():
        cs.sort(key=lambda c: c["car_number"])
        nums = [c["car_number"] for c in cs]
        panto = {c["car_number"] for c in cs if c["panto"]}
        greens = sorted(c["car_number"] for c in cs if c["green"])
        plain = {c["car_number"] for c in cs if not (c["cab"] or c["green"]) and c["car_number"] not in panto}
        partner = set()
        for p_ in sorted(panto):                  # M' partner of each pantograph car: next car, else previous
            for q in (p_ + 1, p_ - 1):
                if q in plain and q not in partner:
                    partner.add(q)
                    break
        for c in cs:
            n = c["car_number"]
            if c["cab"]:
                out[n] = ("クハ", 0 if n == min(nums) else 1)
            elif c["green"]:
                out[n] = ("サロ", 0 if n == greens[0] else 1)
            elif n in panto:
                out[n] = ("モハ", 0)
            elif n in partner:
                out[n] = ("モハ", 1)
            else:
                out[n] = ("サハ", 0)
    return out


def commuter():
    insts = [o for o in bpy.data.objects if o.instance_type == 'COLLECTION' and o.instance_collection
             and re.match(r"Track \d\d car \d\d$", o.name) and not o.hide_render]
    infos = {}
    per_track = defaultdict(list)
    for o in insts:
        c = o.instance_collection
        if c.name not in infos:
            infos[c.name] = master_info(c)
        I = infos[c.name]
        per_track[int(o["track"])].append({"obj": o, "car_number": int(o["car_number"]), "cab": bool(o.get("cab")),
                                           "green": bool(o.get("Green_car")), "panto": I["panto"], "unit": o.get("unit", ""), "I": I})
    col = L.collection("V6_Train_Markings")
    n_obj = n_no = n_plate = n_yusen = 0
    for t, cars in sorted(per_track.items()):
        desig = car_designations(cars)
        counter = Counter()
        main_set, att_set = SETNO.get(t, (1, None))
        units = sorted({c["unit"] for c in cars})
        for c in sorted(cars, key=lambda c: c["car_number"]):
            o, I = c["obj"], c["I"]
            s_odd, s_even, base = SERIES_BASE[I["series"]]
            prefix, form = desig[c["car_number"]]
            sfx = s_odd if form == 0 else s_even
            setno = att_set if (att_set and "attached" in c["unit"]) else main_set
            k = counter[(c["unit"], prefix, sfx)]
            counter[(c["unit"], prefix, sfx)] += 1
            num = base + setno + 100 * k
            label = f"{prefix}{sfx}-{num}"
            mb = L.MeshBuilder()
            S = I["surf"]
            hl = I["half_len"]
            got = {"no": 0, "plate": 0, "yusen": 0}
            for s in (-1, 1):
                # 形式番号: near the -x end, below the windows
                for z in (1.42, 1.34, 1.50, 1.26, 1.58, 1.15, 1.05, 0.95):
                    for x in [I["x_mid"] - hl + dx for dx in (0.85, 1.05, 1.25, 1.6, 2.0, 2.5, 3.0, 3.5, 4.0)]:
                        V, Fc = text_mesh(label, FONT_M)
                        wt = (max(v[0] for v in V) - min(v[0] for v in V)) * 0.075
                        P = side_patch(S, x, z, s, wt + 0.04, 0.11, body_ok)
                        if P:
                            C, R, U, N = P
                            put_text(mb, label, C + N * 0.004, R, U, 0.075, "ink")
                            got["no"] += 1
                            break
                    else:
                        continue
                    break
                # 号車 plate beside each door (door-number side towards the car centre)
                for d in I["doors"]:
                    if d[0] != s:
                        continue
                    placed = False
                    inward = 1 if (d[1] + d[2]) / 2 < I["x_mid"] else -1
                    for z in (2.05, 1.95, 2.15, 1.85):
                        for gap in (0.13, 0.17, 0.22):
                            x = (d[2] + gap) if inward > 0 else (d[1] - gap)
                            P = side_patch(S, x, z, s, 0.16, 0.08, body_ok)
                            if P is None:
                                x = (d[1] - gap) if inward > 0 else (d[2] + gap)
                                P = side_patch(S, x, z, s, 0.16, 0.08, body_ok)
                            if P:
                                C, R, U, N = P
                                quad(mb, C + N * 0.004, R, U, 0.16, 0.08, f"gosha_{c['car_number']:02d}", "sticker")
                                got["plate"] += 1
                                placed = True
                                break
                        if placed:
                            break
                # 優先席 on an end window (the non-cab end of cab cars, the +x end otherwise; none in Green cars)
                end = -1 if (c["cab"] and not I["green_v4"]) else 1
                done = c["green"]
                for z in ((2.30, 2.20, 2.40, 2.10) if not done else ()):
                    for dx in (0.95, 1.15, 1.35, 0.75, 1.6):
                        x = I["x_mid"] + end * (hl - dx)
                        P = side_patch(S, x, z, s, 0.20, 0.20, glass_ok)
                        if P:
                            C, R, U, N = P
                            quad(mb, C + N * 0.003, R, U, 0.20, 0.20, "yusen", "sticker")
                            got["yusen"] += 1
                            done = True
                            break
                    if done:
                        break
            if not mb.v:
                REP["warnings"].append(f"{o.name}: no marking placed")
                continue
            ob = mb.build(f"V6 train markings | {o.name}", col, list(MLIST))
            ob.parent = o
            ob.matrix_parent_inverse = Matrix.Identity(4)
            ob["V6_trains"] = True
            ob["car_label"] = label
            n_obj += 1
            n_no += got["no"]; n_plate += got["plate"]; n_yusen += got["yusen"]
            REP["commuter"][o.name] = {"label": label, **got}
            if got["no"] < 2 or got["plate"] < len(I["doors"]) or (got["yusen"] < 2 and not c["green"]):
                REP["warnings"].append(f"{o.name}: placed {got} (doors {len(I['doors'])})")
            MLIST.clear()
    REP["commuter_totals"] = {"objects": n_obj, "car_numbers": n_no, "gosha_plates": n_plate, "yusen_stickers": n_yusen}
    L.log("commuter markings", REP["commuter_totals"])


# ------------------------------------------------------------------ Shinkansen LED panels
LED_W, LED_H = 0.84, 0.16


def led_at(mb, C, R, U, N, key, w=LED_W):
    h = LED_H * w / LED_W
    frame_box(mb, C, R, U, N, w + 0.05, h + 0.05, 0.012, "frame")
    quad(mb, C + N * 0.0135, R, U, w, h, key, "led")


def e5():
    insts = [o for o in bpy.data.objects if o.instance_type == 'COLLECTION' and o.instance_collection
             and re.match(r"Track (\d\d) \| E5 car \d\d$", o.name) and not o.hide_render]
    col = L.collection("V6_Train_Markings")
    n = 0
    for o in insts:
        t = int(re.match(r"Track (\d\d)", o.name).group(1))
        car = int(o["car_number"])
        key = f"led_{t}_{car:02d}"
        if key not in ATL["items"]:
            REP["warnings"].append(f"{o.name}: no LED texture {key}")
            continue
        c = o.instance_collection
        body = [b for b in c.all_objects if b.name.startswith("V5 one-piece body | ")]
        S = Surface(body)
        doors = json.loads(c.get("V5_doors", "[]"))
        xs = [(b.matrix_world @ Vector(v)).x for b in body for v in b.bound_box]
        xm = (max(xs) + min(xs)) / 2
        ok = lambda m_: ("e5" in m_.lower() and "band" not in m_.lower()) or "rail vehicle white" in m_.lower()
        mb = L.MeshBuilder()
        placed = 0
        for d in doors:
            s = d[0]
            inward = 1 if (d[1] + d[2]) / 2 < xm else -1
            done = False
            for z in (2.32, 2.22, 2.42, 2.12):
                for gap in (0.10, 0.20, 0.35, 0.5):
                    x = (d[2] + gap + LED_W / 2) if inward > 0 else (d[1] - gap - LED_W / 2)
                    P = side_patch(S, x, z, s, LED_W + 0.05, LED_H + 0.05, ok)
                    if P:
                        led_at(mb, *P, key)
                        placed += 1
                        done = True
                        break
                if done:
                    break
            if not done:
                REP["warnings"].append(f"{o.name}: door {d} without LED display")
        if mb.v:
            ob = mb.build(f"V6 train markings | {o.name}", col, list(MLIST))
            ob.parent = o
            ob.matrix_parent_inverse = Matrix.Identity(4)
            ob["V6_trains"] = True
        MLIST.clear()
        REP["e5"][o.name] = {"car": car, "doors": len(doors), "led_panels": placed}
        n += placed
    # car-number lettering: Noto Sans JP Bold instead of Bahnschrift
    font = bpy.data.fonts.load(FONT_B, check_existing=True)
    font.pack()
    k = 0
    for ob in bpy.data.objects:
        if ob.type == 'FONT' and re.match(r"V3 E5 car \d\d car number", ob.name):
            ob.data.font = font
            ob.data.font_bold = font
            k += 1
    REP["e5_totals"] = {"led_panels": n, "car_number_font_switched": k}
    L.log("E5", REP["e5_totals"])


def fit_panel(hits, out):
    """Panel plane from the corner hits (centre, LL, LR, UR, UL): horizontal normal perpendicular to the chord between
    the left and right edge mid-points (so the panel follows the body, not the bogie axis), pushed out until no corner
    is below the surface."""
    left = (hits[1][0] + hits[4][0]) / 2
    right = (hits[2][0] + hits[3][0]) / 2
    chord = Vector((right.x - left.x, right.y - left.y, 0.0))
    N = Z.cross(chord).normalized() if chord.length > 1e-6 else Vector(out).normalized()
    if N.dot(Vector(out)) < 0:
        N = -N
    pts = [h[0] for h in hits[1:]]
    C = sum(pts, Vector()) / 4
    push = max((q - C).dot(N) for q in pts)
    return C + N * push, N


def n700():
    col = L.collection("V6_Train_Markings")
    for E in [o for o in bpy.data.objects if o.instance_type == 'COLLECTION' and o.instance_collection
              and re.match(r"Track (\d\d) \| N700", o.name)]:
        t = int(re.match(r"Track (\d\d)", E.name).group(1))
        fc = E.instance_collection
        objs = [o for o in fc.all_objects if o.type == 'MESH' and not o.hide_render]
        body = [o for o in objs if " car " not in o.name]          # the downloaded shell (bogies are named "... car NN ...")
        S = Surface(body)
        # car axes from the axle shafts
        axles = defaultdict(list)
        for o in objs:
            m = re.search(r"N700 car (\d\d) axle shaft", o.name)
            if m:
                ws = [o.matrix_world @ Vector(c) for c in o.bound_box]
                axles[int(m.group(1))].append(sum(ws, Vector()) / 8)
        cars = {}
        for cn, pts in axles.items():
            P = np.array([tuple(p) for p in pts])
            c0 = P.mean(0)
            u, sv, vt = np.linalg.svd(P[:, :2] - c0[:2])
            a = Vector((vt[0][0], vt[0][1], 0)).normalized()
            if a.x < 0:
                a = -a
            cars[cn] = (Vector(c0), a)
        order = sorted(cars, key=lambda cn: -cars[cn][0].x)       # south (+x) first
        darkm = lambda m_: m_ in ("Material.721",) or "glass" in m_.lower()
        mb = L.MeshBuilder()
        placed = 0
        info = {}
        z_win = 2.40
        for i, cn in enumerate(order):
            c0, a = cars[cn]
            nrm = Z.cross(a)                    # +y-ish
            # car ends: half way to the neighbours (end cars: 27 m incl. nose)
            nb = []
            if i > 0:
                nb.append(("+", (cars[order[i - 1]][0] - c0).dot(a) / 2))
            if i < len(order) - 1:
                nb.append(("-", (cars[order[i + 1]][0] - c0).dot(a) / 2))
            info[cn] = {"ends": [round(e[1], 2) for e in nb], "panels": 0}
            key = f"led_{t}_{cn:02d}"
            if key not in ATL["items"]:
                continue
            lo = min([e for _t, e in nb if e < 0], default=-14.5)
            hi = max([e for _t, e in nb if e > 0], default=14.5)
            for s in (-1, 1):
                n_before = info[cn]["panels"]
                # dark runs along the car at window height: passenger windows come in rows, a door window stands alone
                ks = np.arange(lo - 1.0, hi + 1.0, 0.1)
                dark = []
                for k in ks:
                    p = c0 + a * float(k) + nrm * (s * 3.0)
                    r = S.cast((p.x, p.y, z_win), -nrm * s, 4.0)
                    dark.append(r is not None and darkm(r[2]))
                runs, k0 = [], None
                for k, dk in zip(ks, dark):
                    if dk and k0 is None:
                        k0 = float(k)
                    if not dk and k0 is not None:
                        runs.append((k0, float(k) - 0.1)); k0 = None
                if k0 is not None:
                    runs.append((k0, float(ks[-1])))
                for j, (r0, r1) in enumerate(runs):
                    gl = r0 - runs[j - 1][1] if j > 0 else 99
                    gr = runs[j + 1][0] - r1 if j < len(runs) - 1 else 99
                    kd = (r0 + r1) / 2
                    if min(gl, gr) < 1.2 or r1 - r0 > 0.6 or not (lo + 0.2 < kd < hi - 0.2):
                        continue
                    if not any(abs(kd - e) < 3.5 for _t, e in nb):      # crew door near a nose
                        continue
                    toward = -1 if kd > 0 else 1                         # towards the car centre
                    own = [rr for rr in runs if (rr[1] - rr[0]) > 0.3 and (rr[0] + rr[1]) / 2 * toward > kd * toward
                           and lo < (rr[0] + rr[1]) / 2 < hi]
                    if not own:
                        continue
                    w_edge = min(own, key=lambda rr: abs((rr[0] + rr[1]) / 2 - kd))
                    w_edge = w_edge[1] if toward < 0 else w_edge[0]
                    a0 = kd + toward * 0.62                              # door half width + jamb
                    a1 = w_edge - toward * 0.12
                    span = (a1 - a0) * toward
                    if span < 0.55:
                        continue
                    w = min(LED_W, span - 0.06)
                    x = (a0 + a1) / 2
                    p = c0 + a * x
                    done = False
                    for z in (z_win, z_win - 0.1, z_win + 0.1):
                        h = LED_H * w / LED_W
                        hits = []
                        for dx, dz in ((0, 0), (-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
                            q = p + a * dx + nrm * (s * 3.0)
                            hits.append(S.cast((q.x, q.y, z + dz), -nrm * s, 4.0))
                        if any(r is None or darkm(r[2]) for r in hits):
                            continue
                        C, N = fit_panel(hits, nrm * s)
                        led_at(mb, C, Z.cross(N), Z, N, key, w)
                        placed += 1
                        info[cn]["panels"] += 1
                        done = True
                        break
                    if not done:
                        REP["warnings"].append(f"N700 track {t} car {cn} side {s} door at {kd:.1f}: no clear body for the display")
                if info[cn]["panels"] == n_before:
                    big = [rr for rr in runs if (rr[1] - rr[0]) > 0.3 and lo < (rr[0] + rr[1]) / 2 < hi]
                    for _t, e in nb:
                        if not big:
                            break
                        edge = max(rr[1] for rr in big) if e > 0 else min(rr[0] for rr in big)
                        toward = -1 if e > 0 else 1
                        if (e - edge) * (-toward) < 1.8:
                            continue
                        x = edge - toward * (0.12 + LED_W / 2)
                        p = c0 + a * x
                        hits = []
                        for dx, dz in ((0, 0), (-LED_W / 2, -LED_H / 2), (LED_W / 2, -LED_H / 2), (LED_W / 2, LED_H / 2), (-LED_W / 2, LED_H / 2)):
                            q = p + a * dx + nrm * (s * 3.0)
                            hits.append(S.cast((q.x, q.y, z_win + dz), -nrm * s, 4.0))
                        if any(r is None or darkm(r[2]) for r in hits):
                            continue
                        C, N = fit_panel(hits, nrm * s)
                        led_at(mb, C, Z.cross(N), Z, N, key)
                        placed += 1
                        info[cn]["panels"] += 1
                        info[cn]["fallback"] = info[cn].get("fallback", 0) + 1
                        break
        # head / tail lamps
        lamps = n700_lamps(mb, S, cars, order)
        if mb.v:
            ob = mb.build(f"V6 train markings | Track {t} N700 side displays and lamps", col, list(MLIST))
            ob.parent = E
            ob.matrix_parent_inverse = Matrix.Identity(4)
            ob["V6_trains"] = True
        MLIST.clear()
        REP["n700"][f"track {t}"] = {"cars": len(cars), "led_panels": placed, "lamps": lamps,
                                     "panels_per_car": {k_: v["panels"] for k_, v in info.items()}}
        L.log("N700 track", t, placed, "panels", lamps)


def n700_lamps(mb, S, cars, order):
    """two lamp lenses per nose, just below the front corners of the windscreen (approximate)."""
    out = []
    for cn, sign, kind in ((order[0], 1, "head"), (order[-1], -1, "tail")):
        c0, a = cars[cn]
        ax = a * sign                                  # outwards along the train
        nrm = Z.cross(ax)
        # nose tip: furthest hit along the axis at coupler height
        tip = None
        for k in np.arange(16.0, 8.0, -0.05):
            p = c0 + ax * float(k)
            r = S.cast((p.x, p.y, 1.2), -ax, 1.0)
            if r is not None:
                tip = float(k) - r[3]
                break
        if tip is None:
            out.append({"car": cn, "kind": kind, "placed": 0})
            continue
        n = 0
        for s in (-1, 1):
            r = None
            for back in (2.4, 2.7, 2.1, 3.0):
                for zl in (1.72, 1.62, 1.82):
                    p = c0 + ax * (tip - back)
                    r = S.cast((p.x + nrm.x * s * 3.0, p.y + nrm.y * s * 3.0, zl), -nrm * s, 4.0)
                    if r is not None and r[2] != "Material.721":
                        break
                    r = None
                if r is not None:
                    break
            if r is None:
                continue
            loc, N = r[0], r[1].normalized()
            if N.dot(nrm * s) < 0:
                N = -N
            T = (ax - N * ax.dot(N)).normalized()    # along the surface towards the nose
            B = N.cross(T)
            if B.z < 0:
                B = -B
            w, h = 0.70, 0.17
            C = loc + N * 0.006
            cs = [C - T * w / 2 - B * h / 2, C + T * w / 2 - B * h / 2 * 0.6, C + T * w / 2 + B * h / 2 * 0.6, C - T * w / 2 + B * h / 2]
            rim = [C + (q - C) * 1.4 - N * 0.003 for q in cs]
            mb.add([tuple(q) for q in rim], [(0, 1, 2, 3) if (rim[1] - rim[0]).cross(rim[3] - rim[0]).dot(N) > 0 else (3, 2, 1, 0)], mi("lamp_rim"))
            mb.add([tuple(q) for q in cs], [(0, 1, 2, 3) if (cs[1] - cs[0]).cross(cs[3] - cs[0]).dot(N) > 0 else (3, 2, 1, 0)], mi(kind))
            n += 1
        out.append({"car": cn, "kind": kind, "placed": n, "tip_from_car_centre_m": round(tip, 2)})
    return out


def fix_floor_markers():
    """V5 numbered the 乗車位置目標 floor markers of the conventional lines from the north end, while the trains standing
    there (and the real Tokyo-station convention: Tokaido 1号車 at the Atami end, Green cars 4-5) count car 1 from the
    south end.  Renumber the markers n -> N + 1 - n so that marker and car agree; checked against the car instances."""
    out = {}
    for ob in bpy.data.objects:
        m = re.match(r"V5 platform \| Track (\d\d) door-position floor markers$", ob.name)
        if not m or ob.type != 'MESH' or int(m.group(1)) > 10:
            continue
        t = int(m.group(1))
        me = ob.data
        uvl = me.uv_layers.get("UVMap") or me.uv_layers[0]
        cells = []
        for poly in me.polygons:
            us = [uvl.data[li].uv.x for li in poly.loop_indices]
            vs = [uvl.data[li].uv.y for li in poly.loop_indices]
            cu, cv = int(min(us) * 4 + 1e-4), int(min(vs) * 4 + 1e-4)
            cells.append(cu + 4 * (3 - cv))
        insts = [o for o in bpy.data.objects if re.match(r"Track %02d car \d\d$" % t, o.name) and o.instance_type == 'COLLECTION']
        N = len(insts) if insts else max(cells) + 1
        mism = 0
        for poly, cell in zip(me.polygons, cells):
            n_new = N + 1 - (cell + 1)
            c2 = n_new - 1
            du = (c2 % 4 - cell % 4) / 4.0
            dv = -((c2 // 4) - (cell // 4)) / 4.0
            for li in poly.loop_indices:
                uvl.data[li].uv.x += du
                uvl.data[li].uv.y += dv
            if insts:
                c = ob.matrix_world @ poly.center
                near = min(insts, key=lambda o: (o.matrix_world.translation - c).length)
                if int(near.get("car_number", -1)) != n_new:
                    mism += 1
        me.update()
        ob["V6_renumbered_from_south"] = True
        out[f"track {t:02d}"] = {"markers": len(cells), "cars": N, "mismatch_with_train": mism if insts else None}
    REP["floor_markers"] = out
    L.log("floor markers renumbered", out)


def run():
    global MATS
    MATS = materials()
    commuter()
    e5()
    n700()
    fix_floor_markers()
    bpy.context.scene["V6_trains_summary"] = json.dumps({k: v for k, v in REP.items() if k.endswith("totals") or k in ("warnings", "floor_markers")}, ensure_ascii=False)
    L.log("warnings", len(REP["warnings"]), REP["warnings"][:20])
    if REPORT:
        json.dump(REP, open(REPORT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    if OUT:
        bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=True)
        L.log("saved", OUT)


run()
