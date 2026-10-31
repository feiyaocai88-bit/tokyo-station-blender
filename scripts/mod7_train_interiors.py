"""V7 module: passenger interiors for the commuter cars (E233-0/1000/3000, E235-0) and see-through side windows.

Round-7 feedback: "换成下载的开源列车模型我都同意". The interior comes from a downloaded CC BY model:
  "Subway_[interior]" by Comicaroid (@yuuuusukeeee), https://sketchfab.com/3d-models/subway-interior-b7f25426ac674a9291ba092fb9fe8406
  CC BY 4.0. File: scripts/assets/subway_interior_comicaroid.glb (the downloaded original, unmodified).
The model is a 17 m, 3-door Japanese commuter-car interior (longitudinal seats, straps, poles, racks, ceiling lights).
Here it is cut into end / door / seat-bay modules and re-assembled to the 4-door layout of each car body (doors at
x = +-2.3 and +-6.7 m), scaled to the body (inner half-width 1.40 m, floor 1.15 m above rail), and given scene
materials. The model's own outer shell, wall posters and door leaves are dropped: the existing car body provides those.
Side-wall lining, end walls and the cab partition are generated here. Window glass on the car bodies is changed to a
see-through glass, and the window back plates behind the glass are cut to frames.

usage: blender -b Tokyo_Station_V6.blend --python-exit-code 1 -P mod7_train_interiors.py -- out.blend [report.json]
"""
import sys, os, json, math
import bpy, bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v5lib as L

ASSET = os.path.join(HERE, "assets", "subway_interior_comicaroid.glb")
ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGV[0] if ARGV else None
REPORT = ARGV[1] if len(ARGV) > 1 else None
CREDIT = ('"Subway_[interior]" by Comicaroid (@yuuuusukeeee), '
          'https://sketchfab.com/3d-models/subway-interior-b7f25426ac674a9291ba092fb9fe8406 , CC BY 4.0')

# ---- source model frame (metres, glTF import, Z up)
SRC_YC, SRC_FLOOR = 9.08, -0.66
SRC_X0, SRC_X1 = -3.03, 14.03
SRC_SEG = {"endA": (-3.03, -1.04), "door0": (-1.04, 1.04), "bench1": (1.04, 4.46), "door1": (4.46, 6.54),
           "bench2": (6.54, 9.96), "door2": (9.96, 12.04), "endB": (12.04, 14.03)}
SRC_WALL_IN = (7.53, 10.64)          # inner faces of the side walls
# ---- target (car-master frame: x along the car, y across, z = 0 at rail top)
SY, SZ = 0.90, 0.868                 # SZ keeps the ceiling 5 cm under the roof at the side walls (roof z 3.636 at |y| 1.395)
FLOOR = 1.15
WALL_Y = 1.40                        # lining plane, 3 cm inside the window glass (|y| = 1.43)
DOOR_HALF = 0.82                     # half width of a door module (door 1.24 m + standing space)
DOOR_OPEN_HALF = 0.64                # half width of the door opening kept free of lining
END_GAP = 0.12                       # end wall inside the body end (|x| = 9.85)
CAB_PARTITION = 7.60                 # cab cars: passenger area ends here (cab at +x)
CEIL_SIDE_Z = FLOOR + (1.66 - SRC_FLOOR) * SZ      # 3.164: lower edge of the curved side ceiling
CEIL_TOP_Z = FLOOR + (2.14 - SRC_FLOOR) * SZ       # 3.580
CEIL_SIDE_Y = (SRC_YC - 8.13) * SY                 # 0.855

GLASS_NAME = "V7 | EMU side window glass (see-through)"
SKIP_MASTER_KEYS = ("Green",)        # Green cars keep dark glass (no interior of that type)


def src_to_target_yz(y, z):
    yy = (y - SRC_YC) * SY
    yy = max(-WALL_Y + 0.005, min(WALL_Y - 0.005, yy))
    return yy, FLOOR + (z - SRC_FLOOR) * SZ


