"""V5 module 5: central pavilion roof re-covered in fish-scale slate (restoration spec: dome-type roofs of the
south, north and central sections are gyorin-buki; the long gabled wings keep straight ichimonji courses)."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import v5lib as L
import v5mats as M


def run():
    fish = M.fish_scale_slate()
    old = bpy.data.materials.get("V2 | natural slate with fine overlapping courses")
    done = {}
    for name in ("V4 Architecture central slate roof with Atrium opening",):
        o = bpy.data.objects.get(name)
        if o is None:
            continue
        me = o.data
        if fish.name not in [m.name for m in me.materials if m]:
            me.materials.append(fish)
        fi = [m.name if m else None for m in me.materials].index(fish.name)
        L.set_face_slope_uvs(me, "V5 slope UV")
        n = 0
        for p in me.polygons:
            m = me.materials[p.material_index]
            if m == old and p.normal.z > 0.2:
                p.material_index = fi
                n += 1
        done[name] = n
        L.log(name, "faces re-covered", n)
    return done


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    bpy.ops.wm.open_mainfile(filepath=src, load_ui=False, use_scripts=False)
    info = run()
    bpy.context.scene["V5_central_roof_summary"] = json.dumps(info)
    bpy.ops.wm.save_as_mainfile(filepath=dst, compress=True)
    print("SAVED", dst)
