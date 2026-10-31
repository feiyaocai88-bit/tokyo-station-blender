"""V5 module 1: north/south dome roofs.
- Upper dome rebuilt as an octagonal curved dome reaching ~34.8 m (JR East: max height approx. 34.8 m excl. finial)
  with lantern and finial/spire to 46.1 m (JR East: approx. 46.1 m incl. finial).
- Dome roofs re-covered with fish-scale slate (restoration spec: dome roofs gyorin-buki).
- 8 round dormers rebuilt on the new surface; copper hip rolls and base gutter.
"""
import sys, os, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector, Matrix
import v5lib as L
import v5mats as M

T22 = math.tan(math.radians(22.5))
C22 = math.cos(math.radians(22.5))

# ---- profile (apothem a, z) of the new upper dome
Z_BASE, A_LIP = 26.80, 9.92
A_ELL, Z_ELL, H_ELL, A_TOP = 9.70, 27.10, 6.55, 1.30


def dome_profile(n=40):
    prof = [(A_LIP, Z_BASE), (9.86, 26.92), (9.76, 27.03)]
    phimax = math.acos(A_TOP / A_ELL)
    for i in range(n + 1):
        f = i / n
        phi = phimax * (1 - (1 - f) ** 1.15)
        prof.append((A_ELL * math.cos(phi), Z_ELL + H_ELL * math.sin(phi)))
    return prof


def apothem_at(z):
    if z <= Z_ELL:
        return A_ELL
    s = (z - Z_ELL) / H_ELL
    return A_ELL * math.sqrt(max(0.0, 1 - s * s))


def face_frame(cx, cy, theta, ap, z):
    """Local frame on a dome face: x along face (horizontal), y up, z outward normal."""
    n = Vector((math.cos(theta), math.sin(theta), 0))
    t = Vector((-math.sin(theta), math.cos(theta), 0))
    up = Vector((0, 0, 1))
    o = Vector((cx, cy, z)) + n * ap
    R = Matrix((t, up, n)).transposed().to_4x4()
    return Matrix.Translation(o) @ R


def build_upper_shell(tag, cx, cy, col, slate):
    prof = dome_profile()
    # arc length along the face centre line
    S = [0.0]
    for k in range(1, len(prof)):
        S.append(S[-1] + math.hypot(prof[k][0] - prof[k - 1][0], prof[k][1] - prof[k - 1][1]))
    verts, faces, uvs = [], [], []
    for k in range(8):
        th = math.radians(45 * k)
        n = Vector((math.cos(th), math.sin(th)))
        t = Vector((-math.sin(th), math.cos(th)))
        base = len(verts)
        for (a, z) in prof:
            hw = a * T22
            for sgn in (-1, 1):
                p = Vector((cx, cy)) + n * a + t * (sgn * hw)
                verts.append((p.x, p.y, z))
        for i in range(len(prof) - 1):
            a0, b0 = base + 2 * i, base + 2 * i + 1
            a1, b1 = a0 + 2, b0 + 2
            faces.append((a0, b0, b1, a1))
            hw0, hw1 = prof[i][0] * T22, prof[i + 1][0] * T22
            uvs.append([(-hw0, S[i]), (hw0, S[i]), (hw1, S[i + 1]), (-hw1, S[i + 1])])
    # small flat top ring under the lantern collar
    ob = L.mesh_object(f"V5 {tag} dome curved octagonal slate shell", verts, faces, col, mats=[slate], uvs=uvs, smooth=True)
    ob["V5_top_z"] = prof[-1][1]
    return ob, prof


def build_ribs_and_gutter(tag, cx, cy, mb, prof, mat_cu):
    # hip rolls at the 8 corners
    for k in range(8):
        ang = math.radians(45 * k + 22.5)
        d = Vector((math.cos(ang), math.sin(ang), 0))
        path = []
        for (a, z) in prof[1:]:
            r = a / C22 + 0.035
            path.append(Vector((cx, cy, z + 0.02)) + d * r)
        L.tube(mb, path, 0.075, sides=8, mat=mat_cu)
    # copper eaves gutter (half-round approximated by a tube) around the dome base
    ring = []
    for k in range(9):
        ang = math.radians(45 * k + 22.5)
        ring.append(Vector((cx + math.cos(ang) * (A_LIP + 0.06) / C22, cy + math.sin(ang) * (A_LIP + 0.06) / C22, Z_BASE + 0.02)))
    L.tube(mb, ring, 0.11, sides=10, mat=mat_cu)


