"""Photo-informed passenger fittings, fitted to the retained model's car envelopes.

All new seating, handrails and panels are native procedural geometry. Dimensions are
visual approximations, not manufacturer drawings or a claim of exact seat capacity.
"""
import bpy, math
from mathutils import Vector,Matrix
import v5lib as L
import v12lib as H

def glazing_rects(body):
    out=[]
    for p in body.data.polygons:
        name=body.data.materials[p.material_index].name.lower()
        if not any(k in name for k in ('glazing','glass')):continue
        vs=[v.co for i in p.vertices for v in [body.data.vertices[i]]]
        if abs(p.normal.y)<.85 or abs(p.center.y)<1.25:continue
        a,c=min(v.x for v in vs),max(v.x for v in vs);d,e=min(v.z for v in vs),max(v.z for v in vs)
        if c-a>.12 and e-d>.2:out.append((a,c,d,e,1 if p.center.y>0 else -1,float(p.center.y)))
    return out

def bench(b,detail,a,c,side,family,priority=False):
    n=7 if c-a>2.6 else max(1,round((c-a)/.46));pitch=(c-a)/n
    back='priority_back' if priority else family+'_back';cush='priority_cushion' if priority else family+'_cushion'
    H.box(detail,((a+c)/2,side*1.12,1.43),(c-a,.46,.17),'dark')
    for j in range(n):
        x=a+(j+.5)*pitch;w=pitch-.012
        H.box(b,(x,side*1.105,1.60),(w,.47,.15),cush)
        # Slight recline: a separate padded back with a narrow lower lumbar roll.
        yz=[(1.22,1.65),(1.34,1.65),(1.39,2.13),(1.32,2.18),(1.26,2.13),(1.20,1.76)]
        vs=[(xx,side*y,z) for xx in (x-w/2,x+w/2) for y,z in yz];m=len(yz)
        fs=[tuple(range(m-1,-1,-1)),tuple(range(m,2*m))]+[(i,(i+1)%m,(i+1)%m+m,i+m) for i in range(m)]
        b.add(vs,fs,H.I[back])
        if j<n-1:H.rod(detail,(x+pitch/2,side*.94,1.66),(x+pitch/2,side*1.27,1.75),.008,'dark')
    # Moulded end partitions with curved/swept grab poles.
    for x in (a-.025,c+.025):
        yz=[(.72,1.42),(1.38,1.42),(1.38,2.37),(1.20,2.37),(.77,2.12),(.72,1.95)]
        vs=[(xx,side*y,z) for xx in (x-.025,x+.025) for y,z in yz];m=len(yz)
        detail.add(vs,[tuple(range(m-1,-1,-1)),tuple(range(m,2*m))]+[(i,(i+1)%m,(i+1)%m+m,i+m) for i in range(m)],H.I['pink' if priority and family=='yamanote' else 'white'])
        H.tube(detail,[(x,side*.74,1.73),(x,side*.66,1.90),(x,side*.67,2.38),(x,side*.77,2.72),(x,side*.80,3.10)],.017,'steel',10)
    if n>=6:
        for j in (2,5):
            x=a+j*pitch
            H.tube(detail,[(x,side*.91,1.68),(x,side*.72,1.80),(x,side*.74,2.50),(x,side*.80,3.10)],.016,'steel',10)
    return n

def recliner(b,d,x,y,z,key='green_blue',width=.45,F=None,head=True):
    T=(F or Matrix.Identity(4))@Matrix.Translation((x,y,z))
    def box(c,sz,k):H.box(b,c,sz,k,T)
    box((0,0,.46),(.48,width,.15),key)
    # Upholstered back / headrest / contrasting moulded rear shell.
    B=T@Matrix.Translation((-.23,0,.84))@Matrix.Rotation(-.10,4,'Y')
    H.box(b,(0,0,0),(.13,width,.67),key,B)
    if key=='chuo_green':H.box(b,(.073,0,.13),(.016,width-.012,.43),'green_grey',B)
    H.box(d,(-.08,0,-.02),(.035,width-.025,.54),'tray',B)
    if head:box((-.22,0,1.10),(.15,width*.82,.25),'white')
    for s in (-1,1):box((.015,s*(width/2+.012),.65),(.42,.055,.065),'grey')
    H.box(d,(0,0,.19),(.13,width*.64,.38),'dark',T)
    H.box(d,(-.327,0,.84),(.018,width*.76,.24),'tray',T)
    H.box(d,(-.342,0,.66),(.025,width*.65,.04),'dark',T)

