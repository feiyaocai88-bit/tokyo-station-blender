"""Build the target track layout for the Tokyo Station re-layout from GSI data.

Inputs
  model_layout.json   model track centrelines (V3 sleeper beds)
  gsi_tracked.json    GSI RailTrCL (optimal_bvmap-v1, z16) track centrelines, georeferenced to model
                      coordinates and followed outward from the station centre
  building_edge.json  east edge of the model's Marunouchi building per 1 m of X
Output
  targets.json        model and target centreline of every track on a 0.5 m X grid, platform and
                      canopy extents, Chuo-line raise
"""
import json, sys, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
GEO = "/home/claude/geo"
X = np.round(np.arange(-262.0, 262.01, 0.5), 2)

ORDER = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10',
         '20', '21', '22', '23', '14', '15', '16', '17', '18', '19']
SHINKANSEN = {'14', '15', '16', '17', '18', '19', '20', '21', '22', '23'}

# island: (name, west track, east track, edge offset, platform extent P, canopy extent Q)
# P / Q measured on the GSI seamless aerial photo (unrolled along each island), north ends clipped
# to the model site (tracks end at X = -207).
ISLANDS = [
    ("01-02", "01", "02", 1.59, (-145.0, 112.0), (-142.0, 108.0)),
    ("03-04", "03", "04", 1.59, (-140.0, 128.0), (-132.0, 112.0)),
    ("05-06", "05", "06", 1.59, (-135.0, 152.0), (-122.0, 105.0)),
    ("07-08", "07", "08", 1.59, (-190.0, 150.0), (-188.0, 145.0)),
    ("09-10", "09", "10", 1.59, (-192.0, 152.0), (-188.0, 148.0)),
    ("20-21", "20", "21", 1.75, (-204.0, 190.0), (-204.0, 187.0)),
    ("22-23", "22", "23", 1.75, (-204.0, 185.0), (-204.0, 180.0)),
    ("14-15", "14", "15", 1.75, (-204.0, 198.0), (-204.0, 186.0)),
    ("16-17", "16", "17", 1.75, (-204.0, 212.0), (-204.0, 210.0)),
    ("18-19", "18", "19", 1.75, (-204.0, 212.0), (-204.0, 210.0)),
]
CHUO_RAISE = 7.0          # Chuo deck must clear the 3-4 portal crossbeams under it
TRACK3_UNDER_CHUO = 0.6   # track 3 runs under Chuo track 2, 0.6 m further east (GSI shows one line)


def smooth(y, win):
    if win <= 1:
        return y
    k = np.ones(win) / win
    pad = win // 2
    yp = np.concatenate([np.full(pad, y[0]), y, np.full(win - 1 - pad, y[-1])])
    return np.convolve(yp, k, mode="valid")


