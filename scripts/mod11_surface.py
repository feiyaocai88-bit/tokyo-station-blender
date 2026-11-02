"""V11: real platform recesses, differentiated column sections, plaza and facade detail.
Photographic interpretation. All replaced meshes are retained in V11_Replaced_hidden.
"""
import bpy,math,json,re,numpy as np
from mathutils import Vector,Matrix
import v11lib as H
L=H.L

def platform_undercrofts():
    H.REPORT['platform_recesses']={}
    for isl in H.D['islands']:
        o=bpy.data.objects[f'V3 Platform {isl} raised deck'];v=H.world(o);zt=float(v[:,2].max());zb=float(v[:,2].min())
        # Compress only the deck copy: stair apertures and the exact walking surface remain.
        new=H.copy_replace(o);inv=new.matrix_world.inverted()
        for vert,p in zip(new.data.vertices,v):
            q=Vector((p[0],p[1],zt-(zt-p[2])*.23/(zt-zb)));vert.co=inv@q
        new['V11_kind']='platform_deck';new['island']=isl
        a,b=isl.split('-');x0=float(v[:,0].min());x1=float(v[:,0].max());edge=H.D['islands'][isl]['edge']
        mb=L.MeshBuilder();detail=L.MeshBuilder();npier=0;length=0
        xs=np.linspace(x0,x1,int(math.ceil((x1-x0)/2))+1)
        for xa,xb in zip(xs[:-1],xs[1:]):
            xm=(xa+xb)/2;w=float(H.ty(a,xm)+edge);e=float(H.ty(b,xm)-edge)
            if e-w<2.0:continue
            # Inboard longitudinal wall leaves a genuine 0.72 m-wide refuge / service recess.
            # Broad gaps around stairwells keep every lower stair flight unobstructed.
            c=(w+e)/2
            if H.free_stair(isl,xm,c,1.6):
                H.box(mb,(xm,c,zt-.88),(xb-xa+.015,e-w-1.44,1.30),'concrete')
            for s,y in [(-1,w),(1,e)]:
                yy=y-s*.67
                H.box(detail,(xm,yy,zt-.57),(xb-xa+.01,.12,.10),'dark')
                H.box(detail,(xm,yy,zt-.71),(xb-xa+.01,.10,.08),'steel')
                # Fascia is a thin bearing slab, with visible individual edge units.
                H.box(detail,(xm,y-s*.035,zt-.13),(xb-xa-.018,.07,.22),'paint')
                length+=xb-xa
        for x in np.arange(x0+1.5,x1-1.5,3.6):
            w=float(H.ty(a,x)+edge);e=float(H.ty(b,x)-edge)
            if e-w<2:continue
            for s,y in [(-1,w),(1,e)]:
                yy=y-s*.47
                if not H.free_stair(isl,x,yy,.15):continue
                H.box(mb,(x,yy,zt-.76),(.30,.42,1.04),'concrete');npier+=1
                H.beam(detail,(x,y-s*.08,zt-.27),(x,y-s*.70,zt-.75),.14,.12,'steel')
                for dz in (.36,.62):H.box(detail,(x,yy,zt-dz),(.07,.55,.055),'steel')
        H.build(mb,isl+' recessed platform core and piers','Platform_Undercrofts','undercroft',island=isl)
        H.build(detail,isl+' open edge service recess and brackets','Platform_Undercrofts','undercroft_detail',island=isl)
        H.REPORT['platform_recesses'][isl]={'deck_top':zt,'slab_thickness':.23,'recess_width':.72,'support_piers':npier,'edge_length':round(length,1)}
        H.count('platforms_with_real_edge_recess');H.count('under_platform_piers',npier)
    print('V11_PLATFORM_RECESSES_OK',flush=True)

def column_guards(mb,x,y,z,w=.42,d=.42):
    for s in (-1,1):
        H.box(mb,(x,y+s*(d/2+.012),z+1.45),(w,.025,.55),'red')
        # Diagonal white bands, clipped to the guard-panel rectangle.
        for xbase in np.arange(-w/2-.55,w/2,.17):
            p=[(xbase,-.275),(xbase+.07,-.275),(xbase+.62,.275),(xbase+.55,.275)]
            def clip(poly,edge,greater):
                out=[]
                for A,B in zip(poly,poly[1:]+poly[:1]):
                    ai=A[0]>=edge if greater else A[0]<=edge;bi=B[0]>=edge if greater else B[0]<=edge
                    if ai:out.append(A)
                    if ai!=bi:
                        t=(edge-A[0])/(B[0]-A[0]);out.append((edge,A[1]+t*(B[1]-A[1])))
                return out
            p=clip(clip(p,-w/2,True),w/2,False)
            if len(p)>=3:mb.add([(x+a,y+s*(d/2+.027),z+1.45+b) for a,b in p],[tuple(range(len(p)))],H.I['white'])

