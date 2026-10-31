"""V5 module 4: platform furniture and people.
Adds to each of the 10 island platforms (straight central part only):
- JR-style station name boards (東京 / Tokyo, line-colour band, station-number tile) hung from the canopy, facing each track
- two departure indicators (発車標) under the canopy with lit LED rows
- back-to-back bench groups, vending machines, 3-way recycling bins, fire-extinguisher boxes on columns
- glass waiting rooms on the Shinkansen platforms
- instanced pedestrians (6 simple variants) on platforms and in the two dome halls
Positions avoid canopy columns, platform-door zones and the edge tactile strips. Layout is illustrative.
"""
import sys, os, math, json, random, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector, Matrix
import v5lib as L

CJK = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
CJK_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"


def srgb(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


LINES = {
    1: ("JC", "01", "#F15A22"), 2: ("JC", "01", "#F15A22"),
    3: ("JK", "26", "#00B2E5"), 6: ("JK", "26", "#00B2E5"),
    4: ("JY", "01", "#80C241"), 5: ("JY", "01", "#80C241"),
    7: ("JT", "01", "#F68B1E"), 8: ("JT", "01", "#F68B1E"), 9: ("JT", "01", "#F68B1E"), 10: ("JT", "01", "#F68B1E"),
}
SHINKANSEN_COLOUR = {14: "#0072BA", 15: "#0072BA", 16: "#0072BA", 17: "#0072BA", 18: "#0072BA", 19: "#0072BA",
                     20: "#009A44", 21: "#009A44", 22: "#009A44", 23: "#009A44"}


def text_mesh(body, size, font_path, extrude=0.003, res=4):
    cu = bpy.data.curves.new("V5_tmp_text", "FONT")
    cu.font = bpy.data.fonts.load(font_path, check_existing=True)
    cu.body = body
    cu.size = size
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    cu.resolution_u = res
    cu.extrude = extrude
    ob = bpy.data.objects.new("V5_tmp_text", cu)
    bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = ob.evaluated_get(dg).to_mesh()
    verts = [tuple(v.co) for v in me.vertices]
    faces = [tuple(p.vertices) for p in me.polygons]
    ob.evaluated_get(dg).to_mesh_clear()
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)
    return verts, faces


_TXT = {}


def add_text(mb, F, body, size, mat, font=CJK, dz=0.0):
    key = (body, size, font)
    if key not in _TXT:
        _TXT[key] = text_mesh(body, size, font)
    v, f = _TXT[key]
    mb.add([tuple(F @ Vector((x, y, z + dz))) for x, y, z in v], f, mat)


def board_frame(pos, facing_neg_y):
    if facing_neg_y:
        R = Matrix((Vector((1, 0, 0)), Vector((0, 0, 1)), Vector((0, -1, 0)))).transposed()
    else:
        R = Matrix((Vector((-1, 0, 0)), Vector((0, 0, 1)), Vector((0, 1, 0)))).transposed()
    return Matrix.Translation(pos) @ R.to_4x4()


NEIGHBOURS = {  # (north neighbour, south neighbour) shown on JR East boards
    "JC": ("神田 Kanda", None), "JK": ("神田 Kanda", "有楽町 Yūrakuchō"), "JY": ("神田 Kanda", "有楽町 Yūrakuchō"),
    "JT": ("上野 Ueno", "新橋 Shimbashi"),
}


