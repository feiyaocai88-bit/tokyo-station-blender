"""Connect Marunouchi building shells and roof runs on the complete V16 scene.
-- output.blend report.json baseline.json
"""
import bpy,bmesh,sys,os,json,math,numpy as np
from mathutils import Vector,Matrix
sys.path.insert(0,os.path.dirname(__file__))
import v5lib as L
from v16lib import snapshot
R={'revision':17,'retained':[],'roof_links':[],'dome_links':[],'counts':{}}
M=[];I={};LINKS={};ACTIVE=[]

def col(name):return L.collection('V17_'+name)
def setup():
 hidden=set()
 def walk(c,h=False):
  h=h or c.hide_render
  if h:hidden.update(o.name for o in c.objects)
  for cc in c.children:walk(cc,h)
 walk(bpy.context.scene.collection)
 for c in bpy.data.collections:
  for o in c.objects:LINKS.setdefault(o.name,[]).append(c)
 ACTIVE.extend(o for o in bpy.context.scene.objects if not o.hide_render and o.name not in hidden)
 for key,name in [('brick','V2 | 109 x 60.5 mm header brick'),('slate','V2 | natural slate with fine overlapping courses'),('stone','V2 | pale granite and stone dressings'),('copper','V16 | copper'),('floor','V11 | floor'),('glass','V16 | glass'),('sash','V16 | sash')]:
  I[key]=len(M);M.append(bpy.data.materials[name])
def build(mb,name,kind):
 o=mb.build('V17 '+name,col(kind),M);o['V17_kind']=kind;return o
def box(mb,c,size,key='brick'):L.box(mb,*c,*size,I[key])
def tube(mb,pts,r=.045):L.tube(mb,[Vector(p) for p in pts],r,sides=8,mat=I['copper'])
def retire(o):
 name=o.name;cs=LINKS.get(name) or list(o.users_collection);o.name=name+' [before V17]';o['V17_original_name']=name
 for c in cs:c.objects.unlink(o)
 c=col('Replaced_hidden');c.objects.link(o);c.hide_render=True;c.hide_viewport=True;o.hide_render=True;o.hide_viewport=True
 R['retained'].append({'original':name,'retained':o.name,'collections':[c.name for c in cs]})
 return cs
def replace_copy(o):
 name=o.name;q=o.copy();q.data=o.data.copy();cs=retire(o);q.name=name
 for c in cs:c.objects.link(q)
 q.hide_render=False;q.hide_viewport=False;q['V17_modified_copy']=True;return q
def vertices(o):return [o.matrix_world@v.co for v in o.data.vertices]

def profile(o,end,offset=0):
 """Roof cross-section at a plateau end, including exact slope/eave contacts."""
 v=vertices(o);u=((v[5]+v[6])-(v[4]+v[7])).normalized();u.z=0;u.normalize()
 a,b=(v[4],v[7]) if end==0 else (v[5],v[6]);cen=(a+b)/2
 def at(p,q):return p+(q-p)*((cen-p).dot(u)/(q-p).dot(u))
 p=[at(v[0],v[1]),a.copy(),b.copy(),at(v[3],v[2])]
 return [q+u*offset for q in p],u
def loft(p,q,label):
 # Keep the underside slightly below the old coplanar roof bottoms. This avoids
 # duplicate coplanar bottom faces when several solid unions meet at a joint.
 p=[v.copy() for v in p];q=[v.copy() for v in q]
 for profile_ in (p,q):
  for k in (0,3):profile_[k].z-=.035
 mb=L.MeshBuilder();vs=[tuple(v) for v in p+q]
 faces=[(0,3,2,1),(4,5,6,7)]
 for i in range(4):j=(i+1)%4;faces.extend([(i,j,4+j),(i,4+j,4+i)])
 mb.add(vs,faces,I['slate']);o=build(mb,label,'Roofs')
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
 R['roof_links'].append({'name':o.name,'from':[list(v) for v in p],'to':[list(v) for v in q]})
 return o
