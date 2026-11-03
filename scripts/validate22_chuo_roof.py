"""V22 preservation, real shell continuity and model clearance checks.
-- baseline_v21.json validate_v22.json
"""
import bpy,sys,json,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
import v22lib as H
import mod22_chuo_roof as G
a=sys.argv[sys.argv.index('--')+1:];sc=bpy.data.scenes['Tokyo Station'];bpy.context.window.scene=sc
r=json.loads(sc['V22_chuo_roof']);base=json.loads(Path(a[0]).read_text(encoding='utf8'));now=H.snapshot();checks=[]
def check(name,bad,**kw):
 checks.append({'name':name,'pass':not bool(bad),'failures':bad[:30],**kw});print(name,'FAIL' if bad else 'PASS',str(bad[:4]),flush=True)
lookup={q['original']:q['retained'] for q in r['retained']};bad=[]
for n,v in base.items():
 cur=now.get(lookup.get(n,n))
 if cur and n in lookup:cur=dict(cur);cur['visibility']=v['visibility'];cur['collections']=v['collections']
 if cur!=v:bad.append(n)
check('Every V21 source remains unchanged or preserved as an original',bad,source_objects=len(base))
check('Replaced sources are isolated and hidden',[n for n in lookup.values() if now[n]['visibility']!=[True,True] or now[n]['collections']!=['V22_Replaced_hidden']],objects=len(lookup))
new=[o for o in sc.objects if o.type=='MESH' and o.get('V22_kind') and not o.hide_render];trees={};boxes={}
def tree(o):
 if o.name not in trees:trees[o.name]=BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(p.vertices) for p in o.data.polygons])
 return trees[o.name]
def box(o):
 if o.name not in boxes:
  v=np.array([o.matrix_world@Vector(p) for p in o.bound_box]);boxes[o.name]=(v.min(0),v.max(0))
 return boxes[o.name]
def hits(p,h,objs,d=Vector((0,0,1))):
 for o in objs:
  lo,hi=box(o);end=np.array(p)+np.array(d)*h
  if np.any(np.maximum(p,end)<lo-.001) or np.any(np.minimum(p,end)>hi+.001):continue
  hit=tree(o).ray_cast(Vector(p),d,h)[0]
  if hit is not None:return o.name
 return None
unchanged=['V6 OCS | masts','V6 OCS | contact wires and messengers','V6 OCS | droppers','V6 OCS | insulators']
check('Mast and electrical wire fitting meshes keep their exact V21 geometry and coordinates',[n for n in unchanged if now[n]!=base[n]])
old_h=H.world(bpy.data.objects[lookup['V6 OCS | hangers, drop tubes, steady arms']]);new_h=H.world(bpy.data.objects['V6 OCS | hangers, drop tubes, steady arms'])
keep=(old_h[:,2]<=22.65)|(old_h[:,0]<G.X0)|(old_h[:,0]>G.X1)|(old_h[:,1]>46)
check('Lower hanger clamps steady arms and all fittings outside the roof remain exact',[] if old_h.shape==new_h.shape and np.array_equal(old_h[keep],new_h[keep]) else ['unchanged lower fitting vertices differ'],retained_vertices=int(keep.sum()))
old=bpy.data.objects[lookup['V6 OCS | V-truss beams and cantilevers']];v,labels,lo,hi=H.component_labels(old);mid=(lo+hi)/2
selected=(lo[:,2]>22.55)&(mid[:,0]>G.X0-.1)&(mid[:,0]<G.X1+.1)&(hi[:,1]<46)
kept=v[~selected[labels]];current=H.world(bpy.data.objects['V6 OCS | V-truss beams and cantilevers'])
def sorted_points(q):return q[np.lexsort((q[:,2],q[:,1],q[:,0]))]
check('Catenary steel outside the edited Chuo span has exactly the same vertices',[] if kept.shape==current.shape and np.array_equal(sorted_points(kept),sorted_points(current)) else ['retained steel vertices differ'],retained_vertices=len(kept))
bad=[];n=0
for o in new:
 if o.get('V22_kind') in ('OCS_Copy','Hanger_Copy'):continue
 q=np.vstack([H.world(o),np.array([o.matrix_world@f.center for f in o.data.polygons])]);q=q[(q[:,2]>15.45)&(q[:,0]>G.X0-.5)&(q[:,0]<G.X1+.5)]
 for k in ('01','02'):
  dy=np.abs(q[:,1]-np.interp(q[:,0],H.D['X'],H.D['target'][k]));body=(dy<1.60)&(q[:,2]<19.90);upper=(dy<.78)&(q[:,2]>=19.9)&(q[:,2]<22.20)
  if np.any(body|upper):bad.append([o.name,k,int(np.sum(body|upper)),q[body|upper][:2].tolist()])
 n+=len(q)
