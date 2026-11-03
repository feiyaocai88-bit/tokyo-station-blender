"""Native architectural detail and reversible source retention for V16."""
import bpy,math,numpy as np
from mathutils import Vector,Matrix
import v5lib as L
from v14lib import world,component_labels
M=[];I={};LINKS={};ACTIVE=[]
R={'revision':16,'retained':[],'counts':{},'changes':[]}

def snapshot():
 """Source geometry plus curves, text, visibility and collection membership."""
 import json,hashlib
 from mod12_surface_trains import fingerprint
 result=fingerprint();links={};cache={}
 for c in bpy.data.collections:
  for o in c.objects:links.setdefault(o.name,[]).append(c.name)
 for sc in bpy.data.scenes:
  for o in sc.collection.objects:links.setdefault(o.name,[]).append('SCENE:'+sc.name)
 for o in bpy.data.objects:
  r=result[o.name];r['visibility']=[o.hide_render,o.hide_viewport];r['collections']=sorted(links.get(o.name,[]))
  if o.type in ['CURVE','FONT']:
   key=o.data.as_pointer()
   if key not in cache:
    d=o.data;payload={'materials':[m.name if m else None for m in d.materials]}
    if o.type=='FONT':payload.update(body=d.body,size=d.size,extrude=d.extrude,align_x=d.align_x)
    else:
     payload.update(bevel_depth=d.bevel_depth,bevel_resolution=d.bevel_resolution,resolution=d.resolution_u,splines=[])
     for s in d.splines:
      payload['splines'].append({'type':s.type,'cyclic':s.use_cyclic_u,'order':s.order_u,'points':[(list(p.co),p.radius,p.tilt) for p in s.points],'bezier':[(list(p.co),list(p.handle_left),list(p.handle_right),p.radius,p.tilt) for p in s.bezier_points]})
    cache[key]=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
   r['curve_or_text']=cache[key]
 return result

def count(key,n=1):R['counts'][key]=R['counts'].get(key,0)+n
def col(name):return L.collection('V16_'+name)
def bounds(o):
 p=np.array([o.matrix_world@Vector(v) for v in o.bound_box]);return p.min(0),p.max(0)
def setup():
 hidden=set()
 def walk(c,h=False):
  h=h or c.hide_render
  if h:hidden.update(o.name for o in c.objects)
  for q in c.children:walk(q,h)
 walk(bpy.data.scenes['Tokyo Station'].collection)
 for c in [*bpy.data.collections,*[s.collection for s in bpy.data.scenes]]:
  for o in c.objects:LINKS.setdefault(o.name,[]).append(c)
 ACTIVE.extend(o for o in bpy.data.scenes['Tokyo Station'].objects if not o.hide_render and o.name not in hidden)
 for key,existing in [('brick','V2 | 109 x 60.5 mm header brick'),('slate','V5 | Ogatsu-type natural slate fish-scale (gyorin-buki)'),('shadow','V2 | recessed room shadow')]:I[key]=len(M);M.append(bpy.data.materials[existing])
 for key,color,metal,rough in [('stone',(.59,.565,.50),0,.72),('stone_light',(.72,.695,.62),0,.63),('copper',(.28,.115,.057),.40,.48),('copper_dark',(.14,.070,.040),.42,.53),('patina',(.16,.22,.15),.35,.59),('sash',(.73,.72,.65),.12,.38),('glass',(.13,.19,.22),.22,.20),('iron',(.15,.12,.072),.6,.42),('joint',(.16,.125,.09),0,.8)]:
  m=L.principled('V16 | '+key,color,rough=rough,metal=metal);I[key]=len(M);M.append(m)
  if key in ['stone','stone_light','copper','copper_dark']:
   nt=m.node_tree;b=nt.nodes.get('Principled BSDF');tex=nt.nodes.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=44 if key.startswith('stone') else 6
   coord=nt.nodes.new('ShaderNodeTexCoord');nt.links.new(coord.outputs['Object'],tex.inputs['Vector'])
   ramp=nt.nodes.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(*(c*.84 for c in color),1);ramp.color_ramp.elements[1].color=(*color,1)
   nt.links.new(tex.outputs['Fac'],ramp.inputs[0]);nt.links.new(ramp.outputs['Color'],b.inputs['Base Color'])

