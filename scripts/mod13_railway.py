"""Repair barrier extents; expose sleepers; add physical track and service detail."""
import bpy,math,re,numpy as np
from mathutils import Vector,Matrix
import v13lib as H
L=H.L

def trackframe(k,x,z=0,dy=0):
    a=math.atan2(float(H.ty(k,x+.1)-H.ty(k,x-.1)),.2)
    return Matrix.Translation((x,float(H.ty(k,x)),z))@Matrix.Rotation(a,4,'Z')@Matrix.Translation((0,dy,0))

def barriers():
    for name,k,side,height in [('Chuo west','01',-1,2.20),('Chuo east','02',1,1.85),('Shinkansen east','19',1,2.15)]:
        old=bpy.data.objects['V10 '+name+' segmented acoustic screen'];lo,hi=H.bounds(old);H.retire(old)
        deck=bpy.data.objects['V3 Track '+k+' curved viaduct'];p=H.world(deck)
        # Mesh follows the curved centreline; choose the actual end sections, not
        # the full station box. End panels never continue beyond this track deck.
        x0=math.ceil(float(p[:,0].min())+1.0);x1=math.floor(float(p[:,0].max())-.65)
        z0=float(p[:,2].max());off=1.94
        mb=L.MeshBuilder();support=L.MeshBuilder();xs=np.linspace(x0,x1,math.ceil((x1-x0)/2.50)+1)
        for j,(a,b) in enumerate(zip(xs[:-1],xs[1:])):
            x=(a+b)/2;F=trackframe(k,x,z0,side*off);ln=math.hypot(b-a,H.ty(k,b)-H.ty(k,a));h=height
            # Low return at either end keeps the terminating screen visually grounded.
            if j in (0,len(xs)-2):h=1.20
            H.box(mb,(0,0,.34),(ln,.18,.68),'concrete',F=F)
            H.box(mb,(0,0,.93),(ln-.08,.11,.49),'paint',F=F)
            if h>1.25:
                H.box(mb,(0,0,(1.22+h)/2),(ln-.10,.055,h-1.22),'glass' if name.startswith('Chuo') else 'paint',F=F)
            for zz in (.75,.89,1.03,1.17):H.box(mb,(0,-side*.067,zz),(ln-.11,.025,.025),'steel',F=F)
            for dx in (-ln/2+.035,ln/2-.035):
                H.box(mb,(dx,0,h/2),(.07,.19,h),'steel',F=F)
                H.box(support,(dx,-side*.23,-.14),(.22,.65,.25),'steel',F=F)
            H.box(mb,(0,0,h),(ln,.15,.055),'steel',F=F)
            # An edge coping/corbel lands 0.33 m inside the existing viaduct mesh.
            H.box(support,(0,-side*.13,-.07),(ln,.56,.14),'concrete',F=F)
        o=H.build(mb,name+' deck-edge acoustic screen','Acoustic_Barriers','barrier',track=k)
        H.build(support,name+' continuous coping and deck anchors','Acoustic_Barriers','barrier_support',track=k)
        H.R['barriers'].append({'object':o.name,'track':k,'range':[x0,x1],'previous_range':[round(float(lo[0]),2),round(float(hi[0]),2)],'deck_top':z0,'offset':off,'height':height,'panels':len(xs)-1,'basis':'clipped to actual model viaduct; section height is photo-informed, not a field measurement'})
        H.count('barrier_panels',len(xs)-1)