def column_detail(mb,x,y,z0,z1,style,num):
    H.box(mb,(x,y,z0+.045),(.62,.62,.09),'steel')
    for dx in (-.23,.23):
        for dy in (-.23,.23):H.cyl(mb,(x+dx,y+dy,z0+.11),.035,.05,'steel',6)
    if style=='round':
        H.cyl(mb,(x,y,(z0+z1)/2),.18,z1-z0,'cream',20)
        for zz in (z0+.16,z1-.12):H.cyl(mb,(x,y,zz),.25,.10,'cream',20)
    elif style=='paired_channel':
        for dx in (-.15,.15):H.hcolumn(mb,x+dx,y,z0+.09,z1,.19,.28,'cream')
        for zz in np.arange(z0+.3,z1-.1,.56):H.box(mb,(x,y,zz),(.44,.08,.10),'cream')
    else:H.hcolumn(mb,x,y,z0+.09,z1,.40,.38,'white' if style=='modern' else 'cream')
    for s in (-1,1):H.beam(mb,(x,y+s*.17,z1-.85),(x,y+s*.80,z1+.08),.11,.10,'cream')
    column_guards(mb,x,y,z0,.43,.40)
    H.box(mb,(x,y-.232,z0+2.1),(.30,.035,.36),'blue');H.text(mb,str(num),(x,y-.256,z0+2.1),size=.23)
    H.rod(mb,(x+.26,y+.25,z0+.15),(x+.26,y+.25,z1),.048,'paint',10)
    for zz in np.arange(z0+.4,z1,.8):H.ring(mb,(x+.26,y+.25,zz),.059,.014,'steel',n=12)

