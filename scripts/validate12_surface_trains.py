"""Reopen V12 and validate preserved source, instance placement, glazing and vehicle envelopes.
Usage: -- baseline_v11.json report.json
"""
import bpy,sys,os,json,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,os.path.dirname(__file__))
from mod12_surface_trains import fingerprint
import mod12_interiors as IN
args=sys.argv[sys.argv.index('--')+1:];sc=bpy.context.scene;R=json.loads(sc['V12_refinement']);out={'revision':12,'checks':{},'failures':[]}
def check(name,ok,**data):
    out['checks'][name]={'pass':bool(ok),**data}
    if not ok:out['failures'].append(name)
base=json.load(open(args[0],encoding='utf8'));now=fingerprint();allowed={i['name']:i for i in R['instances']};missing=[];changed=[]
for name,old in base.items():
    if name not in now:missing.append(name);continue
    new=now[name].copy()
    if name in allowed:new['instance_collection']=old['instance_collection']
    if new!=old:changed.append(name)
check('all_original_objects_retained',not missing and not changed,source_objects=len(base),missing=missing,changed=changed)
bad=[]
for i in R['instances']:
    e=bpy.data.objects.get(i['name'])
    if not e or e.instance_collection.name!=i['replacement'] or not np.allclose(e.matrix_basis,i['matrix'],atol=1e-7):bad.append(i['name'])
check('surface_instance_placement',not bad,instances=len(R['instances']),failures=bad)
bad=[]
for name,old in base.items():
    if 'instance_collection' in old and name not in allowed and now[name]['instance_collection']!=old['instance_collection']:bad.append(name)
check('other_instances_unchanged',not bad,changed=bad)
missing=[]
for im in list(bpy.data.images)+list(bpy.data.fonts):
    p=getattr(im,'filepath','')
    if im.users and p and p!='<builtin>' and not im.name.startswith('Bfont') and not im.packed_file and not os.path.isfile(bpy.path.abspath(p)):missing.append(im.name)
check('packed_assets',not missing,missing=missing)
new=[o for o in bpy.data.objects if o.type=='MESH' and o.get('V12_kind') and not o.name.startswith('V12 cutaway')]
bad=[]
for o in new:
    a=np.empty(len(o.data.vertices)*3);o.data.vertices.foreach_get('co',a)
    if not np.isfinite(a).all():bad.append(o.name)
check('finite_new_geometry',not bad,mesh_objects=len(new),failures=bad)
palettes={}
for fam in ('chuo','keihin','yamanote','tokaido'):
    m=bpy.data.materials.get('V12 | '+fam+'_back');palettes[fam]=list(m.diffuse_color[:3]) if m else None
check('distinct_family_palettes',all(palettes.values()) and len({tuple(x) for x in palettes.values()})==4,palettes=palettes)
bad=[];widths={}
for c in bpy.data.collections:
    if not c.get('V12_source') or 'N700' in c.name:continue
    for o in c.objects:
        if o.type!='MESH' or not o.get('V12_kind'):continue
        vs=[o.matrix_local@v.co for v in o.data.vertices]
        if not vs:continue
        w=max(abs(v.y) for v in vs);widths[o.name]=w
        limit=1.78 if 'E5' in c.name else 1.56
        if w>limit:bad.append({'object':o.name,'half_width':w,'limit':limit})
check('new_vehicle_widths',not bad,maximum_half_width=max(widths.values()),failures=bad)
TREES={}
def tree(o):
    if o.name not in TREES:TREES[o.name]=BVHTree.FromPolygons([o.matrix_local@v.co for v in o.data.vertices],[list(p.vertices) for p in o.data.polygons])
    return TREES[o.name]
