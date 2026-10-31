"""V5: E5 long-nose end car (E523 / E514 type) as part of the one-piece E5 body.

The 15 m nose is a loft of the same half cross-section that the E5 intermediate cars use, so the nose surface
shares vertices and tangent with the straight body (no seam).  Along the nose the section is re-shaped by
control curves (d = distance from the nose tip, metres):
    TC(d)  deck centre height        WC(d)  half width          BC(d)  bottom height
    HH(d)  cockpit canopy hump       ZBAND(d)  height of the pink band (livery line)
    the tip is rounded over RR; the upper side gets tumblehome toward the tip (rounded section).
Values are fitted to the V4 shell proportions (nose 15 m, tip ~1.15 m above rail, cockpit glass x 4.2-6.5)
and to E5 photographs.  Canopy glazing, head/tail lamp units, crew doors and the coupler-cover seam are flush
overlays sampled on the shell facets (3.5-7 mm proud).  Also: under-nose obstacle deflector and the
full-perimeter gangway bellows used on every E5 car end.
"""
import math
import numpy as np

D_NOSE = 15.0
ZT, RR = 1.00, 0.90          # tip apex height (coupler height), length of the tip rounding
WH = 1.08                    # canopy hump half width
V_P0 = (1.86 - 0.48) / 3.225  # pink band rows of the E5 section (normalised height)
V_P1 = (1.99 - 0.48) / 3.225
V_PC = 0.5 * (V_P0 + V_P1)
D_PINK_END = 3.30            # pink band runs into the head lamp unit


def pchip(xk, yk, d_left=None, d_right=None):
    """Monotone cubic Hermite interpolation (Fritsch-Carlson); optional end slopes."""
    xk = np.asarray(xk, float)
    yk = np.asarray(yk, float)
    n = len(xk)
    h = np.diff(xk)
    dl = np.diff(yk) / h
    m = np.zeros(n)
    for k in range(1, n - 1):
        if dl[k - 1] * dl[k] > 0:
            w1, w2 = 2 * h[k] + h[k - 1], h[k] + 2 * h[k - 1]
            m[k] = (w1 + w2) / (w1 / dl[k - 1] + w2 / dl[k])

    def endslope(h0, h1, d0, d1):
        s = ((2 * h0 + h1) * d0 - h0 * d1) / (h0 + h1)
        if np.sign(s) != np.sign(d0):
            return 0.0
        if np.sign(d0) != np.sign(d1) and abs(s) > abs(3 * d0):
            return 3 * d0
        return s
    if n > 2:
        m[0] = endslope(h[0], h[1], dl[0], dl[1])
        m[-1] = endslope(h[-1], h[-2], dl[-1], dl[-2])
    else:
        m[:] = dl[0]
    if d_left is not None:
        m[0] = d_left
    if d_right is not None:
        m[-1] = d_right

    def f(x):
        xc = np.clip(np.asarray(x, float), xk[0], xk[-1])
        i = np.clip(np.searchsorted(xk, xc, side='right') - 1, 0, n - 2)
        t = (xc - xk[i]) / h[i]
        t2, t3 = t * t, t * t * t
        r = ((2 * t3 - 3 * t2 + 1) * yk[i] + (t3 - 2 * t2 + t) * h[i] * m[i]
             + (-2 * t3 + 3 * t2) * yk[i + 1] + (t3 - t2) * h[i] * m[i + 1])
        return float(r) if np.ndim(r) == 0 else r
    return f


# control curves -------------------------------------------------------------------------------------------
TC = pchip([0.0, 0.6, 1.5, 3.2, 5.0, 6.5, 8.0, 9.5, 11.0, 12.5, 13.8, 15.0],
           [1.30, 1.40, 1.55, 1.80, 2.07, 2.34, 2.61, 2.88, 3.15, 3.42, 3.62, 3.705], d_right=0.0)
