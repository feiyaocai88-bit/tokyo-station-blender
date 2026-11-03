"""Native plaza geometry, local materials and reversible V18 source retention."""
import bpy, math, random
from mathutils import Vector, Matrix
import v5lib as L
from v16lib import snapshot
M=[]; I={}; ACTIVE=[]; LINKS={}
R={'revision':19,'retained':[],'counts':{},'lawns':[],'trees':[],'lamps':[],'taxi_bays':[],'shelters':[],'moved':[]}
GROUND=.248

def col(name):return L.collection('V19_'+name)
def count(k,n=1):R['counts'][k]=R['counts'].get(k,0)+n
def bounds(o):
 p=[o.matrix_world@Vector(v) for v in o.bound_box]
 return Vector(tuple(min(v[k] for v in p) for k in range(3))),Vector(tuple(max(v[k] for v in p) for k in range(3)))
def setup():
 hidden=set()
 def walk(c,h=False):
  h=h or c.hide_render
  if h:hidden.update(o.name for o in c.objects)
  for cc in c.children:walk(cc,h)
 walk(bpy.context.scene.collection)
 for c in [*bpy.data.collections,*[s.collection for s in bpy.data.scenes]]:
  for o in c.objects:LINKS.setdefault(o.name,[]).append(c)
 ACTIVE.extend(o for o in bpy.context.scene.objects if not o.hide_render and o.name not in hidden)
 specs=[('white',(.70,.70,.66),.74,0),('pale',(.61,.62,.59),.75,0),('mid',(.43,.46,.46),.75,0),('grey',(.30,.34,.35),.74,0),('darkstone',(.20,.24,.25),.73,0),('kerb',(.53,.55,.53),.7,0),('joint',(.19,.21,.21),.85,0),('asphalt',(.055,.065,.071),.92,0),('concrete',(.37,.40,.39),.85,0),('iron',(.035,.045,.047),.43,.55),('steel',(.51,.55,.56),.28,.8),('rope',(.035,.040,.031),.9,0),('soil',(.09,.075,.045),1,0),('grass',(.16,.28,.044),.9,0),('bark',(.26,.23,.16),.88,0),('leaf0',(.12,.25,.043),.8,0),('leaf1',(.20,.34,.065),.8,0),('leaf2',(.30,.42,.11),.8,0),('hedge',(.07,.16,.033),.95,0),('paint',(.89,.90,.86),.6,0),('yellow',(.88,.60,.035),.6,0),('cream',(.74,.73,.59),.5,.12),('green',(.06,.32,.13),.45,.1),('blackcar',(.013,.023,.029),.25,.45),('red',(.65,.024,.014),.32,.1),('rubber',(.009,.012,.014),.8,0),('glass',(.40,.65,.68),.15,.08),('window',(.055,.105,.12),.20,.2),('lamp',(.87,.83,.67),.4,0)]
 for key,c,rough,metal in specs:
  m=L.principled('V19 | '+key,c,rough=rough,metal=metal);I[key]=len(M);M.append(m)
  b=m.node_tree.nodes.get('Principled BSDF')
  if key=='glass':b.inputs['Transmission Weight'].default_value=.82;b.inputs['IOR'].default_value=1.45
  if key=='lamp':b.inputs['Emission Color'].default_value=(*c,1);b.inputs['Emission Strength'].default_value=.8
  if key in ['white','pale','mid','grey','darkstone','kerb','asphalt','concrete','grass','bark','leaf0','leaf1','leaf2']:
   nt=m.node_tree;n=nt.nodes.new('ShaderNodeTexNoise');n.inputs['Scale'].default_value=55 if key!='grass' else 28;n.inputs['Detail'].default_value=2
   co=nt.nodes.new('ShaderNodeTexCoord');nt.links.new(co.outputs['Object'],n.inputs[0])
   ramp=nt.nodes.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(*(v*.84 for v in c),1);ramp.color_ramp.elements[1].color=(*c,1)
   nt.links.new(n.outputs['Fac'],ramp.inputs[0]);nt.links.new(ramp.outputs[0],b.inputs['Base Color'])
   bump=nt.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.15;bump.inputs['Distance'].default_value=.006
   nt.links.new(n.outputs['Fac'],bump.inputs['Height']);nt.links.new(bump.outputs[0],b.inputs['Normal'])

