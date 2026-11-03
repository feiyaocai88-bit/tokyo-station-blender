"""M7/M8 surface stairs and continuous passages to the inherited M17 B1 concourse.

Exit topology and M8 architectural vocabulary are referenced. Locations are fitted
to this diorama's already adjusted plaza/Metro geometry, not survey coordinates.
"""
import bpy,math,numpy as np
from mathutils import Matrix,Vector
import v13lib as H
from mod11_marunouchi import F as MF,B1
L=H.L
GROUND=.30
RISE=(GROUND-B1)/36
TREAD=.28
RUN=36*TREAD+1.4

def corridor(points,label,volumes):
    floor=L.MeshBuilder();walls=L.MeshBuilder();detail=L.MeshBuilder();clear=[]
    for a,b in zip(points[:-1],points[1:]):
        a,b=Vector((*a,0)),Vector((*b,0));d=b-a;length=d.length
        F=Matrix.Translation((a+b)/2)@Matrix.Rotation(math.atan2(d.y,d.x),4,'Z')
        H.box(floor,(0,0,B1-.16),(length+3.3,3.4,.26),'concrete',F=F)
        H.box(floor,(0,0,B1-.015),(length+3.25,3.28,.03),'metro_tile',F=F)
        # Complete perimeter, including end caps; the union of the neighbouring
        # clear volumes removes only internal walls at the turning junctions.
        for s in (-1,1):
            H.box(walls,(0,s*1.78,B1+1.62),(length+3.6,.20,3.24),'metro_tile',F=F)
            H.box(walls,(s*(length/2+1.70),0,B1+1.62),(.20,3.76,3.24),'metro_tile',F=F)
        H.box(walls,(0,0,B1+3.40),(length+3.3,3.75,.24),'concrete',F=F)
        # Keep a small separation from the coplanar inner wall faces. Exact
        # subtraction at the same plane can discard an entire thin wall.
        clear.append((F,(0,0,B1+1.63),(length+3.30,3.30,3.27)))
        for x in np.arange(-length/2+2,length/2,4.5):
            H.box(detail,(x,0,B1+3.23),(1.8,.22,.035),'lamp',F=F)
            H.box(detail,(x,0,B1+.05),(2.0,.30,.028),'yellow',F=F)
        for x in np.arange(-length/2+3,length/2,9):
            dlight=bpy.data.lights.new('V13 '+label+' passage luminaire','AREA');dlight.energy=160;dlight.shape='DISK';dlight.size=2.5;dlight.color=(1,.96,.89)
            ob=bpy.data.objects.new(dlight.name,dlight);H.col('Metro_Access_Lights').objects.link(ob);ob.location=F@Vector((x,0,B1+3.12))
        volumes.append((F,(0,0,B1+1.70),(length+3.6,3.65,3.65),label+' passage'))
    H.build(floor,label+' continuous B1 passage floor','Metro_Access_Floor','metro_passage_floor')
    wallobj=H.build(walls,label+' B1 passage walls and roof','Metro_Access_Shell','metro_passage_shell')
    start=points[0];end=points[-1]
    # Open the side facing the stair outlet. Keep the wall opposite the stairs.
    clear.append((Matrix.Identity(4),(start[0]-.75,start[1],B1+1.63),(2.7,3.15,3.27)))
    clear.append((Matrix.Identity(4),(end[0],end[1],B1+1.63),(7,6.5,3.27)))
    for FF,cc,ss in clear:
        b=L.MeshBuilder();H.box(b,cc,ss,'dark',F=FF);cut=H.build(b,'temporary passage union cutter','Work','temporary')
        H.boolean_cut(wallobj,cut);bpy.data.objects.remove(cut,do_unlink=True)
    H.build(detail,label+' B1 passage lighting and guidance','Metro_Access_Detail','metro_passage_detail')