def columns():
    styles={'01-02':'modern','03-04':'round','05-06':'modern','07-08':'paired_channel','09-10':'portal_pair'}
    H.REPORT['columns']={}
    for isl,style in styles.items():
        old=bpy.data.objects[f'V8 canopy {isl} | columns'];shafts=[]
        for lo,hi in H.components(old):
            if hi[2]-lo[2]>2.5 and .40<hi[0]-lo[0]<.7 and .4<hi[1]-lo[1]<.7:shafts.append((lo,hi))
        H.retire(old);mb=L.MeshBuilder();n=0
        for ix,(lo,hi) in enumerate(sorted(shafts,key=lambda p:p[0][0])):
            x,y=(lo[:2]+hi[:2])/2;z0=lo[2];z1=hi[2]
            pair=style=='portal_pair' and all(H.free_stair(isl,x,y+s*.85,.25) for s in (-1,1))
            offsets=(-.85,.85) if pair else (0,)
            for dy in offsets:column_detail(mb,x,y+dy,z0,z1,style,ix+1);n+=1
            if pair:
                H.beam(mb,(x,y-1.12,z1+.05),(x,y+1.12,z1+.05),.30,.35,'cream')
                for t in np.arange(-.9,.91,.24):
                    H.rod(mb,(x-.17,y+t,z1-.08),(x-.17,y+t,z1+.18),.022,'steel',6)
        H.build(mb,isl+' '+style+' canopy columns','Platform_Columns','platform_column',island=isl)
        H.REPORT['columns'][isl]={'section':style,'count':n};H.count('differentiated_columns',n)
    # The Shinkansen roof objects contain both beams and columns: retain their structure,
    # give the supports distinct section jackets / capitals and numbered service panels.
    for isl in ['14-15','16-17','18-19','20-21','22-23']:
        o=bpy.data.objects.get(f'V10 {isl} retained steel and lights')
        if not o:continue
        # V10 copied individual faces, so topological connected components are faces,
        # not whole columns. Use the retained source's explicit structural schedule.
        meta=json.loads(H.SC['V5_shinkansen_roofs'])[isl]
        shafts=[(np.array([x-.25,y-.25,meta['z_deck']]),np.array([x+.25,y+.25,meta['z_girder_underside']-.30])) for x,y in meta['columns'] if H.free_stair(isl,x,y,.4)]
        mb=L.MeshBuilder();count=0
        for i,(lo,hi) in enumerate(shafts):
            x,y=(lo[:2]+hi[:2])/2;z0,z1=lo[2],hi[2]
            if isl in ['18-19']:
                H.cyl(mb,(x,y,(z0+z1)/2),max(hi[0]-lo[0],hi[1]-lo[1])*.55,z1-z0,'white',20)
            else:H.box(mb,(x,y,(z0+z1)/2),(max(.49,hi[0]-lo[0]+.04),max(.49,hi[1]-lo[1]+.04),z1-z0),'white')
            H.box(mb,(x,y,z0+.1),(.72,.72,.20),'concrete')
            H.box(mb,(x,y,z1-.15),(.78,.66,.22),'cream')
            if isl in ['20-21','22-23']:
                # Polished dark stone insert and stainless corner strips seen in 2021 photo.
                for s in (-1,1):
                    H.box(mb,(x,y+s*.285,z0+2.1),(.43,.025,4.0),'dark')
                    for dx in (-.25,.25):H.box(mb,(x+dx,y+s*.30,z0+2.1),(.04,.04,4.0),'steel')
                    H.box(mb,(x,y+s*.31,z0+1.7),(.29,.025,.65),'white')
                    H.text(mb,'非常停止',(x,y+s*.33,z0+1.9),right=(-s,0,0),size=.09,key='red')
            else:column_guards(mb,x,y,z0,.51,.51)
            count+=1
        H.build(mb,isl+' Shinkansen column finishes','Platform_Columns','platform_column',island=isl)
        H.REPORT['columns'][isl]={'section':'circular_jacket' if isl=='18-19' else 'stone_stainless_jacket' if isl in ['20-21','22-23'] else 'box_jacket','count':count}
        H.count('differentiated_columns',count)
    # Two conserved cast-iron columns, rather than repeating historic columns throughout 5/6.
    mb=L.MeshBuilder();y=float(H.yc('05-06',138))
    for x in (136,140):
        H.box(mb,(x,y,6.32),(.8,.8,.22),'granite')
        prof=[(.29,6.43),(.29,6.63),(.22,6.78),(.17,8.6),(.22,8.75),(.40,8.88),(.40,9.05)]
        L.lathe(mb,prof,(x,y),24,H.I['cream'],cap_top=True,cap_bottom=True)
        for s in (-1,1):H.ring(mb,(x,y+s*.38,8.72),.22,.045,'cream','XZ',24)
        H.box(mb,(x,y-.5,6.75),(.6,.07,.42),'bronze');H.text(mb,'1914',(x,y-.55,6.75),size=.14,key='white')
    H.build(mb,'05-06 preserved cast iron column monuments','Platform_Columns','heritage_column');H.count('preserved_column_monuments',2)
    print('V11_COLUMNS_OK',flush=True)

