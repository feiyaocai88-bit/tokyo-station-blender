"""V10: differentiated platform roofs, rooftop plant and railway service context.

Run on the published V9 scene, never on the user's only copy:
  blender -b Tokyo_Station.blend --python-exit-code 1 -P mod10_platform_context.py -- out.blend report.json

Reference-derived features and estimated dimensions are distinguished in
sources_and_licenses/platform_context_v10.json. Old roof meshes remain in a
hidden collection. Track geometry, trains, architecture and underground levels
are not transformed. Uses the existing track centres and canopy outlines.
"""
import bpy, sys, os, math, json, re
import numpy as np
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v5lib as L

SC = bpy.context.scene
D = json.load(open(os.path.join(HERE, 'targets.json'), encoding='utf8'))
GX = np.array(D['X'])
TRACKS = {k: np.array(v) for k, v in D['target'].items()}
ISLANDS = D['islands']
REPORT = {'revision': 10, 'roofs': {}, 'roof_buildings': [], 'facilities': [],
          'barriers': [], 'service_buildings': [], 'retired': [], 'warnings': []}
MATS = []
MI = {}
COLS = {}
MASTS = []


def ty(k, x):
    return np.interp(x, GX, TRACKS[k])


def center(isl, x):
    a, b = isl.split('-')
    return (ty(a, x) + ty(b, x)) * .5


def angle(isl, x):
    return math.atan2(float(center(isl, x+.25)-center(isl, x-.25)), .5)


def world(o):
    a = np.empty(len(o.data.vertices)*3, dtype=np.float64)
    o.data.vertices.foreach_get('co', a)
    mw = np.array(o.matrix_world)
    return a.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]


def material(key, color, rough=.65, metal=.1, noise=False, transmission=0, emission=0):
    m = L.principled('V10 | '+key, color, rough=rough, metal=metal)
    bs = m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Transmission Weight'].default_value = transmission
    if emission:
        bs.inputs['Emission Color'].default_value = (*color, 1)
        bs.inputs['Emission Strength'].default_value = emission
    if noise:
        nt = m.node_tree
        tex = nt.nodes.new('ShaderNodeTexNoise'); tex.inputs['Scale'].default_value=.38
        tex.inputs['Detail'].default_value=3
        geo=nt.nodes.new('ShaderNodeNewGeometry')
        nt.links.new(geo.outputs['Position'],tex.inputs['Vector'])
        ramp=nt.nodes.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].color=(*(c*.79 for c in color),1)
        ramp.color_ramp.elements[1].color=(*color,1)
        nt.links.new(tex.outputs['Fac'],ramp.inputs[0]); nt.links.new(ramp.outputs[0],bs.inputs['Base Color'])
    MI[key]=len(MATS); MATS.append(m)
    return m


def setup():
    for key in ('Roofs','Roof_Plant','Platform_Details','Acoustic_Barriers','Service_Buildings','Review_Cameras'):
        COLS[key]=L.collection('V10_'+key)
    material('mint',(.24,.53,.43),noise=True)
    material('pale_green',(.39,.57,.49),noise=True)
    material('aged_green',(.23,.38,.33),noise=True)
    material('charcoal_roof',(.11,.13,.135),noise=True)
    material('roof_white',(.76,.78,.74),noise=True)
    material('repair_grey',(.48,.51,.48),noise=True)
    material('cream',(.62,.60,.51))
    material('metal',(.49,.53,.53),.35,.65)
    material('dark',(.042,.055,.06),.7,.2)
    material('concrete',(.40,.43,.42),noise=True)
    material('wall',(.69,.69,.63),noise=True)
    material('glass',(.18,.30,.32),.22,.15,transmission=.7)
    material('clear_glass',(.91,.95,.97),.09,0,transmission=1.0)
    material('skylight',(.64,.76,.73),.32,.05,transmission=.65)
    material('solar',(.028,.066,.13),.27,.4)
    material('solar_grid',(.28,.37,.45),.4,.45)
    material('orange',(.84,.17,.018))
    material('blue',(.013,.24,.47))
    material('green',(.20,.46,.035))
    material('red',(.58,.025,.025))
    material('yellow',(.88,.58,.035))
    material('white',(.84,.85,.82),.45)
    material('light',(.8,.89,.88),.3,emission=1.5)
    material('wood',(.32,.21,.11),noise=True)
    # The existing overhead-line masts intentionally pass through these roofs.
    # Find each connected vertical shaft so new roofing gets real openings.
    o=bpy.data.objects['V6 OCS | masts']; P=world(o); me=o.data
    labels=np.arange(len(P)); edges=np.empty(len(me.edges)*2,dtype=np.int32)
    me.edges.foreach_get('vertices',edges); edges=edges.reshape(-1,2)
    for _ in range(80):
        old=labels.copy(); m=np.minimum(labels[edges[:,0]],labels[edges[:,1]])
        np.minimum.at(labels,edges[:,0],m);np.minimum.at(labels,edges[:,1],m);labels=labels[labels]
        if np.array_equal(labels,old): break
    for lab in np.unique(labels):
        q=P[labels==lab]
        if np.ptp(q[:,2])>3 and np.ptp(q[:,0])<.8 and np.ptp(q[:,1])<.8:
            MASTS.append((float(q[:,0].mean()),float(q[:,1].mean()),float(q[:,2].min()),float(q[:,2].max())))