check('New roof and fittings clear both train bodies and upper electrical corridors',bad,samples=n,body_half_width=1.6,upper_half_width=.78,upper_clear_z=22.2)
shells=[o for o in new if o.get('V22_kind') in ('Green_Roof','Curved_Enclosure','White_Cover')]
bad=[];pairs=0
for o in shells:
 for n in unchanged+['V6 OCS | V-truss beams and cantilevers','V6 OCS | hangers, drop tubes, steady arms','V22 Chuo internal transverse contact support beams']:
  q=bpy.data.objects[n];lo,hi=box(o);l,h=box(q)
  if np.any(hi<l) or np.any(lo>h):continue
  overlap=tree(o).overlap(tree(q));pairs+=1
  if overlap:bad.append([o.name,n,len(overlap)])
check('Actual envelope meshes do not intersect retained electrical or mast meshes',bad,pairs=pairs)
roof=bpy.data.objects['V22 Chuo broad shallow mint roof sheets'];bad=[];n=0
for s,label in [(-1,'west'),(1,'east')]:
 side=bpy.data.objects['V22 Chuo '+label+' continuous dark curved glazing']
 for x in np.linspace(G.X0+.2,G.X1-.2,67):
  for t in (.10,.40,.75,1.10,1.48):
   p=Vector(G.shoulder(float(x),s,t))+Vector((0,0,.16))
   if tree(side).ray_cast(p,Vector((0,0,-1)),.30)[0] is None:bad.append([label,x,t])
   n+=1
  # The glazing crown and mint boundary share the same analytic position;
  # both actual meshes must continue up to that joint.
  edge=Vector(G.shoulder(float(x),s,np.pi/2));inside=edge+Vector((0,-s*.035,.16));outside=edge+Vector((0,s*.035,.16))
  if tree(roof).ray_cast(inside,Vector((0,0,-1)),.32)[0] is None:bad.append(['green edge',label,x])
  if tree(side).ray_cast(outside,Vector((0,0,-1)),.32)[0] is None:bad.append(['glazed edge',label,x])
check('Both curved shoulders are continuous and meet the mint roof along their crowns',bad,samples=n)
bad=[];n=0
for q in r['masts']:
 for dx,dy in ((0,0),(.28,0),(-.28,0),(0,.28),(0,-.28)):
  p=Vector((q['x']+dx,q['y']+dy,G.CROWN-1))
  if tree(roof).ray_cast(p,Vector((0,0,1)),2)[0] is not None:bad.append([q['x'],q['y'],dx,dy])
  n+=1
check('Green-roof openings preserve clear space around the existing mast shafts',bad,samples=n,openings=len(r['masts']))
bad=[];beam=bpy.data.objects['V22 Chuo internal transverse contact support beams']
for q in r['catenary']['hanger_top_attachments']:
 p=Vector((q['x'],q['y'],q['top_z']-.10))
 if tree(beam).ray_cast(p,Vector((0,0,1)),.15)[0] is None:bad.append(q)
check('Every adapted hanger mounting point reaches a curved internal support beam',bad,attachments=len(r['catenary']['hanger_top_attachments']))
bad=[];n=0
for q in json.loads(sc['V6_platform_keepouts']):
 if q['kind']!='stairwell' or q['island']!='01-02':continue
 u=Vector((*q['u'],0));v=Vector((-u.y,u.x,0))
 for x in np.linspace(.3,7,10):
  for y in (-1.2,0,1.2):
   p=Vector((*q['c'],16.57))+u*x+v*y;hit=hits(p,2.35,new)
   if hit:bad.append([q['pos'],hit,list(p)])
   n+=1
