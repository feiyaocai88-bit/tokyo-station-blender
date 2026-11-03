"""V19 rear concourse and continuous streets, starting from the complete V18.
Blender --background V18.blend -P this.py -- output.blend build.json baseline.json
"""
import bpy,sys,os,json,math,random
from pathlib import Path
from mathutils import Vector,Matrix
sys.path.insert(0,os.path.dirname(__file__))
import v19lib as H
L=H.L
PLAN=json.loads(Path(__file__).with_name('streets_v19.json').read_text(encoding='utf8'))
def mesh_surface(rec,name,group,z,key):
 mb=L.MeshBuilder();mb.add([(x,y,z) for x,y in rec['v']],rec['f'],H.I[key]);o=H.build(mb,name,group)
 import bmesh
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0002)
 bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(o.data);bm.free();return o
def line(mb,a,b,width=.12,z=.15,key='paint'):H.stripe(mb,a,b,width,z,key)
def at_path(points,dist,off=0):
 for a,b in zip(points[:-1],points[1:]):
  ln=math.dist(a,b)
  if dist<=ln:
   ux=(b[0]-a[0])/ln;uy=(b[1]-a[1])/ln
   return (a[0]+ux*dist-uy*off,a[1]+uy*dist+ux*off),math.atan2(uy,ux)
  dist-=ln
 return points[-1],0
def dashed(mb,points,off=0,start=0,end=None,skip=()):
 length=sum(math.dist(a,b) for a,b in zip(points[:-1],points[1:]));end=length if end is None else min(end,length);t=start
 while t<end-1:
  a,_=at_path(points,t,off);b,_=at_path(points,min(t+3,end),off)
  if not any(math.dist(a,q)<r or math.dist(b,q)<r for q,r in skip):line(mb,a,b)
  t+=6
def arrow(mb,p,a,z=.151):
 F=Matrix.Translation((*p,z))@Matrix.Rotation(a,4,'Z');vs=[(-1.8,-.13),(.25,-.13),(.25,-.65),(1.5,0),(.25,.65),(.25,.13),(-1.8,.13)]
 mb.add([tuple(F@Vector((x,y,0))) for x,y in vs],[tuple(range(len(vs)))],H.I['paint'])