def tracks():
    # Preserve node-instanced sleepers. Only the independent ballast copy changes.
    rng=np.random.default_rng(1313)
    for bed in list(bpy.context.scene.objects):
        m=re.match(r'V5 track \| Track (\d+) ballast bed$',bed.name)
        if not m or bed.hide_render:continue
        k=m.group(1);q=H.copy_replace(bed);p=H.world(q);top=float(p[:,2].max());bottom=float(p[:,2].min())
        # Sleeper centre is 25 mm lower than its rail seat. The old crib surface
        # left just 5 mm exposed at midspan; expose 65 mm without moving the rails.
        inv=q.matrix_world.inverted()
        for v in q.data.vertices:
            w=q.matrix_world@v.co
            if w.z>bottom+.20:w.z-=.060
            v.co=inv@w
        q.data.update();stone=L.MeshBuilder();details=L.MeshBuilder();start=math.ceil(float(p[:,0].min())+1);end=math.floor(float(p[:,0].max())-1)
        shin=k in ['14','15','16','17','18','19','20','21','22','23'];half=1.36 if shin else 1.16;g=.750 if shin else .566
        # Low-poly angular rocks remain visible in Solid shading as real geometry.
        for x in np.arange(start,end,.22):
            for yy in (-half*.86,0,half*.86):
                xx=x+rng.uniform(-.09,.09);y=yy+rng.uniform(-.14,.14);F=trackframe(k,xx,top-.060)
                sx=rng.uniform(.035,.070);sy=rng.uniform(.026,.055);sz=rng.uniform(.015,.034);ang=rng.uniform(0,math.tau)
                pts=[(-sx,-sy,0),(sx,-sy*.8,0),(sx*.8,sy,0),(-sx*.7,sy*.9,0),(-sx*.55,-sy*.5,sz),(sx*.5,-sy*.4,sz*.85),(sx*.35,sy*.5,sz*.9),(-sx*.4,sy*.4,sz)]
                C=F@Matrix.Translation((0,y,0))@Matrix.Rotation(ang,4,'Z')
                stone.add([tuple(C@Vector(v)) for v in pts],[(0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)],H.I[['ballast_a','ballast_b','ballast_c'][int(rng.integers(3))]])
                H.count('physical_ballast_stones')
        H.build(stone,'Track '+k+' angular ballast stones','Track_Detail','ballast_stones',track=k)
        # Maintenance cable troughs outside sleepers, recessed joints and access lids.
        side=-1 if int(k)%2 else 1
        for a in np.arange(start,end,2):
            ln=min(1.96,end-a);F=trackframe(k,a+ln/2,top-.015,side*(1.47 if shin else 1.32))
            H.box(details,(0,0,0),(ln,.20,.15),'concrete',F=F)
            H.box(details,(0,0,.08),(ln-.025,.21,.035),'paint',F=F)
            if int(a)%20==0:
                for dx in (-.4,.4):H.box(details,(dx,0,.102),(.14,.045,.008),'dark',F=F)
        # Bonding jumpers on the field side; no invented switches in straight platforms.
        for x in np.arange(start+15,end-5,30):
            F=trackframe(k,x,top+.035)
            for s in (-1,1):
                pts=[F@Vector((dx,s*(g+.09+off),zz)) for dx,off,zz in [(-.4,0,.02),(-.22,.13,-.005),(.22,.13,-.005),(.4,0,.02)]]
                H.tube(details,pts,.008,'rust',6)
            # Trackside numbered junction box on a squat concrete plinth.
            F=trackframe(k,x,top,side*(1.49 if shin else 1.35))
            H.box(details,(0,0,.15),(.43,.30,.30),'paint',F=F)
            H.box(details,(0,0,.31),(.48,.34,.035),'steel',F=F)
            H.count('track_junction_boxes')
        H.build(details,'Track '+k+' trough lids bonding and junction boxes','Track_Detail','track_fittings',track=k)
        H.R['tracks'].append({'track':k,'old_crib_top':top,'new_crib_top':top-.06,'rail_and_sleepers_moved':False})
    # Give the source sleepers a new material by copying both the template and GN
    # owner. Originals and their material assignments stay available for rollback.
    templates={}
    for o in list(bpy.context.scene.objects):
        if not re.match(r'V5 track \| Track \d+ PC sleepers \+ fastenings$',o.name):continue
        oldmod=next(m for m in o.modifiers if m.type=='NODES');ident=oldmod.node_group.interface.items_tree['Template'].identifier
        src=getattr(oldmod.properties.inputs,ident).value
        if src.name not in templates:
            c=bpy.data.collections.new('V13 sleeper templates '+str(len(templates)));c.use_fake_user=True
            t=src.copy();t.data=src.data.copy();t.name='V13 '+src.name;t.hide_render=False;t.hide_viewport=False;c.objects.link(t)
            for i,mat in enumerate(t.data.materials):
                if mat and 'concrete' in mat.name.lower():t.data.materials[i]=H.M[H.I['pc_sleeper']]
            templates[src.name]=t
        q=H.copy_replace(o);mod=next(m for m in q.modifiers if m.type=='NODES');getattr(mod.properties.inputs,ident).value=templates[src.name]
    H.count('surface_tracks_detailed',len(H.R['tracks']))