def build_dormers(tag, cx, cy, mb, mats):
    """8 round dormers (oeil-de-boeuf), one per face, copper-framed."""
    i_cu, i_glass, i_dark, i_bar = mats
    zc = 29.15
    ap_w = apothem_at(zc) + 0.30
    for k in range(8):
        th = math.radians(45 * k)
        F = face_frame(cx, cy, th, ap_w, zc)
        # body cylinder going back into the roof (axis = local z / outward normal)
        L.lathe(mb, [(0.80, -2.6), (0.80, -0.02)], (0, 0), segments=24, mat=i_cu, frame=F, smooth=True)
        # dark reveal disc behind glass and the glass itself
        L.lathe(mb, [(0.0, -0.10), (0.60, -0.10)], (0, 0), segments=24, mat=i_dark, frame=F, smooth=False)
        L.lathe(mb, [(0.0, -0.04), (0.60, -0.04)], (0, 0), segments=24, mat=i_glass, frame=F, smooth=False)
        # thick moulded copper surround (ring with a front bead)
        L.lathe(mb, [(0.58, -0.05), (0.58, 0.10), (0.64, 0.16), (0.76, 0.16), (0.86, 0.10), (0.90, 0.0), (0.90, -0.05)],
                (0, 0), segments=28, mat=i_cu, frame=F, smooth=True)
        # glazing bars: inner ring + cross
        L.lathe(mb, [(0.28, -0.03), (0.28, 0.0), (0.32, 0.0), (0.32, -0.03)], (0, 0), segments=20, mat=i_bar, frame=F, smooth=False)
        L.box(mb, 0, 0, 0, 0.035, 1.18, 0.05, mat=i_bar, frame=F @ Matrix.Translation((0, 0, -0.02)))
        L.box(mb, 0, 0, 0, 1.18, 0.035, 0.05, mat=i_bar, frame=F @ Matrix.Translation((0, 0, -0.02)))
        # eyebrow hood: arc of copper over the ring + keystone
        arc = []
        for j in range(15):
            a = math.radians(15 + 150 * j / 14)
            arc.append(F @ Vector((0.98 * math.cos(a), 0.98 * math.sin(a), 0.10)))
        L.tube(mb, arc, 0.065, sides=8, mat=i_cu)
        L.box(mb, 0, 0, 0, 0.20, 0.30, 0.22, mat=i_cu, frame=F @ Matrix.Translation((0, 0.98, 0.10)))
        # small scroll-like side blocks at the springing
        for s in (-1, 1):
            L.box(mb, 0, 0, 0, 0.16, 0.24, 0.20, mat=i_cu, frame=F @ Matrix.Translation((s * 0.94, -0.12, 0.08)))


def build_lantern_and_spire(tag, cx, cy, mb, mats):
    i_cu, i_dark, i_spire = mats
    oct_phase = math.radians(22.5)
    def octo(profile, mat, smooth=False):
        # octagonal lathe: 8 segments with corners at 22.5deg; r given as apothem
        prof = [(r / C22, z) for r, z in profile]
        L.lathe(mb, prof, (cx, cy), segments=8, mat=mat, smooth=smooth, phase=oct_phase, cap_top=True, cap_bottom=True)
    z0 = A_TOP_Z = None
    top = Z_ELL + H_ELL * math.sin(math.acos(A_TOP / A_ELL))  # ~33.59
    octo([(1.46, top - 0.10), (1.46, top + 0.10), (1.36, top + 0.16)], i_cu)          # collar
    octo([(1.08, top + 0.10), (1.08, 34.30)], i_cu)                                     # lantern body
    octo([(1.24, 34.28), (1.24, 34.40)], i_cu)                                          # lantern cornice
    # louvred openings on each lantern face + corner pilasters
    for k in range(8):
        th = math.radians(45 * k)
        F = face_frame(cx, cy, th, 1.08, (top + 34.28) / 2)
        L.box(mb, 0, 0, 0, 0.46, 0.44, 0.06, mat=i_dark, frame=F)
        for j in range(4):
            L.box(mb, 0, 0, 0, 0.46, 0.035, 0.05, mat=i_cu, frame=F @ Matrix.Translation((0, -0.16 + 0.105 * j, 0.03)))
        ang = th + math.radians(22.5)
        L.box(mb, cx + math.cos(ang) * 1.15, cy + math.sin(ang) * 1.15, (top + 34.30) / 2, 0.16, 0.16, 34.30 - top, mat=i_cu, rotz=ang)
    # ogee cap, neck, orb, collar and spire (round)
    L.lathe(mb, [(1.18, 34.40), (1.05, 34.50), (0.80, 34.60), (0.50, 34.68), (0.28, 34.75), (0.16, 34.80),
                 (0.12, 34.90), (0.12, 34.97)], (cx, cy), segments=20, mat=i_cu, smooth=True)
    orb = [(0.0, 34.95)] + [(0.30 * math.sin(math.pi * j / 12), 35.25 - 0.30 * math.cos(math.pi * j / 12)) for j in range(1, 12)] + [(0.0, 35.55)]
    L.lathe(mb, orb, (cx, cy), segments=20, mat=i_cu, smooth=True)
    L.lathe(mb, [(0.13, 35.52), (0.20, 35.60), (0.20, 35.66), (0.13, 35.74)], (cx, cy), segments=16, mat=i_cu, smooth=True)
    spire = [(0.11, 35.72)]
    for z, r in ((37.0, 0.09), (37.12, 0.16), (37.26, 0.09), (39.2, 0.07), (39.3, 0.12), (39.42, 0.07),
                 (41.8, 0.05), (41.88, 0.085), (41.98, 0.05), (45.2, 0.028), (46.10, 0.006)):
        spire.append((r, z))
    L.lathe(mb, spire, (cx, cy), segments=12, mat=i_spire, smooth=True)
    return top