HH = pchip([6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.5, 13.8, 15.0],
           [0.0, 0.06, 0.20, 0.29, 0.30, 0.25, 0.12, 0.03, 0.0], d_left=0.0, d_right=0.0)
WC = pchip([0.0, 0.6, 1.5, 3.2, 6.2, 8.2, 10.2, 12.5, 15.0],
           [0.60, 0.68, 0.93, 1.21, 1.41, 1.54, 1.64, 1.675, 1.675], d_right=0.0)
BC = pchip([0.0, 0.6, 1.43, 2.5, 3.5, 4.5, 15.0],
           [0.74, 0.66, 0.57, 0.52, 0.495, 0.48, 0.48], d_right=0.0)
ZBAND = pchip([0.0, 1.0, 2.0, 3.2, 5.0, 7.0, 9.0, 11.0, 12.5, 15.0],
              [1.00, 1.08, 1.17, 1.28, 1.43, 1.59, 1.74, 1.85, 1.90, 1.925], d_right=0.0)

STATIONS = [0.012, 0.035, 0.07, 0.115, 0.17, 0.235, 0.31, 0.40, 0.50, 0.62, 0.76, 0.92, 1.10, 1.30, 1.52, 1.76,
            2.02, 2.30, 2.60, 2.92, 3.30, 3.65, 4.0, 4.4, 4.8, 5.2, 5.6, 6.0, 6.3, 6.6, 6.9, 7.2, 7.5, 7.8, 8.1,
            8.4, 8.7, 9.0, 9.3, 9.6, 9.9, 10.25, 10.6, 11.0, 11.4, 11.8, 12.2, 12.65, 13.1, 13.6, 14.1, 14.55, 15.0]


def smoothstep(e0, e1, x):
    t = min(max((x - e0) / (e1 - e0), 0.0), 1.0)
    return t * t * (3 - 2 * t)


