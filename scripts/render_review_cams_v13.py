"""Render V13 views: -- output_dir samples selected_numbers width height."""
import bpy,sys,os,re
args=sys.argv[sys.argv.index('--')+1:];out=os.path.abspath(args[0]);os.makedirs(out,exist_ok=True)
samples=int(args[1]) if len(args)>1 else 64;only=set(args[2].split(',')) if len(args)>2 and args[2] else None
width=int(args[3]) if len(args)>3 else 1600;height=int(args[4]) if len(args)>4 else 1000
prefs=bpy.context.preferences.addons['cycles'].preferences;device='CPU'
try:
    prefs.compute_device_type='OPTIX';prefs.get_devices();ds=[d for d in prefs.devices if d.type=='OPTIX']
    if ds:
        for d in prefs.devices:d.use=d in ds
        device='GPU'
except Exception:pass
for c in sorted((o for o in bpy.data.objects if o.type=='CAMERA' and o.get('V13_scene')),key=lambda o:o.name):
    if only and c.name.split()[1] not in only:continue
    sc=bpy.data.scenes[c['V13_scene']];sc.camera=c;sc.render.engine='CYCLES';sc.cycles.device=device;sc.cycles.samples=samples;sc.cycles.use_denoising=True;sc.cycles.transparent_max_bounces=32
    sc.render.resolution_x=width;sc.render.resolution_y=height;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
    sc.render.filepath=os.path.join(out,re.sub('[^A-Za-z0-9]+','_',c.name).strip('_')+'.png')
    bpy.ops.render.render(write_still=True,scene=sc.name);print('RENDER_OK',c.name,flush=True)
