"""Photo-reference fittings, native meshes, reversible V20 source preservation."""
import bpy,math,json,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
import v5lib as L
from v16lib import snapshot
from v14lib import world,component_labels
M=[];I={};R={'revision':21,'retained':[],'counts':{},'platforms':{},'rooms':[],'equipment':[]}
D=json.loads(Path(__file__).with_name('targets.json').read_text(encoding='utf8'))
def ty(k,x):return float(np.interp(x,D['X'],D['target'][k]))
def yc(isl,x):
 a,b=isl.split('-');return (ty(a,x)+ty(b,x))/2
def angle(isl,x):return math.atan2(yc(isl,x+.1)-yc(isl,x-.1),.2)
def frame(isl,x,z,y=None):return Matrix.Translation((x,yc(isl,x) if y is None else y,z))@Matrix.Rotation(angle(isl,x),4,'Z')
def col(n):return L.collection('V21_'+n)
def count(k,n=1):R['counts'][k]=R['counts'].get(k,0)+n
def setup():
 for k,c,r,m in [('cream',(.59,.565,.46),.65,.25),('white',(.72,.73,.69),.52,.12),('silver',(.48,.52,.54),.30,.75),('trim',(.68,.70,.70),.30,.8),('dark',(.07,.085,.09),.65,.3),('black',(.015,.02,.025),.47,.1),('lens',(.02,.07,.10),.12,.3),('glass',(.75,.86,.88),.12,0),('glazing',(.63,.73,.72),.23,0),('yellow',(.84,.61,.04),.64,0),('red',(.65,.025,.02),.55,.15),('green',(.22,.49,.035),.60,0),('blue',(.025,.27,.49),.60,0),('orange',(.84,.22,.025),.64,0),('light',(.86,.91,.87),.35,0),('tile',(.43,.44,.41),.78,0),('joint',(.15,.16,.145),.85,0),('stone',(.13,.16,.18),.40,0),('seat',(.16,.26,.35),.68,.05),('bronze',(.39,.27,.12),.48,.65)]:
  mat=L.principled('V21 | '+k,c,rough=r,metal=m);I[k]=len(M);M.append(mat);bs=mat.node_tree.nodes.get('Principled BSDF')
  if k in ('glass','glazing'):bs.inputs['Transmission Weight'].default_value=.92 if k=='glass' else .55;bs.inputs['IOR'].default_value=1.45
  if k=='light':bs.inputs['Emission Color'].default_value=(*c,1);bs.inputs['Emission Strength'].default_value=2.5
  if k in ('cream','stone','tile'):
   nt=mat.node_tree;co=nt.nodes.new('ShaderNodeTexCoord');tx=nt.nodes.new('ShaderNodeTexNoise');tx.inputs['Scale'].default_value=65 if k=='stone' else 18;nt.links.new(co.outputs['Object'],tx.inputs['Vector'])
   ramp=nt.nodes.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(*(v*.82 for v in c),1);ramp.color_ramp.elements[1].color=(*c,1);nt.links.new(tx.outputs['Fac'],ramp.inputs[0]);nt.links.new(ramp.outputs['Color'],bs.inputs['Base Color'])
def retire(o):
 n=o.name;cs=list(o.users_collection);o.name=n+' [before V21]';o['V21_original_name']=n
 for c in cs:c.objects.unlink(o)
 c=col('Replaced_hidden');c.objects.link(o);c.hide_render=True;c.hide_viewport=True;o.hide_render=True;o.hide_viewport=True
 R['retained'].append({'original':n,'retained':o.name,'collections':[c.name for c in cs]})
def copy_source(o):
 n=o.name;cs=list(o.users_collection);q=o.copy()
 if o.data:q.data=o.data.copy()
 retire(o);q.name=n
 for c in cs:c.objects.link(q)
 q.hide_render=False;q.hide_viewport=False;q['V21_modified_copy']=True;return q
def build(mb,n,g,isl=None):
 if not mb.f:return None
 o=mb.build('V21 '+n,col(g),M);o['V21_kind']=g
 if isl:o['island']=isl
 return o
def box(mb,p,s,k='silver',F=None):L.box(mb,*p,*s,I[k]) if F is None else L.box(mb,0,0,0,*s,I[k],frame=F@Matrix.Translation(p))
def tube(mb,p,r=.02,k='silver',n=8,F=None):L.tube(mb,[Vector(v) if F is None else F@Vector(v) for v in p],r,n,I[k])
def cyl(mb,p,r,h,k='silver',n=16,F=None):
 T=Matrix.Translation(p) if F is None else F@Matrix.Translation(p);L.lathe(mb,[(r,-h/2),(r,h/2)],(0,0),n,I[k],cap_top=True,cap_bottom=True,frame=T)
def beam(mb,p,q,w,h,k='cream',F=None,section=True):
 p=Vector(p);q=Vector(q)
 if F is not None:p=F@p;q=F@q
 d=q-p;T=Matrix.Translation((p+q)/2)@d.to_track_quat('X','Z').to_matrix().to_4x4()
 if not section:box(mb,(0,0,0),(d.length,w,h),k,T);return
 box(mb,(0,0,0),(d.length,max(.018,w*.09),h),k,T)
 for s in (-1,1):box(mb,(0,0,s*(h/2-.012)),(d.length,w,.024),k,T)
def text(body,p,size=.12,key='black',right=(1,0,0),up=(0,0,1),group='Labels',F=None):
 r=Vector(right);u=Vector(up);p=Vector(p)
 if F is not None:r=F.to_3x3()@r;u=F.to_3x3()@u;p=F@p
 n=r.cross(u);cu=bpy.data.curves.new('V21 '+body,'FONT');cu.body=body;cu.size=size;cu.align_x='CENTER';cu.align_y='CENTER';cu.resolution_u=2
 font=next((f for f in bpy.data.fonts if 'NotoSansJP' in f.name),None)
 if font:cu.font=font
 cu.materials.append(M[I[key]]);o=bpy.data.objects.new(cu.name,cu);col(group).objects.link(o)
 o.matrix_world=Matrix(((r.x,u.x,n.x,p.x),(r.y,u.y,n.y,p.y),(r.z,u.z,n.z,p.z),(0,0,0,1)));o['V21_kind']=group;return o
def bvh(o):return BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(p.vertices) for p in o.data.polygons])
def bounds(o):
 v=np.array([o.matrix_world@Vector(p) for p in o.bound_box]);return v.min(0),v.max(0)
def lamp(n,F,p,length=3,power=100):
 d=bpy.data.lights.new('V21 '+n,'AREA');d.energy=power;d.shape='RECTANGLE';d.size=length;d.size_y=.2
 o=bpy.data.objects.new(d.name,d);col('Lighting').objects.link(o);o.matrix_world=F@Matrix.Translation(p);o['V21_kind']='Lighting'
