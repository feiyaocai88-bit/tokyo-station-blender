"""V5 module 3: rolling-stock detail pass.
Adds detail to the MASTER car collections (each is instanced along the tracks), so every instance updates.
- commuter cars (E233-0/1000/3000, E235): curved roof skin + drip gutters (E233 masters), AC base frame and side louvres,
  window rubber gaskets, door step plates, gangway bellows and drawbar couplers, detailed underfloor equipment,
  bogie side-frame plates, axle-box covers, axle beams, tread-brake units, traction motors on intermediate (M) masters,
  cab skirt plates, tail lamps, grab rails, run-number display, roof antennas, lit destination LEDs
- E5: window gaskets, door step plates, bogie axle-box covers/axle beams, yaw dampers, roof antennas
- V3 simple single-arm pantographs on tracks 1/3/4/5 replaced by copies of the detailed V4 pantograph
Dimensions are scale-model estimates from the public type drawings/photos; not manufacturer CAD.
"""
import sys, os, math, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector, Matrix
import v5lib as L

COMMUTER_CAB = ["E233-0 style cab | procedural", "E233-1000 style cab | procedural", "E233-3000 style cab | procedural", "V3 E235-0 cab"]
COMMUTER_MID = ["E233-0 style ordinary car | procedural", "E233-1000 style intermediate | procedural",
                "E233-3000 style intermediate | procedural", "V3 E235-0 intermediate"]
GREEN = ["E233-0 style Green car | procedural", "V4_Train_Green_E233_3000_car_04", "V4_Train_Green_E233_3000_car_05"]
E5 = ["V4_Train_E5_car_01"] + [f"V3 E5 car {i:02d}" for i in range(2, 10)] + ["V4_Train_E5_car_10"]
GLASS_KEYS = ("passenger window", "passenger glazing", "door glass", "door glazing", "driver side window",
              "driver door window", "driver window", "double deck window", "door narrow glass")


def bbox(o):
    ws = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return Vector([min(w[i] for w in ws) for i in range(3)]), Vector([max(w[i] for w in ws) for i in range(3)])


def parts(col, key):
    return [o for o in col.objects if key in o.name and not o.get("V5_retired")]


def axle_xs(col):
    xs = sorted(round((bbox(o)[0].x + bbox(o)[1].x) / 2, 3) for o in parts(col, "axle shaft"))
    return xs


def bogies(col):
    xs = axle_xs(col)
    out = []
    for i in range(0, len(xs) - 1, 2):
        out.append(((xs[i] + xs[i + 1]) / 2, abs(xs[i + 1] - xs[i]), (xs[i], xs[i + 1])))
    return out


def shell_extent(col):
    best = None
    for o in col.objects:
        if any(k in o.name for k in ("stainless shell", "common stainless profile", "green white pink shell", "shell_with_lamp_pockets",
                                     "V5 one-piece body")):
            mn, mx = bbox(o)
            if best is None or (mx.x - mn.x) > (best[1].x - best[0].x):
                best = (mn, mx)
    return best


# ------------------------------------------------------------------ builders
def window_gaskets(mb, col, mat):
    n = 0
    for o in col.objects:
        if not any(k in o.name for k in GLASS_KEYS) or o.type != 'MESH':
            continue
        mn, mx = bbox(o)
        if (mx.y - mn.y) > 0.08 or (mx.x - mn.x) > 3.5 or (mx.z - mn.z) > 2.6:
            continue
        side = 1 if (mn.y + mx.y) > 0 else -1
        yf = mx.y if side > 0 else mn.y
        t, d = 0.038, 0.016
        yc = yf + side * (d / 2 - 0.004)
        x0, x1, z0, z1 = mn.x, mx.x, mn.z, mx.z
        L.box(mb, (x0 + x1) / 2, yc, z1 + t / 2 - 0.01, x1 - x0 + 2 * t - 0.02, d, t, mat)
        L.box(mb, (x0 + x1) / 2, yc, z0 - t / 2 + 0.01, x1 - x0 + 2 * t - 0.02, d, t, mat)
        L.box(mb, x0 - t / 2 + 0.01, yc, (z0 + z1) / 2, t, d, z1 - z0, mat)
        L.box(mb, x1 + t / 2 - 0.01, yc, (z0 + z1) / 2, t, d, z1 - z0, mat)
        n += 1
    return n