# Only side-shell elements are used here: an interior seat is an expected hit after entry.
bad=[];rays=0
for c in bpy.data.collections:
    if not c.get('V12_source') or 'N700' in c.name:continue
    bodies=[o for o in c.objects if o.type=='MESH' and ('one-piece body |' in o.name or o.get('V12_kind')=='green_shell')]
    lining=[o for o in c.objects if o.type=='MESH' and o.get('V12_kind') in ('interior_lining','green_lining','e5_lining','exterior_detail')]
    for body in bodies:
        rects=IN.glazing_rects(body)
        for a,d,z,t,s,y in rects:
            if d-a<.4:continue
            p=Vector(((a+d)/2,s*2.1,(z+t)/2));direction=Vector((0,-s,0));rays+=1
            for o in [body]+lining:
                tr=tree(o);pos=p.copy();remain=abs(p.y)-1.30
                for _ in range(10):
                    hit,n,idx,dist=tr.ray_cast(pos,direction,remain)
                    if hit is None:break
                    mat=o.data.materials[o.data.polygons[idx].material_index].name.lower()
                    if not ('glass' in mat or 'glazing' in mat):
                        bad.append({'collection':c.name,'object':o.name,'material':mat,'point':list(hit)});break
                    remain-=dist+.002;pos=hit+direction*.002
                    if remain<=0:break
check('passenger_glazing_apertures',not bad,rays=rays,blocked=bad)
bad=[];cab_rays=0
for family,record in R.get('cab_fronts',{}).items():
    front=bpy.data.objects[record['front_object']];col=next(c for c in front.users_collection if c.get('V12_source'));xf=front['V12_front_x']
    for y in (-.80,0,.80):
        for z in (2.62,2.96):
            cab_rays+=1;glass_hit=False
            for o in col.all_objects:
                if o.type!='MESH':continue
                tr=tree(o);pos=Vector((xf+.20,y,z));direction=Vector((-1,0,0));remain=.60
                for _ in range(12):
                    hit,n,idx,dist=tr.ray_cast(pos,direction,remain)
                    if hit is None:break
                    mat=o.data.materials[o.data.polygons[idx].material_index].name.lower()
                    if 'glass' in mat or 'glazing' in mat:glass_hit=True
                    else:bad.append({'family':family,'object':o.name,'material':mat,'point':list(hit)});break
                    remain-=dist+.002;pos=hit+direction*.002
                    if remain<=0:break
            if not glass_hit:bad.append({'family':family,'missing_glazing_at':[y,z]})
check('new_cab_front_glazing',cab_rays==24 and not bad,rays=cab_rays,blocked=bad)
c=bpy.data.collections['V12 | E233-0 style Green car | procedural'];bad=[]
for o in c.all_objects:
    if o.type!='MESH':continue
    tr=tree(o)
    for z in (3.50,3.65,3.80):
        h=tr.ray_cast(Vector((4.4,0,z)),Vector((-1,0,0)),8.7)[0]
        if h:bad.append({'object':o.name,'point':list(h)})
check('green_upper_aisle_clear',not bad,blocked=bad)
bad=[]
for c in bpy.data.collections:
    if not c.get('V12_source') or 'Green' not in c.name:continue
    for o in c.all_objects:
        if o.type!='MESH':continue
        tr=tree(o)
        for z in (.70,.85,1.05,1.25):
            h=tr.ray_cast(Vector((3.8,0,z)),Vector((-1,0,0)),7.6)[0]
            if h:bad.append({'collection':c.name,'object':o.name,'point':list(h)})
        for x in (-3,-1,1,3):
            h=tr.ray_cast(Vector((x,0,.49)),Vector((0,0,1)),1.0)[0]
            if h:bad.append({'collection':c.name,'object':o.name,'point':list(h),'vertical':True})
check('green_lower_aisle_clear',not bad,blocked=bad)
green=[v for v in R['templates'].values() if v.get('decks')==2]
check('green_car_decks',len(green)==3,templates=green)
check('review_views',all(bpy.data.objects.get(n) for n in R['review_cameras']),count=len(R['review_cameras']))
out['pass']=not out['failures'];json.dump(out,open(args[1],'w',encoding='utf8'),ensure_ascii=False,indent=2)
print('V12_VALIDATION',out['pass'],out['failures'],flush=True)
if out['failures']:raise RuntimeError(str(out['failures']))
