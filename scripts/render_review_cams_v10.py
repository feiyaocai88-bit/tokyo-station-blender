"""Render the V10 cameras. Usage: blender -b scene.blend -P this.py -- out_dir [samples] [01,02,...] [width height]."""
import bpy, sys, os, re

args=sys.argv[sys.argv.index('--')+1:]
out=os.path.abspath(args[0]); os.makedirs(out,exist_ok=True)
samples=int(args[1]) if len(args)>1 else 64
only=set(args[2].split(',')) if len(args)>2 and args[2] else None
sc=bpy.context.scene
sc.render.engine='CYCLES'
prefs=bpy.context.preferences.addons['cycles'].preferences
try:
    prefs.compute_device_type='OPTIX';prefs.get_devices()
    devices=[d for d in prefs.devices if d.type=='OPTIX']
    if not devices: raise RuntimeError('No OptiX device')
    for d in prefs.devices: d.use=d in devices
    sc.cycles.device='GPU'
except Exception:
    sc.cycles.device='CPU'
sc.cycles.samples=samples;sc.cycles.use_denoising=True
sc.cycles.transparent_max_bounces=32
sc.render.resolution_x=int(args[3]) if len(args)>3 else 1600
sc.render.resolution_y=int(args[4]) if len(args)>4 else 1000
sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG'
for cam in sorted(bpy.data.collections['V10_Review_Cameras'].objects,key=lambda o:o.name):
    num=cam.name.split()[1]
    if only and num not in only: continue
    sc.camera=cam
    slug=re.sub('[^A-Za-z0-9]+','_',cam.name).strip('_')
    sc.render.filepath=os.path.join(out,slug+'.png')
    bpy.ops.render.render(write_still=True)
    print('RENDER_OK',cam.name,flush=True)