def door_steps(mb, col, face_y, mat, door_w=1.30, z=1.02, key="door split"):
    n = 0
    if "V5_doors" in col.keys():
        for s, x0, x1 in json.loads(col["V5_doors"]):
            L.box(mb, (x0 + x1) / 2, s * (face_y + 0.012), z, (x1 - x0) * 0.96, 0.07, 0.05, mat)
            n += 1
        return n
    for o in parts(col, key):
        mn, mx = bbox(o)
        side = 1 if (mn.y + mx.y) > 0 else -1
        xc = (mn.x + mx.x) / 2
        w = door_w if key == "door split" else (mx.x - mn.x)
        L.box(mb, xc, side * (face_y + 0.015), z, w, 0.07, 0.05, mat)
        n += 1
    return n


def curved_roof(mb, x0, x1, half_w, z_edge, z_peak, mat_roof, mat_gutter, segs=14):
    sag = z_peak - z_edge
    R = (half_w ** 2 + sag ** 2) / (2 * sag)
    zc = z_peak - R
    prof = []
    for i in range(segs + 1):
        y = -half_w + 2 * half_w * i / segs
        prof.append((y, zc + math.sqrt(max(0.0, R * R - y * y))))
    verts, faces, uvs = [], [], []
    for x in (x0, x1):
        for y, z in prof:
            verts.append((x, y, z))
    n = len(prof)
    for i in range(n - 1):
        faces.append((i, i + 1, n + i + 1, n + i))
        uvs.append([(x0, prof[i][0]), (x0, prof[i + 1][0]), (x1, prof[i + 1][0]), (x1, prof[i][0])])
    # end caps (closing the profile down to the edge height)
    faces.append(tuple(reversed(range(n))))
    uvs.append([(0, 0)] * n)
    faces.append(tuple(n + i for i in range(n)))
    uvs.append([(0, 0)] * n)
    mb.add(verts, faces, mat_roof, uvs, smooth=False)
    for k in range(n - 1):
        mb.sm[-3 - k] = True
    # drip gutters along both eaves + fine longitudinal roof beads
    for s in (-1, 1):
        L.box(mb, (x0 + x1) / 2, s * (half_w + 0.02), z_edge - 0.01, x1 - x0, 0.05, 0.06, mat_gutter)
        for f in (0.45, 0.80):
            y = s * half_w * f
            z = zc + math.sqrt(max(0.0, R * R - y * y))
            L.box(mb, (x0 + x1) / 2, y, z + 0.006, x1 - x0, 0.03, 0.014, mat_roof)
    return R, zc


def ac_unit_details(mb, col, mat_frame, mat_dark):
    for o in col.objects:
        if not (o.name.endswith("roof air conditioning") or o.name.endswith(" HVAC")):
            continue
        mn, mx = bbox(o)
        cx, cy = (mn.x + mx.x) / 2, (mn.y + mx.y) / 2
        L.box(mb, cx, cy, mn.z - 0.06, (mx.x - mn.x) + 0.16, (mx.y - mn.y) + 0.12, 0.16, mat_frame)
        for s in (-1, 1):
            y = cy + s * ((mx.y - mn.y) / 2 + 0.004)
            for j in range(12):
                x = mn.x + 0.25 + j * ((mx.x - mn.x) - 0.5) / 11
                L.box(mb, x, y, (mn.z + mx.z) / 2, 0.06, 0.012, (mx.z - mn.z) * 0.55, mat_dark)
        # lid seams and lifting lugs
        for f in (0.33, 0.66):
            L.box(mb, mn.x + f * (mx.x - mn.x), cy, mx.z + 0.004, 0.025, (mx.y - mn.y) * 0.98, 0.012, mat_dark)
        for sx in (-1, 1):
            for sy in (-1, 1):
                L.box(mb, cx + sx * ((mx.x - mn.x) / 2 - 0.12), cy + sy * ((mx.y - mn.y) / 2 - 0.10), mx.z + 0.03, 0.06, 0.06, 0.06, mat_frame)
        return True
    return False