def ordinary(col,body,family,cab=False,semi=False):
    b=L.MeshBuilder();d=L.MeshBuilder();seats=L.MeshBuilder()
    x0=-9.70;x1=7.58 if cab else 9.70;doors=[-6.7,-2.3,2.3,6.7];wins=glazing_rects(body)
    H.box(b,((x0+x1)/2,0,1.115),(x1-x0,2.77,.06),'floor_e235' if family=='yamanote' else 'floor_e233')
    for side in (-1,1):
        holes=[(a-.012,c+.012,z-.012,t+.012) for a,c,z,t,s,y in wins if s==side and a<x1 and c>x0]
        H.wall_with_holes(b,x0,x1,1.15,3.22,side*1.395,holes)
        for dc in doors:
            # On the inside the stainless exterior is backed by white laminated leaves.
            h=[h for h in holes if dc-.67<h[0]<dc+.67]
            H.wall_with_holes(b,dc-.635,dc+.635,1.16,3.19,side*1.388,h,'white')
            H.box(d,(dc,side*1.382,2.16),(.017,.014,2.0),'rubber')
            for xx in (dc-.64,dc+.64):H.box(d,(xx,side*1.375,2.16),(.024,.022,2.0),'steel')
            H.box(b,(dc,side*1.14,1.151),(1.30,.46,.012),'yellow')
            for dy in (-.10,0,.10):H.box(d,(dc,side*(1.12+dy),1.159),(1.25,.012,.007),'grey')
            for xx in (dc-.16,dc+.16):
                H.box(d,(xx,side*1.369,2.17),(.18,.012,.09),'white')
                H.text(d,'注意',(xx,side*1.360,2.17),right=(-side,0,0),size=.045,k='red')
            # Family-specific display arrangement: LED on -3000, twin LCD on 0/1000.
            if family=='tokaido':
                H.box(d,(dc,side*1.31,3.30),(.93,.10,.18),'black')
                H.text(d,'東京  TOKYO',(dc,side*1.252,3.30),right=(-side,0,0),size=.082,k='led')
            else:
                for off in (-.31,.31):
                    H.box(d,(dc+off,side*1.31,3.30),(.56,.10,.27),'black')
                    H.box(d,(dc+off,side*1.253,3.30),(.50,.01,.21),'screen')
                    H.text(d,'東京' if off<0 else 'TOKYO',(dc+off,side*1.245,3.32),right=(-side,0,0),size=.065,k='white')
                    H.box(d,(dc+off,side*1.244,3.25),(.44,.006,.018),{'chuo':'orange','keihin':'blue','yamanote':'green'}[family])
            if family in ('chuo','tokaido'):
                H.box(d,(dc+.79,side*1.36,2.17),(.11,.03,.20),'grey')
                for dz,k in ((-.045,'green'),(.045,'orange')):H.box(d,(dc+.79,side*1.34,2.17+dz),(.065,.016,.052),k)
        # Split lining under the curved shoulder instead of a box ceiling.
        b.add([(x0,side*1.395,3.22),(x1,side*1.395,3.22),(x1,side*.78,3.58),(x0,side*.78,3.58)],[(0,1,2,3)],H.I['ceiling'])
        H.rod(d,(x0+.15,side*.79,3.08),(x1-.18,side*.79,3.08),.021,'steel',12)
        for yy in (.97,1.06,1.15,1.24,1.33):H.rod(d,(x0+.2,side*yy,2.97),(x1-.2,side*yy,2.97),.010,'steel')
        for q in range(int((x1-x0)/.72)):
            x=x0+.30+q*.72
            H.rod(d,(x,side*.93,2.97),(x,side*1.37,2.97),.012,'steel')
        for q in range(int((x1-x0)/.45)):
            x=x0+.32+q*.45;k='orange' if x<-7.5 else 'green' if family=='yamanote' else 'black'
            H.box(d,(x,side*.79,2.91),(.036,.032,.33),k)
            H.tube(d,[(x,side*.79,2.76),(x-.115,side*.79,2.58),(x+.115,side*.79,2.58),(x,side*.79,2.76)],.015,k,10)
        H.box(b,((x0+x1)/2,side*.73,3.56),(x1-x0-.25,.105,.025),'lamp')
    H.box(b,((x0+x1)/2,0,3.605),(x1-x0,1.57,.035),'ceiling')
    for x in (-7,-3,1,5):
        H.box(d,(x,0,3.565),(1.05,.36,.035),'grey')
        for j in range(9):H.box(d,(x,(-4+j)*.036,3.542),(.96,.012,.012),'dark')
    bays=[(x0+.10,-7.44),(-5.96,-3.04),(-1.56,1.56),(3.04,5.96)]
    if not cab:bays.append((7.44,x1-.10))
    n=0
    for side in (-1,1):
        for a,c in bays:
            if semi and -6<a<4:
                # 2+2 facing bays in the selected near-suburban cab templates.
                for x,angle in ((a+.44,0),(c-.44,math.pi)):
                    F=Matrix.Translation((x,side*.85,1.15))@Matrix.Rotation(angle,4,'Z')
                    for yy in (-.24,.24):recliner(seats,d,0,yy,0,'tokaido_cushion',.43,F,False);n+=1
            elif not cab and a>7 and side==1:
                H.rod(d,(a,side*1.32,2.05),(c,side*1.32,2.05),.025,'steel')
                H.box(d,((a+c)/2,side*1.35,1.91),(c-a,.06,.24),'white')
                H.text(d,'FREE SPACE',((a+c)/2,side*1.31,2.36),right=(-side,0,0),size=.10,k='blue')
            else:n+=bench(seats,d,a,c,side,family,a<-7)
    # End doors, glazing and recessed handles. Passenger volume remains inside the body.
    for x in (x0-.015,x1+.015):
        for side in (-1,1):H.box(b,(x,side*.87,2.20),(.04,1.03,2.10),'white')
        H.box(b,(x,0,1.70),(.04,.70,1.10),'white');H.box(b,(x,0,3.27),(.04,.70,.28),'white')
        H.box(b,(x,0,2.68),(.012,.66,.83),'glass')
        H.rod(d,(x-.028,.25,2.17),(x-.028,.25,2.47),.014,'steel')
    H.text(d,'優先席  PRIORITY SEAT',(-8.55,-1.377,2.35),size=.085,k='red')
    H.box(d,(-7.55,-1.36,2.46),(.14,.025,.22),'red');H.text(d,'SOS',(-7.55,-1.34,2.46),size=.055,k='white')
    if family=='yamanote':
        for side in (-1,1):
            for cx in (-4.5,0,4.5):
                for dx in (-.65,0,.65):
                    H.box(d,(cx+dx,side*1.19,3.36),(.58,.05,.25),'black')
                    H.box(d,(cx+dx,side*1.155,3.36),(.52,.012,.20),'screen')
                    H.text(d,'JR EAST',(cx+dx,side*1.146,3.36),right=(-side,0,0),size=.055,k='white')
    H.build(b,family+' passenger lining | '+col.name,col,'interior_lining')
    o=H.build(seats,family+' individual seats | '+col.name,col,'passenger_seats',.012);o['V12_family']=family;o['V12_seats']=n
    H.build(d,family+' rails displays and fittings | '+col.name,col,'interior_fittings',.003)
    return {'family':family,'seats':n,'semi_cross':semi,'window_apertures':len(wins)}

