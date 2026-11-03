"""Shared native-mesh helpers for the V11 photographic refinement."""
import bpy, math, json, os, numpy as np
from mathutils import Vector, Matrix
import v5lib as L
SC=bpy.context.scene
HERE=os.path.dirname(__file__)
D=json.load(open(os.path.join(HERE,'targets.json')))
GX=np.array(D['X']); TRACKS={k:np.array(v) for k,v in D['target'].items()}
M=[];I={}; REPORT={'revision':11,'retired':[],'counts':{},'approximations':[]}

def count(k,n=1):REPORT['counts'][k]=REPORT['counts'].get(k,0)+n
def mat(key,color,rough=.6,metal=0,trans=0,emit=0,noise=0):
    m=L.principled('V11 | '+key,color,rough=rough,metal=metal)
    b=m.node_tree.nodes.get('Principled BSDF'); b.inputs['Transmission Weight'].default_value=trans
    if emit:b.inputs['Emission Color'].default_value=(*color,1);b.inputs['Emission Strength'].default_value=emit
    if noise:
        nt=m.node_tree;n=nt.nodes.new('ShaderNodeTexNoise');n.inputs['Scale'].default_value=noise;n.inputs['Detail'].default_value=3
        tex=nt.nodes.new('ShaderNodeTexCoord');nt.links.new(tex.outputs['Object'],n.inputs['Vector'])
        r=nt.nodes.new('ShaderNodeValToRGB');r.color_ramp.elements[0].color=(*(v*.76 for v in color),1);r.color_ramp.elements[1].color=(*color,1)
        nt.links.new(n.outputs['Fac'],r.inputs[0]);nt.links.new(r.outputs[0],b.inputs['Base Color'])
        bm=nt.nodes.new('ShaderNodeBump');bm.inputs['Strength'].default_value=.13;bm.inputs['Distance'].default_value=.012
        nt.links.new(n.outputs['Fac'],bm.inputs['Height']);nt.links.new(bm.outputs[0],b.inputs['Normal'])
    I[key]=len(M);M.append(m);return m

def setup():
    fontpath=os.path.join(HERE,'fonts','NotoSansJP-Medium.otf')
    if not any('NotoSansJP' in f.name for f in bpy.data.fonts):bpy.data.fonts.load(fontpath)
    for key,col,rough,metal in [
        ('steel',(.53,.56,.56),.3,.75),('paint',(.69,.70,.66),.62,.12),('cream',(.64,.59,.46),.65,.08),
        ('white',(.82,.83,.79),.45,.05),('dark',(.032,.041,.047),.58,.15),('rubber',(.018,.022,.025),.85,0),
        ('red',(.67,.018,.028),.3,.25),('orange',(.84,.22,.02),.5,0),('green',(.20,.40,.10),.5,0),
        ('blue',(.015,.10,.30),.5,0),('yellow',(.86,.61,.04),.65,0),('copper',(.22,.25,.20),.48,.5),
        ('mint',(.23,.51,.42),.6,.25),('wood',(.24,.12,.055),.6,.05),('bronze',(.18,.16,.12),.55,.55)]: mat(key,col,rough,metal)
    mat('concrete',(.42,.43,.40),noise=3)
    mat('granite',(.60,.61,.57),noise=38)
    mat('pale_stone',(.69,.70,.66),noise=48)
    mat('plaza_dark',(.42,.46,.46),noise=45)
    mat('floor',(.53,.54,.52),noise=32)
    mat('glass',(.61,.76,.79),.14,.05,trans=.92)
    mat('window',(.055,.10,.12),.17,.18,trans=.50)
    mat('lamp',(.91,.94,.86),.3,emit=2.2)
    mat('led',(.84,.39,.045),.3,emit=1.5)
    mat('soil',(.12,.095,.06),noise=6)
    mat('hedge',(.09,.20,.048),noise=15)

def col(key):return L.collection('V11_'+key)
def build(mb,name,group,kind=None,frame=None,**props):
    if not mb.f:return None
    o=mb.build('V11 '+name,col(group),M)
    if frame is not None:o.matrix_world=frame
    o['V11_kind']=kind or group
    for k,v in props.items():o[k]=v
    return o
def world(o):
    a=np.empty(len(o.data.vertices)*3);o.data.vertices.foreach_get('co',a);m=np.array(o.matrix_world)
    return a.reshape(-1,3)@m[:3,:3].T+m[:3,3]
def bounds(o):
    v=world(o);return v.min(0),v.max(0)
def retire(o,rename=False):
    original=o.name
    if rename:o.name=original+' [before V11]'
    o['V11_original_name']=original
    c=col('Replaced_hidden');c.hide_render=True;c.hide_viewport=True
    for cc in list(o.users_collection):cc.objects.unlink(o)
    c.objects.link(o);o.hide_render=True;o.hide_viewport=True
    REPORT['retired'].append({'original':original,'retained':o.name})
def copy_replace(o):
    n=o.name; cs=list(o.users_collection);new=o.copy();new.data=o.data.copy();retire(o,True);new.name=n
    for c in cs:c.objects.link(new)
    new.hide_render=False;new.hide_viewport=False;new['V11_modified_copy']=True;return new
def box(mb,c,size,key='steel',a=0,F=None):
    if F is None:L.box(mb,*c,*size,I[key],rotz=a)
    else:L.box(mb,0,0,0,*size,I[key],frame=F@Matrix.Translation(c))