def finish(mb, name, collection, kind, **props):
    if not mb.f:
        return None
    o=mb.build('V10 '+name,COLS[collection],MATS)
    o['V10_kind']=kind
    for k,v in props.items(): o[k]=v
    return o


def retire(o):
    hc=L.collection('V10_Replaced_roofs_hidden',hide_render=True)
    hc.hide_viewport=True
    for c in list(o.users_collection): c.objects.unlink(o)
    hc.objects.link(o); o.hide_render=True; o.hide_viewport=True
    o['V10_retired']=True
    REPORT['retired'].append(o.name)


def box(mb, p, size, mat, a=0):
    L.box(mb,*p,*size,MI[mat],rotz=a)


def rod(mb, p, q, r=.035, mat='metal', sides=6):
    L.tube(mb,[Vector(p),Vector(q)],r,sides=sides,mat=MI[mat])


def shell(mb, pts, thickness, top, underside='cream'):
    p=[tuple(v) for v in pts]; n=len(p)
    bottom=[(x,y,z-thickness) for x,y,z in p]
    mb.add(p,[tuple(range(n))],MI[top])
    mb.add(bottom,[tuple(reversed(range(n)))],MI[underside])
    mb.add(p+bottom,[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],MI[underside])


class RoofPath:
    def __init__(self, isl):
        self.isl=isl
        self.shin=isl in ('20-21','22-23','14-15','16-17','18-19')
        self.x0,self.x1=ISLANDS[isl]['Q']
        if self.shin:
            src=next(o for o in SC.objects if o.get('V5_shinkansen_roof')==isl)
            meta=json.loads(SC['V5_shinkansen_roofs'])[isl]
            self.eave=meta['z_eave']; self.deck=meta['z_deck']
            self.sections=[(self.x0,self.x1)]
            # Retain the already validated columns, main girders and lights.
            W=world(src); mb=L.MeshBuilder()
            for p in src.data.polygons:
                mat=src.data.materials[p.material_index].name
                verts=W[list(p.vertices)]
                if ('steel' in mat or 'LED' in mat) and verts[:,2].min()<self.eave-.32:
                    mb.add(verts,[tuple(range(len(verts)))],MI['light' if 'LED' in mat else 'cream'])
            finish(mb,f'{isl} retained steel and lights','Roofs','roof_structure',island=isl)
            retire(src)
        else:
            src=bpy.data.objects[f'V8 canopy {isl} | roof deck and skylight']
            W=world(src)
            self.eave=20.75 if isl=='01-02' else 10.45
            self.deck=16.51 if isl=='01-02' else 6.21
            top=W[np.abs(W[:,2]-self.eave)<.002]
            xs=np.unique(np.round(top[:,0],4))
            self.xs=xs
            self.yw=np.array([top[np.abs(top[:,0]-x)<.002,1].min() for x in xs])
            self.ye=np.array([top[np.abs(top[:,0]-x)<.002,1].max() for x in xs])
            self.sections=[tuple(p['x']) for p in json.loads(SC['V8_canopies'])[isl]['parts']]
            # The stored report rounds end coordinates; clamp to actual mesh.
            self.sections=[(float(xs.min()),float(xs.max()))]
            retire(src)
        self.holes=[]
        for x,y,z0,z1 in MASTS:
            if not self.x0<x<self.x1: continue
            a,b=self.edges(x)
            if a<y<b and z0<self.eave<z1:
                self.holes.append((x,y,.37))

    def edges(self,x):
        if self.shin:
            a,b=self.isl.split('-')
            return float(ty(a,x)-1.05),float(ty(b,x)+1.05)
        return float(np.interp(x,self.xs,self.yw)),float(np.interp(x,self.xs,self.ye))

    def z(self,x,f):
        i=self.isl
        if i=='01-02': return self.eave+.16+.70*(1-abs(2*f-1))
        if i=='03-04': return self.eave+.06+.48*(1-abs(2*f-1))
        if i=='05-06': return self.eave+.08+.72*(1-abs(2*f-1))
        if i=='07-08': return self.eave+.04+.30*(1-abs(2*f-1))
        if i=='09-10': return self.eave+.08+.76*(1-abs(2*f-1))
        if i=='20-21': return self.eave+.12+.69*(1-abs(2*f-1))
        if i=='22-23': return self.eave+.08+.96*(1-abs(2*f-1))
        # Tokaido roofs: independently proportioned raised central roof strips.
        half={'14-15':.155,'16-17':.225,'18-19':.185}[i]
        half += .025 if -38<x<55 else 0
        r=abs(f-.5)
        if r>half+.012: return self.eave+.11+.39*(.5-r)/(.5-half)
        return self.eave+{'14-15':1.05,'16-17':1.25,'18-19':.93}[i]+.12*(1-r/half)

    def p(self,x,f,dz=0):
        a,b=self.edges(x)
        return (float(x),a+(b-a)*f,self.z(x,f)+dz)

    def hole_overlap(self,x0,x1,f0,f1):
        x=(x0+x1)/2;a,b=self.edges(x)
        y0=a+(b-a)*f0;y1=a+(b-a)*f1
        return any(x0<hx+r+.06 and x1>hx-r-.06 and y0<hy+r+.06 and y1>hy-r-.06 for hx,hy,r in self.holes)


