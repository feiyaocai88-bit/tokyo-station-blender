"""V12: independent surface-train templates, photographic interiors and exterior fittings.
Run on V11: blender -b input.blend -P mod12_surface_trains.py -- output.blend report.json baseline.json
"""
import bpy,bmesh,sys,os,json,math,re,hashlib,numpy as np
from collections import defaultdict
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
sys.path.insert(0,os.path.dirname(__file__))
import v5lib as L
import v12lib as H
import mod12_interiors as IN
import mod12_exteriors as EX
R={'revision':12,'instances':[],'templates':{},'windows':{},'exterior':{},'retained_collections':[],'scope':'surface trains only'}
COLS={};OBS={};MAIN=bpy.context.scene

def fingerprint():
    records={};cache={}
    for o in bpy.data.objects:
        r={'type':o.type,'basis':[list(v) for v in o.matrix_basis],'parent_inverse':[list(v) for v in o.matrix_parent_inverse],'parent':o.parent.name if o.parent else None}
        if o.type=='MESH':
            me=o.data
            if me.name not in cache:
                hh=hashlib.sha256()
                for seq,p,s,t in [(me.vertices,'co',3,np.float32),(me.edges,'vertices',2,np.int32),(me.loops,'vertex_index',1,np.int32),(me.polygons,'loop_total',1,np.int32),(me.polygons,'material_index',1,np.int32)]:
                    a=np.empty(len(seq)*s,dtype=t);seq.foreach_get(p,a);hh.update(a.tobytes())
                hh.update(json.dumps([m.name if m else None for m in me.materials]).encode());cache[me.name]=hh.hexdigest()
            r['geometry']=cache[me.name]
        if o.instance_collection:r['instance_collection']=o.instance_collection.name
        records[o.name]=r
    return records

def clone(c):
    if c.name in COLS:return COLS[c.name]
    c.use_fake_user=True;R['retained_collections'].append(c.name)
    n=bpy.data.collections.new('V12 | '+c.name);n['V12_source']=c.name;COLS[c.name]=n
    for o in c.objects:
        # The old full interior is retained in the original template, replaced in this copy.
        if o.name.startswith('V7 interior |'):continue
        if o.name not in OBS:
            q=o.copy();q.name='V12 copy | '+o.name;q['V12_source_object']=o.name;OBS[o.name]=q
        n.objects.link(OBS[o.name])
    for child in c.children:n.children.link(clone(child))
    return n

def clear_windows(body):
    body.data=body.data.copy();body.data.name='V12 '+body.data.name
    me=body.data;names=[m.name if m else '' for m in me.materials]
    for i,n in enumerate(names):
        if n=='V2 | stainless commuter body':me.materials[i]=H.M[H.I['steel']]
        if n=='V5 | EMU door leaf stainless':me.materials[i]=H.M[H.I['door_steel']]
    gi=len(me.materials);me.materials.append(H.M[H.I['glass']])
    bm=bmesh.new();bm.from_mesh(me);bm.faces.ensure_lookup_table();glass=[];count=0
    for f in bm.faces:
        name=names[f.material_index].lower();cen=f.calc_center_median()
        if any(k in name for k in ('see-through','reflective dark glazing')) and abs(f.normal.y)>.85:
            xs=[v.co.x for v in f.verts];zs=[v.co.z for v in f.verts]
            glass.append((min(xs),max(xs),min(zs),max(zs),cen.y));f.material_index=gi;count+=1
    cuts=0
    for f in list(bm.faces):
        if f.material_index>=len(names) or 'rubber' not in names[f.material_index].lower() or abs(f.normal.y)<.85:continue
        cen=f.calc_center_median();xs=[v.co.x for v in f.verts];zs=[v.co.z for v in f.verts];a,c,d,e=min(xs),max(xs),min(zs),max(zs)
        if abs(f.calc_area()-(c-a)*(e-d))>.012*f.calc_area()+1e-6:continue
        cover=[g for g in glass if g[4]*cen.y>0 and abs(abs(g[4])-abs(cen.y))<.014 and g[0]<c and g[1]>a and g[2]<e and g[3]>d]
        if not cover:continue
        xx=sorted(set([a,c]+[max(a,min(c,v)) for g in cover for v in g[:2]]));zz=sorted(set([d,e]+[max(d,min(e,v)) for g in cover for v in g[2:4]]))
        for x0,x1 in zip(xx,xx[1:]):
            for z0,z1 in zip(zz,zz[1:]):
                if x1-x0<1e-5 or z1-z0<1e-5:continue
                if any(g[0]-1e-5<(x0+x1)/2<g[1]+1e-5 and g[2]-1e-5<(z0+z1)/2<g[3]+1e-5 for g in cover):continue
                vs=[bm.verts.new((x0,cen.y,z0)),bm.verts.new((x1,cen.y,z0)),bm.verts.new((x1,cen.y,z1)),bm.verts.new((x0,cen.y,z1))]
                nf=bm.faces.new(vs if f.normal.y<0 else list(reversed(vs)));nf.material_index=f.material_index
        bm.faces.remove(f);cuts+=1
    bm.normal_update();bm.to_mesh(me);bm.free();me.update();R['windows'][body.name]={'transparent_faces':count,'backplates_opened':cuts}

