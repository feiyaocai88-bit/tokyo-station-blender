"""Create an inspectable Blender copy and render the actual printable solid."""
import bpy,sys,json,math
import numpy as np
from mathutils import Vector
from pathlib import Path
out=Path(sys.argv[sys.argv.index('--')+1]).resolve()
data=np.load(out/'print_mesh.npz')
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.name='Marunouchi FDM 1-1000'
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.001;scene.unit_settings.length_unit='MILLIMETERS'
mesh=bpy.data.meshes.new('Watertight printable station');mesh.from_pydata(data['vertices'].tolist(),[],data['faces'].tolist());mesh.update()
mesh.polygons.foreach_set('use_smooth',np.ones(len(mesh.polygons),dtype=bool))
if hasattr(mesh,'set_sharp_from_angle'):mesh.set_sharp_from_angle(angle=math.radians(35))
obj=bpy.data.objects.new('PRINT Marunouchi single solid - millimeters',mesh);scene.collection.objects.link(obj)
obj.color=(.74,.59,.40,1)
obj['scale']='1:1000';obj['base_mm']=4.0;obj['purpose']='One connected FDM solid, underground excluded'
bpy.context.view_layer.objects.active=obj;obj.select_set(True)
scene.render.engine='BLENDER_WORKBENCH'
shade=scene.display.shading;shade.light='STUDIO';shade.studiolight_rotate_z=.45;shade.color_type='OBJECT';shade.show_shadows=True
shade.show_cavity=True;shade.cavity_type='BOTH';shade.curvature_ridge_factor=1.6;shade.curvature_valley_factor=1.2
shade.cavity_ridge_factor=1.4;shade.cavity_valley_factor=1.2;shade.show_specular_highlight=True
shade.background_type='WORLD';scene.world=bpy.data.worlds.new('Neutral preview world');scene.world.color=(.055,.065,.08);shade.show_object_outline=False
scene.view_settings.view_transform='Standard';scene.render.image_settings.file_format='PNG'
scene.render.resolution_percentage=100
def camera(name,location,target,ortho,res):
    cam=bpy.data.cameras.new(name);cam.type='ORTHO';cam.ortho_scale=ortho;cam.clip_end=2500;cam.clip_start=.01
    ob=bpy.data.objects.new(name,cam);scene.collection.objects.link(ob);ob.location=location;ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
    scene.camera=ob;scene.render.resolution_x=res[0];scene.render.resolution_y=res[1]
    scene.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
    return ob
overview=camera('01_Printable_overview',(28,-220,170),(0,0,15),357,(2300,900))
camera('02_Central_entrance_detail',(-1,-90,48),(-17,-12,17),73,(1500,1000))
camera('03_North_dome_detail',(-140,-82,65),(-121,-12,24),75,(1500,1100))
camera('05_Underside_interfaces',(0,-95,-200),(0,0,1),350,(2300,850))
scene.camera=overview;scene.render.resolution_x=2300;scene.render.resolution_y=900
# Save a clean model scene. Cameras are non-print objects with explicit names.
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_distance=235
            area.spaces.active.region_3d.view_location=(0,0,15)
scene['print_validation']=json.dumps(json.loads((out/'validation.json').read_text(encoding='utf8'))['model_dimensions_mm'])
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out/'Marunouchi_FDM_1-1000.blend'),compress=True)
print('PRINT_PREVIEWS_DONE',flush=True)