def roof_patch(R,mb,x0,x1,f0,f1,mat):
    holes=[(x,y,r) for x,y,r in R.holes if x-r<x1 and x+r>x0]
    if not holes:
        shell(mb,[R.p(x0,f0),R.p(x1,f0),R.p(x1,f1),R.p(x0,f1)],.07,mat);return
    xx=sorted(set([x0,x1]+[max(x0,min(x1,x+s*r)) for x,y,r in holes for s in (-1,1)]))
    for a,b in zip(xx[:-1],xx[1:]):
        if b-a<1e-6:continue
        mid=(a+b)/2;yw,ye=R.edges(mid);width=ye-yw
        hh=[(x,y,r) for x,y,r in holes if abs(mid-x)<r]
        ff=sorted(set([f0,f1]+[max(f0,min(f1,(y+s*r-yw)/width)) for x,y,r in hh for s in (-1,1)]))
        for c,d in zip(ff[:-1],ff[1:]):
            if d-c<1e-6:continue
            cy=yw+(ye-yw)*(c+d)/2
            if any(abs(cy-y)<r+.001 for x,y,r in hh):continue
            shell(mb,[R.p(a,c),R.p(b,c),R.p(b,d),R.p(a,d)],.07,mat)


def rib_segments(R,x,f0,f1):
    yw,ye=R.edges(x);width=ye-yw
    hh=[(y,r+.06) for hx,y,r in R.holes if abs(x-hx)<r+.06]
    fs=sorted(set([f0,f1]+[max(f0,min(f1,(y+s*r-yw)/width)) for y,r in hh for s in (-1,1)]))
    return [(a,b) for a,b in zip(fs[:-1],fs[1:]) if b-a>1e-6 and not any(abs(yw+width*(a+b)/2-y)<r for y,r in hh)]


ROOF_COL={'01-02':'pale_green','03-04':'mint','05-06':'aged_green','07-08':'pale_green','09-10':'solar',
          '20-21':'pale_green','22-23':'mint','14-15':'roof_white','16-17':'roof_white','18-19':'roof_white'}


def roof_material(isl,x,f):
    if isl=='03-04' and -53<x<22: return 'charcoal_roof'
    if isl=='05-06' and (x<-77 or 68<x<86): return 'repair_grey'
    if isl=='07-08' and -163<x<-112: return 'repair_grey'
    if isl in ('20-21','22-23'):
        patches={'20-21':[(-157,-147),(-13,-5),(91,99)],'22-23':[(-113,-102),(20,30),(128,138)]}
        if any(a<x<b for a,b in patches[isl]): return 'roof_white'
    return ROOF_COL[isl]


