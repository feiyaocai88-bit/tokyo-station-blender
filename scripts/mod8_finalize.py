"""V8 finalize: review cameras for the raised Shinkansen side and the new canopy ceilings, embedded change log /
README, orphan purge, save as Tokyo_Station_V8.blend.

usage: blender -b in.blend --python-exit-code 1 -P mod8_finalize.py -- out.blend package_dir
       (package_dir: README_CN.txt is embedded from there if present; V8_Changes.json is written there)
"""
import sys, os, json
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v5lib as L

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGV[0] if ARGV else None
PKG = ARGV[1] if len(ARGV) > 1 else os.path.join(HERE, "..", "pkg")

CAMS = [  # name, world position, world target, lens
    ("V8 01 PLATFORM 7-8 | canopy ceiling: H-beams, purlins, skylight, light fittings", (-40, 77.6, 7.8), (-60, 76.2, 15.9), 16),
    ("V8 02 PLATFORM 9-10 | canopy ceiling: lattice girders", (-40, 97.6, 7.8), (-60, 96.2, 15.9), 16),
    ("V8 03 PLATFORM 3-4 | canopy ceiling: haunched beams", (-40, 39.8, 7.8), (-60, 38.4, 15.9), 16),
    ("V8 04 PLATFORM 9-10 | the raised Shinkansen side across track 10", (-186, 87.0, 7.81), (-160, 99.5, 8.6), 20),
    ("V8 05 PLATFORM 20-21 | looking down to platform 9-10", (-186, 97.4, 9.92), (-160, 90.0, 6.6), 20),
    ("V8 06 SOUTH END | portals at the level change", (196, 84, 19), (222, 112, 11), 22),
    ("V8 07 NORTH END | both levels from above", (-215, 70, 17), (-170, 108, 7), 24),
]


def add_camera(name, loc, target, lens):
    col = L.collection("V8_Review_Cameras")
    wl, wt = Vector(loc), Vector(target)
    cd = bpy.data.cameras.get(name) or bpy.data.cameras.new(name)
    cd.type = 'PERSP'; cd.lens = lens; cd.clip_start = 0.03; cd.clip_end = 3000
    co = bpy.data.objects.get(name) or bpy.data.objects.new(name, cd)
    co.location = wl
    co.rotation_euler = (wt - wl).to_track_quat('-Z', 'Y').to_euler()
    if co.name not in col.objects:
        col.objects.link(co)
    return co


def run():
    for name, loc, tgt, lens in CAMS:
        add_camera(name, loc, tgt, lens)
    sc = bpy.context.scene
    summ = {}
    for k in ("V8_shinkansen_level", "V8_canopies"):
        if k in sc.keys():
            summ[k] = json.loads(sc[k])
    summ["review_cameras"] = [c[0] for c in CAMS]
    sc["V8_representation"] = ("V8 on top of V7: Shinkansen side raised 1.90 m with a side wall along the step; steel-framed "
                               "canopies with visible beams, purlins, light fittings on the conventional islands. "
                               "Interpretive diorama.")
    os.makedirs(PKG, exist_ok=True)
    changelog = os.path.join(PKG, "V8_Changes.json")
    json.dump(summ, open(changelog, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    readme = os.path.join(PKG, "README_CN.txt")
    for tname, path in (("V8_CHANGELOG_JSON", changelog), ("V8_README_CN", readme)):
        if os.path.exists(path):
            t = bpy.data.texts.get(tname) or bpy.data.texts.new(tname)
            t.clear(); t.write(open(path, encoding="utf-8").read())
    sc.name = "TOKYO STATION | V8 levels and canopies"
    cam = bpy.data.objects.get(CAMS[0][0])
    if cam:
        sc.camera = cam
    return summ


info = run()
before = len(bpy.data.objects)
bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
L.log("objects", before, "->", len(bpy.data.objects))
if OUT:
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=True)
    L.log("saved", OUT)
