"""V8 checks for the raised Shinkansen side (run on a V8 .blend after mod8_shinkansen_level.py).
usage: blender -b V8.blend --python-exit-code 1 -P validate8_level.py -- report.json

  rails              rail-top height per track: conventional 5.17 m, Chuo unchanged, Shinkansen 5.17 + 1.90 m
  decks              platform deck tops: conventional 6.21 m, Shinkansen V7 value + 1.90 m; platform height above rail
                     on the Shinkansen side unchanged
  trains             every car instance stands at the rail top of its track (origin = rail top)
  people             people on the Shinkansen platforms stand on the raised deck (|dz| <= 0.10 m)
  escalators         escalator instances keep their V7 height relative to their platform deck
  step_profile       every 10 m along the step: top of the wall/deck just east of it and the conventional surface just
                     west of it (rays from 7.6 m down); the difference should be ~1.9 m everywhere
  portal_masts       new masts at the level change: clearance from tracks 10 and 20
"""
import sys, os, json, re
import numpy as np
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else None
D = json.load(open(os.path.join(HERE, "targets.json")))
GX = np.array(D["X"]); TGT = {k: np.array(v) for k, v in D["target"].items()}
SHIN = {"14", "15", "16", "17", "18", "19", "20", "21", "22", "23"}
DZ = 1.90
V7_DECK = {"14-15": 6.504, "16-17": 6.504, "18-19": 6.504, "20-21": 6.42, "22-23": 6.42}
sc = bpy.context.scene
dg = bpy.context.evaluated_depsgraph_get()
res = {}


def ty(k, x):
    return float(np.interp(x, GX, TGT[k]))


def yb(x):
    return 0.5 * (ty("10", x) + ty("20", x))


def vw(o):
    n = len(o.data.vertices); co = np.empty(n * 3); o.data.vertices.foreach_get("co", co)
    mw = np.array(o.matrix_world)
    return co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]


# rails
rails = {}
for o in bpy.data.objects:
    m = re.match(r"V5 track \| Track (\d\d) rails", o.name)
    if m and o.type == 'MESH':
        rails[m.group(1)] = round(float(vw(o)[:, 2].max()), 3)
bad = {k: z for k, z in rails.items() if k not in ("01", "02") and abs(z - (5.17 + (DZ if k in SHIN else 0.0))) > 0.02}
res["rails"] = {"top_z": rails, "bad": bad, "pass": not bad}

# decks
decks = {}
badd = {}
for o in bpy.data.objects:
    m = re.match(r"V3 Platform (\d\d-\d\d) raised deck$", o.name)
    if not m or o.type != 'MESH':
        continue
    isl = m.group(1)
    z = float(vw(o)[:, 2].max())
    decks[isl] = round(z, 3)
    exp = V7_DECK[isl] + DZ if isl in V7_DECK else (16.51 if isl == "01-02" else 6.21)
    if abs(z - exp) > 0.02:
        badd[isl] = (round(z, 3), exp)
hab = {}
for isl in V7_DECK:
    a, b = isl.split("-")
    hab[isl] = round(decks.get(isl, 0) - rails.get(a, 0), 3)
res["decks"] = {"top_z": decks, "bad": badd, "platform_above_rail_shinkansen": hab, "pass": not badd}

# trains
tb = []
ntr = 0
for o in sc.objects:
    m = re.match(r"Track (\d\d) \| ", o.name)
    if m and o.type == 'EMPTY' and o.instance_collection is not None:
        ntr += 1
        k = m.group(1)
        if k in rails and k not in ("01", "02") and abs(o.matrix_world.translation.z - rails[k]) > 0.03:
            tb.append((o.name, round(o.matrix_world.translation.z, 3), rails[k]))
res["trains"] = {"instances": ntr, "bad": tb[:20], "n_bad": len(tb), "pass": not tb}

# people on Shinkansen platforms
pb = []
npp = 0
for o in sc.objects:
    m = re.match(r"V5 person P(\d\d) ", o.name)
    if not m or o.type != 'EMPTY':
        continue
    trk = m.group(1)
    isl = next((k for k in V7_DECK if trk in k.split("-")), None)
    if isl is None:
        continue
    npp += 1
    z = o.matrix_world.translation.z
    if abs(z - decks[isl]) > 0.10:
        pb.append((o.name, round(z, 3), decks[isl]))
res["people"] = {"on_shinkansen_platforms": npp, "bad": pb[:20], "n_bad": len(pb), "pass": not pb}

# escalators: height below the deck of their island
eb = {}
for o in sc.objects:
    m = re.match(r"V6 escalator (\d\d-\d\d) ([NCS])$", o.name)
    if m and o.type == 'EMPTY':
        isl = m.group(1)
        eb[o.name] = round(decks[isl] - o.matrix_world.translation.z, 3)
vals = sorted(set(eb.values()))
res["escalators"] = {"deck_minus_instance_z": vals, "n": len(eb), "pass": (max(vals) - min(vals)) < 0.12 if vals else False}

# step profile
prof = []
for x in np.arange(-200.0, 241.0, 10.0):
    y0 = yb(x)
    row = {"x": float(x)}
    for key, yy in (("east", y0 + 0.50), ("west", y0 - 0.45)):
        hit, loc, nrm, idx, ob, mtx = sc.ray_cast(dg, Vector((x, yy, 7.6)), Vector((0, 0, -1)))
        row[key] = round(loc.z, 2) if hit else None
        row[key + "_obj"] = ob.name[:40] if hit else None
    prof.append(row)
diffs = [r["east"] - r["west"] for r in prof if r["east"] is not None and r["west"] is not None]
res["step_profile"] = {"rows": prof, "min_diff": round(min(diffs), 2) if diffs else None,
                       "max_diff": round(max(diffs), 2) if diffs else None}

# portal masts
info = json.loads(sc.get("V8_shinkansen_level", "{}"))
res["portal_masts"] = info.get("portal_masts", [])
res["pass"] = all(res[k]["pass"] for k in ("rails", "decks", "trains", "people", "escalators")) and \
    all(m.get("clear") for m in res["portal_masts"])
print(json.dumps({k: (v if k != "step_profile" else {kk: vv for kk, vv in v.items() if kk != "rows"}) for k, v in res.items()},
                 ensure_ascii=False)[:3000])
if OUT:
    json.dump(res, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
