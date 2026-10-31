"""V5 module 2: rotunda interiors of the north and south domes.
Documented content (JR East 2011 attachment, Tokyo Station City):
- 8 eagles at the octagon corners below the dome ceiling, wingspan ~2.1 m, facing left
- 8 of 12 zodiac reliefs at the 8 corners by compass direction: ox NNE, tiger ENE, dragon ESE, snake SSE,
  goat SSW, monkey WSW, dog WNW, boar NNW (rat/rabbit/horse/rooster omitted), grey-green background
- 16 clematis flower reliefs around the central ceiling ornament
- helmet-shaped (kabuto) keystones; egg-yolk ("kiran-iro") plaster ceiling in three graded tones
Everything else (gallery tiers, opening sizes, floor, gates, lighting) is an interpretive estimate.
"""
import sys, os, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector, Matrix, Euler
import v5lib as L
import v5mats as M

C22 = math.cos(math.radians(22.5))
T22 = math.tan(math.radians(22.5))
A = 10.0                 # interior apothem (20 m span)
W = A * T22              # face half width 4.142
FLOOR = 0.13
Z_CORN_BOT, Z_CORN_TOP = 16.1, 16.9
Z_DOME0, DOME_R, DOME_RISE = 17.5, 9.4, 6.2
EMOJI_FONT = os.path.join(bpy.utils.system_resource('DATAFILES', path="fonts"), "NotoEmoji-VariableFont_wght.woff2")

# compass bearing (deg, clockwise from north) -> model angle; model: north=-X, east=+Y
def bearing_to_model(b):
    return math.radians(180.0 - b)

ZODIAC = [("ox", 22.5, "\U0001F402"), ("tiger", 67.5, "\U0001F405"), ("dragon", 112.5, "\U0001F409"),
          ("snake", 157.5, "\U0001F40D"), ("goat", 202.5, "\U0001F410"), ("monkey", 247.5, "\U0001F412"),
          ("dog", 292.5, "\U0001F415"), ("boar", 337.5, "\U0001F417")]

EAGLE = [(0.12, 0.25), (0.5, 0.55), (0.85, 0.63), (1.05, 0.50), (0.92, 0.31), (0.96, 0.18), (0.82, 0.19), (0.85, 0.06),
         (0.70, 0.09), (0.71, -0.04), (0.56, 0.01), (0.53, -0.12), (0.40, -0.06), (0.30, -0.20), (0.15, -0.15),
         (0.12, -0.45), (0.22, -0.75), (0.08, -0.70), (0.0, -0.86), (-0.08, -0.70), (-0.22, -0.75), (-0.12, -0.45),
         (-0.15, -0.15), (-0.30, -0.20), (-0.40, -0.06), (-0.53, -0.12), (-0.56, 0.01), (-0.71, -0.04), (-0.70, 0.09),
         (-0.85, 0.06), (-0.82, 0.19), (-0.96, 0.18), (-0.92, 0.31), (-1.05, 0.50), (-0.85, 0.63), (-0.5, 0.55),
         (-0.12, 0.25), (-0.10, 0.40), (-0.17, 0.48), (-0.29, 0.50), (-0.36, 0.45), (-0.27, 0.42), (-0.20, 0.42),
         (-0.06, 0.48), (0.06, 0.41)]


def face_in(cx, cy, th, ap=A, z=0.0):
    """Interior face frame: x along the face, y up, z pointing into the hall."""
    n = Vector((math.cos(th), math.sin(th), 0))
    t = Vector((-math.sin(th), math.cos(th), 0))
    R = Matrix((-t, Vector((0, 0, 1)), -n)).transposed().to_4x4()
    return Matrix.Translation(Vector((cx, cy, z)) + n * ap) @ R


def arch_points(w, spring, rad, segs=16, close=True, y0=None):
    """Rectangle-plus-semicircle outline (CCW) centred on x=0; bottom at y0."""
    pts = [(-w / 2, y0), (w / 2, y0)] if close else []
    pts.append((w / 2, spring))
    for i in range(1, segs):
        a = math.pi * i / segs
        pts.append((rad * math.cos(a), spring + rad * math.sin(a)))
    pts.append((-w / 2, spring))
    return pts