def build_roof(R):
    mb,detail=L.MeshBuilder(),L.MeshBuilder()
    isl=R.isl; solar_count=0
    for xa,xb in R.sections:
        xs=np.linspace(xa,xb,int(math.ceil((xb-xa)/1.6))+1)
        fs=[0,.5,1]
        if isl=='07-08': fs=[0,.39,.61,1]
        if isl=='01-02': fs=[0,.34,.5,.66,1]
        if isl in ('14-15','16-17','18-19'):
            h={'14-15':.155,'16-17':.225,'18-19':.185}[isl]
            fs=[0,.5-h-.04,.5-h,.5,.5+h,.5+h+.04,1]
        for x0,x1 in zip(xs[:-1],xs[1:]):
            for f0,f1 in zip(fs[:-1],fs[1:]):
                if isl=='07-08' and .4<(f0+f1)/2<.6: continue
                mat=roof_material(isl,(x0+x1)/2,(f0+f1)/2)
                if isl=='01-02' and .34<=(f0+f1)/2<=.66: mat='skylight'
                roof_patch(R,mb,x0,x1,f0,f1,mat)
        # Actual geometry for folded metal ribs, gutters and roof-end flashing.
        if isl!='09-10':
            for x in np.arange(xa+.22,xb-.1,.62):
                for f0,f1 in zip(fs[:-1],fs[1:]):
                    if isl=='07-08' and .4<(f0+f1)/2<.6: continue
                    mat=roof_material(isl,x,(f0+f1)/2)
                    if isl=='01-02' and .34<=(f0+f1)/2<=.66: mat='metal'
                    for ca,cb in rib_segments(R,x,f0,f1):
                        rod(detail,R.p(x,ca,.025),R.p(x,cb,.025),.024,mat,4)
        for f in (0,1):
            path=[R.p(x,f,-.04) for x in xs]
            L.tube(detail,[Vector(p) for p in path],.09,6,MI['metal'])
        for x in (xa,xb):
            for f0,f1 in zip(fs[:-1],fs[1:]): rod(detail,R.p(x,f0,-.05),R.p(x,f1,-.05),.08,'cream',4)
        for x in np.arange(xa+2,xb-1,9.3):
            for f in (.22,.78):
                rod(detail,(x,*R.p(x,f)[1:2],R.eave-.04),R.p(x,f,-.06),.045,'cream')
        if isl=='07-08':
            # Segmented translucent barrel, open to the original skylight below.
            for x0,x1 in zip(xs[:-1],xs[1:]):
                if R.hole_overlap(x0,x1,.39,.61):
                    roof_patch(R,mb,x0,x1,.39,.61,'metal');continue
                for k in range(8):
                    def p(x,kk):
                        a,b=R.edges(x); c=(a+b)/2
                        t=math.pi*kk/8
                        return (x,c+.96*math.cos(t),R.eave+.22+.50*math.sin(t))
                    mb.add([p(x0,k),p(x1,k),p(x1,k+1),p(x0,k+1)],[(0,1,2,3)],MI['skylight'])
            for x in np.arange(xa+.2,xb,3.2):
                if any(abs(x-hx)<1.9 for hx,hy,r in R.holes):continue
                a,b=R.edges(x); c=(a+b)/2
                pts=[Vector((x,c+.97*math.cos(t),R.eave+.23+.50*math.sin(t))) for t in np.linspace(0,math.pi,9)]
                L.tube(detail,pts,.035,6,MI['metal'])
        if isl=='09-10':
            # Roofing-integrated PV, with silver module frames and cell busbars.
            for x in np.arange(xa+.2,xb-1.3,1.65):
                for row in range(8):
                    f0=.025+row*.119; f1=f0+.111
                    if R.hole_overlap(x,x+1.57,f0,f1):continue
                    pts=[R.p(x,f0,.028),R.p(x+1.57,f0,.028),R.p(x+1.57,f1,.028),R.p(x,f1,.028)]
                    mb.add(pts,[(0,1,2,3)],MI['solar']); solar_count+=1
                    for a,b in zip(pts,pts[1:]+pts[:1]): rod(detail,a,b,.016,'metal',4)
                    for q in range(1,6): rod(detail,R.p(x+q*1.57/6,f0,.033),R.p(x+q*1.57/6,f1,.033),.004,'solar_grid',4)
        # Roof maintenance anchor points and short repairs do not repeat identically.
        if R.shin:
            for x in np.arange(xa+17,xb-8,38):
                if isl=='22-23' and -167<x<-103:continue
                f=.5
                z=R.z(x,f)
                a,b=R.edges(x); c=(a+b)/2
                box(detail,(x,c,z+.22),(1.10,.68,.42),'metal',angle(isl,x))
                box(detail,(x,c,z+.46),(1.28,.86,.08),'roof_white',angle(isl,x))
    finish(mb,f'{isl} differentiated roof skin','Roofs','roof_skin',island=isl)
    collars=L.MeshBuilder()
    for hx,hy,r in R.holes:
        verts=[]
        for radius,lift in ((.30,.16),(.54,.025)):
            for t in np.linspace(0,2*math.pi,25)[:-1]:
                x=hx+radius*math.cos(t);y=hy+radius*math.sin(t);a,b=R.edges(x)
                verts.append((x,y,R.z(x,(y-a)/(b-a))+lift))
        collars.add(verts,[(i,(i+1)%24,(i+1)%24+24,i+24) for i in range(24)],MI['metal'])
    finish(collars,f'{isl} flashed mast penetrations','Roofs','roof_penetration',island=isl)
    if not R.shin:
        # The original shared 12 m break is replaced by a supported roof bay.
        for f in (.23,.77):
            rod(detail,R.p(-11,f,-.25),R.p(1,f,-.25),.12,'cream',4)
    finish(detail,f'{isl} seams flashings gutters and glazing ribs','Roofs','roof_detail',island=isl)
    if isl=='22-23':
        # Approximately 433 m2 in the published 1993 installation; placement estimated.
        pv=L.MeshBuilder(); x0=-165; rows=6; count=0; area=0.0
        for x in np.arange(x0,x0+60,2.0):
            west,east=R.edges(x+.94);width=east-west
            for j in range(rows):
                f0=.5+(-4.01+j*1.35)/width; f1=f0+1.27/width
                ps=[R.p(x,f0,.27),R.p(x+1.88,f0,.27),R.p(x+1.88,f1,.27),R.p(x,f1,.27)]
                shell(pv,ps,.06,'solar','metal')
                for a,b in zip(ps,ps[1:]+ps[:1]): rod(pv,a,b,.025,'metal',4)
                P=[Vector(v) for v in ps]
                area+=((P[1]-P[0]).cross(P[2]-P[0]).length+(P[2]-P[0]).cross(P[3]-P[0]).length)/2
                count+=1
        finish(pv,'22-23 local rooftop PV array','Roof_Plant','roof_pv',island=isl)
        solar_count+=count
        REPORT['22_23_pv_surface_area_m2']=round(area,2)
    REPORT['roofs'][isl]={'style':ROOF_COL[isl], 'eave_z':R.eave,'sections':R.sections,'pv_modules':solar_count,
                          'estimated_profile':True,'platform_deck_z':R.deck,'flashed_mast_openings':len(R.holes)}
    print('V10 roof',isl,flush=True)


def local_box(mb,F,p,size,mat):
    L.box(mb,0,0,0,*size,MI[mat],frame=F@Matrix.Translation(p))


def local_rod(mb,F,p,q,r=.035,mat='metal'):
    rod(mb,F@Vector(p),F@Vector(q),r,mat)


def louvres(mb,F,c,w,h,spacing=.16):
    x,y,z=c
    local_box(mb,F,(x,y,z),(w,.10,h),'dark')
    for zz in np.arange(z-h/2+.08,z+h/2,.16):
        local_box(mb,F,(x,y-.07,zz),(w,.16,.065),'metal')
    for xx in (x-w/2,x+w/2): local_box(mb,F,(xx,y-.09,z),(.07,.18,h+.1),'metal')