def roof56():
    old=bpy.data.objects['V10 05-06 differentiated roof skin'];v=H.world(old)
    xs0=np.unique(np.round(v[:,0],4));w0=[];e0=[]
    for x in xs0:
        q=v[abs(v[:,0]-x)<.001];w0.append(q[:,1].min());e0.append(q[:,1].max())
    def edges(x):return float(np.interp(x,xs0,w0)),float(np.interp(x,xs0,e0))
    holes=[]
    for lo,hi in H.components(bpy.data.objects['V6 OCS | masts']):
        x,y=(lo[:2]+hi[:2])/2;w,e=edges(x)
        if hi[2]-lo[2]>3 and max(hi[0]-lo[0],hi[1]-lo[1])<.8 and xs0[0]<x<xs0[-1] and w<y<e:holes.append((x,y,.42))
    def p(x,f,lift=0):
        w,e=edges(x);u=(f-.5)/.27
        z=10.57+(.80*math.sqrt(max(0,1-u*u)) if abs(u)<1 else .08*(1-abs(2*f-1)))
        return (x,w+(e-w)*f,z+lift)
    for name in ['differentiated roof skin','seams flashings gutters and glazing ribs','flashed mast penetrations']:
        H.retire(bpy.data.objects['V10 05-06 '+name])
    mb=L.MeshBuilder();detail=L.MeshBuilder()
    xs=sorted(set(list(np.arange(xs0[0],xs0[-1],1.8))+[float(xs0[-1])]+[float(x+s*r) for x,y,r in holes for s in (-1,1)]))
    for a,b in zip(xs[:-1],xs[1:]):
        xm=(a+b)/2;w,e=edges(xm)
        fs=sorted(set([0,.23,.77,1]+[.5+.27*math.cos(t) for t in np.linspace(0,math.pi,15)]+[max(0,min(1,(y+s*r-w)/(e-w))) for x,y,r in holes if abs(xm-x)<r for s in (-1,1)]))
        for c,d in zip(fs[:-1],fs[1:]):
            yy=w+(e-w)*(c+d)/2
            if any(abs(xm-x)<r+.001 and abs(yy-y)<r+.001 for x,y,r in holes):continue
            pts=[p(a,c),p(b,c),p(b,d),p(a,d)]
            mb.add(pts,[(0,1,2,3)],H.I['mint']);mb.add([(x,y,z-.055) for x,y,z in pts],[(3,2,1,0)],H.I['cream'])
    for x in np.arange(xs0[0]+.2,xs0[-1],1.0):
        fs=np.linspace(0,1,31)
        for a,b in zip(fs[:-1],fs[1:]):
            pp=p(x,(a+b)/2)
            if any(abs(x-hx)<r+.1 and abs(pp[1]-hy)<r+.3 for hx,hy,r in holes):continue
            H.rod(detail,p(x,a,.018),p(x,b,.018),.018,'mint',4)
    for x in [xs0[0],xs0[-1]]:
        pp=[p(x,f) for f in np.linspace(0,1,41)];lower=[(px,py,10.48) for px,py,pz in pp]
        for a,b,c,d in zip(pp[:-1],pp[1:],lower[1:],lower[:-1]):detail.add([a,b,c,d],[(0,1,2,3)],H.I['mint'])
    for s in (0,1):H.tube(detail,[p(x,s,-.05) for x in xs],.075,'steel')
    for hx,hy,r in holes:
        w,e=edges(hx);z=p(hx,(hy-w)/(e-w))[2]
        for s in (-1,1):
            H.box(detail,(hx+s*.46,hy,z+.06),(.08,.99,.13),'steel');H.box(detail,(hx,hy+s*.46,z+.06),(.99,.08,.13),'steel')
    o=H.build(mb,'05-06 curved green roof with low side wings','Roof_Details','roof_skin',island='05-06');o['V10_kind']='roof_skin'
    H.build(detail,'05-06 curved roof seams and penetration collars','Roof_Details','roof_detail',island='05-06')
    H.REPORT['roof56']={'profile':'green barrel centre with low side wings','mast_openings':len(holes),'dimensions':'photo inferred'}
    H.count('new_curved_roof_profiles');print('V11_ROOF56_OK',flush=True)

def ventilation_towers():
    # Official JR East 2013 alteration: roughly 4 m body and roughly 3 m canopy extension.
    cores=[o for o in bpy.data.objects if o.name.startswith('V3 ventilation tower continuous core') and not o.hide_render]
    for o in list(bpy.context.scene.objects):
        if o.name.startswith(('V3 ventilation ','V3 concentric tower roof seam','V3 underground railway ventilation tower plinth')) and not o.hide_render:H.retire(o)
    for i,o in enumerate(cores):
        lo,hi=H.bounds(o);cx,cy=(lo[:2]+hi[:2])/2;r=(hi[0]-lo[0])/2;R=r+3
        mb=L.MeshBuilder();H.cyl(mb,(cx,cy,.47),r+.60,.46,'granite',64)
        H.cyl(mb,(cx,cy,2.15),r,3.4,'dark',80)
        for t in np.linspace(0,math.tau,180,endpoint=False):
            x=cx+(r+.02)*math.cos(t);y=cy+(r+.02)*math.sin(t)
            H.box(mb,(x,y,2.15),(.11,.09,3.35),'steel',a=t)
        L.lathe(mb,[(r,3.79),(R,3.88),(R+.05,4.03),(R-.08,4.13),(r,4.23)],(cx,cy),96,H.I['steel'],cap_top=True)
        for t in np.linspace(0,math.tau,36,endpoint=False):
            H.beam(mb,(cx+r*.9*math.cos(t),cy+r*.9*math.sin(t),3.5),(cx+R*.97*math.cos(t),cy+R*.97*math.sin(t),3.9),.09,.17,'steel')
        H.ring(mb,(cx,cy,4.23),R-.10,.04,'steel',n=100)
        # Transparent framed roof sectors make the top construction readable.
        for t in np.linspace(0,math.tau,48,endpoint=False):
            a=t;b=t+math.tau/48-.008
            pp=[(cx+rr*math.cos(tt),cy+rr*math.sin(tt),4.25+(R-rr)*.012) for rr,tt in [(r*.35,a),(R-.17,a),(R-.17,b),(r*.35,b)]]
            mb.add(pp,[(0,1,2,3)],H.I['glass'])
            H.rod(mb,pp[0],pp[1],.035,'steel')
        # Low stone retaining arc, kept open on the approach side.
        for t in np.arange(.20,math.tau-.60,.14):
            rr=R+.75;x=cx+rr*math.cos(t);y=cy+rr*math.sin(t)
            H.box(mb,(x,y,.68),(rr*.14-.025,.42,.88),'pale_stone',a=t+math.pi/2)
        H.build(mb,f'plaza ventilation tower {i+1} broad canopy and vertical fins','Plaza','plaza_ventilation')
        H.count('corrected_plaza_ventilation_towers')

