"""Matched V17/V18 plaza views. -- folder samples camera_ids width height"""
import bpy,sys,os,re
sys.path.insert(0,os.path.dirname(__file__))
args=sys.argv[sys.argv.index('--')+1:];out=os.path.abspath(args[0]);os.makedirs(out,exist_ok=True)
sc=bpy.data.scenes['Tokyo Station'];bpy.context.window.scene=sc
if not sc.get('V18_plaza'):
 from mod18_plaza import cameras
 cameras()
prefs=bpy.context.preferences.addons['cycles'].preferences;device='CPU'
try:
 prefs.compute_device_type='OPTIX';prefs.get_devices();ds=[d for d in prefs.devices if d.type=='OPTIX']
 if ds:
  for d in prefs.devices:d.use=d in ds
  device='GPU'
except Exception:pass
only=set(args[2].split(','))
for cam in sorted((o for o in sc.objects if o.type=='CAMERA' and o.get('V18_review')),key=lambda o:o.name):
 if cam.name.split()[1] not in only:continue
 sc.camera=cam;sc.render.engine='CYCLES';sc.cycles.device=device;sc.cycles.samples=int(args[1]);sc.cycles.use_denoising=True;sc.cycles.transparent_max_bounces=32
 sc.render.resolution_x=int(args[3]);sc.render.resolution_y=int(args[4]);sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
 sc.render.filepath=os.path.join(out,re.sub('[^A-Za-z0-9]+','_',cam.name).strip('_')+'.png');bpy.ops.render.render(write_still=True,scene=sc.name);print('RENDER_OK',cam.name,flush=True)
