"""Preservation, actual surface and access checks for the rebuilt plaza.
-- baseline_v17.json report.json
"""
import bpy,sys,os,json,math,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,os.path.dirname(__file__))
from v16lib import snapshot
from v18lib import bounds
args=sys.argv[sys.argv.index('--')+1:];sc=bpy.data.scenes['Tokyo Station'];bpy.context.window.scene=sc
r=json.loads(sc['V18_plaza']);base=json.load(open(args[0]));now=snapshot();checks=[]
lookup={x['original']:x['retained'] for x in r['retained']};reverse={v:k for k,v in lookup.items()}
def check(name,bad,**more):
 checks.append({'name':name,'pass':not bool(bad),'failures':bad,**more});print(name,'PASS' if not bad else 'FAIL',str(bad)[:1400],flush=True)
bad=[]
for name,rec in base.items():
 cur=now.get(lookup.get(name,name))
 if cur:
  cur=dict(cur)
  if cur.get('parent') in reverse:cur['parent']=reverse[cur['parent']]
  if name in lookup:cur['collections']=rec['collections'];cur['visibility']=rec['visibility']
 if cur!=rec:bad.append(name)
check('All V17 source objects retain geometry curves text transforms and materials',bad,objects=len(base))
bad=[name for name,rec in base.items() if name not in lookup and rec!=now.get(name)]
check('Unrelated station trains platforms tracks and underground objects remain unchanged',bad,objects=len(base)-len(lookup))
bad=[n for n in lookup.values() if now[n]['visibility']!=[True,True] or now[n]['collections']!=['V18_Replaced_hidden']]
check('Replaced originals are isolated and hidden',bad,objects=len(lookup))
hidden=set()
def walk(c,h=False):
 h=h or c.hide_render
 if h:hidden.update(o.name for o in c.objects)
 for cc in c.children:walk(cc,h)
walk(sc.collection)
active=[o for o in sc.objects if not o.hide_render and o.name not in hidden]
new=[o for o in active if o.get('V18_kind')]
trees={}
def ray(o,p,d=(0,0,-1),dist=20):
 if o.name not in trees:trees[o.name]=BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(f.vertices) for f in o.data.polygons])
 return trees[o.name].ray_cast(Vector(p),Vector(d),dist)[0]
lawns=[o for o in new if o.get('V18_kind')=='Lawns'];bad=[];areas=[]
for o in lawns:
 area=sum(f.area for f in o.data.polygons if f.normal.z>.99 and o.data.materials[f.material_index].name=='V18 | grass');areas.append(area)
 lo,hi=bounds(o)
 if abs(area-600)>.01 or abs((lo.y+hi.y)/2+89)>.01:bad.append([o.name,area,list(lo),list(hi)])
if len(lawns)!=2:bad.append(['lawn count',len(lawns)])
check('Both 600 square metre lawns align symmetrically with the central axis',bad,areas_m2=areas)
bad=[];samples=0;axis=bpy.data.objects['V18 white granite central axis aligned to imperial entrance']
substrate=bpy.data.objects.get('V18 continuous plaza substrate under replacement finishes')
for x in (-8,-4,0,4,8):
 for y in np.linspace(-121.7,-35.2,80):
  samples+=1;hit=ray(axis,(x,y,2))
  if hit is None and substrate:hit=ray(substrate,(x,y,2))
  if hit is None or not .240<=hit.z<=.252:bad.append([x,float(y),'missing axis surface'])
 # Keep the full walking axis clear of new solid furniture.
for o in new:
 if o.type!='MESH' or o.get('V18_kind') in ['Paving','Drainage','Road_Markings','Cooling_Paving']:continue
 lo,hi=bounds(o)
 if lo.x<10 and hi.x>-10 and lo.y<-35 and hi.y>-123 and hi.z>.5:
  v=np.array([o.matrix_world@v.co for v in o.data.vertices])
  for f in o.data.polygons:
   p=v[list(f.vertices)];lo=p.min(0);hi=p.max(0)
   if lo[0]<10 and hi[0]>-10 and lo[1]<-35 and hi[1]>-123 and hi[2]>.5:
    bad.append([o.name,'actual face intrudes into central corridor']);break