def service_details():
    for name,x,y,l,w,roof in [('North',-176,17,17,12,10.55),('South',192,16,18,11,9.85),('Yaesu',-95,216.2,63,11.5,13.85)]:
        b=L.MeshBuilder();twx=x-l*.21;twz=roof+.52;hh=4.5 if l>30 else 3.6;sw=6.4
        # The old tower had blank ends. All four faces now have deep blade frames.
        for s in (-1,1):
            F=Matrix.Translation((twx+s*2.73,y,twz))@Matrix.Rotation(s*math.pi/2,4,'Z')
            H.box(b,(0,0,hh*.52),(sw-.5,.05,hh*.78),'dark',F=F)
            for z in np.arange(.35,hh-.25,.16):H.box(b,(0,-.09,z),(sw-.55,.19,.055),'paint',F=F)
            for xx in (-sw/2+.17,sw/2-.17):H.box(b,(xx,-.1,hh/2),(.10,.22,hh-.25),'steel',F=F)
            for yy in (-sw*.22,sw*.22):H.box(b,(yy,-.11,hh/2),(.07,.20,hh-.32),'steel',F=F)
        # Flashing seams, roof inspection walkway, duct elbows and mounting flanges.
        for dx in np.arange(-2.65,2.66,.65):H.box(b,(twx+dx,y,twz+hh+.315),(.035,sw+.62,.025),'steel')
        walkway_y=y-w/2+1.1
        H.box(b,(x,walkway_y,roof+.34),(l-1.3,.75,.10),'steel')
        for xx in np.arange(x-l/2+.8,x+l/2-.5,.20):H.box(b,(xx,walkway_y,roof+.402),(.04,.71,.025),'dark')
        for dx in (-l*.31,l*.32):
            H.box(b,(x+dx,y-w*.19,roof+.57),(1.6,.65,.62),'paint')
            H.box(b,(x+dx,y-w*.19,roof+.90),(1.7,.75,.06),'steel')
            for a in (-.55,.55):H.box(b,(x+dx+a,y-w*.19,roof+.60),(.06,.72,.68),'steel')
        # End-wall service doors, large ventilation grilles, reveal joints and lamps.
        for s in (-1,1):
            F=Matrix.Translation((x+s*(l/2+.025),y,0))@Matrix.Rotation(s*math.pi/2,4,'Z')
            H.box(b,(-w*.23,-.025,1.30),(1.7,.08,2.5),'dark',F=F)
            for d in (-.42,.42):H.box(b,(-w*.23+d,-.083,1.30),(.80,.045,2.4),'paint',F=F)
            for d in (-.12,.12):H.box(b,(-w*.23+d,-.13,1.28),(.045,.055,.32),'steel',F=F)
            H.box(b,(-w*.23,-.43,2.69),(2.15,.95,.09),'steel',F=F)
            H.box(b,(w*.22,-.04,3.45),(w*.33,.07,1.9),'dark',F=F)
            for zz in np.arange(2.62,4.36,.14):H.box(b,(w*.22,-.11,zz),(w*.32,.17,.045),'paint',F=F)
            for xx in (-w/2+.35,w/2-.35):
                for zz in np.arange(.8,roof-.3,1.1):H.box(b,(xx,-.08,zz),(.18,.10,.045),'steel',F=F)
                pts=[F@Vector((xx,-.10,z)) for z in (.3,roof-.1)];H.rod(b,*pts,.055,'steel')
            for xx in (-w*.23,w*.23):
                H.box(b,(xx,-.16,5.0),(.24,.20,.16),'steel',F=F);H.box(b,(xx,-.27,4.96),(.17,.025,.08),'lamp',F=F)
            H.text(b,'設備室',tuple(F@Vector((-w*.23,-.14,2.05))),right=tuple(F.to_3x3()@Vector((1,0,0))),size=.20,key='dark')
        H.build(b,name+' service block end grilles ducts walkways and doors','Service_Detail','service_detail')
        H.count('service_buildings_completed')
    # The station-side strip needs ground fittings as well as rooftop equipment.
    for side,x0,x1 in [('North',-198,-145),('South',140,215)]:
        b=L.MeshBuilder();y=8.6
        for xx in np.arange(x0,x1,1.25):
            H.box(b,(xx,y,.045),(1.20,.24,.08),'dark')
            for dx in np.arange(-.55,.56,.1):H.box(b,(xx+dx,y,.09),(.025,.22,.02),'steel')
        for xx in np.arange(x0+4,x1,13):
            H.box(b,(xx,y+1.0,.06),(.82,.65,.08),'concrete')
            H.box(b,(xx,y+1.0,.11),(.70,.54,.025),'steel')
            for dx in (-.22,.22):H.box(b,(xx+dx,y+1.0,.126),(.11,.035,.008),'dark')
        H.build(b,side+' service alley grated drain and inspection covers','Service_Detail','alley_detail')
    # Existing station-side canopies retain their shapes; add attached gutters,
    # braces and recessed soffit light strips using their actual mesh bounds.
    for o in list(bpy.context.scene.objects):
        if o.type!='MESH' or o.hide_render or 'canopy' not in o.name.lower() or o.name.startswith(('V10','V11','V12','V13','V5','V6','V8')):continue
        lo,hi=H.bounds(o)
        if not (4<lo[1]<25 and 2<hi[2]<8 and hi[0]-lo[0]>7 and hi[1]-lo[1]>3):continue
        b=L.MeshBuilder();z=float(lo[2]);yy=float(hi[1]);a=float(lo[0]);c=float(hi[0])
        H.box(b,((a+c)/2,yy+.03,z-.06),(c-a,.15,.13),'steel')
        for xx in np.arange(a+.7,c,4):
            H.rod(b,(xx,yy-.1,z-.8),(xx,yy-1.2,z-.1),.04,'paint')
            H.box(b,(xx,yy-1.0,z-.13),(1.4,.14,.04),'lamp')
        for xx in (a+.3,c-.3):H.rod(b,(xx,yy,.2),(xx,yy,z-.10),.06,'steel')
        H.build(b,o.name+' gutter braces and soffit lights','Service_Detail','canopy_detail')

