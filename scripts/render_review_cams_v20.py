"""Actual model views. -- folder samples ids width height"""
import bpy,sys,os,re
from mathutils import Vector
sys.path.insert(0,os.path.dirname(__file__))
import v20lib as H
SPECS=[('01 End passage',(100,29.8,18.20),(114,29.2,18.05),23,None),('02 Rounded staff room',(32,27.5,18.18),(43,23.9,18.13),28,None),('03 Curved canopy connection',(90,29.8,18.25),(98.1,35.2,21.0),26,None),('04 Roof and end overview',(167,-24,67),(88,28,18),50,88),('05 CCTV and departure monitor',(53.7,28.3,18.25),(58,26.1,19.4),44,None),('06 Chuo whole platform',(200,-130,135),(-12,26,18),50,290),('07 CCTV lens detail',(61.3,29.2,18.9),(57.1,27.3,19.36),48,None)]
def cameras():
 c=H.col('Review_Cameras')
 for n,p,t,l,scale in SPECS:
  o=bpy.data.objects.get('V20 '+n)
  if o is None:
   d=bpy.data.cameras.new('V20 '+n);o=bpy.data.objects.new(d.name,d);c.objects.link(o)
  o.location=p;o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler();o.data.lens=l;o.data.clip_start=.035;o.data.clip_end=2500;o['V20_review']=True
  if scale:o.data.type='ORTHO';o.data.ortho_scale=scale
 bpy.context.scene.camera=bpy.data.objects['V20 04 Roof and end overview']
def main():
 a=sys.argv[sys.argv.index('--')+1:];out=os.path.abspath(a[0]);os.makedirs(out,exist_ok=True);sc=bpy.data.scenes['Tokyo Station'];bpy.context.window.scene=sc;cameras()
 prefs=bpy.context.preferences.addons['cycles'].preferences;device='CPU'
 try:
  prefs.compute_device_type='OPTIX';prefs.get_devices();ds=[d for d in prefs.devices if d.type=='OPTIX']
  if ds:
   for d in prefs.devices:d.use=d in ds
   device='GPU'
 except Exception:pass
 for cam in sorted((o for o in sc.objects if o.type=='CAMERA' and o.get('V20_review')),key=lambda o:o.name):
  if cam.name.split()[1] not in a[2].split(','):continue
  sc.camera=cam;sc.render.engine='CYCLES';sc.cycles.device=device;sc.cycles.samples=int(a[1]);sc.cycles.use_denoising=True;sc.cycles.transparent_max_bounces=32
  sc.render.resolution_x=int(a[3]);sc.render.resolution_y=int(a[4]);sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
  sc.render.filepath=os.path.join(out,re.sub('[^A-Za-z0-9]+','_',cam.name).strip('_')+'.png');bpy.ops.render.render(write_still=True,scene=sc.name);print('V20_RENDER_OK',cam.name,flush=True)
if __name__=='__main__':main()
