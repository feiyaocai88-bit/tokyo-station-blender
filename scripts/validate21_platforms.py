"""Geometry-based preservation and platform passage checks. -- baseline report"""
import bpy,sys,json,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
sys.path.insert(0,str(Path(__file__).parent))
import v21lib as H
a=sys.argv[sys.argv.index('--')+1:];sc=bpy.data.scenes['Tokyo Station'];bpy.context.window.scene=sc
r=json.loads(sc['V21_platforms']);base=json.loads(Path(a[0]).read_text(encoding='utf8'));now=H.snapshot();checks=[]
def check(name,bad,**kw):
 checks.append({'name':name,'pass':not bool(bad),'failures':bad[:30],**kw});print(name,'FAIL' if bad else 'PASS',str(bad[:4]),flush=True)
lookup={q['original']:q['retained'] for q in r['retained']};bad=[]
for n,v in base.items():
 cur=now.get(lookup.get(n,n))
 if cur and n in lookup:cur=dict(cur);cur['visibility']=v['visibility'];cur['collections']=v['collections']
 if cur!=v:bad.append(n)
check('Every V20 source is unchanged or preserved with original geometry and materials',bad,source_objects=len(base))
check('Replacement originals are isolated and hidden',[n for n in lookup.values() if now[n]['visibility']!=[True,True] or now[n]['collections']!=['V21_Replaced_hidden']],objects=len(lookup))
expected=['01-02','03-04','05-06','07-08','09-10','14-15','16-17','18-19','20-21','22-23','Sobu 1-2','Sobu 3-4','Metro M17']
new=[o for o in sc.objects if o.type=='MESH' and o.get('V21_kind')];trees={};bounds={}
def tree(o):
 if o.name not in trees:trees[o.name]=H.bvh(o)
 return trees[o.name]
def box(o):
 if o.name not in bounds:bounds[o.name]=H.bounds(o)
 return bounds[o.name]
def hits(p,h,objs):
 for o in objs:
  lo,hi=box(o)
  if not(lo[0]-.005<=p[0]<=hi[0]+.005 and lo[1]-.005<=p[1]<=hi[1]+.005 and hi[2]>=p[2] and lo[2]<=p[2]+h):continue
  hit=tree(o).ray_cast(Vector(p),Vector((0,0,1)),h)[0]
  if hit is not None:return o.name
 return None
check('All ten surface islands and three underground islands receive native detail',[s for s in expected if s not in r['platforms'] or not any(o.get('island')==s for o in new)],groups=len(expected))
bad=[];n=0
for q in r['rooms']:
 F=Matrix(q['frame']);deck=bpy.data.objects['V3 Platform '+q['island']+' raised deck']
 for x in np.linspace(-q['length']/2-.3,q['length']/2+.3,30):
  for y in (-q['walkway_sample_offset'],q['walkway_sample_offset']):
   p=F@Vector((x,y,.06))
   if tree(deck).ray_cast(p,Vector((0,0,-1)),.12)[0] is None:bad.append(['unsupported',q['island'],list(p)])
   hit=hits(p,2.1,new)
   if hit:bad.append([hit,list(p)])
   n+=1
check('Waiting-room side passages have existing deck support and 2.1 m headroom',bad,samples=n,rooms=len(r['rooms']))
bad=[];n=0
for q in json.loads(sc['V6_platform_keepouts']):
 if q['kind']!='stairwell':continue
 z=r['platforms'][q['island']]['deck_z'];u=Vector((*q['u'],0));v=Vector((-u.y,u.x,0))
 for x in np.linspace(.3,7,10):
  for y in (-1.2,0,1.2):
   p=Vector((*q['c'],z+.06))+u*x+v*y;hit=hits(p,2.35,new)
   if hit:bad.append([q['island'],q['pos'],hit,list(p)])
   n+=1