def bogie_details(mb, bog, wheel_r, mats, motor=False, shinkansen=False, side_y=1.14, damper_xmax=None):
    i_frame, i_dark, i_steel, i_spring = mats
    for xc, wb, (xa, xb) in bog:
        half = wb / 2 + 0.75
        # side-frame outline plates (raised over the axle boxes, dropped in the middle)
        outline = [(-half, 0.80), (-wb / 2 - 0.05, 0.84), (-0.55, 0.84), (-0.40, 0.70), (0.40, 0.70), (0.55, 0.84),
                   (wb / 2 + 0.05, 0.84), (half, 0.80), (half, 0.66), (wb / 2 + 0.25, 0.62), (0.70, 0.60), (0.45, 0.54),
                   (-0.45, 0.54), (-0.70, 0.60), (-wb / 2 - 0.25, 0.62), (-half, 0.66)]
        for s in (-1, 1):
            # outline lies in the X-Z plane -> frame maps local (x, y) to (x, z), extrude along y
            F = Matrix(((1, 0, 0, xc), (0, 0, s * 1, s * side_y), (0, 1, 0, 0), (0, 0, 0, 1)))
            ol = outline if s < 0 else list(reversed(outline))
            L.prism(mb, ol, 0.0, 0.06, mat=i_frame, frame=F)
            for xax in (xa, xb):
                # axle-box front cover + bolts
                Fc = Matrix.Translation((xax, s * (side_y + 0.05), wheel_r)) @ Matrix.Rotation(-s * math.pi / 2, 4, 'X')
                L.lathe(mb, [(0.0, 0.0), (0.15, 0.0), (0.15, 0.05), (0.11, 0.08), (0.0, 0.08)], (0, 0), segments=16, mat=i_steel, frame=Fc)
                # axle beam (link from axle box toward the bogie centre)
                dirx = 1 if xax < xc else -1
                L.box(mb, xax + dirx * 0.38, s * (side_y - 0.02), wheel_r + 0.05, 0.62, 0.10, 0.13, i_dark)
                if not shinkansen:
                    # tread brake unit outboard of the wheel
                    L.box(mb, xax - dirx * 0.52, s * 0.74, wheel_r + 0.02, 0.22, 0.26, 0.30, i_dark)
            if shinkansen:
                # yaw damper between bogie frame and body bracket
                for sx in (-1, 1):
                    if damper_xmax is not None and xc + sx * 2.10 > damper_xmax:
                        continue          # under the tapering E5 nose the damper would poke through the skirt
                    p0 = Vector((xc + sx * 0.55, s * (side_y + 0.12), 0.80))
                    p1 = Vector((xc + sx * 1.75, s * (side_y + 0.12), 0.86))
                    L.tube(mb, [p0, p1], 0.065, sides=10, mat=i_dark)
                    L.tube(mb, [p1, p1 + Vector((sx * 0.35, 0, 0.02))], 0.035, sides=8, mat=i_steel)
        if motor:
            for xax in (xa, xb):
                dirx = 1 if xax < xc else -1
                Fm = Matrix.Translation((xax + dirx * 0.48, -0.30, wheel_r + 0.02)) @ Matrix.Rotation(-math.pi / 2, 4, 'X')
                L.lathe(mb, [(0.0, 0.0), (0.26, 0.0), (0.27, 0.05), (0.27, 0.52), (0.22, 0.58), (0.0, 0.58)], (0, 0), segments=18, mat=i_dark, frame=Fm)
                L.box(mb, xax, 0.42, wheel_r, 0.42, 0.20, 0.42, i_dark)   # gear box
        # lateral damper across the bogie centre
        L.tube(mb, [Vector((xc + 0.15, -0.55, 0.70)), Vector((xc + 0.15, 0.55, 0.72))], 0.045, sides=8, mat=i_dark)


def underfloor(mb, x0, x1, half_y, z_top, mats, kind):
    """Equipment boxes hung under the underframe, both sides, with fins/latches; tanks along the centre."""
    i_box, i_fin, i_tank = mats
    layouts = {
        "M": [(2.3, 0.50, 0.95, "fins"), (0.9, 0.40, 0.80, "plain"), (1.3, 0.42, 0.90, "louvre"), (0.8, 0.36, 0.70, "plain")],
        "T": [(1.6, 0.46, 0.90, "louvre"), (1.0, 0.40, 0.80, "plain"), (1.4, 0.44, 0.85, "fins"), (0.9, 0.34, 0.70, "plain")],
    }[kind]
    for s in (-1, 1):
        x = x0 + 0.25
        seq = layouts if s > 0 else list(reversed(layouts))
        for (lx, hz, dy, style) in seq:
            if x + lx > x1 - 0.2:
                break
            yc = s * (half_y - dy / 2)
            L.box(mb, x + lx / 2, yc, z_top - hz / 2, lx, dy, hz, i_box)
            yface = s * half_y
            if style == "fins":
                for j in range(int(lx / 0.09)):
                    L.box(mb, x + 0.06 + j * 0.09, yface + s * 0.03, z_top - hz / 2, 0.02, 0.06, hz * 0.8, i_fin)
            elif style == "louvre":
                for j in range(5):
                    L.box(mb, x + lx / 2, yface + s * 0.008, z_top - 0.08 - j * (hz - 0.12) / 5, lx * 0.85, 0.02, 0.025, i_fin)
            else:
                for f in (0.25, 0.75):
                    L.box(mb, x + f * lx, yface + s * 0.012, z_top - hz * 0.5, 0.05, 0.025, 0.12, i_fin)
            x += lx + 0.25
    # main air reservoirs and pipe run in the centre
    for yy in (-0.22, 0.22):
        Ft = Matrix.Translation(((x0 + x1) / 2 - 0.9, yy, z_top - 0.22)) @ Matrix.Rotation(math.pi / 2, 4, 'Y')
        L.lathe(mb, [(0.0, -0.8), (0.12, -0.79), (0.17, -0.72), (0.17, 0.72), (0.12, 0.79), (0.0, 0.8)], (0, 0), segments=14, mat=i_tank, frame=Ft)
    L.tube(mb, [Vector((x0, 0.0, z_top - 0.05)), Vector((x1, 0.0, z_top - 0.05))], 0.03, sides=6, mat=i_fin)