class NoseGrid:
    """Vertex grid of the nose loft (right half, y >= 0): stations d (ascending) x profile points j."""

    def __init__(self, H, x_tip, D=D_NOSE, stations=STATIONS, tumble=0.85):
        Hn = np.array(H, float)
        self.nH = len(Hn)
        u = Hn[:, 0] / 1.675
        v = (Hn[:, 1] - 0.48) / 3.225
        self.v = v
        self.d = np.array(sorted(set(round(x, 5) for x in list(stations) + [D] if 0.0 < x <= D)))
        self.x_tip = x_tip
        self.X = x_tip - self.d
        nS = len(self.d)
        Y = np.zeros((nS, self.nH))
        Z = np.zeros((nS, self.nH))
        tent = np.where(v <= V_PC, v / V_PC, (1 - v) / (1 - V_PC))
        for i, d in enumerate(self.d):
            r = 1.0 if d >= RR else math.sqrt(max(0.0, 1 - (1 - d / RR) ** 2))
            T = ZT + (TC(d) - ZT) * r
            Bz = ZT - (ZT - BC(d)) * r
            W = WC(d) * r
            se = smoothstep(9.0, 1.0, d)
            k = 1 - se * tumble * np.maximum(0.0, v - 0.25) ** 2
            nat = Bz + V_PC * (T - Bz)
            delta = min(max((ZBAND(d) - nat) / (T - Bz), 0.0), 0.13) * smoothstep(1.2, 2.5, d)
            y = W * u * k
            z = Bz + (v + delta * tent) * (T - Bz)
            if 6.0 < d < D:
                z = z + HH(d) * np.clip(1 - (y / WH) ** 2, 0.0, None) ** 2
            Y[i], Z[i] = y, z
        self.Y, self.Z = Y, Z
        self.zmid = 0.5 * (Z.min(1) + Z.max(1))
        # landmark rows
        self.j_wt = max(j for j in range(self.nH) if Hn[j, 0] >= 1.675 - 1e-6 and Hn[j, 1] <= 3.0 + 1e-6)
        self.j_p0 = int(np.argmin(np.abs(Hn[:, 1] - 1.86) + (Hn[:, 0] < 1.0) * 9))
        self.j_p1 = int(np.argmin(np.abs(Hn[:, 1] - 1.99) + (Hn[:, 0] < 1.0) * 9))

    # bilinear sampling on the facets -------------------------------------------------------------------
    def sec(self, d):
        d = min(max(d, self.d[0]), self.d[-1])
        i = int(np.clip(np.searchsorted(self.d, d) - 1, 0, len(self.d) - 2))
        t = (d - self.d[i]) / (self.d[i + 1] - self.d[i])
        return self.Y[i] * (1 - t) + self.Y[i + 1] * t, self.Z[i] * (1 - t) + self.Z[i + 1] * t

    def pt(self, d, jf, s=1):
        y, z = self.sec(d)
        jf = min(max(jf, 0.0), self.nH - 1.0)
        j = int(min(math.floor(jf), self.nH - 2))
        u = jf - j
        return np.array([self.x_tip - d, s * (y[j] * (1 - u) + y[j + 1] * u), z[j] * (1 - u) + z[j + 1] * u])

    def nrm(self, d, jf, s=1):
        e = 0.012
        a = self.pt(d - e, jf, s) - self.pt(d + e, jf, s)          # toward +x
        j0, j1 = max(jf - 0.05, 0.0), min(jf + 0.05, self.nH - 1.0)
        b = self.pt(d, j1, s) - self.pt(d, j0, s)
        n = np.cross(a, b)
        p = self.pt(d, jf, s)
        ref = np.array([0.6, p[1], p[2] - 1.6])
        if np.dot(n, ref) < 0:
            n = -n
        ln = np.linalg.norm(n)
        return n / ln if ln > 1e-12 else np.array([0.0, s * 1.0, 0.0])

    def jf_top(self, d, yq):
        """Fractional profile index on the upper surface (shoulder + roof) where |y| == yq."""
        y, _ = self.sec(d)
        for j in range(self.j_wt, self.nH - 1):
            if y[j] >= yq >= y[j + 1]:
                return j + (y[j] - yq) / max(1e-9, y[j] - y[j + 1])
        return float(self.j_wt) if yq > y[self.j_wt] else float(self.nH - 1)

    def jf_side(self, d, zq):
        """Fractional profile index on the side where z == zq (z increases with j from j=1)."""
        _, z = self.sec(d)
        for j in range(1, self.nH - 1):
            if z[j] <= zq <= z[j + 1]:
                return j + (zq - z[j]) / max(1e-9, z[j + 1] - z[j])
        return 1.0 if zq < z[1] else float(self.nH - 1)

    def on_top(self, d, y, off):
        s = 1 if y >= 0 else -1
        jf = self.jf_top(d, abs(y))
        n = self.nrm(d, jf, s)
        return self.pt(d, jf, s) + n * off, n

    def on_side(self, s):
        def f(d, z, off):
            jf = self.jf_side(d, z)
            n = self.nrm(d, jf, s)
            return self.pt(d, jf, s) + n * off, n
        return f


# ---------------------------------------------------------------------------------------------- helpers
def _v(B, p):
    return B.vert((float(p[0]), float(p[1]), float(p[2])))


def _grid(B, G, mat):
    """G: rows of (point, normal)."""
    idx = [[_v(B, p) for p, _ in row] for row in G]
    for a in range(len(G) - 1):
        for b in range(len(G[a]) - 1):
            n = G[a][b][1]
            B.face([idx[a][b], idx[a + 1][b], idx[a + 1][b + 1], idx[a][b + 1]], mat,
                   want=(float(n[0]), float(n[1]), float(n[2])))


def _ring(B, inner, outer, mat):
    iv = [_v(B, p) for p, _ in inner]
    ov = [_v(B, p) for p, _ in outer]
    n = len(iv)
    for k in range(n):
        k2 = (k + 1) % n
        nn = inner[k][1]
        B.face([iv[k], ov[k], ov[k2], iv[k2]], mat, want=(float(nn[0]), float(nn[1]), float(nn[2])))