def exterior(c,body,family,cab=False):
    b=L.MeshBuilder();rects=IN.glazing_rects(body);n=0
    for a,d,z,t,s,y in rects:
        # Rounded rubber perimeter with a second narrow bright reveal, all outside existing glass.
        H.rim(b,(a+.004,d-.004,z+.004,t-.004),y+s*.025,.024,'rubber',.048)
        H.rim(b,(a-.020,d+.020,z-.020,t+.020),y+s*.030,.007,'steel',.070)
        if d-a>.60:
            H.box(b,((a+d)/2,y+s*.034,z+.10),(.16,.018,.019),'steel')
        n+=1
    if family!='e5':
        for s in (-1,1):
            for x in (-6.7,-2.3,2.3,6.7):
                H.box(b,(x,s*1.458,2.12),(.017,.010,2.00),'rubber')
                H.box(b,(x,s*1.42,1.155),(1.28,.14,.035),'steel')
                for dy in (-.04,0,.04):H.box(b,(x,s*(1.42+dy),1.176),(1.25,.010,.008),'rubber')
                H.box(b,(x,s*1.474,3.32),(.15,.025,.055),'dark')
                H.box(b,(x,s*1.489,3.32),(.085,.009,.031),'red')
                if family in ('chuo','tokaido'):
                    H.box(b,(x+.81,s*1.471,2.16),(.12,.024,.19),'steel')
                    H.box(b,(x+.81,s*1.489,2.15),(.071,.015,.071),'green')
                    H.text(b,'開',(x+.81,s*1.499,2.15),right=(s,0,0),size=.044,k='white')
            for x in (-9.65,9.65) if not cab else (-9.65,):
                H.tube(b,[(x,s*1.43,1.10),(x,s*1.43,1.8),(x,s*1.42,3.25)],.012,'rubber')
        # Ribbed flexible gangway and cable jumpers at non-driving ends.
        for end in (-1,1) if not cab else (-1,):
            for i in range(5):
                x=end*(9.86+i*.021)
                H.tube(b,[(x,-.70,1.12),(x,-.70,3.05),(x,.70,3.05),(x,.70,1.12)],.025,'rubber')
            for s in (-1,1):H.tube(b,[(end*9.82,s*.78,1.06),(end*10.00,s*.85,.84),(end*10.02,s*.65,.75)],.018,'rubber')
        if cab:
            R.setdefault('cab_fronts',{})[family]=EX.front(c,body,family)
            H.box(b,(8.95,0,1.90),(.62,2.10,.14),'dark')
            for yy in (-.57,.10):
                H.box(b,(8.94,yy,2.04),(.32,.42,.10),'black')
                H.box(b,(8.92,yy,2.095),(.26,.34,.012),'screen')
            H.rod(b,(8.93,-.77,1.98),(8.93,-.77,2.20),.025,'black')
            H.box(b,(8.4,-.65,1.65),(.44,.45,.14),'dark');H.box(b,(8.15,-.65,1.96),(.12,.45,.55),'dark')
            for s in (-1,1):
                H.rod(b,(8.03,s*1.475,1.96),(8.25,s*1.475,1.96),.013,'steel')
                H.box(b,(8.09,s*1.35,1.12),(.42,.27,.045),'steel')
    o=H.build(b,'window seals door thresholds and end fittings | '+c.name,c,'exterior_detail',.002)
    R['exterior'][c.name]={'rounded_glazing_perimeters':n,'cab_fittings':cab}

