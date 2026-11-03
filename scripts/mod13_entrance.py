"""Photo-informed central imperial porte-cochere, gate and planted forecourt."""
import bpy,bmesh,math,numpy as np
from mathutils import Vector
import v13lib as H
L=H.L

def lathe(mb,profile,x,y,key,n=40):L.lathe(mb,profile,(x,y),n,H.I[key],cap_top=True,cap_bottom=True)
def pine(mb,x,y,height,seed):
    rng=np.random.default_rng(seed)
    trunk=[(x,y,.65),(x+.16,y+.08,height*.42),(x-.12,y+.16,height*.77),(x+.16,y+.13,height)]
    H.tube(mb,trunk,.12,'wood',9)
    for j,z in enumerate(np.linspace(height*.4,height*.93,5)):
        t=j*2.38;reach=1.65*(1-j*.09);end=(x+math.cos(t)*reach,y+math.sin(t)*reach,z)
        H.tube(mb,[(x,y,z-.35),(x+math.cos(t)*reach*.65,y+math.sin(t)*reach*.65,z-.12),end],.065,'wood',8)
        # Clipped pine foliage consists of flattened irregular sprays, not spheres.
        for k in range(7):
            a=k*math.tau/7;xx=end[0]+.50*math.cos(a);yy=end[1]+.45*math.sin(a)
            H.ellipsoid(mb,(xx,yy,z+.12+rng.uniform(-.07,.07)),(.64,.53,.20),'leaf_dark' if k%2 else 'leaf_light',n=10,rings=4,seed=seed+j*10+k)
    H.ellipsoid(mb,(x+.16,y+.13,height),(.64,.56,.30),'leaf_dark',seed=seed+80)

