"""Tokyo Metro M17: an editable B2 island station and six-car 2000-series interpretation.
Official April 2026 station diagram supplies levels, track directions and three stair groups.
The station frame follows the existing GSI/OSM Marunouchi alignment; dimensions are estimates.
No overhead wire: the Marunouchi Line is represented with a covered third rail.
"""
import bpy,math,numpy as np
from mathutils import Vector,Matrix
import v11lib as H
L=H.L
ANGLE=math.atan2(24.0,116.0)
# A 7.35 m transverse shift from the former schematic line keeps the new station
# clear of the inherited Sobu B1/B2 end walls; the street-aligned bearing is retained.
F=Matrix.Translation((-5.5,-124.7,0))@Matrix.Rotation(ANGLE,4,'Z')
RAIL=-11.20;DECK=-10.15;B1=-5.80;CEIL=-7.00
EDGE=4.20;TRACK=5.85;HALF=8.20;PLEN=61.5
STAIRS=[(-38,1),(1,-1),(39,-1)]

def obj(mb,name,group,kind=None):return H.build(mb,'M17 '+name,'Metro_'+group,kind or 'metro_station',frame=F)
def floor_with_holes(mb,x0,x1,y0,y1,z,thick,holes,key):
    xx=sorted(set([x0,x1]+[max(x0,min(x1,v)) for h in holes for v in h[:2]]))
    yy=sorted(set([y0,y1]+[max(y0,min(y1,v)) for h in holes for v in h[2:]]))
    for a,b in zip(xx[:-1],xx[1:]):
        for c,d in zip(yy[:-1],yy[1:]):
            mx,my=(a+b)/2,(c+d)/2
            if any(h[0]-.001<mx<h[1]+.001 and h[2]-.001<my<h[3]+.001 for h in holes):continue
            H.box(mb,(mx,my,z-thick/2),(b-a,d-c,thick),key)