oldreport=json.loads(sc['V20_chuo'])
for spec,ys,length in [(oldreport['staff_room'],(-2.25,2.25),10.4),(oldreport['passage'],(-.5,0,.5),11.3)]:
 F=Matrix(spec['frame'])
 for x in np.linspace(.35,length-.5,28) if spec is oldreport['passage'] else np.linspace(-6,6,28):
  for y in ys:
   p=F@Vector((x,y,.06));hit=hits(p,2.1,new)
   if hit:bad.append(['retained passage',hit,list(p)])
   n+=1
check('Existing stairs staff-room side routes and covered end passage remain clear',bad,samples=n)
bad=[];cap=bpy.data.objects['V22 Chuo raised transverse white cover'];supports=bpy.data.objects['V22 Chuo white cover bearing curbs and support struts']
for x in (-10.45,0,10.45):
 w,e=G.edges(x)
 for y in (w+.20,e-.20):
  p=Vector((x,y,G.CROWN+.13))
  if tree(roof).ray_cast(p,Vector((0,0,-1)),.25)[0] is None:bad.append(['support has no roof bearing',x,y])
  if tree(supports).ray_cast(p,Vector((0,0,1)),1.5)[0] is None:bad.append(['missing strut',x,y])
  if tree(cap).ray_cast(p,Vector((0,0,1)),1.5)[0] is None:bad.append(['missing cover',x,y])
check('Raised white transverse cover has supported bearing points and an intact shell',bad,bearings=6)
lower=bpy.data.objects['V10 03-04 differentiated roof skin'];portals=bpy.data.objects['V22 Chuo full width continuous portal rings'];bad=[];bearings=0;connections=0
for q in r['interlevel_connections']:
 unit={k:bpy.data.objects[v] for k,v in q['objects'].items()}
 for x,y,z in q['bearing_corners']:
  p=Vector((x,y,z+.06))
  if tree(lower).ray_cast(p,Vector((0,0,-1)),.12)[0] is None:bad.append([q['id'],'roof bearing',x,y])
  bearings+=1
 for ob_a,ob_b in [(unit['curb'],lower),(unit['riser'],unit['curb']),(unit['riser'],unit['cabinet']),(unit['brackets'],unit['cabinet']),(unit['brackets'],unit['curb']),(unit['brackets'],portals)]:
  if not tree(ob_a).overlap(tree(ob_b)):bad.append([q['id'],ob_a.name,ob_b.name])
  connections+=1
check('Each interlevel assembly joins a real lower-roof bearing cabinet riser and upper portal',bad,units=len(r['interlevel_connections']),bearing_corners=bearings,mesh_connections=connections)
bad=[];pairs=0
for o in new:
 if not o.get('V22_kind','').startswith('Interlevel_'):continue
 for name in unchanged+['V6 OCS | hangers, drop tubes, steady arms','V6 OCS | V-truss beams and cantilevers']:
  q=bpy.data.objects[name];lo,hi=box(o);l,h=box(q)
  if np.any(hi<l) or np.any(lo>h):continue
  pairs+=1
  if tree(o).overlap(tree(q)):bad.append([o.name,name])
check('Interlevel equipment and supports avoid the actual overhead-line meshes',bad,pairs=pairs)
bad=[]
for o in new:
 if not np.isfinite(H.world(o)).all():bad.append(o.name)
for im in bpy.data.images:
 if im.source=='FILE' and not im.packed_file and not Path(bpy.path.abspath(im.filepath)).exists():bad.append('image '+im.name)
check('Finite native geometry and resolving image resources',bad,mesh_objects=len(new))
passed=all(c['pass'] for c in checks);report={'revision':22,'passed':passed,'checks':checks,'limits':'An interpretation of the supplied aerial photograph. Roof dimensions and internal support arrangements are model adaptations, not measured engineering data. Original wire, insulator, mast and lower hanger coordinates stay; only upper hanger ends and mounting plates adapt to the curved support beams. No inherited positions are claimed to be surveyed.'}
Path(a[1]).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
if not passed:raise RuntimeError('V22 validation failed')
