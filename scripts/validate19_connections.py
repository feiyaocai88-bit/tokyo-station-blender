"""Preservation plus actual street, walkway, roof and Metro-opening checks.
-- baseline.json report.json
"""
import bpy,sys,os,json,math,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,os.path.dirname(__file__))
from v16lib import snapshot
from v18lib import bounds
args=sys.argv[sys.argv.index('--')+1:];sc=bpy.data.scenes['Tokyo Station'];bpy.context.window.scene=sc
r=json.loads(sc['V19_connections']);plan=json.loads(Path(__file__).with_name('streets_v19.json').read_text(encoding='utf8'));base=json.load(open(args[0]));now=snapshot();checks=[]
def check(name,bad,**extra):
 checks.append({'name':name,'pass':not bool(bad),'failures':bad,**extra});print(name,'PASS' if not bad else 'FAIL',str(bad)[:700],flush=True)
lookup={q['original']:q['retained'] for q in r['retained']};rev={v:k for k,v in lookup.items()};bad=[]
for name,rec in base.items():
 cur=now.get(lookup.get(name,name))
 if cur:
  cur=dict(cur)
  if cur.get('parent') in rev:cur['parent']=rev[cur['parent']]
  if name in lookup:cur['collections']=rec['collections'];cur['visibility']=rec['visibility']
 if cur!=rec:bad.append(name)
check('Every V18 source object retained with identical geometry and materials',bad,objects=len(base))
check('Unrelated buildings trains tracks platforms and underground objects unchanged',[n for n,rec in base.items() if n not in lookup and rec!=now.get(n)],objects=len(base)-len(lookup))
check('All replaced sources isolated and hidden',[n for n in lookup.values() if now[n]['visibility']!=[True,True] or now[n]['collections']!=['V19_Replaced_hidden']],objects=len(lookup))
hidden=set()
def walk(c,h=False):
 h=h or c.hide_render
 if h:hidden.update(o.name for o in c.objects)
 for q in c.children:walk(q,h)
walk(sc.collection)
active=[o for o in sc.objects if not o.hide_render and o.name not in hidden];new=[o for o in active if o.get('V19_kind')];cache={}
def tree(o):
 if o.name not in cache:cache[o.name]=BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(f.vertices) for f in o.data.polygons])
 return cache[o.name]
road=bpy.data.objects['V19 continuous perimeter and underbridge carriageway'];area=sum(f.area for f in road.data.polygons)
bad=[]
if abs(area-plan['areas']['asphalt'])>.1:bad.append(['area',area,plan['areas']['asphalt']])
from v14lib import component_labels
v,inv,lo,hi=component_labels(road)
if len(lo)!=1:bad.append(['mesh components',len(lo)])
check('Asphalt is one connected mesh with uncapped outline holes',bad,area_m2=area,components=len(lo))
groundlo,groundhi=bounds(bpy.data.objects['Site ground']);bad=[]
for o in new:
 if o.type=='MESH' and o.get('V19_kind') in ['Road_Surface','Footways']:
  a,b=bounds(o)
  if a.x<groundlo.x-.01 or b.x>groundhi.x+.01 or a.y<groundlo.y-.01 or b.y>groundhi.y+.01:bad.append(o.name)
check('New streets and footways remain on the existing site footprint',bad)
# Only ground-height faces enter this BVH, so elevated decks do not mask a road
# collision below. Inspect both rebuilt geometry and inherited pavement/curbs.
verts=[];faces=[]
for o in active:
 if o.type!='MESH':continue
 lo,hi=bounds(o)
 if lo.z>.52 or hi.z<.125:continue
 if hi.x<-215 or lo.x>261 or hi.y<-145 or lo.y>224:continue
 vv=np.array([o.matrix_world@v.co for v in o.data.vertices])
 selected=[]
 for f in o.data.polygons:
  z=vv[list(f.vertices),2]
  if min(z)>.12 and max(z)<.52:selected.append(tuple(f.vertices))
 if not selected:continue
 offset=len(verts);verts.extend(vv.tolist());faces.extend(tuple(i+offset for i in f) for f in selected)