check('Central white walking axis is continuous and clear of new furniture',bad,samples=samples)
bad=[];samples=0
central=[o for o in new if o.name.startswith('V18 central zelkova ')]
if len(central)!=14:bad.append(['central tree count',len(central)])
for y in (-42,-54,-66,-78,-90,-102,-114):
 for s in (-1,1):
  if not any(abs(o.location.x-s*33.5)<.01 and abs(o.location.y-y)<.01 for o in central):bad.append([s,y,'missing row tree'])
for o in active:
 if not (o.name.startswith('V5 person plaza') or o.name.startswith('Visitor head')):continue
 if o.type=='EMPTY':x,y,z=o.location
 else:lo,hi=bounds(o);x,y,z=(lo+hi)/2
 if not -123<y<-34:continue
 if any(a['bounds'][0]-.1<x<a['bounds'][1]+.1 and a['bounds'][2]-.1<y<a['bounds'][3]+.1 for a in r['lawns']):bad.append([o.name,'pedestrian in lawn'])
 if any(abs(x-t['xy'][0])<3 and abs(y-t['xy'][1])<3 for t in r['trees'] if t['central']):bad.append([o.name,'pedestrian in tree seat'])
check('Paired seven-tree rows and pedestrian placement respect grass and seats',bad,trees=len(central))
bad=[];pool=bpy.data.objects['V18 two open asphalt taxi holding areas'];taxicount=0
for o in new:
 if not o.get('V18_taxi_pool'):continue
 taxicount+=1;lo,hi=bounds(o)
 for x in (lo.x+.06,hi.x-.06):
  for y in (lo.y+.06,hi.y-.06):
   hit=ray(pool,(x,y,3));samples+=1
   if hit is None or abs(hit.z-.318)>.005:bad.append([o.name,'vehicle outside taxi pool',x,y])
 if abs(lo.z-.318)>.025:bad.append([o.name,'tyres not at pavement',lo.z])
check('Waiting vehicles stand inside taxi holding areas with tyres at pavement',bad,vehicles=taxicount)
bad=[];samples=0
surfaces=[o for o in new if o.type=='MESH' and o.get('V18_kind') in ['Transport_Roads','Transport_Islands','Taxi_Access','Taxi_Pools','Transport_Kerbs']]
for a in r['taxi_access']:
 for dx in (-2.5,0,2.5):
  last=None
  for y in np.linspace(a['y0']+.02,a['y1']-.02,65):
   hits=[q for o in surfaces if (q:=ray(o,(a['x']+dx,float(y),.8),dist=1)) is not None];samples+=1
   if not hits:bad.append([a['label'],'missing taxi approach surface']);continue
   top=max(q.z for q in hits)
   if last is not None and abs(top-last)>.035:bad.append([a['label'],dx,float(y),'step or kerb in taxi approach',top-last])
   last=top
check('Taxi approaches climb continuously through real kerb gaps into the pools',bad,samples=samples)
bad=[];samples=0
# New mesh geometry must not cap either inherited ground-to-B1 stair opening.
for code,xs,y in [('M8',(-141,-138,-135,-132),-94),('M7',(-31,-28,-25,-22),-139)]:
 for x in xs:
  for dy in (-.8,0,.8):
   samples+=1
   for o in new:
    if o.type!='MESH':continue
    lo,hi=bounds(o)
    if lo.x<=x<=hi.x and lo.y<=y+dy<=hi.y and hi.z>=-.1:
     if ray(o,(x,y+dy,.8),dist=.9) is not None:bad.append([code,o.name,x,y+dy])
check('M7 and M8 stair openings remain unobstructed by new plaza geometry',bad,samples=samples)
bad=[]
for o in new:
 if o.type=='MESH' and not np.isfinite(np.array([v.co for v in o.data.vertices])).all():bad.append(o.name)
for im in bpy.data.images:
 if im.source=='FILE' and not im.packed_file and im.filepath and not os.path.isfile(bpy.path.abspath(im.filepath)):bad.append(im.name)
check('New geometry is finite and image dependencies resolve',bad)
out={'revision':18,'passed':all(c['pass'] for c in checks),'checks':checks,'limits':'Model geometry and source preservation checks; not certification of as-built dimensions or exact current traffic operation.'}
with open(args[1],'w',encoding='utf8') as f:json.dump(out,f,ensure_ascii=False,indent=2)
if not out['passed']:raise RuntimeError('V18 validation failed')