def plant_house(name,x,y,z,length,width,height,a=0,kind='roof_house',windows=True,large=False):
    mb=L.MeshBuilder(); F=Matrix.Translation((x,y,z))@Matrix.Rotation(a,4,'Z')
    local_box(mb,F,(0,0,.12),(length+.35,width+.35,.24),'concrete')
    local_box(mb,F,(0,0,height/2+.2),(length,width,height),'wall')
    # Standing metal siding, corner trims and drip flashing.
    for xx in np.arange(-length/2+.6,length/2,.9):
        for s in (-1,1): local_box(mb,F,(xx,s*(width/2+.012),height/2+.2),(.026,.03,height-.1),'repair_grey')
    local_box(mb,F,(0,0,height+.28),(length+.45,width+.45,.16),'charcoal_roof')
    local_box(mb,F,(0,0,height+.42),(length+.56,width+.56,.09),'roof_white')
    # Door faces away from the track; raised sill and handle.
    local_box(mb,F,(-length*.28,-width/2-.05,1.25),(1.0,.10,2.1),'metal')
    local_box(mb,F,(-length*.28+.34,-width/2-.12,1.25),(.04,.10,.23),'dark')
    louvres(mb,F,(length*.19,-width/2-.08,height*.59),min(length*.37,3.8),min(height*.55,2.5))
    if windows and height<5:
        for xx in (-length*.16,length*.05):
            local_box(mb,F,(xx,width/2+.03,height*.66),(length*.16,.10,.54),'metal')
            local_box(mb,F,(xx,width/2+.09,height*.66),(length*.16-.12,.03,.43),'glass')
    elif windows:
        # Service blocks have storeys and grouped windows, unlike the small roof huts.
        for zz in np.arange(3.0,height-.5,3.4):
            for s in (-1,1):
                local_box(mb,F,(0,s*(width/2+.035),zz-1.0),(length,.10,.16),'concrete')
                for xx in np.arange(-length/2+2.2,length/2-1.0,3.4):
                    local_box(mb,F,(xx,s*(width/2+.055),zz),(1.85,.10,.96),'metal')
                    local_box(mb,F,(xx,s*(width/2+.115),zz),(1.67,.026,.79),'glass')
                    local_box(mb,F,(xx,s*(width/2+.14),zz),(.035,.035,.81),'metal')
            EF=F@Matrix.Rotation(math.pi/2,4,'Z')
            louvres(mb,EF,(0,-length/2-.06,zz),min(width*.55,4.6),1.8)
    # Air-conditioning condenser and duct riser, including fan grilles.
    for dx in ([0,length*.29] if large else [length*.27]):
        local_box(mb,F,(dx,0,height+.95),(1.8,1.3,1.0),'metal')
        for yy in (-.32,.32):
            c=F@Vector((dx,yy,height+1.46))
            L.lathe(mb,[(.26,c.z),(.26,c.z+.025)],c,16,MI['dark'],cap_top=True)
            for t in (-.17,0,.17):
                local_rod(mb,F,(dx-.22,yy+t,height+1.49),(dx+.22,yy+t,height+1.49),.016)
    if large:
        # Rooftop cooling banks, plinths and connected rectangular air ducts.
        positions=np.linspace(1.4,length*.38,5) if length>30 else [length*.24]
        for dx in positions:
            for sy in (-1,1):
                yy=sy*(width*.28)
                local_box(mb,F,(dx,yy,height+.60),(2.9,1.9,.24),'concrete')
                local_box(mb,F,(dx,yy,height+1.36),(2.65,1.65,1.30),'metal')
                for q in (-.68,.68):
                    c=F@Vector((dx+q,yy,height+2.025))
                    L.lathe(mb,[(.51,c.z),(.51,c.z+.035)],c,20,MI['dark'],cap_top=True)
                    for g in np.arange(-.4,.41,.10):
                        chord=math.sqrt(max(0,.49**2-g*g))
                        local_rod(mb,F,(dx+q-chord,yy+g,height+2.07),(dx+q+chord,yy+g,height+2.07),.015)
                local_box(mb,F,(dx,sy*width*.14,height+.80),(.62,width*.22,.56),'metal')
    # Caged access ladder on end wall and roof safety rails.
    lx=length/2+.16
    for yy in (-.38,.38): local_rod(mb,F,(lx,yy,.25),(lx,yy,height+1.15),.045)
    for zz in np.arange(.45,height+.7,.30): local_rod(mb,F,(lx,-.38,zz),(lx,.38,zz),.032)
    for s in (-1,1):
        for xx in np.arange(-length/2+.3,length/2,2.6):
            local_rod(mb,F,(xx,s*(width/2-.2),height+.48),(xx,s*(width/2-.2),height+1.40),.025)
        local_rod(mb,F,(-length/2+.2,s*(width/2-.2),height+1.4),(length/2-.2,s*(width/2-.2),height+1.4),.025)
    col='Roof_Plant' if kind=='roof_house' else 'Service_Buildings'
    o=finish(mb,name,col,kind)
    o['estimated_dimensions']=True
    return o