def entrance(code,x,y,join,via,volumes):
    F=Matrix.Translation((x,y,0));stair=L.MeshBuilder();shell=L.MeshBuilder();pavilion=L.MeshBuilder();detail=L.MeshBuilder()
    # Ground landing then two flights with a real intermediate landing.
    H.box(stair,(-.70,0,GROUND-.12),(1.4,3.3,.24),'granite',F=F)
    samples=[]
    for k in range(36):
        u=k*TREAD+(1.4 if k>=18 else 0);z=GROUND-(k+1)*RISE
        H.box(stair,(u+TREAD/2,0,z-.10),(TREAD+.008,3.0,.20),'metro_tile',F=F)
        H.box(detail,(u+.025,0,z+.008),(.045,2.96,.018),'stone',F=F)
        for sy in (-1,1):H.box(detail,(u+.02,sy*1.37,z+.018),(.045,.14,.018),'yellow',F=F)
        samples.append([x+u+.14,y,z])
    H.box(stair,(18*TREAD+.70,0,GROUND-18*RISE-.12),(1.40,3.0,.24),'metro_tile',F=F)
    H.box(stair,(RUN+.80,0,B1-.12),(1.60,3.35,.24),'metro_tile',F=F)
    # Sloping cheeks support the thin treads; stair flights have open space above.
    for sy in (-1,1):
        H.beam(stair,(x+.14,y+sy*1.40,GROUND-.31),(x+18*TREAD-.14,y+sy*1.40,GROUND-18*RISE-.30),.20,.24,'concrete')
        H.beam(stair,(x+18*TREAD+1.54,y+sy*1.40,GROUND-18*RISE-.31),(x+RUN-.14,y+sy*1.40,B1-.30),.20,.24,'concrete')
        # Tile side walls with real grout, extending down to the bottom of the stair box.
        H.box(shell,(RUN/2,sy*1.68,(B1+GROUND)/2),(RUN+.30,.24,GROUND-B1+.1),'metro_tile',F=F)
        for z in np.arange(B1+.15,GROUND,.60):H.box(detail,(RUN/2,sy*1.553,z),(RUN-.15,.012,.012),'stone',F=F)
        for u in np.arange(.6,RUN,.90):H.box(detail,(u,sy*1.553,(B1+GROUND)/2),(.012,.012,GROUND-B1-.1),'stone',F=F)
        # The handrail follows both flights and the landing, with continuous returns.
        pts=[(-.65,GROUND+.87),(0,GROUND+.87),(18*TREAD,GROUND-18*RISE+.87),(18*TREAD+1.4,GROUND-18*RISE+.87),(RUN,B1+.87),(RUN+1.1,B1+.87)]
        for offset in (0,-.25):H.tube(detail,[F@Vector((u,sy*1.38,z+offset)) for u,z in pts],.032,'steel',10)
        for u in [1,3.5,7.3,9.8]:
            step=max(0,min(35,int((u-(1.4 if u>6.44 else 0))/TREAD)))
            z=GROUND-(step+1)*RISE
            H.rod(detail,(x+u,y+sy*1.53,z+.55),(x+u,y+sy*1.38,z+.55),.022,'steel')
    H.box(shell,(RUN+.14,0,B1+1.5),(.20,3.55,3.0),'metro_tile',F=F)
    # End wall has a genuine doorway, cut before linking to the branch corridor.
    shellobj=H.build(shell,code+' tiled stairwell retaining walls','Metro_Access_Shell','metro_stair_shell')
    cut=L.MeshBuilder();H.box(cut,(x+RUN+.14,y,B1+1.5),(1,3.12,3.1),'dark')
    cutter=H.build(cut,'temporary stair outlet cutter','Work','temporary');H.boolean_cut(shellobj,cutter);bpy.data.objects.remove(cutter,do_unlink=True)
    H.build(stair,code+' 36 treads mid landing and B1 landing','Metro_Access_Floor','metro_stairs',exit_code=code)
    # Photo of M8: granite end bollards, dark metal portal, transparent side panels,
    # flat overhanging roof and an illuminated station sign above the stair mouth.
    for sy in (-1,1):
        H.box(pavilion,(RUN/2,sy*1.79,GROUND+.43),(RUN+.40,.34,.86),'granite',F=F)
        for u in np.linspace(-.30,RUN+.30,6):H.box(pavilion,(u,sy*1.82,GROUND+1.90),(.10,.10,2.75),'iron',F=F)
        for a,b in zip(np.linspace(-.25,RUN+.25,6)[:-1],np.linspace(-.25,RUN+.25,6)[1:]):H.box(pavilion,((a+b)/2,sy*1.82,GROUND+1.99),(b-a-.12,.025,2.18),'entrance_glass',F=F)
        for z in (GROUND+.91,GROUND+3.10):H.box(pavilion,(RUN/2,sy*1.82,z),(RUN+.70,.10,.09),'iron',F=F)
        H.cyl(pavilion,(x-.36,y+sy*1.82,GROUND+.42),.28,.84,'granite',24)
    H.box(pavilion,(RUN/2,0,GROUND+3.18),(RUN+1.25,4.08,.23),'iron',F=F)
    H.box(pavilion,(RUN/2,0,GROUND+3.04),(RUN+1.0,3.80,.045),'paint',F=F)
    # Rear glazing protects the stair, without an opaque pretend door on the ground.
    H.box(pavilion,(RUN+.30,0,GROUND+1.99),(.025,3.57,2.18),'entrance_glass',F=F)
    H.box(pavilion,(-.66,0,GROUND+3.15),(.10,3.70,.40),'iron',F=F)
    H.box(pavilion,(-.719,0,GROUND+3.15),(.025,3.48,.29),'lamp',F=F)
    H.text(pavilion,'東京駅  Tokyo',(x-.74,y+.30,GROUND+3.15),right=(0,-1,0),size=.26,key='blue')
    H.box(pavilion,(-.74,-1.39,GROUND+3.15),(.025,.55,.285),'yellow',F=F)
    H.text(pavilion,code,(x-.765,y-1.39,GROUND+3.15),right=(0,-1,0),size=.23,key='dark')
    H.text(pavilion,'丸ノ内線  M17',(x-.755,y+.12,GROUND+2.79),right=(0,-1,0),size=.15,key='white')
    for u in np.arange(.65,RUN,2.4):
        H.cyl(pavilion,(x+u,y,GROUND+2.99),.10,.04,'lamp',16)
    H.build(pavilion,code+' glazed surface entrance pavilion and illuminated sign','Metro_Entrances','metro_entrance',exit_code=code)
    # Tactile studs across the top landing and raised guide bars approaching it.
    for u in np.arange(-1.18,-.32,.15):
        for v in np.arange(-1.38,1.4,.15):H.cyl(detail,(x+u,y+v,GROUND+.027),.025,.014,'yellow',8)
    H.box(detail,(-.75,0,GROUND+.007),(.90,2.95,.02),'yellow',F=F)
    for sy in (-1,1):H.box(detail,(-.65,sy*1.1,GROUND+2.85),(.04,.65,.045),'lamp',F=F)
    H.build(detail,code+' handrails stair nosings tactile paving and lights','Metro_Access_Detail','metro_stair_detail')
    paving=L.MeshBuilder()
    for u in np.arange(-2.6,RUN+1.6,.60):
        for v in np.arange(-3.0,3.0,.60):
            if u+.60>-.05 and u<RUN+.1 and v+.60>-1.60 and v<1.60:continue
            H.box(paving,(u+.30,v+.30,GROUND+.003),(.591,.591,.025),'granite',F=F)
    H.build(paving,code+' approach stone paving with joints','Metro_Approaches','metro_approach')
    volumes.append((F,(RUN/2,0,(GROUND+B1)/2),(RUN+.15,3.12,GROUND-B1+.6),code+' stair opening'))
    # Additional below-ground headroom/landing space reaches the passage floor.
    volumes.append((F,(RUN+.80,0,B1+1.65),(2.0,3.65,3.7),code+' bottom landing'))
    end=(x+RUN+.80,y)
    points=[end]+via+[tuple(join[:2])]
    corridor(points,code,volumes)
    for u in (2.5,8.6):
        d=bpy.data.lights.new('V13 '+code+' entrance lighting','AREA');d.energy=150;d.shape='DISK';d.size=2.0;d.color=(1,.96,.85)
        ob=bpy.data.objects.new(d.name,d);H.col('Metro_Access_Lights').objects.link(ob);ob.location=(x+u,y,GROUND+2.8)
    H.R['entrances'].append({'exit':code,'top':[x,y,GROUND],'bottom':[end[0],end[1],B1],'steps':36,'rise':RISE,'tread':TREAD,'mid_landing':1.4,'width':3.0,'join_B1':list(join),'passage_waypoints':[list(p) for p in points],'stair_samples':samples,'placement':'approximate fit to inherited plaza and shifted Metro frame; topological connection, not surveyed coordinates'})