def rod(mb,a,b,r=.025,key='steel',n=8):L.tube(mb,[Vector(a),Vector(b)],r,sides=n,mat=I[key])
def tube(mb,pts,r=.025,key='steel',n=8):L.tube(mb,[Vector(p) for p in pts],r,sides=n,mat=I[key])
def cyl(mb,c,r,h,key='steel',n=24):L.lathe(mb,[(r,c[2]-h/2),(r,c[2]+h/2)],c,n,I[key],cap_top=True,cap_bottom=True)
def ring(mb,c,r,t,key='steel',plane='XY',n=40):
    pts=[]
    for a in np.linspace(0,math.tau,n+1):
        if plane=='XY':pts.append((c[0]+r*math.cos(a),c[1]+r*math.sin(a),c[2]))
        elif plane=='XZ':pts.append((c[0]+r*math.cos(a),c[1],c[2]+r*math.sin(a)))
        else:pts.append((c[0],c[1]+r*math.cos(a),c[2]+r*math.sin(a)))
    tube(mb,pts,t,key,6)
def beam(mb,p,q,width,depth,key='cream'):
    p,q=Vector(p),Vector(q);z=(q-p).normalized();up=Vector((0,0,1))
    if abs(z.dot(up))>.98:up=Vector((0,1,0))
    x=z.cross(up).normalized();y=z.cross(x).normalized();F=Matrix((x,y,z)).transposed().to_4x4();F.translation=(p+q)/2
    box(mb,(0,0,0),(width,depth,(q-p).length),key,F=F)
def hcolumn(mb,x,y,z0,z1,w=.32,d=.32,key='paint'):
    box(mb,(x,y,(z0+z1)/2),(.035,d,z1-z0),key)
    for yy in (-d/2,d/2):box(mb,(x,y+yy,(z0+z1)/2),(w,.035,z1-z0),key)
def ty(k,x):return np.interp(x,GX,TRACKS[k])
def yc(isl,x):a,b=isl.split('-');return (ty(a,x)+ty(b,x))/2
def keepouts():return json.loads(SC.get('V6_platform_keepouts','[]'))
def free_stair(isl,x,y,margin=.4):
    for k in keepouts():
        if k.get('kind')!='stairwell' or k['island']!=isl:continue
        dx=x-k['c'][0];dy=y-k['c'][1];ux,uy=k['u'];u=dx*ux+dy*uy;v=-dx*uy+dy*ux
        if -2-margin<u<14+margin and abs(v)<2.1+margin:return False
    return True
def components(o):
    p=world(o);lab=np.arange(len(p));e=np.array([e.vertices[:] for e in o.data.edges],int)
    for _ in range(150):
        old=lab.copy();m=np.minimum(lab[e[:,0]],lab[e[:,1]]);np.minimum.at(lab,e[:,0],m);np.minimum.at(lab,e[:,1],m);lab=lab[lab]
        if np.array_equal(lab,old):break
    roots,inv=np.unique(lab,return_inverse=True)
    lo=np.full((len(roots),3),np.inf);hi=np.full((len(roots),3),-np.inf)
    np.minimum.at(lo,inv,p);np.maximum.at(hi,inv,p)
    return list(zip(lo,hi))
_texts={}
def text(mb,s,c,right=(1,0,0),up=(0,0,1),size=.18,key='white'):
    if s not in _texts:
        font=next((f for f in bpy.data.fonts if 'NotoSansJP' in f.name),None)
        cu=bpy.data.curves.new('V11 temp text','FONT');cu.body=s;cu.size=1;cu.align_x='CENTER';cu.align_y='CENTER';cu.resolution_u=2
        if font:cu.font=font
        ob=bpy.data.objects.new('V11 temp text',cu);SC.collection.objects.link(ob)
        me=bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
        _texts[s]=([v.co.copy() for v in me.vertices],[list(p.vertices) for p in me.polygons])
        bpy.data.objects.remove(ob,do_unlink=True);bpy.data.curves.remove(cu);bpy.data.meshes.remove(me)
    v,f=_texts[s];c=Vector(c);right=Vector(right);up=Vector(up)
    mb.add([tuple(c+right*p.x*size+up*p.y*size) for p in v],f,I[key])
def camera(name,pos,target,lens=34,ortho=None):
    ca=bpy.data.cameras.new('V11 '+name);ca.lens=lens;ca.clip_start=.035;ca.clip_end=3000
    ob=bpy.data.objects.new('V11 '+name,ca);col('Review_Cameras').objects.link(ob);ob.location=pos
    ob.rotation_euler=(Vector(target)-Vector(pos)).to_track_quat('-Z','Y').to_euler()
    if ortho:ca.type='ORTHO';ca.ortho_scale=ortho
    return ob
def light(name,pos,power,size=3,color=(1,.94,.82),target=None,group='Lights'):
    d=bpy.data.lights.new('V11 '+name,'AREA');d.energy=power;d.shape='DISK';d.size=size;d.color=color
    o=bpy.data.objects.new('V11 '+name,d);col(group).objects.link(o);o.location=pos
    if target:o.rotation_euler=(Vector(target)-Vector(pos)).to_track_quat('-Z','Y').to_euler()
    return o