def name_board(mb, pos, facing_neg_y, track, I, z_canopy):
    F = board_frame(pos, facing_neg_y)
    W, H = 1.90, 0.62
    L.box(mb, 0, 0, 0, W + 0.06, H + 0.06, 0.07, I["frame"], frame=F)
    L.box(mb, 0, 0, 0, W, H, 0.02, I["white"], frame=F @ Matrix.Translation((0, 0, 0.03)))
    face = F @ Matrix.Translation((0, 0, 0.041))
    key = f"line{track}"
    if track in LINES:
        code, num, col = LINES[track]
        add_text(mb, face @ Matrix.Translation((0.10, 0.235, 0)), "とうきょう", 0.060, I["black"])
        add_text(mb, face @ Matrix.Translation((0.10, 0.055, 0)), "東京", 0.25, I["black"], CJK_BOLD)
        add_text(mb, face @ Matrix.Translation((0.10, -0.135, 0)), "Tokyo", 0.085, I["black"])
        L.box(mb, 0, 0, 0, W, 0.11, 0.008, I[key], frame=face @ Matrix.Translation((0, -H / 2 + 0.055, 0)))
        north, south = NEIGHBOURS[code]
        # viewer's right is south when the board faces -Y (west edge), north when it faces +Y
        right, left = (south, north) if facing_neg_y else (north, south)
        if left:
            add_text(mb, face @ Matrix.Translation((-0.55, -H / 2 + 0.056, 0.006)), "← " + left, 0.05, I["white"])
        if right:
            add_text(mb, face @ Matrix.Translation((0.55, -H / 2 + 0.056, 0.006)), right + " →", 0.05, I["white"])
        L.box(mb, 0, 0, 0, 0.26, 0.26, 0.008, I[key], frame=face @ Matrix.Translation((-0.72, 0.06, 0)))
        L.box(mb, 0, 0, 0, 0.20, 0.20, 0.008, I["white"], frame=face @ Matrix.Translation((-0.72, 0.06, 0.004)))
        add_text(mb, face @ Matrix.Translation((-0.72, 0.105, 0.009)), code, 0.07, I["black"], CJK_BOLD)
        add_text(mb, face @ Matrix.Translation((-0.72, 0.015, 0.009)), num, 0.075, I["black"], CJK_BOLD)
    else:
        add_text(mb, face @ Matrix.Translation((0, 0.07, 0)), "東京", 0.27, I["black"], CJK_BOLD)
        add_text(mb, face @ Matrix.Translation((0, -0.15, 0)), "Tokyo", 0.095, I["black"])
        L.box(mb, 0, 0, 0, W, 0.06, 0.008, I[key], frame=face @ Matrix.Translation((0, -H / 2 + 0.03, 0)))
    # hangers to the canopy (z_canopy: height, or a function p -> fixing point for the Shinkansen roofs)
    for s in (-0.7, 0.7):
        p = F @ Vector((s, H / 2 + 0.03, 0))
        if callable(z_canopy):
            z_canopy(mb, p, I["frame"])
        else:
            L.box(mb, p.x, p.y, (p.z + z_canopy) / 2, 0.04, 0.04, z_canopy - p.z, I["frame"])


def roof_hanger(SR, isl, z_deck, conv_top):
    """Hanger rod from point p up to the Shinkansen roof (vertical, or inclined to the spine / edge beam)."""
    def hang(mb, p, mat):
        if SR is None:
            L.box(mb, p.x, p.y, (p.z + conv_top) / 2, 0.04, 0.04, conv_top - p.z, mat)
            return
        x2, y2, z2 = SR.hang_point(isl, p.x, p.y, z_deck)
        if z2 is None or z2 <= p.z + 0.05:
            return
        if math.hypot(x2 - p.x, y2 - p.y) < 0.03:
            L.box(mb, p.x, p.y, (p.z + z2) / 2, 0.04, 0.04, z2 - p.z, mat)
        else:
            L.tube(mb, [Vector((p.x, p.y, p.z)), Vector((x2, y2, z2))], 0.02, sides=6, mat=mat, smooth=False)
    return hang


def departure_board(mb, x, y, z, I, hang=None):
    L.box(mb, x, y, z, 0.16, 2.6, 0.62, I["frame"])
    rnd = random.Random(int(x * 7 + y * 13))
    for side in (-1, 1):
        L.box(mb, x + side * 0.081, y, z, 0.004, 2.48, 0.52, I["led_bg"])
        for row in range(3):
            zz = z + 0.17 - row * 0.17
            yy = -1.15
            while yy < 1.1:
                w = rnd.choice((0.07, 0.07, 0.07, 0.12, 0.05))
                mat = I["led_amber"] if (row == 0 or rnd.random() < 0.75) else I["led_green"]
                if rnd.random() > 0.12:
                    L.box(mb, x + side * 0.085, y + yy + w / 2, zz, 0.004, w, 0.09, mat)
                yy += w + 0.025
    for s in (-0.9, 0.9):
        if hang is not None:
            hang(mb, Vector((x, y + s, z + 0.31)), I["frame"])
        else:
            L.box(mb, x, y + s, (z + 0.31 + z + 1.0) / 2, 0.04, 0.04, 0.70, I["frame"])


