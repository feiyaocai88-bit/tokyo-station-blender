"""Photograph-informed Marunouchi plaza on the complete V17 scene.
-- output.blend build.json baseline_v17.json
"""
import bpy,sys,os,json,math,random
from mathutils import Vector,Matrix
sys.path.insert(0,os.path.dirname(__file__))
import v18lib as H
L=H.L;G=H.GROUND
LAWNS=[(-25.5,-10.5,-109.,-69.),(10.5,25.5,-109.,-69.)]
BASINS=[(-25.5,-10.5,-67.5,-43.5),(10.5,25.5,-67.5,-43.5)]
TREES=[(s*33.5,y) for s in (-1,1) for y in (-42,-54,-66,-78,-90,-102,-114)]
LAMPS=[(s*27.5,y) for s in (-1,1) for y in (-42,-54,-66,-78,-90,-102,-114)]
M8=(-145.8,-129.2,-97.2,-90.8)

def inrect(x,y,r,margin=0):return r[0]-margin<=x<=r[1]+margin and r[2]-margin<=y<=r[3]+margin
def excluded(x,y):return any(inrect(x,y,r) for r in LAWNS) or any(abs(x-a)<2.7 and abs(y-b)<2.7 for a,b in TREES)
def retire_old():
 prefixes=('Zelkova ','Modern three-head','Three-head ','V3 interchange ','V3 plaza granite bench','V3 bench foot','Route bus','Vehicle glazing','Road wheel')
 names={'V4 lawn 1','V4 lawn 2','V4 dry seasonal basin 1','V4 dry seasonal basin 2','V4 lawn stone edging','V4 granite joint grid','V11 Marunouchi granite paving with real joints','V11 tree pit stone benches planting drain channels and covers','V4 fifteen open tree grates','V4 tree-pit soil','V4 lamp mounting plates','V4 lamp base fixings','V4 north vent island','V4 south vent island','V4 north bus island','V4 south interchange island','V4 segmented kerb boundaries','V4 attached road markings','V4 central crossing ramp inner','V4 central crossing ramp outer','V4 recessed linear drainage','V4 drainage cross slots'}
 for o in H.ACTIVE:
  if o.name in names or o.name.startswith(prefixes):H.retire(o)
 # Their source floor remains intact; raise the retained entrance tactile strips
 # to the new finish instead of burying them beneath the new stone faces.
 for name in ['V4 embedded entrance tactile tiles','V4 tactile directional ribs','V4 tactile warning studs']:
  q=H.copy(bpy.data.objects[name]);q.location.z+=.024

def paving():
 rng=random.Random(1818);mb=L.MeshBuilder();axis=L.MeshBuilder();dr=L.MeshBuilder()
 base=L.MeshBuilder();H.prism(base,H.rect(-44.8,44.8,-123.5,-34),.016,.243,'joint');H.build(base,'continuous plaza substrate under replacement finishes','Paving')
 # White ceremonial axis and varied grey/white modular granite on either side.
 for j in range(112):
  y=-123.5+j*.80
  for i in range(112):
   x=-44.8+i*.80
   if x+.8>44.8 or excluded(x+.4,y+.4):continue
   if abs(x+.4)<10.4:continue
   key=rng.choices(['white','pale','mid','grey'],[.34,.36,.23,.07])[0]
   if any(inrect(x+.4,y+.4,r) for r in BASINS):key=rng.choice(['mid','grey','darkstone'])
   H.face(mb,H.rect(x+.006,x+.794,y+.006,min(y+.794,-34)),G,key);H.count('granite_units')
 for j in range(75):
  y=-123.5+j*1.2
  for i in range(18):
   x=-10.5+i*1.2;x1=min(x+1.2,10.5)
   if x>=10.5:continue
   H.face(axis,H.rect(x+.006,x1-.006,y+.006,min(y+1.194,-34)),G+.001,'white');H.count('axis_units')
 # Station-front apron follows the existing polygon. Keep its original tactile
 # routes and the imperial entrance garden clear.
 p=[(-150,-34),(160,-34),(184,-10.3),(-158,-10.3),(-158,-15)]
 for j in range(30):
  y=-34+j*.8
  for i in range(418):
   x=-158+i*.8
   if not all(H.inside(xx,yy,p) for xx,yy in H.rect(x,x+.8,y,y+.8)):continue
   if abs(x+.4)<12.4 and y> -20.7:continue
   if any(abs(x+.4-d)<.9 for d in (-104,107)):continue
   key=rng.choices(['white','pale','mid'],[.45,.35,.2])[0]
   H.face(mb,H.rect(x+.006,x+.794,y+.006,y+.794),G,key);H.count('granite_units')
 H.build(mb,'modular granite apron and side promenades','Paving');H.build(axis,'white granite central axis aligned to imperial entrance','Paving')
 for x in (-26.2,-9.8,9.8,26.2,-43.5,43.5):
  for y in range(-120,-35):
   H.box(dr,(x,y+.48,G+.002),(.14,.96,.012),'iron')
   for dx in (-.048,0,.048):H.box(dr,(x+dx,y+.48,G+.012),(.012,.96,.012),'steel')
 for x in (-41,-8,8,41):
  for y in (-117,-39):
   H.box(dr,(x,y,G+.002),(.8,.65,.015),'mid')
   H.edge(dr,H.rect(x-.4,x+.4,y-.325,y+.325),G+.012,.018,.018,'steel')
 H.build(dr,'flush slot drains and inspection covers','Drainage')