def plaza():
    mb=L.MeshBuilder();rng=np.random.default_rng(110)
    # Real separate stone faces and joints, raised only 5 mm over the existing paving.
    for row,y in enumerate(np.arange(-123.4,-34,.80)):
        for x in np.arange(-44.9,54.4,1.60):
            xa=x+(.8 if row%2 else 0)
            if xa+1.58>55:continue
            key='pale_stone' if rng.random()>.21 else 'granite'
            mb.add([(xa,y,.246),(xa+1.58,y,.246),(xa+1.58,y+.782,.246),(xa,y+.782,.246)],[(0,1,2,3)],H.I[key]);H.count('plaza_paving_units')
    H.build(mb,'Marunouchi granite paving with real joints','Plaza','paving')
    mb=L.MeshBuilder();trees=[o for o in bpy.context.scene.objects if o.name.startswith('Zelkova trunk') and not o.hide_render]
    for o in trees:
        lo,hi=H.bounds(o);x,y=(lo[:2]+hi[:2])/2
        H.box(mb,(x,y,.27),(3.5,3.5,.06),'soil')
        for s in (-1,1):
            H.box(mb,(x+s*1.9,y,.47),(.38,4.18,.46),'granite');H.box(mb,(x,y+s*1.9,.47),(3.42,.38,.46),'granite')
            H.box(mb,(x+s*1.9,y,.725),(.50,4.3,.09),'pale_stone');H.box(mb,(x,y+s*1.9,.725),(3.80,.50,.09),'pale_stone')
        for dx in np.arange(-1.4,1.41,.23):
            for dy in np.arange(-1.4,1.41,.23):
                if dx*dx+dy*dy<.2:continue
                H.box(mb,(x+dx,y+dy,.32),(.18,.18,.07),'hedge')
        H.count('tree_pits_with_seating')
    # Linear drain slots, inspection covers and small guide bollards.
    for x in (-23.0,33.0):
        H.box(mb,(x,-84,.255),(.16,50,.018),'dark')
        for y in np.arange(-108,-59,.28):H.box(mb,(x,y,.27),(.18,.035,.025),'steel')
    for x,y in [(-38,-40),(48,-42),(-38,-117),(47,-117),(4,-118)]:
        H.box(mb,(x,y,.254),(1.1,.85,.025),'plaza_dark')
        for d in (-.5,.5):H.box(mb,(x+d,y,.275),(.025,.84,.03),'steel')
        H.box(mb,(x,y,.275),(1.0,.025,.03),'steel');H.count('plaza_service_hatches')
    H.build(mb,'tree pit stone benches planting drain channels and covers','Plaza','plaza_furniture')
    # Visible street-side utility enclosure uses vertical fins and a high clerestory,
    # as in the Google Maps panorama; footprint remains an estimate in the existing diorama.
    mb=L.MeshBuilder();x,y=-144,-39;w,d,h=13,9,13.2
    H.box(mb,(x,y,h/2+.25),(w,d,h),'bronze')
    for xx in np.arange(x-w/2,x+w/2,.24):
        for s in (-1,1):H.box(mb,(xx,y+s*(d/2+.06),h/2+.25),(.065,.18,h),'bronze')
    for yy in np.arange(y-d/2,y+d/2,.24):
        for s in (-1,1):H.box(mb,(x+s*(w/2+.06),yy,h/2+.25),(.18,.065,h),'bronze')
    for xx in np.arange(x-5.5,x+6,1.3):H.box(mb,(xx,y-d/2-.12,h-1.0),(.80,.08,.45),'window')
    H.box(mb,(x,y,h+.30),(w+.4,d+.4,.18),'steel')
    H.build(mb,'north plaza vertically screened utility enclosure','Service_Details','service_enclosure',estimated_dimensions=True)
    H.count('streetview_informed_utility_enclosures')
    ventilation_towers();print('V11_PLAZA_OK',flush=True)

