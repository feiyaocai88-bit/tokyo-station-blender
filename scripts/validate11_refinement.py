"""Validate retained source meshes and geometric clearances. Run on the reopened V11 file.
Usage: -- V10_baseline.json report.json
The baseline is produced before any edits by mod11_refinement.py.
"""
import bpy,sys,os,json,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,os.path.dirname(__file__))
import v11lib as H
import mod11_marunouchi as G
from mod11_refinement import fingerprint
args=sys.argv[sys.argv.index('--')+1:];sc=bpy.context.scene
bpy.context.view_layer.update()
R=json.loads(sc['V11_refinement']);out={'revision':11,'checks':{},'failures':[]}
def check(k,ok,**data):
    out['checks'][k]={'pass':bool(ok),**data}
    if not ok:out['failures'].append(k)
baseline=json.load(open(args[0],encoding='utf8'));now=fingerprint()
mapping={r['original']:r['retained'] for r in R['retired']}
missing=[];changed=[]
for name,data in baseline.items():
    retained=mapping.get(name,name)
    if retained not in now:missing.append(name)
    elif now[retained]!=data:changed.append(name)
check('source_preservation',not missing and not changed,source_objects=len(baseline),missing=missing,changed=changed,retained_replaced_objects=len(mapping))
missing=[]
for im in list(bpy.data.images)+list(bpy.data.fonts):
    if not im.users or im.name.startswith('Bfont'):continue
    p=getattr(im,'filepath','')
    if p and p!='<builtin>' and not im.packed_file and not os.path.isfile(bpy.path.abspath(p)):missing.append(im.name)
check('assets',not missing,missing=missing)
new=[o for o in sc.objects if o.type=='MESH' and o.get('V11_kind') and not o.hide_render]
check('finite_vertices',all(np.isfinite(H.world(o)).all() for o in new),mesh_objects=len(new),vertices=sum(len(o.data.vertices) for o in new))
check('platform_groups',len(R['platform_recesses'])==10 and len(R['columns'])==10 and all(v['count']>0 for v in R['columns'].values()),columns=R['columns'],recesses=R['platform_recesses'])
deckbad=[]
for isl,r in R['platform_recesses'].items():
    o=bpy.data.objects[f'V3 Platform {isl} raised deck'];p=H.world(o)
    if abs(float(p[:,2].max())-r['deck_top'])>.001 or abs(float(np.ptp(p[:,2]))-.23)>.001:deckbad.append(isl)
check('deck_levels_and_open_slab',not deckbad,failures=deckbad)
def samples(o):
    v=H.world(o);o.data.calc_loop_triangles();t=np.array([t.vertices[:] for t in o.data.loop_triangles],int)
    return np.concatenate([v,v[t].mean(1),(v[t[:,0]]+v[t[:,1]])/2,(v[t[:,1]]+v[t[:,2]])/2,(v[t[:,2]]+v[t[:,0]])/2])
bad=[];minclear=999
for o in new:
    if o.get('V11_kind') not in ('platform_column','heritage_column','roof_skin','roof_detail','service_enclosure','service_detail'):continue
    p=samples(o)
    for tr,ys in H.TRACKS.items():
        rail=15.47 if tr in ('01','02') else 7.07 if int(tr)>=14 else 5.17
        q=p[(p[:,2]>rail+.08)&(p[:,2]<rail+4.95)]
        if not len(q):continue
        slope=np.interp(q[:,0],H.GX,np.gradient(ys,H.GX));dist=abs(q[:,1]-np.interp(q[:,0],H.GX,ys))/np.sqrt(1+slope*slope)
        minclear=min(minclear,float(dist.min()))
        if dist.min()<1.90:bad.append({'object':o.name,'track':tr,'clearance':float(dist.min()),'point':q[dist.argmin()].tolist()})
check('surface_track_clearance',not bad,minimum_m=minclear,intrusions=bad)
def tree(o,F=None):
    v=H.world(o)
    if F is not None:
        m=np.array(F);v=v@m[:3,:3].T+m[:3,3]
    o.data.calc_loop_triangles();tris=[tuple(t.vertices) for t in o.data.loop_triangles]
    return BVHTree.FromPolygons(v.tolist(),tris,all_triangles=True)
roof=bpy.data.objects['V11 05-06 curved green roof with low side wings'];rt=tree(roof);bad=[]
for o in sc.objects:
    if o.type=='MESH' and o.name.startswith('V6 OCS |') and not o.hide_render:
        pairs=rt.overlap(tree(o))
        if pairs:bad.append({'object':o.name,'triangles':len(pairs)})
