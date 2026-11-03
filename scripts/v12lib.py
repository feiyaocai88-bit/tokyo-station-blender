"""Native mesh helpers for the surface rolling-stock revision; no downloaded images required."""
import bpy, math, os, numpy as np
from mathutils import Vector, Matrix
import v5lib as L
M=[]; I={}; TEXT={}; FONT=None
def mat(key,col,rough=.5,metal=0,noise=0,accent=None,emit=0):
    m=L.principled('V12 | '+key,col,rough=rough,metal=metal)
    p=m.node_tree.nodes.get('Principled BSDF');nt=m.node_tree
    if emit:p.inputs['Emission Color'].default_value=(*col,1);p.inputs['Emission Strength'].default_value=emit
    if noise:
        tc=nt.nodes.new('ShaderNodeTexCoord');n=nt.nodes.new('ShaderNodeTexNoise');n.inputs['Scale'].default_value=noise;n.inputs['Detail'].default_value=2
        nt.links.new(tc.outputs['Object'],n.inputs['Vector'])
        r=nt.nodes.new('ShaderNodeValToRGB');r.color_ramp.elements[0].position=.3;r.color_ramp.elements[0].color=(*(accent or [v*.60 for v in col]),1)
        r.color_ramp.elements[1].position=.7;r.color_ramp.elements[1].color=(*col,1)
        nt.links.new(n.outputs['Fac'],r.inputs[0]);nt.links.new(r.outputs[0],p.inputs['Base Color'])
        b=nt.nodes.new('ShaderNodeBump');b.inputs['Strength'].default_value=.18;b.inputs['Distance'].default_value=.0007
        nt.links.new(n.outputs['Fac'],b.inputs['Height']);nt.links.new(b.outputs[0],p.inputs['Normal'])
    I[key]=len(M);M.append(m);return m
def setup():
    global FONT
    for k,c,r,m in [('steel',(.56,.59,.62),.28,.78),('door_steel',(.48,.51,.54),.34,.7),('rubber',(.013,.016,.02),.8,0),('white',(.78,.77,.72),.48,0),('ceiling',(.86,.86,.83),.6,0),('grey',(.28,.30,.31),.55,.1),('dark',(.035,.043,.052),.52,.1),('yellow',(.88,.59,.025),.62,0),('orange',(.83,.21,.015),.48,0),('green',(.25,.48,.055),.48,0),('blue',(.015,.12,.38),.52,0),('red',(.62,.025,.045),.48,0),('pink',(.68,.38,.41),.65,0),('black',(.008,.011,.014),.42,0),('tray',(.61,.60,.55),.5,0),('wood',(.32,.16,.075),.6,0)]:mat(k,c,r,m)
    mat('floor_e233',(.36,.30,.23),.82,noise=120)
    mat('floor_e235',(.42,.44,.43),.85,noise=140)
    mat('floor_green',(.15,.14,.13),.9,noise=160)
    mat('chuo_green',(.26,.06,.18),.92,noise=180,accent=(.08,.035,.12))
    mat('green_grey',(.43,.47,.51),.92,noise=200,accent=(.22,.26,.30))
    mat('green_aisle',(.32,.09,.065),.9,noise=160)
    mat('e5_green',(.31,.24,.13),.88,noise=170,accent=(.11,.09,.055))
    for k,c,ac in [('chuo_back',(.65,.22,.045),(.27,.09,.033)),('chuo_cushion',(.15,.075,.043),(.075,.04,.027)),('keihin_back',(.07,.15,.40),(.025,.04,.12)),('keihin_cushion',(.025,.055,.25),(.01,.02,.09)),('tokaido_back',(.24,.27,.29),(.08,.12,.17)),('tokaido_cushion',(.025,.09,.26),(.013,.035,.10)),('yamanote_back',(.25,.43,.08),(.11,.22,.035)),('yamanote_cushion',(.16,.31,.045),(.075,.17,.025)),('priority_back',(.40,.12,.18),(.16,.06,.10)),('priority_cushion',(.28,.08,.12),(.12,.025,.05)),('green_red',(.35,.045,.08),(.12,.017,.04)),('green_blue',(.025,.08,.21),(.012,.025,.065)),('e5_seat',(.45,.24,.16),(.19,.08,.055)),('gran_seat',(.61,.51,.36),(.34,.26,.16))]:mat(k,c,.92,noise=190,accent=ac)
    mat('lamp',(.96,.95,.90),.3,emit=4)
    # E5 ordinary cloth is a subdued grey/brown, distinct from the Green-car ochre.
    m=M[I['e5_seat']];m.diffuse_color=(.24,.21,.17,1)
    ramp=next(n for n in m.node_tree.nodes if n.type=='VALTORGB')
    ramp.color_ramp.elements[0].color=(.085,.075,.065,1);ramp.color_ramp.elements[1].color=(.24,.21,.17,1)
    mat('screen',(.12,.26,.37),.35,emit=.45)
    mat('led',(.90,.30,.025),.4,emit=2)
    m=bpy.data.materials.new('V12 | neutral clear glazing');m.use_nodes=True;nt=m.node_tree;nt.nodes.clear()
    out=nt.nodes.new('ShaderNodeOutputMaterial');tr=nt.nodes.new('ShaderNodeBsdfTransparent');tr.inputs[0].default_value=(.965,.972,.977,1)
    gl=nt.nodes.new('ShaderNodeBsdfGlossy');gl.inputs['Color'].default_value=(.92,.94,.96,1);gl.inputs['Roughness'].default_value=.055
    fr=nt.nodes.new('ShaderNodeFresnel');fr.inputs['IOR'].default_value=1.45
    mx=nt.nodes.new('ShaderNodeMixShader');nt.links.new(fr.outputs[0],mx.inputs[0]);nt.links.new(tr.outputs[0],mx.inputs[1]);nt.links.new(gl.outputs[0],mx.inputs[2]);nt.links.new(mx.outputs[0],out.inputs[0]);m.diffuse_color=(.62,.71,.77,.18)
    I['glass']=len(M);M.append(m)
    fp=os.path.join(os.path.dirname(__file__),'fonts','NotoSansJP-Medium.otf')
    FONT=bpy.data.fonts.load(fp,check_existing=True);FONT.name='V12 NotoSansJP Medium'