def catenary_audit():
    # Photos confirm roof-piercing supports, independent platform portals and
    # staggered throat portals, but do not resolve surveyed coordinates for each
    # mast. Keep the prior wire geometry; record every observable model position.
    rows=[];b=L.MeshBuilder()
    for name in ['V6 OCS | masts','V8 OCS | masts at the level change']:
        o=bpy.data.objects.get(name)
        if not o:continue
        for lo,hi in H.components(o):
            if hi[2]-lo[2]<3 or hi[0]-lo[0]>.7 or hi[1]-lo[1]>.7:continue
            x,y=(lo[:2]+hi[:2])/2;z0=float(lo[2]);z1=float(hi[2]);i=len(rows)+1
            same=[k for k in H.TRACKS] if hasattr(H,'TRACKS') else list(H.B.TRACKS)
            candidates=[k for k in same if (k in ('01','02'))==(z0>11)]
            nearest=min(candidates,key=lambda k:abs(float(H.ty(k,x))-y));offset=abs(float(H.ty(nearest,x))-y)
            row={'id':i,'object':name,'xy':[round(float(x),3),round(float(y),3)],'base_z':round(z0,3),'top_z':round(z1,3),'nearest_track':nearest,'lateral_distance':round(offset,3),'photo_position_status':'unmeasured; inherited procedural location'}
            rows.append(row)
            # Grounding cable, straps and base bolts are attached to the existing
            # stem, not placed as floating independent utility poles.
            H.rod(b,(x+.18,y,z0+.12),(x+.18,y,min(z0+3.1,z1)),.010,'copper_aged',6)
            for zz in np.arange(z0+.5,min(z0+3.0,z1),.65):H.ring(b,(x,y,zz),.186,.013,'steel','XY',16)
            for dx in (-.21,.21):
                for dy in (-.21,.21):H.cyl(b,(x+dx,y+dy,z0+.075),.025,.06,'steel',6)
            H.count('catenary_masts_audited')
    H.build(b,'catenary mast grounding straps and anchor bolts','Catenary_Detail','mast_fittings')
    H.R['catenary_audit']={'all_positions_survey_verified':False,'source_grid':'V6 nominal 22 m stations with obstacle offsets','mast_records':rows,'finding':'Support families and roof/track relationships can be checked photographically. These sources do not establish every mast coordinate; no random repositioning or claim of survey equivalence is made.'}

def run():barriers();tracks();service_details();catenary_audit()