def arch_path(F, w, y0, spring, rad, z, segs=20):
    p = [F @ Vector((w / 2, y0, z)), F @ Vector((w / 2, spring, z))]
    for i in range(1, segs):
        a = math.pi * i / segs
        p.append(F @ Vector((rad * math.cos(a), spring + rad * math.sin(a), z)))
    p += [F @ Vector((-w / 2, spring, z)), F @ Vector((-w / 2, y0, z))]
    return p


def glyph_mesh(char, size, depth):
    cu = bpy.data.curves.new("V5_tmp_glyph", "FONT")
    cu.font = bpy.data.fonts.load(EMOJI_FONT, check_existing=True)
    cu.body = char
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    cu.resolution_u = 3
    cu.extrude = depth / 2
    ob = bpy.data.objects.new("V5_tmp_glyph", cu)
    bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = ob.evaluated_get(dg).to_mesh()
    dims = max(ob.dimensions.x, ob.dimensions.y) or 1.0
    s = size / dims
    verts = [(v.co.x * s, v.co.y * s, (v.co.z + depth / 2)) for v in me.vertices]
    faces = [tuple(p.vertices) for p in me.polygons]
    ob.evaluated_get(dg).to_mesh_clear()
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)
    return verts, faces


def rosette(mb, F, r, petals, i_relief, depth=0.06):
    """Flower relief: centre boss + elliptical petals, in local XY of frame F (z = out of surface)."""
    L.lathe(mb, [(0.0, depth * 2.2), (r * 0.22, depth * 1.8), (r * 0.30, 0.0)], (0, 0), segments=14, mat=i_relief, frame=F)
    for k in range(petals):
        a = 2 * math.pi * k / petals
        Fp = F @ Matrix.Rotation(a, 4, 'Z') @ Matrix.Translation((r * 0.58, 0, 0))
        ell = [(r * 0.42 * math.cos(2 * math.pi * j / 12), r * 0.20 * math.sin(2 * math.pi * j / 12)) for j in range(12)]
        L.prism(mb, ell, 0.0, depth, mat=i_relief, frame=Fp)


