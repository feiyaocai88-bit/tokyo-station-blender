"""V14 geometry, continuity and source preservation checks. -- baseline report."""
import bpy,sys,os,json,math,numpy as np
from mathutils import Vector
sys.path.insert(0,os.path.dirname(__file__))
import v14lib as H
from mod12_surface_trains import fingerprint
from mod14_ground import wall_y
args=sys.argv[sys.argv.index('--')+1:];sc=bpy.context.scene;R=json.loads(sc['V14_refinement']);checks=[]
def check(name,bad,**kw):
 checks.append({'name':name,'pass':not bool(bad),'failures':bad,**kw});print(name,'PASS' if not bad else 'FAIL',str(bad)[:700],flush=True)
base=json.load(open(args[0]));now=fingerprint();lookup={r['original']:r['retained'] for r in R['retained']};reverse={v:k for k,v in lookup.items()};bad=[]
for name,value in base.items():
 nn=lookup.get(name,name);v=now.get(nn)
 if v is None:bad.append([name,'missing']);continue
 v=dict(v)
 if v.get('parent') in reverse:v['parent']=reverse[v['parent']]
 if v!=value:bad.append([name,'source geometry or transform changed'])
check('all V13 source objects retained with unchanged geometry transforms and materials',bad,count=len(base))
bad=[];minimum=999
for m in R['catenary']['new_masts']:
 clearance=min(abs(m['y']-float(H.ty(k,m['x'])))-.175 for k in ['03','04','05','06','07','08','09','10']);minimum=min(minimum,clearance)
 if clearance<2.30:bad.append([m['x'],m['y'],clearance])
check('new mast shafts clear conventional vehicle envelopes',bad,min_clearance_m=minimum,masts=len(R['catenary']['new_masts']))
v,inv,lo,hi=H.component_labels(bpy.data.objects['V6 OCS | masts']);centers=(lo+hi)/2;bad=[]
for p in R['catenary']['old_mast_xy']:
 if np.any((np.linalg.norm(centers[:,:2]-np.array(p),axis=1)<.65)&((hi[:,2]-lo[:,2])>3)):bad.append(p)
check('all replaced south mast shafts are removed from the active mesh',bad,replaced=len(R['catenary']['old_mast_xy']))
v,inv,lo,hi=H.component_labels(bpy.data.objects['V6 OCS | V-truss beams and cantilevers']);c=(lo+hi)/2
bad=c[(c[:,0]>157)&(lo[:,2]<13.5)].tolist()
check('old south conventional trusses and high tie rods are removed',bad)
wire=bpy.data.objects['V14 south OCS wire'];world=H.world(wire);bad=[];maxdev=0;samples=0
for r in R['catenary']['contact_spans']:
 a,b=np.array(r['start_xy']),np.array(r['end_xy']);k=r['track'];z=r['contact_z']
 for f in np.linspace(0,1,121):
  p=a+(b-a)*f;dev=abs(p[1]-float(H.ty(k,p[0])));maxdev=max(maxdev,dev);samples+=1
  if dev>.281:bad.append([k,'offset',f,dev])
  if f not in (0,1):
   hit,loc,n,idx=wire.ray_cast(Vector((*p,z+.04)),Vector((0,0,-1)),distance=.08)
   if not hit:bad.append([k,'missing actual contact wire',f])
 if r['join_to_inherited']:
  o=bpy.data.objects['V6 OCS | contact wires and messengers'];v=H.world(o);d=np.linalg.norm(v-np.array([*a,z]),axis=1)
  if d.min()>.012:bad.append([k,'gap to inherited wire',float(d.min())])
check('straight contact spans are continuous and inside pantograph working width',bad,max_offset_m=maxdev,samples=samples)
bad=[];count=0
for k,rs in R['catenary']['supports'].items():
 for r in rs:
  p=r['contact_xy'];z=r['messenger_z'];count+=1
  hit,*_=wire.ray_cast(Vector((*p,z+.03)),Vector((0,0,-1)),distance=.06)
  if not hit:bad.append([k,r['row_x'],'messenger missing at clamp'])
  o=bpy.data.objects['V14 south OCS beam'];hit,*_=o.ray_cast(Vector((p[0],p[1],r['beam_z']+.20)),Vector((0,0,-1)),distance=.4)
  if not hit:bad.append([k,r['row_x'],'suspension not attached to beam'])
check('messenger clamps and suspension rods meet actual new beams',bad,supports=count)
bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
def ray(p,d,dist):
 hit,loc,n,idx,o,m=sc.ray_cast(dg,Vector(p),Vector(d),distance=dist)
 return (o.name,list(loc)) if hit else (None,None)
bad=[]
for m in R['catenary']['new_masts']:
 name,p=ray((m['x']+.43,m['y'],4.75),(0,0,-1),.55)
 if not p or not 4.40<p[2]<4.72:bad.append([m['x'],m['y'],name,p])
check('mast plinths land on existing deck structure',bad)
bad=[];count=0
for x in np.linspace(184,250,45):
 for off in [-5.8,-4.5,-3.2]:
  y=wall_y(x)+off;name,p=ray((x,y,.34),(0,0,-1),.20);count+=1
  if not p or abs(p[2]-.205)>.03:bad.append([float(x),off,'floor',name,p])
  name,p=ray((x,y,.31),(0,0,1),2.05)
  if name:bad.append([float(x),off,'headroom',name,p])
check('south sidewalk has continuous floor and walking headroom',bad,samples=count)
bus=bpy.data.objects['V14 parked yellow sightseeing coach with cabin and wheel wells'];lo,hi=H.bounds(bus)
check('parked coach tyres rest on road surface',[] if abs(float(lo[2])-.145)<.003 else [float(lo[2])],tyre_min_z=float(lo[2]),road_top_z=.145)
bad=[]
for name in base:
 if name.startswith('V12 ') or name.startswith('V11 M17') or name.startswith('V13 M7') or name.startswith('V13 M8'):
  if name in lookup:bad.append([name,'unrelated source retired'])
check('V12 rolling stock and V13 Metro access remain active',bad)
bad=[];n=0
for o in sc.objects:
 if o.type=='MESH' and o.name.startswith('V14 ') and len(o.data.vertices):
  n+=1
  if not np.isfinite(H.world(o)).all():bad.append([o.name,'nonfinite'])
check('new native meshes are finite',bad,objects=n)
rows=R['catenary']['rows'];bad=[]
if sum(r['status']=='photo_interpreted' for r in rows)!=5:bad.append('photographic and adapted support rows not distinguished')
if R['catenary']['all_masts_survey_verified']:bad.append('unsupported survey claim')
check('photo estimates and additional curve support are explicitly distinguished',bad,rows=rows)
bad=[i.name for i in bpy.data.images if i.source=='FILE' and not i.packed_file and i.filepath and not os.path.isfile(bpy.path.abspath(i.filepath))]
check('image assets are packed or resolve',bad)
out={'revision':14,'passed':all(x['pass'] for x in checks),'checks':checks};json.dump(out,open(args[1],'w',encoding='utf8'),ensure_ascii=False,indent=2)
if not out['passed']:raise RuntimeError('V14 checks failed; inspect report')