def _fan(B, centre, loop, mat):
    c = _v(B, centre[0])
    lv = [_v(B, p) for p, _ in loop]
    nn = centre[1]
    for k in range(len(lv)):
        B.face([c, lv[k], lv[(k + 1) % len(lv)]], mat, want=(float(nn[0]), float(nn[1]), float(nn[2])))


def offset_loop(loop, dist):
    """Offset a closed convex loop of 2D param points outward (dist > 0) or inward (dist < 0)."""
    P = np.array(loop, float)
    c = P.mean(0)
    out = []
    for k in range(len(P)):
        t = P[(k + 1) % len(P)] - P[k - 1]
        n = np.array([t[1], -t[0]])
        ln = np.linalg.norm(n)
        n = n / ln if ln > 1e-12 else n
        if np.dot(n, P[k] - c) < 0:
            n = -n
        out.append(tuple(P[k] + n * dist))
    return out


def cosspace(a, b, n):
    return [a + (b - a) * (0.5 - 0.5 * math.cos(math.pi * k / (n - 1))) for k in range(n)]


def rr_span(a, a0, a1, b0, b1, rc):
    """Rounded rectangle [a0,a1]x[b0,b1]: (lo, hi) of b at a."""
    sh = 0.0
    for da in (a - a0, a1 - a):
        if da < rc:
            sh = max(sh, rc - math.sqrt(max(0.0, rc * rc - (rc - da) ** 2)))
    return b0 + sh, b1 - sh


def span_patch(B, mapf, a_rows, span, mat, off, ncol=10):
    """Patch between b = span(a)[0..1] for a in a_rows; mapf(a, b, off) -> (p, n)."""
    G = []
    for a in a_rows:
        lo, hi = span(a)
        G.append([mapf(a, lo + (hi - lo) * c / (ncol - 1), off) for c in range(ncol)])
    _grid(B, G, mat)


def span_loop(a_rows, span, n_end=6):
    lo_side = [(a, span(a)[0]) for a in a_rows]
    hi_side = [(a, span(a)[1]) for a in a_rows]
    a1, a0 = a_rows[-1], a_rows[0]
    e1 = [(a1, span(a1)[1] + (span(a1)[0] - span(a1)[1]) * k / n_end) for k in range(1, n_end)]
    e0 = [(a0, span(a0)[0] + (span(a0)[1] - span(a0)[0]) * k / n_end) for k in range(1, n_end)]
    return hi_side + e1 + lo_side[::-1] + e0


def outline_ring(B, mapf, loop, w_in, w_out, mat, off):
    inner = [mapf(a, b, off) for a, b in offset_loop(loop, -w_in)]
    outer = [mapf(a, b, off) for a, b in offset_loop(loop, w_out)]
    _ring(B, inner, outer, mat)


