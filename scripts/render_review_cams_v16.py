"""Matching V15/V16 architectural views: -- folder samples cameras width height."""
import bpy,sys,os,re
sys.path.insert(0,os.path.dirname(__file__))
args=sys.argv[sys.argv.index('--')+1:];out=os.path.abspath(args[0]);os.makedirs(out,exist_ok=True)
samples=int(args[1]) if len(args)>1 else 48
only=set(args[2].split(',')) if len(args)>2 and args[2] else None
width=int(args[3]) if len(args)>3 else 1440;height=int(args[4]) if len(args)>4 else 1100
sc=bpy.data.scenes['Tokyo Station'];bpy.context.window.scene=sc
if not sc.get('V16_refinement'):
    from mod16_marunouchi_architecture import cameras
    cameras()
prefs=bpy.context.preferences.addons['cycles'].preferences;device='CPU'
try:
    prefs.compute_device_type='OPTIX';prefs.get_devices();ds=[d for d in prefs.devices if d.type=='OPTIX']
    if ds:
        for d in prefs.devices:d.use=d in ds
        device='GPU'
except Exception:pass
for cam in sorted((o for o in bpy.data.objects if o.type=='CAMERA' and o.get('V16_review')),key=lambda o:o.name):
    if only and cam.name.split()[1] not in only:continue
    sc.camera=cam;sc.render.engine='CYCLES';sc.cycles.device=device;sc.cycles.samples=samples;sc.cycles.use_denoising=True
    sc.cycles.transparent_max_bounces=32
    sc.render.resolution_x=width;sc.render.resolution_y=height;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
    sc.render.filepath=os.path.join(out,re.sub('[^A-Za-z0-9]+','_',cam.name).strip('_')+'.png')
    bpy.ops.render.render(write_still=True,scene=sc.name);print('RENDER_OK',cam.name,flush=True)