def lawns():
 for i,r in enumerate(LAWNS):
  mb=L.MeshBuilder();posts=L.MeshBuilder();x0,x1,y0,y1=r
  H.prism(mb,H.rect(*r),.24,.267,'grass');H.edge(mb,H.rect(*r),.255,.16,.025,'kerb')
  H.build(mb,f'lawn {i+1} 600 square metres','Lawns',area_m2=600)
  path=[]
  for a,b in zip(H.rect(*r),H.rect(*r)[1:]+H.rect(*r)[:1]):
   n=math.ceil(math.dist(a,b)/2.6)
   for j in range(n):path.append((a[0]+(b[0]-a[0])*j/n,a[1]+(b[1]-a[1])*j/n))
  for a,b in zip(path,path[1:]+path[:1]):
   H.cyl(posts,(a[0],a[1],G+.31),.022,.62,'iron',6)
   H.tube(posts,[(a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,G+.57-.10*4*t*(1-t)) for t in [j/10 for j in range(11)]],.012,'rope',5)
  H.build(posts,f'lawn {i+1} slender hexagonal posts and sagging rope','Lawn_Ropes');H.count('lawn_posts',len(path));H.R['lawns'].append({'bounds':r,'area':600,'posts':len(path)})
 # The cooling surface is dry by default; visible paving and no deep pool walls.
 for i,r in enumerate(BASINS):
  mb=L.MeshBuilder();H.edge(mb,H.rect(*r),G+.005,.07,.012,'steel')
  for x in (r[0]+.15,r[1]-.15):
   for y in [r[2]+k*3 for k in range(9)]:H.cyl(mb,(x,y,G+.015),.035,.015,'steel',10)
  H.build(mb,f'cooling pavement {i+1} flush edge and water outlets','Cooling_Paving',season='dry')