def build_one(tag, cx, cy, col, mats, cams):
    (i_wall, i_relief, i_stone, i_dark, i_glass, i_frame, i_zbg, i_floor, i_gate, i_gate_top, i_lamp, i_ceiling) = range(12)
    mb = L.MeshBuilder()
    # ---- floor
    L.lathe(mb, [(0.0, FLOOR), (A / C22, FLOOR)], (cx, cy), segments=8, mat=i_floor, smooth=False, phase=math.radians(22.5))
    L.lathe(mb, [(A / C22 - 0.9, FLOOR + 0.005), (A / C22 - 0.3, FLOOR + 0.005)], (cx, cy), segments=8, mat=i_stone, smooth=False, phase=math.radians(22.5))
    L.lathe(mb, [(2.6, FLOOR + 0.006), (3.0, FLOOR + 0.006)], (cx, cy), segments=32, mat=i_stone, smooth=False)
    for k in range(8):
        th = math.radians(45 * k)
        F = face_in(cx, cy, th)
        # wall panel
        mb.add([tuple(F @ Vector(p)) for p in [(-W, FLOOR, 0), (W, FLOOR, 0), (W, Z_CORN_TOP, 0), (-W, Z_CORN_TOP, 0)]],
               [(0, 1, 2, 3)], i_wall)
        # stone wainscot left/right of the ground-floor opening
        for s in (-1, 1):
            xa, xb = sorted((s * 2.35, s * (W - 0.3)))
            L.box(mb, 0, 0, 0, xb - xa, 1.05, 0.08, mat=i_stone, frame=F @ Matrix.Translation(((xa + xb) / 2, FLOOR + 0.525, 0.04)))
        # ground floor opening (entrance doors on the plaza side, passages elsewhere)
        entrance = k in (5, 6, 7)
        L.prism(mb, arch_points(4.0, 3.6, 2.0, close=True, y0=FLOOR), 0.01, 0.03, mat=(i_glass if entrance else i_dark), frame=F)
        L.tube(mb, arch_path(F, 4.25, FLOOR, 3.6, 2.125, 0.10), 0.13, sides=8, mat=i_relief)
        if entrance:
            for x in (-1.0, 0.0, 1.0):
                L.box(mb, 0, 0, 0, 0.08, 3.5, 0.06, mat=i_frame, frame=F @ Matrix.Translation((x, FLOOR + 1.75, 0.05)))
            L.box(mb, 0, 0, 0, 4.0, 0.10, 0.06, mat=i_frame, frame=F @ Matrix.Translation((0, 3.0, 0.05)))
        # string courses
        for z0, h, d in ((5.85, 0.30, 0.22), (10.75, 0.30, 0.22)):
            L.box(mb, 0, 0, 0, 2 * W, h, d, mat=i_relief, frame=F @ Matrix.Translation((0, z0 + h / 2, d / 2)))
        # first floor (2F): two arched windows, sills, railing
        for xc in (-1.55, 1.55):
            Fw = F @ Matrix.Translation((xc, 0, 0))
            L.prism(mb, arch_points(1.5, 8.6, 0.75, close=True, y0=6.5), 0.01, 0.03, mat=i_glass, frame=Fw)
            L.tube(mb, arch_path(Fw, 1.7, 6.5, 8.6, 0.85, 0.09), 0.09, sides=8, mat=i_relief)
            L.box(mb, 0, 0, 0, 0.05, 2.8, 0.05, mat=i_frame, frame=Fw @ Matrix.Translation((0, 7.9, 0.04)))
            L.box(mb, 0, 0, 0, 1.5, 0.05, 0.05, mat=i_frame, frame=Fw @ Matrix.Translation((0, 8.6, 0.04)))
        L.box(mb, 0, 0, 0, 5.0, 0.14, 0.42, mat=i_relief, frame=F @ Matrix.Translation((0, 6.43, 0.21)))
        railing(mb, F, -2.4, 2.4, 6.5, 7.45, 0.36, i_relief)
        # second floor (3F): big face arch with corridor window and balustrade
        spring, rad = 12.2, W - 0.55
        L.tube(mb, arch_path(F, 2 * rad, 11.15, spring, rad, 0.12, segs=28), 0.16, sides=8, mat=i_relief)
        L.prism(mb, arch_points(4.0, 13.4, 2.0, close=True, y0=11.4), 0.01, 0.03, mat=i_glass, frame=F)
        L.tube(mb, arch_path(F, 4.2, 11.4, 13.4, 2.1, 0.08), 0.08, sides=8, mat=i_frame)
        for x in (-1.0, 0.0, 1.0):
            hgt = 13.4 + math.sqrt(max(0.0, 2.0 ** 2 - x * x)) - 11.4
            L.box(mb, 0, 0, 0, 0.06, hgt, 0.05, mat=i_frame, frame=F @ Matrix.Translation((x, 11.4 + hgt / 2, 0.05)))
        L.box(mb, 0, 0, 0, 4.0, 0.06, 0.05, mat=i_frame, frame=F @ Matrix.Translation((0, 13.4, 0.05)))
        L.box(mb, 0, 0, 0, 5.4, 0.16, 0.48, mat=i_relief, frame=F @ Matrix.Translation((0, 11.02, 0.24)))
        railing(mb, F, -2.6, 2.6, 11.1, 12.05, 0.44, i_relief)
        # kabuto (helmet) keystone at the arch crown
        kz = spring + rad
        Fk = F @ Matrix.Translation((0, kz, 0.0))
        L.prism(mb, [(-0.30, -0.35), (0.30, -0.35), (0.40, 0.55), (-0.40, 0.55)], 0.0, 0.36, mat=i_relief, frame=Fk)
        Fh = Fk @ Matrix.Translation((0, 0.12, 0.36)) @ Matrix.Rotation(math.radians(-90), 4, 'X')
        L.lathe(mb, [(0.0, 0.0), (0.42, 0.0), (0.44, 0.04), (0.30, 0.06), (0.30, 0.16), (0.24, 0.28), (0.12, 0.34), (0.0, 0.36)],
                (0, 0), segments=14, mat=i_relief, frame=Fh)          # bowl + brim, projecting into the hall
        for s in (-1, 1):                                              # kuwagata (crest horns)
            L.tube(mb, [Fk @ Vector((s * 0.06, 0.32, 0.72)), Fk @ Vector((s * 0.20, 0.62, 0.70)), Fk @ Vector((s * 0.30, 0.86, 0.62))], 0.035, sides=6, mat=i_relief)
        # wall sconces either side of the ground floor opening
        for s in (-1, 1):
            L.box(mb, 0, 0, 0, 0.22, 0.45, 0.16, mat=i_lamp, frame=F @ Matrix.Translation((s * 3.3, 4.6, 0.12)))
    # ---- corners: pilasters, capitals, zodiac medallions
    zod = {}
    for name, bearing, ch in ZODIAC:
        zod[round(math.degrees(bearing_to_model(bearing)) % 360, 1)] = (name, ch)
    for k in range(8):
        thc = math.radians(22.5 + 45 * k)
        rc = A / C22
        d = Vector((math.cos(thc), math.sin(thc), 0))
        base = Vector((cx, cy, 0)) + d * (rc - 0.32)
        L.box(mb, base.x, base.y, (FLOOR + 12.0) / 2, 0.64, 1.15, 12.0 - FLOOR, mat=i_relief, rotz=thc)
        L.box(mb, base.x - d.x * 0.08, base.y - d.y * 0.08, 12.1, 0.85, 1.4, 0.32, mat=i_relief, rotz=thc)
        L.box(mb, base.x, base.y, (12.25 + Z_CORN_BOT) / 2, 0.64, 1.15, Z_CORN_BOT - 12.25, mat=i_wall, rotz=thc)
        L.box(mb, base.x, base.y, 1.0, 0.75, 1.3, 1.75, mat=i_stone, rotz=thc)
        # zodiac medallion in the spandrel at the corner, facing the hall centre
        name, ch = zod[round(math.degrees(thc) % 360, 1)]
        Fm = Matrix.Translation(Vector((cx, cy, 14.55)) + d * (rc - 0.66)) @ \
            Matrix((-Vector((-d.y, d.x, 0)), Vector((0, 0, 1)), -d)).transposed().to_4x4()
        L.lathe(mb, [(0.0, 0.0), (0.92, 0.0), (0.92, 0.10), (0.80, 0.16), (0.70, 0.16), (0.70, 0.08)],
                (0, 0), segments=32, mat=i_relief, frame=Fm, smooth=True)
        L.lathe(mb, [(0.0, 0.06), (0.71, 0.06)], (0, 0), segments=32, mat=i_zbg, frame=Fm, smooth=False)
        gv, gf = glyph_mesh(ch, 1.05, 0.07)
        Fg = Fm @ Matrix.Translation((0, 0, 0.07))
        mb.add([tuple(Fg @ Vector(v)) for v in gv], gf, i_relief)
        cams.setdefault("zodiac", []).append({"animal": name, "model_angle_deg": round(math.degrees(thc) % 360, 1)})
        # eagle on the pendentive above the corner, facing the centre, leaning back with the vault
        Fe = Matrix.Translation(Vector((cx, cy, Z_CORN_TOP + 0.35)) + d * (rc - 1.25)) @ \
            Matrix((-Vector((-d.y, d.x, 0)), Vector((0, 0, 1)), -d)).transposed().to_4x4() @ Matrix.Rotation(math.radians(28), 4, 'X')
        L.prism(mb, EAGLE, 0.0, 0.16, mat=i_relief, frame=Fe)
        L.lathe(mb, [(0.0, 0.16), (0.16, 0.16), (0.14, 0.30), (0.0, 0.34)], (0, 0), segments=10, mat=i_relief,
                frame=Fe @ Matrix.Translation((0, 0.05, 0)) @ Matrix.Scale(1.0, 4, (0, 0, 1)))
        L.box(mb, 0, 0, 0, 0.22, 0.75, 0.12, mat=i_relief, frame=Fe @ Matrix.Translation((0, -0.05, 0.22)))
    # ---- main cornice ring (octagonal), dentils
    prof = [(A, Z_CORN_BOT), (A - 0.22, Z_CORN_BOT + 0.12), (A - 0.22, Z_CORN_BOT + 0.36), (A - 0.55, Z_CORN_BOT + 0.52),
            (A - 0.60, Z_CORN_TOP), (A, Z_CORN_TOP)]
    L.lathe(mb, [(r / C22, z) for r, z in prof], (cx, cy), segments=8, mat=i_relief, smooth=False, phase=math.radians(22.5))
    for k in range(8):
        th = math.radians(45 * k)
        F = face_in(cx, cy, th)
        for j in range(15):
            x = -W + 0.55 + j * (2 * W - 1.1) / 14
            L.box(mb, 0, 0, 0, 0.14, 0.16, 0.30, mat=i_relief, frame=F @ Matrix.Translation((x, Z_CORN_BOT + 0.05, 0.15)))
    # ---- pendentive ring from octagon (z=16.9) up to the round dome base (z=17.5)
    seg = 48
    pv, pf = [], []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        nearest = round((a) / (math.pi / 4)) * (math.pi / 4)
        ro = (A - 0.6) / math.cos(a - nearest)
        pv.append((cx + ro * math.cos(a), cy + ro * math.sin(a), Z_CORN_TOP))
        pv.append((cx + DOME_R * math.cos(a), cy + DOME_R * math.sin(a), Z_DOME0))
    for i in range(seg):
        j = (i + 1) % seg
        pf.append((2 * i, 2 * j, 2 * j + 1, 2 * i + 1))
    mb.add(pv, pf, i_wall)
    # ---- dome ceiling with ribs, clematis ring and central ornament
    prof = []
    for i in range(33):
        phi = (math.pi / 2) * i / 32
        prof.append((max(DOME_R * math.cos(phi), 0.0), Z_DOME0 + DOME_RISE * math.sin(phi)))
    L.lathe(mb, prof, (cx, cy), segments=64, mat=i_ceiling, smooth=True)

    def dome_point(r):
        phi = math.acos(min(1.0, r / DOME_R))
        return Z_DOME0 + DOME_RISE * math.sin(phi), phi

    for k in range(8):
        thc = math.radians(22.5 + 45 * k)
        path = []
        for r in [9.35 - 0.2 * j for j in range(36)]:
            if r < 2.7:
                break
            z, _ = dome_point(r)
            path.append(Vector((cx + (r - 0.02) * math.cos(thc), cy + (r - 0.02) * math.sin(thc), z - 0.03)))
        L.tube(mb, path, 0.16, sides=8, mat=i_relief)
    for ring_r, dz in ((2.75, 0.0), (5.6, 0.0)):
        z, _ = dome_point(ring_r)
        path = [Vector((cx + (ring_r - 0.02) * math.cos(2 * math.pi * i / 64), cy + (ring_r - 0.02) * math.sin(2 * math.pi * i / 64), z - 0.03)) for i in range(65)]
        L.tube(mb, path, 0.12, sides=8, mat=i_relief)
    rr = 3.85
    for i in range(16):
        a = 2 * math.pi * (i + 0.5) / 16
        z, phi = dome_point(rr)
        pos = Vector((cx + rr * math.cos(a), cy + rr * math.sin(a), z))
        nrm = -Vector((math.cos(a) * math.cos(phi) / DOME_R, math.sin(a) * math.cos(phi) / DOME_R, math.sin(phi) / DOME_RISE)).normalized()
        q = nrm.to_track_quat('Z', 'Y')
        Ff = Matrix.Translation(pos + nrm * 0.02) @ q.to_matrix().to_4x4()
        rosette(mb, Ff, 0.42, 6, i_relief, depth=0.07)
    ztop, _ = dome_point(0.01)
    Fc = Matrix.Translation((cx, cy, ztop - 0.04)) @ Matrix.Rotation(math.pi, 4, 'X')
    rosette(mb, Fc, 1.25, 12, i_relief, depth=0.12)
    L.lathe(mb, [(0.0, ztop - 0.10), (0.30, ztop - 0.25), (0.42, ztop - 0.60), (0.30, ztop - 0.95), (0.0, ztop - 1.05)],
            (cx, cy), segments=16, mat=i_lamp, smooth=True)
    # ---- automatic ticket gates on the track (east, +Y) side
    for j in range(9):
        x = cx - 4.0 + j * 1.0
        L.box(mb, x, cy + 6.3, FLOOR + 0.52, 0.24, 1.6, 1.04, mat=i_gate)
        L.box(mb, x, cy + 6.3, FLOOR + 1.06, 0.26, 1.62, 0.05, mat=i_gate_top)
        L.box(mb, x, cy + 5.55, FLOOR + 0.98, 0.20, 0.06, 0.10, mat=i_lamp)
    ob = mb.build(f"V5 {tag} dome rotunda interior (reliefs, galleries, gates)", col, mats)
    return ob