def chuo_green_body(c,old):
    c.objects.unlink(old);b=L.MeshBuilder();doors=(-6.45,6.45)
    holes=[]
    for z0,z1 in ((1.10,1.98),(2.92,3.70)):
        for x in (-3.84,-1.92,0,1.92,3.84):holes.append((x-.86,x+.86,z0,z1))
    for x in (-8.35,8.35):holes.append((x-.83,x+.83,2.18,3.25))
    for s in (-1,1):
        dh=[(x-.66,x+.66,1.15,3.24) for x in doors]
        H.wall_with_holes(b,-5.16,5.16,.38,3.80,s*1.47,holes+dh,'steel')
        for a,d in ((-9.85,-5.16),(5.16,9.85)):
            H.wall_with_holes(b,a,d,1.10,3.80,s*1.47,holes+dh,'steel')
        for end in (-1,1):
            b.add([(end*5.16,s*1.47,.38),(end*5.72,s*1.47,1.10),(end*5.16,s*1.47,1.10)],[(0,1,2)],H.I['steel'])
        H.panel(b,(-5.16,5.16,2.02,2.76),s*1.478,'orange')
        for a,d in ((-9.85,-5.16),(5.16,9.85)):
            for z0,z1 in ((1.50,1.90),(3.50,3.64)):H.wall_with_holes(b,a,d,z0,z1,s*1.478,dh,'orange')
        for a,d,z,t in holes:
            H.panel(b,(a,d,z,t),s*1.448,'glass');H.rim(b,(a+.012,d-.012,z+.012,t-.012),s*1.48,.028,'rubber',.07)
        for x in doors:
            wh=[(x-.50,x-.12,2.37,3.14),(x+.12,x+.50,2.37,3.14)]
            H.wall_with_holes(b,x-.65,x+.65,1.15,3.24,s*1.455,wh,'door_steel')
            for q in wh:H.panel(b,q,s*1.449,'glass');H.rim(b,q,s*1.472,.018,'rubber',.06)
            H.box(b,(x,s*1.47,2.17),(.02,.014,2.02),'rubber');H.box(b,(x,s*1.42,1.155),(1.3,.16,.04),'steel')
    # Curved shoulders and roof; Green-car roof is higher than ordinary stock.
    profile=[(-1.47,3.80),(-1.36,3.96),(-1.08,4.10),(0,4.16),(1.08,4.10),(1.36,3.96),(1.47,3.80)]
    for xa,xb in zip((-9.85,-6.2,-5.1,5.1,6.2),(-6.2,-5.1,5.1,6.2,9.85)):
        for (y,z),(yy,zz) in zip(profile,profile[1:]):
            def rz(x,v):return 3.80+(v-3.80)*(1 if abs(x)<=5.1 else .10 if abs(x)>=6.2 else .5)
            b.add([(xa,y,rz(xa,z)),(xb,y,rz(xb,z)),(xb,yy,rz(xb,zz)),(xa,yy,rz(xa,zz))],[(0,1,2,3)],H.I['grey'])
    H.box(b,(0,0,.35),(10.32,2.90,.06),'grey')
    for x in (-7.50,7.50):H.box(b,(x,0,1.07),(4.70,2.85,.06),'grey')
    for x in (-9.85,9.85):H.box(b,(x,0,2.455),(.035,2.88,2.71),'steel')
    o=H.build(b,'Chuo Green double deck shell',c,'green_shell');o['V12_source_object']=old.get('V12_source_object','')
    # Photographs show a clear central double-deck roof, with low equipment at the ends.
    for ob in list(c.objects):
        if ob==o or ob.type!='MESH':continue
        lo,hi=H.world_bounds(ob)
        if lo.z>3.60 or ' underframe' in ob.name.lower() or (lo.x>-5.16 and hi.x<5.16 and hi.z<1.15 and hi.z>.40):c.objects.unlink(ob)
        elif hi.z>3.60 or (lo.z<1.15 and hi.z>.46):
            ob.data=ob.data.copy();bm=bmesh.new();bm.from_mesh(ob.data)
            fs=[f for f in bm.faces if all((ob.matrix_local@v.co).z>3.5 for v in f.verts) or all(abs((ob.matrix_local@v.co).x)<5.16 and .40<(ob.matrix_local@v.co).z<1.15 for v in f.verts)]
            bmesh.ops.delete(bm,geom=fs,context='FACES');bm.to_mesh(ob.data);bm.free()
    top=L.MeshBuilder()
    for x in (-8,8):
        H.box(top,(x,0,3.91),(2.2,1.7,.15),'grey')
        for j in range(19):H.box(top,(x-.94+j*.105,0,3.992),(.035,1.54,.016),'dark')
    H.build(top,'Chuo Green end roof ventilation',c,'green_roof_detail',.009)
    return o