def tree_mesh(seed):
 rng=random.Random(seed);mb=L.MeshBuilder()
 H.lathe(mb,[(.22,0),(.20,1.8),(.16,3.4),(.095,5.1),(.015,7.3)],(0,0),'bark',10)
 tips=[]
 for k in range(12):
  a=k*math.tau/12+rng.uniform(-.18,.18);rad=rng.uniform(2.1,3.7);z=rng.uniform(6.9,8.5)
  start=(0,0,2.5+k*.18);mid=(math.cos(a)*rad*.42,math.sin(a)*rad*.42,5.4)
  end=(math.cos(a)*rad,math.sin(a)*rad,z);H.tube(mb,[start,mid,end],.047,'bark',7)
  for j in range(4):
   aa=a+rng.uniform(-.6,.6);rr=rad+rng.uniform(-.8,1.0);zz=z+rng.uniform(-.8,1.0);tip=(math.cos(aa)*rr,math.sin(aa)*rr,zz)
   H.tube(mb,[mid,tip],.024,'bark',5);tips.append(tip)
 # Dense inner leaf masses support the fine perimeter leaves in distant views.
 # Small irregular lobes overlap at twig tips, avoiding a bare wire-like crown.
 for tip in tips:
  rr=rng.uniform(.56,.78);z=tip[2]
  H.lathe(mb,[(0,z-rr),(.68*rr,z-.7*rr),(rr,z),(rr*.7,z+.68*rr),(0,z+rr)],tip,'leaf'+str(rng.randrange(2)),12)
 for k in range(7500):
  c=Vector(rng.choice(tips))+Vector((rng.gauss(0,.65),rng.gauss(0,.65),rng.gauss(0,.55)))
  a=rng.random()*math.tau;length=rng.uniform(.04,.095);w=length*.48;u=Vector((math.cos(a),math.sin(a),rng.uniform(-.7,.7)))*length;v=Vector((-math.sin(a),math.cos(a),rng.uniform(-.3,.3)))*w
  mb.add([tuple(c-u),tuple(c+v),tuple(c+u),tuple(c-v),tuple(c+Vector((0,0,.018)))],[(0,1,4),(1,2,4),(2,3,4),(3,0,4)],H.I['leaf'+str(rng.randrange(3))])
 return mb

def trees_and_benches():
 bases=[]
 for k in range(4):
  o=H.build(tree_mesh(180+k),f'zelkova branch and leaf canopy variant {k+1}','Trees');bases.append(o)
 for i,(x,y) in enumerate(TREES):
  if i<4:o=bases[i]
  else:o=bases[i%4].copy();o.data=bases[i%4].data;H.col('Trees').objects.link(o)
  o.name=f'V18 central zelkova {i+1:02d}';o.location=(x,y,G+.38);o.rotation_euler.z=i*.71;o['V18_kind']='Trees';H.R['trees'].append({'name':o.name,'xy':[x,y],'central':True})
  mb=L.MeshBuilder();H.box(mb,(x,y,G+.24),(5.0,5.0,.46),'soil')
  H.edge(mb,H.rect(x-2.55,x+2.55,y-2.55,y+2.55),G+.31,.56,.30,'kerb')
  # Broad pale cantilever seat, dark recessed plinth and thin integrated light.
  H.edge(mb,H.rect(x-2.62,x+2.62,y-2.62,y+2.62),G+.43,.78,.22,'white')
  H.edge(mb,H.rect(x-2.56,x+2.56,y-2.56,y+2.56),G+.27,.45,.045,'iron')
  H.edge(mb,H.rect(x-2.59,x+2.59,y-2.59,y+2.59),G+.29,.46,.025,'lamp')
  H.box(mb,(x,y,G+.48),(4.55,4.55,.055),'hedge')
  rng=random.Random(1800+i)
  for j in range(200):
   xx=x+rng.uniform(-2.15,2.15);yy=y+rng.uniform(-2.15,2.15)
   if math.hypot(xx-x,yy-y)<.32:continue
   H.box(mb,(xx,yy,G+.50),(.19,.19,.055),'hedge',rng.random()*3)
  H.build(mb,f'zelkova {i+1:02d} planted stone seat with recessed base','Tree_Seats')
 # Retain the sparse outer planting positions with the same improved tree mesh.
 for i,(x,y) in enumerate([(-137,-99),(-87,-99),(67,-97),(146,-55),(105,-94)]):
  o=bases[i%4].copy();o.data=bases[i%4].data;H.col('Trees').objects.link(o);o.name=f'V18 perimeter tree {i+1}';o.location=(x,y,.31);o.scale=(.68,.68,.72);o['V18_kind']='Trees'
  # These positions are reconciled with transport geometry below.
  H.R['trees'].append({'name':o.name,'xy':[x,y],'central':False})

