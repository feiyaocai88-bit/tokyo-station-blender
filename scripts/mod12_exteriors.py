"""Photo-observed E233 subseries and E235 exterior differences.

The E233 subseries share their real design family. E235 receives its own upright,
rounded front, lamp optics and green framing. Dimensions fit the inherited shell.
"""
import bpy,bmesh,math,json
import numpy as np
from mathutils import Vector
import v5lib as L
import v12lib as H
from mod_train_bodies import half_profile


def setup():
    for key,col,r,m in [('nose_white',(.72,.75,.76),.28,.15),('face_black',(.008,.012,.017),.25,.08),('sky_blue',(.035,.35,.62),.35,.15),('lime',(.36,.66,.075),.32,.10),('shonan_green',(.045,.31,.13),.34,.15),('roof_skin',(.29,.31,.32),.78,.12),('hvac_skin',(.43,.46,.48),.51,.5),('e235_apron',(.065,.080,.10),.6,.12)]:
        H.mat(key,col,r,m)
    wind=H.M[H.I['glass']].copy();wind.name='V12 | neutral cab glazing'
    for node in wind.node_tree.nodes:
        if node.type=='BSDF_TRANSPARENT':node.inputs[0].default_value=(.56,.63,.69,1)
        if node.type in ('BSDF_GLOSSY','BSDF_ANISOTROPIC'):node.inputs['Color'].default_value=(.30,.35,.40,1)
    H.I['cab_glass']=len(H.M);H.M.append(wind)
    for key,name in [('head_lit','V5 | head lamp (lit on leading cab)'),('tail_lit','V5 | tail lamp (lit on trailing cab)')]+[(f'{line}_{kind}',f'V5 | LED {line} {kind}') for line in ('chuo','kt','yamanote','tokaido') for kind in ('front','runno')]:
        H.I[key]=len(H.M);H.M.append(bpy.data.materials[name])


def remove_faces(ob,predicate):
    ob.data=ob.data.copy();bm=bmesh.new();bm.from_mesh(ob.data)
    fs=[f for f in bm.faces if predicate([ob.matrix_local@v.co for v in f.verts])]
    bmesh.ops.delete(bm,geom=fs,context='FACES');bm.to_mesh(ob.data);bm.free();ob.data.update()


def prepare(col,body,family,cab):
    """Replace copied old AC/grilles and front fittings; original source is untouched."""
    for o in list(col.objects):
        if o.type!='MESH' or o==body:continue
        n=o.name.lower()
        if 'roof air conditioning' in n or ' ac grille' in n or n.endswith(' hvac'):
            col.objects.unlink(o)
        elif 'v5 detail |' in n or 'v11 rolling-stock fittings' in n:
            remove_faces(o,lambda ps:all(p.z>3.76 and abs(p.x)<3.5 for p in ps) or (cab and all(p.x>9.45 for p in ps)))
    # Continue E233 waist bands across the closed passenger doors. The E235
    # driver door stays stainless, while passenger doors carry vertical lime bands.
    me=body.data;names=[m.name for m in me.materials];ids={};bands=[]
    colours={'V2 | Chuo orange':'orange','V2 | Keihin Tohoku sky blue':'sky_blue','V2 | Shonan green':'shonan_green'}
    for p in me.polygons:
        name=names[p.material_index]
        if name in colours and abs(p.normal.y)>.75 and abs(p.center.x)<7.5:
            zz=[me.vertices[v].co.z for v in p.vertices]
            if max(zz)-min(zz)>.002:bands.append((min(zz),max(zz),colours[name]))
    for k in ('orange','sky_blue','shonan_green','lime','steel','door_steel','roof_skin'):
        ids[k]=len(me.materials);me.materials.append(H.M[H.I[k]])
    for p in me.polygons:
        n=names[p.material_index] if p.material_index<len(names) else ''
        z=p.center.z;x=p.center.x
        if n=='V5 | EMU roof grey anti-slip paint':p.material_index=ids['roof_skin']
        if abs(p.normal.y)<.75:continue
        if n=='V2 | Chuo orange':p.material_index=ids['orange']
        if n=='V2 | Keihin Tohoku sky blue':p.material_index=ids['sky_blue']
        if n=='V2 | Shonan green':p.material_index=ids['shonan_green']
        if family=='yamanote':
            if n=='V2 | Yamanote green':p.material_index=ids['lime'] if abs(x)<7.5 else ids['door_steel']
            if n=='V12 | steel' and 3.25<z<3.63 and any(abs(x-q)<.71 for q in (-6.7,-2.3,2.3,6.7)):
                p.material_index=ids['lime']
        elif n=='V12 | door_steel':
            band=next((k for low,high,k in bands if low<z<high),None)
            if band:p.material_index=ids[band]
    me.update();roof(col,family)


