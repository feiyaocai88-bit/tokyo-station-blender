"""Native geometry and non-destructive replacement helpers for V13."""
import bpy,math,numpy as np
from mathutils import Vector,Matrix
import v11lib as B
L=B.L
M=B.M;I=B.I
R={'revision':13,'retained':[],'counts':{},'barriers':[],'tracks':[],'entrances':[]}
box=B.box;rod=B.rod;tube=B.tube;cyl=B.cyl;ring=B.ring;beam=B.beam;text=B.text
world=B.world;bounds=B.bounds;ty=B.ty;yc=B.yc;components=B.components

def count(k,n=1):R['counts'][k]=R['counts'].get(k,0)+n
def material(key,color,rough=.6,metal=0,trans=0):
    m=L.principled('V13 | '+key,color,rough=rough,metal=metal)
    m.node_tree.nodes.get('Principled BSDF').inputs['Transmission Weight'].default_value=trans
    I[key]=len(M);M.append(m);return m
def setup():
    for k in ['steel','paint','cream','white','dark','rubber','red','orange','green','blue','yellow','copper','mint','wood','bronze','concrete','granite','pale_stone','floor','glass','window','lamp','soil','hedge']:
        I[k]=len(M);M.append(bpy.data.materials['V11 | '+k])
    I['brick']=len(M);M.append(bpy.data.materials['V2 | 109 x 60.5 mm header brick'])
    for k,c,rough,metal in [('ballast_a',(.20,.18,.15),.92,0),('ballast_b',(.32,.30,.27),.92,0),('ballast_c',(.43,.42,.39),.9,0),('pc_sleeper',(.59,.56,.49),.85,0),('rust',(.17,.075,.032),.8,.25),('stone',(.53,.52,.46),.82,0),('iron',(.06,.075,.073),.45,.7),('copper_aged',(.24,.28,.23),.65,.5),('leaf_dark',(.075,.14,.04),.9,0),('leaf_light',(.13,.22,.055),.9,0),('metro_tile',(.68,.67,.62),.55,0)]:
        material(k,c,rough,metal)
    material('gate_iron',(.24,.26,.25),.38,.55)
    material('entrance_glass',(.82,.91,.92),.035,0,1.0)
def col(key):return L.collection('V13_'+key)
def build(mb,name,group,kind=None,frame=None,**props):
    if not mb.f:return None
    o=mb.build('V13 '+name,col(group),M)
    if frame is not None:o.matrix_world=frame
    o['V13_kind']=kind or group
    for k,v in props.items():o[k]=v
    return o
def retire(o):
    original=o.name;cs=[c.name for c in o.users_collection]
    o.name=original+' [before V13]';o['V13_original_name']=original
    for c in list(o.users_collection):c.objects.unlink(o)
    c=col('Replaced_hidden');c.objects.link(o);c.hide_render=True;c.hide_viewport=True
    o.hide_render=True;o.hide_viewport=True
    R['retained'].append({'original':original,'retained':o.name,'collections':cs})
def copy_replace(o):
    name=o.name;cs=list(o.users_collection);q=o.copy();q.data=o.data.copy();retire(o);q.name=name
    for c in cs:c.objects.link(q)
    q.hide_render=False;q.hide_viewport=False;q['V13_modified_copy']=True
    return q
def camera(name,pos,target,lens=45,ortho=None,scene=None):
    sc=scene or bpy.context.scene;d=bpy.data.cameras.new('V13 '+name);d.lens=lens;d.clip_start=.05;d.clip_end=3000
    o=bpy.data.objects.new(d.name,d);sc.collection.objects.link(o);o.location=pos;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
    if ortho:d.type='ORTHO';d.ortho_scale=ortho
    o['V13_scene']=sc.name;return o
def ellipsoid(mb,c,scale,key,n=12,rings=6,seed=0):
    rng=np.random.default_rng(seed);v=[]
    for j in range(rings+1):
        a=math.pi*j/rings
        for i in range(n):
            t=math.tau*i/n;rr=1+rng.uniform(-.09,.09)
            v.append((c[0]+scale[0]*math.sin(a)*math.cos(t)*rr,c[1]+scale[1]*math.sin(a)*math.sin(t)*rr,c[2]+scale[2]*math.cos(a)*rr))
    f=[(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for j in range(rings) for i in range(n)]
    mb.add(v,f,I[key],smooth=True)
def boolean_cut(obj,cutter):
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    for previous in list(obj.modifiers):
        if previous.type=='BEVEL':bpy.ops.object.modifier_apply(modifier=previous.name)
    m=obj.modifiers.new('V13 real opening','BOOLEAN');m.operation='DIFFERENCE';m.solver='EXACT';m.object=cutter
    if obj.get('V13_kind')=='metro_passage_shell':m.use_self=True
    bpy.ops.object.modifier_apply(modifier=m.name);obj.select_set(False)
