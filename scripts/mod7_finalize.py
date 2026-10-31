"""V7 finalize: review cameras for the train interiors, embedded change log / README, orphan purge,
save as Tokyo_Station_V7.blend.

usage: blender -b in.blend --python-exit-code 1 -P mod7_finalize.py -- out.blend package_dir
       (package_dir: README_CN.txt is embedded from there if present; V7_Changes.json is written there)
The cameras are defined in the local frame of a car instance (x along the car, y across, z = 0 at rail top) and
converted to world coordinates here, so they stay correct if the cars are moved before rebuilding.
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

CAMS = [  # name, car instance, local camera position, local target, lens
    ("V7 01 E233-3000 TRACK 8 | interior seen through the window from platform 7-8", "Track 08 car 02",
     (-2.0, -4.6, 2.75), (1.0, 0.0, 2.35), 24),
    ("V7 02 E233-3000 TRACK 8 | inside the car, along the aisle", "Track 08 car 02",
     (-8.9, 0.35, 2.75), (6.0, -0.2, 2.45), 18),
    ("V7 03 E233-3000 TRACK 8 | from the seat, out through the window to the platform", "Track 08 car 02",
     (0.2, 0.9, 2.5), (0.6, -3.0, 2.3), 20),
    ("V7 04 E235 TRACK 4 | cab car from platform 3-4", "Track 04 car 01",
     (3.0, 4.4, 2.8), (7.5, 0.0, 2.3), 22),
    ("V7 05 E233-3000 TRACK 8 | cab car, aisle towards the cab partition", "Track 08 car 01",
     (-1.5, -0.3, 2.75), (8.0, 0.1, 2.45), 20),
    ("V7 06 E235 TRACK 4 | intermediate car from platform 3-4", "Track 04 car 03",
     (-3.0, -4.6, 2.75), (1.0, 0.0, 2.35), 24),
]


def add_camera(name, inst, loc, target, lens):
    col = L.collection("V7_Review_Cameras")
    M = bpy.data.objects[inst].matrix_world
    wl, wt = M @ Vector(loc), M @ Vector(target)
    cd = bpy.data.cameras.get(name) or bpy.data.cameras.new(name)
    cd.type = 'PERSP'; cd.lens = lens; cd.clip_start = 0.03; cd.clip_end = 3000
    co = bpy.data.objects.get(name) or bpy.data.objects.new(name, cd)
    co.location = wl
    co.rotation_euler = (wt - wl).to_track_quat('-Z', 'Y').to_euler()
    co["V7_relative_to"] = inst
    if co.name not in col.objects:
        col.objects.link(co)
    return co


def run():
    for name, inst, loc, tgt, lens in CAMS:
        add_camera(name, inst, loc, tgt, lens)
    sc = bpy.context.scene
    summ = {}
    for k in ("V7_interiors_summary",):
        if k in sc.keys():
            summ[k] = json.loads(sc[k])
    summ["interior_credit"] = sc.get("V7_interior_credit")
    summ["review_cameras"] = [c[0] for c in CAMS]
    sc["V7_representation"] = ("V7 on top of V6: passenger interiors in the commuter cars (downloaded CC BY interior, "
                               "re-assembled to each car body) and see-through side windows. Interpretive diorama.")
    os.makedirs(PKG, exist_ok=True)
    changelog = os.path.join(PKG, "V7_Changes.json")
    json.dump(summ, open(changelog, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    readme = os.path.join(PKG, "README_CN.txt")
    for tname, path in (("V7_CHANGELOG_JSON", changelog), ("V7_README_CN", readme)):
        if os.path.exists(path):
            t = bpy.data.texts.get(tname) or bpy.data.texts.new(tname)
            t.clear(); t.write(open(path, encoding="utf-8").read())
    sc.name = "TOKYO STATION | V7 train interiors"
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