def bench_pair(mb, x, y, z, I):
    L.box(mb, x, y, z + 0.30, 2.0, 0.10, 0.06, I["frame"])
    for sx in (-0.8, 0.8):
        L.box(mb, x + sx, y, z + 0.15, 0.08, 0.30, 0.30, I["frame"])
    for side in (-1, 1):
        for k in range(4):
            sx = x - 0.72 + k * 0.48
            L.box(mb, sx, y + side * 0.25, z + 0.42, 0.44, 0.42, 0.05, I["seat"])
            L.box(mb, sx, y + side * 0.05, z + 0.66, 0.44, 0.05, 0.42, I["seat"])


def vending_machine(mb, x, y, z, front_sign, I):
    L.box(mb, x, y, z + 0.915, 1.0, 0.72, 1.83, I["vm_body"])
    fy = y + front_sign * 0.361
    L.box(mb, x, fy, z + 1.30, 0.86, 0.01, 0.70, I["vm_glass"])
    for r in range(3):
        for c in range(6):
            L.box(mb, x - 0.33 + c * 0.13, fy + front_sign * 0.006, z + 1.05 + r * 0.24, 0.09, 0.006, 0.16, I[("can_a", "can_b", "can_c")[(r + c) % 3]])
    L.box(mb, x, fy + front_sign * 0.004, z + 0.82, 0.86, 0.01, 0.10, I["vm_buttons"])
    L.box(mb, x, fy + front_sign * 0.01, z + 0.36, 0.60, 0.02, 0.20, I["frame"])
    L.box(mb, x, fy, z + 1.78, 1.0, 0.012, 0.08, I["vm_red"])


def recycle_bin(mb, x, y, z, I):
    L.box(mb, x, y, z + 0.52, 1.20, 0.42, 1.04, I["bin"])
    for k, m in enumerate(("bin_a", "bin_b", "bin_c")):
        for side in (-1, 1):
            L.box(mb, x - 0.40 + k * 0.40, y + side * 0.212, z + 0.86, 0.26, 0.008, 0.10, I["frame"])
            L.box(mb, x - 0.40 + k * 0.40, y + side * 0.212, z + 0.70, 0.30, 0.008, 0.12, I[m])


def waiting_room(mb, x0, x1, y, w, z, I):
    h = 2.7
    L.box(mb, (x0 + x1) / 2, y, z + h + 0.05, x1 - x0 + 0.2, w + 0.2, 0.10, I["frame"])
    L.box(mb, (x0 + x1) / 2, y, z + 0.02, x1 - x0, w, 0.04, I["frame"])
    for side in (-1, 1):
        L.box(mb, (x0 + x1) / 2, y + side * w / 2, z + h / 2, x1 - x0, 0.03, h, I["glass"])
    for xx in (x0, x1):
        L.box(mb, xx, y, z + h / 2, 0.03, w, h, I["glass"])
    n = int((x1 - x0) / 1.2)
    for k in range(n + 1):
        xx = x0 + (x1 - x0) * k / n
        for side in (-1, 1):
            L.box(mb, xx, y + side * w / 2, z + h / 2, 0.06, 0.06, h, I["frame"])
    for side in (-1, 1):
        L.box(mb, (x0 + x1) / 2, y + side * w / 2, z + 1.0, x1 - x0, 0.05, 0.05, I["frame"])
    L.box(mb, x0 + 1.0, y, z + 0.45, 1.6, 0.5, 0.45, I["seat"])
    L.box(mb, x1 - 1.0, y, z + 0.45, 1.6, 0.5, 0.45, I["seat"])



