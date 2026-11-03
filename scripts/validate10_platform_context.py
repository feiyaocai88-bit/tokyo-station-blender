"""V10 geometry checks, including triangle samples, not only object origins.
Usage: blender -b scene.blend --python-exit-code 1 -P this.py -- report.json
"""
import bpy, sys, os, json, math
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sc=bpy.context.scene
HERE=os.path.dirname(os.path.abspath(__file__))
D=json.load(open(os.path.join(HERE,'targets.json')))
GX=np.array(D['X']); tracks={k:np.array(v) for k,v in D['target'].items()}
R=json.loads(sc['V10_platform_context'])
out={'revision':10,'counts':{},'track_envelope':{},'stair_clearance':{},'retired':{},'packed_assets':{},'plinth':{}}
new=[o for o in sc.objects if o.get('V10_kind') and not o.hide_render]


def W(o):
    p=np.empty(len(o.data.vertices)*3)
    o.data.vertices.foreach_get('co',p); mw=np.array(o.matrix_world)
    return p.reshape(-1,3)@mw[:3,:3].T+mw[:3,3]


def samples(o):
    v=W(o)
    o.data.calc_loop_triangles()
    ts=np.array([t.vertices[:] for t in o.data.loop_triangles],dtype=int)
    if not len(ts): return v
    t=v[ts]
    return np.concatenate([v,t.mean(1),(t[:,0]+t[:,1])/2,(t[:,1]+t[:,2])/2,(t[:,2]+t[:,0])/2])


meshes=[o for o in new if o.type=='MESH']
bad=[]; minimum=999
bbad=[]
keep=json.loads(sc.get('V6_platform_keepouts','[]'))
stairbad=[]
roof_by_island={}
for o in meshes:
    p=samples(o)
    if not np.isfinite(p).all(): raise AssertionError('Non-finite mesh '+o.name)
    if p[:,0].min()<-215.01 or p[:,0].max()>255.01 or p[:,1].min()<-151.01 or p[:,1].max()>225.44:
        bbad.append(o.name)
    for tr,ys in tracks.items():
        rail=15.47 if tr in ('01','02') else (7.07 if int(tr)>=14 else 5.17)
        band=(p[:,2]>rail+.08)&(p[:,2]<rail+4.95)
        q=p[band]
        if not len(q): continue
        slope=np.interp(q[:,0],GX,np.gradient(ys,GX))
        dist=np.abs(q[:,1]-np.interp(q[:,0],GX,ys))/np.sqrt(1+slope*slope)
        minimum=min(minimum,float(dist.min()))
        ix=np.flatnonzero(dist<1.90)
        if len(ix): bad.append({'object':o.name,'track':tr,'minimum_m':round(float(dist.min()),3),'point':q[ix[0]].tolist()})
    if o.get('V10_kind') in ('platform_facility','service_building'):
        for k in keep:
            if k['kind']!='stairwell': continue
            c=np.array(k['c']); u=np.array(k['u']); v=np.array([-u[1],u[0]])
            d=p[:,:2]-c
            inside=(d@u>-.3)&(d@u<7.62)&(np.abs(d@v)<1.97)&(p[:,2]>k['z0'])&(p[:,2]<k['z1'])
            if inside.any(): stairbad.append({'object':o.name,'island':k['island'],'position':k['pos']})
    if o.get('V10_kind')=='roof_skin': roof_by_island[o['island']]=o.name
out['track_envelope']={'minimum_sampled_clearance_m':round(minimum,3),'violations':bad,'pass':not bad}
out['stair_clearance']={'intrusions':stairbad,'pass':not stairbad}
out['plinth']={'outside':bbad,'pass':not bbad}
out['counts']={'roof_islands':len(roof_by_island),'roof_buildings':len(R['roof_buildings']),
               'service_buildings':len(R['service_buildings']),'platform_facilities':len(R['facilities']),
               'acoustic_panels':sum(b['panels'] for b in R['barriers']),
               'new_meshes':len(meshes),'new_mesh_vertices':sum(len(o.data.vertices) for o in meshes)}
ret=[bpy.data.objects.get(n) for n in R['retired']]
out['retired']={'count':len(ret),'pass':all(o and o.hide_render and o.hide_viewport for o in ret)}
missing=[]
for im in bpy.data.images:
    if im.source=='FILE' and im.users and not im.packed_file and not os.path.isfile(bpy.path.abspath(im.filepath)):
        missing.append(im.name)
for f in bpy.data.fonts:
    if not f.name.startswith('Bfont') and f.filepath!='<builtin>' and f.users and not f.packed_file and not os.path.isfile(bpy.path.abspath(f.filepath)):
        missing.append(f.name)
out['packed_assets']={'missing':missing,'pass':not missing}
out['roofs_complete']={'islands':sorted(roof_by_island),'pass':set(roof_by_island)==set(D['islands'])}
def surface_tree(o):
    pts=W(o);o.data.calc_loop_triangles()
    tris=[tuple(t.vertices) for t in o.data.loop_triangles]
    return pts,tris,BVHTree.FromPolygons(pts.tolist(),tris,all_triangles=True)

ocs=[(o,*surface_tree(o)) for o in sc.objects if o.type=='MESH' and o.name.startswith('V6 OCS |')]
intersections=[]
for o in meshes:
    if o.get('V10_kind') not in ('roof_skin','roof_house','roof_pv','service_building','ventilation_tower','platform_facility'):continue
    pts,tris,bv=surface_tree(o)
    for so,sp,st,sbv in ocs:
        pairs=bv.overlap(sbv)
        if pairs:
            a,b=pairs[0]
            intersections.append({'new':o.name,'ocs':so.name,'triangle_pairs':len(pairs),'point':pts[list(tris[a])].mean(0).tolist()})
out['overhead_line_intersections']={'intersections':intersections,'pass':not intersections}
out['pass']=all(v['pass'] for v in out.values() if isinstance(v,dict) and 'pass' in v)
dest=sys.argv[sys.argv.index('--')+1]
with open(dest,'w',encoding='utf8') as f: json.dump(out,f,indent=2,ensure_ascii=False)
print(json.dumps(out,ensure_ascii=False),flush=True)
if not out['pass']: raise AssertionError('V10 validation failed; see '+dest)