def gsmooth(y, sigma_m, dx=0.5):
    n = int(4 * sigma_m / dx) * 2 + 1
    k = np.exp(-0.5 * ((np.arange(n) - n // 2) * dx / sigma_m) ** 2)
    k /= k.sum()
    yp = np.concatenate([np.full(n // 2, y[0]), y, np.full(n // 2, y[-1])])
    return np.convolve(yp, k, mode="valid")


def curvature(y, h=12, dx=0.5):
    yp = np.pad(y, h, mode="edge")
    return (yp[2 * h:] - 2 * yp[h:-h] + yp[:-2 * h]) / ((h * dx) ** 2)


def _dilate(m, half_m, dx=0.5):
    out = m.copy()
    for i in range(1, int(half_m / dx) + 1):
        out[i:] |= m[:-i]; out[:-i] |= m[i:]
    return out


def _widen(d, half_m, dx=0.5):
    out = d.copy()
    for i in range(1, int(half_m / dx) + 1):
        out[i:] = np.maximum(out[i:], d[:-i]); out[:-i] = np.maximum(out[:-i], d[i:])
    return out


def limit_curvature(y0, rmin=250.0, maxdev=0.6, protect=None, iters=600):
    """Relax kinks (joins between GSI segments, places where spacing rules switched on) to R >= rmin,
    moving the line by at most maxdev; straight and gently curved sections are not touched."""
    y = y0.copy()
    for _ in range(iters):
        m = _dilate(np.abs(curvature(y)) > 1.0 / rmin, 12.0)
        if protect is not None:
            m &= ~protect
        if not m.any():
            break
        ys = gsmooth(y, 2.5)
        y[m] += 0.5 * (ys[m] - y[m])
        y = np.clip(y, y0 - maxdev, y0 + maxdev)
    return y


def smoothstep(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def main():
    L = json.load(open(os.path.join(GEO, "model_layout.json")))
    G = json.load(open(os.path.join(GEO, "v2", "gsi_tracked.json")))
    BE = {int(k): v for k, v in json.load(open(os.path.join(HERE, "building_edge.json"))).items()}

    # ---------------- model: every track = m0 + common curve c(X)
    m0 = {k: float(np.interp(0, *np.array(L["tracks"][k]).T)) for k in ORDER}
    a = np.array(L["tracks"]["10"])
    c = np.interp(X, a[:, 0], a[:, 1]) - m0["10"]
    # linear extrapolation beyond the data with the end slopes
    lo, hi = a[0, 0], a[-1, 0]
    s_lo = (a[3, 1] - a[0, 1]) / (a[3, 0] - a[0, 0]); s_hi = (a[-1, 1] - a[-4, 1]) / (a[-1, 0] - a[-4, 0])
    c = np.where(X < lo, (a[0, 1] - m0["10"]) + s_lo * (X - lo), c)
    c = np.where(X > hi, (a[-1, 1] - m0["10"]) + s_hi * (X - hi), c)
    M = {k: m0[k] + c for k in ORDER}

    # ---------------- GSI tracks
    gs = {}
    for k, pts in G.items():
        p = np.array([(q[0], q[1]) for q in pts])
        gs[k] = smooth(np.interp(X, p[:, 0], p[:, 1]), 21)     # 10 m running mean
    # track 3 is not drawn by GSI under the Chuo viaduct: run it 0.6 m east of Chuo track 2;
    # south of the Chuo buffers (X 137) the tracker's "02" line already follows track 3
    blend = smoothstep((X - 130.0) / 14.0)
    gs["03"] = (gs["02"] + TRACK3_UNDER_CHUO) * (1 - blend) + gs["02"] * blend

    # ---------------- island centre / width curves
    T = {}
    info = {}
    for name, w, e, edge, P, Q in ISLANDS:
        tw, te = gs[w], gs[e]
        C = (tw + te) / 2
        Wg = (te - tw) - 2 * edge
        inside = (X >= P[0]) & (X <= P[1])
        W = np.where(inside, np.maximum(Wg, 4.0), np.nan)
        # smooth inside, hold + blend outside towards the GSI value over 40 m
        Wi = W.copy()
        idx = np.where(inside)[0]
        Wi[idx] = smooth(np.maximum(Wg[idx], 4.0), 41)
        W_n, W_s = Wi[idx[0]], Wi[idx[-1]]
        dn = np.clip(P[0] - X, 0, None); ds = np.clip(X - P[1], 0, None)
        out_n = W_n + (Wg - W_n) * smoothstep(dn / 40.0)
        out_s = W_s + (Wg - W_s) * smoothstep(ds / 40.0)
        Wf = np.where(inside, Wi, np.where(X < P[0], out_n, out_s))
        T[w] = C - Wf / 2 - edge
        T[e] = C + Wf / 2 + edge
        info[name] = {"west": w, "east": e, "edge": edge, "P": P, "Q": Q,
                      "model_center0": (m0[w] + m0[e]) / 2,
                      "target_center0": float(np.interp(0, X, C)),
                      "target_width0": float(np.interp(0, X, Wf)),
                      "model_width0": (m0[e] - m0[w]) - 2 * edge}

    # ---------------- constraints
    # (a) keep track 3 clear of the model's south wing.  V5.2: the wing itself is bent back onto the GSI outline
    #     (scripts/south_wing.py, applied to building_edge.json); what is left is a push of about 1 m, spread
    #     into a long, gentle bulge instead of the former S-bend.
    bx = np.array(sorted(BE)); by = np.array([BE[k] for k in bx])
    bedge = np.maximum.reduce([np.interp(X + d, bx + 0.5, by, left=-1e9, right=-1e9) for d in (-4, -2, 0, 2, 4)])
    south = X > 120
    need3 = np.where(south, bedge + 3.6, -1e9)
    push0 = np.maximum(need3 - T["03"], 0.0)
    push = gsmooth(_widen(push0, 30.0), 20.0)
    if push0.max() > 0:
        push *= max(1.0, float(np.max(push0[push0 > 0] / np.maximum(push[push0 > 0], 1e-6))))
    T["03"] = T["03"] + push
    print("south-wing push of track 03: max %.2f m over X %.0f..%.0f" % (push.max(), X[push > 0.01].min() if (push > 0.01).any() else 0,
          X[push > 0.01].max() if (push > 0.01).any() else 0))
    # (b) minimum spacing between neighbouring tracks (track 2/3 are stacked, exempt)
    seq = [k for k in ORDER]
    for it in range(200):
        moved = 0.0
        for i in range(len(seq) - 1):
            k1, k2 = seq[i], seq[i + 1]
            if (k1, k2) == ("02", "03"):
                continue
            if k1 in ("01", "02"):
                continue
            smin = 4.3 if (k1 in SHINKANSEN or k2 in SHINKANSEN) else 4.0
            same = any(w == k1 and e == k2 for _, w, e, *_ in ISLANDS)
            if same:
                smin = max(smin, 3.18 + 4.0)
            gap = T[k2] - T[k1]
            d = np.clip(smin - gap, 0, None)
            if d.max() > 1e-4:
                # track 3 is pinned by the building on its west side; push east neighbours only there
                if k1 == "03":
                    T[k2] = T[k2] + d
                else:
                    T[k1] = T[k1] - d / 2
                    T[k2] = T[k2] + d / 2
                moved = max(moved, float(d.max()))
        if moved < 1e-3:
            break
    # (c) Chuo pair spacing >= 4 m where it extends beyond the platform
    d = np.clip(4.2 - (T["02"] - T["01"]), 0, None)
    T["01"] -= d / 2; T["02"] += d / 2
    # (d) V5.1: local curvature limit R >= 250 m (cars on the old kinks stood up to 0.17 m off their rails and
    #     cut into platform edges).  Lines move <= 0.6 m.  V5.2: applies to every track (no more south-wing jog).
    #     Then the spacing rule again, with smooth corrections.
    T0 = {k: T[k].copy() for k in ORDER}
    for k in ORDER:
        T[k] = limit_curvature(T[k], 250.0, 0.6, None)
    # beyond the platform ends (station throats, no platform edge to respect) relax the remaining GSI kinks
    # further: R >= 180 m with up to 1.5 m of movement
    plat = {}
    for name, w, e, edge, P, Q in ISLANDS:
        plat[w] = plat[e] = (X >= P[0] - 5.0) & (X <= P[1] + 5.0)
    for k in ORDER:
        T[k] = limit_curvature(T[k], 180.0, 1.5, plat.get(k))
    for it in range(100):
        moved = 0.0
        for i in range(len(ORDER) - 1):
            k1, k2 = ORDER[i], ORDER[i + 1]
            if (k1, k2) in (("01", "02"), ("02", "03")):
                continue
            smin = 4.3 if (k1 in SHINKANSEN or k2 in SHINKANSEN) else 4.0
            if any(w == k1 and e == k2 for _, w, e, *_ in ISLANDS):
                smin = max(smin, 3.18 + 4.0)
            smin = np.minimum(smin, T0[k2] - T0[k1])
            d = np.clip(smin - (T[k2] - T[k1]), 0, None)
            if d.max() > 1e-3:
                d = np.maximum(gsmooth(_widen(d, 20.0), 8.0), d)
                T[k1] = T[k1] - d / 2; T[k2] = T[k2] + d / 2
                moved = max(moved, float(d.max()))
        if moved < 1e-3:
            break

    out = {"X": X.tolist(), "order": ORDER,
           "model": {k: M[k].tolist() for k in ORDER},
           "target": {k: T[k].tolist() for k in ORDER},
           "islands": info, "chuo_raise": CHUO_RAISE,
           "model_platform_extent": {},
           "notes": "target from GSI optimal_bvmap-v1 RailTrCL (z16) + GSI seamlessphoto z18 aerial"}
    for k, pl in L["platforms"].items():
        p = np.array(pl)
        out["model_platform_extent"][k] = [float(p[0, 0] - 1), float(p[-1, 0] + 1)]
    json.dump(out, open(os.path.join(HERE, "targets.json"), "w"))

    # report
    print("%-6s %7s %7s %7s | %6s %6s" % ("island", "model_c", "targ_c", "shift", "W_mod", "W_tgt"))
    for name, v in info.items():
        print("%-6s %7.1f %7.1f %+7.1f | %6.1f %6.1f" % (name, v["model_center0"], v["target_center0"],
              v["target_center0"] - v["model_center0"], v["model_width0"], v["target_width0"]))
    for xq in (-200, -150, -100, -50, 0, 50, 100, 150, 200, 240):
        j = int(np.argmin(abs(X - xq)))
        print("X=%5d " % xq + " ".join("%6.1f" % T[k][j] for k in ORDER))


if __name__ == "__main__":
    main()