def railing(mb, F, x0, x1, z0, z1, proud, mat):
    L.box(mb, 0, 0, 0, x1 - x0, 0.10, 0.20, mat=mat, frame=F @ Matrix.Translation(((x0 + x1) / 2, z1 - 0.05, proud)))
    L.box(mb, 0, 0, 0, x1 - x0, 0.10, 0.20, mat=mat, frame=F @ Matrix.Translation(((x0 + x1) / 2, z0 + 0.05, proud)))
    n = int((x1 - x0) / 0.2)
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        L.box(mb, 0, 0, 0, 0.08, z1 - z0 - 0.2, 0.08, mat=mat, frame=F @ Matrix.Translation((x, (z0 + z1) / 2, proud)))



def hollow_octagonal_slabs(tag, cx, cy, col, inner_apothem=10.7):
    """V3 modelled the dome string courses as solid octagonal prisms (16 verts) that fill the hall.
    Replace each with a ring of the same outer outline so the rotunda is open."""
    made = []
    for o in list(bpy.data.objects):
        nm = o.name
        if not nm.startswith(f"{tag} dome octagonal ring") or o.get("V5_retired") or o.type != 'MESH':
            continue
        me = o.data
        if len(me.vertices) != 16:
            continue
        ws = [o.matrix_world @ v.co for v in me.vertices]
        zs = sorted(set(round(w.z, 4) for w in ws))
        z0, z1 = zs[0], zs[-1]
        bot = sorted([w for w in ws if abs(w.z - z0) < 1e-3], key=lambda w: math.atan2(w.y - cy, w.x - cx))
        if len(bot) != 8:
            continue
        verts, faces = [], []
        # outer ring from the original vertices, inner ring scaled to the requested apothem
        ap_out = sum(((bot[i] + bot[(i + 1) % 8]) / 2 - Vector((cx, cy, z0))).length for i in range(8)) / 8
        k = inner_apothem / ap_out
        for z in (z0, z1):
            for w in bot:
                verts.append((w.x, w.y, z))
            for w in bot:
                verts.append((cx + (w.x - cx) * k, cy + (w.y - cy) * k, z))
        def vi(level, inner, i):
            return level * 16 + inner * 8 + (i % 8)
        for i in range(8):
            faces.append((vi(1, 0, i), vi(1, 0, i + 1), vi(1, 1, i + 1), vi(1, 1, i)))   # top
            faces.append((vi(0, 0, i + 1), vi(0, 0, i), vi(0, 1, i), vi(0, 1, i + 1)))   # bottom
            faces.append((vi(0, 0, i), vi(0, 0, i + 1), vi(1, 0, i + 1), vi(1, 0, i)))   # outer
            faces.append((vi(0, 1, i + 1), vi(0, 1, i), vi(1, 1, i), vi(1, 1, i + 1)))   # inner
        new = L.mesh_object(nm + " | V5 hollow ring", verts, faces, o.users_collection[0], mats=list(me.materials))
        L.retire(o)
        made.append(new.name)
    return made