def gangway_bellows(mb, x_end, sgn, half_y, z0, z1, mat):
    for k in range(4):
        x = x_end - sgn * (0.02 + 0.035 * k)
        path = [Vector((x, -half_y, z0)), Vector((x, half_y, z0)), Vector((x, half_y, z1)), Vector((x, -half_y, z1)), Vector((x, -half_y, z0))]
        L.tube(mb, path, 0.022, sides=6, mat=mat, smooth=False)


def coupler(mb, x_end, sgn, mats):
    i_steel, i_dark = mats
    L.box(mb, x_end - sgn * 0.20, 0.0, 0.82, 0.42, 0.20, 0.16, i_steel)
    L.box(mb, x_end - sgn * 0.02, 0.0, 0.82, 0.08, 0.30, 0.24, i_dark)
    for yy in (-0.25, 0.25):
        L.tube(mb, [Vector((x_end - sgn * 0.35, yy, 0.86)), Vector((x_end - sgn * 0.12, yy, 0.72)), Vector((x_end, yy * 0.6, 0.70))], 0.025, sides=6, mat=i_dark)


def e233_black_front(mb, col, x_front, mats):
    """E233 family: the upper front is a glossy black panel framing the windscreen, with the destination
    display at the top centre and combined head/tail lamp units in the upper corners."""
    i_black, i_led, i_head, i_tail, i_dark = mats
    xf = x_front + 0.035
    L.box(mb, xf, 0.0, 2.80, 0.02, 2.62, 1.66, i_black)
    L.box(mb, xf + 0.012, 0.0, 3.405, 0.01, 1.22, 0.18, i_led)               # front destination LED
    for s in (-1, 1):
        L.box(mb, xf + 0.012, s * 1.06, 3.42, 0.01, 0.30, 0.17, i_head)       # head lamp (HID) lens
        L.box(mb, xf + 0.012, s * 0.80, 3.42, 0.01, 0.16, 0.12, i_tail)       # LED tail lamp
        L.box(mb, xf + 0.014, s * 0.42, 2.30, 0.012, 0.035, 0.62, i_dark)      # parked wiper
    return xf


