"""Asymmetric transport squares, slender glass shelters and plaza circulation."""
import bpy,math,random
from mathutils import Vector,Matrix
import v18lib as H
L=H.L
NORTH_OUT=[(-127,-112),(-127,-55),(-119,-39),(-54,-39),(-43,-48),(-43,-111),(-52,-120),(-118,-120)]
NORTH_IN=[(-119,-103),(-119,-64),(-110,-53),(-61,-53),(-52,-61),(-52,-100),(-61,-109),(-110,-109)]
SOUTH_OUT=[(49,-105),(49,-48),(59,-36),(106,-36),(153,-78),(153,-100),(140,-116),(66,-116)]
SOUTH_IN=[(60,-94),(60,-57),(66,-45),(103,-45),(141,-80),(140,-94),(132,-104),(79,-104)]
POOLS=[('north',H.round_poly(H.rect(-115.5,-87,-102,-59),.12),(-114,-88.5,-100.5,-60.5)),('south',H.round_poly([(82,-99),(112,-99),(131,-82),(131,-75),(104,-75),(82,-92)],.09),(83,130,-98,-76))]

def precinct(label,outer,inner):
 outer=H.round_poly(outer,.18);inner=H.round_poly(inner,.17)
 road=L.MeshBuilder();island=L.MeshBuilder();kerb=L.MeshBuilder()
 for i in range(len(outer)):
  j=(i+1)%len(outer);H.prism(road,[outer[i],outer[j],inner[j],inner[i]],.015,.142,'concrete')
 H.prism(island,inner,.015,.305,'pale')
 H.edge(kerb,outer,.20,.22,.16,'kerb');H.edge(kerb,inner,.23,.24,.16,'kerb')
 H.build(road,label+' light stone circulation loop','Transport_Roads')
 H.build(island,label+' combined planted and taxi island','Transport_Islands')
 ko=H.build(kerb,label+' shaped kerbs','Transport_Kerbs')
 # A real opening through the kerb lets the taxi pool connect to the loop.
 # Only local new geometry is cut; source Metro ground openings are unaffected.
 x=-101 if label=='north' else 101;y=-107 if label=='north' else -101
 mb=L.MeshBuilder();H.box(mb,(x,y,.3),(7,12,1),'iron');cut=H.build(mb,'temporary taxi entrance cut','Temporary')
 bpy.context.view_layer.objects.active=ko;mod=ko.modifiers.new('Taxi access kerb gap','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cut,do_unlink=True)
 ramp=L.MeshBuilder();y0=y-6;y1=y+5;bend=-109 if label=='north' else -104
 ramp.add([(x-3.4,y0,.145),(x+3.4,y0,.145),(x+3.4,bend,.318),(x-3.4,bend,.318),(x-3.4,y1,.318),(x+3.4,y1,.318)],[(0,1,2,3),(3,2,5,4)],H.I['asphalt'])
 H.build(ramp,label+' taxi-pool entrance ramp','Taxi_Access')
 H.R.setdefault('taxi_access',[]).append({'label':label,'x':x,'y0':y0,'y1':y1,'bend':bend,'width':6.8})
 # The loop joins the inherited perimeter street rather than being a closed
 # display island. The existing M8 entrance lies south of the north connection.
 if label=='north':
  p=[(-157,-58),(-121,-58),(-115,-47),(-151,-47)];c=(-123,-52,.3);size=(18,15,1)
 else:
  p=[(145,-83),(173,-64),(179,-73),(151,-92)];c=(152,-84,.3);size=(15,17,1)
 mb=L.MeshBuilder();H.prism(mb,p,.02,.144,'concrete');H.build(mb,label+' road connection to perimeter street','Road_Connections')
 mb=L.MeshBuilder();H.box(mb,c,size,'iron');cut=H.build(mb,'temporary street entrance cut','Temporary')
 bpy.context.view_layer.objects.active=ko;mod=ko.modifiers.new('Perimeter street opening','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cut,do_unlink=True)
 H.R.setdefault('road_connections',[]).append({'label':label,'outline':p})
 return inner

def parking():
 lines=L.MeshBuilder();paves=L.MeshBuilder()
 for label,p,b in POOLS:
  H.prism(paves,p,.305,.318,'asphalt')
  x0,x1,y0,y1=b;ny=int((y1-y0)/5.25);nx=int((x1-x0)/3.2)
  for j in range(ny):
   for i in range(nx):
    x=x0+i*3.2;y=y0+j*5.25;corners=H.rect(x,x+3.2,y,y+5.25)
    if not all(H.inside(a,c,p) for a,c in corners):continue
    H.edge(lines,corners,.324,.075,.008,'paint');H.R['taxi_bays'].append({'label':label,'c':[x+1.6,y+2.625],'size':[3.2,5.25]})
 H.build(paves,'two open asphalt taxi holding areas','Taxi_Pools');H.build(lines,'taxi holding grid markings','Road_Markings')
 H.count('taxi_pool_bays',len(H.R['taxi_bays']))

def landscaping():
 mb=L.MeshBuilder();plants=L.MeshBuilder()
 polys=[H.round_poly([(-81,-60),(-62,-58),(-56,-64),(-62,-67),(-76,-69)],.2),H.round_poly([(-80,-96),(-60,-94),(-55,-101),(-63,-106),(-78,-104)],.18),H.round_poly([(61,-92),(72,-96),(77,-102),(67,-107),(59,-99)],.2),H.round_poly([(104,-50),(118,-58),(130,-70),(121,-72),(107,-61)],.2)]
 for i,p in enumerate(polys):
  H.prism(mb,p,.306,.39,'soil');H.edge(mb,p,.40,.27,.20,'kerb')
  rng=random.Random(1820+i);lo=[min(q[k] for q in p) for k in (0,1)];hi=[max(q[k] for q in p) for k in (0,1)]
  for j in range(220):
   x=rng.uniform(lo[0],hi[0]);y=rng.uniform(lo[1],hi[1])
   if H.inside(x,y,p):H.box(plants,(x,y,.48),(.38,.38,.20),'hedge',rng.random()*math.pi)
 H.build(mb,'curved traffic-island planting beds','Planting');H.build(plants,'low planting around transport squares','Planting')
 # Clear the new pool and carriageway; smaller outer trees occupy planting beds.
 pos=[(-73,-63),(-65,-101),(66,-100),(116,-60),(126,-67)]
 for i,xy in enumerate(pos):
  o=bpy.data.objects[f'V18 perimeter tree {i+1}'];o.location=(*xy,.40)
  rec=next(r for r in H.R['trees'] if r['name']==o.name);rec['xy']=list(xy)
 # The northern ventilation canopy is moved into its planted island. Preserve
 # all native details and record the fitted photographic, non-surveyed offset.
 src=bpy.data.objects['V11 plaza ventilation tower 1 broad canopy and vertical fins'];q=H.copy(src);q.location.x-=9
 H.R['moved'].append({'name':q.name,'delta':[-9,0,0],'reason':'Fit northern ventilation tower within the revised combined island; approximate photographic alignment.'})

def sidewalks():
 mb=L.MeshBuilder();tiles=L.MeshBuilder();rng=random.Random(188)
 # Western north-square walkway with an actual gap for the existing M8 stairs.
 rects=[(-151,-127,-119,-98),(-151,-127,-90,-59),(-151,-146,-98,-90),(-129,-127,-98,-90)]
 for r in rects:
  H.prism(mb,H.rect(*r),.015,.30,'pale')
  for j in range(math.floor((r[3]-r[2])/.8)):
   for i in range(math.floor((r[1]-r[0])/1.2)):
    x=r[0]+i*1.2;y=r[2]+j*.8;H.face(tiles,H.rect(x+.008,x+1.192,y+.008,y+.792),.306,rng.choice(['white','pale','mid']))
 H.build(mb,'north western pavement around open M8 entrance','Paving');H.build(tiles,'north transport footway granite joints','Paving')

def shelter(name,a,b):
 mb=L.MeshBuilder();ax,ay=a;bx,by=b;dx=bx-ax;dy=by-ay;length=math.hypot(dx,dy);ux,uy=dx/length,dy/length;vx,vy=-uy,ux;angle=math.atan2(dy,dx)
 n=math.ceil(length/5.6);step=length/n
 for i in range(n+1):
  x=ax+dx*i/n;y=ay+dy*i/n
  # Rectangular paired steel flanges and a narrow web, with a cantilever arm.
  for off in (-.14,.14):H.box(mb,(x+ux*off,y+uy*off,2.24),(.065,.42,3.98),'iron',angle)
  H.box(mb,(x,y,2.24),(.26,.06,3.98),'iron',angle)
  H.box(mb,(x,y,4.24),(.20,3.65,.24),'iron',angle)
  H.box(mb,(x,y,.34),(.55,.65,.12),'steel',angle)
  H.box(mb,(x,y,4.08),(.20,.70,.045),'lamp',angle)
 for i in range(n):
  x=ax+dx*(i+.5)/n;y=ay+dy*(i+.5)/n
  for j in (-1,1):
   H.box(mb,(x+vx*j*.88,y+vy*j*.88,4.38),(step-.04,1.72,.055),'glass',angle)
  for s in (-1,1):H.box(mb,(x+vx*s*1.79,y+vy*s*1.79,4.36),(step,.06,.10),'steel',angle)
 H.build(mb,name+' slim cantilever glass shelter','Shelters');H.R['shelters'].append({'name':name,'a':a,'b':b,'width':3.6,'columns':n+1})

def rail_and_signs():
 mb=L.MeshBuilder()
 for xa,xb,y in [(-122,-50,-37.5),(50,88,-37.5),(-117,-90,-120.7),(84,122,-111.5)]:
  for x in [xa+k*2.5 for k in range(int((xb-xa)/2.5)+1)]:H.cyl(mb,(x,y,.86),.043,1.2,'iron',10)
  for z in (.57,1.18):H.tube(mb,[(xa,y,z),(xb,y,z)],.028,'iron')
 for x,y,label in [(-113,-120.5,'バスのりば'),(-82,-66,'タクシーのりば'),(85,-111.5,'バスのりば'),(81,-43,'タクシーのりば')]:
  H.box(mb,(x,y,1.7),(.08,.08,2.9),'iron');H.box(mb,(x,y,2.65),(1.7,.16,.65),'iron');H.box(mb,(x,y,1.55),(.62,.12,.90),'white')
  H.label(label,(x,y-.09,2.65),.21);H.label('TOKYO STATION',(x,y-.09,2.43),.09)
 H.build(mb,'waiting rails stop flags and timetable cases','Street_Furniture')
 # Simple stainless retractable bollards along the forecourt road boundaries.
 mb=L.MeshBuilder()
 for y in (-36,-121.5):
  for x in [-40,-35,-30,30,35,40]:
   H.lathe(mb,[(.13,.25),(.13,.91),(.115,1.04),(.0,1.06)],(x,y),'steel',16)
   H.cyl(mb,(x,y,.85),.135,.055,'paint',16)
 H.build(mb,'stainless plaza boundary bollards','Street_Furniture')

def road_marks():
 mb=L.MeshBuilder()
 for y in (-126.8,-131):
  for x in range(-151,156,7):H.stripe(mb,(x,y),(x+3.4,y),.12,.126)
 # Daily pedestrian crossings are offset to either side of the ceremonial axis.
 for x in (-38,38):
  for y in [ -133.7+k*1.0 for k in range(11)]:H.box(mb,(x,y,.127),(5.8,.48,.009),'paint')
  # Tactile warning blocks on each kerb approach.
  for yy in (-122.5,-135.0):
   H.box(mb,(x,yy,.245),(5.8,.6,.025),'yellow')
   for i in range(29):
    for j in range(3):H.cyl(mb,(x-2.8+i*.2,yy-.2+j*.2,.263),.025,.025,'yellow',8)
 # Direction arrows in the new loops, fitted to the actual road strips.
 for x,y,a in [(-96,-44,0),(-99,-115,math.pi),(-122,-80,-math.pi/2),(-47,-81,math.pi/2),(100,-111,math.pi),(143,-85,math.pi/2),(54,-77,-math.pi/2)]:
  F=Matrix.Translation((x,y,.151))@Matrix.Rotation(a,4,'Z');pts=[(-1.5,-.12),(0,-.12),(0,-.65),(1.2,0),(0,.65),(0,.12),(-1.5,.12)]
  mb.add([tuple(F@Vector((u,v,0))) for u,v in pts],[tuple(range(7))],H.I['paint'])
 H.build(mb,'traffic direction arrows and offset pedestrian crossings','Road_Markings')

def taxi_mesh():
 mb=L.MeshBuilder();H.box(mb,(0,0,.75),(4.45,1.72,.82),'blackcar')
 # Sloping glazed cabin, separate side windows, trim, lamps, mirrors and wheels.
 v=[(-1.70,-.81,1.05),(1.20,-.81,1.05),(1.20,.81,1.05),(-1.70,.81,1.05),(-1.42,-.74,1.80),(.80,-.74,1.80),(.80,.74,1.80),(-1.42,.74,1.80)]
 mb.add(v,[(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)],H.I['window'])
 H.box(mb,(-.3,0,1.82),(2.35,1.49,.08),'blackcar')
 for s in (-1,1):
  for x in (-1.42,-.65,.22,.80):H.box(mb,(x,s*.78,1.43),(.075,.08,.75),'blackcar')
  H.box(mb,(-.2,s*.88,1.06),(3.1,.035,.055),'steel');H.box(mb,(.9,s*1.0,1.18),(.25,.25,.12),'blackcar')
  for x in (-.95,.25):H.box(mb,(x,s*.89,.93),(.19,.04,.045),'steel')
  for x in (-1.35,1.35):
   H.tube(mb,[(x,s*.79,.30),(x,s*.94,.30)],.30,'rubber',20);H.tube(mb,[(x,s*.94,.30),(x,s*.96,.30)],.16,'steel',12)
  H.box(mb,(2.245,s*.56,.85),(.035,.34,.15),'lamp');H.box(mb,(-2.245,s*.58,.9),(.035,.27,.30),'red')
 H.box(mb,(2.25,0,.64),(.025,.64,.18),'iron');H.box(mb,(2.27,0,.47),(.025,.34,.15),'green')
 H.box(mb,(-.05,0,1.98),(.40,.25,.22),'lamp')
 for s in (-1,1):H.tube(mb,[(.95,s*.30,1.16),(.85,s*.54,1.59)],.013,'iron',5)
 return mb

def bus_mesh():
 mb=L.MeshBuilder();H.box(mb,(0,0,1.65),(10.6,2.45,2.65),'cream')
 H.box(mb,(0,0,.79),(10.65,2.48,.42),'green');H.box(mb,(0,0,2.98),(10.5,2.40,.10),'white')
 for s in (-1,1):
  H.box(mb,(0,s*1.24,1.85),(9.9,.025,1.3),'iron')
  for x in [ -4.3+i*1.18 for i in range(8)]:H.box(mb,(x,s*1.26,1.9),(1.04,.03,1.10),'window')
  for x in (-3.25,3.35):
   H.tube(mb,[(x,s*1.1,.44),(x,s*1.30,.44)],.42,'rubber',20);H.tube(mb,[(x,s*1.3,.44),(x,s*1.32,.44)],.23,'steel',16)
 for x in (-1.7,4.15):
  H.box(mb,(x,-1.285,1.45),(1.05,.035,1.95),'iron')
  for dx in (-.26,.26):H.box(mb,(x+dx,-1.31,1.60),(.43,.035,1.50),'window')
 H.box(mb,(5.32,0,1.93),(.035,2.20,1.35),'window');H.box(mb,(5.35,0,2.73),(.035,1.65,.25),'iron')
 for s in (-1,1):
  H.box(mb,(5.34,s*.83,.94),(.04,.44,.18),'lamp');H.box(mb,(-5.34,s*.88,.90),(.04,.19,.44),'red')
  H.tube(mb,[(5.28,s*1.05,2.6),(5.55,s*1.43,2.6),(5.55,s*1.43,2.25)],.035,'iron');H.box(mb,(5.55,s*1.43,2.20),(.19,.12,.38),'iron')
  H.tube(mb,[(5.37,s*.37,1.45),(5.37,s*.78,2.14)],.018,'iron',6)
 for x in (-2,2):H.box(mb,(x,0,3.11),(1.7,1.55,.22),'white')
 return mb

def vehicles():
 base=H.build(taxi_mesh(),'taxi 01','Vehicles');selected=[r for i,r in enumerate(H.R['taxi_bays']) if i%4==0 and not (r['label']=='south' and abs(r['c'][0]-101)<5 and r['c'][1]<-93)][:19]
 for i,r in enumerate(selected):
  if i==0:o=base
  else:o=base.copy();o.data=base.data;H.col('Vehicles').objects.link(o)
  o.name=f'V18 waiting taxi {i+1:02d}';o.location=(*r['c'],.318);o.rotation_euler.z=math.pi/2;o['V18_kind']='Vehicles';o['V18_taxi_pool']=r['label']
 for i,(x,y,a) in enumerate([(-101,-115.2,0),(114,-107.4,0)]):
  o=H.build(bus_mesh(),f'city route bus {i+1}','Vehicles');o.location=(x,y,.142);o.rotation_euler.z=a
  tx=H.label('都営バス',(0,-1.32,.95),.28);tx.parent=o;tx.location=(0,-1.32,.95)
 H.count('waiting_taxis',len(selected));H.count('route_buses',2)

def people():
 from mod18_plaza import LAWNS,BASINS,TREES,inrect
 rng=random.Random(18191);changed=0
 for o in H.ACTIVE:
  if not o.name.startswith('V5 person plaza'):continue
  x,y,z=o.location
  if y>-34:continue
  bad=any(inrect(x,y,r,.8) for r in LAWNS) or any(abs(x-a)<3.1 and abs(y-b)<3.1 for a,b in TREES) or abs(x)>42
  if not bad:continue
  q=H.copy(o)
  for _ in range(300):
   x=rng.uniform(-40,40);y=rng.uniform(-120,-35)
   if any(inrect(x,y,r,1) for r in LAWNS) or any(abs(x-a)<3.4 and abs(y-b)<3.4 for a,b in TREES):continue
   if any(inrect(x,y,r) for r in BASINS) and rng.random()<.65:continue
   break
  q.location=(x,y,.249);changed+=1
 # Early V3 visitors are individual head/torso/leg meshes. Move the complete
 # nearby figure, retaining every original, when a new lawn occupies its spot.
 heads=[o for o in H.ACTIVE if o.name.startswith('Visitor head')]
 parts=[o for o in H.ACTIVE if o.name.startswith(('Visitor head','Visitor torso','Visitor leg'))]
 moved=set()
 for head in heads:
  lo,hi=H.bounds(head);c=(lo+hi)/2
  if not -123<c.y<-34:continue
  if not any(inrect(c.x,c.y,r,.6) for r in LAWNS) and not any(abs(c.x-a)<3.1 and abs(c.y-b)<3.1 for a,b in TREES):continue
  target=Vector((rng.uniform(-8,8),c.y,0));delta=Vector((target.x-c.x,target.y-c.y,.05))
  for part in parts:
   if part.name in moved:continue
   lo,hi=H.bounds(part);pc=(lo+hi)/2
   if math.hypot(pc.x-c.x,pc.y-c.y)<.45:
    name=part.name;q=H.copy(part);q.location+=delta;moved.add(name)
  changed+=1
 H.count('pedestrians_repositioned_from_lawns_and_furniture',changed)

def transport():
 precinct('north',NORTH_OUT,NORTH_IN);precinct('south',SOUTH_OUT,SOUTH_IN);parking();landscaping();sidewalks()
 for args in [('north station front',(-123,-33.5),(-47,-33.5)),('north return',(-47,-33.5),(-47,-48.5)),('south station front',(47,-33.5),(89,-33.5)),('south return',(47,-33.5),(47,-50.5)),('north taxi waiting',(-83,-87),(-83,-62)),('north bus stop',(-116,-120.8),(-89,-120.8)),('south bus stop',(87,-112.5),(124,-112.5))]:shelter(*args)
 rail_and_signs();road_marks();vehicles()