def retire(o):
 name=o.name;cs=LINKS.get(name) or list(o.users_collection);o.name=name+' [before V19]';o['V19_original_name']=name
 for c in cs:c.objects.unlink(o)
 c=col('Replaced_hidden');c.objects.link(o);c.hide_render=True;c.hide_viewport=True;o.hide_render=True;o.hide_viewport=True
 R['retained'].append({'original':name,'retained':o.name,'collections':[c.name for c in cs]});return cs
def copy(o):
 name=o.name;q=o.copy()
 if o.data:q.data=o.data.copy()
 cs=retire(o);q.name=name
 for c in cs:c.objects.link(q)
 q.hide_render=False;q.hide_viewport=False;q['V19_modified_copy']=True;return q
def build(mb,name,group,**props):
 if not mb.f:return None
 o=mb.build('V19 '+name,col(group),M);o['V19_kind']=group
 for k,v in props.items():o[k]=v
 return o
def box(mb,c,size,key='kerb',a=0,F=None):L.box(mb,*c,*size,I[key],rotz=a,frame=F)
def tube(mb,pts,r=.025,key='iron',n=8):L.tube(mb,[Vector(p) for p in pts],r,sides=n,mat=I[key])
def cyl(mb,c,r,h,key='iron',n=16):L.lathe(mb,[(r,c[2]-h/2),(r,c[2]+h/2)],c,n,I[key],cap_top=True,cap_bottom=True)
def lathe(mb,p,c,key='iron',n=16):L.lathe(mb,p,c,n,I[key],cap_top=True,cap_bottom=True)
def ccw(xy):
 if sum(xy[i][0]*xy[(i+1)%len(xy)][1]-xy[(i+1)%len(xy)][0]*xy[i][1] for i in range(len(xy)))<0:return list(reversed(xy))
 return xy
def face(mb,xy,z,key):
 xy=ccw(xy);mb.add([(x,y,z) for x,y in xy],[tuple(range(len(xy)))],I[key])
def prism(mb,xy,z0,z1,key):
 xy=ccw(xy);n=len(xy);mb.add([(x,y,z) for z in (z0,z1) for x,y in xy],[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],I[key])
def rect(x0,x1,y0,y1):return [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]
def inside(x,y,p):
 ok=False;j=len(p)-1
 for i,(xx,yy) in enumerate(p):
  qx,qy=p[j]
  if (yy>y)!=(qy>y) and x<(qx-xx)*(y-yy)/(qy-yy)+xx:ok=not ok
  j=i
 return ok
def round_poly(p,f=.16,n=5):
 out=[]
 for i,b in enumerate(p):
  a=Vector(p[i-1]);b=Vector(b);c=Vector(p[(i+1)%len(p)]);u=b+(a-b)*f;v=b+(c-b)*f
  for j in range(n+1):
   t=j/n;q=(1-t)**2*u+2*t*(1-t)*b+t*t*v;out.append(tuple(q))
 return out
def edge(mb,p,z,w=.22,h=.14,key='kerb',closed=True):
 for a,b in zip(p,p[1:]+p[:1] if closed else p[1:]):
  dx=b[0]-a[0];dy=b[1]-a[1];length=math.hypot(dx,dy)
  box(mb,((a[0]+b[0])/2,(a[1]+b[1])/2,z),(length,w,h),key,math.atan2(dy,dx))
def stripe(mb,a,b,w=.12,z=.145,key='paint'):edge(mb,[a,b],z,w,.007,key,False)
_font=None
def label(s,c,size=.22,key='paint',rotation=(math.pi/2,0,0),group='Signs'):
 global _font
 if _font is None:_font=next((f for f in bpy.data.fonts if 'NotoSansJP' in f.name),bpy.data.fonts.get('Bfont Regular'))
 cu=bpy.data.curves.new('V19 '+s,'FONT');cu.body=s;cu.align_x='CENTER';cu.align_y='CENTER';cu.size=size;cu.resolution_u=2
 if _font:cu.font=_font
 cu.materials.append(M[I[key]]);o=bpy.data.objects.new('V19 '+s,cu);col(group).objects.link(o);o.location=c;o.rotation_euler=rotation;o['V19_kind']=group;return o