def run():
    oldnames=[]
    for o in list(bpy.context.scene.objects):
        if o.hide_render or o.type in ('CAMERA','LIGHT'):continue
        if ('imperial' in o.name.lower() or o.name.startswith('Central deep entrance') or o.name=='V3 Central recessed masonry masonry horizontal band'):
            oldnames.append(o.name);H.retire(o)
    # A shared detail mesh contains the old entrance sash as well as facade windows.
    src=bpy.data.objects.get('V3 central finer sash subdivisions')
    if src:
        q=H.copy_replace(src);bm=bmesh.new();bm.from_mesh(q.data)
        remove=[]
        for f in bm.faces:
            c=q.matrix_world@f.calc_center_median()
            if abs(c.x)<2.15 and c.y<-7.5 and c.z<6.5:remove.append(f)
        bmesh.ops.delete(bm,geom=remove,context='FACES');bm.to_mesh(q.data);bm.free()
    b=L.MeshBuilder()
    H.box(b,(0,-10.7,.55),(10.2,7.3,.34),'stone')
    # The recess is real space with a door at its back, rather than a flat facade pane.
    for s in (-1,1):
        H.box(b,(s*1.92,-7.14,3.05),(.40,2.1,4.70),'pale_stone')
        H.box(b,(s*1.62,-6.28,2.95),(.20,.40,4.5),'stone')
    H.box(b,(0,-7.14,5.32),(4.22,2.1,.44),'pale_stone')
    H.box(b,(0,-6.30,4.98),(3.25,.4,.28),'stone')
    H.box(b,(0,-5.85,2.89),(3.05,.10,4.28),'dark')
    H.box(b,(0,-7.1,.76),(3.6,2.5,.14),'stone')
    H.box(b,(0,-7.05,6.51),(4.2,.72,2.52),'brick')
    for s in (-1,1):
        for yy in (-12.85,-9.10):
            xx=s*3.65
            lathe(b,[(1.02,.56),(1.02,.85),(.96,.95),(.88,1.02),(.88,5.20),(.95,5.30),(1.02,5.40),(1.02,5.60)],xx,yy,'brick')
            # White stone belts alternate with broad red-brick drums.
            for z in [1.02,1.93,2.84,3.75,4.66]:lathe(b,[(.90,z),(.95,z+.04),(.95,z+.22),(.90,z+.26)],xx,yy,'stone')
            lathe(b,[(1.08,.56),(1.08,.75),(1.01,.82)],xx,yy,'stone')
            lathe(b,[(.92,5.08),(1.03,5.24),(1.05,5.43),(1.13,5.49),(1.13,5.68)],xx,yy,'stone')
            # Carved capitals: layered abacus, scroll rounds and central rosette.
            for dx in (-.72,.72):
                H.ring(b,(xx+dx,yy-.92,5.37),.19,.060,'pale_stone','XZ',18)
                H.ring(b,(xx+dx,yy-.97,5.37),.095,.035,'stone','XZ',16)
            H.ellipsoid(b,(xx,yy-1.0,5.38),(.26,.06,.19),'pale_stone',n=12,rings=4)
    H.build(b,'Imperial round brick piers stone belts and recessed doorway','Imperial_Architecture','imperial_structure')
    b=L.MeshBuilder()
    # Entablature follows the rounded front piers and has layered weathered stone.
    for z,thick,w,d in [(5.72,.22,9.7,5.9),(5.99,.32,9.55,5.7),(6.25,.13,9.90,5.95),(6.42,.16,10.05,6.1)]:
        H.box(b,(0,-11.10,z),(w,d,thick),'stone')
    for x in np.arange(-4.6,4.61,.23):H.box(b,(x,-14.04,6.26),(.11,.14,.12),'pale_stone')
    for x in (-3.65,3.65):
        lathe(b,[(1.03,6.50),(1.03,6.65),(.95,6.68),(.92,6.97),(.84,7.20),(.61,7.42),(.18,7.56)],x,-12.85,'stone')
        H.cyl(b,(x,-12.85,7.62),.10,.24,'stone',16)
        for a in np.linspace(0,math.tau,13)[:-1]:
            pts=[]
            for r,z in [(.93,6.69),(.90,6.98),(.82,7.20),(.60,7.43),(.17,7.57)]:pts.append((x+r*math.cos(a),-12.85+r*math.sin(a),z))
            H.tube(b,pts,.025,'pale_stone',6)
    crest=[(-2.85,6.50),(-2.85,6.88),(-2.0,6.93),(-1.54,7.15),(0,7.84),(1.54,7.15),(2,6.93),(2.85,6.88),(2.85,6.50)]
    v=[(x,y,z) for y in (-14.02,-13.65) for x,z in crest];n=len(crest)
    b.add(v,[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],H.I['stone'])
    for dy,dz,r in [(0,0,.055),(-.025,-.14,.035)]:H.tube(b,[(x,-14.09+dy,z+dz) for x,z in crest[:8]],r,'pale_stone',8)
    # Recessed rectangular ceiling coffers and lamps visible from below.
    for x in (-2.0,0,2.0):
        for y in (-12.8,-10.8,-9.1):
            H.box(b,(x,y,5.584),(1.75,1.45,.045),'cream');H.box(b,(x,y,5.56),(1.42,1.14,.02),'pale_stone')
    H.cyl(b,(0,-11.1,5.48),.20,.12,'bronze',20);H.cyl(b,(0,-11.1,5.40),.14,.035,'lamp',20)
    H.build(b,'Imperial carved cornice crest domed stone caps and coffers','Imperial_Architecture','imperial_cornice')
    b=L.MeshBuilder();y=-6.08
    # Two iron gate leaves; circular floral centres and fan-shaped forged bars.
    for s in (-1,1):
        cx=s*.72
        for x in (s*.035,s*1.43):H.box(b,(x,y,2.70),(.065,.10,3.86),'iron')
        for z in (.80,1.05,4.51,4.65):H.box(b,(cx,y,z),(1.40,.10,.07),'iron')
        for x in np.arange(.14,1.4,.16):H.rod(b,(s*x,y,.98),(s*x,y,2.5),.014,'iron',6)
        for z in np.arange(1.15,4.45,.30):H.box(b,(s*1.33,y-.025,z),(.045,.10,.045),'bronze')
        c=(cx,y-.03,3.08)
        for rad in (.10,.32,.46):H.ring(b,c,rad,.018,'iron','XZ',40)
        for a in np.linspace(0,math.tau,17)[:-1]:
            H.rod(b,(cx+.09*math.cos(a),y-.05,3.08+.09*math.sin(a)),(cx+.43*math.cos(a),y-.05,3.08+.43*math.sin(a)),.012,'bronze',6)
        for t in np.linspace(-1,1,9):
            H.tube(b,[(cx+t*.15,y,2.72),(cx+t*.40,y,2.05),(cx+t*.65,y,1.09)],.013,'iron',6)
            H.tube(b,[(cx+t*.24,y,3.44),(cx+t*.46,y,3.85),(cx+t*.65,y,4.45)],.013,'iron',6)
        H.rod(b,(s*.14,y-.09,2.45),(s*.14,y-.09,2.75),.026,'bronze')
    gate=H.build(b,'Imperial double iron gate radial rosettes bars and handles','Imperial_Gate','imperial_gate')
    for poly in gate.data.polygons:
        if poly.material_index==H.I['iron']:poly.material_index=H.I['gate_iron']
    d=bpy.data.lights.new('V13 Imperial soffit light','AREA');d.energy=240;d.shape='DISK';d.size=2.4;d.color=(1,.95,.85)
    light=bpy.data.objects.new(d.name,d);H.col('Imperial_Lights').objects.link(light);light.location=(0,-11.1,5.30)
    light.rotation_euler=(Vector((0,-6.08,2.65))-light.location).to_track_quat('-Z','Y').to_euler()
    # The actual doorway is separated from the plaza by a planted, balustraded apron.
    b=L.MeshBuilder()
    H.box(b,(0,-17.35,.44),(24.3,6.0,.34),'stone')
    for xx in (-7.7,7.7):
        H.box(b,(xx,-16.7,.65),(8.7,4.3,.20),'soil')
        for yy in (-18.8,-14.6):H.box(b,(xx,yy,.70),(8.7,.24,.25),'pale_stone')
        for xedge in (xx-4.25,xx+4.25):H.box(b,(xedge,-16.7,.70),(.25,4.3,.25),'pale_stone')
        for j in range(11):H.ellipsoid(b,(xx-3.85+j*.77,-18.45,.93),(.50,.43,.30),'leaf_dark',seed=j+int(xx*10)%53)
    for a,c in [(-12,-2.0),(2.0,12)]:
        H.box(b,((a+c)/2,-14.45,.86),(c-a,.38,.15),'stone')
        H.box(b,((a+c)/2,-14.45,1.88),(c-a,.42,.15),'pale_stone')
        for xx in np.arange(a+.25,c,.42):
            profile=[(.10,.94),(.10,1.03),(.06,1.11),(.105,1.38),(.06,1.65),(.10,1.76),(.10,1.83)]
            lathe(b,profile,float(xx),-14.45,'pale_stone',12)
        for xx in (a,c):H.box(b,(xx,-14.45,1.35),(.40,.48,1.08),'stone')
    # Front stone tablet and flag poles are outside the retained pedestrian path.
    H.box(b,(-5.7,-20.0,.91),(2.5,.62,.78),'stone')
    H.text(b,'東京駅',(-5.7,-20.321,1.01),size=.32,key='iron')
    H.box(b,(5.7,-20.0,.85),(2.1,.60,.66),'stone')
    for x in (-6.5,6.5):
        H.cyl(b,(x,-17.85,4.55),.039,7.70,'steel',12)
        H.cyl(b,(x,-17.85,.78),.15,.30,'stone',16)
        H.ellipsoid(b,(x,-17.85,8.43),(.068,.068,.08),'bronze',n=10,rings=4)
    for xx,yy,hh,seed in [(-9.1,-16.7,4.9,10),(-4.9,-16.0,3.2,20),(9.2,-16.7,4.8,30),(4.9,-16.0,3.3,40)]:pine(b,xx,yy,hh,seed)
    H.build(b,'Imperial forecourt stone balustrade clipped pines and name tablet','Imperial_Garden','imperial_forecourt')
    # Retain any diorama figures displaced by the new planter in a hidden group.
    for o in list(bpy.context.scene.objects):
        if o.type=='EMPTY' and 'person' in o.name.lower():
            p=o.matrix_world.translation
            if abs(p.x)<12.3 and -20.5<p.y<-14.1 and p.z<1:H.retire(o)
    H.R['imperial_entrance']={'retired_parts':len(oldnames),'reference':'railwaystation.jp central imperial porte-cochere photograph','gate_recess_y':-6.08,'door_clear_width':2.86,'gate_bottom':.8,'gate_top':4.65,'forecourt_width':24.3,'interpretation':'Photographic proportions fitted to the retained facade; dimensions and small carving are estimated.'}
