"""Verify source preservation and actual building/roof continuity.
-- baseline_v16.json report.json
"""
import bpy,bmesh,sys,os,json,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,os.path.dirname(__file__))
from v16lib import snapshot
args=sys.argv[sys.argv.index('--')+1:];sc=bpy.data.scenes['Tokyo Station'];bpy.context.window.scene=sc
r=json.loads(sc['V17_connections']);base=json.load(open(args[0]));now=snapshot();checks=[]
lookup={v['original']:v['retained'] for v in r['retained']};reverse={v:k for k,v in lookup.items()}
def check(name,bad,**more):
 checks.append({'name':name,'pass':not bool(bad),'failures':bad,**more});print(name,'PASS' if not bad else 'FAIL',str(bad)[:1000],flush=True)
bad=[]
for name,rec in base.items():
 cur=now.get(lookup.get(name,name))
 if cur:
  cur=dict(cur)
  if cur.get('parent') in reverse:cur['parent']=reverse[cur['parent']]
  if name in lookup:cur['collections']=rec['collections'];cur['visibility']=rec['visibility']
 if cur!=rec:bad.append(name)
check('Every V16 source object retains its geometry curves text and transform',bad,objects=len(base))
bad=[]
for name,old in lookup.items():
 if now[old]['visibility']!=[True,True] or now[old]['collections']!=['V17_Replaced_hidden']:bad.append(old)
check('Replaced roof and stone-ornament originals are hidden and isolated',bad,objects=len(lookup))
bad=[name for name,rec in base.items() if name not in lookup and rec!=now.get(name)]
check('Unrelated objects retain their geometry materials visibility and collection links',bad,objects=len(base)-len(lookup))
roofs=[o for o in sc.objects if o.get('V17_kind')=='Roofs'];bad=[];topology=[]
for o in roofs:
 bm=bmesh.new();bm.from_mesh(o.data);bm.verts.ensure_lookup_table();edges=sum(not e.is_manifold for e in bm.edges)
 unseen=set(bm.verts);components=0
 while unseen:
  components+=1;stack=[unseen.pop()]
  while stack:
   v=stack.pop()
   for e in v.link_edges:
    w=e.other_vert(v)
    if w in unseen:unseen.remove(w);stack.append(w)
 topology.append({'name':o.name,'nonmanifold_edges':edges,'connected_components':components,'faces':len(bm.faces)})
 if edges or components!=1:bad.append(topology[-1])
 bm.free()
check('Each roof run is one connected closed native mesh after boolean union',bad,roofs=topology)
TREES={}
def tree(o):
 if o.name not in TREES:TREES[o.name]=BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(f.vertices) for f in o.data.polygons])
 return TREES[o.name]
def ray(o,p,d=(0,0,-1),distance=30):return tree(o).ray_cast(Vector(p),Vector(d),distance)[0]
bad=[];samples=0
for link in r['roof_links']:
 group=next(o for o in roofs if link['name'].startswith(o.name.replace(' continuous roof','')))
 a=np.array(link['from']);b=np.array(link['to'])
 # A turning connector is triangulated, not a bilinear patch. Its planar
 # triangles are the lower bound for the final union's actual roof surface.
 ref=BVHTree.FromPolygons([Vector(p) for p in np.concatenate((a,b))],[(i,i+1,i+5) for i in range(3)]+[(i,i+5,i+4) for i in range(3)])
 for t in np.linspace(.04,.96,13):
  p=a*(1-t)+b*t
  for edge,f in [(0,.35),(0,.75),(1,.5),(2,.25),(2,.65)]:
   q=p[edge]*(1-f)+p[edge+1]*f;hit=ray(group,(q[0],q[1],35));samples+=1
   expected=ref.ray_cast(Vector((q[0],q[1],35)),Vector((0,0,-1)),30)[0]
   if expected is None or hit is None or hit.z<expected.z-.015:bad.append([link['name'],float(t),edge,None if hit is None else float(hit.z),None if expected is None else float(expected.z)])
check('Roof surfaces have no gap or hip-end trough along all connection paths',bad,samples=samples,connections=len(r['roof_links']))
bad=[];samples=0
for link in r['dome_links']:
 tag=link['dome'];cx=link['cx'];s=link['side'];wall=bpy.data.objects[f'V17 {tag} {s:+d} connecting brick walls'];floor=bpy.data.objects[f'V17 {tag} {s:+d} connecting storey slabs']
 for dx in (12.7,13.2,13.7):
  for z in (2,8,14,16.5):
   for y,d in [(-10,(0,1,0)),(12,(0,-1,0))]:
    samples+=1
    if ray(wall,(cx+s*dx,y,z),d,6) is None:bad.append([tag,s,dx,z,y,'open facade'])
  for z in link['floor_z']:
   for y in (-4,0,4):
    samples+=1;hit=ray(floor,(cx+s*dx,y,z+.25),distance=.4)
    if hit is None or abs(hit.z-z-.07)>.003:bad.append([tag,s,dx,y,z,'missing floor surface'])
 # The neck must leave the rotunda interior clear rather than spanning it.
 for z in link['floor_z']:
  samples+=1
  if ray(floor,(cx+s*10,0,z+.25),distance=.4) is not None:bad.append([tag,s,z,'neck enters rotunda'])
check('Four dome necks contain continuous facades and slabs while keeping the rotunda clear',bad,samples=samples)
bad=[];samples=0
for label,cx in [('North',-18),('South',18)]:
 o=bpy.data.objects['V17 '+label+' attic side and back returns']
 for dx,d in [(-4,(1,0,0)),(4,(-1,0,0))]:
  for y in (-6,-2,2,5):
   samples+=1
   if ray(o,(cx+dx,y,19),d,2) is None:bad.append([label,dx,y])
 samples+=1
 if ray(o,(cx,8,19),(0,-1,0),3) is None:bad.append([label,'open back'])
check('Both central attic turrets have side and rear enclosure below their flat caps',bad,samples=samples)
bad=[]
for o in sc.objects:
 if o.type=='MESH' and o.get('V17_kind'):
  a=np.array([v.co for v in o.data.vertices])
  if not np.isfinite(a).all():bad.append(o.name)
for im in bpy.data.images:
 if im.source=='FILE' and not im.packed_file and im.filepath and not os.path.isfile(bpy.path.abspath(im.filepath)):bad.append(im.name)
check('New mesh coordinates are finite and image dependencies resolve',bad)
out={'revision':17,'passed':all(c['pass'] for c in checks),'checks':checks,'limits':'These checks establish model continuity, not measured as-built dimensions.'}
json.dump(out,open(args[1],'w',encoding='utf8'),ensure_ascii=False,indent=2)
if not out['passed']:raise RuntimeError('V17 validation failed')