def rooftop_buildings(roofs):
    # Sparse individually sized huts; broad silhouette and louvres from reference photos.
    entries=[('01-02',-88,13,5.4,2.9),('03-04',33,5.8,3.0,2.45),
             ('07-08',-63,8.4,3.0,2.35),('20-21',-94,10.2,4.5,3.0),
             ('20-21',102,3.1,3.3,4.0),('22-23',120,7.1,4.6,2.8),
             ('14-15',135,10.5,4.5,2.8),('16-17',111,13.8,4.5,3.0)]
    for isl,x,l,w,h in entries:
        R=roofs[isl]; y=float(center(isl,x)); z=max(R.z(x,.5),R.z(x-l/2,.5),R.z(x+l/2,.5))+.025
        o=plant_house(f'{isl} roof equipment room at {x:+g}',x,y,z,l,w,h,angle(isl,x))
        o['island']=isl
        # Explicit load-bearing curb extends down to the underlying roof.
        mb=L.MeshBuilder()
        for xx in np.linspace(x-l/2+.4,x+l/2-.4,4):
            for s in (-1,1):
                yy=float(center(isl,xx))+s*(w/2-.35)
                a,b=R.edges(xx); zz=R.z(xx,(yy-a)/(b-a))
                box(mb,(xx,yy,(zz+z)/2),(.25,.25,max(.05,z-zz)),'cream')
        finish(mb,f'{isl} equipment room roof curbs {x:+g}','Roof_Plant','roof_curbs',island=isl)
        REPORT['roof_buildings'].append({'island':isl,'x':x,'size':[l,w,h],'object':o.name})


def barriers():
    # Outer boundaries only. Keep each panel centre >=3.45 m from its track.
    specs=[('Chuo west','01',-1,-201,229,14.90,2.80),
           ('Chuo east','02',1,-198,221,14.90,2.35),
           ('Shinkansen east','19',1,-201,235,6.50,3.10)]
    for name,tr,side,x0,x1,z0,h in specs:
        mb=L.MeshBuilder(); count=0
        xs=np.linspace(x0,x1,int(math.ceil((x1-x0)/2.75))+1)
        for a,b in zip(xs[:-1],xs[1:]):
            x=(a+b)/2; yc=float(ty(tr,x)+side*3.65)
            yaw=math.atan2(float(ty(tr,b)-ty(tr,a)),b-a)
            ln=math.hypot(b-a,float(ty(tr,b)-ty(tr,a)))
            F=Matrix.Translation((x,yc,z0))@Matrix.Rotation(yaw,4,'Z')
            local_box(mb,F,(0,0,.45),(ln,.29,.90),'concrete')
            # Opaque corrugated absorber with periodic glazed upper screens.
            clear=(name.startswith('Chuo') and -139<x<115) or count%7 in (3,4)
            local_box(mb,F,(0,0,1.28),(ln-.10,.14,.78),'repair_grey')
            topmat='glass' if clear else 'wall'
            local_box(mb,F,(0,0,(h+1.70)/2),(ln-.12,.09,h-1.70),topmat)
            for zz in np.arange(.97,1.62,.14):
                local_box(mb,F,(0,-side*.085,zz),(ln-.14,.055,.026),'metal')
            for dx in (-ln/2+.045,ln/2-.045):
                local_box(mb,F,(dx,0,h/2),(.09,.26,h+.10),'metal')
            for zz in (1.70,h): local_box(mb,F,(0,0,zz),(ln,.15,.075),'metal')
            # Bracket connecting panel post to edge beam.
            local_box(mb,F,(0,-side*.26,.12),(.35,.72,.18),'metal')
            count+=1
        o=finish(mb,name+' segmented acoustic screen','Acoustic_Barriers','barrier',track=tr)
        REPORT['barriers'].append({'name':name,'panels':count,'height_m':h,'object':o.name})


def service_buildings():
    # Within the existing diorama boundary. These are railway plant volumes,
    # not a reconstruction of the surrounding high-rise redevelopment.
    specs=[('Yaesu trackside maintenance building',-95,216.2,.05,63,11.5,13.8,0),
           ('North station-side ventilation building',-176,17,.05,17,12,10.5,0),
           ('South station-side ventilation building',192,16,.05,18,11,9.8,0),
           ('South Shinkansen service room',220,float(center('20-21',220)),6.50,9,4.4,3.1,angle('20-21',220)),
           ('South conventional service room',177,float(center('07-08',177)),4.60,6.4,2.4,2.9,angle('07-08',177))]
    for name,x,y,z,l,w,h,a in specs:
        o=plant_house(name,x,y,z,l,w,h,a,'service_building',windows=True,large=l>15)
        REPORT['service_buildings'].append({'object':o.name,'position':[x,y,z],'size':[l,w,h],'estimated':True})
        # Louvred intake stack rising above the plant building, with overhanging rain cap.
        if l>15:
            mb=L.MeshBuilder(); F=Matrix.Translation((x-l*.21,y,z+h+.52))@Matrix.Rotation(a,4,'Z')
            sh=4.5 if l>30 else 3.6; sw=min(w*.72,6.4)
            local_box(mb,F,(0,0,sh/2),(5.4,sw,sh),'concrete')
            louvres(mb,F,(0,-sw/2-.04,sh*.53),4.85,sh*.75)
            F2=F@Matrix.Rotation(math.pi,4,'Z')
            louvres(mb,F2,(0,-sw/2-.04,sh*.53),4.85,sh*.75)
            local_box(mb,F,(0,0,sh+.15),(6.1,sw+.75,.30),'roof_white')
            finish(mb,name+' louvred ventilation tower','Service_Buildings','ventilation_tower')
            # External rectangular ducts and wall rainwater downpipes.
            ducts=L.MeshBuilder()
            for dx in (-l*.38,l*.35):
                yy=y+w/2+.25
                box(ducts,(x+dx,yy,z+h/2),(.18,.20,h),'metal',a)
            finish(ducts,name+' service pipes','Service_Buildings','service_pipes')