def station():
    old=bpy.data.objects.get('V9 context | Tokyo Metro Marunouchi Line tunnel crossing (simplified)')
    if old:H.retire(old)
    # The display base and studio backdrop are solid meshes. Create a real enclosed
    # cavity below the plaza, retaining both originals and the visible upper base skin.
    mb=L.MeshBuilder();H.box(mb,(0,4.5,-7.5),(156,29,11.2),'concrete')
    cutter=H.build(mb,'temporary underground void cutter','Metro_Work','temporary',frame=F)
    for name in ('Display base','Studio floor'):
        old=bpy.data.objects.get(name)
        if not old:continue
        new=H.copy_replace(old)
        mod=new.modifiers.new('M17 underground void','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
        bpy.context.view_layer.objects.active=new;new.select_set(True)
        bpy.ops.object.modifier_apply(modifier=mod.name);new.select_set(False)
        new['V11_kind']='underground_void';H.count('display_meshes_with_real_underground_void')
    bpy.data.objects.remove(cutter,do_unlink=True)
    H.mat('metro_red',(.69,.018,.034),.25,.25)
    H.mat('metro_seat',(.32,.035,.10),.8)
    H.mat('metro_tile',(.57,.58,.54),.35,noise=42)
    # Track bed, platform and the station's structural box are separate editable groups.
    mb=L.MeshBuilder();H.box(mb,(0,0,RAIL-.55),(151,2*HALF,1.1),'concrete')
    H.box(mb,(0,0,DECK-.42),(2*PLEN,EDGE*2,.84),'concrete')
    for x in np.arange(-PLEN,PLEN-.59,.60):
        for y in np.arange(-EDGE,EDGE-.59,.60):
            H.box(mb,(x+.295,y+.295,DECK+.014),(.589,.589,.028),'metro_tile')
    obj(mb,'platform slab and jointed tiles','Platform')
    mb=L.MeshBuilder()
    for s in (-1,1):
        yc=s*TRACK
        H.box(mb,(0,yc,RAIL-.25),(151,3.1,.22),'dark')
        for x in np.arange(-75,76,.65):
            H.box(mb,(x,yc,RAIL-.12),(.24,2.25,.17),'concrete')
            for y in (yc-.7175,yc+.7175):H.box(mb,(x,y,RAIL-.055),(.31,.21,.065),'dark')
        for dy in (-.7175,.7175):
            H.box(mb,(0,yc+dy,RAIL-.055),(151,.07,.11),'steel')
            H.box(mb,(0,yc+dy,RAIL-.125),(151,.13,.035),'steel')
        third=yc+s*1.12
        H.box(mb,(0,third,RAIL+.22),(151,.14,.09),'steel');H.box(mb,(0,third+s*.035,RAIL+.32),(151,.30,.045),'paint')
        for x in np.arange(-74,76,3):H.box(mb,(x,third,RAIL+.09),(.18,.22,.20),'white')
    obj(mb,'standard gauge rails sleepers and covered third rails','Track','metro_track')
    mb=L.MeshBuilder()
    for s in (-1,1):
        H.box(mb,(0,s*(HALF+.20),(RAIL-6.35)/2),(151,.40,-6.35-RAIL),'concrete')
        for x in np.arange(-74,75,1.25):
            H.box(mb,(x,s*(HALF-.035),-8.55),(1.23,.09,2.75),'white')
            H.box(mb,(x,s*(HALF-.095),-8.70),(1.25,.035,.25),'metro_red')
        for x in (-55,-30,-5,20,45):
            H.box(mb,(x,s*(HALF-.16),-8.55),(3.30,.06,.82),'white')
            H.text(mb,'東京  Tokyo',(x,s*(HALF-.20),-8.32),right=(-s,0,0),size=.28,key='dark')
            H.text(mb,'M17',(x,s*(HALF-.21),-8.73),right=(-s,0,0),size=.17,key='metro_red')
    obj(mb,'track walls with red band and station names','Walls')
    # B1 slab and B2 ceiling apertures align with all three stair / escalator banks.
    holes=[(-12.2,-9.8,-1.2,1.2)];ceilingholes=[(-12.2,-9.8,-1.2,1.2)]
    for x,s in STAIRS:
        a,b=sorted([x+s*3.0,x+s*9.0]);holes.append((a,b,-1.86,1.86))
        a,b=sorted([x+s*1.0,x+s*9.5]);ceilingholes.append((a,b,-1.95,1.95))
    mb=L.MeshBuilder();floor_with_holes(mb,-67,67,-HALF,HALF,B1,.35,holes,'concrete')
    floor_with_holes(mb,-PLEN,PLEN,-EDGE,EDGE,CEIL,.10,ceilingholes,'white')
    for s in (-1,1):H.box(mb,(0,s*TRACK,-6.45),(135,3.2,.15),'dark')
    obj(mb,'B1 slab and B2 ceilings with stair openings','Ceiling')
    mb=L.MeshBuilder()
    for x in np.arange(-58,61,6):
        if any(min(q,q+s*9)-1.2<x<max(q,q+s*9)+1.2 for q,s in STAIRS):continue
        for y in (-2.45,2.45):
            H.cyl(mb,(x,y,(DECK+CEIL)/2),.46,CEIL-DECK,'granite',32)
            H.cyl(mb,(x,y,DECK+.065),.48,.13,'dark',32)
            for s in (-1,1):
                H.box(mb,(x,y+s*.466,DECK+1.65),(.54,.025,.65),'white')
                H.box(mb,(x,y+s*.482,DECK+1.47),(.54,.015,.22),'metro_red')
                H.text(mb,'東京',(x,y+s*.494,DECK+1.79),right=(-s,0,0),size=.19,key='dark')
                H.text(mb,'M17',(x,y+s*.500,DECK+1.48),right=(-s,0,0),size=.14)
            H.count('metro_granite_columns')
    obj(mb,'round granite columns and M17 identification','Columns')
    stairs();screen_doors();concourse(holes);fixtures()
    # Two short tunnel extensions, with section ends intentionally open for inspection.
    mb=L.MeshBuilder()
    for s in (-1,1):
        H.box(mb,(s*69,0,-6.15),(15,2*HALF,.40),'concrete')
    obj(mb,'tunnel roof extensions','Ceiling')
    H.REPORT['marunouchi_station']={'platform_level':'B2','concourse_level':'B1','rail_z':RAIL,'platform_z':DECK,'concourse_z':B1,
        'platform_length':2*PLEN,'island_width':2*EDGE,'track_gauge':1.435,'stair_groups':3,'frame':[list(r) for r in F],
        'alignment_basis':'existing model Marunouchi bearing; axis shifted approximately 7.35 m west to clear inherited Sobu upper structures; station extent and cross-section estimated',
        'transfer_passages':'short schematic branches toward JR, not a survey of the entire underground pedestrian network'}

def stairs():
    mb=L.MeshBuilder();rise=(B1-DECK)/26;tread=.30
    for x,s in STAIRS:
        FF=Matrix.Translation((x,0,DECK))@Matrix.Rotation(0 if s>0 else math.pi,4,'Z')
        for k in range(26):
            u=(k+.5)*tread;h=(k+1)*rise
            H.box(mb,(u,-.68,h/2),(tread,1.75,h),'granite',F=FF)
            H.box(mb,(u-tread/2+.025,-.68,h+.012),(.05,1.73,.024),'yellow',F=FF)
        for y in (-1.62,.26):
            H.beam(mb,FF@Vector((0,y,.95)),FF@Vector((7.8,y,B1-DECK+.95)),.045,.045,'steel')
            for u in np.arange(.3,7.8,1.2):H.rod(mb,FF@Vector((u,y,u/7.8*(B1-DECK))),FF@Vector((u,y,u/7.8*(B1-DECK)+.95)),.025,'steel')
        # Parallel escalator with independent black handrails and metal treads.
        for k in range(36):
            u=k*7.8/36;h=u/7.8*(B1-DECK)
            H.box(mb,(u,.97,h+.06),(.23,1.0,.12),'steel',F=FF)
            H.box(mb,(u-.11,.97,h+.125),(.022,.98,.014),'yellow',F=FF)
        for y in (.40,1.54):
            H.beam(mb,FF@Vector((-.4,y,.7)),FF@Vector((8.3,y,B1-DECK+.7)),.10,.48,'glass')
            H.tube(mb,[FF@Vector((u,y,z)) for u,z in [(-.5,.95),(0,.95),(7.8,B1-DECK+.95),(8.6,B1-DECK+.95)]],.05,'rubber')
        for yy in (-1.8,1.8):
            H.beam(mb,FF@Vector((0,yy,.50)),FF@Vector((8.8,yy,B1-DECK+.50)),.10,1.0,'white')
        H.box(mb,(8.6,0,B1-DECK-.08),(1.5,3.6,.16),'floor',F=FF)
        H.count('metro_stair_escalator_banks')
    obj(mb,'three stair and escalator banks to B1','Stairs')
    # Glass lift tower on the platform, matching the central connection in the diagram.
    mb=L.MeshBuilder();x=-11
    for s in (-1,1):H.box(mb,(x+s*1.05,0,(DECK+B1)/2),(.08,2.2,B1-DECK),'steel')
    H.box(mb,(x,1.05,(DECK+B1)/2),(2.1,.08,B1-DECK),'glass')
    H.box(mb,(x,-1.05,DECK+1.1),(2.1,.07,2.2),'steel');H.box(mb,(x,-1.10,DECK+1.1),(.035,.02,2.1),'dark')
    H.text(mb,'エレベーター',(x,-1.12,DECK+2.4),size=.17,key='dark')
    obj(mb,'lift shaft and doors','Stairs');H.count('metro_lifts')

def screen_doors():
    mb=L.MeshBuilder();centres=[-45+18*i for i in range(6)];doors=[cx+d for cx in centres for d in (-5.4,0,5.4)]
    for s in (-1,1):
        y=s*(EDGE-.08);last=-PLEN
        for i,x in enumerate(doors):
            a=x-.75;b=x+.75
            H.box(mb,((last+a)/2,y,DECK+.58),(a-last,.18,1.16),'paint')
            for xx in (a,b):
                H.box(mb,(xx,y,DECK+.60),(.13,.28,1.20),'white')
                H.box(mb,(xx,y-s*.155,DECK+.65),(.09,.02,.96),'metro_red')
            for d in (-.365,.365):
                H.box(mb,(x+d,y,DECK+.55),(.72,.09,1.06),'steel')
                H.box(mb,(x+d,y-s*.053,DECK+.78),(.60,.018,.37),'paint')
            H.box(mb,(x,y-s*.13,DECK+1.17),(1.54,.16,.06),'steel')
            H.text(mb,str(i//3+1),(x+.55,y-s*.169,DECK+.87),right=(s,0,0),size=.10,key='dark')
            last=b;H.count('metro_platform_door_pairs')
        H.box(mb,((last+PLEN)/2,y,DECK+.58),(PLEN-last,.18,1.16),'paint')
        # Tactile slabs stop at platform edge; their studs are physical geometry.
        for x in np.arange(-PLEN,PLEN,.30):
            H.box(mb,(x,s*(EDGE-.64),DECK+.025),(.295,.58,.05),'yellow')
            for dx in (-.10,0,.10):
                for dy in (-.18,0,.18):H.cyl(mb,(x+dx,s*(EDGE-.64)+dy,DECK+.057),.022,.014,'yellow',6)
    obj(mb,'36 half height platform door pairs and tactile paving','Platform_Doors','metro_platform_doors')

def concourse(holes):
    mb=L.MeshBuilder();floor_with_holes(mb,-67,67,-6.3,6.3,B1+.025,.05,holes,'metro_tile')
    for x,s in STAIRS:
        a,b=sorted([x+s*3,x+s*9])
        for y in (-1.95,1.95):
            H.box(mb,((a+b)/2,y,B1+.48),(b-a,.06,.96),'glass')
            H.rod(mb,(a,y,B1+1.0),(b,y,B1+1.0),.035,'steel')
    for x in (-25,55):
        for y in np.arange(-4.7,5.0,1.0):
            H.box(mb,(x,y,B1+.48),(1.7,.36,.96),'paint')
            H.box(mb,(x-.56,y,B1+.98),(.34,.32,.07),'blue')
            H.box(mb,(x,y+.35,B1+.47),(.07,.32,.73),'glass')
        H.count('metro_ticket_gate_banks')
    # JR-bound branch passages are intentionally schematic and independently editable.
    for x in (-16,48):
        H.box(mb,(x,11.2,B1-.1),(5,10,.25),'concrete')
        H.box(mb,(x,11.2,B1+3.2),(5,10,.16),'white')
        for s in (-1,1):H.box(mb,(x+s*2.55,11.2,B1+1.5),(.16,10,3.2),'white')
        H.box(mb,(x,6.5,B1+2.5),(4.8,.16,.6),'yellow')
        H.text(mb,'JR線  のりかえ',(x,6.39,B1+2.5),size=.30,key='dark')
    obj(mb,'B1 concourse ticket gates balustrades and transfer branches','Concourse')
    mb=L.MeshBuilder();H.box(mb,(0,0,B1+3.4),(135,13.5,.30),'concrete')
    for s in (-1,1):
        for a,b in [(-67,-19),(-13,45),(51,67)]:H.box(mb,((a+b)/2,s*6.7,B1+1.6),(b-a,.25,3.2),'white')
    obj(mb,'B1 concourse roof and side walls','Ceiling')
    mb=L.MeshBuilder()
    for x in np.arange(-60,65,8):
        for y in (-3.8,3.8):H.box(mb,(x,y,B1+3.16),(4.0,.23,.045),'lamp')
    for x in (-22,51):
        H.box(mb,(x,0,B1+2.60),(.12,4.9,.56),'blue')
        for s in (-1,1):H.text(mb,'丸ノ内線   Marunouchi Line',(x+s*.073,0,B1+2.60),right=(0,s,0),size=.22)
    for x in (-40,-38.8,-37.6):
        H.box(mb,(x,5.8,B1+.78),(.95,.65,1.56),'paint')
        H.box(mb,(x,5.46,B1+1.1),(.63,.025,.42),'dark')
        H.box(mb,(x,5.43,B1+1.1),(.52,.014,.32),'blue')
        H.box(mb,(x,5.42,B1+.64),(.34,.03,.04),'dark')
    obj(mb,'B1 light panels direction signs and ticket machines','Concourse')

def fixtures():
    mb=L.MeshBuilder()
    for x in np.arange(-56,59,7):
        for y in (-3.1,3.1):
            H.box(mb,(x,y,CEIL-.07),(3.4,.29,.08),'white');H.box(mb,(x,y,CEIL-.12),(3.28,.20,.02),'lamp')
        for y in (-1.8,1.8):
            if any(min(q,q+s*10)-1<x<max(q,q+s*10)+1 for q,s in STAIRS):continue
            H.box(mb,(x,y,CEIL-.01),(1.4,.42,.055),'dark')
            for dx in np.arange(-.62,.65,.13):H.box(mb,(x+dx,y,CEIL-.05),(.035,.44,.04),'steel')
    for x in (-53,-21,22,56):
        H.box(mb,(x,0,DECK+2.5),(.13,3.7,.59),'blue')
        H.text(mb,'1  荻窪方面   2  池袋方面',(x-.08,0,DECK+2.5),right=(0,-1,0),size=.22)
        for y in (-1.5,1.5):H.rod(mb,(x,y,DECK+2.80),(x,y,CEIL),.017,'steel')
    for x in (-51,18,54):
        for y in (-.58,.58):
            H.box(mb,(x,y,DECK+.48),(2.5,.43,.12),'blue')
            H.box(mb,(x,y+(.20 if y>0 else -.20),DECK+.76),(2.5,.07,.46),'paint')
            for dx in (-.86,.86):H.box(mb,(x+dx,y,DECK+.23),(.08,.38,.46),'steel')
    obj(mb,'lights ventilation grilles signs and seating','Fixtures')
    for x in np.arange(-54,60,14):
        for y in (-2.2,2.2):
            p=F@Vector((x,y,CEIL-.21));H.light('M17 platform light',(p.x,p.y,p.z),420,5,(.90,.95,1.0),group='Metro_Lights')
        p=F@Vector((x,0,B1+3.12));H.light('M17 concourse light',p,600,6,(.95,.96,1.0),group='Metro_Lights')

def side_window(mb,x0,x1,y,z0,z1):
    H.box(mb,((x0+x1)/2,y,(z0+z1)/2),(x1-x0,.018,z1-z0),'window')
    for xx in (x0,x1):H.box(mb,(xx,y,.5*(z0+z1)),(.035,.042,z1-z0+.04),'rubber')
    for zz in (z0,z1):H.box(mb,((x0+x1)/2,y,zz),(x1-x0,.042,.035),'rubber')

def make_car(cab=False):
    mb=L.MeshBuilder();W=1.39
    H.box(mb,(0,0,1.02),(17.4,2.68,.15),'floor')
    H.box(mb,(0,0,.72),(16.9,2.1,.30),'dark')
    for s in (-1,1):
        y=s*W
        H.box(mb,(0,y,1.43),(17.4,.055,.75),'metro_red')
        H.box(mb,(0,y,3.13),(17.4,.055,.36),'metro_red')
        openings=[(-8.1,-7.1),(-6.05,-4.75),(-4.25,-1.15),(-.65,.65),(1.15,4.25),(4.75,6.05),(7.1,8.1)]
        last=-8.7
        for a,b in openings:
            if a>last:H.box(mb,((a+last)/2,y,2.375),(a-last,.055,1.15),'metro_red')
            last=b
        H.box(mb,((last+8.7)/2,y,2.375),(8.7-last,.055,1.15),'metro_red')
        for a,b in [(-4.25,-1.15),(1.15,4.25)]:side_window(mb,a,b,y+s*.008,1.84,2.91)
        for x in (-7.6,7.6):
            for z,h in [(1.85,.10),(2.925,.05)]:H.box(mb,(x,y,z),(1.0,.055,h),'metro_red')
            # A real circular window with a red annulus; no opaque wall behind the glass.
            pts=[]
            for t in np.linspace(0,math.tau,33)[:-1]:pts.append((x+.43*math.cos(t),y+s*.015,2.40+.43*math.sin(t)))
            mb.add(pts,[tuple(range(32))],H.I['window']);H.ring(mb,(x,y+s*.03,2.40),.445,.035,'white','XZ',40)
            for k in range(32):
                a=math.tau*k/32;b=math.tau*(k+1)/32
                def pp(t,r):return (x+r*math.cos(t),y,2.40+r*math.sin(t))
                def outer(t):return .5/max(abs(math.cos(t)),abs(math.sin(t)))
                mb.add([pp(a,.46),pp(b,.46),pp(b,outer(b)),pp(a,outer(a))],[(0,1,2,3)],H.I['metro_red'])
        for x in (-5.4,0,5.4):
            for d in (-.325,.325):
                H.box(mb,(x+d,y+s*.025,1.48),(.64,.035,.81),'metro_red')
                H.box(mb,(x+d,y+s*.025,2.97),(.64,.035,.12),'metro_red')
                side_window(mb,x+d-.23,x+d+.23,y+s*.027,1.99,2.83)
                for xx in (x+d-.30,x+d+.30):H.box(mb,(xx,y+s*.03,2.44),(.055,.035,1.08),'metro_red')
            H.box(mb,(x,y+s*.053,2.02),(.023,.018,1.90),'rubber')
            H.box(mb,(x,y+s*.04,1.09),(1.27,.10,.05),'steel')
        # High white sinusoidal band is visible above platform screens.
        H.tube(mb,[(x,y+s*.040,3.225+.055*math.sin(x*math.pi/1.15)) for x in np.linspace(-8.55,8.55,220)],.019,'white',5)
        H.box(mb,(2.7,y+s*.05,3.04),(1.05,.04,.21),'dark');H.text(mb,'荻窪',(2.7,y+s*.078,3.04),right=(-s,0,0),size=.15,key='led')
        # Interior seven-seat bench sections and visible yellow grab loops.
        for cx in (-2.7,2.7):
            for dx in np.arange(-1.32,1.33,.44):H.box(mb,(cx+dx,s*1.03,1.46),(.42,.51,.14),'metro_seat')
            H.box(mb,(cx,s*1.25,1.81),(3.06,.10,.62),'metro_seat')
            H.rod(mb,(cx-1.55,s*.78,1.1),(cx-1.55,s*.78,2.95),.022,'steel')
        H.rod(mb,(-8,s*.78,2.90),(8,s*.78,2.90),.022,'steel')
        for x in np.arange(-7.5,8,.75):
            H.rod(mb,(x,s*.78,2.9),(x,s*.78,2.64),.012,'steel');H.ring(mb,(x,s*.78,2.56),.075,.014,'yellow','YZ',12)
    # Shallow arched roof (no pantograph) and paired HVAC boxes.
    prof=[(-1.39,3.30),(-1.32,3.48),(-1.12,3.62),(-.75,3.69),(0,3.72),(.75,3.69),(1.12,3.62),(1.32,3.48),(1.39,3.30)]
    roofverts=[(x,y,z) for x in (-8.7,8.7) for y,z in prof];nr=len(prof)
    mb.add(roofverts,[(i,nr+i,nr+i+1,i+1) for i in range(nr-1)],H.I['metro_red'],smooth=True)
    for x in (-3.5,3.5):
        H.box(mb,(x,0,3.81),(2.7,1.82,.20),'steel')
        for dx in np.arange(-1.22,1.23,.12):H.box(mb,(x+dx,0,3.925),(.045,1.60,.025),'dark')
    H.box(mb,(0,0,3.29),(16.9,2.58,.07),'white')
    for y in (-.76,.76):H.box(mb,(0,y,3.22),(16.6,.12,.035),'lamp')
    for bx in (-5.8,5.8):
        H.box(mb,(bx,0,.63),(2.70,2.05,.22),'dark')
        for dx in (-.95,.95):
            for sy in (-1,1):
                wheelF=Matrix.Translation((bx+dx,sy*.7175,.38))@Matrix.Rotation(math.pi/2,4,'X')
                L.lathe(mb,[(.38,-.065),(.38,.065)],(0,0),24,H.I['steel'],cap_top=True,cap_bottom=True,frame=wheelF)
                hubF=Matrix.Translation((bx+dx,sy*.81,.38))@Matrix.Rotation(math.pi/2,4,'X')
                L.lathe(mb,[(.19,-.035),(.19,.035)],(0,0),20,H.I['dark'],cap_top=True,cap_bottom=True,frame=hubF)
                H.box(mb,(bx+dx,sy*1.05,.56),(.34,.23,.30),'dark')
        for sy in (-1,1):
            H.box(mb,(bx,sy*1.04,.75),(2.6,.14,.16),'dark')
            H.cyl(mb,(bx,sy*.94,.90),.22,.16,'rubber',16)
            H.box(mb,(bx,sy*1.37,.27),(.64,.25,.08),'steel')
        H.box(mb,(bx*.5,0,.52),(1.5,1.45,.40),'paint')
    for end in (-1,1):
        if end==1 and cab:continue
        H.box(mb,(end*8.71,0,2.25),(.055,2.68,2.38),'metro_red')
        for t in np.arange(-.15,.16,.06):
            H.box(mb,(end*(8.78+t),-.63,2.10),(.025,.07,1.95),'rubber');H.box(mb,(end*(8.78+t),.63,2.10),(.025,.07,1.95),'rubber')
            H.box(mb,(end*(8.78+t),0,3.06),(.025,1.3,.08),'rubber')
        H.box(mb,(end*8.95,0,.66),(.16,.32,.23),'dark')
    if cab:
        # Rounded front mask with broad curved black glazing and visible emergency door seam.
        outline=[(-1.25,.93),(-1.39,1.2),(-1.39,3.15),(-1.23,3.49),(-.80,3.67),(.80,3.67),(1.23,3.49),(1.39,3.15),(1.39,1.2),(1.25,.93)]
        pts=[(8.88,y,z) for y,z in outline];mb.add(pts,[tuple(range(len(pts)))],H.I['metro_red'])
        for i in range(len(outline)):
            a=outline[i];b=outline[(i+1)%len(outline)]
            mb.add([(8.60,*a),(8.88,*a),(8.88,*b),(8.60,*b)],[(0,1,2,3)],H.I['metro_red'])
        pp=[(8.905,1.23*math.cos(t),2.58+.99*math.sin(t)) for t in np.linspace(0,math.tau,49)[:-1]]
        mb.add(pp,[tuple(range(len(pp)))],H.I['window']);H.tube(mb,pp+[pp[0]],.035,'rubber')
        H.rod(mb,(8.94,-.36,1.75),(8.94,-.36,3.37),.025,'steel')
        H.tube(mb,[(8.945,y,z) for y,z in [(-.76,2.02),(-.76,3.22),(-.64,3.34),(-.18,3.34),(-.18,1.98),(-.76,2.02)]],.010,'steel',6)
        H.tube(mb,[(8.945,y,z) for y,z in [(-.03,2.03),(.91,2.03),(1.08,2.26),(1.08,2.96),(.90,3.10),(-.03,3.10),(-.03,2.03)]],.010,'steel',6)
        H.rod(mb,(8.93,-1.05,1.14),(8.93,1.05,1.14),.018,'red')
        H.box(mb,(8.90,0,.98),(.08,2.2,.09),'metro_red')
        H.rod(mb,(8.947,.12,1.78),(8.947,.53,2.45),.019,'dark')
        H.rod(mb,(8.953,.24,2.25),(8.953,.72,2.53),.014,'rubber')
        H.text(mb,'荻窪',(8.95,.12,3.24),right=(0,1,0),size=.22,key='led')
        for sy in (-1,1):
            H.rod(mb,(8.89,sy*.99,1.47),(8.96,sy*.99,1.47),.125,'dark',20)
            H.rod(mb,(8.96,sy*.99,1.47),(8.975,sy*.99,1.47),.069,'lamp',20)
        H.box(mb,(8.98,0,.68),(.38,.40,.30),'dark');H.box(mb,(9.18,0,.68),(.04,.25,.18),'steel')
    return mb

def trains():
    masters={}
    for cab in (False,True):
        mb=make_car(cab);o=mb.build('V11 2000 series '+('cab' if cab else 'intermediate')+' template',H.col('Metro_Train_Templates'),H.M)
        masters[cab]=o
    # Template collection is not linked to the scene; only the six transformed copies appear.
    tc=bpy.data.collections['V11_Metro_Train_Templates'];bpy.context.scene.collection.children.unlink(tc)
    H.REPORT['metro_cars']=[]
    for i,x in enumerate([-45,-27,-9,9,27,45]):
        cab=i in (0,5);o=masters[cab].copy();o.data=masters[cab].data
        H.col('Metro_Trains').objects.link(o);o.name=f'V11 Marunouchi 2000 series car {i+1:02d}'
        FF=F@Matrix.Translation((x,TRACK,RAIL))@Matrix.Rotation(math.pi if i==0 else 0,4,'Z');o.matrix_world=FF
        o['V11_kind']='metro_train';o['car_number']=6-i;o['third_rail_supply']=True
        mb=L.MeshBuilder()
        for s in (-1,1):H.text(mb,str(6-i)+'号車',(6.8,s*1.435,1.65),right=(-s,0,0),size=.14,key='white')
        H.build(mb,f'2000 series car {i+1} numbers','Metro_Trains','metro_train_markings',frame=FF)
        H.REPORT['metro_cars'].append({'car':6-i,'centre_x':x,'track':1,'cab':cab,'body_width':2.78,'pitch':18.0,'roof_equipment_top_above_rail':3.94})
    H.count('marunouchi_2000_cars',6)

def review():
    def wp(p):return F@Vector(p)
    H.camera('10 Marunouchi platform',wp((-49,-.8,DECK+1.7)),wp((-17,0,DECK+1.65)),26)
    H.camera('11 Marunouchi 2000 cab',wp((59,3.35,RAIL+2.8)),wp((53.3,TRACK,RAIL+2.15)),34)
    H.camera('12 Marunouchi B1 concourse',wp((-8,-4.5,B1+1.65)),wp((-24,-.5,B1+1.3)),24)
    cam=H.camera('13 Marunouchi cutaway',wp((105,-86,38)),wp((0,1,-8)),45,ortho=165)
    scene=bpy.data.scenes.new('V11 Marunouchi cutaway')
    for name in ['Platform','Track','Columns','Stairs','Platform_Doors','Fixtures','Trains','Lights']:
        c=bpy.data.collections.get('V11_Metro_'+name)
        if c:scene.collection.children.link(c)
    scene.collection.objects.link(cam);scene.camera=cam;scene.world=bpy.context.scene.world
    scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
    scene.view_settings.view_transform='AgX';scene['description']='B2 inspection cutaway: B1 concourse, walls and ceiling omitted; the full station remains in the main scene.'
    # Dedicated studio lights, not projected into the main station.
    for p,power,size in [((0,0,45),4500,60),((-60,-30,25),3000,45)]:
        d=bpy.data.lights.new('M17 cutaway softbox','AREA');d.energy=power;d.size=size
        o=bpy.data.objects.new('M17 cutaway softbox',d);scene.collection.objects.link(o);o.location=wp(p)
        o.rotation_euler=(wp((0,0,-8))-o.location).to_track_quat('-Z','Y').to_euler()
    # A single linked cab-car mesh in a separate studio makes bogies and circular
    # end windows inspectable without the platform screens hiding the lower body.
    study=bpy.data.scenes.new('V11 2000 series vehicle study');study.world=H.SC.world
    source=bpy.data.objects['V11 Marunouchi 2000 series car 06'];copy=source.copy();copy.data=source.data
    copy.name='V11 2000 cab isolated linked study';copy.matrix_world=Matrix.Identity(4);study.collection.objects.link(copy)
    ca=H.camera('14 2000 series vehicle study',(22,-19,10),(1.0,0,1.8),48,ortho=26)
    study.collection.objects.link(ca);study.camera=ca
    study.render.engine='CYCLES';study.cycles.samples=48;study.cycles.use_denoising=True;study.view_settings.view_transform='AgX'
    for pos,power,size in [((4,-8,13),1600,9),((-9,4,10),1200,8)]:
        d=bpy.data.lights.new('2000 study softbox','AREA');d.energy=power;d.size=size
        o=bpy.data.objects.new('2000 study softbox',d);study.collection.objects.link(o);o.location=pos
        o.rotation_euler=(Vector((0,0,1.5))-o.location).to_track_quat('-Z','Y').to_euler()

def run():
    station();trains();review();print('V11_MARUNOUCHI_OK',flush=True)