def folded_plate_roof_material():
    """Platform canopies: profiled (folded-plate) steel roofing, ribs running across the platform."""
    name = "V5 | platform canopy folded-plate steel roofing"
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = 1.0 / 0.25
    nt.links.new(sep.outputs[0], mul.inputs[0])
    fr = nt.nodes.new("ShaderNodeMath"); fr.operation = 'PINGPONG'; fr.inputs[1].default_value = 0.5
    nt.links.new(mul.outputs[0], fr.inputs[0])
    sm = nt.nodes.new("ShaderNodeMath"); sm.operation = 'SMOOTH_MIN'
    sm.inputs[1].default_value = 0.32; sm.inputs[2].default_value = 0.08
    nt.links.new(fr.outputs[0], sm.inputs[0])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.8
    bump.inputs["Distance"].default_value = 0.05
    nt.links.new(sm.outputs[0], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    noise = nt.nodes.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 0.08
    nt.links.new(geo.outputs["Position"], noise.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.30, 0.32, 0.33, 1)
    ramp.color_ramp.elements[1].color = (0.40, 0.42, 0.43, 1)
    nt.links.new(noise.outputs["Fac"], ramp.inputs[0])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Metallic"].default_value = 0.35
    b.inputs["Roughness"].default_value = 0.45
    m.diffuse_color = (0.36, 0.38, 0.39, 1)
    return m


def reroof_canopies():
    slate = bpy.data.materials.get("V2 | natural slate with fine overlapping courses")
    new = folded_plate_roof_material()
    n = 0
    for o in bpy.data.objects:
        if o.type == 'MESH' and re.match(r"V3 platform canopy \d\d-\d\d", o.name):
            me = o.data
            for i, mm in enumerate(me.materials):
                if mm == slate:
                    me.materials[i] = new
                    n += 1
    return n

# --------------------------------------------------------------- pedestrians
def make_people_masters(pcol):
    coats = [("V5 | person coat navy", (0.03, 0.04, 0.07)), ("V5 | person coat charcoal", (0.05, 0.05, 0.055)),
             ("V5 | person coat beige", (0.42, 0.32, 0.20)), ("V5 | person shirt white", (0.75, 0.75, 0.73)),
             ("V5 | person coat olive", (0.13, 0.15, 0.08)), ("V5 | person coat burgundy", (0.25, 0.04, 0.05))]
    skin = L.principled("V5 | person skin", (0.55, 0.36, 0.25), rough=0.6)
    hair = L.principled("V5 | person hair", (0.015, 0.012, 0.01), rough=0.5)
    trouser = L.principled("V5 | person trousers", (0.03, 0.035, 0.04), rough=0.8)
    shoe = L.principled("V5 | person shoes", (0.02, 0.018, 0.016), rough=0.4)
    bag = L.principled("V5 | person bag", (0.09, 0.06, 0.04), rough=0.5)
    masters = []
    for i, (cn, cc) in enumerate(coats):
        coat = L.principled(cn, cc, rough=0.85)
        h = (1.58, 1.72, 1.66, 1.78, 1.62, 1.75)[i]
        s = h / 1.70
        mb = L.MeshBuilder()
        for side in (-1, 1):
            L.lathe(mb, [(0.0, 0.0), (0.06, 0.0), (0.065, 0.06), (0.0, 0.07)], (0.03 * side, side * 0.10 * s), segments=8, mat=4)
            L.lathe(mb, [(0.055 * s, 0.06), (0.065 * s, 0.45 * s), (0.08 * s, 0.82 * s), (0.0, 0.84 * s)], (0.0, side * 0.10 * s), segments=8, mat=2)
            L.tube(mb, [Vector((0.0, side * 0.24 * s, 1.40 * s)), Vector((0.02, side * 0.26 * s, 1.12 * s)), Vector((0.05, side * 0.25 * s, 0.88 * s))], 0.045 * s, sides=6, mat=0)
            L.lathe(mb, [(0.0, 0.83 * s), (0.04 * s, 0.84 * s), (0.04 * s, 0.88 * s), (0.0, 0.89 * s)], (0.05, side * 0.25 * s), segments=6, mat=1)
        L.lathe(mb, [(0.0, 0.78 * s), (0.17 * s, 0.80 * s), (0.18 * s, 1.05 * s), (0.20 * s, 1.36 * s), (0.15 * s, 1.44 * s), (0.06 * s, 1.47 * s), (0.0, 1.47 * s)],
                (0.0, 0.0), segments=10, mat=0)
        L.lathe(mb, [(0.0, 1.46 * s), (0.05 * s, 1.47 * s), (0.05 * s, 1.52 * s), (0.0, 1.53 * s)], (0.0, 0.0), segments=8, mat=1)
        head = [(0.0, 1.51 * s)] + [(0.105 * s * math.sin(math.pi * j / 8), 1.62 * s - 0.11 * s * math.cos(math.pi * j / 8)) for j in range(1, 8)] + [(0.0, 1.73 * s)]
        L.lathe(mb, head, (0.0, 0.0), segments=10, mat=1)
        hairp = [(0.0, 1.745 * s)] + [(0.112 * s * math.sin(math.pi * j / 10), 1.62 * s + 0.125 * s * math.cos(math.pi * j / 10)) for j in range(1, 6)]
        L.lathe(mb, hairp, (-0.01, 0.0), segments=10, mat=3)
        if i % 2 == 0:
            L.box(mb, 0.0, 0.30 * s, 0.95 * s, 0.30, 0.10, 0.25, 5)
        ob = mb.build(f"V5 pedestrian variant {i}", pcol, [coat, skin, trouser, hair, shoe, bag])
        masters.append(ob)
    return masters


def instance_person(col, master_col, name, x, y, z, rot):
    e = bpy.data.objects.new(name, None)
    e.instance_type = 'COLLECTION'
    e.instance_collection = master_col
    e.location = (x, y, z)
    e.rotation_euler = (0, 0, rot)
    col.objects.link(e)
    return e


# --------------------------------------------------------------------- main
def run():
    rnd = random.Random(20261029)
    here = os.path.dirname(os.path.abspath(__file__))
    def _find(fn):
        for c in (os.path.join(here, fn), os.path.join(here, "..", "inv", fn)):
            if os.path.exists(c):
                return c
        raise FileNotFoundError(fn)
    plat_json = json.load(open(_find("platforms.json")))
    cols_json = json.load(open(_find("platforms_cols.json")))["columns"]
    col = L.collection("V5_Platform_Furniture")
    pcol_root = L.collection("V5_People_instances")
    # people masters live in an excluded collection
    pm_col = bpy.data.collections.get("V5 pedestrian masters") or bpy.data.collections.new("V5 pedestrian masters")
    if pm_col.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(pm_col)
    masters = make_people_masters(pm_col)
    var_cols = []
    for i, m in enumerate(masters):
        vc = bpy.data.collections.get(f"V5 pedestrian {i}") or bpy.data.collections.new(f"V5 pedestrian {i}")
        for c in list(m.users_collection):
            c.objects.unlink(m)
        vc.objects.link(m)
        if vc.name not in pm_col.children:
            pm_col.children.link(vc)
        var_cols.append(vc)
    # exclude the masters from the view layer (instances still render)
    def find_lc(lc, name):
        if lc.collection.name == name:
            return lc
        for c in lc.children:
            r = find_lc(c, name)
            if r:
                return r
    lc = find_lc(bpy.context.view_layer.layer_collection, pm_col.name)
    if lc:
        lc.exclude = True

    I_mats = {
        "frame": L.principled("V5 | platform fittings dark grey", (0.07, 0.075, 0.08), rough=0.45, metal=0.5),
        "white": L.principled("V5 | sign face white", (0.82, 0.83, 0.82), rough=0.35),
        "black": L.principled("V5 | sign lettering black", (0.01, 0.01, 0.012), rough=0.4),
        "led_bg": L.principled("V5 | LED board black", (0.005, 0.005, 0.006), rough=0.3),
        "led_amber": L.principled("V5 | LED amber", (0.05, 0.02, 0.0), emission=(1.0, 0.42, 0.04), strength=5.0),
        "led_green": L.principled("V5 | LED green", (0.0, 0.05, 0.02), emission=(0.15, 1.0, 0.25), strength=4.0),
        "seat": L.principled("V5 | bench seat blue-grey", (0.10, 0.17, 0.26), rough=0.45),
        "vm_body": L.principled("V5 | vending machine white", (0.78, 0.78, 0.76), rough=0.35),
        "vm_red": L.principled("V5 | vending machine red band", (0.55, 0.02, 0.02), rough=0.35),
        "vm_glass": L.principled("V5 | vending display glass", (0.03, 0.035, 0.04), rough=0.08, emission=(0.9, 0.9, 0.85), strength=0.4),
        "vm_buttons": L.principled("V5 | vending buttons", (0.3, 0.3, 0.3), rough=0.3, emission=(0.6, 0.8, 1.0), strength=0.8),
        "can_a": L.principled("V5 | drink can red", (0.5, 0.04, 0.03), rough=0.3),
        "can_b": L.principled("V5 | drink can green", (0.05, 0.3, 0.08), rough=0.3),
        "can_c": L.principled("V5 | drink can blue", (0.04, 0.10, 0.4), rough=0.3),
        "bin": L.principled("V5 | recycling bin silver", (0.45, 0.47, 0.48), rough=0.35, metal=0.6),
        "bin_a": L.principled("V5 | bin label blue", (0.02, 0.15, 0.55), rough=0.4),
        "bin_b": L.principled("V5 | bin label yellow", (0.75, 0.55, 0.02), rough=0.4),
        "bin_c": L.principled("V5 | bin label green", (0.05, 0.40, 0.10), rough=0.4),
        "glass": L.principled("V5 | waiting room glass", (0.30, 0.38, 0.40), rough=0.05, spec=0.8),
        "fire": L.principled("V5 | fire extinguisher box red", (0.55, 0.03, 0.02), rough=0.4),
    }
    for t in list(LINES) + list(SHINKANSEN_COLOUR):
        hexc = LINES[t][2] if t in LINES else SHINKANSEN_COLOUR[t]
        I_mats[f"line{t}"] = L.principled(f"V5 | line colour {hexc}", srgb(hexc), rough=0.4)
    mats = list(dict.fromkeys(I_mats.values()))
    idx = {k: mats.index(v) for k, v in I_mats.items()}

    summary = {}
    people = 0
    roofs = json.loads(bpy.context.scene.get("V5_shinkansen_roofs", "{}"))
    SR = None
    if roofs:
        import mod_shinkansen_roofs as SR
    for deck, d in plat_json.items():
        m = re.search(r"Platform (\d\d)-(\d\d)", deck)
        tw, te = int(m.group(1)), int(m.group(2))
        z = d["ztop"]
        # platforms follow the real (curved, tapering) alignment: centre line and width per X
        sl = sorted(d["slices"])
        sx = [s_[0] for s_ in sl]
        s_c = [(s_[1] + s_[2]) / 2 for s_ in sl]
        s_w = [s_[2] - s_[1] for s_ in sl]

        def ycw(x):
            import numpy as _np
            return float(_np.interp(x, sx, s_c)), float(_np.interp(x, sx, s_w))
        yc, w = ycw(0.0)
        wide = [x_ for x_, w_ in zip(sx, s_w) if w_ >= 6.5]
        xmin, xmax = max(min(wide) + 6, -150), min(max(wide) - 6, 150)

        def on_platform(xq, yq, pad=0.5):
            c_, w_ = ycw(xq)
            return abs(yq - c_) < w_ / 2 + pad
        colx = sorted(set(round((min(c[0] for c in bb) + max(c[0] for c in bb)) / 2, 2) for bb in cols_json
                          if on_platform((min(c[0] for c in bb) + max(c[0] for c in bb)) / 2,
                                         (min(c[1] for c in bb) + max(c[1] for c in bb)) / 2)))
        z_canopy = z + (4.04 if z < 9 else 4.04)
        isl = f"{tw:02d}-{te:02d}"
        shin = SR is not None and isl in roofs
        hang = None
        col_off = 0.2                       # fire-extinguisher box offset from the column centre
        if shin:
            # V5.2 Shinkansen roofs: the V3 columns are retired, the roof columns stand on the centre line
            colx = sorted(set(c[0] for c in roofs[isl]["columns"] if on_platform(c[0], c[1])))
            hang = roof_hanger(SR, isl, z, z_canopy)
            z_canopy = hang
            col_off = 0.33
        mb = L.MeshBuilder()
        taken = []

        def free(x0, x1):
            if x0 < xmin or x1 > xmax or (-16 < x1 and x0 < 6):
                return False
            if any(abs(cx - (x0 + x1) / 2) < (x1 - x0) / 2 + 0.8 for cx in colx):
                return False
            return not any(a < x1 + 0.5 and x0 - 0.5 < b for a, b in taken)

        def place(xc, half, tries=40):
            for k in range(tries):
                for sgn in (1, -1):
                    xx = xc + sgn * k * 1.5
                    if free(xx - half, xx + half):
                        taken.append((xx - half, xx + half))
                        return xx
            return None

        n_boards = 0
        for xc in (-120, -60, 40, 105):
            xx = place(xc, 1.0)
            if xx is None:
                continue
            c_, w_ = ycw(xx)
            name_board(mb, Vector((xx, c_ - w_ / 2 + 1.15, z + 2.55)), True, tw, idx, z_canopy)
            name_board(mb, Vector((xx, c_ + w_ / 2 - 1.15, z + 2.55)), False, te, idx, z_canopy)
            n_boards += 2
        n_dep = 0
        for xc in (-32, 22):
            xx = place(xc, 0.2)
            if xx is not None:
                departure_board(mb, xx, ycw(xx)[0], z + 2.95, idx, hang)
                n_dep += 1
        n_bench = 0
        for xc in (-95, -45, 60, 90):
            xx = place(xc, 1.1)
            if xx is not None:
                bench_pair(mb, xx, ycw(xx)[0], z, idx)
                n_bench += 1
        n_vm = 0
        for xc, sgn in ((-75, 1), (75, -1)):
            xx = place(xc, 1.2)
            if xx is not None:
                vending_machine(mb, xx - 0.52, ycw(xx)[0], z, sgn, idx)
                vending_machine(mb, xx + 0.52, ycw(xx)[0], z, sgn, idx)
                n_vm += 2
        for xc in (-20 - 12, 120):
            xx = place(xc, 0.7)
            if xx is not None:
                recycle_bin(mb, xx, ycw(xx)[0], z, idx)
        if tw >= 14:
            xx = place(30, 4.0)
            if xx is not None:
                c_, w_ = ycw(xx)
                waiting_room(mb, xx - 3.6, xx + 3.6, c_, min(3.4, w_ - 3.6), z, idx)
        # fire-extinguisher boxes on some canopy columns
        for k, cx in enumerate(colx):
            if k % 2 == 0 and xmin < cx < xmax:
                L.box(mb, cx + col_off, ycw(cx)[0], z + 0.55, 0.12, 0.30, 0.55, idx["fire"])
        ob = mb.build(f"V5 platform {tw:02d}-{te:02d} furniture and signs", col, mats)
        # pedestrians
        np_ = 0
        for k in range(34):
            for attempt in range(30):
                xx = rnd.uniform(xmin + 2, xmax - 2)
                c_, w_ = ycw(xx)
                yy = c_ + rnd.uniform(-(w_ / 2 - 1.35), (w_ / 2 - 1.35))
                if any(abs(cx - xx) < 0.6 for cx in colx) and abs(yy - c_) < 0.6:
                    continue
                if any(a - 0.4 < xx < b + 0.4 and abs(yy - c_) < 1.4 for a, b in taken):
                    continue
                rot = rnd.choice((0.0, math.pi)) + rnd.uniform(-0.5, 0.5) if rnd.random() < 0.7 else rnd.uniform(0, 2 * math.pi)
                instance_person(pcol_root, var_cols[rnd.randrange(len(var_cols))], f"V5 person P{tw:02d} {k:02d}", xx, yy, z, rot)
                np_ += 1
                break
        people += np_
        summary[f"{tw}-{te}"] = {"boards": n_boards, "departure_boards": n_dep, "bench_pairs": n_bench,
                                 "vending_machines": n_vm, "people": np_, "verts": len(ob.data.vertices)}
        L.log(deck, summary[f"{tw}-{te}"])
    # people in the two dome halls (inside the gate line)
    for tag, (cx, cy) in (("S", L.SOUTH_DOME), ("N", L.NORTH_DOME)):
        for k in range(14):
            a = rnd.uniform(0, 2 * math.pi)
            r = rnd.uniform(1.5, 7.0)
            xx, yy = cx + r * math.cos(a), cy + r * math.sin(a)
            if yy > cy + 5.0:
                continue
            instance_person(pcol_root, var_cols[rnd.randrange(len(var_cols))], f"V5 person dome {tag} {k:02d}", xx, yy, 0.13, rnd.uniform(0, 2 * math.pi))
            people += 1
    summary["people_total"] = people
    summary["canopy_slots_reroofed"] = reroof_canopies()
    return summary


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    bpy.ops.wm.open_mainfile(filepath=src, load_ui=False, use_scripts=False)
    info = run()
    bpy.context.scene["V5_platform_summary"] = json.dumps(info)
    bpy.ops.wm.save_as_mainfile(filepath=dst, compress=True)
    print("SAVED", dst)
