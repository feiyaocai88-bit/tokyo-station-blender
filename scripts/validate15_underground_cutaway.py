"""Check source preservation, actual slab surfaces, side openings and retained interiors.
Run: blender -b V15.blend -P validate15_underground_cutaway.py -- baseline.json report.json
"""
import bpy,sys,os,json,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,os.path.dirname(__file__))
from mod12_surface_trains import fingerprint
import v9geo as G
from mod11_marunouchi import F as MF

args=sys.argv[sys.argv.index('--')+1:];sc=bpy.data.scenes['Tokyo Station'];r=json.loads(sc['V15_refinement'])
base=json.load(open(args[0]));now=fingerprint();checks=[];lookup={v['original']:v['retained'] for v in r['retained']}

def check(name,bad,**more):
    checks.append({'name':name,'pass':not bool(bad),'failures':bad,**more});print(name,'PASS' if not bad else 'FAIL',str(bad)[:600],flush=True)

bad=[];reverse={v:k for k,v in lookup.items()}
for name,rec in base.items():
    cur=now.get(lookup.get(name,name))
    if cur:
        cur=dict(cur)
        if cur.get('parent') in reverse:cur['parent']=reverse[cur['parent']]
    if cur!=rec:bad.append(name)
check('Every V14 source object retains its original geometry transform and materials',bad,count=len(base))

TREES={}
def object_matrix(o):
    # Hidden originals may not have an evaluated matrix_world after reopening.
    return object_matrix(o.parent)@o.matrix_parent_inverse@o.matrix_basis if o.parent else o.matrix_basis

def ray(o,frame,p,d=(0,0,-1),distance=.25):
    mat=object_matrix(o);inv=mat.inverted();p=inv@(frame@Vector(p));d=inv.to_3x3()@(frame.to_3x3()@Vector(d));d.normalize()
    if o.name not in TREES:TREES[o.name]=BVHTree.FromPolygons([v.co for v in o.data.vertices],[tuple(f.vertices) for f in o.data.polygons])
    loc,n,idx,dist=TREES[o.name].ray_cast(p,d,distance)
    return tuple(mat@loc) if loc is not None else None

# Compare the actual upper surfaces in both meshes. Holes are expected to remain
# holes. Sampling uses storey heights and a plan grid, not the edit predicates.
name='V9 Sobu | box structure (slabs, walls, end walls, tunnel stubs, ventilation shaft)'
o=bpy.data.objects[lookup[name]];q=bpy.data.objects[name];bad=[];samples=0;floor_hits=0;holes=0
for z,xa,xb in [(-28.6,-171,171),(-20.9,-171,171),(-16.5,-59,149),(-12.4,-59,149),(-8.2,-59,149),(-3.6,-59,149)]:
    for x in np.linspace(xa,xb,23):
        for y in [-17.8,-13,-9,-5,0,5,9,13,17.8]:
            a=ray(o,G.frame_matrix(),(x,y,z+.10));b=ray(q,G.frame_matrix(),(x,y,z+.10));samples+=1
            floor_hits+=bool(a);holes+=not bool(a)
            if bool(a)!=bool(b) or (a and np.linalg.norm(np.array(a)-b)>.0001):bad.append([z,float(x),y,a,b])
check('JR floor and roof surfaces and existing openings survive the wall removal',bad,samples=samples,surfaces=floor_hits,openings=holes)

bad=[];samples=0
shells=[bpy.data.objects[n] for n in [name,'V9 Sobu | B5 ceilings, bulkheads, track walls, soffit beams','V9 Sobu | B4 concourse (ceiling, partitions, doors)','V9 Sobu | B1 concourse (ceiling, walls, ticket gates, ventilation-shaft cladding)']]
for z,xx in [(-25,np.linspace(-165,165,15)),(-19.5,np.linspace(-125,125,13)),(-15,np.linspace(-50,140,11)),(-11,np.linspace(-50,140,11)),(-6.8,np.linspace(-50,140,11))]:
    for x in xx:
        for side in (-1,1):
            samples+=1
            for ob in shells:
                if ray(ob,G.frame_matrix(),(x,side*22,z),(0,-side,0),9):bad.append([ob.name,float(x),side,z])
for end,direction in [(-172,1),(172,-1)]:
    for y in [-11,0,11]:
        samples+=1
        if ray(q,G.frame_matrix(),(end-direction*3,y,-25),(direction,0,0),6):bad.append(['JR end wall',end,y])
for end,direction in [(-60,1),(150,-1)]:
    for z in [-15,-11,-6.8]:
        samples+=1
        if ray(q,G.frame_matrix(),(end-direction*3,0,z),(direction,0,0),5):bad.append(['JR upper end',end,z])
mq=bpy.data.objects['V11 M17 B1 concourse roof and side walls']
for x in np.linspace(-62,62,19):
    for side in (-1,1):
        samples+=1
        if ray(mq,MF,(x,side*10,-4),(0,-side,0),5):bad.append(['M17 B1 side',float(x),side])
check('Both sides and end enclosures are geometrically open through the occupied levels',bad,rays=samples)

bad=[];samples=0
for name in ['V11 M17 B1 concourse roof and side walls','V13 M7 B1 passage walls and roof','V13 M8 B1 passage walls and roof']:
    ob=bpy.data.objects[name];v=np.array([ob.matrix_world@p.co for p in ob.data.vertices])
    if v[:,2].min()<-2.551:bad.append([name,'vertical wall geometry remains'])
for name in ['V9 Sobu | box west wall (hide for the cutaway view)','V11 M17 track walls with red band and station names','V13 M7 tiled stairwell retaining walls','V13 M8 tiled stairwell retaining walls']:
    if bpy.data.objects.get(name):bad.append([name,'old wall still has its active name'])
    old=bpy.data.objects[lookup[name]]
    if not old.hide_render or not old.hide_viewport:bad.append([name,'not hidden in both modes'])
for rec in r['retained']:
    old=bpy.data.objects[rec['retained']]
    if [c.name for c in old.users_collection]!=['V15_Replaced_hidden']:bad.append([old.name,'unexpected active link'])
check('Wall originals are isolated and Metro passage meshes contain only their roofs',bad)

bad=[];preserved=0
detail_collections=['V9_Sobu_Trains','V11_Metro_Trains','V9_Sobu_People','V13_Metro_Access_Floor','V13_Metro_Entrances','V11_Metro_Track','V11_Metro_Platform','V11_Metro_Columns','V11_Metro_Stairs','V11_Metro_Platform_Doors']
detail_objects={o for n in detail_collections for o in bpy.data.collections[n].objects}
for o in detail_objects:
    if o.name not in base or o.name in lookup:continue
    preserved+=1
    if o.hide_render or o.hide_viewport or o.name not in sc.objects:bad.append(o.name)
machine=bpy.data.objects['V9 Sobu | B2-B3 machine rooms (partitions, switchgear, tanks, fans)']
for p in machine.data.polygons:
    if machine.data.materials[p.material_index].name=='V9 | cast-in-place concrete (box structure)':bad.append('machine room partition remains');break
check('Underground trains platforms stairs entrances and equipment remain available',bad,active_unchanged_objects=preserved)

bad=[im.name for im in bpy.data.images if im.source=='FILE' and not im.packed_file and im.filepath and not os.path.isfile(bpy.path.abspath(im.filepath))]
check('Image assets are packed or resolve',bad)
out={'revision':15,'passed':all(c['pass'] for c in checks),'checks':checks}
json.dump(out,open(args[1],'w',encoding='utf8'),ensure_ascii=False,indent=2)
if not out['passed']:raise RuntimeError('V15 validation failed; inspect report')