def roof(col,family):
    b=L.MeshBuilder();e235=family=='yamanote';hx=2.45 if e235 else 2.20
    # Lower sloping shells replace the block-shaped original AC. Both are twin
    # fan units; E235 has the longer, flatter housing visible in the side photos.
    zs=(3.84,4.08 if e235 else 4.12,4.15 if e235 else 4.22)
    rings=[]
    for x,w,z in [(-hx,.78,zs[0]),(-hx+.40,.95,zs[1]),(-hx+.72,.95,zs[2]),(hx-.72,.95,zs[2]),(hx-.40,.95,zs[1]),(hx,.78,zs[0])]:
        rings.append([(x,-w,3.84),(x,-w,z-.035),(x,-w+.14,z),(x,w-.14,z),(x,w,z-.035),(x,w,3.84)])
    for a,c in zip(rings,rings[1:]):
        for j in range(5):b.add([a[j],c[j],c[j+1],a[j+1]],[(0,1,2,3)],H.I['hvac_skin'])
    H.box(b,(0,0,3.85),(hx*2,1.70,.04),'dark')
    top=zs[2]
    for x in (-.87,.87):
        ps=[(x+.40*math.cos(t),.40*math.sin(t),top+.003) for t in np.linspace(0,math.tau,41)[:-1]]
        b.add(ps,[tuple(range(len(ps)))],H.I['dark'])
        H.tube(b,ps+[ps[0]],.012,'steel',6)
        for q in np.arange(-.34,.35,.075):
            d=math.sqrt(.39**2-q*q);H.rod(b,(x-d,q,top+.014),(x+d,q,top+.014),.006,'hvac_skin',4)
    for s in (-1,1):
        for x in np.arange(-hx+.55,hx-.50,.12):H.box(b,(x,s*.952,3.98),(.045,.014,.16),'dark')
    o=H.build(b,'low profile HVAC | '+col.name,col,'family_roof',.005)
    o['V12_family']=family;o['V12_roof_housing']='E235 long low shell' if e235 else 'E233 sloping shell'


def rwidth(z,width,low,high,r):
    if z<low-1e-7 or z>high+1e-7:return 0.
    h=min(z-low,high-z)
    return width if h>=r else width-r+math.sqrt(max(0,r*r-(r-h)**2))


