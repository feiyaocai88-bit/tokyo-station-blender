"""V5 re-layout: move the whole track / platform system to the positions measured from GSI data.

Source of the target layout: relayout/targets.json (built by relayout/build_targets.py from the GSI
vector-tile track centrelines RailTrCL and the GSI seamless aerial photo).

What happens
  * every track keeps its own cross-section (rails, sleepers, ballast, viaduct, wires, platform edge,
    tactile strip, platform doors move rigidly with their track); the space *between* tracks is
    stretched, so island platforms widen from 5.1-5.4 m to their real 9.6-14 m and follow the real
    curvature at the north end
  * small parts (columns, lights, signs, masts, insulators, door panels ...) are translated, never
    stretched
  * platforms and canopies are cut to their real length (or extended at the north end), trains are
    slid along their track so they stay inside the platform
  * the Chuo Line (tracks 1-2) is raised 7.0 m and placed above track 3, as at the real station
  * site ground, display base and perimeter road are extended east by the same amount
"""
import sys, os, json, re, math
import numpy as np
import bpy, bmesh
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v5lib as L

HERE = os.path.dirname(os.path.abspath(__file__))


def _find(fn):
    for c in (os.environ.get("V5_RELAYOUT_DIR", ""), os.path.join(HERE, "..", "relayout"), HERE):
        p = os.path.join(c, fn)
        if c and os.path.exists(p):
            return p
    raise FileNotFoundError(fn)


D = json.load(open(_find("targets.json")))
GX = np.array(D["X"], float)
DX = GX[1] - GX[0]
ORDER = D["order"]
MOD = {k: np.array(D["model"][k]) for k in ORDER}
TGT = {k: np.array(D["target"][k]) for k in ORDER}
ISL = D["islands"]
CHUO_DZ = float(D["chuo_raise"])
SHINKANSEN = {'14', '15', '16', '17', '18', '19', '20', '21', '22', '23'}
TRACK_ISLAND = {}
for name, v in ISL.items():
    TRACK_ISLAND[v["west"]] = name
    TRACK_ISLAND[v["east"]] = name
WEST_ANCHOR = 12.0
GEN = [k for k in ORDER if k not in ("01", "02")]          # general knot tracks (west -> east)


# ------------------------------------------------------------------ knot tables
E_IN = 1.30            # end of the rigid track part (sleepers end at 1.23) on the platform side


