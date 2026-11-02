"""Render V11 review views: -- out_dir samples comma_separated_camera_numbers width height."""
import bpy,sys,os,re
args=sys.argv[sys.argv.index('--')+1:];out=os.path.abspath(args[0]);os.makedirs(out,exist_ok=True)
samples=int(args[1]) if len(args)>1 else 64
only=set(args[2].split(',')) if len(args)>2 and args[2] else None
width=int(args[3]) if len(args)>3 else 1600;height=int(args[4]) if len(args)>4 else 1000
main=bpy.context.scene
prefs=bpy.context.preferences.addons['cycles'].preferences
device='CPU'
try:
    prefs.compute_device_type='OPTIX';prefs.get_devices();devices=[d for d in prefs.devices if d.type=='OPTIX']
    if devices:
        for d in prefs.devices:d.use=d in devices
        device='GPU'
except Exception:pass
for cam in sorted(bpy.data.collections['V11_Review_Cameras'].objects,key=lambda o:o.name):
    num=cam.name.split()[1]
    if only and num not in only:continue
    sc=bpy.data.scenes['V11 Marunouchi cutaway'] if num=='13' else bpy.data.scenes['V11 2000 series vehicle study'] if num=='14' else main
    sc.render.engine='CYCLES';sc.cycles.device=device;sc.cycles.samples=samples;sc.cycles.use_denoising=True;sc.cycles.transparent_max_bounces=32
    sc.render.resolution_x=width;sc.render.resolution_y=height;sc.render.resolution_percentage=100
    sc.render.image_settings.file_format='PNG';sc.camera=cam
    # The diorama studio plane is an artificial backdrop at -4.2 m; it must not cut the B1 camera.
    restore=[]
    if num=='12':
        for o in main.objects:
            if o.type=='MESH' and 'studio' in o.name.lower() and not o.hide_render:restore.append(o);o.hide_render=True
    sc.render.filepath=os.path.join(out,re.sub('[^A-Za-z0-9]+','_',cam.name).strip('_')+'.png')
    bpy.ops.render.render(write_still=True,scene=sc.name)
    for o in restore:o.hide_render=False
    print('RENDER_OK',cam.name,flush=True)