def green(col,chuo=False):
    b=L.MeshBuilder();d=L.MeshBuilder();seats=L.MeshBuilder()
    lo,up=.46,2.30 if chuo else 2.17;half=4.80 if chuo else 4.20;nrows=10 if chuo else 9;pitch=2*half/nrows
    for floor,key in ((lo,'chuo_green' if chuo else 'green_red'),(up,'chuo_green' if chuo else 'green_blue')):
        H.box(b,(0,0,floor-.04),(2*half,2.34 if not chuo and floor==lo else 2.72,.08),'floor_green')
        if chuo and floor==up:H.box(b,(0,0,floor+.005),(2*half,.55,.01),'green_aisle')
        for j in range(nrows):
            x=-half+(j+.5)*pitch
            for y in (-1.04,-.54,.54,1.04):recliner(seats,d,x,y,floor,key,.43)
            for s in (-1,1):
                H.box(d,(x,s*1.13,floor+1.40),(.17,.07,.09),'grey')
                H.box(d,(x,s*1.08,floor+1.40),(.04,.02,.025),'red' if j%3 else 'green')
        ceil=1.70 if chuo else 1.54 if floor==up else 1.64
        cw=1.68 if not chuo and floor==up else 2.68
        H.box(b,(0,0,floor+ceil),(2*half,cw,.055),'ceiling')
        for s in (-1,1):
            H.box(b,(0,s*.72,floor+ceil-.035),(2*half-.15,.08,.018),'lamp')
            H.rod(d,(-half,s*1.24,floor+1.48),(half,s*1.24,floor+1.48),.02,'steel')
            if not chuo and floor==up:
                b.add([(-half,s*.84,3.71),(half,s*.84,3.71),(half,s*1.28,3.55),(-half,s*1.28,3.55)],[(0,1,2,3)],H.I['ceiling'])
    # End vestibules and half-level stairs occupy the retained envelope.
    for side in (-1,1):
        H.box(b,(side*(half+1.2),0,1.12),(2.35,2.70,.07),'floor_e233')
        for level in (lo,up):
            for j in range(6):
                x=side*(half+.15+j*.18);z=level+(1.15-level)*(j+1)/6
                H.box(d,(x,-.78,z-.035),(.19,.60,.07),'grey')
                H.box(d,(x,-.78,z+.003),(.015,.57,.008),'yellow')
            H.rod(d,(side*(half+.1),-.43,level+.84),(side*(half+1.12),-.43,1.99),.022,'steel')
        H.box(b,(side*9.6,0,2.27),(.045,2.70,2.25),'white')
        for x in (side*8.0,side*8.94):
            for y in (-1.04,-.54,.54,1.04):recliner(seats,d,x,y,1.15,'chuo_green' if chuo else 'green_red',.43)
        H.box(b,(side*8.4,0,1.11),(2.45,2.70,.08),'floor_green')
    for s in (-1,1):
        # Horizontal lining bands leave both levels of side glazing open.
        for z,sz in ((.72,.40),(2.12,.23),(3.96,.18)) if chuo else ((.72,.36),(2.12,.18),(3.55,.08)):
            y=1.37 if chuo or z==2.12 else 1.18 if z<1 else 1.27
            H.box(b,(0,s*y,z),(2*half,.05,sz),'white')
    H.build(b,'Green car two decks | '+col.name,col,'green_lining')
    o=H.build(seats,'Green car reclining seats | '+col.name,col,'green_seats',.018);o['V12_seats']=nrows*8+16
    H.build(d,'Green car stairs trays and readers | '+col.name,col,'green_fittings',.004)
    return {'decks':2,'seats':nrows*8+16,'chuo':chuo,'approximation':'seat rows fitted to retained/modelled shell; not certified capacity'}