def n700(c):
    # Use the model's actual curved formation, infer local axes from the four axles.
    objs=[o for o in c.objects if o.type=='MESH' and not o.hide_render];verts=[];faces=[];mats=[];axles=defaultdict(list)
    for o in objs:
        mt=re.search(r'N700 car (\d\d) axle shaft',o.name)
        if mt:
            lo,hi=H.world_bounds(o);axles[int(mt.group(1))].append((lo+hi)/2)
        if 'Downloaded N700' not in o.name:continue
        off=len(verts);verts.extend([o.matrix_local@v.co for v in o.data.vertices])
        for p in o.data.polygons:faces.append([off+i for i in p.vertices]);mats.append(o.data.materials[p.material_index].name)
    if not faces:return
    tree=BVHTree.FromPolygons(verts,faces);b=L.MeshBuilder();doors=0
    for cn,ps in axles.items():
        a=np.array(ps);center=Vector(a.mean(0));_,_,vt=np.linalg.svd(a[:,:2]-a[:,:2].mean(0));u=Vector((*vt[0],0));u=-u if u.x<0 else u;v=Vector((-u.y,u.x,0))
        for s in (-1,1):
            runs=[];start=None
            for x in np.arange(-12.5,12.61,.10):
                p=center+u*float(x)+v*(s*3);p.z=2.40;hit,norm,idx,dist=tree.ray_cast(p,-v*s,5)
                dark=idx is not None and mats[idx]=='Material.721'
                if dark and start is None:start=float(x)
                if not dark and start is not None:runs.append((start,float(x)-.1));start=None
            for j,(a,z) in enumerate(runs):
                gapL=a-runs[j-1][1] if j else 99;gapR=runs[j+1][0]-z if j+1<len(runs) else 99
                x=(a+z)/2
                if min(gapL,gapR)<1.25 or z-a>.60 or abs(x)<7.5:continue
                points=[]
                for xx,zz in H.rectpoints(x-.46,x+.46,1.12,3.13,.10,5):
                    p=center+u*xx+v*(s*3);p.z=zz;hit,norm,idx,dist=tree.ray_cast(p,-v*s,5)
                    if hit is None:points=[];break
                    points.append(hit+norm*.007)
                if points:
                    H.tube(b,points+[points[0]],.007,'rubber',6);doors+=1
                    p=center+u*x+v*(s*3);p.z=1.13;hit,n,idx,dist=tree.ray_cast(p,-v*s,5)
                    if hit:H.rod(b,hit-u*.40+n*.01,hit+u*.40+n*.01,.016,'steel')
    H.build(b,'N700 surface-conforming door joints | '+c.name,c,'n700_door_detail')
    R['exterior'][c.name]={'door_outlines':doors,'interior':'original downloaded N700 retained; not rebuilt in V12'}