def streets():
 # Remove only superseded layers; keep their complete source objects hidden.
 for name in ['V4 unified perimeter and transport road','V18 north road connection to perimeter street','V18 south road connection to perimeter street']:
  H.retire(bpy.data.objects[name])
 mesh_surface(PLAN['asphalt'],'continuous perimeter and underbridge carriageway','Road_Surface',.142,'asphalt')
 mesh_surface(PLAN['concrete'],'flush concrete transport-square approaches','Road_Surface',.142,'concrete')
 mesh_surface(PLAN['infill'],'connected footway infill substrate','Footways',.238,'joint')
 mb=L.MeshBuilder()
 for t in PLAN['tiles']:H.face(mb,t['p'],.244,t['shade'])
 H.build(mb,'granite footways filling obsolete asphalt aprons','Footways')
 mb=L.MeshBuilder()
 for path in PLAN['kerbs']:
  for a,b in zip(path[:-1],path[1:]):
   # Low roll-over kerbs at crossing approaches; uninterrupted edge elsewhere.
   mid=((a[0]+b[0])/2,(a[1]+b[1])/2);h=.01 if any(abs(mid[0]-x)<3.4 and mid[1]<-121 for x in (-38,38)) else .13
   H.edge(mb,[a,b],.142+h/2,.21,h,'kerb',False)
 H.build(mb,'continuous kerb alignment with driveway openings','Road_Kerbs')
 # V14 road and new network share asphalt and grade, without recolouring its pavement.
 old=bpy.data.objects['V14 south curved road sidewalk and raised curbs'];q=H.copy(old)
 for i,m in enumerate(q.data.materials):
  if m and m.name=='V14 | asphalt':q.data.materials[i]=H.M[H.I['asphalt']]
 # Trim inherited raised kerbs/pavement where the new southern road crosses
 # their end, preventing a hidden curb from remaining across the carriageway.
 cutmb=L.MeshBuilder();rec=PLAN['primary'];n=len(rec['v'])
 cutmb.add([(x,y,z) for z in (-1,1) for x,y in rec['v']],[tuple(reversed(f)) for f in rec['f']]+[tuple(i+n for i in f) for f in rec['f']],H.I['iron'])
 for p in PLAN['primary_outline']:
  for ring in [p['outer'],*p['holes']]:
   for a,b in zip(ring[:-1],ring[1:]):cutmb.add([(*a,-1),(*b,-1),(*b,1),(*a,1)],[(0,1,2,3)],H.I['iron'])
 cutter=H.build(cutmb,'temporary street kerb trimmer','Temporary')
 # Weld the triangulated caps and boundary walls into a closed cutter.
 import bmesh
 bm=bmesh.new();bm.from_mesh(cutter.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0001);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(cutter.data);bm.free()
 for obj in [q,H.copy(bpy.data.objects['V14 south paving joints and bus stop road markings'])]:
  bpy.context.view_layer.objects.active=obj;mod=obj.modifiers.new('Continuous street opening','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter;bpy.ops.object.modifier_apply(modifier=mod.name)
 bpy.data.objects.remove(cutter,do_unlink=True)
 # Preserve loop arrows and tactile studs; replace only the buried front-road paint.
 o=H.copy(bpy.data.objects['V18 traffic direction arrows and offset pedestrian crossings'])
 bm=bmesh.new();bm.from_mesh(o.data)
 kill=[f for f in bm.faces if max(v.co.z for v in f.verts)<.14]
 bmesh.ops.delete(bm,geom=kill,context='FACES');bm.to_mesh(o.data);bm.free()
 markings=L.MeshBuilder();front=PLAN['paths']['front']['points']
 skip=[((-166,-129),14),((167,-129),14),((-38,-129),5),((38,-129),5)]
 for off in (-2,2):dashed(markings,front,off,skip=skip)
 for x in (-38,38):
  for k in range(12):H.box(markings,(x,-134.5+k,.151),(5.8,.46,.012),'paint')
  for xx in (x-4.6,x+4.6):H.box(markings,(xx,-129,.151),(.35,5.5,.012),'paint')
  # Gentle 0.10 m kerb transitions preserve wheelchair access.
  ramps=L.MeshBuilder()
  for ya,yb,za,zb in [(-135.8,-134.8,.244,.142),(-123.2,-122.3,.142,.244)]:
   ramps.add([(x-3,ya,za),(x+3,ya,za),(x+3,yb,zb),(x-3,yb,zb)],[(0,1,2,3)],H.I['pale'])
  H.build(ramps,f'pedestrian crossing {x} flush dropped approaches','Crossing_Ramps')
 for side in ('north','south'):
  pts=PLAN['paths'][side]['points'];junctions=[(((-166 if side=='north' else 167),-129),14),(((-162 if side=='north' else 166),(-52 if side=='north' else -80)),10)]
  dashed(markings,pts,skip=junctions)
  for dist in (42,78,135,190,245,300):
   for off,a in [(-2.8,0),(2.8,math.pi)]:
    p,ang=at_path(pts,dist,off)
    if p[1]<216 and not any(math.dist(p,c)<r for c,r in junctions):arrow(markings,p,ang+a)
 # Perimeter intersections: crossings, stop bars, lane guidance and short hatching.
 for x,y in [(-164,-117),(-162,-40),(164,-116),(172,-27)]:
  for dx in [ -5.3+i*.9 for i in range(13)]:H.box(markings,(x+dx,y,.151),(.44,4.5,.012),'paint')
  H.box(markings,(x,y+3.7,.151),(5.1,.35,.012),'paint')
 for x in (-139,-91,91,139):
  arrow(markings,(x,-125.5),0);arrow(markings,(x,-132.5),math.pi)
 for x in (-159,156):
  for k in range(8):line(markings,(x+k*.7,-129.9),(x+k*.7+1.6,-128.1),.16)
 H.build(markings,'continuous lane lines arrows stop bars and crossings','Road_Markings')
 # Detailed gullies and cast iron access covers are deliberately kept out of lane centres.
 drains=L.MeshBuilder()
 for side in ('front','north','south'):
  pts=PLAN['paths'][side]['points'];width=PLAN['paths'][side]['width'];length=sum(math.dist(a,b) for a,b in zip(pts[:-1],pts[1:]))
  for d in range(15,int(length)-10,18):
   for off in (-width/2+.32,width/2-.32):
    p,a=at_path(pts,d,off);H.box(drains,(*p,.149),(.65,.34,.025),'iron',a)
    for j in range(7):
     dx=(j-3)*.085;pp=(p[0]+math.cos(a)*dx,p[1]+math.sin(a)*dx)
     H.box(drains,(*pp,.166),(.035,.28,.018),'steel',a)
  for d in range(33,int(length)-12,53):
   p,a=at_path(pts,d,-width*.24);H.cyl(drains,(*p,.147),.36,.012,'iron',24)
   for t in range(-3,4):H.box(drains,(p[0]+t*.08,p[1],.155),(.016,.54,.008),'steel',a)
 H.build(drains,'roadside gullies and recessed utility covers','Road_Detail')
 street_furniture()
 H.R['road_plan']={'areas':PLAN['areas'],'connected_asphalt_components':PLAN['components'],'reference':'scripts/streets_v19.json','road_z':.142,'tile_count':len(PLAN['tiles'])}
def street_furniture():
 mb=L.MeshBuilder()
 for x,y,a in [(-154,-121,0),(-175,-116,math.pi),(154,-120,math.pi),(177,-115,0),(-154,-38,0),(184,-26,math.pi),(-42,-121,0),(42,-136,math.pi)]:
  H.cyl(mb,(x,y,2.65),.095,5.1,'iron',16);H.cyl(mb,(x,y,.33),.17,.35,'iron',16)
  dx,dy=math.cos(a),math.sin(a);H.tube(mb,[(x,y,5.18),(x+dx*2.8,y+dy*2.8,5.18)],.065,'iron')
  H.box(mb,(x+dx*2.55,y+dy*2.55,5.03),(1.12,.28,.34),'iron',a)
  for i,key in enumerate(['green','yellow','red']):
   xx=x+dx*(2.18+i*.36);yy=y+dy*(2.18+i*.36)
   H.tube(mb,[(xx+dy*.14,yy-dx*.14,5.03),(xx+dy*.23,yy-dx*.23,5.03)],.115,key,16)
  H.box(mb,(x,y,2.45),(.24,.28,.57),'iron',a)
 # Modest perimeter lights, positioned on the footway side of the kerb.
 for side in ('north','south'):
  pts=PLAN['paths'][side]['points'];off=-(PLAN['paths'][side]['width']/2+(1.1 if side=='north' else .4))
  for d in (52,93,135,180,225,270,315):
   (x,y),a=at_path(pts,d,off)
   if y>219:continue
   H.cyl(mb,(x,y,3.0),.07,5.6,'iron',12);H.box(mb,(x,y,5.87),(.25,1.25,.12),'iron',a);H.box(mb,(x,y,5.79),(.19,1.11,.035),'lamp',a)
 H.build(mb,'intersection signals and coherent perimeter lighting','Street_Furniture')

def rear_y(x):
 # Envelope adjoining wall samples across window openings; do not follow rays
 # passing through an open sash to the opposite facade.
 values=[y for a,y in PLAN['rear_profile'] if abs(a-x)<=1.75 and y>1]
 return max(6.7,max(values) if values else 8.4)
def zroof(y,wall):return 4.97-(y-(wall+2.6))*.0267
def rear_concourse():
 for o in list(H.ACTIVE):
  if any(c.name=='V4_Architecture_RearConcourse' for c in o.users_collection):H.retire(o)
 glass=L.MeshBuilder();metal=L.MeshBuilder();frame=L.MeshBuilder();floor=L.MeshBuilder();fittings=L.MeshBuilder();supports=L.MeshBuilder();lights=L.MeshBuilder()
 # The angled south wing closes the gap beyond this point; terminate the
 # canopy at that pinch instead of pushing it through inherited masonry.
 start=-164;end=146;step=2
 profiles=[]
 for xa in range(start,end,step):
  xb=min(xa+step,end);wa=rear_y(xa);wb=rear_y(xb);ya=wa+2.6;yb=wb+2.6
  # True panels and frame joints replace the formerly separated roof patches.
  glass.add([(xa+.035,wa+.08,5.08),(xb-.035,wb+.08,5.08),(xb-.035,yb-.035,4.97),(xa+.035,ya-.035,4.97)],[(0,1,2,3)],H.I['glass'])
  metal.add([(xa,ya,4.97),(xb,yb,4.97),(xb,25,zroof(25,wb)),(xa,25,zroof(25,wa))],[(0,1,2,3)],H.I['steel'])
  H.tube(frame,[(xa,wa,5.11),(xa,ya,5.0),(xa,25,zroof(25,wa)+.025)],.045,'iron',6)
  for yfun,z in [(lambda w:w,5.12),(lambda w:w+2.6,4.995)]:H.tube(frame,[(xa,yfun(wa),z),(xb,yfun(wb),z)],.045,'steel',8)
  H.tube(frame,[(xa,25,zroof(25,wa)),(xb,25,zroof(25,wb))],.10,'steel',8)
  H.face(floor,[(xa,wa+.06),(xb,wb+.06),(xb,29),(xa,29)],.18,'mid')
  for y in range(math.ceil(max(wa,wb)),29):line(fittings,(xa,y),(xb,y),.012,.185,'joint')
  line(fittings,(xa,wa+.06),(xa,29),.012,.185,'joint')
  # Illuminated ceiling cove beside the skylight, supported by an opaque soffit.
  lights.add([(xa,ya+.10,4.73),(xb,yb+.10,4.73),(xb,yb+.66,4.59),(xa,ya+.66,4.59)],[(0,3,2,1)],H.I['lamp'])
  profiles.append([xa,xb,wa,wb])
 for x in range(-160,end,8):
  w=rear_y(x);z=zroof(25,w)
  H.box(supports,(x,24.1,(z+.18)/2),(.18,.22,z-.18),'steel');H.box(supports,(x,24.1,.235),(.46,.50,.11),'concrete')
  for dx in (-.14,.14):
   for dy in (-.17,.17):H.cyl(supports,(x+dx,24.1+dy,.30),.025,.04,'iron',6)
  H.tube(supports,[(x,24.1,z-.80),(x,22.9,z-.10)],.045,'steel')
  # Rainwater run and roof joints; fittings stop above the walking surface.
  if x%16==0:
   H.tube(fittings,[(x,25,z),(x,25.18,z-.3),(x,25.18,.30),(x,25.50,.22)],.060,'steel')
   for zz in (.7,1.7,2.7,3.7):H.box(fittings,(x,25.12,zz),(.23,.20,.05),'iron')
  # A maintenance rail sits on the opaque roof edge, rather than in the aisle.
  if x%16==0:H.cyl(fittings,(x,24.75,z+.43),.025,.85,'iron',8)
 for a,b in zip(profiles[:-1],profiles[1:]):
  xa=a[0];xb=b[0];H.tube(fittings,[(xa,24.75,zroof(25,a[2])+.83),(xb,24.75,zroof(25,b[2])+.83)],.024,'iron')
 H.build(glass,'continuous rear skylight panes following station wall','Rear_Skylight');H.build(metal,'connected standing seam concourse roof','Rear_Roof');H.build(frame,'skylight mullions gaskets and eaves','Rear_Frame')
 H.build(floor,'continuous paved rear passage','Rear_Floor');H.build(supports,'concourse columns baseplates and knee braces','Rear_Supports');H.build(fittings,'roof rails rainwater fittings and floor joints','Rear_Detail');H.build(lights,'warm ceiling cove along historical brick wall','Rear_Lighting')
 H.R['rear']={'x_range':[start,end],'profiles':profiles,'ground_z':.18,'clear_walk_offset':[.8,2.3]}
 for x in range(-155,end-4,12):
  w=rear_y(x);d=bpy.data.lights.new('V19 rear cove luminaire','AREA');d.energy=650;d.shape='RECTANGLE';d.size=5;d.size_y=1.5;d.color=(1.0,.88,.72)
  o=bpy.data.objects.new(d.name,d);H.col('Rear_Lighting').objects.link(o);o.location=(x,w+2.8,4.50);o['V19_kind']='Rear_Lighting'
 figures=[o for o in H.ACTIVE if o.name.startswith('V5 person plaza') and o.type in ['MESH','EMPTY']]
 for i,x in enumerate([-139,-113,-76,-55,-31,21,45,83,122]):
  if not figures:break
  q=figures[i%len(figures)].copy();H.col('Rear_People').objects.link(q);q.name=f'V19 concourse passenger {i+1}';q.location=(x,rear_y(x)+3.8,.18);q.rotation_euler.z=i*.71;q['V19_kind']='Rear_People'
 rear_equipment();end_yards()
def rear_equipment():
 mb=L.MeshBuilder();rng=random.Random(19)
 for i,x in enumerate([-151,-135,-74,-34,31,72,137]):
  w=rear_y(x);y=(w+2.6+24)/2;z=zroof(y,w)
  H.box(mb,(x,y,z+.13),(3.2,1.65,.25),'concrete');H.box(mb,(x,y,z+.60),(2.7,1.40,.74),'cream')
  H.box(mb,(x,y,z+1.0),(2.82,1.52,.08),'steel')
  for dx in (-.75,.75):
   H.cyl(mb,(x+dx,y,z+1.055),.46,.045,'iron',24)
   for j in range(7):H.box(mb,(x+dx+(j-3)*.11,y,z+1.088),(.025,.77,.018),'steel')
  for k in range(9):H.box(mb,(x,y-.72,z+.31+k*.065),(2.45,.08,.023),'steel')
  H.box(mb,(x+1.90,y,z+.38),(1.10,.60,.56),'steel')
  for xx in (x+1.45,x+2.35):H.box(mb,(xx,y,z+.38),(.05,.67,.64),'iron')
  H.tube(mb,[(x+1.3,y,z+.6),(x+2.4,y,z+.6),(x+2.4,24.3,z+.6)],.045,'steel')
  H.box(mb,(x-2.25,y,z+.055),(.85,1.1,.09),'iron');H.box(mb,(x-2.25,y,z+.12),(.72,.97,.04),'steel')
 H.build(mb,'roof ventilation units fans ducts hatches and flashings','Rear_Equipment')
 # Freestanding cabinets and conduit on service side; passenger aisle stays open.
 mb=L.MeshBuilder()
 for x in (-153,-128,-68,-29,29,68,128):
  H.box(mb,(x,27.3,1.12),(1.25,.58,1.85),'cream');H.box(mb,(x,26.98,1.12),(1.12,.045,1.70),'steel')
  for z in (.55,.67,.79,.91):H.box(mb,(x,26.95,z),(.87,.04,.035),'iron')
  H.box(mb,(x+.43,26.93,1.24),(.045,.045,.21),'iron')
  H.tube(mb,[(x+.72,27.15,.3),(x+.72,27.15,3.55),(x+3,27.15,3.55)],.04,'iron')
  H.box(mb,(x,26.91,1.65),(.23,.015,.18),'yellow')
 for x in (-80,-40,40,80):
  H.box(mb,(x,21.0,3.92),(3.4,.15,.56),'iron');H.box(mb,(x,21.0,4.28),(.04,.04,.22),'steel')
  H.label('JR  1・2   中央線',(x,20.91,3.94),.24,'white',group='Rear_Signs')
 H.build(mb,'rear service cabinets conduits and hanging wayfinding','Rear_Detail')
def end_yards():
 floor=L.MeshBuilder();mb=L.MeshBuilder()
 for label,x0,x1,building in [('north',-189,-164,(-184.8,-167.2,10.72,23.3)),('south',180,205,(182.72,201.28,10.22,21.8))]:
  # Four strips around each retained service building leave doors and walls intact.
  a,b,c,d=building
  for r in [(x0,x1,4.0,c),(x0,x1,d,27.0),(x0,a,c,d),(b,x1,c,d)]:
   if r[1]>r[0]:H.prism(floor,H.rect(*r),.01,.14,'concrete')
  for x in (x0+1,x1-1):
   H.box(mb,(x,7.0,.66),(.15,.15,1.05),'steel');H.box(mb,(x,7.0,1.08),(.17,.17,.08),'yellow')
  # Small service-yard fixtures: grated channels, hose reel and caged lights.
  for x in range(math.ceil(x0)+2,math.floor(x1)-1,2):
   H.box(mb,(x,6.2,.155),(1.8,.25,.035),'iron')
   for j in range(12):H.box(mb,(x-.81+j*.145,6.2,.18),(.04,.23,.025),'steel')
  for x in (a+2,b-2):
   H.box(mb,(x,c-.12,2.6),(.9,.25,.16),'iron');H.box(mb,(x,c-.27,2.56),(.72,.035,.08),'lamp')
   H.box(mb,(x,c-.21,1.18),(.62,.24,.8),'cream');H.box(mb,(x,c-.35,1.18),(.48,.025,.62),'red')
 for name in ['V13 North service alley grated drain and inspection covers','V13 South service alley grated drain and inspection covers']:
  q=H.copy(bpy.data.objects[name]);q.location.z+=.08
 H.build(floor,'connected north and south service-yard paving','Service_Yards');H.build(mb,'service-yard drains bollards cabinets and lamps','Service_Detail')
def main():
 args=sys.argv[sys.argv.index('--')+1:];sc=bpy.data.scenes['Tokyo Station'];bpy.context.window.scene=sc
 if sc.get('V19_connections'):raise RuntimeError('Start from V18')
 Path(args[2]).write_text(json.dumps(H.snapshot(),separators=(',',':')),encoding='utf8');H.setup()
 streets();rear_concourse()
 from render_review_cams_v19 import cameras
 cameras();sc['V19_connections']=json.dumps(H.R,ensure_ascii=False);sc['last_stage']='V19 rear concourse and connected street network'
 guide=Path(__file__).parent.parent/'README_V19.txt'
 if guide.exists():bpy.data.texts.new('README_V19_中文').write(guide.read_text(encoding='utf8'))
 bpy.context.view_layer.update();bpy.ops.file.pack_all();bpy.context.preferences.filepaths.save_version=0
 Path(args[0]).parent.mkdir(parents=True,exist_ok=True);bpy.ops.wm.save_as_mainfile(filepath=str(Path(args[0]).resolve()),compress=True)
 Path(args[1]).write_text(json.dumps(H.R,ensure_ascii=False,indent=2),encoding='utf8');print('V19_BUILD_OK',len(H.R['retained']),flush=True)
if __name__=='__main__':main()
