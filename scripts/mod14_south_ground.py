"""V14 on final V13: -- output.blend report.json baseline.json."""
import bpy,sys,os,json
from mathutils import Vector
sys.path.insert(0,os.path.dirname(__file__))
import v14lib as H
import mod14_catenary,mod14_ground
from mod12_surface_trains import fingerprint

def camera(name,pos,target,lens=45,ortho=None):
 d=bpy.data.cameras.new('V14 '+name);d.lens=lens;d.clip_start=.05;d.clip_end=2500
 o=bpy.data.objects.new(d.name,d);H.col('Review_Cameras').objects.link(o);o.location=pos;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();o['V14_scene']=bpy.context.scene.name
 if ortho:d.type='ORTHO';d.ortho_scale=ortho
 return o
def cameras():
 camera('01 south ground overview',(291,-39,39),(211,55,3.5),48)
 camera('02 brick arches and Hato Bus frontage',(231,25,3.1),(208,43.5,1.8),32)
 camera('03 paving drainage and curb',(223,39,2.8),(218,44,.3),43)
 camera('04 south catenary staggered portals',(289,10,38),(190,78,11),48)
 camera('05 catenary plan',(199,73,210),(199,73,0),ortho=117)
 camera('06 south undercroft detail',(249,66,2.5),(233,68,2),28)
 bpy.context.scene.camera=bpy.data.objects['V14 01 south ground overview']
 for screen in bpy.data.screens:
  for area in screen.areas:
   if area.type=='VIEW_3D':
    space=area.spaces.active;space.region_3d.view_perspective='CAMERA';space.shading.color_type='MATERIAL'
def main():
 args=sys.argv[sys.argv.index('--')+1:];sc=bpy.context.scene
 if sc.get('V14_refinement'):raise RuntimeError('Start with final V13')
 if len(args)>2:json.dump(fingerprint(),open(args[2],'w'),separators=(',',':'))
 H.setup();mod14_catenary.run();print('V14_CATENARY_OK',H.R['counts'],flush=True)
 mod14_ground.run();cameras();print('V14_GROUND_OK',H.R['counts'],flush=True)
 H.R['limitations']=['Interpretive multi-epoch diorama; no full-station survey claim.','Five south portal rows photo-interpreted to +/-3m; one terminal row adapted 3m to the cropped model edge. One extra twin-arm pole at X184 is required by inherited track curvature and is not photo-verified. Lateral mast coordinates are fitted to the inherited rails.','Eight brick bays and office/street details follow photographic typology; individual dimensions and utilities are not measured. The parked coach is a simplified sightseeing-coach interpretation.','Hidden V14 originals retain every changed source mesh; V12 trains and V13 Metro access are unchanged.']
 sc['V14_refinement']=json.dumps(H.R,ensure_ascii=False);sc['last_stage']='V14 south ground and photo-interpreted south OCS, 2026-11-03'
 sc['V14_accuracy']='See README_V14.txt and sources_and_licenses/south_ground_v14.json. Only five south portal chainages are photo-interpreted; no claim of a surveyed complete mast layout.'
 p=os.path.join(os.path.dirname(__file__),'..','README_V14.txt')
 if os.path.isfile(p):tx=bpy.data.texts.new('README_V14_中文');tx.write(open(p,encoding='utf8').read())
 bpy.context.view_layer.update();bpy.ops.file.pack_all();bpy.context.preferences.filepaths.save_version=0
 out=os.path.abspath(args[0]);os.makedirs(os.path.dirname(out),exist_ok=True);bpy.ops.wm.save_as_mainfile(filepath=out,compress=True)
 json.dump(H.R,open(args[1],'w',encoding='utf8'),ensure_ascii=False,indent=2);print('V14_BUILD_OK',flush=True)
if __name__=='__main__':main()