def retire(o):
 if o.get('V16_original_name'):raise RuntimeError('Already retired '+o.name)
 name=o.name;cs=LINKS.get(name) or list(o.users_collection)
 o.name=name+' [before V16]';o['V16_original_name']=name
 for c in cs:c.objects.unlink(o)
 c=col('Replaced_hidden');c.objects.link(o);c.hide_viewport=True;c.hide_render=True;o.hide_viewport=True;o.hide_render=True
 R['retained'].append({'original':name,'retained':o.name,'collections':[c.name for c in cs]})
 return cs
def copy(o):
 name=o.name;q=o.copy();q.data=o.data.copy();cs=retire(o);q.name=name
 for c in cs:c.objects.link(q)
 q.hide_viewport=False;q.hide_render=False;q['V16_modified_copy']=True
 return q
def recolor(o,keys):
 q=copy(o)
 for i,m in enumerate(q.data.materials):
  if m and m.name in keys:q.data.materials[i]=M[I[keys[m.name]]]
 return q
def build(mb,name,group,**props):
 if not mb.f:return None
 o=mb.build('V16 '+name,col(group),M);o['V16_kind']=group
 for k,v in props.items():o[k]=v
 return o
def box(mb,c,size,key='stone',F=None):L.box(mb,*c,*size,I[key]) if F is None else L.box(mb,0,0,0,*size,I[key],frame=F@Matrix.Translation(c))
def tube(mb,pts,r=.025,key='stone',n=8):L.tube(mb,[Vector(p) for p in pts],r,sides=n,mat=I[key])
def ring(mb,c,r,t,key='stone',n=48):tube(mb,[(c[0]+r*math.cos(a),c[1],c[2]+r*math.sin(a)) for a in np.linspace(0,math.tau,n+1)],t,key)
def lathe(mb,profile,c,key='stone',n=24,F=None):L.lathe(mb,profile,c,n,I[key],cap_top=True,cap_bottom=True,frame=F)
def extrude(mb,poly,y0,y1,key='brick'):
 n=len(poly);v=[(x,y,z) for y in (y0,y1) for x,z in poly]
 mb.add(v,[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],I[key])
def arc(mb,c,r0,r1,y0,y1,key='copper',a0=0,a1=math.pi,n=64):
 for a,b in zip(np.linspace(a0,a1,n+1)[:-1],np.linspace(a0,a1,n+1)[1:]):
  extrude(mb,[(c[0]+r*math.cos(t),c[1]+r*math.sin(t)) for r,t in [(r0,a),(r1,a),(r1,b),(r0,b)]],y0,y1,key)
def scroll(mb,x,y,z,r,key='stone_light',flip=1):
 pts=[]
 for a in np.linspace(0,math.tau*1.5,45):
  rr=r*(1-a/(math.tau*1.65));pts.append((x+flip*rr*math.cos(a),y,z+rr*math.sin(a)))
 tube(mb,pts,r*.12,key)
def rosette(mb,x,y,z,r,key='copper'):
 ring(mb,(x,y,z),r,.035,key)
 for a in np.linspace(0,math.tau,9)[:-1]:
  pts=[]
  for t in np.linspace(0,math.tau,17):
   u=r*.53+r*.37*math.cos(t);v=r*.17*math.sin(t)
   pts.append((x+u*math.cos(a)-v*math.sin(a),y-.035*math.sin(t)**2,z+u*math.sin(a)+v*math.cos(a)))
  tube(mb,pts,r*.065,key,6)
 ring(mb,(x,y-.035,z),r*.19,r*.11,key)
def capital(mb,x,y,z,w=.65):
 box(mb,(x,y+.06,z-.24),(w*.50,.34,.38),'stone')
 box(mb,(x,y,z+.12),(w*1.22,.46,.10),'stone_light')
 box(mb,(x,y,z+.02),(w,.40,.10),'stone')
 for s in (-1,1):scroll(mb,x+s*w*.32,y-.23,z-.08,w*.22,flip=s)
 for s in (-1,0,1):
  pts=[(x+s*w*.12,y-.18,z-.38),(x+s*w*.21,y-.26,z-.22),(x+s*w*.13,y-.25,z-.10)]
  tube(mb,pts,w*.045,'stone_light',6)
def frame(x,y,z):return Matrix.Translation((x,y,z))@Matrix.Rotation(math.pi/2,4,'X')