def front(col,body,family):
    src=bpy.data.collections[col['V12_source']];xf=float(src['V5_cab_front_x']);cut=xf-.355
    # Remove the old common cap, its lamps, opaque face and black backing.
    bm=bmesh.new();bm.from_mesh(body.data)
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-6,plane_co=(cut,0,0),plane_no=(1,0,0),clear_outer=True,clear_inner=False)
    bm.to_mesh(body.data);bm.free();body.data.update()
    b=L.MeshBuilder();e235=family=='yamanote';profile=half_profile('E233',[])
    profile=sorted({round(z,6):max(y for yy,zz in profile if abs(zz-z)<1e-6 for y in [yy]) for _,z in profile}.items())
    def rear_width(z):return float(np.interp(z,[p[0] for p in profile],[p[1] for p in profile]))
    def ow(z):return rwidth(z,1.445,1.0,3.83,.35) if e235 else max(0,rear_width(z)-.035)
    def mask(z):
        if e235:return rwidth(z,1.325,1.36,3.72,.25)
        return rwidth(z,1.285,1.88,3.73,.18)*(.91+.09*(z-1.88)/1.85)
    window=(2.24,3.27,1.235) if e235 else (2.28,3.25,1.125)
    def gw(z):return rwidth(z,window[2],window[0],window[1],.055)
    def fx(y,z,off=0):return xf-(.018 if e235 else .115)*max(0,z-1.8)/2.03-(.018 if e235 else .065)*(abs(y)/1.45)**2+off
    def p(y,z,off=0):return (fx(y,z,off),y,z)
    def face(points,key,off=0,uvs=None):
        b.add([p(y,z,off) for y,z in points],[tuple(range(len(points)))],H.I[key],uvs=[uvs] if uvs else None)
    def plate(rect,key,r=.03,off=.012):face(H.rectpoints(*rect,r,8),key,off)
    def ring(rect,key,width=.014,r=.04,off=.016):
        a,d,z,t=rect;outside=H.rectpoints(a-width,d+width,z-width,t+width,r+width,8);inside=H.rectpoints(a,d,z,t,r,8);n=len(inside)
        b.add([p(y,z,off) for y,z in outside+inside],[(j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n)],H.I[key])
    breaks=[1,1.34,1.40,1.48,1.70,1.88,2.08,window[0],window[1],3.72,3.73,3.83]
    zz=sorted(set([round(float(z),6) for z in np.arange(1,3.83,.035)]+breaks))
    for za,zb in zip(zz,zz[1:]):
        z=(za+zb)/2
        wa,wb=ow(za),ow(zb);ma=min(wa,mask(za) or 1.16);mb=min(wb,mask(zb) or 1.16)
        glass=window[0]<z<window[1];ga,gb=(gw(za),gw(zb)) if glass else (0,0)
        ya=[-wa,-ma,-ga,ga,ma,wa];yb=[-wb,-mb,-gb,gb,mb,wb]
        for j in range(5):
            if (ya[j+1]-ya[j])+(yb[j+1]-yb[j])<1e-7:continue
            central=j in (1,2,3)
            if glass and j==2:key='cab_glass'
            elif e235:key='face_black' if central and z>2.08 and mask(z)>0 else 'lime'
            elif z<1.40:key='steel'
            elif central and z>=1.88 and mask(z)>0:key='face_black'
            elif 1.48<z<1.88:
                key=('nose_white' if central else 'orange') if family=='chuo' else ('sky_blue' if central else 'nose_white') if family=='keihin' else ('orange' if z>1.70 else 'shonan_green') if central else 'nose_white'
            else:key='nose_white'
            face([(ya[j],za),(ya[j+1],za),(yb[j+1],zb),(yb[j],zb)],key)
        # Rounded transition into the source side profile, with a separate E235 cap.
        for s in (-1,1):
            for k in range(6):
                def q(z,t):
                    w=rear_width(z)*(1-t)+ow(z)*t
                    return (cut+(fx(s*ow(z),z)-cut)*math.sin(t*math.pi/2),s*w,z)
                key='lime' if e235 and k>2 else 'orange' if family=='chuo' and 1.48<z<1.88 else 'nose_white' if not e235 and z>1.40 else 'steel'
                b.add([q(za,k/6),q(za,(k+1)/6),q(zb,(k+1)/6),q(zb,k/6)],[(0,1,2,3)],H.I[key],smooth=True)
    # E235 front roof edge is flat between its rounded corners.
    if e235:b.add([(cut,0,3.83),p(-ow(3.83),3.83),p(ow(3.83),3.83)],[(0,1,2)],H.I['lime'])
    ring((-window[2],window[2],window[0],window[1]),'rubber',.018,.055,.005)
    # Laminated-screen edge, narrow internal divider, and articulated lower wipers.
    H.rod(b,p(.36,window[0]+.03,.007),p(.36,window[1]-.03,.007),.009,'rubber',6)
    for s in (-1,1):
        z0=window[0]-.035
        H.tube(b,[p(s*.78,z0,.035),p(s*.61,z0+.18,.035),p(s*.20,z0+.39,.035)],.012,'black',8)
        H.rod(b,p(s*.50,z0+.16,.045),p(s*.03,z0+.53,.045),.014,'black')
    line='kt' if family=='keihin' else family;display=(-.79,.79,3.39,3.64) if e235 else (-.72,.72,3.40,3.62)
    a,d,z,t=display;plate((a-.025,d+.025,z-.018,t+.018),'black',.025)
    face([(a,z),(d,z),(d,t),(a,t)],line+'_front',.020,[(0,0),(1,0),(1,1),(0,1)])
    rz=3.10 if e235 else 2.12
    face([(-1.08,rz),(-.64,rz),(-.64,rz+.105),(-1.08,rz+.105)],line+'_runno',.021,[(0,0),(1,0),(1,1),(0,1)])
    for s in (-1,1):
        y=s*1.065;z=3.52
        plate((y-.115,y+.115,z-.115,z+.115),'black',.04,.013)
        if e235:
            plate((y-.063,y+.063,z-.065,z+.065),'head_lit',.015,.021)
            for a in (-.035,0,.035):H.rod(b,p(y+a,z-.052,.025),p(y+a,z+.052,.025),.003,'steel',4)
        else:
            for r,key,off in ((.085,'steel',.018),(.066,'head_lit',.023)):
                face([(y+r*math.cos(a),z+r*math.sin(a)) for a in np.linspace(0,math.tau,33)[:-1]],key,off)
        yy=y-s*.17;plate((yy-.05,yy+.05,z-.035,z+.035),'tail_lit',.013,.023)
    if e235:
        for j in range(22):
            z=1.61+j*.023;r=.002+j*.0012
            for k in range(59):
                y=-1.28+k*.044+(j%2)*.022
                if abs(y)+r>mask(z)-.012:continue
                face([(y+r*math.cos(a),z+r*math.sin(a)) for a in np.linspace(0,math.tau,9)[:-1]],'face_black',.005)
        H.tube(b,[p(y,1.27,.018) for y in np.linspace(-1.16,1.16,25)],.022,'lime',8)
    else:
        H.text(b,'JR',p(.96,2.01,.017),right=(0,1,0),size=.13,k='white')
        H.text(b,'EAST JAPAN RAILWAY COMPANY',p(.37,1.985,.018),right=(0,1,0),size=.028,k='white')
        H.tube(b,[p(y,1.24,.022) for y in np.linspace(-1.24,1.24,25)],.016,'steel',8)
    # Split, swept E233 snowplough versus the E235 continuous dark-grey apron.
    for s in (-1,1):
        yz=[(.38,.34),(1.13,.34),(1.34,.42),(1.34,.91),(.72,.91),(.38,.57)] if not e235 else [(.42,.31),(1.18,.31),(1.35,.39),(1.35,.85),(.72,.85),(.48,.62)]
        ps=[(xf-.13-.12*(1-z)-.06*y*y,s*y,z) for y,z in yz]
        b.add(ps,[tuple(range(len(ps)))],H.I['e235_apron' if e235 else 'nose_white'])
        for a,c in zip(ps,ps[1:]+ps[:1]):b.add([a,c,(c[0]-.12,c[1],c[2]),(a[0]-.12,a[1],a[2])],[(0,1,2,3)],H.I['e235_apron' if e235 else 'nose_white'])
        H.tube(b,[(xf-.08,s*.30,.87),(xf+.02,s*.33,.70),(xf-.02,s*.40,.55)],.021,'rubber',8)
    H.box(b,(xf-.30,0,.37),(.14,.95,.13),'dark' if not e235 else 'e235_apron')
    if not e235:
        for z in (.76,.81):H.box(b,(xf-.19,.98,z),(.025,.29,.022),'black')
    o=H.build(b,'photo front | '+family,col,'cab_front')
    # Merge the face strips to give the shallow convex face a continuous highlight.
    bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6);bm.normal_update();bm.to_mesh(o.data);bm.free()
    for poly in o.data.polygons:
        if poly.center.z>1.0 and poly.normal.x>.65 and poly.material_index in {H.I[k] for k in ('face_black','nose_white','lime','cab_glass')}:
            poly.use_smooth=True
    o.data.set_sharp_from_angle(angle=math.radians(35));o.data.update()
    o['V12_family']=family;o['V12_window']=list(window);o['V12_front_x']=xf
    o['V12_front_features']=json.dumps({'shell':'upright rounded rectangle' if e235 else 'raked E233 tapered mask','waist':'orange corners and white centre' if family=='chuo' else 'sky-blue centre' if family=='keihin' else 'orange over green centre' if family=='tokaido' else 'lime wrap and native halftone','lamp':'square LED' if e235 else 'round optic','driver_door':'stainless'},ensure_ascii=False)
    return {'front_object':o.name,'family':family,'window':list(window),'source_front_trim':cut}
