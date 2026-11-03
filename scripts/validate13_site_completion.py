"""Geometric regression and access/clearance checks for V13; -- baseline report."""
import bpy,sys,os,json,math,numpy as np
from mathutils import Vector
sys.path.insert(0,os.path.dirname(__file__))
import v13lib as H
from mod12_surface_trains import fingerprint
args=sys.argv[sys.argv.index('--')+1:]
sc=bpy.context.scene;R=json.loads(sc['V13_refinement']);checks=[]
def check(name,bad,**data):
    checks.append({'name':name,'pass':not bool(bad),'failures':bad,**data});print(name,'PASS' if not bad else 'FAIL',str(bad)[:800],flush=True)
baseline=json.load(open(args[0],encoding='utf8'));now=fingerprint();lookup={r['original']:r['retained'] for r in R['retained']};reverse={v:k for k,v in lookup.items()};bad=[]
for name,record in baseline.items():
    nn=lookup.get(name,name);v=now.get(nn)
    if v is None:bad.append([name,'missing']);continue
    v=dict(v)
    if v.get('parent') in reverse:v['parent']=reverse[v['parent']]
    if v!=record:bad.append([name,'changed source geometry or transform'])
check('all V12 source geometry and transforms retained',bad,source_objects=len(baseline))
bad=[]
for row in R['barriers']:
    o=bpy.data.objects[row['object']];lo,hi=H.bounds(o);dl,dh=H.bounds(bpy.data.objects['V3 Track '+row['track']+' curved viaduct'])
    if lo[0]<dl[0]-.05 or hi[0]>dh[0]+.05:bad.append([o.name,'longitudinal overrun',float(lo[0]),float(hi[0])])
    p=H.world(o);dist=np.abs(p[:,1]-H.ty(row['track'],p[:,0]));z=p[:,2]
    if dist[z>row['deck_top']+.50].min()<1.68:bad.append([o.name,'vehicle envelope',float(dist.min())])
check('barriers stay within viaduct length and outside train envelope',bad,barriers=R['barriers'])
bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
instances={}
for ins in dg.object_instances:
    if ins.is_instance and ins.parent and 'PC sleepers + fastenings' in ins.parent.name and ins.object.name.startswith('V13 '):instances[ins.parent.name]=instances.get(ins.parent.name,0)+1
bad=[]
for row in R['tracks']:
    name='V5 track | Track '+row['track']+' PC sleepers + fastenings'
    if instances.get(name,0)<300:bad.append([name,'missing evaluated sleepers',instances.get(name,0)])
    if abs(row['old_crib_top']-row['new_crib_top']-.06)>1e-5:bad.append([name,'crib depth'])
check('twenty tracks retain visible evaluated sleeper instances',bad,instances=instances,total=sum(instances.values()))

def ray(p,d,dist):
    hit,loc,n,idx,o,m=sc.ray_cast(dg,Vector(p),Vector(d),distance=dist)
    return (o.name,list(loc)) if hit else (None,None)

bad=[];sample_count=0
for e in R['entrances']:
    for x,y,z in e['stair_samples']:
        for dy in (-1.1,0,1.1):
            sample_count+=1;name,p=ray((x,y+dy,z+.08),(0,0,-1),.30)
            floor_at_last_tread=bool(name and p and 'continuous B1 passage floor' in name and abs(p[2]-z)<.01)
            if not name or ('treads mid landing' not in name and not floor_at_last_tread):bad.append([e['exit'],'tread not accessible',x,name,p])
            name,p=ray((x,y+dy,z+.10),(0,0,1),2.0)
            if name:bad.append([e['exit'],'headroom below 2.1 m',x,name,p])
            name,p=ray((x,y+dy,e['top'][2]+.15),(0,0,-1),7.0)
            # The last treads legitimately descend under the new B1 passage
            # roof. Its clearance is checked from the tread above; inherited
            # ground, kerbs or benches may never bridge the stair opening.
            covered_by_passage=bool(p and name and 'B1 passage walls and roof' in name and p[2]-z>2.1)
            if not p or (abs(p[2]-z)>.07 and not covered_by_passage):bad.append([e['exit'],'ground surface bridges stair opening',x,dy,name,p])