# ------------------------------------------------------------------------------------------------ build
def build_nose(B, H, M, x_tip):
    """Loft + overlays into Body B.  Returns stats."""
    ng = NoseGrid(H, x_tip)
    nS, nH = len(ng.d), ng.nH
    vid = {}

    def P(i, j, s):
        if abs(ng.Y[i, j]) < 1e-9:
            s = 1
        key = (i, j, s)
        if key not in vid:
            vid[key] = B.vert((float(ng.X[i]), float(s * ng.Y[i, j]), float(ng.Z[i, j])))
        return vid[key]

    def want(q, i):
        c = np.mean([B.v[k] for k in q], 0)
        return (0.5, float(c[1]), float(c[2] - ng.zmid[i]))

    def zone(dm, j):
        vm = 0.5 * (ng.v[j] + ng.v[j + 1])
        if vm < V_P0:
            return M["e5_white"]
        if vm < V_P1:
            return M["e5_pink"] if dm > D_PINK_END else M["e5_white"]
        return M["e5_green"]

    nf0 = len(B.f)
    for i in range(nS - 1):
        dm = 0.5 * (ng.d[i] + ng.d[i + 1])
        for j in range(nH - 1):
            mat = zone(dm, j)
            for s in (1, -1):
                q = [P(i, j, s), P(i + 1, j, s), P(i + 1, j + 1, s), P(i, j + 1, s)]
                B.face(q, mat, want=want(q, i))
    tip = B.vert((float(x_tip), 0.0, ZT))
    for j in range(nH - 1):
        mat = zone(0.0, j)
        for s in (1, -1):
            q = [tip, P(0, j, s), P(0, j + 1, s)]
            B.face(q, mat, want=want(q, 0))
    stats = {"nose_stations": int(nS), "nose_faces": len(B.f) - nf0}

    # cockpit canopy glazing -------------------------------------------------------------------------------
    df, dr, hwf, hwr, rc = 6.90, 9.55, 0.40, 1.18, 0.25

    def hw(d):
        base = hwf + (hwr - hwf) * (d - df) / (dr - df)
        sh = 0.0
        for da in (d - df, dr - d):
            if da < rc:
                sh = max(sh, rc - math.sqrt(max(0.0, rc * rc - (rc - da) ** 2)))
        return max(base - sh, 0.0)
    rows = cosspace(df, dr, 30)
    span = lambda d: (-hw(d), hw(d))
    span_patch(B, ng.on_top, rows, span, M["glass"], 0.0055, ncol=25)
    loop = span_loop(rows, span, n_end=12)
    outline_ring(B, ng.on_top, loop, 0.012, 0.045, M["rubber"], 0.0042)

    # head / tail lamp units (both sides): slim teardrop housing on the livery line --------------------------
    jc = 0.5 * (ng.j_p0 + ng.j_p1)
    zc = lambda d: float(ng.pt(d, jc)[2])
    l0, l1, h0, h1 = 2.40, 3.35, 0.040, 0.078

    def lamp_hh(d, grow=0.0, a=l0, b=l1, ha=h0, hb=h1, pw=4):
        L = (b - a) + 2 * grow
        dm = 0.5 * (a + b)
        base = ha + (hb - ha) * (d - a) / (b - a) + grow
        e = min(abs(d - dm) / (L / 2), 1.0)
        return max(base, 0.0) * (1 - e ** pw) ** (1 / pw)

    for s in (1, -1):
        side = ng.on_side(s)
        g = 0.028
        rws = cosspace(l0 - g + 0.003, l1 + g - 0.003, 26)
        span_patch(B, side, rws, lambda d: (zc(d) - lamp_hh(d, g), zc(d) + lamp_hh(d, g)), M["black"], 0.0040, ncol=8)
        rws = cosspace(l0 + 0.003, l1 - 0.003, 24)
        span_patch(B, side, rws, lambda d: (zc(d) - lamp_hh(d), zc(d) + lamp_hh(d)), M["hl_reflector"], 0.0055, ncol=8)
        # main (HID) lamp capsule, auxiliary lamp, red tail-lamp strip
        hl, tl = M.get("head_lit", M["hl_optic"]), M.get("tail_lit", M["tail"])
        for a, b, ha, hb, zo, mat in ((2.93, 3.27, 0.034, 0.046, 0.004, hl),
                                      (2.62, 2.86, 0.026, 0.032, 0.002, hl),
                                      (2.44, 2.58, 0.012, 0.016, -0.014, tl)):
            rws = cosspace(a + 0.002, b - 0.002, 12)
            span_patch(B, side, rws, lambda d, a=a, b=b, ha=ha, hb=hb, zo=zo: (
                zc(d) + zo - lamp_hh(d, 0.0, a, b, ha, hb, 4), zc(d) + zo + lamp_hh(d, 0.0, a, b, ha, hb, 4)),
                mat, 0.0068, ncol=5)

    # crew doors (seam outline, droplight window, recessed handle) ---------------------------------------------
    for s in (1, -1):
        side = ng.on_side(s)
        a0, a1, b0, b1, rcd = 9.85, 10.55, 1.26, 2.62, 0.09
        rws = cosspace(a0, a1, 16)
        sp = lambda a: rr_span(a, a0, a1, b0, b1, rcd)
        outline_ring(B, side, span_loop(rws, sp, 8), 0.006, 0.006, M["rubber"], 0.0035)
        w0, w1, z0, z1, rcw = 9.98, 10.42, 2.10, 2.48, 0.06
        rws = cosspace(w0, w1, 14)
        sp = lambda a: rr_span(a, w0, w1, z0, z1, rcw)
        span_patch(B, side, rws, sp, M["glass"], 0.0050, ncol=8)
        outline_ring(B, side, span_loop(rws, sp, 6), 0.008, 0.026, M["rubber"], 0.0040)
        rws = cosspace(10.41, 10.47, 4)
        span_patch(B, side, rws, lambda a: (1.78, 1.98), M["dark"], 0.0040, ncol=4)

    # coupler-cover seam around the nose cone --------------------------------------------------------------------
    for s in (1, -1):
        G = []
        for d in (0.618, 0.622):
            G.append([(ng.pt(d, jf, s) + ng.nrm(d, jf, s) * 0.003, ng.nrm(d, jf, s))
                      for jf in np.linspace(0.0, nH - 1.0, 4 * (nH - 1) + 1)])
        _grid(B, G, M["dark"])

    # obstacle deflector under the nose -------------------------------------------------------------------------
    _snowplow(B, ng, M["plow"])
    return stats


