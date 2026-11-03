"""Native Chuo aerial-roof correction; photo-derived dimensions."""
import bpy, math, json, numpy as np
from pathlib import Path
from mathutils import Vector, Matrix
import v5lib as L
from v16lib import snapshot
from v14lib import world, component_labels
M=[]; I={}; R={'revision':22,'retained':[],'counts':{},'frames':[],'masts':[],'catenary':{}}
D=json.loads(Path(__file__).with_name('targets.json').read_text(encoding='utf8'))
def ty(k,x):return float(np.interp(x,D['X'],D['target'][k]))
def yc(x):return (ty('01',x)+ty('02',x))/2
def angle(x):return math.atan2(yc(x+.1)-yc(x-.1),.2)
def frame(x,y=None,z=16.51):return Matrix.Translation((x,yc(x) if y is None else y,z))@Matrix.Rotation(angle(x),4,'Z')
def col(n):return L.collection('V22_'+n)
def count(k,n=1):R['counts'][k]=R['counts'].get(k,0)+n
def setup():
 for k,c,r,m in [('silver',(.48,.51,.54),.31,.72),('trim',(.65,.68,.69),.27,.8),('seam',(.055,.065,.073),.68,.1),('steel',(.23,.27,.28),.38,.6),('cream',(.64,.63,.55),.47,.25),('black',(.012,.018,.021),.43,.1),('glass',(.17,.23,.26),.16,.08),('lens',(.025,.07,.10),.10,.4),('concrete',(.34,.35,.34),.84,0),('tile',(.42,.43,.40),.78,0),('yellow',(.77,.54,.035),.66,0),('red',(.70,.04,.02),.59,0),('white',(.78,.80,.76),.61,.1),('light',(.86,.91,.88),.36,0),('soffit',(.25,.27,.25),.62,.25),('screen',(.025,.065,.056),.34,.05)]:
  mat=L.principled('V22 | '+k,c,rough=r,metal=m);I[k]=len(M);M.append(mat)
  b=mat.node_tree.nodes.get('Principled BSDF')
  if k=='glass':b.inputs['Transmission Weight'].default_value=.72;b.inputs['IOR'].default_value=1.46
  if k in ('light','screen'):b.inputs['Emission Color'].default_value=(*c,1);b.inputs['Emission Strength'].default_value=2.2 if k=='light' else .2
  if k=='soffit':
   nt=mat.node_tree;co=nt.nodes.new('ShaderNodeTexCoord');wave=nt.nodes.new('ShaderNodeTexWave');wave.bands_direction='Y';wave.inputs['Scale'].default_value=35
   nt.links.new(co.outputs['Object'],wave.inputs['Vector']);bump=nt.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.35;bump.inputs['Distance'].default_value=.004
   nt.links.new(wave.outputs['Fac'],bump.inputs['Height']);nt.links.new(bump.outputs['Normal'],b.inputs['Normal'])
def retire(o):
 n=o.name;cs=list(o.users_collection);o.name=n+' [before V22]';o['V22_original_name']=n
 for c in cs:c.objects.unlink(o)
 c=col('Replaced_hidden');c.objects.link(o);c.hide_render=True;c.hide_viewport=True;o.hide_render=True;o.hide_viewport=True
 R['retained'].append({'original':n,'retained':o.name,'collections':[c.name for c in cs]})
def build(mb,n,g,**props):
 if not mb.f:return None
 o=mb.build('V22 '+n,col(g),M);o['V22_kind']=g
 for k,v in props.items():o[k]=v
 return o
def copy_source(o):
 n=o.name;cs=list(o.users_collection);q=o.copy()
 if o.data:q.data=o.data.copy()
 retire(o);q.name=n
 for c in cs:c.objects.link(q)
 q.hide_render=False;q.hide_viewport=False;q['V22_modified_copy']=True
 return q
def box(mb,p,s,k='silver',F=None):L.box(mb,*p,*s,I[k]) if F is None else L.box(mb,0,0,0,*s,I[k],frame=F@Matrix.Translation(p))
def tube(mb,p,r=.02,k='trim',n=8,F=None):L.tube(mb,[Vector(v) if F is None else F@Vector(v) for v in p],r,n,I[k])
def cyl(mb,p,r,h,k='trim',n=16,F=None):
 T=Matrix.Translation(p) if F is None else F@Matrix.Translation(p)
 L.lathe(mb,[(r,-h/2),(r,h/2)],(0,0),n,I[k],cap_top=True,cap_bottom=True,frame=T)
def shell(mb,points,thickness,key):
 n=len(points);q=[(x,y,z-thickness) for x,y,z in points]
 mb.add(points+q,[tuple(range(n)),tuple(range(2*n-1,n-1,-1))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],I[key])
def sweep(mb,pts,width,depth,k='steel'):
 p=[Vector(v) for v in pts];v=[]
 for j,q in enumerate(p):
  t=(p[min(j+1,len(p)-1)]-p[max(0,j-1)]).normalized();a=Vector((1,0,0));b=t.cross(a).normalized()
  v.extend([tuple(q+a*s*width/2+b*h*depth/2) for s,h in [(-1,-1),(1,-1),(1,1),(-1,1)]])
 faces=[(3,2,1,0),tuple(range(len(v)-4,len(v)))]+[(4*j+i,4*j+(i+1)%4,4*(j+1)+(i+1)%4,4*(j+1)+i) for j in range(len(p)-1) for i in range(4)]
 mb.add(v,faces,I[k])
def text(body,p,size=.12,key='black',right=(1,0,0),up=(0,0,1),group='Labels'):
 r=Vector(right);u=Vector(up);n=r.cross(u)
 cu=bpy.data.curves.new('V22 '+body,'FONT');cu.body=body;cu.size=size;cu.align_x='CENTER';cu.align_y='CENTER';cu.resolution_u=2
 f=next((f for f in bpy.data.fonts if 'NotoSansJP' in f.name),None)
 if f:cu.font=f
 cu.materials.append(M[I[key]]);o=bpy.data.objects.new(cu.name,cu);col(group).objects.link(o)
 o.matrix_world=Matrix(((r.x,u.x,n.x,p[0]),(r.y,u.y,n.y,p[1]),(r.z,u.z,n.z,p[2]),(0,0,0,1)));o['V22_kind']=group
 return o