def union(base,operand):
 # The south bend contains slightly non-planar quads. Triangulate independent
 # copies and use Blender's manifold solver so coplanar intersections cannot
 # leave duplicate internal bottom sheets in the result.
 temp=operand.copy();temp.data=operand.data.copy();col('Temporary').objects.link(temp)
 for obj in (base,temp):
  bm=bmesh.new();bm.from_mesh(obj.data)
  bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
  if bm.calc_volume(signed=True)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
  bm.to_mesh(obj.data);bm.free()
 bpy.context.view_layer.objects.active=base;base.select_set(True)
 mod=base.modifiers.new('Connected roof union','BOOLEAN');mod.operation='UNION';mod.solver='MANIFOLD';mod.object=temp
 bpy.ops.object.modifier_apply(modifier=mod.name);base.select_set(False)
 bpy.data.objects.remove(temp,do_unlink=True)
 if len(base.data.polygons)<4:raise RuntimeError('Empty roof union: '+base.name)
def roof_run(label,names,extension_start=None,extension_end=None):
 source=[bpy.data.objects[n] for n in names];bridges=[]
 for a,b in zip(source[:-1],source[1:]):
  p,_=profile(a,1,-.12);q,_=profile(b,0,.12);bridges.append(loft(p,q,label+' joint '+str(len(bridges)+1)))
 for end,target in [(0,extension_start),(1,extension_end)]:
  if target is None:continue
  p,u=profile(source[0] if end==0 else source[-1],end,.12 if end==0 else -.12)
  cen=(p[1]+p[2])/2;shift=Vector(target)-Vector((cen.x,cen.y,0));shift.z=0
  q=[v+shift for v in p]
  bridges.append(loft(q,p,label+' start connection') if end==0 else loft(p,q,label+' end connection'))
 # Actual boolean union gives a connected native roof mesh, rather than leaving
 # the old independent hip ends under a decorative strip.
 first=source[0];me=first.data.copy();o=bpy.data.objects.new('V17 '+label+' continuous roof',me);col('Roofs').objects.link(o);o.matrix_world=first.matrix_world.copy();o['V17_kind']='Roofs'
 # Alternate bridges and old solids so each boolean has a volume overlap.
 for i,s in enumerate(source[1:]):
  union(o,bridges[i]);union(o,s)
 for q in bridges[len(source)-1:]:union(o,q)
 bpy.context.view_layer.update();L.set_face_slope_uvs(o.data,'V17 continuous slate UV')
 for s in source:retire(s)
 for b in bridges:bpy.data.objects.remove(b,do_unlink=True)
 R['counts']['connected_roof_runs']=R['counts'].get('connected_roof_runs',0)+1
 # Continue metal ridge caps over the new roof links.
 mb=L.MeshBuilder()
 for link in R['roof_links']:
  if not link['name'].startswith('V17 '+label):continue
  for k in (1,2):tube(mb,[np.array(link['from'][k])+[0,0,.035],np.array(link['to'][k])+[0,0,.035]])
 build(mb,label+' connecting ridge flashings','Flashings')
 return o

def dome_necks():
 for tag,cx in [('NORTH',-104.),('SOUTH',107.)]:
  for s in (-1,1):
   mb=L.MeshBuilder();stone=L.MeshBuilder();floor=L.MeshBuilder()
   # The dome side is octagonal: front/back returns start inside the diagonal
   # facets, rather than stopping at the side-face bounding box.
   for y,inner in [(-6.8,10.25),(8.4,8.85)]:
    a,b=sorted((cx+s*inner,cx+s*14.30));box(mb,((a+b)/2,y,8.5),(b-a,.74,17))
    for z,h,projection in [(.32,.38,.10),(5.65,.22,.14),(11.15,.22,.14),(16.45,.20,.23),(16.88,.28,.42),(17.12,.12,.52)]:
     yy=y+(-1 if y<0 else 1)*projection/2
     box(stone,((a+b)/2,yy,z),(b-a,.74+projection,h),'stone')
   # Enclosed floor/roof plates bridge all occupied storeys of the neck.
   plan=[(cx+s*x,y) for x,y in [(10.25,-6.8),(14.30,-6.8),(14.30,8.4),(8.85,8.4),(12.15,5.2),(12.15,-5.0)]]
   if s<0:plan.reverse()
   for z in [.15,5.95,11.35,16.95]:
    vs=[(x,y,zz) for zz in (z-.07,z+.07) for x,y in plan];n=len(plan)
    floor.add(vs,[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],I['floor'])
   build(mb,tag+f' {s:+d} connecting brick walls','Dome_Necks');build(stone,tag+f' {s:+d} continuous stone courses','Dome_Necks');build(floor,tag+f' {s:+d} connecting storey slabs','Dome_Necks')
   R['dome_links'].append({'dome':tag,'cx':cx,'side':s,'front':[-6.8,10.25,14.3],'rear':[8.4,8.85,14.3],'floor_z':[.15,5.95,11.35,16.95],'floor_plan':plan})
  # Engage the V16 round corner stone ornaments in the connected front wall.
  o=bpy.data.objects['V16 '+tag+' front corner round stone ornaments with copper caps'];q=replace_copy(o)
  q.location.y-=1.80
 R['counts']['dome_wing_necks']=4