def service_and_facade():
    mb=L.MeshBuilder()
    for o in list(bpy.context.scene.objects):
        if o.get('V10_kind')!='service_building' or o.hide_render:continue
        lo,hi=H.bounds(o);x0,y0,z0=lo;x1,y1,z1=hi
        if x1-x0<15:continue
        # Use side-wall maintenance features; avoid the access ladder at the east end.
        y=y0-.13;zroof=z1-1.8
        for x in (x0+1.1,x1-1.2):
            H.tube(mb,[(x,y,z0+.15),(x,y,zroof-.4),(x,y+.25,zroof+.1)],.065,'steel',10)
            for z in np.arange(z0+.5,zroof,.9):H.box(mb,(x,y+.02,z),(.20,.22,.05),'steel')
        if x1-x0>15:
            H.box(mb,(x0+4,y0-.3,z0+1.28),(2.7,.17,2.4),'paint')
            for x in (x0+3.34,x0+4.66):
                H.box(mb,(x,y0-.40,z0+1.25),(.06,.10,.40),'dark')
            H.box(mb,(x0+4,y0-.6,z0+2.65),(3.4,1.1,.10),'steel')
            H.box(mb,(x0+8,y0-.20,z0+1.05),(1.1,.3,1.6),'paint')
            H.text(mb,'設備室',(x0+4,y0-.42,z0+2.05),size=.25,key='dark')
            H.count('service_facades_detailed')
    H.build(mb,'service block entrance canopies drainpipes and electrical cupboards','Service_Details','service_detail')
    mb=L.MeshBuilder()
    # Drain pipes align with the front facade piers, outside existing window openings.
    for x in [-90,-56,-45,-19,19,45,56,90]:
        y=-7.24
        H.tube(mb,[(x,y,.50),(x,y,15.9),(x,y+.35,16.3)],.07,'copper',10)
        for z in np.arange(1.2,15.5,1.6):H.box(mb,(x,y+.02,z),(.24,.23,.05),'bronze')
        H.box(mb,(x,y+.08,16.1),(.28,.30,.45),'copper')
    # Thin mullion shadows, sills and interior blinds on sampled real facade windows.
    n=0
    for o in list(bpy.context.scene.objects):
        if o.hide_render or o.type!='MESH' or 'front' not in o.name or 'glaz' not in o.name.lower():continue
        lo,hi=H.bounds(o)
        if not (-95<lo[0]<95 and lo[1]<-5 and .7<hi[0]-lo[0]<2.8 and hi[2]-lo[2]>.6):continue
        x=(lo[0]+hi[0])/2;y=lo[1]-.015;w=hi[0]-lo[0];z=(lo[2]+hi[2])/2
        H.box(mb,(x,y,z),(.025,.035,hi[2]-lo[2]),'bronze')
        H.box(mb,(x,y-.025,lo[2]-.045),(w+.1,.22,.055),'pale_stone')
        if n%3==0:H.box(mb,(x,y+.10,hi[2]-.25),(w-.12,.028,.44),'cream')
        n+=1
    # Ground-level entrance fittings and understated wall lamps.
    for x in [-88,-59,-42,-22,22,42,59,88]:
        H.box(mb,(x,-7.45,2.8),(.20,.20,.42),'bronze');H.box(mb,(x,-7.57,2.82),(.13,.02,.28),'lamp')
    H.build(mb,'Marunouchi facade rainwater goods window sills and entrance lamps','Facade_Details','facade_detail')
    H.count('facade_windows_detailed',n);H.count('facade_rainwater_pipes',8)
    print('V11_FACADE_OK',n,flush=True)

def run():
    platform_undercrofts();columns();roof56();plaza();service_and_facade()