check('surface stairs have real openings treads and headroom',bad,samples=sample_count)
bad=[];count=0
for e in R['entrances']:
    pts=e['passage_waypoints']
    for a,b in zip(pts[:-1],pts[1:]):
        d=np.array(b)-np.array(a);length=np.linalg.norm(d)
        for t in np.linspace(0,1,max(3,int(length/.7))):
            x,y=np.array(a)+d*t;count+=1
            name,p=ray((x,y,-5.60),(0,0,-1),.6)
            if not name or p[2]<-5.86:bad.append([e['exit'],'floor discontinuity',round(float(x),2),round(float(y),2),name])
            # A horizontal ray within the walking envelope catches hidden base or
            # inherited walls which cannot be seen in an isolated cutaway render.
            direction=Vector((d[0],d[1],0)).normalized()
            name,p=ray((x,y,-4.5),direction,.31)
            if name:bad.append([e['exit'],'blocked passage',round(float(x),2),round(float(y),2),name])
check('both entrance passages connect through the main scene to B1',bad,samples=count)
bad=[];count=0
for e in R['entrances']:
    x,y,z=e['bottom']
    for zz in (-5.3,-4.5,-3.0):
        name,p=ray((x,y,zz),(1,0,0),2.1);count+=1
        if not name or 'B1 passage walls and roof' not in name:bad.append([e['exit'],'open wall opposite stair outlet',zz,name])
    for a,b in zip(e['passage_waypoints'][:-1],e['passage_waypoints'][1:]):
        d=Vector((b[0]-a[0],b[1]-a[1],0));length=d.length;n=Vector((-d.y,d.x,0)).normalized()
        for offset in np.arange(4.0,length-4,5.0):
            p=Vector((a[0],a[1],-4.3))+d*(offset/length)
            for s in (-1,1):
                name,hit=ray(p,n*s,2.05);count+=1
                if not name or 'B1 passage walls and roof' not in name:bad.append([e['exit'],'open passage side wall',list(p),s,name])
check('new passage side walls remain enclosed after boolean openings',bad,samples=count)
bad=[]
for e in R['entrances']:
    x,y,z=e['bottom'];name,p=ray((x+.05,y,-4.6),(1,0,0),.5)
    if name and ('wall' in name.lower() or 'base' in name.lower()):bad.append([e['exit'],name])
check('stair bottom doorways are open',bad)
bad=[];gate_hits=0;recess_hits=0
# Sample a grid rather than the centres of the open rosettes. Rays through the
# ironwork gaps should reach the rear shadow wall, not the removed facade pane.
for x in np.linspace(-1.35,1.35,31):
    for z in np.linspace(1.15,4.42,31):
        name,p=ray((x,-12.0,z),(0,1,0),8)
        if name and 'Imperial double iron gate' in name:gate_hits+=1
        if p and p[1]>-6.3:recess_hits+=1
if gate_hits<40:bad.append(['insufficient visible ironwork',gate_hits])
if recess_hits<900:bad.append(['door recess obstructed',recess_hits])
check('central doorway has depth and visible iron gate',bad,gate_rays=gate_hits,recess_rays=recess_hits,total_rays=961)
bad=[]
for o in bpy.data.objects:
    if o.type=='MESH' and o.name.startswith('V13 ') and len(o.data.vertices):
        a=H.world(o)
        if not np.isfinite(a).all():bad.append([o.name,'nonfinite geometry'])
check('new native mesh coordinates are finite',bad)
check('catenary survey limits are explicit',[] if not R['catenary_audit']['all_positions_survey_verified'] else ['unverified survey claim'],audited_masts=len(R['catenary_audit']['mast_records']))
bad=[o.name for o in bpy.data.images if o.source=='FILE' and not o.packed_file and o.filepath and not os.path.isfile(bpy.path.abspath(o.filepath))]
check('image assets are packed or resolve',bad)
out={'revision':13,'checks':checks,'passed':all(c['pass'] for c in checks)}
json.dump(out,open(args[1],'w',encoding='utf8'),ensure_ascii=False,indent=2)
if not out['passed']:raise RuntimeError('V13 validation failed; inspect JSON report.')