def add_lights(tag, cx, cy, col):
    made = []
    for k in range(8):
        a = math.radians(45 * k)
        ld = bpy.data.lights.new(f"V5 {tag} dome cove uplight {k}", 'AREA')
        ld.shape = 'RECTANGLE'; ld.size = 3.2; ld.size_y = 0.35
        ld.energy = 260.0; ld.color = (1.0, 0.86, 0.66)
        lo = bpy.data.objects.new(ld.name, ld)
        lo.location = (cx + 9.0 * math.cos(a), cy + 9.0 * math.sin(a), Z_CORN_TOP + 0.05)
        lo.rotation_euler = Euler((math.radians(150), 0, a + math.pi / 2), 'XYZ')
        lo.visible_camera = False
        col.objects.link(lo); made.append(lo.name)
    for z, e in ((6.0, 1300.0), (12.5, 900.0)):
        ld = bpy.data.lights.new(f"V5 {tag} dome hall fill {z}", 'POINT')
        ld.energy = e; ld.color = (1.0, 0.9, 0.75); ld.shadow_soft_size = 1.5
        lo = bpy.data.objects.new(ld.name, ld); lo.location = (cx, cy, z); lo.visible_camera = False
        col.objects.link(lo); made.append(lo.name)
    return made


def add_camera(name, loc, target, lens, col):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens; cd.clip_start = 0.1; cd.clip_end = 400
    co = bpy.data.objects.new(name, cd)
    co.location = loc
    co.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    col.objects.link(co)
    return co