def studies():
    cams=[]
    def scene(name):
        sc=bpy.data.scenes.new('V12 '+name);sc.world=bpy.data.worlds.new('V12 studio '+name);sc.world.use_nodes=True
        sc.world.node_tree.nodes['Background'].inputs[0].default_value=(.55,.62,.72,1);sc.world.node_tree.nodes['Background'].inputs[1].default_value=.30
        for pos,pow,sz in [((0,-8,10),3000,10),((0,8,8),2400,8),((-9,-2,6),1200,6)]:H.light(sc,'softbox',pos,(0,0,2),pow,sz)
        return sc
    definitions=[('Chuo','E233-0 style cab | procedural','02','03'),('Keihin','E233-1000 style cab | procedural','19','04'),('Yamanote','V3 E235-0 cab','05','06'),('Tokaido','E233-3000 style cab | procedural','07','08')]
    for name,src,ext,inside in definitions:
        sc=scene(name+' vehicle study');e=bpy.data.objects.new('V12 lit study '+name,None);e.instance_type='COLLECTION';e.instance_collection=COLS[src];e['V5_head']=1.;e['V5_tail']=0.;e['V5_dest']=0.;sc.collection.objects.link(e)
        if ext:cams.append(H.camera(sc,ext+' '+name+' exterior',(24,-32,11),(0,0,2.0),48))
        cams.append(H.camera(sc,inside+' '+name+' passenger cabin',(6.9,.02,2.70),(-8.7,.0,2.55),18))
    sc=scene('surface fleet');
    for i,(_,src,_,_) in enumerate(definitions):
        e=bpy.data.objects.new('V12 comparison '+src,None);e.instance_type='COLLECTION';e.instance_collection=COLS[src];sc.collection.objects.link(e);e.location=(0,i*5.4,0);e['V5_head']=1.;e['V5_tail']=0.;e['V5_dest']=0.
    H.light(sc,'fleet fill',(0,12,13),(0,8,0),5000,16)
    cams.append(H.camera(sc,'01 surface fleet',(31,-29,30),(0,7.5,1.5),48))
    sc=scene('front comparison');labels=L.MeshBuilder()
    for i,((name,src,_,_),series) in enumerate(zip(definitions,['E233-0','E233-1000','E235-0','E233-3000'])):
        e=bpy.data.objects.new('V12 face comparison '+name,None);e.instance_type='COLLECTION';e.instance_collection=COLS[src];sc.collection.objects.link(e);e.location=(0,i*4.1,0);e['V5_head']=1.;e['V5_tail']=0.;e['V5_dest']=0.
        H.text(labels,series,(10.7,i*4.1,5.05),right=(0,1,0),size=.32,k='white')
        H.text(labels,name,(10.7,i*4.1,4.65),right=(0,1,0),size=.24,k='white')
    H.build(labels,'front comparison labels',sc.collection,'study_labels')
    H.light(sc,'front key',(22,-1,9),(10,6,2),4500,12);H.light(sc,'front fill',(18,14,7),(10,6,2),3000,10)
    camera=H.camera(sc,'18 four cab fronts',(32,6.15,2.60),(9.9,6.15,2.60),48,ortho=15.8);camera['V12_aspect_height']=.39;cams.append(camera)
    cams.append(H.camera(bpy.data.scenes['V12 Yamanote vehicle study'],'20 E235 cab close',(17,-10,6),(8,0,2.25),52))
    sc=scene('Chuo Green study');sc.collection.children.link(COLS['E233-0 style Green car | procedural'])
    cams.append(H.camera(sc,'09 Chuo Green exterior',(24,-31,11),(0,0,2.05),50))
    cams.append(H.camera(sc,'10 Chuo Green upper deck',(4.45,0,3.55),(-4.3,0,3.20),19))
    # True cutaway is a separate study: main scene keeps the complete car.
    cut=scene('Green cutaway');src=COLS['E233-0 style Green car | procedural'];cc=bpy.data.collections.new('V12 Green cutaway copies');cut.collection.children.link(cc)
    for o in src.all_objects:
        if o.type!='MESH':continue
        q=o.copy();q.data=o.data.copy();q.name='V12 cutaway '+o.name;cc.objects.link(q)
        if o.get('V12_kind') in ('green_shell','green_lining'):
            bm=bmesh.new();bm.from_mesh(q.data)
            remove=[f for f in bm.faces if f.calc_center_median().y<-.30 or f.calc_center_median().z>3.85]
            bmesh.ops.delete(bm,geom=remove,context='FACES');bm.to_mesh(q.data);bm.free()
    cams.append(H.camera(cut,'11 Green two deck cutaway',(17,-27,12),(0,0,1.9),48))
    if 'V3 E5 car 02' in COLS:
        sc=scene('E5 vehicle study');sc.collection.children.link(COLS['V3 E5 car 02'])
        cams.append(H.camera(sc,'12 E5 exterior',(27,-34,11),(0,0,2),48));cams.append(H.camera(sc,'13 E5 ordinary seats',(9,0,2.98),(-10,0,2.8),20))
    cams.append(H.camera(MAIN,'14 trains at Tokyo platforms',(-88,48.8,11.4),(-64,52,7.9),45))
    sc=scene('N700 body details');sc.collection.children.link(COLS['V3 N700 corrected formation track 14'])
    H.light(sc,'N700 close key',(50,-8,12),(50,0,2),5000,12);H.light(sc,'N700 close fill',(50,8,7),(50,0,2),2500,10)
    cams.append(H.camera(sc,'15 N700 side door details',(66,-28,8),(50,0,1.9),48))
    sc=scene('Tokaido Green study');sc.collection.children.link(COLS['V4_Train_Green_E233_3000_car_05'])
    cams.append(H.camera(sc,'16 Tokaido Green upper deck',(3.85,0,3.43),(-3.85,0,3.15),19))
    cams.append(H.camera(sc,'17 Tokaido Green exterior',(24,-31,11),(0,0,2.05),50))
    R['review_cameras']=[o.name for o in cams]