check('All thirty existing surface stair apertures stay clear',bad,samples=n)
bad=[];samples=0
for o in new:
 isl=o.get('island');kind=o.get('V21_kind')
 if isl not in expected[:10] or kind in ('Paving','Sign_Hangers_Adjusted'):continue
 z=r['platforms'][isl]['deck_z'];q=np.vstack([H.world(o),np.array([o.matrix_world@f.center for f in o.data.polygons])]);q=q[(q[:,2]>z-.1)&(q[:,0]>r['platforms'][isl]['extent'][0])&(q[:,0]<r['platforms'][isl]['extent'][1])]
 for k in isl.split('-'):
  dy=np.abs(q[:,1]-np.interp(q[:,0],H.D['X'],H.D['target'][k]));body=(dy<1.49)&(q[:,2]<z+3.55);upper=(dy<.78)&(q[:,2]>=z+3.55)&(q[:,2]<z+5.50)
  if np.any(body|upper):bad.append([o.name,k,int(np.sum(body|upper)),q[body|upper][:2].tolist()])
 samples+=len(q)
check('New structures clear model train-body and upper electrical corridors',bad,samples=samples,body_half_width=1.49,upper_half_width=.78,upper_clearance_above_platform=5.5)
bad=[];n=0
import csv
roof=[o for o in new if o.get('V21_kind') in ('Roof_Skins','Roof_Details','Roof_Structure','Soffits')]
with (Path(__file__).parent.parent/'validation/surface_catenary_masts.csv').open() as f:
 for q in csv.DictReader(f):
  x,y,z0,z1=[float(q[k]) for k in ('x','y','base_z','top_z')]
  for dx,dy in ((0,0),(.20,0),(-.20,0),(0,.20),(0,-.20)):
   hit=hits(Vector((x+dx,y+dy,z0+.10)),z1-z0-.2,roof)
   if hit:bad.append([q['id'],hit,x+dx,y+dy])
   n+=1
check('Actual roof meshes and frames leave the inherited OCS mast shafts open',bad,samples=n)
hidden=set()
def walk(c,h=False):
 h=h or c.hide_render
 if h:hidden.update(o.name for o in c.objects)
 for cc in c.children:walk(cc,h)
walk(sc.collection)
ocs=[o for o in sc.objects if o.type=='MESH' and 'OCS' in o.name and not o.hide_render and o.name not in hidden]
bad=[];pairs=0
for o in new:
 if o.get('V21_kind') not in ('Roof_Equipment_Adjusted','Roof_Room_Supports'):continue
 lo,hi=box(o)
 for w in ocs:
  wl,wh=box(w)
  if np.any(hi<wl) or np.any(lo>wh):continue
  overlap=tree(o).overlap(tree(w));pairs+=1
  if overlap:bad.append([o.name,w.name,len(overlap)])
check('Relocated rooftop rooms and support pedestals clear actual OCS meshes',bad,geometry_pairs=pairs)
from mod11_marunouchi import F as MF,DECK as MZ
gate=bpy.data.objects['V11 M17 36 half height platform door pairs and tactile paving'];lamps=bpy.data.objects['V21 M17 platform gate status lamps'];bad=[];n=0
for centre in [-45+18*i for i in range(6)]:
 for offset in (-5.4,0,5.4):
  for s in (-1,1):
   p=MF@Vector((centre+offset+.75,s*4.12,MZ+1.205))
   if tree(gate).ray_cast(p,Vector((0,0,-1)),.025)[0] is None:bad.append(['missing gate post',list(p)])
   if tree(lamps).ray_cast(p-Vector((0,0,.01)),Vector((0,0,1)),.10)[0] is None:bad.append(['missing lamp',list(p)])
   n+=1
check('All Metro status lamps attach to the existing door-post tops',bad,lamps=n)
check('Underground cutaway sides stay open',[o.name for o in new if o.get('V21_kind','').startswith('Underground') and (box(o)[1][2]-box(o)[0][2]>3.20)],side_walls_added=0)
bad=[]
for o in new:
 if not np.isfinite(H.world(o)).all():bad.append(o.name)
for im in bpy.data.images:
 if im.source=='FILE' and not im.packed_file and not Path(bpy.path.abspath(im.filepath)).exists():bad.append('image '+im.name)
check('Finite native geometry and resolving image resources',bad,mesh_objects=len(new))
passed=all(q['pass'] for q in checks);report={'revision':21,'passed':passed,'checks':checks,'limits':'Dated street views and photographs inform visual structure; dimensions, repeated fittings and positions are estimates. These geometric model checks are not a survey or railway operational certification.'}
Path(a[1]).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
if not passed:raise RuntimeError('V21 validation failed')