def _snowplow(B, ng, mat):
    apex, rear, half, th = 1.55, 3.60, 0.82, 0.06
    zb = 0.25
    for s in (1, -1):
        pts_o, pts_i = [], []
        for t in np.linspace(0.0, 1.0, 7):
            d = apex + (rear - apex) * t
            y = s * half * t
            _, z = ng.sec(d)
            ztop = float(z[0]) + 0.05
            pts_o.append((ng.x_tip - d, y, ztop))
            # inner face: offset toward the rear/centre
            pts_i.append((ng.x_tip - d - th, y - s * th * 0.35, ztop))
        ob = [B.vert((p[0], p[1], zb)) for p in pts_o]
        ot = [B.vert(p) for p in pts_o]
        ib = [B.vert((p[0], p[1], zb + 0.01)) for p in pts_i]
        it = [B.vert(p) for p in pts_i]
        for k in range(len(pts_o) - 1):
            B.face([ob[k], ob[k + 1], ot[k + 1], ot[k]], mat, want=(1.0, s * 0.6, 0.0))
            B.face([ib[k], ib[k + 1], it[k + 1], it[k]], mat, want=(-1.0, -s * 0.6, 0.0))
            B.face([ob[k], ob[k + 1], ib[k + 1], ib[k]], mat, want=(0.0, 0.0, -1.0))
        B.face([ob[-1], ib[-1], it[-1], ot[-1]], mat, want=(0.0, s * 1.0, 0.0))


def bellows(B, H, N, xe, end, mat):
    """Full-perimeter gangway bellows at a car end (x = xe, end = +1 front / -1 rear), flush with the body."""
    rings = [(-0.05, 0.020), (0.0, 0.020), (0.022, 0.040), (0.045, 0.020), (0.068, 0.040), (0.090, 0.020),
             (0.112, 0.026)]
    nH = len(H)
    R = []
    for dx, ins in rings:
        x = xe + end * dx
        ring = {}
        for s in (1, -1):
            ring[s] = [B.vert((x, s * (H[j][0] - N[j].x * ins), H[j][1] - N[j].y * ins)) for j in range(nH)]
        R.append(ring)
    for k in range(len(R) - 1):
        for s in (1, -1):
            a, b = R[k][s], R[k + 1][s]
            for j in range(nH - 1):
                nn = N[j] + N[j + 1]
                B.face([a[j], b[j], b[j + 1], a[j + 1]], mat, want=(0.0, s * nn.x, nn.y))
    return len(R)