def _gsmooth(y, sigma_m):
    n = int(4 * sigma_m / DX) * 2 + 1
    k = np.exp(-0.5 * ((np.arange(n) - n // 2) * DX / sigma_m) ** 2); k /= k.sum()
    yp = np.concatenate([np.full(n // 2, y[0]), y, np.full(n // 2, y[-1])])
    return np.convolve(yp, k, mode="valid")


def curve_clearance(k, side, edge):
    """Extra platform-edge offset on curves (V5.1).  A rigid car whose bogies are on the track bulges toward
    the centre of the curve at mid-car (b^2/2R) and swings out at its ends ((h^2-b^2)/2R); real curved
    platforms leave that much more gap.  side = +1: platform east (+y) of the track."""
    y = TGT[k]; h = 12
    yp = np.pad(y, h, mode="edge")
    kap = (yp[2 * h:] - 2 * yp[h:-h] + yp[:-2 * h]) / ((h * DX) ** 2)
    if k in SHINKANSEN:
        mid, end, half, hw = 38.3, 48.8, 12.7, 1.69          # N700 b = 8.75 m, E5 model b = 7.5 m, h = 12.4 m
    else:
        mid, end, half, hw = 23.8, 26.7, 10.1, 1.50          # E233 / E235: b = 6.9 m, h = 10.0 m
    need = np.where(kap * side > 0, mid, end) * np.abs(kap)
    win = int(half / DX)
    mx = need.copy()
    for s_ in range(1, win + 1):
        mx[s_:] = np.maximum(mx[s_:], need[:-s_]); mx[:-s_] = np.maximum(mx[:-s_], need[s_:])
    w = np.clip(mx + 0.08 - (edge - hw), 0.0, 0.45)
    return np.maximum(_gsmooth(w, 5.0), 0.0)


CLEARANCE = {}


def _rigid_tables(tracks, M, T, west_anchor=None):
    """Per X: knot positions (model / target). Each track gets a rigid band [c-rl, c+rr]; on the platform side
    the platform edge zone [edge, edge+1.6] is a second rigid piece that is moved out by the curve clearance."""
    n = len(tracks)
    NX = len(GX)
    rl = np.zeros((n, NX)); rr = np.zeros((n, NX))
    side = [0] * n; edges = [0.0] * n
    for i, k in enumerate(tracks):
        isl = TRACK_ISLAND[k]
        edge = ISL[isl]["edge"]
        edges[i] = edge
        rp = edge + 1.6
        if ISL[isl]["west"] == k:
            rr[i] = rp; rl[i] = 1.9; side[i] = 1
        else:
            rl[i] = rp; rr[i] = 1.9; side[i] = -1
    for i in range(n - 1):
        a, b = tracks[i], tracks[i + 1]
        avail = np.minimum(M[b] - M[a], T[b] - T[a]) - 0.15
        want = rr[i] + rl[i + 1]
        s = np.where(want > avail, np.clip(avail, 0.2, None) / want, 1.0)
        rr[i] *= s; rl[i + 1] *= s
    if west_anchor is not None:
        a = tracks[0]
        avail = np.minimum(M[a], T[a]) - west_anchor - 0.15
        rl[0] = np.minimum(rl[0], np.clip(avail, 0.2, None))
    KM, KT = [], []
    if west_anchor is not None:
        KM.append(np.full(NX, west_anchor)); KT.append(np.full(NX, west_anchor))
    for i, k in enumerate(tracks):
        w = curve_clearance(k, side[i], edges[i])
        CLEARANCE[k] = w
        e2 = edges[i] - 0.02
        if side[i] > 0:
            e2v = np.minimum(e2, rr[i] - 0.05); ein = np.minimum(E_IN, e2v - 0.05)
            KM += [M[k] - rl[i], M[k] + ein, M[k] + e2v, M[k] + rr[i]]
            KT += [T[k] - rl[i], T[k] + ein, T[k] + e2v + w, T[k] + rr[i] + w]
        else:
            e2v = np.minimum(e2, rl[i] - 0.05); ein = np.minimum(E_IN, e2v - 0.05)
            KM += [M[k] - rl[i], M[k] - e2v, M[k] - ein, M[k] + rr[i]]
            KT += [T[k] - rl[i] - w, T[k] - e2v - w, T[k] - ein, T[k] + rr[i]]
    KM = np.stack(KM, 1); KT = np.stack(KT, 1)
    # strictly increasing (guard against round-off)
    for K in (KM, KT):
        for j in range(1, K.shape[1]):
            K[:, j] = np.maximum(K[:, j], K[:, j - 1] + 1e-3)
    return KM, KT


KM_G, KT_G = _rigid_tables(GEN, MOD, TGT, WEST_ANCHOR)
KM_C, KT_C = _rigid_tables(["01", "02"], MOD, TGT, None)
# site ground / display base / perimeter road: everything east of the model bundle moves by the
# largest eastward shift so the widened bundle always has ground under it
_site = (GX >= -216) & (GX <= 256)
EAST_SHIFT = float(np.max(TGT["19"][_site] - MOD["19"][_site]))
SITE_EAST_FROM = 165.0


def _rows(K, Xq):
    f = (np.asarray(Xq, float) - GX[0]) / DX
    f = np.clip(f, 0, len(GX) - 1.000001)
    i0 = np.floor(f).astype(int); w = (f - i0)[:, None]
    return K[i0] * (1 - w) + K[i0 + 1] * w


def F(Xm, Xt, Y, chuo=False):
    """Map model Y (at model X = Xm) to target Y (at target X = Xt)."""
    Xm = np.atleast_1d(np.asarray(Xm, float)); Xt = np.atleast_1d(np.asarray(Xt, float))
    Y = np.atleast_1d(np.asarray(Y, float))
    if chuo:
        KM, KT = _rows(KM_C, Xm), _rows(KT_C, Xt)
        lo_shift = KT[:, 0] - KM[:, 0]
    else:
        KM, KT = _rows(KM_G, Xm), _rows(KT_G, Xt)
        lo_shift = np.zeros(len(Y))
    K = KM.shape[1]
    out = Y + lo_shift                                   # below the first knot
    idx = (Y[:, None] >= KM).sum(1) - 1
    mid = (idx >= 0) & (idx < K - 1)
    r = np.where(mid)[0]; j = idx[mid]
    a = KM[r, j]; b = KM[r, j + 1]; ta = KT[r, j]; tb = KT[r, j + 1]
    out[mid] = ta + (Y[mid] - a) * (tb - ta) / (b - a)
    hi = idx >= K - 1
    out[hi] = Y[hi] + (KT[hi, -1] - KM[hi, -1])
    return out


def track_y(k, X, target=True):
    return np.interp(X, GX, (TGT if target else MOD)[k])


def track_angle(k, X, target=True):
    h = 2.0
    return math.atan2(track_y(k, X + h, target) - track_y(k, X - h, target), 2 * h)


def model_dir(xc, yc, chuo=False):
    """Direction (rad) of the model track nearest to (xc, yc) at xc: the line a rigid part was aligned with."""
    cand = ("01", "02") if chuo else GEN
    k = min(cand, key=lambda t: abs(float(np.interp(xc, GX, MOD[t])) - yc))
    return track_angle(k, xc, target=False)


# --------------------------------------------------------------- x handling
def xmap(x, A, B, Am, Bm, ramp=30.0):
    """Cut [Am,Bm] to [A,B]; where the target end lies beyond the model end, stretch the last `ramp` metres."""
    x = np.asarray(x, float).copy()
    if A >= Am:
        x = np.maximum(x, A)
    else:
        r = (x < Am + ramp)
        x[r] = A + (np.maximum(x[r], Am) - Am) * (Am + ramp - A) / ramp
    if B <= Bm:
        x = np.minimum(x, B)
    else:
        r = (x > Bm - ramp)
        x[r] = (Bm - ramp) + (np.minimum(x[r], Bm) - (Bm - ramp)) * (B - (Bm - ramp)) / ramp
    return x


def outside(xc, A, B, Am, Bm, tol=0.05):
    return (A >= Am and xc < A - tol) or (B <= Bm and xc > B + tol)


# ------------------------------------------------------------ classification
BUNDLE_COLS = ("V3 05 | Tracks platforms and catenary",)
SITE_NAMES = ("Site ground", "Display base", "V4 unified perimeter and transport road",
              "V4 north underbridge walkway -1", "V4 north underbridge walkway 1",
              "V4 south underbridge walkway -1", "V4 south underbridge walkway 1")
RE_NAMED_ISL = re.compile(r"(?:Platform |platform canopy |tactile strip |Staff_gate_)(\d\d)-(\d\d)")
RE_DOOR = re.compile(r"Platform_door_system_track_(\d\d)")
RE_CANOPY_KIND = re.compile(r"platform (column|strip light|numbered sign|route|number|canopy diagonal)|platform canopy \d\d")
RE_PLAT_KIND = re.compile(r"Platform \d\d-\d\d raised deck|tactile strip|platform edge coping|Platform_door_system|"
                          r"Platform_longitudinal_risers|Unobstructed_platform_tactile")
RE_END_KIND = re.compile(r"Platform_end_fixed_guards|Staff_gate")


def is_bundle(o):
    if o.name in SITE_NAMES:
        return True
    return any(c.name in BUNDLE_COLS or c.name.startswith("V4_Structure_") for c in o.users_collection)


def chuo_by_name(name):
    return bool(re.search(r"Track 0[12] |Track 0[12]$|01-02|Chuo", name))


def island_for_point(xc, yc):
    """Platform island whose model platform zone contains (xc, yc)."""
    for name, v in ISL.items():
        yw = np.interp(xc, GX, MOD[v["west"]]); ye = np.interp(xc, GX, MOD[v["east"]])
        if yw + 0.35 < yc < ye - 0.35:
            return name
    return None


def island_for_points(X, Y):
    """Majority vote over the vertices of a (possibly long, curved) part."""
    best, cnt = None, 0
    for name, v in ISL.items():
        yw = np.interp(X, GX, MOD[v["west"]]); ye = np.interp(X, GX, MOD[v["east"]])
        c = int(((Y > yw + 0.35) & (Y < ye - 0.35)).sum())
        if c > cnt:
            best, cnt = name, c
    return best if cnt >= 0.5 * len(X) else None


def item_kind(name):
    if RE_END_KIND.search(name):
        return "end"
    if RE_CANOPY_KIND.search(name):
        return "canopy"
    if RE_PLAT_KIND.search(name):
        return "platform"
    return None


MODEL_EXT = {}          # island -> {"platform": (Am,Bm), "canopy": (Am,Bm)}


def model_extents():
    for name in ISL:
        ext = D["model_platform_extent"].get(name)
        cmin, cmax = 1e9, -1e9
        for o in bpy.data.objects:
            if o.type == 'MESH' and re.match(r"V3 platform canopy %s(\.\d+)?$" % name, o.name):
                bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
                cmin = min(cmin, min(v.x for v in bb)); cmax = max(cmax, max(v.x for v in bb))
        MODEL_EXT[name] = {"platform": tuple(ext), "canopy": (cmin, cmax) if cmax > cmin else tuple(ext)}


def extents(island, kind):
    v = ISL[island]
    if kind == "canopy":
        A, B = v["Q"]; Am, Bm = MODEL_EXT[island]["canopy"]
    else:
        A, B = v["P"]; Am, Bm = MODEL_EXT[island]["platform"]
    return A, B, Am, Bm


# ----------------------------------------------------------------- islands
def mesh_islands(me):
    n = len(me.vertices)
    lab = np.arange(n)
    ne = len(me.edges)
    if ne == 0 or n == 0:
        return lab
    ev = np.empty(ne * 2, int); me.edges.foreach_get("vertices", ev); ev = ev.reshape(-1, 2)
    a, b = ev[:, 0], ev[:, 1]
    for _ in range(10000):
        la, lb = lab[a], lab[b]
        m = np.minimum(la, lb)
        changed = np.any(la != lb)
        if not changed:
            break
        np.minimum.at(lab, a, m); np.minimum.at(lab, b, m)
        for _ in range(4):
            lab = lab[lab]
    return lab


STATS = {"objects_vertex_mapped": 0, "objects_moved": 0, "objects_retired": 0, "verts_mapped": 0,
         "islands_rigid": 0, "islands_deleted": 0, "curves": 0, "trains": 0, "chuo_objects": 0}


def process_mesh(o):
    me = o.data
    n = len(me.vertices)
    if n == 0:
        return
    if me.users > 1:
        o.data = me.copy(); me = o.data
    mw = np.array(o.matrix_world)
    co = np.empty(n * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    W = co @ mw[:3, :3].T + mw[:3, 3]
    site = o.name in SITE_NAMES
    lab = mesh_islands(me) if not site else np.zeros(n, int)
    uniq, inv = np.unique(lab, return_inverse=True)
    ni = len(uniq)
    mn = np.full((ni, 3), 1e18); mx = np.full((ni, 3), -1e18)
    for k in range(3):
        np.minimum.at(mn[:, k], inv, W[:, k]); np.maximum.at(mx[:, k], inv, W[:, k])
    ctr = (mn + mx) / 2; ext = mx - mn
    name = o.name
    named_chuo = chuo_by_name(name)
    m_isl = RE_NAMED_ISL.search(name)
    m_door = RE_DOOR.search(name)
    kind = item_kind(name)
    newW = W.copy()
    delete = np.zeros(n, bool)
    chuo_any = False
    for i in range(ni):
        sel = inv == i
        xc, yc = ctr[i, 0], ctr[i, 1]
        chuo = (not site) and (named_chuo or (yc < 40.0 and xc < 130.0))
        chuo_any |= chuo
        # platform membership
        isl = None
        if kind:
            if m_isl:
                isl = "%s-%s" % (m_isl.group(1), m_isl.group(2))
            elif m_door:
                isl = TRACK_ISLAND.get(m_door.group(1))
            elif ext[i, 0] < 30.0:
                isl = island_for_point(xc, yc)
            else:
                isl = island_for_points(W[sel, 0], W[sel, 1])
        rigid = (ext[i, 1] < 1.0 and ext[i, 0] < 30.0)
        discrete = ext[i, 0] < 6.0          # columns, braces, lights, signs, door panels, gates
        Xi = W[sel, 0]; Yi = W[sel, 1]; Zi = W[sel, 2]
        # ---- X handling (platform items only)
        if isl and kind:
            A, B, Am, Bm = extents(isl, "canopy" if kind == "canopy" else "platform")
            if kind == "end" and (abs(xc - Am) < 8 or abs(xc - Bm) < 8):
                Xt = Xi + ((A - Am) if abs(xc - Am) < abs(xc - Bm) else (B - Bm))
            elif discrete or kind == "end":
                if outside(xc, A, B, Am, Bm):
                    delete[sel] = True
                    STATS["islands_deleted"] += 1
                    continue
                Xt = Xi + (float(xmap([xc], A, B, Am, Bm)[0]) - xc)
            else:
                Xt = xmap(Xi, A, B, Am, Bm)
        else:
            Xt = Xi
        # ---- Y mapping
        if site:
            Yt = np.where(Yi > SITE_EAST_FROM, Yi + EAST_SHIFT, F(Xi, Xt, Yi, False))
        elif rigid:
            xct = xc + float(np.mean(Xt - Xi))
            dy = float(F([xc], [xct], [yc], chuo)[0]) - yc
            # turn the part with the re-laid track: map a short segment along the local model track direction
            # and rotate the part (about its new centre) by the change of direction.  Without this, rigid parts
            # (platform-door panels, signs, guards) stay parallel to X and stand crooked on curved platforms.
            am = model_dir(xc, yc, chuo)
            h = min(max(0.5 * float(ext[i, 0]), 1.0), 8.0)
            ca, sa = math.cos(am), math.sin(am)
            xs = np.array([xc - h * ca, xc + h * ca]); ys = np.array([yc - h * sa, yc + h * sa])
            yts = F(xs, xs + (xct - xc), ys, chuo)
            th = math.atan2(float(yts[1] - yts[0]), float(xs[1] - xs[0])) - am
            if abs(th) > 2e-4:
                c_, s_ = math.cos(th), math.sin(th)
                px, py = Xt - xct, Yi - yc
                Xt = xct + c_ * px - s_ * py
                Yt = (yc + dy) + s_ * px + c_ * py
                STATS["islands_rotated"] = STATS.get("islands_rotated", 0) + 1
                STATS["max_island_turn_deg"] = max(STATS.get("max_island_turn_deg", 0.0), round(abs(math.degrees(th)), 2))
            else:
                Yt = Yi + dy
            STATS["islands_rigid"] += 1
        else:
            Yt = F(Xi, Xt, Yi, chuo)
        # ---- Z (Chuo raised above track 3)
        if chuo:
            zmin, zmax = mn[i, 2], mx[i, 2]
            if zmin >= 6.0:
                Zt = Zi + CHUO_DZ
            elif zmax > 5.0 and zmin < 1.0:
                Zt = zmin + (Zi - zmin) * (zmax - zmin + CHUO_DZ) / max(zmax - zmin, 1e-6)
            else:
                Zt = Zi
        else:
            Zt = Zi
        newW[sel, 0] = Xt; newW[sel, 1] = Yt; newW[sel, 2] = Zt
    if delete.all():
        L.retire(o); STATS["objects_retired"] += 1
        return
    inv_m = np.linalg.inv(mw)
    loc = newW @ inv_m[:3, :3].T + inv_m[:3, 3]
    me.vertices.foreach_set("co", loc.ravel())
    if delete.any():
        bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[bm.verts[i] for i in np.where(delete)[0]], context='VERTS')
        bm.to_mesh(me); bm.free()
    me.update()
    o["V5_relayout"] = True
    STATS["objects_vertex_mapped"] += 1
    STATS["verts_mapped"] += n
    if chuo_any:
        STATS["chuo_objects"] += 1


def process_small_object(o):
    """Objects whose data is shared (signs, lights, buffers) or text: move the whole object."""
    bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
    mn = Vector([min(v[i] for v in bb) for i in range(3)]); mx = Vector([max(v[i] for v in bb) for i in range(3)])
    c = (mn + mx) / 2
    chuo = chuo_by_name(o.name) or (c.y < 40.0 and c.x < 130.0)
    kind = item_kind(o.name)
    isl = None
    if kind:
        m_isl = RE_NAMED_ISL.search(o.name)
        isl = "%s-%s" % (m_isl.group(1), m_isl.group(2)) if m_isl else island_for_point(c.x, c.y)
    xt = c.x
    if isl:
        A, B, Am, Bm = extents(isl, "canopy" if kind == "canopy" else "platform")
        if kind == "end" and (abs(c.x - Am) < 8 or abs(c.x - Bm) < 8):
            xt = c.x + ((A - Am) if abs(c.x - Am) < abs(c.x - Bm) else (B - Bm))
        else:
            if outside(c.x, A, B, Am, Bm):
                L.retire(o); STATS["objects_retired"] += 1
                return
            xt = float(xmap([c.x], A, B, Am, Bm)[0])
    yt = float(F([c.x], [xt], [c.y], chuo)[0])
    dz = CHUO_DZ if (chuo and mn.z >= 6.0) else 0.0
    o.matrix_world = Matrix.Translation(Vector((xt - c.x, yt - c.y, dz))) @ o.matrix_world
    o["V5_relayout"] = True
    STATS["objects_moved"] += 1
    if chuo:
        STATS["chuo_objects"] += 1


def process_curve(o):
    cu = o.data
    if cu.users > 1:
        o.data = cu.copy(); cu = o.data
    mw = o.matrix_world.copy(); inv = mw.inverted()
    bb = [mw @ Vector(c) for c in o.bound_box]
    c = sum(bb, Vector()) / 8
    chuo = chuo_by_name(o.name) or (c.y < 40.0 and c.x < 130.0)
    dz = CHUO_DZ if chuo else 0.0

    def mp(p):
        w = mw @ p
        y = float(F([w.x], [w.x], [w.y], chuo)[0])
        return inv @ Vector((w.x, y, w.z + dz))
    for sp in cu.splines:
        for bp in sp.bezier_points:
            bp.co = mp(bp.co); bp.handle_left = mp(bp.handle_left); bp.handle_right = mp(bp.handle_right)
        for p in sp.points:
            v = mp(Vector(p.co[:3])); p.co = (v.x, v.y, v.z, p.co[3])
    o["V5_relayout"] = True
    STATS["curves"] += 1


# ------------------------------------------------------------------ trains
def collection_xspan(col):
    xs = []
    for ob in col.all_objects:
        if ob.type in ('MESH', 'CURVE'):
            xs += [(ob.matrix_world @ Vector(c)).x for c in ob.bound_box]
    if not xs:
        return 10.0
    off = col.instance_offset.x if hasattr(col, "instance_offset") else 0.0
    return (max(xs) - min(xs)) / 2


def swap_curve_following_cabs():
    """V3 kept three hand-bent "curve-following" box-built cab cars for the old curved layout; on the re-laid
    track every car is rigid and placed by its bogies, so they become ordinary instances of the one-piece
    E233-3000 cab master (cab at local +x in both)."""
    base = bpy.data.collections.get("E233-3000 style cab | procedural")
    out = []
    for e in bpy.data.objects:
        col = e.instance_collection if e.type == 'EMPTY' else None
        if base and col and col.name.startswith("V3 curve-following"):
            e["V5_master_before"] = col.name
            e.instance_collection = base
            out.append(e.name)
    return out


_BOGIES = {}


def bogie_x(col):
    """Local x of the two bogie centres (mean of each axle pair)."""
    if col.name in _BOGIES:
        return _BOGIES[col.name]
    xs = []
    for ob in col.all_objects:
        if "axle shaft" in ob.name and not ob.get("V5_retired"):
            bb = [ob.matrix_basis @ Vector(c) for c in ob.bound_box]
            xs.append(sum(v.x for v in bb) / 8)
    xs.sort()
    r = ((xs[0] + xs[1]) / 2, (xs[-2] + xs[-1]) / 2) if len(xs) >= 4 else (-6.9, 6.9)
    _BOGIES[col.name] = r
    return r


def chord_pose(k, xc, yaw, ba, bb):
    """Car centre (x fixed) and yaw so that both bogie centres lie on the target centreline of track k."""
    psi = yaw
    for _ in range(6):
        c, s_ = math.cos(psi), math.sin(psi)
        ax, bx = xc + c * ba, xc + c * bb
        ay, by = float(np.interp(ax, GX, TGT[k])), float(np.interp(bx, GX, TGT[k]))
        psi = math.atan2(by - ay, bx - ax) if bb > ba else math.atan2(ay - by, ax - bx)
    yc = ay - math.sin(psi) * ba
    return yc, psi


def world_xspan(o):
    """Actual X span of an instanced collection in world space (formations need not be centred on the empty)."""
    col = o.instance_collection
    M = o.matrix_world @ Matrix.Translation(-col.instance_offset)
    xs = []
    for ob in col.all_objects:
        if ob.type in ('MESH', 'CURVE') and not ob.get("V5_retired"):
            xs += [(M @ (ob.matrix_basis @ Vector(c))).x for c in ob.bound_box]
    return (min(xs), max(xs)) if xs else (o.matrix_world.translation.x - 10, o.matrix_world.translation.x + 10)


def usable_range(k, A, B):
    """Part of the platform where the track is not in the south-wing jog (R < 150 m): trains stop short of it."""
    y = TGT[k]; h = 12
    yp = np.pad(y, h, mode="edge")
    kap = np.abs((yp[2 * h:] - 2 * yp[h:-h] + yp[:-2 * h]) / ((h * DX) ** 2))
    sharp = (kap > 1 / 150.0) & (GX > 60.0) & (GX < B + 30)
    if sharp.any():
        B = min(B, float(GX[np.argmax(sharp)]) - 3.0)
    return A, B


def process_trains():
    swapped = swap_curve_following_cabs()
    emp = [o for o in bpy.data.objects if o.type == 'EMPTY' and o.instance_type == 'COLLECTION' and o.instance_collection
           and "Taxi" not in o.instance_collection.name and any(c.name == "V3 06 | Rolling stock and people" for c in o.users_collection)]
    groups = {}
    for o in emp:
        p = o.matrix_world.translation
        best = min(ORDER, key=lambda k: abs(np.interp(p.x, GX, MOD[k]) - p.y))
        if abs(np.interp(p.x, GX, MOD[best]) - p.y) > 1.0:
            L.log("train empty off-track", o.name, tuple(p)); continue
        groups.setdefault(best, []).append(o)
    moved = {}
    for k, objs in groups.items():
        isl = TRACK_ISLAND[k]
        A, B = usable_range(k, *ISL[isl]["P"])
        spans = [world_xspan(o) for o in objs]
        s0 = min(a for a, b in spans); s1 = max(b for a, b in spans)
        dx = 0.0
        if s1 - s0 > (B - A) - 2:
            # longer than the platform: the Tokaido Shinkansen platforms continue north beyond the model site,
            # so keep the south end inside; otherwise centre
            dx = ((B - 1) - s1) if k in SHINKANSEN else ((A + B) / 2 - (s0 + s1) / 2)
        elif s0 < A + 1:
            dx = (A + 1) - s0
        elif s1 > B - 1:
            dx = (B - 1) - s1
        chuo = k in ("01", "02")
        for o in objs:
            p = o.matrix_world.translation.copy()
            xt = p.x + dx
            dang = track_angle(k, xt, True) - track_angle(k, p.x, False)
            yaw = o.rotation_euler.z + dang
            if o.instance_collection.name.startswith("V3 N700"):
                yt = float(F([p.x], [xt], [p.y], chuo)[0])        # formations: cars are placed in bend_formations
            else:
                ba, bb = bogie_x(o.instance_collection)
                yt, yaw = chord_pose(k, xt, yaw, ba, bb)
            o.location = (xt, yt, p.z + (CHUO_DZ if chuo else 0.0))
            o.rotation_euler.z = yaw
            o["V5_relayout"] = True
            STATS["trains"] += 1
        moved[k] = {"cars": len(objs), "dx": round(dx, 2), "span": [round(s0 + dx, 1), round(s1 + dx, 1)],
                    "usable": [A, B]}
    moved["_curve_following_cabs_replaced"] = swapped
    return moved


def bend_formations():
    """Multi-car formations that are a single collection instance (the two N700 sets) cannot follow a
    curved track as one rigid block: put every car of the formation on the target track and turn it to
    the local track direction.  Each car's present pose is measured from its bogie crossmembers (V3 had
    already turned the end cars to follow the old model curve)."""
    out = {}
    bpy.context.view_layer.update()          # empties were just moved: refresh matrix_world
    for e in bpy.data.objects:
        col = e.instance_collection if e.type == 'EMPTY' else None
        if not col or not col.name.startswith("V3 N700"):
            continue
        p = e.matrix_world.translation
        k = min(ORDER, key=lambda t: abs(np.interp(p.x, GX, TGT[t]) - p.y))
        E = e.matrix_world @ Matrix.Translation(-col.instance_offset)
        Einv = E.inverted()
        base_ang = math.atan2(E[1][0], E[0][0])

        def centre(o):
            bb = [o.matrix_basis @ Vector(c) for c in o.bound_box]
            return sum(bb, Vector()) / 8
        cm = {}
        for o in col.objects:
            m = re.search(r"N700 car (\d\d)", o.name)
            if m and "crossmember" in o.name:
                cm.setdefault(int(m.group(1)), []).append(centre(o))
        if len(cm) < 4:
            continue
        pose = {}
        bog = {}
        for c, pts in cm.items():
            xs = np.array([q.x for q in pts]); ys = np.array([q.y for q in pts]); zs = np.array([q.z for q in pts])
            ctr = Vector((float(xs.mean()), float(ys.mean()), 0.0))
            a_ = xs < xs.mean(); b_ = ~a_
            if a_.any() and b_.any():
                ang = math.atan2(ys[b_].mean() - ys[a_].mean(), xs[b_].mean() - xs[a_].mean())
                bog[c] = (Vector((float(xs[a_].mean()), float(ys[a_].mean()), float(zs.mean()))),
                          Vector((float(xs[b_].mean()), float(ys[b_].mean()), float(zs.mean()))))
            else:
                ang = 0.0
            pose[c] = (ctr, ang)
        order_c = sorted(pose, key=lambda c: pose[c][0].x)
        bounds = [(pose[a][0].x + pose[b][0].x) / 2 for a, b in zip(order_c[:-1], order_c[1:])]
        groups = {}
        for o in col.objects:
            idx = int(np.searchsorted(bounds, centre(o).x))
            groups.setdefault(order_c[idx], []).append(o)
        for c, objs in groups.items():
            ctr_l, ang_l = pose[c]
            C = E @ ctr_l
            if c in bog:
                # both bogie centres of the car on the target centreline (V5.1)
                Aw, Bw = E @ bog[c][0], E @ bog[c][1]
                psi_cur = math.atan2(Bw.y - Aw.y, Bw.x - Aw.x)
                half = 0.5 * math.hypot(Bw.x - Aw.x, Bw.y - Aw.y)
                xm = 0.5 * (Aw.x + Bw.x)
                psi = psi_cur
                for _ in range(6):
                    ax, bx = xm - math.cos(psi) * half, xm + math.cos(psi) * half
                    ay, by = float(np.interp(ax, GX, TGT[k])), float(np.interp(bx, GX, TGT[k]))
                    psi = math.atan2(by - ay, bx - ax)
                D = (Matrix.Translation(Vector((ax, ay, Aw.z))) @ Matrix.Rotation(psi - psi_cur, 4, 'Z')
                     @ Matrix.Translation(-Aw))
            else:
                yt = float(np.interp(C.x, GX, TGT[k]))
                ang_t = track_angle(k, C.x, True)
                D = (Matrix.Translation(Vector((C.x, yt, C.z))) @ Matrix.Rotation(ang_t - (base_ang + ang_l), 4, 'Z')
                     @ Matrix.Translation(-C))
            W = Einv @ D @ E
            for o in objs:
                o.matrix_basis = W @ o.matrix_basis
        out[col.name] = {"track": k, "cars": len(groups)}
    return out


def fix_chuo_piers():
    """The Chuo viaduct's east pier row was mapped to where the old deck's east edge went - directly under the
    re-laid Chuo track 2, i.e. on top of track 3 (trains on track 3 ran through them).  Move those shafts west
    so they stand between track 3 and the building, clear of the track 3 kinematic envelope; the pier caps stay
    and carry the deck edge over track 3 as a cantilever."""
    o = bpy.data.objects.get("V4_Structure_Piers_caps_foundations")
    if o is None:
        return 0
    me = o.data
    n = len(me.vertices)
    mw = np.array(o.matrix_world); inv = np.linalg.inv(mw)
    co = np.empty(n * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    W = co @ mw[:3, :3].T + mw[:3, 3]
    lab = mesh_islands(me)
    uniq, invl = np.unique(lab, return_inverse=True)
    moved = 0
    for i in range(len(uniq)):
        sel = invl == i
        P = W[sel]
        mn, mx = P.min(0), P.max(0)
        if not (mx[0] - mn[0] < 2.0 and mx[1] - mn[1] < 2.0 and mn[2] < 1.0 and mx[2] > 10.0):
            continue                                  # only full-height pier shafts
        xc, yc = (mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2
        if xc > 140 or yc > 45:
            continue
        t3 = float(np.interp(xc, GX, TGT["03"]))
        half_y = (mx[1] - mn[1]) / 2
        env = 1.50 + 0.40                              # car half width + clearance
        if abs(yc - t3) < env + half_y:
            target_yc = t3 - env - half_y - 0.05
            W[sel, 1] += target_yc - yc
            moved += 1
    loc = W @ inv[:3, :3].T + inv[:3, 3]
    me.vertices.foreach_set("co", loc.ravel()); me.update()
    return moved


def add_gap_fillers():
    """Where two neighbouring islands moved far apart (e.g. the wedge north of 14-15 / 16-17, where 14-15
    follows the Tohoku Shinkansen curve and 16-19 stay straight) the original 4.2 m inter-track deck is
    stretched many times over; cover it with one clean deck surface so hairline gaps of the original
    pieces do not open up into visible slots."""
    mat = bpy.data.materials.get("V4_Structure_MAT_concrete")
    col = bpy.data.collections.get("V4_Structure_Decks") or L.collection("V4_Structure_Decks")
    verts, faces = [], []
    xs = np.arange(-207.0, 243.01, 2.0)
    n_strips = 0
    for a, b in zip(GEN[:-1], GEN[1:]):
        if TRACK_ISLAND[a] == TRACK_ISLAND[b]:
            continue
        ya = np.interp(xs, GX, TGT[a]) + 2.3
        yb = np.interp(xs, GX, TGT[b]) - 2.3
        ga = np.interp(xs, GX, MOD[b]) - np.interp(xs, GX, MOD[a])
        gt = np.interp(xs, GX, TGT[b]) - np.interp(xs, GX, TGT[a])
        ok = (yb - ya > 0.3) & (gt - ga > 1.0)
        run = []
        for i in range(len(xs)):
            if ok[i]:
                run.append(i)
            if run and (not ok[i] or i == len(xs) - 1):
                if len(run) >= 2:
                    o = len(verts)
                    for j in run:
                        verts += [(xs[j], ya[j], 4.606), (xs[j], yb[j], 4.606)]
                    for k in range(len(run) - 1):
                        faces.append((o + 2 * k, o + 2 * k + 2, o + 2 * k + 3, o + 2 * k + 1))
                    n_strips += 1
                run = []
    if not faces:
        return 0
    me = bpy.data.meshes.new("V5 relayout deck infill between separated islands")
    me.from_pydata(verts, [], faces)
    if mat:
        me.materials.append(mat)
    me.update()
    ob = bpy.data.objects.new(me.name, me)
    col.objects.link(ob)
    ob["V5_relayout"] = True
    return n_strips


def process_cameras_lights():
    n = 0
    for o in bpy.data.objects:
        if o.type not in ('CAMERA', 'LIGHT') or o.get("V5_relayout"):
            continue
        p = o.matrix_world.translation
        if p.y > WEST_ANCHOR and p.z < 100:
            yt = float(F([p.x], [p.x], [p.y], False)[0])
            o.matrix_world = Matrix.Translation(Vector((0, yt - p.y, 0))) @ o.matrix_world
            o["V5_relayout"] = True
            n += 1
    return n


WING_COLS = ("V3 01 | Architecture and real openings", "V3 02 | Windows stonework and porticos",
             "V3 03 | Slate roofs and domes")


def bend_south_wing():
    """V5.2: bend the south wing back onto the GSI building outline (see south_wing.py)."""
    import south_wing as SW
    cols = [c for c in bpy.data.collections if c.name in WING_COLS or c.name.startswith("V4_Architecture_")]
    seen, n_obj, n_v, mx = set(), 0, 0, 0.0
    for c in cols:
        for o in c.all_objects:
            if o.name in seen or o.get("V5_retired"):
                continue
            seen.add(o.name)
            M = np.array(o.matrix_world)
            if o.type == 'MESH' and len(o.data.vertices):
                if o.data.users > 1:
                    o.data = o.data.copy()
                me = o.data
                co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
                W = co @ M[:3, :3].T + M[:3, 3]
                bx, by = SW.bend_xy(W[:, 0], W[:, 1])
                d = np.hypot(bx - W[:, 0], by - W[:, 1])
                if d.max() < 1e-4:
                    continue
                W[:, 0], W[:, 1] = bx, by
                Mi = np.linalg.inv(M)
                me.vertices.foreach_set("co", (W @ Mi[:3, :3].T + Mi[:3, 3]).ravel())
                me.update()
                n_obj += 1; n_v += int((d > 1e-4).sum()); mx = max(mx, float(d.max()))
            elif o.type == 'CURVE':
                moved = False
                Mi = np.linalg.inv(M)
                for sp in o.data.splines:
                    pts = list(sp.bezier_points) if sp.type == 'BEZIER' else list(sp.points)
                    for p in pts:
                        if sp.type == 'BEZIER':
                            for attr in ("co", "handle_left", "handle_right"):
                                v = M @ np.append(np.array(getattr(p, attr)), 1.0)
                                bx, by = SW.bend_xy([v[0]], [v[1]])
                                if abs(bx[0] - v[0]) + abs(by[0] - v[1]) > 1e-4:
                                    w = Mi @ np.array([bx[0], by[0], v[2], 1.0])
                                    setattr(p, attr, tuple(w[:3])); moved = True
                        else:
                            v = M @ np.append(np.array(p.co[:3]), 1.0)
                            bx, by = SW.bend_xy([v[0]], [v[1]])
                            if abs(bx[0] - v[0]) + abs(by[0] - v[1]) > 1e-4:
                                w = Mi @ np.array([bx[0], by[0], v[2], 1.0])
                                p.co = (w[0], w[1], w[2], p.co[3]); moved = True
                if moved:
                    n_obj += 1
    return {"objects": n_obj, "vertices": n_v, "max_move_m": round(mx, 2), "bend_deg": round(math.degrees(SW.THETA), 1)}


def run():
    model_extents()
    STATS["south_wing_bent"] = bend_south_wing()
    objs = [o for o in bpy.data.objects if is_bundle(o) and o.users_scene and not o.get("V5_retired")]
    L.log("bundle objects", len(objs))
    for o in objs:
        if o.type == 'MESH':
            if o.data.users > 1 and item_kind(o.name) != "end":
                process_small_object(o)
            else:
                process_mesh(o)
        elif o.type == 'CURVE':
            process_curve(o)
        elif o.type == 'FONT':
            process_small_object(o)
    STATS["chuo_piers_moved_clear_of_track_3"] = fix_chuo_piers()
    trains = process_trains()
    bent = bend_formations()
    ncam = process_cameras_lights()
    info_bent = bent
    STATS["gap_filler_strips"] = add_gap_fillers()
    info = dict(STATS)
    info["trains_by_track"] = trains
    info["formations_bent_to_curve"] = info_bent
    info["cameras_lights_moved"] = ncam
    info["chuo_raise_m"] = CHUO_DZ
    info["platform_curve_clearance_max_m"] = {k: round(float(v.max()), 3) for k, v in CLEARANCE.items()}
    info["islands"] = {k: {"target_centre_x0": round(v["target_center0"], 2), "target_width_x0": round(v["target_width0"], 2),
                           "model_centre_x0": round(v["model_center0"], 2), "platform_extent": v["P"], "canopy_extent": v["Q"]}
                       for k, v in ISL.items()}
    for k, v in STATS.items():
        L.log(k, v)
    return info


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    bpy.ops.wm.open_mainfile(filepath=src, load_ui=False, use_scripts=False)
    info = run()
    bpy.context.scene["V5_relayout_summary"] = json.dumps(info)
    bpy.ops.wm.save_as_mainfile(filepath=dst, compress=True)
    print("SAVED", dst)