ground=BVHTree.FromPolygons(verts,faces);bad=[];samples=0
from mod19_connections import at_path,rear_y
for label,p in plan['paths'].items():
 length=sum(math.dist(a,b) for a,b in zip(p['points'][:-1],p['points'][1:]));last={}
 for d in np.arange(2,length-2,1.25):
  for off in (-2.2,0,2.2):
   (x,y),_=at_path(p['points'],float(d),off);hit=ground.ray_cast(Vector((x,y,.65)),Vector((0,0,-1)),.65)[0];samples+=1
   if hit is None or not .135<=hit.z<=.205:
    bad.append([label,round(x,2),round(y,2),None if hit is None else round(hit.z,3)])
   if hit and off in last and abs(hit.z-last[off])>.045:bad.append([label,'step',round(float(d),2),float(hit.z-last[off])])
   if hit:last[off]=hit.z
check('Actual road lanes have ground support and no retained curb steps',bad,samples=samples)
bad=[]
for label,x0,x1,y0,y1 in [('M8',-144,-131,-95.4,-92.6),('M7',-34,-21,-140.4,-137.6)]:
 for x in np.linspace(x0,x1,7):
  for y in np.linspace(y0,y1,3):
   for o in new:
    if o.type!='MESH' or o.get('V19_kind') not in ['Road_Surface','Footways','Crossing_Ramps']:continue
    hit=tree(o).ray_cast(Vector((x,y,1)),Vector((0,0,-1)),1.1)[0]
    if hit is not None:bad.append([label,o.name,float(x),float(y)])
check('Both M7 and M8 underground entrances remain open',bad,samples=42)
floor=bpy.data.objects['V19 continuous paved rear passage'];bad=[];samples=0
obstructions=[o for o in new if o.type=='MESH' and o.get('V19_kind') in ['Rear_Supports','Rear_Detail','Rear_Equipment']]
for x in np.arange(r['rear']['x_range'][0]+1,r['rear']['x_range'][1]-1,1.2):
 y=rear_y(float(x))+1.4;hit=tree(floor).ray_cast(Vector((x,y,1)),Vector((0,0,-1)),1)[0];samples+=1
 if hit is None or abs(hit.z-.18)>.005:bad.append(['floor',float(x),y])
 for o in obstructions:
  hit=tree(o).ray_cast(Vector((x,y,.25)),Vector((0,0,1)),3.1)[0]
  if hit is not None:bad.append(['aisle obstruction',o.name,float(x),y])
check('Rear concourse floor continuous with a clear walking corridor',bad,samples=samples)
bad=[];glass=bpy.data.objects['V19 continuous rear skylight panes following station wall'];roof=bpy.data.objects['V19 connected standing seam concourse roof']
for xa,xb,wa,wb in r['rear']['profiles']:
 x=(xa+xb)/2;w=(wa+wb)/2
 for obj,y in [(glass,w+1.3),(roof,(w+2.6+25)/2)]:
  hit=tree(obj).ray_cast(Vector((x,y,7)),Vector((0,0,-1)),3)[0]
  if hit is None:bad.append([obj.name,x,y])
check('Rear skylight and roof cover all bays including former gaps',bad,bays=len(r['rear']['profiles']))
bad=[]
for o in new:
 if o.type=='MESH':
  a=np.array([v.co[:] for v in o.data.vertices])
  if not np.isfinite(a).all():bad.append(o.name)
for im in bpy.data.images:
 if im.source=='FILE' and not im.packed_file and not os.path.isfile(bpy.path.abspath(im.filepath)):bad.append('missing image '+im.name)
check('Finite geometry and packed or resolving image dependencies',bad)
report={'revision':19,'passed':all(c['pass'] for c in checks),'checks':checks,'limits':'Geometric connectivity and preservation checks, not surveyed placement or current traffic-operation certification.'}
Path(args[1]).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
if not report['passed']:raise RuntimeError('V19 validation failed')
print('V19_VALIDATION_OK',len(checks),flush=True)