def main():
    if MAIN.get('V12_refinement'):raise RuntimeError('Start from the V11 deliverable, not a previously modified V12.')
    args=sys.argv[sys.argv.index('--')+1:]
    if len(args)>2:json.dump(fingerprint(),open(args[2],'w',encoding='utf8'),separators=(',',':'))
    H.setup();EX.setup()
    instances=[o for o in MAIN.objects if o.name.startswith('Track ') and o.instance_collection and o.location.z>0]
    for e in instances:
        src=e.instance_collection;e.instance_collection=clone(src)
        R['instances'].append({'name':e.name,'source':src.name,'replacement':e.instance_collection.name,'matrix':[list(v) for v in e.matrix_basis]})
    for name,c in list(COLS.items()):
        body=next((o for o in c.objects if 'one-piece body |' in o.name),None)
        if body:
            green='Green' in name;e5='E5' in name
            if green:
                body=chuo_green_body(c,body);R['templates'][name]=IN.green(c,True)
            else:
                clear_windows(body)
                if e5:
                    car=int(re.search(r'(?:car_|car )(\d\d)',name).group(1));R['templates'][name]=IN.e5(c,body,car);exterior(c,body,'e5')
                else:
                    fam='yamanote' if 'E235' in name else 'keihin' if '1000' in name else 'tokaido' if '3000' in name else 'chuo';cab='cab' in name
                    EX.prepare(c,body,fam,cab)
                    R['templates'][name]=IN.ordinary(c,body,fam,cab,semi=cab and fam=='tokaido');exterior(c,body,fam,cab)
        elif name.startswith('V4_Train_Green'):
            for o in list(c.objects):
                if 'lower_deck_floor' in o.name or 'upper_deck_floor' in o.name:c.objects.unlink(o);continue
                if 'dropped_double_deck_belly' in o.name:
                    o.data=o.data.copy();bm=bmesh.new();bm.from_mesh(o.data)
                    fs=[f for f in bm.faces if all((o.matrix_local@v.co).z>1.03 for v in f.verts)]
                    bmesh.ops.delete(bm,geom=fs,context='FACES');bm.to_mesh(o.data);bm.free()
                if o.type=='MESH' and 'recessed_glass' in o.name:
                    o.data=o.data.copy()
                    for i in range(len(o.data.materials)):o.data.materials[i]=H.M[H.I['glass']]
            R['templates'][name]=IN.green(c,False)
        elif 'N700 corrected formation' in name:n700(c)
        print('V12_TEMPLATE',name,flush=True)
    studies()
    R['counts']={'surface_instances':len(instances),'cloned_templates':len(COLS),'passenger_templates':len(R['templates']),'review_views':len(R['review_cameras'])}
    R['limitations']=['Photo-referenced interpretation, not measured engineering reproduction.','Retained vehicle positions, train formation and wheelbases. New seating fits model envelopes; counts are not certified capacities.','E233-3000 cab templates use representative semi-cross seating; other ordinary templates retain longitudinal seating.','N700 source body and interior retained; V12 adds surface-conforming door joints.','Station, underground Sobu/Yokosuka and Marunouchi Line assets remain as V11.']
    MAIN['V12_refinement']=json.dumps(R,ensure_ascii=False);MAIN['V12_accuracy']='Photo-informed surface rolling stock. See README_V12.txt and sources_and_licenses/train_refinement_v12.json.'
    guide=os.path.join(os.path.dirname(__file__),'..','README_V12.txt')
    if os.path.isfile(guide):tx=bpy.data.texts.new('README_V12_中文');tx.write(open(guide,encoding='utf8').read())
    bpy.context.view_layer.update();bpy.ops.file.pack_all();bpy.context.preferences.filepaths.save_version=0
    out=os.path.abspath(args[0]);os.makedirs(os.path.dirname(out),exist_ok=True);bpy.ops.wm.save_as_mainfile(filepath=out,compress=True)
    json.dump(R,open(args[1],'w',encoding='utf8'),ensure_ascii=False,indent=2);print('V12_BUILD_OK',R['counts'],flush=True)
if __name__=='__main__':main()