def e5(col,body,car):
    b=L.MeshBuilder();d=L.MeshBuilder();seats=L.MeshBuilder();ws=glazing_rects(body)
    xs=sorted(set(round((a+c)/2,3) for a,c,z,t,s,y in ws if t-z>.35 and c-a<1.0))
    if not xs:return {'seats':0}
    lo=min(xs)-.5;hi=max(xs)+.5;floor=1.40
    H.box(b,((lo+hi)/2,0,floor-.035),(hi-lo,3.10,.07),'floor_green')
    key='gran_seat' if car==10 else 'e5_green' if car==9 else 'e5_seat'
    ys=(-1.04,.45,1.04) if car==10 else (-1.04,-.52,.52,1.04) if car==9 else (-1.18,-.67,-.16,.62,1.15)
    nrows=6 if car in (1,10) else 14 if car==9 else len(xs)
    rows=[lo+.55+(hi-lo-1.10)*j/max(1,nrows-1) for j in range(nrows)]
    for x in rows:
        for y in ys:recliner(seats,d,x,y,floor,key,.52 if car==10 else .45,head=True)
    for s in (-1,1):
        holes=[(a-.02,c+.02,z-.02,t+.02) for a,c,z,t,ss,y in ws if ss==s]
        H.wall_with_holes(b,lo,hi,floor,3.30,s*1.59,holes)
        b.add([(lo,s*1.59,3.30),(hi,s*1.59,3.30),(hi,s*.76,3.52),(lo,s*.76,3.52)],[(0,1,2,3)],H.I['ceiling'])
        H.box(b,((lo+hi)/2,s*.94,3.38),(hi-lo,.25,.06),'ceiling')
        H.box(b,((lo+hi)/2,s*.76,3.34),(hi-lo,.06,.02),'lamp')
    H.box(b,((lo+hi)/2,0,3.52),(hi-lo,1.52,.06),'ceiling')
    H.build(b,'E5 passenger lining '+str(car),col,'e5_lining');H.build(seats,'E5 seats '+str(car),col,'e5_seats',.014);H.build(d,'E5 seatback trays '+str(car),col,'e5_fittings',.003)
    return {'seats':len(rows)*len(ys),'seat_class':'GranClass' if car==10 else 'Green' if car==9 else 'ordinary'}