check('curved_roof_ocs',not bad,intersections=bad)
collisions=[]
facilities=[(o,tree(o)) for o in sc.objects if o.type=='MESH' and o.get('V10_kind')=='platform_facility' and not o.hide_render]
for o in new:
    if o.get('V11_kind')!='platform_column':continue
    t=tree(o)
    for f,ft in facilities:
        if f.get('island')!=o.get('island'):continue
        pairs=t.overlap(ft)
        if pairs:collisions.append({'column':o.name,'facility':f.name,'pairs':len(pairs)})
check('columns_vs_platform_facilities',not collisions,collisions=collisions)
FI=G.F.inverted()
metro_static=[o for o in new if any(c.name.startswith('V11_Metro_') for c in o.users_collection) and o.get('V11_kind') not in ('metro_train','metro_train_markings','metro_track')]
trees=[(o.name,tree(o,FI)) for o in metro_static]
cross=[]
for o in sc.objects:
    if o.type!='MESH' or not o.name.startswith('V9 Sobu |') or o.hide_render:continue
    lo,hi=H.bounds(o)
    if hi[2]<-12.4:continue
    ot=tree(o,FI)
    for name,nt in trees:
        pairs=ot.overlap(nt)
        if pairs:cross.append({'old':o.name,'new':name,'triangle_pairs':len(pairs)})
check('metro_vs_sobu_structures',not cross,intersections=cross)
hits=[]
for y in (-G.TRACK,G.TRACK):
    for dy in np.linspace(-1.48,1.48,7):
        for z in np.arange(G.RAIL+.40,G.RAIL+3.951,.25):
            for name,t in trees:
                loc,n,idx,dist=t.ray_cast(Vector((-60,y+dy,z)),Vector((1,0,0)),120)
                if loc is not None:hits.append({'object':name,'point':list(loc)});break
check('metro_vehicle_envelope',not hits,hits=hits[:30],samples=2*7*len(np.arange(G.RAIL+.40,G.RAIL+3.951,.25)))
ct=[(n,t) for n,t in trees if 'ceiling' in n.lower() or 'concourse' in n.lower()]
head=[];minh=99
for x,s in G.STAIRS:
    for k in range(26):
        u=(k+.5)*.30;z=G.DECK+(k+1)*(G.B1-G.DECK)/26
        for dy in (-1.3,-.3):
            start=Vector((x+s*u,s*dy,z+.03))
            for name,t in ct:
                loc,n,idx,dist=t.ray_cast(start,Vector((0,0,1)),2.1)
                if loc is not None:head.append({'object':name,'step':k,'bank_x':x,'distance':dist,'point':list(loc)});minh=min(minh,dist)
check('metro_stair_headroom',not head,required_m=2.10,obstructions=head[:40])
# Verify the actual void through the display meshes: a temporary renderer hide is
# insufficient, because the editable station must work in the normal main scene.
voidhits=[]
for name in ('Display base','Studio floor'):
    t=tree(bpy.data.objects[name].evaluated_get(bpy.context.evaluated_depsgraph_get()),FI)
    for x in np.linspace(-60,60,13):
        for y in (-5.5,-3,0,3,5.5):
            loc,n,idx,dist=t.ray_cast(Vector((x,y,G.B1+.1)),Vector((0,0,1)),3.15)
            if loc is not None:voidhits.append({'object':name,'point':list(loc)})
check('underground_display_void',not voidhits,evaluated_mesh=True,ray_samples=130,hits=voidhits)
check('metro_content',R['counts'].get('marunouchi_2000_cars')==6 and R['counts'].get('metro_platform_door_pairs')==36 and R['counts'].get('metro_stair_escalator_banks')==3,counts=R['counts'])
check('separate_cutaway','V11 Marunouchi cutaway' in bpy.data.scenes and bpy.data.scenes['V11 Marunouchi cutaway'].camera is not None)
out['scope']='Geometry samples and source preservation; photographic similarity also requires visual review. This is not engineering clearance certification.'
out['pass']=not out['failures'];json.dump(out,open(args[1],'w',encoding='utf8'),ensure_ascii=False,indent=2)
print('V11_VALIDATION',json.dumps({'pass':out['pass'],'failures':out['failures'],'counts':R['counts']}),flush=True)
if not out['pass']:raise AssertionError('V11 validation failed; inspect '+args[1])
