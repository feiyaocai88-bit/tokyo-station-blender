"""V6 finalize: review cameras for the round-6 changes, light-sampling settings for the small emitters, embedded change
log / README, orphan purge, save as Tokyo_Station_V6.blend.

usage: blender -b in.blend --python-exit-code 1 -P mod6_finalize.py -- out.blend package_dir
       (package_dir: README_CN.txt is embedded from there if present; V6_Changes.json is written there)
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

CAMS = [
    ("V6 01 PLATFORM 3-4 | stair entrance, escalator, exit sign", (-10, 39.39, 7.81), (4, 38.42, 6.81), 24),
    ("V6 02 ESCALATOR | KONE TravelMaster 110 model (CC BY 4.0, Sergey Burov)", (-1.8, 41.0, 7.91), (3.0, 39.42, 5.61), 24),
    ("V6 03 ROUTE MAP | stairwell on platform 14-15", (2.5, 160.21, 8.20), (-8.6, 159.01, 7.90), 30),
    ("V6 04 SHINKANSEN 14-15 | car-number boards", (60, 155.29, 8.20), (20, 154.79, 8.90), 30),
    ("V6 05 PLATFORM 3-4 | direction boards, clocks", (-60, 37.21, 7.91), (-20, 38.46, 8.21), 26),
    ("V6 06 OVERHEAD LINE | portals over platform 7-8", (10, 64, 15), (-25, 74, 11), 24),
    ("V6 07 OVERHEAD LINE | drop tubes under the Shinkansen roof 16-17", (33, 175.8, 8.15), (39.5, 172.3, 12.2), 28),
    ("V6 08 N700 | head lamps on the south nose (approximate position)", (201.0, 145.2, 7.0), (195.3, 148.3, 6.7), 40),
    ("V6 09 E5 | side LED display beside the door", (14, 113.2, 7.5), (8.5, 109.9, 7.3), 35),
    ("V6 10 E233-3000 | car number, car-number plate, priority-seat sticker", (-29, 100.9, 7.0), (-32.5, 104.3, 6.6), 35),
    ("V6 11 NORTH DOME CLOCK | serif numerals", (-104, -42, 14), (-104, -13, 19.8), 50),
]


def add_camera(name, loc, target, lens):
    col = L.collection("V6_Review_Cameras")
    cd = bpy.data.cameras.get(name) or bpy.data.cameras.new(name)
    cd.type = 'PERSP'; cd.lens = lens; cd.clip_start = 0.05; cd.clip_end = 3000
    co = bpy.data.objects.get(name) or bpy.data.objects.new(name, cd)
    co.location = loc
    co.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    if co.name not in col.objects:
        col.objects.link(co)
    return co


def run():
    for name, loc, tgt, lens in CAMS:
        add_camera(name, loc, tgt, lens)
    sc = bpy.context.scene
    summ = {}
    for k in ("V6_platform_summary", "V6_catenary_summary", "V6_trains_summary"):
        if k in sc.keys():
            summ[k] = json.loads(sc[k])
    # small V6 emitters (sign boards, LED displays, lamp lenses, light strips in the stairwells) read as lit without
    # being sampled as lights
    n_em = 0
    for m in bpy.data.materials:
        if not m.name.startswith("V6 |") or not m.node_tree:
            continue
        b = m.node_tree.nodes.get("Principled BSDF")
        if b and (b.inputs["Emission Strength"].default_value > 0 or b.inputs["Emission Strength"].is_linked):
            m.cycles.emission_sampling = 'NONE'
            n_em += 1
    summ["emissive_V6_materials_not_light_sampled"] = n_em
    sc["V6_representation"] = ("V6 detail revision on top of V5: overhead line rebuilt from the track centrelines, platform "
                               "stairs/escalators/signage, train markings. Interpretive diorama, not a measured survey.")
    os.makedirs(PKG, exist_ok=True)
    changelog = os.path.join(PKG, "V6_Changes.json")
    json.dump(summ, open(changelog, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    readme = os.path.join(PKG, "README_CN.txt")
    for tname, path in (("V6_CHANGELOG_JSON", changelog), ("V6_README_CN", readme)):
        if os.path.exists(path):
            t = bpy.data.texts.get(tname) or bpy.data.texts.new(tname)
            t.clear(); t.write(open(path, encoding="utf-8").read())
    sc.name = "TOKYO STATION | V6 detail revision"
    cam = bpy.data.objects.get(CAMS[0][0])
    if cam:
        sc.camera = cam
    return summ


info = run()
before = len(bpy.data.objects)
bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
L.log("objects", before, "->", len(bpy.data.objects), "emissive set", info["emissive_V6_materials_not_light_sampled"])
if OUT:
    bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=True)
    L.log("saved", OUT)