def retire_v4_dome_parts(tag):
    pats = [f"{tag} dome flattened curved dome", f"V3 {tag} thin slate laps flattened curved dome",
            f"{tag} dome broad copper rib", f"{tag} dome attached oval dormer housing", f"{tag} dome dormer crown",
            f"{tag} dome oval copper flashing", f"{tag} dome oval roof glazing", f"V3 {tag} oval window fine copper rim",
            f"{tag} dome spire base", f"{tag} dome slender finial",
            f"V3 {tag} thin slate laps lower slate shoulder"]
    n = 0
    for o in list(bpy.data.objects):
        base = o.name.split(".")[0] if o.name[-4:-3] == "." and o.name[-3:].isdigit() else o.name
        if base in pats and not o.get("V5_retired"):
            L.retire(o); n += 1
    return n


def reslate_skirt(tag, slate):
    o = bpy.data.objects.get(f"{tag} dome faceted lower roof revised")
    me = o.data
    if slate.name not in [m.name for m in me.materials]:
        me.materials.append(slate)
    idx = [m.name for m in me.materials].index(slate.name)
    L.set_face_slope_uvs(me, "V5 slope UV")
    cnt = 0
    for p in me.polygons:
        if p.normal.z > 0.25:
            p.material_index = idx; cnt += 1
    return cnt


def run():
    col = L.collection("V5_Architecture_DomeRoofs")
    slate = M.fish_scale_slate()
    cu = M.copper()
    glass = bpy.data.materials["V2 | glazing 0"]
    dark = bpy.data.materials["V2 | recessed room shadow"]
    bar = bpy.data.materials["V2 | patinated bronze frames"]
    spire_m = M.copper("V5 | dark copper finial and lightning spire", base=(0.10, 0.085, 0.07), patina=(0.08, 0.12, 0.11), patina_amt=0.3)
    summary = {}
    for tag, (cx, cy) in (("SOUTH", L.SOUTH_DOME), ("NORTH", L.NORTH_DOME)):
        retired = retire_v4_dome_parts(tag)
        shell, prof = build_upper_shell(tag, cx, cy, col, slate)
        mb = L.MeshBuilder()
        build_ribs_and_gutter(tag, cx, cy, mb, prof, 0)
        mb.build(f"V5 {tag} dome copper hip rolls and eaves gutter", col, [cu])
        mb = L.MeshBuilder()
        build_dormers(tag, cx, cy, mb, (0, 1, 2, 3))
        dorm = mb.build(f"V5 {tag} dome eight round copper dormers", col, [cu, glass, dark, bar])
        mb = L.MeshBuilder()
        top = build_lantern_and_spire(tag, cx, cy, mb, (0, 1, 2))
        lan = mb.build(f"V5 {tag} dome lantern orb and spire to 46.1m", col, [cu, dark, spire_m])
        skirt_faces = reslate_skirt(tag, slate)
        zmax = max((lan.matrix_world @ v.co).z for v in lan.data.vertices)
        summary[tag] = {"retired_v4_objects": retired, "shell_top_z": round(top, 3), "lantern_cap_z": 34.80,
                        "spire_tip_z": round(zmax, 3), "skirt_faces_reslated": skirt_faces,
                        "dormers": 8, "hip_rolls": 8}
        L.log(tag, summary[tag])
    return summary


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    bpy.ops.wm.open_mainfile(filepath=src, load_ui=False, use_scripts=False)
    s = run()
    bpy.context.scene["V5_domes_summary"] = json.dumps(s)
    bpy.ops.wm.save_as_mainfile(filepath=dst, compress=True)
    print("SAVED", dst)