class Reservations:
    def __init__(self):
        self.keep=json.loads(SC.get('V6_platform_keepouts','[]'))
        self.points=[]; self.used=[]
        for o in SC.objects:
            if o.hide_render or not o.visible_get(): continue
            if o.type=='MESH' and (o.name.startswith(('V5 platform','V6 platform','V8 canopy','V5 Shinkansen roof','V6 OCS | masts')) or o.get('V10_kind')=='roof_structure'):
                self.points.append(world(o))
            if o.type=='EMPTY' and re.match(r'V\d person',o.name):
                self.points.append(np.array([list(o.matrix_world.translation)]))
        self.points=np.concatenate(self.points) if self.points else np.zeros((0,3))

    def free(self,isl,x,y,z,l,w,h):
        a=angle(isl,x); u=np.array([math.cos(a),math.sin(a)]); v=np.array([-u[1],u[0]])
        for k in self.keep:
            if k.get('island')!=isl: continue
            cc=np.array(k['c']); ku=np.array(k['u']); kv=np.array([-ku[1],ku[0]])
            p=np.array([x,y])-cc
            # Conservative projected rectangle, also reserves circulation at stair mouths.
            ru=(abs(u@ku)*l+abs(v@ku)*w)/2+.55
            rv=(abs(u@kv)*l+abs(v@kv)*w)/2+.40
            if k.get('z1',999)<z or k.get('z0',-999)>z+h: continue
            if k.get('u0',-.4)-ru<p@ku<k.get('u1',.4)+ru and abs(p@kv)<k.get('hv',1)+rv: return False
        P=self.points
        mask=(np.abs(P[:,0]-x)<l+2)&(np.abs(P[:,1]-y)<w+2)&(P[:,2]>z-.1)&(P[:,2]<z+h+.2)
        Q=P[mask,:2]-np.array([x,y])
        if len(Q) and np.any((np.abs(Q@u)<l/2+.4)&(np.abs(Q@v)<w/2+.4)): return False
        for ix,iy,il,iw in self.used:
            if abs(x-ix)<(l+il)/2+1 and abs(y-iy)<(w+iw)/2+.5: return False
        self.used.append((x,y,l,w)); return True


def sign_text(body,pos,size,collection='Platform_Details',rot=(math.pi/2,0,0),mat='white'):
    cu=bpy.data.curves.new('V10 label','FONT'); cu.body=body; cu.size=size
    cu.align_x='CENTER'; cu.align_y='CENTER'; cu.extrude=.0015; cu.resolution_u=2
    font=next((f for f in bpy.data.fonts if 'Noto' in f.name),None)
    if font: cu.font=font
    o=bpy.data.objects.new('V10 label '+body,cu); COLS[collection].objects.link(o)
    o.location=pos; o.rotation_euler=rot; cu.materials.append(MATS[MI[mat]])
    o['V10_kind']='facility_label'; return o


def platform_facility(isl,x,y,z,kind,l,w):
    a=angle(isl,x); F=Matrix.Translation((x,y,z))@Matrix.Rotation(a,4,'Z'); mb=L.MeshBuilder()
    color='orange' if isl=='01-02' else ('green' if isl in ('03-04','05-06','20-21','22-23') else 'blue')
    if kind=='kiosk':
        local_box(mb,F,(0,w/2-.06,1.22),(l,.12,2.44),'wall')
        for sx in (-1,1): local_box(mb,F,(sx*(l/2-.06),0,1.22),(.12,w,2.44),'wall')
        local_box(mb,F,(0,0,.09),(l,w,.18),'concrete')
        local_box(mb,F,(0,-w/2+.04,.37),(l,.12,.74),'wall')
        local_box(mb,F,(0,0,2.51),(l+.20,w+.16,.15),'charcoal_roof')
        local_box(mb,F,(0,-w/2-.035,1.28),(l-.35,.018,1.15),'clear_glass')
        local_box(mb,F,(0,-w/2-.10,2.12),(l-.12,.16,.35),color)
        local_box(mb,F,(0,-w*.3,.78),(l-.30,.58,.10),'wood')
        for zz in (.52,.96,1.40):
            local_box(mb,F,(0,w*.25,zz),(l-.3,.50,.05),'metal')
            for j,xx in enumerate(np.linspace(-l*.4,l*.4,14)):
                local_box(mb,F,(xx,w*.25,zz+.12),(.16,.20,.21),('orange','blue','green','white')[j%4])
        local_box(mb,F,(0,0,2.37),(l-.5,.20,.04),'light')
        light=bpy.data.lights.new('V10 kiosk interior '+isl,'AREA');light.energy=35;light.shape='RECTANGLE';light.size=l-.5;light.size_y=.55
        lo=bpy.data.objects.new('V10 kiosk interior light '+isl,light);COLS['Platform_Details'].objects.link(lo)
        lo.location=F@Vector((0,0,2.30));lo.rotation_euler=(0,0,a);lo['V10_kind']='facility_light'
        local_box(mb,F,(l/2+.02,0,1.1),(.06,.85,2.1),'metal')
        label=F@Vector((0,-w/2-.19,2.12))
        sign_text('KIOSK',label,.23,rot=(math.pi/2,0,a))
    elif kind=='vending':
        F=F@Matrix.Translation((-.60,0,0))
        for j in (-1,1):
            dx=j*.52
            local_box(mb,F,(dx,0,1.03),(.95,.84,2.02),'white')
            local_box(mb,F,(dx,-.44,1.31),(.76,.04,1.09),'glass')
            for r in range(3):
                for c in range(4):
                    local_box(mb,F,(dx-.27+c*.18,-.48,1.02+r*.29),(.09,.07,.18),('blue','orange','green','white')[c])
            local_box(mb,F,(dx,-.46,.35),(.59,.07,.20),'dark')
            local_box(mb,F,(dx+.32,-.48,.64),(.10,.06,.23),'light')
        for j in range(3):
            dx=1.43+j*.34
            local_box(mb,F,(dx,0,.43),(.30,.55,.86),'metal')
            local_box(mb,F,(dx,-.29,.69),(.16,.025,.12),'dark')
    elif kind=='bench':
        for xx in (-1.12,-.56,0,.56,1.12):
            local_box(mb,F,(xx,0,.47),(.50,.55,.12),'blue')
            local_box(mb,F,(xx,.28,.78),(.50,.08,.55),'blue')
            for dx in (-.25,.25): local_rod(mb,F,(xx+dx,-.18,.68),(xx+dx,.18,.68),.024)
        for xx in (-.95,.95): local_box(mb,F,(xx,0,.23),(.10,.42,.44),'metal')
    else: # Emergency call point + fire extinguisher cabinet and utility standpipe.
        local_box(mb,F,(0,0,.95),(.42,.30,1.9),'cream')
        local_box(mb,F,(0,-.17,1.45),(.30,.08,.35),'yellow')
        local_box(mb,F,(0,-.225,1.46),(.09,.03,.09),'red')
        local_box(mb,F,(.41,0,.46),(.35,.32,.91),'red')
        local_box(mb,F,(.41,-.175,.48),(.24,.02,.61),'glass')
        local_rod(mb,F,(-.33,0,.05),(-.33,0,1.20),.055,'red')
    o=finish(mb,isl+' '+kind+f' at {x:+.1f}','Platform_Details','platform_facility',island=isl,facility_type=kind)
    REPORT['facilities'].append({'object':o.name,'island':isl,'type':kind,'x':x,'y':y,'z':z,'length':l,'width':w})


