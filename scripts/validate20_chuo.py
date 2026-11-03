"""Preservation, rail envelopes and actual floor/headroom checks. -- baseline report"""
import bpy,sys,json,math,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
import v20lib as H
a=sys.argv[sys.argv.index('--')+1:];sc=bpy.data.scenes['Tokyo Station'];bpy.context.window.scene=sc
r=json.loads(sc['V20_chuo']);base=json.loads(Path(a[0]).read_text(encoding='utf8'));now=H.snapshot();checks=[]
def check(name,bad,**kw):checks.append({'name':name,'pass':not bool(bad),'failures':bad[:30],**kw});print(name,'FAIL' if bad else 'PASS',str(bad[:5]),flush=True)
lookup={p['original']:p['retained'] for p in r['retained']};bad=[]
for n,v in base.items():
 cur=now.get(lookup.get(n,n))
 if cur and n in lookup:cur=dict(cur);cur['collections']=v['collections'];cur['visibility']=v['visibility']
 if cur!=v:bad.append(n)
check('All V19 source geometry materials transforms and unrelated content retained',bad,source_objects=len(base))
check('Replaced sources are isolated and hidden',[n for n in lookup.values() if now[n]['visibility']!=[True,True] or now[n]['collections']!=['V20_Replaced_hidden']],objects=len(lookup))
new=[o for o in sc.objects if o.type=='MESH' and o.get('V20_kind')];cache={};boxes={}
def tree(o):
 if o.name not in cache:cache[o.name]=BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(f.vertices) for f in o.data.polygons])
 return cache[o.name]
def box(o):
 if o.name not in boxes:
  p=np.array([o.matrix_world@Vector(v) for v in o.bound_box]);boxes[o.name]=(p.min(0),p.max(0))
 return boxes[o.name]
def hits_up(p,h,objects):
 for o in objects:
  lo,hi=box(o)
  if not(lo[0]-.01<=p[0]<=hi[0]+.01 and lo[1]-.01<=p[1]<=hi[1]+.01 and hi[2]>=p[2] and lo[2]<=p[2]+h):continue
  hit,_,_,dist=tree(o).ray_cast(Vector(p),Vector((0,0,1)),h)
  if hit is not None:return o.name
 return None
# Room and both continuous side routes must land on the existing deck, away from wells.
deck=bpy.data.objects['V3 Platform 01-02 raised deck'];F=Matrix(r['staff_room']['frame']);bad=[];samples=0
for x in np.linspace(-6.1,6.1,50):
 for y in (-2.25,2.25):
  p=F@Vector((x,y,.055));hit=tree(deck).ray_cast(p,Vector((0,0,-1)),.1)[0]
  if hit is None:bad.append(['missing deck',list(p)])
  ob=hits_up(p,2.10,new)
  if ob:bad.append([ob,list(p)])
  samples+=1
check('Both staff-room side passages have real deck support and 2.1 m headroom',bad,samples=samples)
bad=[];n=0
for q in json.loads(sc['V6_platform_keepouts']):
 if q['island']!='01-02' or q['kind']!='stairwell':continue
 u=Vector((*q['u'],0));v=Vector((-u.y,u.x,0))
 for x in np.linspace(.35,7.0,12):
  for y in (-1.2,0,1.2):
   p=Vector((*q['c'],16.55))+u*x+v*y;ob=hits_up(p,2.5,new)
   if ob:bad.append([q['pos'],ob,list(p)])
   n+=1
check('Existing north central and south stair openings remain clear',bad,samples=n)
bad=[];F=Matrix(r['passage']['frame']);floor=bpy.data.objects['V20 end passage supported walkway'];objs=[o for o in new if o.get('V20_kind') in ['End_Passage','End_Passage_Detail']];n=0
for x in np.linspace(.35,r['passage']['length']-.5,24):
 for y in (-.50,0,.50):
  p=F@Vector((x,y,.055))
  if tree(floor).ray_cast(p,Vector((0,0,-1)),.15)[0] is None:bad.append(['missing floor',list(p)])
  ob=hits_up(p,2.08,objs)
  if ob:bad.append([ob,list(p)])
  n+=1
check('Covered end passage has a continuous supported floor and central headroom',bad,samples=n)
# Check actual new vertices AND triangle-centre samples against moving-body and
# pantograph/messenger corridors; checks are geometric, not operating certification.
bad=[];n=0
for o in new:
 if o.get('V20_kind') not in ['Curved_Ribs','Rib_Anchors','Acoustic_Screens','Staff_Room','End_Passage','End_Passage_Floor','CCTV','Monitors']:continue
 v=H.world(o);centres=np.array([o.matrix_world@p.center for p in o.data.polygons]);q=np.vstack([v,centres]);q=q[(q[:,2]>15.45)&(q[:,0]>-146)&(q[:,0]<123.5)]
 for k in ('01','02'):
  dy=np.abs(q[:,1]-np.interp(q[:,0],H.D['X'],H.D['target'][k]));body=(dy<1.60)&(q[:,2]<19.9)
  upper=(dy<.78)&(q[:,2]>=19.9)&(q[:,2]<22.2)
  if np.any(body|upper):bad.append([o.name,k,int(np.count_nonzero(body|upper)),q[body|upper][:2].tolist()])
 n+=len(q)
check('New structures clear both train bodies and the upper electrical corridor',bad,samples=n,body_half_width=1.6,upper_half_width=.78,upper_clear_z=22.2)
bad=[]
for side,k in [('west','01'),('east','02')]:
 o=bpy.data.objects['V20 Chuo '+side+' framed acoustic panels'];v=H.world(o);d=H.world(bpy.data.objects['V3 Track '+k+' curved viaduct'])
 if v[:,0].min()<d[:,0].min()+.1 or v[:,0].max()>d[:,0].max()-.1:bad.append(side)
check('Acoustic screens remain within the corrected viaduct ends',bad)
bad=[]
for o in new:
 if not np.isfinite(H.world(o)).all():bad.append(o.name)
for im in bpy.data.images:
 if im.source=='FILE' and not im.packed_file and not Path(bpy.path.abspath(im.filepath)).exists():bad.append('image '+im.name)
check('Finite new geometry and resolving packed image resources',bad)
passed=all(c['pass'] for c in checks);report={'revision':20,'passed':passed,'checks':checks,'limits':'Photo-derived visual fittings adapted to the inherited geometry; no claim of surveyed equipment positions, load calculations or operational railway clearance certification.'}
Path(a[1]).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
if not passed:raise RuntimeError('V20 validation failed')
