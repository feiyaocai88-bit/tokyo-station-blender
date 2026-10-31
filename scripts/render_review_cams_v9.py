"""Render the V9 review cameras.  For a camera with the custom property V9_cut_y (the cutaway) the section cut is
switched on and the ground / plinth / studio floor, the track-4 train and people west of the cut are hidden for that
frame only.
usage: blender -b Tokyo_Station_V9.blend -P render_review_cams_v9.py -- out_dir [samples] [01,02,...] [width height]"""
import bpy, sys, re, os
argv = sys.argv[sys.argv.index("--") + 1:]
outdir = argv[0]
samples = int(argv[1]) if len(argv) > 1 else 96
only = set(argv[2].split(",")) if len(argv) > 2 and argv[2] else None
res = (int(argv[3]), int(argv[4])) if len(argv) > 4 else (1600, 1000)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.device = 'GPU'
prefs = bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type = 'OPTIX'; prefs.get_devices()
for d in prefs.devices:
    d.use = True
sc.cycles.samples = samples; sc.cycles.use_denoising = True
sc.cycles.transparent_max_bounces = max(sc.cycles.transparent_max_bounces, 32)
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = res[0], res[1], 100
sc.render.image_settings.file_format = 'PNG'
col = bpy.data.collections["V9_Review_Cameras"]
CUT_HIDE = ("Site ground", "Display base", "Studio floor")
for cam in sorted(col.objects, key=lambda o: o.name):
    m = re.match(r"V9 (\d\d) ([^|]+)", cam.name)
    if not m or cam.type != 'CAMERA' or (only and m.group(1) not in only):
        continue
    changed = []
    cut = cam.get("V9_cut_y")
    if cut:
        sc["V9_cut_y"] = float(cut)
        for o in bpy.data.objects:
            hide = o.name in CUT_HIDE or o.get("V9_cutaway_hide")
            hide = hide or (o.get("V9_train") and o.get("track") == "B5-4")
            hide = hide or (o.get("V9_person") and o["V9_local_xy"][1] > cut)
            if hide and not o.hide_render:
                o.hide_render = True; changed.append(o)
    sc.camera = cam
    slug = re.sub(r"[^A-Za-z0-9]+", "_", cam.name[6:].replace("->", "to")).strip("_")[:44].strip("_")
    sc.render.filepath = os.path.join(outdir, f"{m.group(1)}_V9_{slug}.png")
    bpy.ops.render.render(write_still=True)
    for o in changed:
        o.hide_render = False
    sc["V9_cut_y"] = 0.0
    print("rendered", cam.name, flush=True)