def lighting():
 for i,(x,y) in enumerate(LAMPS+[(-129,-28),(-82,-28),(96,-28),(155,-28)]):
  mb=L.MeshBuilder();H.lathe(mb,[(.26,G),(.24,G+.18),(.15,1.3),(.105,6.4),(.055,8.1)],(x,y),'iron',16)
  for k in range(3):
   a=k*math.tau/3;xx=x+.49*math.cos(a);yy=y+.49*math.sin(a);z=6.8+(.15 if k==0 else 0)
   H.tube(mb,[(x,y,z),(xx,yy,z)],.055,'iron')
   H.lathe(mb,[(.02,z-1.0),(.13,z-.82),(.155,z-.62),(.155,z+.62),(.12,z+.82),(.015,z+1.06)],(xx,yy),'iron',12)
   for zz in (-.33,.33):H.cyl(mb,(xx,yy,z+zz),.16,.55,'lamp',12)
  H.build(mb,f'three vertical lantern pole {i+1:02d}','Lighting');H.R['lamps'].append({'xy':[x,y],'lanterns':3})

def cameras():
 specs=[('01 Plaza overview',(-185,-275,185),(0,-52,4),330),('02 Central axis',(0,-181,85),(0,-52,6),130),('03 Lawn ropes and tree seats',(50,-128,13),(13,-76,4),None),('04 North transport square',(-171,-145,86),(-91,-78,2),136),('05 South transport square',(176,-154,88),(102,-78,2),132),('06 Plaza plan',(0,-63,310),(0,-63,0),350)]
 for name,pos,target,scale in specs:
  d=bpy.data.cameras.new('V18 '+name);d.clip_start=.05;d.clip_end=2500
  if scale:d.type='ORTHO';d.ortho_scale=scale
  else:d.lens=40
  o=bpy.data.objects.new(d.name,d);H.col('Review_Cameras').objects.link(o);o.location=pos;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();o['V18_review']=True
 sc=bpy.context.scene;sc.camera=bpy.data.objects['V18 01 Plaza overview'];sc.render.resolution_x=1800;sc.render.resolution_y=1200;sc.render.resolution_percentage=100

def main():
 args=sys.argv[sys.argv.index('--')+1:];sc=bpy.data.scenes['Tokyo Station'];bpy.context.window.scene=sc
 if sc.get('V18_plaza'):raise RuntimeError('Start from V17')
 with open(args[2],'w') as f:json.dump(H.snapshot(),f,separators=(',',':'))
 H.setup();retire_old();paving();lawns();trees_and_benches();lighting()
 from mod18_transport import transport,people
 transport();people();cameras()
 H.R['basis']=['JR East 2017 plaza opening plan: white granite, two lawns around 1200 m2, paired zelkova rows, three-lamp poles.','JSCE 2020 design-award as-built aerial and street photographs: traffic-square pools, slim glass shelters, granite seats.','Katabami planting photographs and Teikin installed lawn ropes and furniture.']
 H.R['limits']=['Photo-informed proportions fitted to inherited station coordinates; not a georeferenced survey.','The central white axis is centred on X=0; two lawns are each 15 x 40 m.','Transport bay counts, furniture dimensions and landscape species outside the central rows are approximations.','Existing M7/M8 positions and below-ground passages remain model approximations; their real openings are kept clear.','Cooling paving is shown dry. No contemporary temporary event furniture is asserted.']
 sc['V18_plaza']=json.dumps(H.R,ensure_ascii=False);sc['last_stage']='V18 Marunouchi plaza photographic comparison'
 p=os.path.join(os.path.dirname(__file__),'..','README_V18.txt')
 if os.path.isfile(p):tx=bpy.data.texts.new('README_V18_中文');tx.write(open(p,encoding='utf8').read())
 bpy.context.view_layer.update();bpy.ops.file.pack_all();bpy.context.preferences.filepaths.save_version=0
 os.makedirs(os.path.dirname(os.path.abspath(args[0])),exist_ok=True);bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args[0]),compress=True)
 with open(args[1],'w',encoding='utf8') as f:json.dump(H.R,f,ensure_ascii=False,indent=2)
 print('V18_BUILD_OK',H.R['counts'],flush=True)
if __name__=='__main__':main()