def attic_returns():
 # V16 removed the old hip roofs from these turrets. Their original attic was
 # only a front panel; side/back returns now support the complete flat cap.
 for s in (-1,1):
  mb=L.MeshBuilder();x=s*18
  box(mb,(x,6.0,18.85),(5.9,.30,3.70),'stone')
  for dx in (-2.8,2.8):box(mb,(x+dx,-.9,18.85),(.30,14.1,3.70),'stone')
  build(mb,('North' if s<0 else 'South')+' attic side and back returns','Central_Returns')
 R['counts']['closed_attic_returns']=2

def roofs():
 roof_run('North outer wing',['North outer wing slate roof'],extension_end=(-113.1,.8,0))
 roof_run('North inner wing',['North inner outer bay slate roof','V3 North projecting gable slate roof','North inner central bay slate roof'],extension_start=(-94.9,.8,0),extension_end=(-20.6,.8,0))
 roof_run('South inner wing',['South inner central bay slate roof','V3 South projecting gable slate roof','South inner outer bay slate roof'],extension_start=(20.6,.8,0),extension_end=(97.9,.8,0))
 roof_run('South outer wing',['V3 South short straight link slate roof','V3 South angled wing start slate roof','V3 South outer projecting gable slate roof','South long wing last slate roof'],extension_start=(116.1,.8,0))

def cameras():
 sc=bpy.data.scenes['Tokyo Station'];bpy.context.window.scene=sc
 specs=[('01 Full connected station',(5,-180,105),(6,4,13),350),('02 North wing roof connections',(-59,-50,44),(-59,0,17),86),('03 Central roof connections',(34,-55,43),(0,0,17),78),('04 South dome necks',(84,-53,36),(102,-1,14),65),('05 South angled wing',(166,-36,51),(150,12,17),70)]
 for name,pos,target,scale in specs:
  d=bpy.data.cameras.new('V17 '+name);d.type='ORTHO';d.ortho_scale=scale;d.clip_start=.05;d.clip_end=2500
  o=bpy.data.objects.new(d.name,d);col('Review_Cameras').objects.link(o);o.location=pos;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();o['V17_review']=True
 sc.camera=bpy.data.objects['V17 01 Full connected station'];sc.render.resolution_x=2000;sc.render.resolution_y=650;sc.render.resolution_percentage=100

def main():
 args=sys.argv[sys.argv.index('--')+1:];sc=bpy.data.scenes['Tokyo Station'];bpy.context.window.scene=sc
 if sc.get('V17_connections'):raise RuntimeError('Start from V16')
 json.dump(snapshot(),open(args[2],'w'),separators=(',',':'))
 setup();dome_necks();attic_returns();roofs();cameras()
 R['reference']='Official Tokyo Station City station-building elevation and Kajima restoration completion aerial image 13: the Marunouchi building is continuous, with articulated roof heights.'
 R['limitations']=['Connection widths follow the inherited model, not surveyed junction dimensions.','Different roof heights, projecting gables and the south bend are retained.','All V16 trains, platforms, tracks, ground and underground cutaways are preserved.']
 sc['V17_connections']=json.dumps(R,ensure_ascii=False);sc['last_stage']='V17 continuous Marunouchi building shells and roof connections'
 p=os.path.join(os.path.dirname(__file__),'..','README_V17.txt')
 if os.path.isfile(p):tx=bpy.data.texts.new('README_V17_中文');tx.write(open(p,encoding='utf8').read())
 bpy.context.view_layer.update();bpy.ops.file.pack_all();bpy.context.preferences.filepaths.save_version=0
 os.makedirs(os.path.dirname(os.path.abspath(args[0])),exist_ok=True);bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args[0]),compress=True)
 json.dump(R,open(args[1],'w',encoding='utf8'),ensure_ascii=False,indent=2);print('V17_BUILD_OK',R['counts'],flush=True)
if __name__=='__main__':main()