def run():
    col = L.collection("V5_Architecture_DomeInteriors")
    camcol = L.collection("V5_Review_Cameras")
    mats = [
        L.principled("V5 | rotunda ivory plaster wall", (0.80, 0.75, 0.62), rough=0.78),
        L.principled("V5 | rotunda cream relief plaster", (0.88, 0.84, 0.72), rough=0.6),
        L.principled("V5 | rotunda warm stone", (0.50, 0.45, 0.37), rough=0.55),
        bpy.data.materials["V2 | recessed room shadow"],
        L.principled("V5 | rotunda gallery glass", (0.10, 0.12, 0.12), rough=0.08, spec=0.6),
        bpy.data.materials["V2 | patinated bronze frames"],
        L.principled("V5 | zodiac relief grey-green ground", (0.30, 0.37, 0.33), rough=0.7),
        L.principled("V5 | rotunda stone floor", (0.46, 0.43, 0.38), rough=0.35),
        L.principled("V5 | ticket gate light grey", (0.70, 0.72, 0.73), rough=0.35, metal=0.2),
        L.principled("V5 | ticket gate dark top", (0.04, 0.045, 0.05), rough=0.3),
        L.principled("V5 | warm lamp diffuser", (1.0, 0.88, 0.70), rough=0.4, emission=(1.0, 0.82, 0.58), strength=6.0),
        ceiling_material(),
    ]
    info = {"zodiac": []}
    for tag, (cx, cy) in (("SOUTH", L.SOUTH_DOME), ("NORTH", L.NORTH_DOME)):
        cams = {}
        rings = hollow_octagonal_slabs(tag, cx, cy, col)
        ob = build_one(tag, cx, cy, col, mats, cams)
        lights = add_lights(tag, cx, cy, col)
        info[tag] = {"object": ob.name, "verts": len(ob.data.vertices), "lights": len(lights), "zodiac": cams.get("zodiac"),
                     "hollowed_string_course_slabs": rings}
        L.log(tag, info[tag]["verts"], "verts")
    add_camera("V5 09 SOUTH DOME rotunda interior", (107.0, -6.6, 1.55), (107.0, 3.0, 15.5), 15.0, camcol)
    add_camera("V5 10 SOUTH DOME ceiling (look up)", (107.0, 0.2, 1.6), (107.0, 0.42, 30.0), 12.0, camcol)
    return info


def ceiling_material():
    name = "V5 | egg-yolk plaster ceiling, three graded tones"
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = Z_DOME0
    mr.inputs["From Max"].default_value = Z_DOME0 + DOME_RISE
    nt.links.new(sep.outputs[2], mr.inputs["Value"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = 'CONSTANT'
    cr = ramp.color_ramp
    cr.elements[0].position = 0.0; cr.elements[0].color = (0.66, 0.40, 0.09, 1)
    cr.elements[1].position = 0.38; cr.elements[1].color = (0.76, 0.52, 0.16, 1)
    e = cr.elements.new(0.72); e.color = (0.85, 0.66, 0.28, 1)
    nt.links.new(mr.outputs["Result"], ramp.inputs[0])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.8
    m.diffuse_color = (0.84, 0.64, 0.27, 1)
    m["V5_note"] = "Kiran-iro (egg-yolk) lime plaster in three graded tones, dark to light (restoration report); hues estimated."
    return m


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    bpy.ops.wm.open_mainfile(filepath=src, load_ui=False, use_scripts=False)
    info = run()
    bpy.context.scene["V5_dome_interior_summary"] = json.dumps(info)
    bpy.ops.wm.save_as_mainfile(filepath=dst, compress=True)
    print("SAVED", dst)
