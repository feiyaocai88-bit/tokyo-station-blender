"""Native model review cameras. -- folder samples ids width height."""
import bpy,sys,os,re,json
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
import v21lib as H
def cameras(report=None):
 sc=bpy.data.scenes['Tokyo Station'];bpy.context.window.scene=sc
 report=report or json.loads(sc['V21_platforms']);spec=[]
 for j,isl in enumerate(['01-02','03-04','05-06','07-08','09-10','14-15','16-17','18-19','20-21','22-23'],1):
  p=report['platforms'][isl];z=p['deck_z'];x=-29;y=H.yc(isl,x)
  if isl=='01-02':pos=(32,27.5,18.18);target=(43,23.9,18.13)
  else:
   room=next((r for r in report['rooms'] if r['island']==isl),None)
   if room:x=room['frame'][0][3]-(3.5 if isl=='16-17' else 5);y=H.yc(isl,x)
   pos=(x,y+(3.25 if room else 2.7),z+1.7);target=(x+(10 if room else 18),H.yc(isl,x+(10 if room else 18))+.3,z+2.05)
  spec.append((f'{j:02d} Platform {isl}',pos,target,23,None))
 import v9geo as G
 for j,isl in enumerate(('1-2','3-4'),11):
  cy=G.ISL_C[isl];F=G.frame_matrix();p=F@Vector((-145,cy+1.15,G.DECK+1.65));t=F@Vector((-124,cy+1.3,G.DECK+1.8))
  spec.append((f'{j:02d} Sobu B5 {isl}',p,t,23,None))
 from mod11_marunouchi import F,DECK
 spec.append(('13 Metro Marunouchi M17',F@Vector((-14.3,3.05,DECK+1.65)),F@Vector((10,2.80,DECK+1.65)),23,None))
 spec.append(('14 All platform roofs',(245,-180,215),(-5,105,8),50,440))
 # A closer external roof view makes the five canopy families easy to compare.
 spec.append(('15 Conventional roof profiles',(172,-40,96),(-30,66,10),48,208))
 c=H.col('Review_Cameras')
 for n,p,t,l,scale in spec:
  name='V21 '+n;o=bpy.data.objects.get(name)
  if o is None:d=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,d);c.objects.link(o)
  o.location=p;o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler();o.data.lens=l;o.data.clip_start=.035;o.data.clip_end=2500;o['V21_review']=True
  if scale:o.data.type='ORTHO';o.data.ortho_scale=scale
 sc.camera=bpy.data.objects['V21 14 All platform roofs']
def main():
 a=sys.argv[sys.argv.index('--')+1:];out=Path(a[0]).resolve();out.mkdir(parents=True,exist_ok=True);sc=bpy.data.scenes['Tokyo Station'];bpy.context.window.scene=sc;cameras()
 prefs=bpy.context.preferences.addons['cycles'].preferences;device='CPU'
 try:
  prefs.compute_device_type='OPTIX';prefs.get_devices();ds=[d for d in prefs.devices if d.type=='OPTIX']
  if ds:
   for d in prefs.devices:d.use=d in ds
   device='GPU'
 except Exception:pass
 for cam in sorted((o for o in sc.objects if o.type=='CAMERA' and o.get('V21_review')),key=lambda o:o.name):
  if cam.name.split()[1] not in a[2].split(','):continue
  sc.camera=cam;sc.render.engine='CYCLES';sc.cycles.device=device;sc.cycles.samples=int(a[1]);sc.cycles.use_denoising=True;sc.cycles.transparent_max_bounces=32
  sc.render.resolution_x=int(a[3]);sc.render.resolution_y=int(a[4]);sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
  sc.render.filepath=str(out/(re.sub('[^A-Za-z0-9]+','_',cam.name).strip('_')+'.png'));bpy.ops.render.render(write_still=True,scene=sc.name);print('V21_RENDER_OK',cam.name,flush=True)
if __name__=='__main__':main()