def cut_site(volumes):
    # Retain source objects; apply cuts to independent mesh copies. Cutting both
    # ground and plinth avoids a dark fake pit with solid display-base material.
    names=['Site ground','Display base','Studio floor','V4 north bus island','V4 west sidewalk','V4 unified perimeter and transport road','V3 connected Marunouchi perimeter street','V3 north street connection','V11 M17 B1 concourse roof and side walls']
    targets={}
    for name in names:
        o=bpy.data.objects.get(name)
        if o and not o.hide_render:targets[name]=o
    copied={};cuts=[]
    for F,c,size,label in volumes:
        b=L.MeshBuilder();H.box(b,c,size,'dark',F=F);cutter=H.build(b,'temporary opening '+label,'Work','temporary');cl,ch=H.bounds(cutter)
        for name,original in targets.items():
            lo,hi=H.bounds(original)
            if not np.all(hi>cl) or not np.all(lo<ch):continue
            q=copied.get(name)
            if q is None:q=H.copy_replace(original);copied[name]=q
            H.boolean_cut(q,cutter);cuts.append([name,label])
        bpy.data.objects.remove(cutter,do_unlink=True)
    H.R['metro_openings']=cuts

def run():
    volumes=[]
    # North bus-plaza side M8 and west pavement M7, within the model boundary.
    north=MF@Vector((-64,0,B1));west=MF@Vector((-16,-4.9,B1))
    entrance('M8',-143,-94,north,[(-130.72,-137.68)],volumes)
    entrance('M7',-33,-139,west,[],volumes)
    cut_site(volumes)
    H.R['metro_access_basis']={'official_diagram':'Tokyo Metro Tokyo station, 2026.4','modelled_ground_exits':['M7','M8'],'outside_scope':'Building-integrated exits M9/M10 and the full Marunouchi commercial underground network are not reconstructed. M10 is not mislabelled as a free-standing lift in this plaza.'}