def shaped_skirt(mb, x_front, i_skirt, i_dark, e235=False):
    """Front skirt (snow plough) as one bent plate: bowed in plan, raked back towards the bottom,
    narrowing downwards, with a coupler opening, 35 mm thickness, wrap-around side returns and a
    rubber lip along the bottom edge."""
    zt, zb = 0.97, 0.30
    wt, wb = (2.70, 2.28) if e235 else (2.66, 2.18)
    rake, bow, th = 0.11, 0.13, 0.035
    zs = [0.97, 0.88, 0.78, 0.68, 0.58, 0.48, 0.38, 0.34, 0.30]
    us = [i / 8.0 - 1.0 for i in range(17)]

    def P(z, u, back=0.0):
        f = (zt - z) / (zt - zb)
        w = wt + (wb - wt) * f
        return (x_front - 0.05 - rake * f - bow * u * u - back, u * w / 2, z)

    def solid(zi, ui):
        if zi < 0 or ui < 0 or zi >= len(zs) - 1 or ui >= len(us) - 1:
            return False
        zc = (zs[zi] + zs[zi + 1]) / 2
        yc = P(zc, (us[ui] + us[ui + 1]) / 2)[1]
        return not (abs(yc) < 0.37 and zc > 0.62)

    groups = {i_skirt: ([], [], {}), i_dark: ([], [], {})}

    def vi(mat, zi, ui, back):
        V, F, idx = groups[mat]
        key = (zi, ui, back)
        if key not in idx:
            idx[key] = len(V)
            V.append(P(zs[zi], us[ui], th if back else 0.0))
        return idx[key]

    for zi in range(len(zs) - 1):
        for ui in range(len(us) - 1):
            if not solid(zi, ui):
                continue
            mat = i_dark if zs[zi + 1] < 0.335 else i_skirt
            F = groups[mat][1]
            f00, f01, f11, f10 = (vi(mat, zi, ui, 0), vi(mat, zi, ui + 1, 0), vi(mat, zi + 1, ui + 1, 0), vi(mat, zi + 1, ui, 0))
            b00, b01, b11, b10 = (vi(mat, zi, ui, 1), vi(mat, zi, ui + 1, 1), vi(mat, zi + 1, ui + 1, 1), vi(mat, zi + 1, ui, 1))
            F.append([f00, f10, f11, f01])            # front (faces +x)
            F.append([b00, b01, b11, b10])            # back
            # rims where the neighbour is open (outer border or coupler opening); own vertices so the
            # 90-degree plate edge stays crisp under smooth shading
            V = groups[mat][0]

            def rim(a, b, c, d):
                o = len(V)
                V.extend([V[a], V[b], V[c], V[d]])
                F.append([o, o + 1, o + 2, o + 3])
            if not solid(zi - 1, ui):
                rim(f00, f01, b01, b00)
            if not solid(zi + 1, ui):
                rim(f10, b10, b11, f11)
            if not solid(zi, ui - 1):
                rim(f00, b00, b10, f10)
            if not solid(zi, ui + 1):
                rim(f01, f11, b11, b01)
    # side returns wrapping back under the body
    V, F, _ = groups[i_skirt]
    for sgn in (-1.0, 1.0):
        for zi in range(len(zs) - 2):
            z0, z1 = zs[zi], zs[zi + 1]
            a0, a1 = P(z0, sgn), P(z1, sgn)
            o = len(V)
            V += [a0, a1, (a1[0] - 0.42, a1[1], z1), (a0[0] - 0.42, a0[1], z0)]
            F.append([o, o + 1, o + 2, o + 3] if sgn > 0 else [o, o + 3, o + 2, o + 1])
    for mat, (V, F, _) in groups.items():
        if F:
            mb.add(V, F, mat=mat, smooth=True)


def cab_front(mb, col, x_front, mats, e235=False, roof_z=3.86, body_has_front=False):
    i_skirt, i_dark, i_tail, i_led, i_steel = mats
    shaped_skirt(mb, x_front, i_skirt, i_dark, e235=e235)
    # tail lamps beside the head lamps
    lamps = [o for o in col.objects if ("upper headlight" in o.name)] if e235 else []
    for o in lamps:
        mn, mx = bbox(o)
        yc = (mn.y + mx.y) / 2
        s = 1 if yc > 0 else -1
        if (mx.y - mn.y) < 0.8:
            L.box(mb, mx.x + 0.01, yc - s * 0.30, (mn.z + mx.z) / 2, 0.03, 0.18, (mx.z - mn.z) * 0.8, i_tail)
        else:  # single object spanning both lamps
            for s2 in (-1, 1):
                L.box(mb, mx.x + 0.01, s2 * (mx.y - 0.42), (mn.z + mx.z) / 2, 0.03, 0.18, (mx.z - mn.z) * 0.8, i_tail)
    # vertical grab rails on the front corners and a run-number display
    for s in (-1, 1):
        L.tube(mb, [Vector((x_front + 0.05, s * 1.22, 1.30)), Vector((x_front + 0.10, s * 1.22, 1.33)),
                    Vector((x_front + 0.10, s * 1.22, 2.10)), Vector((x_front + 0.05, s * 1.22, 2.13))], 0.018, sides=6, mat=i_steel)
    if not body_has_front:
        L.box(mb, x_front + 0.06, 0.78, 2.12, 0.03, 0.40, 0.13, i_led)
    # roof antennas (train radio plate + GPS dome) behind the cab
    rz = roof_z - 0.02
    L.box(mb, x_front - 1.6, 0.0, rz + 0.11, 0.55, 0.05, 0.26, i_dark)
    L.box(mb, x_front - 1.6, 0.0, rz, 0.70, 0.18, 0.05, i_steel)
    L.lathe(mb, [(0.0, rz), (0.10, rz), (0.10, rz + 0.04), (0.07, rz + 0.09), (0.0, rz + 0.11)], (x_front - 2.4, 0.35), segments=12, mat=i_dark)


