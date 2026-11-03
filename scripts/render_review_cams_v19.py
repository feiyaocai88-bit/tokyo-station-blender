"""Matched street and rear-concourse views. -- folder samples ids width height"""
import bpy,sys,os,re
from mathutils import Vector
SPECS=[('01 Streets overview',(-250,-315,255),(5,-30,2),455),('02 North junction',(-227,-185,85),(-155,-72,2),150),('03 South connection',(270,-135,92),(191,-17,3),157),('04 Rear concourse north',(-212,78,61),(-133,16,7),135),('05 Rear concourse detail',(28,48,90),(11,13,5),76),('06 Plaza road plan',(0,-45,330),(0,-45,0),440),('07 Covered passage',(-87,12,2.0),(-48,12,3.0),None)]
def cameras():
 sc=bpy.context.scene;c=bpy.data.collections.get('V19_Review_Cameras')
 if c is None:c=bpy.data.collections.new('V19_Review_Cameras');sc.collection.children.link(c)
 for name,p,t,scale in SPECS:
  if bpy.data.objects.get('V19 '+name):continue
  d=bpy.data.cameras.new('V19 '+name);d.clip_start=.035;d.clip_end=2500
  if scale:d.type='ORTHO';d.ortho_scale=scale
  else:d.lens=25
  o=bpy.data.objects.new(d.name,d);c.objects.link(o);o.location=p;o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler();o['V19_review']=True
 sc.camera=bpy.data.objects['V19 01 Streets overview']
def main():
 args=sys.argv[sys.argv.index('--')+1:];out=os.path.abspath(args[0]);os.makedirs(out,exist_ok=True)
 sc=bpy.data.scenes['Tokyo Station'];bpy.context.window.scene=sc;cameras()
 prefs=bpy.context.preferences.addons['cycles'].preferences;device='CPU'
 try:
  prefs.compute_device_type='OPTIX';prefs.get_devices();ds=[d for d in prefs.devices if d.type=='OPTIX']
  if ds:
   for d in prefs.devices:d.use=d in ds
   device='GPU'
 except Exception:pass
 for cam in sorted((o for o in sc.objects if o.type=='CAMERA' and o.get('V19_review')),key=lambda o:o.name):
  if cam.name.split()[1] not in args[2].split(','):continue
  sc.camera=cam;sc.render.engine='CYCLES';sc.cycles.device=device;sc.cycles.samples=int(args[1]);sc.cycles.use_denoising=True;sc.cycles.transparent_max_bounces=32
  sc.render.resolution_x=int(args[3]);sc.render.resolution_y=int(args[4]);sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
  sc.render.filepath=os.path.join(out,re.sub('[^A-Za-z0-9]+','_',cam.name).strip('_')+'.png');bpy.ops.render.render(write_still=True,scene=sc.name);print('RENDER_OK',cam.name,flush=True)
if __name__=='__main__':main()
