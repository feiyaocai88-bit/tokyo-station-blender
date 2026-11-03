"""Source preservation and independent geometric checks. -- baseline.json report.json"""
import bpy,sys,os,json,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,os.path.dirname(__file__))
import v16lib as H
args=sys.argv[sys.argv.index('--')+1:];sc=bpy.data.scenes['Tokyo Station'];bpy.context.window.scene=sc
r=json.loads(sc['V16_refinement']);base=json.load(open(args[0]));now=H.snapshot();checks=[]
lookup={v['original']:v['retained'] for v in r['retained']};reverse={v:k for k,v in lookup.items()}
def check(name,bad,**more):
    checks.append({'name':name,'pass':not bool(bad),'failures':bad,**more})
    print(name,'PASS' if not bad else 'FAIL',str(bad)[:1200],flush=True)
bad=[]
for name,rec in base.items():
    cur=now.get(lookup.get(name,name))
    if cur:
        cur=dict(cur)
        if cur.get('parent') in reverse:cur['parent']=reverse[cur['parent']]
        if name in lookup:
            cur['visibility']=rec['visibility'];cur['collections']=rec['collections']
    if cur!=rec:bad.append(name)
check('Every V15 source mesh curve text and transform is retained unchanged',bad,objects=len(base))
bad=[]
for name,old in lookup.items():
    rec=now[old]
    if rec['visibility']!=[True,True] or rec['collections']!=['V16_Replaced_hidden']:bad.append(old)
    if name.startswith(('V12','V13','V14','V15')):bad.append(name+' outside architectural edit scope')
check('Replaced originals are isolated and hidden',bad,retained=len(lookup))
bad=[];unchanged=0
for name,rec in base.items():
    if name in lookup:continue
    if rec!=now.get(name):bad.append(name)
    unchanged+=1
check('All other source objects retain geometry materials visibility and collection links',bad,objects=unchanged)
bad=[];verts=faces=0
for o in sc.objects:
    if not o.get('V16_kind') or o.type!='MESH':continue
    v=H.world(o);verts+=len(v);faces+=len(o.data.polygons)
    if not np.isfinite(v).all() or not len(o.data.polygons):bad.append(o.name)
    if v[:,2].min()<-.01 or v[:,2].max()>47:bad.append(o.name+' outside facade/roof height envelope')
check('New native architectural meshes are finite and remain above ground',bad,vertices=verts,faces=faces)
trees={}
def ray(o,p,d=(0,1,0),distance=20):
    if o.name not in trees:trees[o.name]=BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(f.vertices) for f in o.data.polygons])
    return trees[o.name].ray_cast(Vector(p),Vector(d),distance)[0]
body=bpy.data.objects['V16 Central deep arch masonry and open roundel'];bad=[]
for x,z in [(0,23.25),(.25,23.25),(-.25,23.25),(0,23.5),(0,23.0),(0,16),(0,19),(1.5,16)]:
    if ray(body,(x,-10,z)) is not None:bad.append([x,z,'opening blocked'])
for x,z in [(.98,23.25),(-.98,23.25),(0,24.4),(0,22.1),(4.35,18)]:
    if ray(body,(x,-10,z)) is None:bad.append([x,z,'surround masonry missing'])
check('Central niche and circular window are actual openings in the new masonry',bad)
bad=[];moved=0
for name,old in lookup.items():
    if not name.startswith('V3 Central recessed'):continue
    a=bpy.data.objects[old];b=bpy.data.objects[name]
    delta=np.array(b.matrix_basis.translation)-np.array(a.matrix_basis.translation)
    if not np.allclose(delta,[0,1.15,0],atol=1e-5):bad.append(name)
    moved+=1
check('Central inset wall glazing and frame parts move together into the niche',bad,parts=moved)
deps=bpy.context.evaluated_depsgraph_get();bad=[];hits=[]
for cx in (-104.,107.):
    for dx,dz in [(.4,.4),(-.4,.4),(.4,-.4)]:
        result=sc.ray_cast(deps,Vector((cx+dx,-20,20.1+dz)),Vector((0,1,0)),distance=15)
        name=result[4].name if result[0] else None;hits.append(name)
        if not name or 'clock' not in name.lower() or 'gable' in name.lower() or 'archivolt' in name.lower():bad.append([cx,dx,dz,name])
check('Both original clock faces remain visible in front of the new gables',bad,ray_hits=hits)
bad=[];rays=0;occluded=0
for o in sc.objects:
    if o.hide_render or o.type!='MESH' or 'front bay' not in o.name or 'floor2 recessed glazing' not in o.name:continue
    lo,hi=H.bounds(o);cx=float((lo[0]+hi[0])/2)
    for dx,dz in [(0,0),(0,.060),(0,-.060)]:
        hit=sc.ray_cast(deps,Vector((cx+dx,lo[1]-4,16.645+dz)),Vector((0,1,0)),distance=5);rays+=1
        hitname=hit[4].name if hit[0] else ''
        if hitname!='V16 Third floor frieze medallions and window scroll brackets':
            if 'end octagonal corner tower' in hitname or 'outer projecting gable' in hitname:
                # A grid bay hidden by existing projecting masonry should carry
                # no new relief. Verify the absence of a buried medallion.
                q=bpy.data.objects['V16 Third floor frieze medallions and window scroll brackets']
                if ray(q,(cx+dx,lo[1]-4,16.645+dz),distance=5) is not None:bad.append([o.name,'relief buried behind inherited masonry'])
                occluded+=1
            else:bad.append([o.name,dz,hitname or None])
check('Frieze medallions remain visible and concealed inherited bays receive no relief',bad,rays=rays,visible_relief_samples=rays-occluded,concealed_bay_samples=occluded)
bad=[]
for side in ['North','South']:
    o=bpy.data.objects['V16 '+side+' central turret flat cornice and brackets']
    # Downward rays strike one level across the cap, rather than a hip roof.
    cx=-18 if side=='North' else 18;heights=[]
    for dx in [-2,0,2]:
        hit=ray(o,(cx+dx,-1,24),(0,0,-1),5)
        if hit is None:bad.append(side+' missing roof')
        else:heights.append(float(hit.z))
    if heights and max(heights)-min(heights)>.002:bad.append([side,heights])
for n in ['Central flanking finial','Central flanking finial.001']:
    if n in bpy.data.objects:bad.append(n+' old finial remains active')
check('Central turret caps have flat continuous upper surfaces and no floating old finials',bad)
bad=[im.name for im in bpy.data.images if im.source=='FILE' and not im.packed_file and im.filepath and not os.path.isfile(bpy.path.abspath(im.filepath))]
check('Image dependencies are packed or resolve',bad)
out={'revision':16,'passed':all(c['pass'] for c in checks),'checks':checks,'limits':'Geometry checks establish consistency and preservation, not survey accuracy.'}
json.dump(out,open(args[1],'w',encoding='utf8'),ensure_ascii=False,indent=2)
if not out['passed']:raise RuntimeError('V16 validation failed; inspect report')
