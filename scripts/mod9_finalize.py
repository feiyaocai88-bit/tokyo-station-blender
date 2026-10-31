"""V9 finalize: section-cut switch for the cutaway view, review cameras for the Sobu underground station, embedded
change log / README, orphan purge, save as Tokyo_Station_V9.blend.

Section cut: every material of the V9 station objects gets the node group "V9 section cut".  It does nothing while the
scene custom property V9_cut_y is 0 (the saved state).  Set it to e.g. 11.5 (metres, station-local y) and everything of
the station west of that plane turns transparent, cut solids show a flat dark-red section colour; also hide
"Site ground", "Display base", "Studio floor" and the track-4 train for the cutaway (render_review_cams_v9.py does this
for the camera "V9 09 ..." only).

usage: blender -b in.blend --python-exit-code 1 -P mod9_finalize.py -- out.blend package_dir
"""
import sys, os, json
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v5lib as L
import v9geo as G

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGV[0] if ARGV else None
PKG = ARGV[1] if len(ARGV) > 1 else os.path.join(HERE, "..", "pkg")
FR = G.frame_matrix()
CUT_Y = G.CUT_Y

CAMS = G.REVIEW_CAMS


def add_camera(name, loc, target, lens):
    col = L.collection("V9_Review_Cameras")
    wl, wt = FR @ Vector(loc), FR @ Vector(target)
    cd = bpy.data.cameras.get(name) or bpy.data.cameras.new(name)
    cd.type = 'PERSP'; cd.lens = lens; cd.clip_start = 0.03; cd.clip_end = 3000
    co = bpy.data.objects.get(name) or bpy.data.objects.new(name, cd)
    co.location = wl
    co.rotation_euler = (wt - wl).to_track_quat('-Z', 'Y').to_euler()
    co["V9_local_position"] = [round(v, 3) for v in loc]
    if "CUTAWAY" in name:
        co["V9_cut_y"] = CUT_Y
    if co.name not in col.objects:
        col.objects.link(co)
    return co


def section_group():
    ng = bpy.data.node_groups.get("V9 section cut")
    if ng:
        return ng
    ng = bpy.data.node_groups.new("V9 section cut", "ShaderNodeTree")
    ng.interface.new_socket(name="Surface", in_out='INPUT', socket_type='NodeSocketShader')
    ng.interface.new_socket(name="Surface", in_out='OUTPUT', socket_type='NodeSocketShader')
    N = ng.nodes; Lk = ng.links
    gi = N.new("NodeGroupInput"); go = N.new("NodeGroupOutput")
    tc = N.new("ShaderNodeTexCoord"); sep = N.new("ShaderNodeSeparateXYZ")
    Lk.new(tc.outputs["Object"], sep.inputs["Vector"])
    at = N.new("ShaderNodeAttribute"); at.attribute_type = 'VIEW_LAYER'; at.attribute_name = "V9_cut_y"
    act = N.new("ShaderNodeMath"); act.operation = 'GREATER_THAN'; act.inputs[1].default_value = 0.001
    Lk.new(at.outputs["Fac"], act.inputs[0])
    bey = N.new("ShaderNodeMath"); bey.operation = 'GREATER_THAN'
    Lk.new(sep.outputs["Y"], bey.inputs[0]); Lk.new(at.outputs["Fac"], bey.inputs[1])
    cut = N.new("ShaderNodeMath"); cut.operation = 'MULTIPLY'
    Lk.new(act.outputs[0], cut.inputs[0]); Lk.new(bey.outputs[0], cut.inputs[1])
    geo = N.new("ShaderNodeNewGeometry")
    poc = N.new("ShaderNodeMath"); poc.operation = 'MULTIPLY'
    Lk.new(act.outputs[0], poc.inputs[0]); Lk.new(geo.outputs["Backfacing"], poc.inputs[1])
    em = N.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (0.30, 0.055, 0.04, 1); em.inputs["Strength"].default_value = 0.6
    m1 = N.new("ShaderNodeMixShader")
    Lk.new(poc.outputs[0], m1.inputs[0]); Lk.new(gi.outputs[0], m1.inputs[1]); Lk.new(em.outputs[0], m1.inputs[2])
    tr = N.new("ShaderNodeBsdfTransparent")
    m2 = N.new("ShaderNodeMixShader")
    Lk.new(cut.outputs[0], m2.inputs[0]); Lk.new(m1.outputs[0], m2.inputs[1]); Lk.new(tr.outputs[0], m2.inputs[2])
    Lk.new(m2.outputs[0], go.inputs[0])
    return ng


def apply_section_cut():
    ng = section_group()
    mats = set()
    for o in bpy.data.objects:
        if o.get("V9_sobu") and o.type == 'MESH':
            for s in o.material_slots:
                if s.material:
                    mats.add(s.material)
    n = 0
    for m in mats:
        nt = m.node_tree
        if any(nd.type == 'GROUP' and nd.node_tree == ng for nd in nt.nodes):
            continue
        outs = [nd for nd in nt.nodes if nd.type == 'OUTPUT_MATERIAL' and nd.is_active_output] or \
               [nd for nd in nt.nodes if nd.type == 'OUTPUT_MATERIAL']
        if not outs or not outs[0].inputs["Surface"].links:
            continue
        out = outs[0]; lk = out.inputs["Surface"].links[0]; src = lk.from_socket
        g = nt.nodes.new("ShaderNodeGroup"); g.node_tree = ng; g.label = "V9 section cut"
        g.location = (out.location.x - 200, out.location.y - 200)
        nt.links.remove(lk)
        nt.links.new(src, g.inputs[0]); nt.links.new(g.outputs[0], out.inputs["Surface"])
        n += 1
    return n


def run():
    sc = bpy.context.scene
    sc["V9_cut_y"] = 0.0
    nmat = apply_section_cut()
    for name, loc, tgt, lens in CAMS:
        add_camera(name, loc, tgt, lens)
    summ = {}
    for k in ("V9_sobu_station",):
        if k in sc.keys():
            summ[k] = json.loads(sc[k])
    summ["section_cut_materials"] = nmat
    summ["review_cameras"] = [c[0] for c in CAMS]
    summ["trains"] = sorted({o["line"] for o in bpy.data.objects if o.get("V9_train")})
    summ["people"] = sum(1 for o in bpy.data.objects if o.get("V9_person"))
    sc["V9_representation"] = ("V9 on top of V8: the JR Sobu / Yokosuka underground station (B5 platforms 1-4, B4 "
                               "concourse, B3/B2 plant floors, B1 concourse) under the Marunouchi plaza, placed from "
                               "OpenStreetMap (ODbL) and published depths; interior details are interpretive.")
    os.makedirs(PKG, exist_ok=True)
    changelog = os.path.join(PKG, "V9_Changes.json")
    json.dump(summ, open(changelog, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    readme = os.path.join(PKG, "README_CN.txt")
    for tname, path in (("V9_CHANGELOG_JSON", changelog), ("V9_README_CN", readme)):
        if os.path.exists(path):
            t = bpy.data.texts.get(tname) or bpy.data.texts.new(tname)
            t.clear(); t.write(open(path, encoding="utf-8").read())
    sc.name = "TOKYO STATION | V9 Sobu underground station"
    cam = bpy.data.objects.get(CAMS[0][0])
    if cam:
        sc.camera = cam
    return summ


info = run()
before = len(bpy.data.objects)
bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
L.log("objects", before, "->", len(bpy.data.objects), "| section-cut materials", info["section_cut_materials"])
if OUT:
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=True)
    L.log("saved", OUT)
