"""Matched V21-before / V22-after views, all rendered from native geometry.
-- output_folder samples ids [width height]; camera 01 uses a portrait view.
"""
import bpy,sys,re
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
import v22lib as H
SPECS=[('01 Aerial photo comparison',(-235,130,165),(-12,24,18),50,295),
 ('02 Continuous envelope and white cover',(66,97,65),(-8,25,21),50,114),
 ('03 Open south portal',(129,30,21.1),(95,29,20.7),27,None),
 ('04 Curved enclosure from the platform',(90,29.8,18.25),(98.1,35.2,21.0),26,None),
 ('05 Station overview',(245,-180,215),(-5,105,8),50,440),
 ('06 White transverse cover and framing',(26,57,37),(-1,23,23),50,51),
 ('07 Equipment linking the two roof levels',(65,57,24),(50.93,34,14.4),50,20)]
def cameras():
 sc=bpy.data.scenes['Tokyo Station'];bpy.context.window.scene=sc;c=H.col('Review_Cameras')
 for n,p,t,l,scale in SPECS:
  name='V22 '+n;o=bpy.data.objects.get(name)
  if o is None:d=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,d);c.objects.link(o)
  o.location=p;o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler();o.data.lens=l;o.data.clip_start=.035;o.data.clip_end=2500;o['V22_review']=True
  if scale:o.data.type='ORTHO';o.data.ortho_scale=scale
 sc.camera=bpy.data.objects['V22 02 Continuous envelope and white cover']
def main():
 a=sys.argv[sys.argv.index('--')+1:];out=Path(a[0]).resolve();out.mkdir(parents=True,exist_ok=True);sc=bpy.data.scenes['Tokyo Station'];bpy.context.window.scene=sc;cameras()
 prefs=bpy.context.preferences.addons['cycles'].preferences;device='CPU'
 try:
  prefs.compute_device_type='OPTIX';prefs.get_devices();ds=[d for d in prefs.devices if d.type=='OPTIX']
  if ds:
   for d in prefs.devices:d.use=d in ds
   device='GPU'
 except Exception:pass
 for cam in sorted((o for o in sc.objects if o.type=='CAMERA' and o.get('V22_review')),key=lambda o:o.name):
  num=cam.name.split()[1]
  if num not in a[2].split(','):continue
  sc.camera=cam;sc.render.engine='CYCLES';sc.cycles.device=device;sc.cycles.samples=int(a[1]);sc.cycles.use_denoising=True;sc.cycles.transparent_max_bounces=32
  w,h=(int(a[3]),int(a[4])) if len(a)>4 else (1800,1200)
  if num=='01':w,h=h,w
  sc.render.resolution_x=w;sc.render.resolution_y=h;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
  sc.render.filepath=str(out/(re.sub('[^A-Za-z0-9]+','_',cam.name).strip('_')+'.png'));bpy.ops.render.render(write_still=True,scene=sc.name);print('V22_RENDER_OK',cam.name,flush=True)
if __name__=='__main__':main()