def box(b,c,sz,k='steel',F=None):
    if F is None:L.box(b,*c,*sz,I[k])
    else:L.box(b,0,0,0,*sz,I[k],frame=F@Matrix.Translation(c))
def rod(b,a,c,r=.015,k='steel',n=8):L.tube(b,[Vector(a),Vector(c)],r,sides=n,mat=I[k])
def tube(b,ps,r=.015,k='steel',n=8):L.tube(b,[Vector(p) for p in ps],r,sides=n,mat=I[k])
def build(b,name,c,kind,bevel=0):
    if not b.f:return None
    o=b.build('V12 '+name,c,M);o['V12_kind']=kind
    if bevel:
        mod=o.modifiers.new('Small manufactured edge radii','BEVEL');mod.width=bevel;mod.segments=2
    return o
def text(b,s,c,right=(1,0,0),up=(0,0,1),size=.15,k='white'):
    if s not in TEXT:
        cu=bpy.data.curves.new('V12 lettering','FONT');cu.body=s;cu.size=1;cu.align_x='CENTER';cu.align_y='CENTER';cu.resolution_u=2;cu.font=FONT
        o=bpy.data.objects.new('V12 lettering',cu);bpy.context.scene.collection.objects.link(o)
        me=bpy.data.meshes.new_from_object(o.evaluated_get(bpy.context.evaluated_depsgraph_get()))
        TEXT[s]=([v.co.copy() for v in me.vertices],[list(p.vertices) for p in me.polygons])
        bpy.data.objects.remove(o,do_unlink=True);bpy.data.curves.remove(cu);bpy.data.meshes.remove(me)
    vs,fs=TEXT[s];c=Vector(c);r=Vector(right);u=Vector(up);b.add([tuple(c+r*p.x*size+u*p.y*size) for p in vs],fs,I[k])
def rectpoints(x0,x1,z0,z1,r=.05,n=5):
    r=min(r,(x1-x0)*.4,(z1-z0)*.4);ps=[]
    for cx,cz,a in ((x1-r,z1-r,0),(x0+r,z1-r,90),(x0+r,z0+r,180),(x1-r,z0+r,270)):
        for q in range(n+1):
            t=math.radians(a+90*q/n);ps.append((cx+r*math.cos(t),cz+r*math.sin(t)))
    return ps
def rim(b,rect,y,width=.018,k='rubber',radius=.05):
    x0,x1,z0,z1=rect;outer=rectpoints(x0-width,x1+width,z0-width,z1+width,radius+width);inner=rectpoints(x0,x1,z0,z1,radius)
    n=len(inner);vs=[(x,y,z) for x,z in outer+inner];b.add(vs,[(j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n)],I[k])
def panel(b,rect,y,k='white'):
    a,c,d,e=rect;b.add([(a,y,d),(c,y,d),(c,y,e),(a,y,e)],[(0,1,2,3)],I[k])
def wall_with_holes(b,x0,x1,z0,z1,y,holes,k='white'):
    hs=[(max(x0,a),min(x1,c),max(z0,d),min(z1,e)) for a,c,d,e in holes if c>x0 and a<x1 and e>z0 and d<z1]
    xs=sorted(set([x0,x1]+[t for h in hs for t in h[:2]]));zs=sorted(set([z0,z1]+[t for h in hs for t in h[2:]]))
    for a,c in zip(xs,xs[1:]):
        for d,e in zip(zs,zs[1:]):
            if not any(h[0]<(a+c)/2<h[1] and h[2]<(d+e)/2<h[3] for h in hs):panel(b,(a,c,d,e),y,k)
def world_bounds(o):
    pts=[o.matrix_local@Vector(p) for p in o.bound_box]
    return Vector([min(v[i] for v in pts) for i in range(3)]),Vector([max(v[i] for v in pts) for i in range(3)])
def camera(sc,name,pos,target,lens=40,ortho=None):
    d=bpy.data.cameras.new('V12 '+name);d.lens=lens;d.clip_start=.025;d.clip_end=3000
    o=bpy.data.objects.new('V12 '+name,d);sc.collection.objects.link(o);o.location=pos;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
    if ortho:d.type='ORTHO';d.ortho_scale=ortho
    if not sc.camera:sc.camera=o
    o['V12_scene']=sc.name;return o
def light(sc,name,pos,target,power,size=6):
    d=bpy.data.lights.new('V12 '+name,'AREA');d.energy=power;d.shape='DISK';d.size=size
    o=bpy.data.objects.new('V12 '+name,d);sc.collection.objects.link(o);o.location=pos;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();return o