def platform_details(roofs):
    reserve=Reservations()
    for isl,R in roofs.items():
        for kind,l,w,h,target in [('kiosk',4.5,2.2,2.65,-50),('vending',3.5,1.0,2.1,30),
                                ('bench',2.85,.8,1.1,75),('emergency',1.2,.6,2.,-115)]:
            found=False
            for x in sorted(np.arange(max(R.x0+18,-120),min(R.x1-12,140),2.75),key=lambda x:abs(x-target)):
                a,b=isl.split('-'); pw=float(ty(b,x)-ty(a,x)-2*ISLANDS[isl]['edge'])
                if pw<w+4.2: continue
                for off in (0,-.9,.9):
                    y=float(center(isl,x)+off)
                    if reserve.free(isl,x,y,R.deck,l,w,h):
                        platform_facility(isl,float(x),y,R.deck,kind,l,w); found=True; break
                if found: break
            if not found: REPORT['warnings'].append('No clear site for '+isl+' '+kind)


def cameras():
    settings=[('01 roofscape',(300,306,250),(0,65,3),36),
              ('02 north roof comparison',(-264,156,142),(-10,104,7),52),
              ('03 rooftop rooms',(201,226,77),(75,133,14),55),
              ('04 Chuo acoustic screens',(174,10,28),(55,28,16),50),
              ('05 platform facilities',(-60,71.5,8.25),(-53.5,75.4,7.45),28),
              ('06 north ventilation',(-219,-27,39),(-164,20,7),50),
              ('07 Yaesu service building',(-134,272,39),(-91,208,12),48),
              ('08 plan',(20,37.2,550),(20,37.2,0),48),
              ('09 vending and seating',(24,73.4,7.9),(33,75.5,7.3),30)]
    for name,pos,target,lens in settings:
        ca=bpy.data.cameras.new('V10 '+name); ca.lens=lens; ca.clip_end=2500; ca.clip_start=.10
        ob=bpy.data.objects.new('V10 '+name,ca); COLS['Review_Cameras'].objects.link(ob)
        ob.location=pos; ob.rotation_euler=(Vector(target)-Vector(pos)).to_track_quat('-Z','Y').to_euler()
        if name.startswith('08'): ca.type='ORTHO';ca.ortho_scale=620
    SC.camera=bpy.data.objects['V10 01 roofscape']


def main():
    if SC.get('V10_platform_context'): raise RuntimeError('Already a V10 scene; run this module on the original release.')
    setup()
    roofs={i:RoofPath(i) for i in ISLANDS}
    for R in roofs.values(): build_roof(R)
    rooftop_buildings(roofs)
    barriers()
    service_buildings()
    platform_details(roofs)
    cameras()
    REPORT['new_objects']=sum(1 for o in SC.objects if o.name.startswith('V10 '))
    SC['V10_platform_context']=json.dumps(REPORT,ensure_ascii=False)
    SC['V10_accuracy']='Photo-referenced interpretive geometry; roof profile heights, plant dimensions and service-building footprints are estimates. See platform_context_v10.json.'
    bpy.ops.file.pack_all()
    bpy.context.view_layer.update()
    args=sys.argv[sys.argv.index('--')+1:]
    out=os.path.abspath(args[0]); os.makedirs(os.path.dirname(out),exist_ok=True)
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=out,compress=True)
    if len(args)>1:
        with open(args[1],'w',encoding='utf8') as f: json.dump(REPORT,f,ensure_ascii=False,indent=2)
    print('V10_BUILD_OK',out,REPORT['new_objects'],flush=True)


if __name__=='__main__': main()