# ------------------------------------------------------------------ materials
def glass_material():
    m = bpy.data.materials.get(GLASS_NAME)
    if m:
        return m
    m = bpy.data.materials.new(GLASS_NAME)
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    mix = nt.nodes.new("ShaderNodeMixShader")
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.22
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    tr.inputs["Color"].default_value = (0.70, 0.78, 0.75, 1.0)     # slight green tint of laminated glass
    gl = nt.nodes.new("ShaderNodeBsdfGlossy")
    gl.inputs["Roughness"].default_value = 0.03
    gl.inputs["Color"].default_value = (0.9, 0.92, 0.92, 1.0)
    nt.links.new(lw.outputs["Fresnel"], mix.inputs["Fac"])
    nt.links.new(tr.outputs["BSDF"], mix.inputs[1])
    nt.links.new(gl.outputs["BSDF"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    m.diffuse_color = (0.55, 0.65, 0.65, 0.35)
    return m


def interior_materials():
    P = L.principled
    mats = {
        "seat": P("V7 | interior seat moquette (from model)", (0.11, 0.22, 0.05), rough=0.9, spec=0.2),
        "wall": P("V7 | interior wall panel (warm white)", (0.78, 0.76, 0.70), rough=0.55),
        "white": P("V7 | interior white trim", (0.82, 0.82, 0.80), rough=0.45),
        "grey": P("V7 | interior grey trim", (0.42, 0.42, 0.42), rough=0.5),
        "steel": P("V7 | interior stainless poles and racks", (0.62, 0.62, 0.62), rough=0.28, metal=1.0),
        "dark": P("V7 | interior dark metal", (0.20, 0.20, 0.21), rough=0.4, metal=0.6),
        "floor": P("V7 | interior floor (grey)", (0.34, 0.35, 0.35), rough=0.6),
        "black": P("V7 | interior black (screens)", (0.02, 0.02, 0.02), rough=0.25),
        "light": P("V7 | interior ceiling light", (0.95, 0.95, 0.92), rough=0.4, emission=(1.0, 0.97, 0.92), strength=6.0),
        "glass": glass_material(),
    }
    mats["light"].cycles.emission_sampling = 'NONE'
    return mats


SRC_MAT = {"/color-fabric": "seat", "/color-body": "wall", "/color-white": "white", "マテリアル_2": "white",
           "/color-grey": "grey", "/metal-grey": "steel", "/metal-darkGrey": "dark", "/color-floor": "floor",
           "/color-blk": "black", "/Emissive": "light", "/glass": "glass"}


# ------------------------------------------------------------- source model
def load_source():
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=ASSET)
    new = [o for o in bpy.data.objects if o not in before]
    parts, dropped = [], {"shell": 0, "wall_flush": 0, "door_leaf": 0}
    for o in new:
        if o.type != 'MESH':
            continue
        mw = o.matrix_world
        verts = [mw @ v.co for v in o.data.vertices]
        lo = Vector((min(v.x for v in verts), min(v.y for v in verts), min(v.z for v in verts)))
        hi = Vector((max(v.x for v in verts), max(v.y for v in verts), max(v.z for v in verts)))
        span = hi - lo
        full = span.x > 8.0
        if full and span.z > 2.5:
            dropped["shell"] += 1
            continue
        if not full and span.z > 1.0 and (lo.y < SRC_WALL_IN[0] - 0.08 or hi.y > SRC_WALL_IN[1] + 0.08):
            dropped["door_leaf"] += 1          # door leaves / door-side panels in the wall plane
            continue
        if not full and span.y < 0.03 and (abs(lo.y - SRC_WALL_IN[0]) < 0.03 or abs(hi.y - SRC_WALL_IN[1]) < 0.03):
            dropped["wall_flush"] += 1         # posters and frames flush on the model's walls
            continue
        faces = []
        for p in o.data.polygons:
            mname = o.data.materials[p.material_index].name if o.data.materials else "/color-white"
            faces.append((list(p.vertices), SRC_MAT.get(mname, "white")))
        cx = (lo.x + hi.x) / 2
        seg = None
        if not full:
            for k, (a, b) in SRC_SEG.items():
                if a <= cx < b:
                    seg = k
                    break
            if seg is None:
                seg = "endA" if cx < SRC_X0 + 1 else "endB"
        parts.append(dict(name=o.name, full=full, seg=seg, verts=verts, faces=faces))
    for o in new:
        bpy.data.objects.remove(o, do_unlink=True)
    for me in [m for m in bpy.data.meshes if m.users == 0]:
        bpy.data.meshes.remove(me)
    L.log("interior source parts", len(parts), "dropped", dropped)
    return parts, dropped


# ------------------------------------------------------------ body analysis
def analyse_body(me):
    doors = sorted(set(round(p.center.x, 2) for p in me.polygons
                       if p.normal.z < -0.9 and abs(p.center.y) > 1.3 and p.center.z > 2.9
                       and "recessed room shadow" in me.materials[p.material_index].name and abs(p.center.x) < 7.5))
    front = [p.center.x for p in me.polygons if "glossy black front" in me.materials[p.material_index].name]
    cab = bool(front)
    x1 = CAB_PARTITION if cab else 9.85 - END_GAP
    x0 = -(9.85 - END_GAP)
    plates = []
    for p in me.polygons:
        mn = me.materials[p.material_index].name
        if "rubber" in mn and abs(p.normal.y) > 0.9 and p.area > 0.5:
            vs = [me.vertices[i].co for i in p.vertices]
            plates.append((min(v.x for v in vs), max(v.x for v in vs), min(v.z for v in vs), max(v.z for v in vs),
                           1 if p.center.y > 0 else -1))
    return dict(doors=doors, cab=cab, x0=x0, x1=x1, plates=plates)


# --------------------------------------------------------- interior builder
class Builder:
    def __init__(self, mats):
        self.keys = list(mats.keys())
        self.verts, self.faces, self.fmat = [], [], []

    def add(self, verts, faces):
        base = len(self.verts)
        self.verts.extend(verts)
        for f, k in faces:
            self.faces.append([base + i for i in f])
            self.fmat.append(self.keys.index(k))

    def quad(self, a, b, c, d, k):
        self.add([a, b, c, d], [([0, 1, 2, 3], k)])

    def mesh(self, name, mats):
        me = bpy.data.meshes.new(name)
        me.from_pydata([tuple(v) for v in self.verts], [], self.faces)
        for k in self.keys:
            me.materials.append(mats[k])
        me.polygons.foreach_set("material_index", self.fmat)
        me.validate(clean_customdata=False)
        me.update()
        return me


def layout(info):
    d = info["doors"]
    segs = []
    x = info["x0"]
    door_src = ["door0", "door1", "door2", "door1"]
    bench_src = ["bench1", "bench2", "bench1"]
    segs.append(("endA", x, d[0] - DOOR_HALF))
    for i, dc in enumerate(d):
        segs.append((door_src[i % 4], dc - DOOR_HALF, dc + DOOR_HALF))
        if i + 1 < len(d):
            segs.append((bench_src[i % 3], dc + DOOR_HALF, d[i + 1] - DOOR_HALF))
    tail = info["x1"] - (d[-1] + DOOR_HALF)
    if tail > 0.3:
        segs.append(("endB", d[-1] + DOOR_HALF, info["x1"]))
    return segs


def build_interior(name, info, parts, mats):
    B = Builder(mats)
    segs = layout(info)
    x0, x1 = info["x0"], info["x1"]
    for p in parts:
        if p["full"]:
            s0, s1, t0, t1 = SRC_X0, SRC_X1, x0, x1
            vs = []
            for v in p["verts"]:
                y, z = src_to_target_yz(v.y, v.z)
                vs.append(Vector((t0 + (v.x - s0) * (t1 - t0) / (s1 - s0), y, z)))
            B.add(vs, p["faces"])
    for key, t0, t1 in segs:
        s0, s1 = SRC_SEG[key]
        for p in parts:
            if p["full"] or p["seg"] != key:
                continue
            vs = []
            for v in p["verts"]:
                y, z = src_to_target_yz(v.y, v.z)
                vs.append(Vector((t0 + (v.x - s0) * (t1 - t0) / (s1 - s0), y, z)))
            B.add(vs, p["faces"])
    # side-wall lining: full wall minus door openings and window plates
    for side in (-1, 1):
        holes = [(dc - DOOR_OPEN_HALF, dc + DOOR_OPEN_HALF, FLOOR - 1, CEIL_SIDE_Z + 1) for dc in info["doors"]]
        holes += [(a - 0.005, b + 0.005, c - 0.005, e + 0.005) for a, b, c, e, s in info["plates"] if s == side]
        xs = sorted(set([x0, x1] + [min(max(h[0], x0), x1) for h in holes] + [min(max(h[1], x0), x1) for h in holes]))
        zs = sorted(set([FLOOR, CEIL_SIDE_Z] + [min(max(h[2], FLOOR), CEIL_SIDE_Z) for h in holes]
                        + [min(max(h[3], FLOOR), CEIL_SIDE_Z) for h in holes]))
        y = side * WALL_Y
        for i in range(len(xs) - 1):
            for j in range(len(zs) - 1):
                xa, xb, za, zb = xs[i], xs[i + 1], zs[j], zs[j + 1]
                if xb - xa < 1e-4 or zb - za < 1e-4:
                    continue
                cx, cz = (xa + xb) / 2, (za + zb) / 2
                if any(h[0] < cx < h[1] and h[2] < cz < h[3] for h in holes):
                    continue
                a, b, c, d = (Vector((xa, y, za)), Vector((xb, y, za)), Vector((xb, y, zb)), Vector((xa, y, zb)))
                if side < 0:      # normal towards the aisle (+y)
                    B.quad(a, d, c, b, "wall")
                else:
                    B.quad(a, b, c, d, "wall")
    # end walls / cab partition (hexagon following the ceiling profile), facing the aisle
    prof = [(-WALL_Y, FLOOR), (WALL_Y, FLOOR), (WALL_Y, CEIL_SIDE_Z), (CEIL_SIDE_Y, CEIL_TOP_Z),
            (-CEIL_SIDE_Y, CEIL_TOP_Z), (-WALL_Y, CEIL_SIDE_Z)]
    for x, sgn in ((x0 - 0.01, 1), (x1 + 0.01, -1)):
        vs = [Vector((x, y, z)) for y, z in prof]
        idx = list(range(6)) if sgn > 0 else list(reversed(range(6)))
        B.add(vs, [(idx, "wall")])
    if info["cab"]:      # dark window in the cab partition
        x = x1 + 0.005
        B.quad(Vector((x, -0.35, 2.15)), Vector((x, 0.35, 2.15)), Vector((x, 0.35, 2.95)), Vector((x, -0.35, 2.95)), "black")
    me = B.mesh("V7 interior | " + name, mats)
    return me, segs


def clamp_inside(ime, body_me):
    """Safety net: keep every interior vertex inside the body cross-section (4 cm under the roof, 2 cm inside the
    side wall), measured with rays from outside the body at that vertex's x."""
    from mathutils.bvhtree import BVHTree
    bvh = BVHTree.FromPolygons([v.co.copy() for v in body_me.vertices], [list(p.vertices) for p in body_me.polygons])
    moved = 0
    for v in ime.vertices:
        c = v.co
        top = bvh.ray_cast(Vector((c.x, c.y, 8.0)), Vector((0, 0, -1)), 6.0)[0]
        s = 1.0 if c.y >= 0 else -1.0
        side = None
        for dx in (0.0, 0.03, -0.03):     # door seams: retry beside the gap between the two door leaves
            side = bvh.ray_cast(Vector((c.x + dx, 3.0 * s, c.z)), Vector((0, -s, 0)), 3.0)[0]
            if side is not None and abs(side.y) > 1.3:
                break
        nz, ny = c.z, c.y
        if top is not None and c.z > top.z - 0.04:
            nz = top.z - 0.04
        if side is not None and abs(c.y) > abs(side.y) - 0.02:
            ny = s * (abs(side.y) - 0.02)
        if (nz, ny) != (c.z, c.y):
            v.co.z, v.co.y = nz, ny
            moved += 1
    ime.update()
    return moved


# ------------------------------------------------------------ body windows
def convert_windows(me, info, glass):
    """Glazing faces -> see-through glass; window back plates behind the glass -> frames (glass area cut out)."""
    if GLASS_NAME not in [m.name for m in me.materials if m]:
        me.materials.append(glass)
    gi = [m.name if m else "" for m in me.materials].index(GLASS_NAME)
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    names = [m.name if m else "" for m in me.materials]
    glazing, n_glass = [], 0
    for f in bm.faces:
        if "reflective dark glazing" in names[f.material_index] and abs(f.normal.y) > 0.9:
            c = f.calc_center_median()
            if info["x0"] - 0.1 < c.x < info["x1"] + 0.1:
                xs = [v.co.x for v in f.verts]; zs = [v.co.z for v in f.verts]
                glazing.append((min(xs), max(xs), min(zs), max(zs), c.y))
                f.material_index = gi
                n_glass += 1
    n_split, n_new = 0, 0
    for f in list(bm.faces):
        if "rubber" not in names[f.material_index] or abs(f.normal.y) < 0.9:
            continue
        c = f.calc_center_median()
        xs = [v.co.x for v in f.verts]; zs = [v.co.z for v in f.verts]
        r = (min(xs), max(xs), min(zs), max(zs))
        if abs(f.calc_area() - (r[1] - r[0]) * (r[3] - r[2])) > 0.01 * f.calc_area() + 1e-6:
            continue                     # only flat rectangular plates (n-gons with collinear vertices are fine)
        cover = [g for g in glazing if (g[4] > 0) == (c.y > 0) and abs(abs(g[4]) - abs(c.y)) < 0.012
                 and g[0] < r[1] and g[1] > r[0] and g[2] < r[3] and g[3] > r[2]]
        if not cover:
            continue
        gx = sorted(set([r[0], r[1]] + [min(max(v, r[0]), r[1]) for g in cover for v in (g[0], g[1])]))
        gz = sorted(set([r[2], r[3]] + [min(max(v, r[2]), r[3]) for g in cover for v in (g[2], g[3])]))
        y, mat, nrm = c.y, f.material_index, f.normal.copy()
        for i in range(len(gx) - 1):
            for j in range(len(gz) - 1):
                xa, xb, za, zb = gx[i], gx[i + 1], gz[j], gz[j + 1]
                if xb - xa < 1e-5 or zb - za < 1e-5:
                    continue
                cx, cz = (xa + xb) / 2, (za + zb) / 2
                if any(g[0] - 1e-5 <= cx <= g[1] + 1e-5 and g[2] - 1e-5 <= cz <= g[3] + 1e-5 for g in cover):
                    continue
                vs = [bm.verts.new((xa, y, za)), bm.verts.new((xb, y, za)), bm.verts.new((xb, y, zb)), bm.verts.new((xa, y, zb))]
                nf = bm.faces.new(vs if nrm.y < 0 else list(reversed(vs)))
                nf.material_index = mat
                n_new += 1
        bm.faces.remove(f)
        n_split += 1
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    me.update()
    return dict(glass_faces=n_glass, plates_cut=n_split, frame_faces=n_new)


# ---------------------------------------------------------------------- run
def run():
    mats = interior_materials()
    parts, dropped = load_source()
    hidden = L.collection("V7_Replaced_V6_hidden", hide_render=True)
    hidden.hide_viewport = True
    # collections used by the car instances, and the collections that directly hold a commuter body
    used = {}
    for ob in bpy.data.objects:
        if ob.instance_type == 'COLLECTION' and ob.instance_collection and ob.name.startswith("Track"):
            used.setdefault(ob.instance_collection.name, []).append(ob.name)
    holders = {}
    def walk(col):
        for o in col.objects:
            if o.type == 'MESH' and o.name.startswith("V5 one-piece body") and o.data.name.startswith("V5 one-piece body"):
                holders.setdefault(col.name, o)
        for ch in col.children:
            walk(ch)
    for cname in used:
        walk(bpy.data.collections[cname])
    report = {"credit": CREDIT, "dropped_source_objects": dropped, "bodies": {}, "holders": {}, "skipped": []}
    built = {}
    for cname, body in sorted(holders.items()):
        me = body.data
        if any(k in me.name for k in SKIP_MASTER_KEYS) or any(k in cname for k in SKIP_MASTER_KEYS):
            report["skipped"].append(cname)
            continue
        info = analyse_body(me)
        if len(info["doors"]) != 4:
            report["skipped"].append(cname + " (doors %s)" % info["doors"])
            continue
        if me.name not in built:
            keep = me.copy()
            keep.name = me.name + " [V6, before V7 windows]"
            ko = bpy.data.objects.new(keep.name, keep)
            hidden.objects.link(ko)
            ko.hide_render = ko.hide_viewport = True
            ko["V7_retired"] = True
            win = convert_windows(me, info, mats["glass"])
            ime, segs = build_interior(me.name.replace("V5 one-piece body | ", ""), info, parts, mats)
            win["interior_verts_clamped_under_roof"] = clamp_inside(ime, me)
            built[me.name] = ime
            report["bodies"][me.name] = dict(doors=info["doors"], cab=info["cab"], x0=info["x0"], x1=info["x1"],
                                            segments=[(k, round(a, 3), round(b, 3)) for k, a, b in segs],
                                            interior_verts=len(ime.vertices), interior_faces=len(ime.polygons), **win)
            L.log("body", me.name, win, "interior verts", len(ime.vertices))
        ime = built[me.name]
        io = bpy.data.objects.new("V7 interior | " + cname, ime)
        io["V7_interior_source"] = CREDIT
        bpy.data.collections[cname].objects.link(io)
        report["holders"][cname] = io.name
    # which instances now carry an interior
    with_int = []
    for cname, insts in used.items():
        col = bpy.data.collections[cname]
        if any(o.name.startswith("V7 interior |") for o in col.all_objects):
            with_int += insts
    report["instances_with_interior"] = len(with_int)
    report["instances_total_commuter"] = sum(len(v) for k, v in used.items() if "E5" not in k and "N700" not in k)
    sc = bpy.context.scene
    sc["V7_interiors_summary"] = json.dumps({k: report[k] for k in ("instances_with_interior", "instances_total_commuter", "skipped")})
    sc["V7_interior_credit"] = CREDIT
    return report


report = run()
L.log("instances with interior", report["instances_with_interior"], "of", report["instances_total_commuter"], "skipped", report["skipped"])
if REPORT:
    json.dump(report, open(REPORT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
if OUT:
    bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=True)
    L.log("saved", OUT)