def lit_destination(col, mat_led):
    """Swap the dark side/front destination LED material for a softly lit LED panel."""
    n = 0
    for o in col.objects:
        if ("destination LED" in o.name or "passenger LED" in o.name or "front LED" in o.name) and o.type == 'MESH':
            me = o.data
            if mat_led.name not in [m.name for m in me.materials if m]:
                if len(me.materials) == 0:
                    me.materials.append(mat_led)
                else:
                    me.materials[0] = mat_led
                n += 1
    return n


def replace_v3_pantographs(src_col_name, mats_hint=None):
    """Copy the detailed V4 raised pantograph into each V3 simple pantograph variant; retire the simple parts."""
    src = bpy.data.collections.get(src_col_name)
    src_objs = [o for o in src.objects if "_raised_" in o.name]
    bed = next(o for o in src_objs if o.name.endswith("raised_mounting_bed"))
    smn, smx = bbox(bed)
    s_center = (smn + smx) / 2
    done = []
    for col in bpy.data.collections:
        if not re.match(r"V3 Track \d\d car \d\d panto variant$", col.name):
            continue
        old = [o for o in col.objects if "pantograph" in o.name and not o.get("V5_retired")]
        obed = [o for o in old if o.name.endswith("pantograph bed")]
        if not obed:
            continue
        mn, mx = bbox(obed[0])
        center = (mn + mx) / 2
        off = Vector((center.x - s_center.x, center.y - s_center.y, (mn.z - smn.z)))
        for o in old:
            for c in list(o.users_collection):
                c.objects.unlink(o)
            L.hidden_collection().objects.link(o)
            o.hide_render = True
            o.hide_viewport = True
            o["V5_retired"] = True
        for o in src_objs:
            n = o.copy()
            if o.data is not None:
                n.data = o.data      # share mesh data
            n.name = o.name.replace("V4_Train_T08_C07", "V5_" + col.name.replace(" ", "_"))
            mw = Matrix.Translation(off) @ o.matrix_world
            n.parent = None
            n.matrix_world = mw
            col.objects.link(n)
        done.append(col.name)
    return done


# departure direction of the trains standing at each track (Tokyo is a terminal for the Chuo Rapid line and both
# Shinkansen; the others are through lines): True = leaves toward Kanda (-X)
DEPART_NORTH = {"01", "02", "03", "04", "09", "10", "20", "21", "22", "23"}
# destination display variant per track (texture 0 / 1 of the line): Keihin-Tohoku 3 = Omiya / 6 = Ofuna,
# Yamanote 4 = inner loop (Ueno, Ikebukuro) / 5 = outer loop (Shinagawa, Shibuya), Tokaido 7-8 = Atami / 9-10 = Utsunomiya
DEST_VARIANT = {"03": 0, "06": 1, "04": 0, "05": 1, "07": 0, "08": 0, "09": 1, "10": 1}


def set_instance_states():
    """Per-instance flags read by the lamp and LED shaders (Attribute node, type Instancer): V5_head on the
    leading cab, V5_tail on the trailing cab (both off on cabs coupled inside a formation) and V5_dest for the
    destination shown on that track."""
    groups = {}
    for e in bpy.data.objects:
        m = re.match(r"Track (\d\d) ", e.name)
        if e.type == 'EMPTY' and e.instance_collection and m and not e.instance_collection.name.startswith("V3 N700"):
            groups.setdefault(m.group(1), []).append(e)
    out = {}
    for k, objs in groups.items():
        north = k in DEPART_NORTH
        xs = sorted(objs, key=lambda o: o.matrix_world.translation.x)
        heads = tails = 0
        for o in objs:
            o["V5_dest"] = float(DEST_VARIANT.get(k, 0))
            o["V5_head"] = 0.0
            o["V5_tail"] = 0.0
            cname = o.instance_collection.name
            if not ("cab" in cname or cname.startswith("V4_Train_E5_car_")):
                continue
            fx = (o.matrix_world.to_3x3() @ Vector((1.0, 0.0, 0.0))).x          # cab / nose is at local +x
            at_north = o is xs[0] and fx < 0
            at_south = o is xs[-1] and fx > 0
            if (at_north and north) or (at_south and not north):
                o["V5_head"] = 1.0; heads += 1
            elif at_north or at_south:
                o["V5_tail"] = 1.0; tails += 1
        out[k] = {"lead_cabs_lit": heads, "rear_cabs_tail_lit": tails, "dest_variant": DEST_VARIANT.get(k, 0)}
    return out


def run():
    out = {}
    m_roof = L.principled("V5 | EMU roof grey anti-slip paint", (0.50, 0.52, 0.53), rough=0.62, metal=0.15)
    m_gutter = bpy.data.materials["V2 | stainless commuter body"]
    m_rubber = bpy.data.materials["V4_Train_rubber_and_gaskets"]
    m_steel = bpy.data.materials["V2 | rail steel"]
    m_under = L.principled("V5 | underfloor equipment charcoal", (0.05, 0.055, 0.06), rough=0.55, metal=0.35)
    m_fin = L.principled("V5 | underfloor fin dark", (0.025, 0.028, 0.03), rough=0.5, metal=0.4)
    m_bogie = L.principled("V5 | bogie frame dark grey", (0.07, 0.075, 0.08), rough=0.5, metal=0.45)
    m_spring = L.principled("V5 | spring steel black", (0.02, 0.022, 0.024), rough=0.45, metal=0.6)
    m_skirt = L.principled("V5 | cab skirt grey", (0.20, 0.21, 0.22), rough=0.5, metal=0.4)
    m_tail = L.principled("V5 | tail lamp red lens", (0.42, 0.02, 0.02), rough=0.12, spec=0.8)
    m_led = L.principled("V5 | lit LED destination panel", (0.03, 0.02, 0.01), rough=0.3, emission=(1.0, 0.45, 0.08), strength=2.2)
    m_runno = L.principled("V5 | run-number LED", (0.03, 0.02, 0.01), rough=0.3, emission=(1.0, 0.32, 0.05), strength=3.0)
    m_step = bpy.data.materials["V2 | stainless commuter body"]
    m_black = L.principled("V5 | E233 glossy black front", (0.008, 0.009, 0.011), rough=0.08, spec=0.7)
    m_ledf = L.principled("V5 | front destination LED", (0.02, 0.015, 0.01), rough=0.3, emission=(1.0, 0.55, 0.15), strength=2.5)
    m_head = L.principled("V5 | head lamp lens", (0.85, 0.88, 0.9), rough=0.05, spec=0.9)

    for name in COMMUTER_CAB + COMMUTER_MID + GREEN:
        col = bpy.data.collections.get(name)
        if col is None:
            continue
        cab = name in COMMUTER_CAB
        green = name in GREEN
        e235 = "E235" in name
        ext = shell_extent(col)
        mb = L.MeshBuilder()
        rec = {}
        mats = [m_roof, m_gutter, m_rubber, m_steel, m_under, m_fin, m_bogie, m_spring, m_skirt, m_tail, m_runno, m_step,
                m_black, m_ledf, m_head]
        I = {m.name: i for i, m in enumerate(mats)}
        # roof (E233 procedural masters have a separate flat roof box)
        roof = [o for o in col.objects if o.name.endswith(" roof") and o.type == 'MESH']
        if roof and not e235:
            mn, mx = bbox(roof[0])
            x1 = 9.62 if cab else mx.x
            curved_roof(mb, mn.x, x1, 1.45, 3.56, 3.86, I[m_roof.name], I[m_gutter.name])
            L.retire(roof[0])
            rec["curved_roof"] = True
        rec["ac"] = ac_unit_details(mb, col, I[m_roof.name], I[m_fin.name])
        rec["window_gaskets"] = window_gaskets(mb, col, I[m_rubber.name])
        if ext is not None:
            face_y = 1.30 if "V5_doors" in col.keys() else ext[1].y
            rec["door_steps"] = door_steps(mb, col, face_y, I[m_step.name], z=1.0)
        bog = bogies(col)
        rec["bogies"] = len(bog)
        if bog:
            bogie_details(mb, bog, 0.43, (I[m_bogie.name], I[m_under.name], I[m_steel.name], I[m_spring.name]),
                          motor=(name in COMMUTER_MID))
        uf = [o for o in col.objects if o.name.endswith("underfloor equipment") or re.search(r"underfloor equipment\.\d{3}$", o.name)]
        if bog and not green:
            for o in uf:
                L.retire(o)
            inner = min(abs(b[0]) - b[1] / 2 - 0.85 for b in bog)
            underfloor(mb, -inner, inner, 1.22, 0.66, (I[m_under.name], I[m_fin.name], I[m_steel.name]),
                       "M" if name in COMMUTER_MID else "T")
            rec["underfloor_rebuilt"] = len(uf)
        # gangways / couplers
        for g in parts(col, "gangway"):
            mn, mx = bbox(g)
            sgn = 1 if (mn.x + mx.x) > 0 else -1
            xe = mx.x if sgn > 0 else mn.x
            gangway_bellows(mb, xe, sgn, (mx.y - mn.y) / 2 + 0.03, mn.z - 0.02, mx.z + 0.02, I[m_rubber.name])
            coupler(mb, xe, sgn, (I[m_steel.name], I[m_rubber.name]))
        if cab and not parts(col, "gangway") and ext is not None:
            gangway_bellows(mb, ext[0].x - 0.12, -1, 0.68, 0.96, 3.24, I[m_rubber.name])
            coupler(mb, ext[0].x - 0.12, -1, (I[m_steel.name], I[m_rubber.name]))
        if cab:
            if "V5_cab_front_x" in col.keys():          # one-piece body already carries the front livery and lamps
                xf = float(col["V5_cab_front_x"])
            else:
                masks = [o for o in col.objects if "front mask" in o.name]
                xf = max(bbox(o)[1].x for o in masks) if masks else 9.93
                if not e235:
                    e233_black_front(mb, col, xf, (I[m_black.name], I[m_ledf.name], I[m_head.name], I[m_tail.name], I[m_rubber.name]))
            cab_front(mb, col, xf, (I[m_skirt.name], I[m_rubber.name], I[m_tail.name], I[m_runno.name], I[m_steel.name]),
                      e235=e235, roof_z=float(col.get("V5_roof_z", 3.70 if e235 else 3.86)),
                      body_has_front=("V5_cab_front_x" in col.keys()))
            rec["cab_front"] = round(xf, 3)
        rec["lit_led_panels"] = lit_destination(col, m_led)
        ob = mb.build(f"V5 detail | {name}", col, mats)
        rec["verts"] = len(ob.data.vertices)
        out[name] = rec
        L.log(name, rec)

    # ---- E5 cars
    m_e5_frame = L.principled("V5 | E5 bogie frame grey", (0.10, 0.11, 0.115), rough=0.5, metal=0.4)
    for name in E5:
        col = bpy.data.collections.get(name)
        if col is None:
            continue
        mats = [m_rubber, m_e5_frame, m_under, m_steel, m_spring, m_step]
        mb = L.MeshBuilder()
        rec = {"window_gaskets": window_gaskets(mb, col, 0)}
        ext = shell_extent(col)
        if ext is not None:
            n = 0
            if "V5_doors" in col.keys():
                for s, x0, x1 in json.loads(col["V5_doors"]):
                    L.box(mb, (x0 + x1) / 2, s * 1.672, 1.235, (x1 - x0) * 0.92, 0.05, 0.04, 5)
                    n += 1
            else:
                for o in parts(col, "door perimeter"):
                    mn, mx = bbox(o)
                    s = 1 if (mn.y + mx.y) > 0 else -1
                    L.box(mb, (mn.x + mx.x) / 2, s * (ext[1].y + 0.012), 1.24, (mx.x - mn.x) * 0.9, 0.06, 0.05, 5)
                    n += 1
            rec["door_steps"] = n
        bog = bogies(col)
        rec["bogies"] = len(bog)
        if bog:
            dxm = (float(col["V5_nose_x_tip"]) - 5.5) if "V5_nose_x_tip" in col.keys() else None
            bogie_details(mb, bog, 0.43, (1, 2, 3, 4), motor=False, shinkansen=True, side_y=1.14, damper_xmax=dxm)
        ob = mb.build(f"V5 detail | {name}", col, mats)
        rec["verts"] = len(ob.data.vertices)
        out[name] = rec
        L.log(name, rec)

    out["pantographs_upgraded"] = replace_v3_pantographs("V4_Train_Track_08_actual_car_07_pantograph")
    out["instance_states"] = set_instance_states()
    L.log("instance states", out["instance_states"])
    L.log("pantographs", out["pantographs_upgraded"])
    return out


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    bpy.ops.wm.open_mainfile(filepath=src, load_ui=False, use_scripts=False)
    info = run()
    bpy.context.scene["V5_trains_summary"] = json.dumps(info)
    bpy.ops.wm.save_as_mainfile(filepath=dst, compress=True)
    print("SAVED", dst)
