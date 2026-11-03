"""V19 -> V20: photograph-derived Chuo arches, covered end passage and staff room.
-- out.blend build.json baseline.json
"""
import bpy,sys,math,json,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
sys.path.insert(0,str(Path(__file__).parent))
import v20lib as H
L=H.L;Z=16.51
def roof_profile():
 o=bpy.data.objects['V10 01-02 differentiated roof skin'];v=H.world(o);xs=np.unique(np.round(v[:,0],4))
 yw=[];ye=[]
 for x in xs:
  q=v[abs(v[:,0]-x)<.001];yw.append(q[:,1].min());ye.append(q[:,1].max())
 return lambda x:(float(np.interp(x,xs,yw)),float(np.interp(x,xs,ye)))
EDGES=None

def acoustic_arches():
 """Keep the already corrected deck ends. Taller bays only beside the canopy."""
 arches=L.MeshBuilder();posts=L.MeshBuilder();beams=L.MeshBuilder()
 for name,k,side,oldh in [('west','01',-1,2.2),('east','02',1,1.85)]:
  old=bpy.data.objects['V13 Chuo '+name+' deck-edge acoustic screen'];H.retire(old)
  deck=H.world(bpy.data.objects['V3 Track '+k+' curved viaduct']);x0=math.ceil(deck[:,0].min()+1);x1=math.floor(deck[:,0].max()-.65)
  skin=L.MeshBuilder();xs=np.linspace(x0,x1,math.ceil((x1-x0)/2.5)+1)
  for a,b in zip(xs[:-1],xs[1:]):
   x=(a+b)/2;t=max(0,min(1,(x+140)/7,(116-x)/8));h=oldh+(3.55-oldh)*t
   if a==x0 or b==x1:h=1.20
   F=Matrix.Translation((x,H.ty(k,x),14.9))@Matrix.Rotation(math.atan2(H.ty(k,x+.1)-H.ty(k,x-.1),.2),4,'Z')@Matrix.Translation((0,side*1.94,0))
   ln=math.hypot(b-a,H.ty(k,b)-H.ty(k,a));opaque=max(.8,h-.69)
   H.box(skin,(0,0,.28),(ln,.18,.56),'concrete',F)
   for zz in np.arange(.56,opaque,.46):H.box(skin,(0,0,(zz+min(zz+.445,opaque))/2),(ln-.085,.085,min(.445,opaque-zz)),'silver',F)
   if h>1.25:H.box(skin,(0,0,(opaque+h)/2),(ln-.09,.045,h-opaque-.035),'glass',F)
   for dx in (-ln/2+.037,ln/2-.037):H.box(skin,(dx,0,h/2),(.075,.22,h+.04),'trim',F)
   for zz in (opaque,h):H.box(skin,(0,0,zz),(ln,.16,.065),'trim',F)
  H.build(skin,'Chuo '+name+' framed acoustic panels','Acoustic_Screens',track=k,x0=x0,x1=x1)
  # Curved ribs attach to the outer edge and return to the roof. The crest is
  # fitted above this model's existing messenger wire, not claimed as a survey.
  for x in [-128,-119,-109.7,-100.3,-81,-72.3,-63,-53.7,-35,-16.3,6,28.5,49,57.5,79.4,98.1,107]:
   outer=H.ty(k,x)+side*1.94;inner=EDGES(x)[0 if side==-1 else 1]+(-side)*.12
   p0=Vector((x,outer,18.45));p1=Vector((x,outer,25.1));p2=Vector((x,inner,23.3));p3=Vector((x,inner,20.86))
   pts=[tuple((1-t)**3*p0+3*(1-t)**2*t*p1+3*(1-t)*t*t*p2+t**3*p3) for t in np.linspace(0,1,49)]
   H.sweep(arches,pts,.29,.22,'steel')
   for dx in (-.16,.16):H.sweep(arches,[(a+dx,b,c) for a,b,c in pts],.035,.31,'trim')
   H.box(posts,(x,outer,16.675),(.26,.29,3.55),'steel');H.box(posts,(x,outer,14.99),(.49,.52,.18),'silver')
   H.box(posts,(x,inner,20.71),(.54,.42,.32),'steel')
   for dx in (-.17,.17):
    for dy in (-.18,.18):H.cyl(posts,(x+dx,outer+dy,15.10),.035,.05,'trim',6)
   H.R['arches'].append({'side':side,'x':x,'track':k,'outer_y':outer,'inner_y':inner,'path':pts})
  # Two longitudinal seat rails tie the new ribs to the original eave.
  p=[(float(x),EDGES(x)[0 if side==-1 else 1],20.78) for x in np.linspace(-132,108,161)]
  H.tube(beams,p,.085,'steel',8)
 H.build(arches,'paired curved acoustic screen to canopy ribs','Curved_Ribs')
 H.build(posts,'arched rib posts anchor bolts and eave seats','Rib_Anchors')
 H.build(beams,'continuous eave attachment rails','Rib_Anchors');H.count('curved_ribs',len(H.R['arches']))

def end_passage():
 """The photographed small arch is modelled as a person-sized covered passage."""
 H.retire(bpy.data.objects['V4_Structure_Staff_gate_01-02_south'])
 F=H.frame(109.0);length=11.3;w=2.10;r=w/2;spring=1.32
 ribs=L.MeshBuilder();skin=L.MeshBuilder();floor=L.MeshBuilder();gate=L.MeshBuilder();details=L.MeshBuilder()
 def p(u,v,z):return tuple(F@Vector((u,v,z)))
 H.box(floor,(length/2,0,-.11),(length,2.48,.22),'concrete',F)
 for y in (-.92,.92):H.box(floor,(length/2,y,-.33),(length,.18,.34),'steel',F)
 for u in (4,7,10.8):
  H.box(floor,(u,0,-.95),(.40,1.9,1.44),'concrete',F)
  H.box(floor,(u,0,-1.64),(.68,2.1,.12),'concrete',F)
  wx=(F@Vector((u,0,0))).x
  H.box(floor,(wx,H.yc(wx),14.73),(.55,H.ty('02',wx)-H.ty('01',wx)-3.4,.30),'steel')
 for u in np.arange(.25,length,.5):H.box(details,(u,0,.008),(.013,2.09,.014),'seam',F)
 for a,b in zip(np.arange(0,length,1.6),np.minimum(np.arange(0,length,1.6)+1.6,length)):
  for side in (-1,1):
   H.box(skin,((a+b)/2,side*r,.47),(b-a-.025,.06,.94),'silver',F)
   H.box(skin,((a+b)/2,side*r,1.12),(b-a-.025,.04,.35),'glass',F)
  for t0,t1 in zip(np.linspace(0,math.pi,25)[:-1],np.linspace(0,math.pi,25)[1:]):
   skin.add([p(a,r*math.cos(t0),spring+r*math.sin(t0)),p(b,r*math.cos(t0),spring+r*math.sin(t0)),p(b,r*math.cos(t1),spring+r*math.sin(t1)),p(a,r*math.cos(t1),spring+r*math.sin(t1))],[(0,1,2,3)],H.I['glass'])
 for u in [*np.arange(0,length,1.6),length]:
  path=[p(u,-r,0),p(u,-r,spring)]+[p(u,r*math.cos(t),spring+r*math.sin(t)) for t in np.linspace(math.pi,0,41)]+[p(u,r,0)]
  H.tube(ribs,path,.075 if u else .13,'silver',10)
 for t in (.35,math.pi/2,math.pi-.35):H.tube(ribs,[p(0,r*math.cos(t),spring+r*math.sin(t)),p(length,r*math.cos(t),spring+r*math.sin(t))],.028,'steel')
 # A barred access gate keeps the photographed entrance visibly open above it.
 for y in (-1.15,1.15):H.tube(gate,[p(-.18,y,0),p(-.18,y,1.25)],.055,'trim')
 for z in (.16,1.18):H.tube(gate,[p(-.2,-1.05,z),p(-.2,1.05,z)],.035,'trim')
 for y in np.arange(-1.0,1.01,.17):H.tube(gate,[p(-.2,y,.17),p(-.2,y,1.18)],.015,'trim',6)
 H.box(gate,(-.24,.46,.77),(.035,.64,.34),'white',F)
 H.text('関係者以外',p(-.265,.46,.84),.085,'red',right=tuple(F.to_3x3()@Vector((0,-1,0))))
 H.text('立入禁止',p(-.265,.46,.71),.10,'red',right=tuple(F.to_3x3()@Vector((0,-1,0))))
 for s in (-1,1):
  for u in (-1.2,-.15):H.tube(gate,[p(u,s*1.28,0),p(u,s*1.28,1.15)],.038,'trim')
  for z in (.55,1.1):H.tube(gate,[p(-1.2,s*1.28,z),p(-.15,s*1.28,z)],.027,'trim')
 # Solid service end, with a narrow glazed personnel door.
 H.box(skin,(length,0,.65),(.09,w,1.3),'silver',F)
 for y in (-.66,.66):H.box(skin,(length,y,1.65),(.09,.76,.75),'silver',F)
 H.box(details,(length-.06,0,1.0),(.035,.75,1.95),'steel',F)
 H.box(details,(length-.085,0,1.45),(.025,.22,.63),'glass',F)
 for u in (1.2,5.6,9.5):H.box(details,(u,0,2.28),(.65,.12,.04),'light',F)
 # End-of-platform ladder and crossing tactile warning strip.
 for y in (-.28,.28):H.tube(details,[p(-2.0,y,0),p(-2.0,y,3.82)],.025,'trim')
 for z in np.arange(.2,3.8,.29):H.tube(details,[p(-2,-.28,z),p(-2,.28,z)],.018,'trim')
 H.box(details,(-1.4,0,.025),(.45,2.6,.035),'yellow',F)
 H.build(floor,'end passage supported walkway','End_Passage_Floor')
 H.build(skin,'end passage glazed barrel and metal lower panels','End_Passage')
 H.build(ribs,'end passage curved portal and repeated hoops','End_Passage')
 H.build(gate,'end passage staff gate and guardrails','End_Gate')
 H.build(details,'end passage ladder paving door and lights','End_Passage_Detail')
 H.R['passage']={'frame':[list(row) for row in F],'length':length,'clear_width':1.94,'spring':spring,'radius':r,'floor_z':Z,'location_basis':'fitted to retained south staff gate and model buffer end; image gives form, not surveyed chainage'};H.count('covered_end_passages')

def rounded_outline(length,width,r,n=24):
 pts=[]
 for x,y,a in [(length/2-r,width/2-r,0),(-length/2+r,width/2-r,math.pi/2),(-length/2+r,-width/2+r,math.pi),(length/2-r,-width/2+r,math.pi*1.5)]:
  pts.extend([(x+r*math.cos(t),y+r*math.sin(t)) for t in np.linspace(a,a+math.pi/2,n+1)])
 return pts

def staff_room():
 F=H.frame(41.6);length=10.4;width=3.1;height=3.23;outline=rounded_outline(length,width,.64)
 walls=L.MeshBuilder();trim=L.MeshBuilder();fittings=L.MeshBuilder()
 def p(x,y,z):return tuple(F@Vector((x,y,z)))
 # Each cladding course is separated by a physical shadow joint. Corner seams
 # follow the radius, while straight walls retain larger rectangular panels.
 for row,(z0,z1) in enumerate(zip(np.linspace(.08,height,8)[:-1],np.linspace(.08,height,8)[1:])):
  for a,b in zip(outline,outline[1:]+outline[:1]):
   # Door opening at the north end; an inset panel closes it without coplanar faces.
   if a[0]<-length/2+.01 and b[0]<-length/2+.01 and row<5:continue
   verts=[p(*a,z0+.012),p(*b,z0+.012),p(*b,z1-.012),p(*a,z1-.012)]
   walls.add(verts,[(0,1,2,3)],H.I['silver'],smooth=abs(a[0]-b[0])>.001 and abs(a[1]-b[1])>.001)
 # Opaque inner liner, slightly inset; ceiling and floor close the shell.
 for a,b in zip(outline,outline[1:]+outline[:1]):
  aa=(a[0]*.992,a[1]*.976);bb=(b[0]*.992,b[1]*.976)
  walls.add([p(*aa,.03),p(*bb,.03),p(*bb,height),p(*aa,height)],[(0,1,2,3)],H.I['seam'])
 for z,k in [(0,'concrete'),(height,'silver')]:walls.add([p(x,y,z) for x,y in outline],[tuple(range(len(outline)))],H.I[k])
 for z in (.06,height-.035):H.tube(trim,[p(x,y,z) for x,y in outline+outline[:1]],.035,'trim')
 for x in np.arange(-length/2+.7,length/2-.5,1.50):
  for s in (-1,1):H.box(trim,(x,s*(width/2+.007),height/2),(.018,.018,height-.16),'seam',F)
 # North door with window, hinges, closer, pull handle and keypad.
 H.box(fittings,(-length/2-.025,0,1.15),(.055,1.12,2.24),'steel',F)
 for sy in (-1,1):
  for z0,z1 in zip(np.linspace(.08,height,8)[:-1],np.linspace(.08,height,8)[1:]):
   if z0>2.30:continue
   H.box(walls,(-length/2,sy*.745,(z0+min(z1,2.30))/2),(.025,.35,min(z1,2.30)-z0-.02),'silver',F)
 H.box(fittings,(-length/2-.059,0,1.15),(.016,.99,2.12),'silver',F)
 H.box(fittings,(-length/2-.075,-.15,1.53),(.017,.18,.80),'glass',F)
 for y in (-.57,.57):H.box(trim,(-length/2-.07,y,1.16),(.055,.045,2.30),'trim',F)
 H.box(trim,(-length/2-.07,0,2.29),(.055,1.18,.045),'trim',F)
 H.box(fittings,(-length/2-.12,.32,2.17),(.14,.28,.11),'steel',F)
 H.tube(fittings,[(-length/2-.10,.34,.99),(-length/2-.18,.34,.99),(-length/2-.18,.34,1.20),(-length/2-.10,.34,1.20)],.018,'trim',F=F)
 H.box(fittings,(-length/2-.12,.50,1.34),(.055,.10,.22),'black',F)
 for z in (1.28,1.33,1.38):
  for y in (.475,.515):H.box(fittings,(-length/2-.152,y,z),(.007,.018,.015),'white',F)
 H.text('係員室',p(-length/2-.075,0,2.53),.16,'black',right=tuple(F.to_3x3()@Vector((0,-1,0))))
 for side in (-1,1):
  # Ribbon windows and shallow aluminium reveal, as visible in the third image.
  for x in (1.4,2.6,3.8):
   H.box(fittings,(x,side*(width/2+.035),2.22),(1.16,.07,.61),'steel',F)
   H.box(fittings,(x,side*(width/2+.079),2.22),(1.06,.022,.51),'glass',F)
   H.box(fittings,(x,side*(width/2+.095),2.22),(.025,.026,.51),'trim',F)
  H.box(fittings,(-3.25,side*(width/2+.03),.65),(.68,.06,.66),'seam',F)
  for zz in np.arange(.37,.98,.075):H.box(fittings,(-3.25,side*(width/2+.079),zz),(.62,.09,.025),'silver',F)
  H.box(fittings,(-1.4,side*(width/2+.035),1.70),(.48,.055,.31),'white',F)
 H.build(walls,'rounded silver staff room cladding','Staff_Room')
 H.build(trim,'staff room curved reveals and panel joints','Staff_Room')
 H.build(fittings,'staff room ribbon windows personnel door and fittings','Staff_Room_Fittings')
 H.R['staff_room']={'frame':[list(row) for row in F],'length':length,'width':width,'height':height,'corner_radius':.64};H.count('staff_rooms')

def room_clearance_fixes():
 # Relocate the complete local sign assemblies, including their lettering and
 # hangers, rather than cutting visible parts off against the new enclosure.
 for name in ['V5 platform 01-02 furniture and signs','V6 platform signs | hanging boards']:
  old=bpy.data.objects[name];v,inv,lo,hi=H.component_labels(old);mid=(lo+hi)/2
  chosen=(mid[:,0]>36)&(mid[:,0]<47)&(mid[:,1]>17)&(mid[:,1]<30)&(lo[:,2]>18.25)&(hi[:,2]>18.9)
  mask=chosen[inv]
  if not np.any(mask):continue
  q=H.copy_source(old);v[mask]+=np.array([12,H.yc(53.6)-H.yc(41.6),0]);im=np.array(q.matrix_world.inverted());local=v@im[:3,:3].T+im[:3,3]
  q.data.vertices.foreach_set('co',local.ravel());q.data.update();H.R.setdefault('adjusted_signs',[]).append({'object':name,'components':int(chosen.sum()),'dx':12})
 F=H.frame(41.6);inv=F.inverted()
 for o in list(bpy.context.scene.objects):
  if o.type!='EMPTY' or not o.instance_collection or o.hide_render:continue
  p=inv@o.matrix_world.translation
  if -6.8<p.x<5.8 and abs(p.y)<1.98 and abs(p.z)<.2:
   q=H.copy_source(o);old=list(q.matrix_world.translation);p.y=2.45 if p.y>=0 else -2.45;q.matrix_world.translation=F@p
   H.R.setdefault('moved_people',[]).append({'object':q.name,'from':old,'to':list(q.matrix_world.translation)})

def paving_joints():
 from mathutils.bvhtree import BVHTree
 deck=bpy.data.objects['V3 Platform 01-02 raised deck'];tree=BVHTree.FromPolygons([deck.matrix_world@v.co for v in deck.data.vertices],[tuple(p.vertices) for p in deck.data.polygons]);mb=L.MeshBuilder()
 def on(x,y):return tree.ray_cast(Vector((x,y,Z+.03)),Vector((0,0,-1)),.06)[0] is not None
 def line(axis,fix,lo,hi):
  values=np.arange(lo,hi+.001,.25);start=None;last=None
  for u in values:
   x,y=(fix,u) if axis==0 else (u,fix);ok=on(x,y)
   if ok and start is None:start=u
   if start is not None and (not ok or u==values[-1]):
    end=last if not ok else u
    if end is not None and end-start>.15:
     if axis==0:H.box(mb,(fix,(start+end)/2,Z+.002),(.009,end-start,.0015),'concrete')
     else:H.box(mb,((start+end)/2,fix,Z+.002),(end-start,.009,.0015),'concrete')
    start=None
   last=u
 for x in np.arange(-144.5,112,.90):line(0,float(x),17.15,35.4)
 for y in np.arange(17.5,35.5,.90):line(1,float(y),-145,112)
 H.build(mb,'Chuo platform paving joints clear of stair openings','Paving')

def ceiling():
 H.retire(bpy.data.objects['V8 canopy 01-02 | light fittings'])
 mb=L.MeshBuilder();ribs=L.MeshBuilder();lamps=L.MeshBuilder()
 # Preserve existing pole openings in the canopy; no new solid ceiling through them.
 mast=[]
 import csv
 with (Path(__file__).parent.parent/'validation/surface_catenary_masts.csv').open() as f:
  for row in csv.DictReader(f):
   if row['zone']=='Chuo':mast.append((float(row['x']),float(row['y'])))
 def blocked(x,y):return any(abs(x-a)<1.15 and abs(y-b)<.6 for a,b in mast)
 for a in np.arange(-132,108,2):
  b=min(a+1.98,108);w,e=EDGES((a+b)/2)
  for f0 in np.arange(.025,.975,.025):
   f1=f0+.024;ym=w+(e-w)*(f0+f1)/2
   if blocked((a+b)/2,ym):continue
   ps=[(x,EDGES(x)[0]+(EDGES(x)[1]-EDGES(x)[0])*f,20.32) for x,f in [(a,f0),(b,f0),(b,f1),(a,f1)]]
   H.shell(mb,ps,.035,'soffit')
   H.tube(ribs,[(a,ps[0][1],20.275),(b,ps[1][1],20.275)],.011,'steel',4)
  for f in (.17,.50,.83):
   y=w+(e-w)*f
   if blocked((a+b)/2,y):continue
   F=H.frame((a+b)/2,y,20.21);H.box(lamps,(0,0,0),(b-a,.24,.11),'silver',F)
   H.box(lamps,(0,0,-.065),(b-a-.05,.19,.035),'light',F)
 H.build(mb,'Chuo ribbed ceiling panels with pole clearances','Ceiling')
 H.build(ribs,'Chuo longitudinal ceiling grooves','Ceiling')
 H.build(lamps,'three rows of continuous ceiling luminaires','Ceiling_Lights')
 # Local soft fill makes the covered platform readable without altering the sun.
 for x in (-112,-66,-20,25,61,95):
  d=bpy.data.lights.new('V20 platform soft light','AREA');d.energy=420;d.shape='RECTANGLE';d.size=8;d.size_y=4;d.color=(.88,.93,1)
  o=bpy.data.objects.new(d.name,d);H.col('Lighting').objects.link(o);o.location=(x,H.yc(x),20.0);o['V20_kind']='Lighting'

def surveillance():
 for j,x in enumerate([-113,-68,-22,29,57,96]):
  w,e=EDGES(x)
  for side in (-1,1):
   y=H.yc(x)+side*(e-w)*.28;F=H.frame(x,y,19.34)@Matrix.Rotation(0 if j%2==0 else math.pi,4,'Z')
   mb=L.MeshBuilder();cable=L.MeshBuilder()
   H.box(mb,(0,0,.88),(.22,.20,.10),'silver',F);H.tube(mb,[(0,0,.84),(0,0,.28),(.12,0,.22)],.025,'trim',F=F)
   H.box(mb,(.14,0,.18),(.12,.18,.10),'steel',F)
   C=F@Matrix.Translation((.13,0,0))@Matrix.Rotation(math.radians(12),4,'Y')
   H.box(mb,(0,0,0),(.49,.22,.20),'cream',C);H.box(mb,(.26,0,0),(.025,.192,.173),'black',C)
   H.box(mb,(.05,0,.12),(.65,.27,.032),'cream',C)
   for s in (-1,1):H.box(mb,(.23,s*.129,.065),(.23,.026,.10),'cream',C)
   LF=C@Matrix.Translation((.28,0,0))@Matrix.Rotation(math.pi/2,4,'Y');H.cyl(mb,(0,0,0),.056,.027,'trim',20,LF);H.cyl(mb,(0,0,.017),.041,.013,'lens',20,LF)
   H.tube(cable,[(-.20,0,0),(-.32,0,-.05),(-.36,0,.24),(-.06,0,.55),(0,0,.82)],.012,'black',F=F)
   for z in (.34,.62):H.tube(cable,[(-.04,0,z),(.04,0,z)],.018,'steel',F=F)
   o=H.build(mb,f'CCTV {j+1:02d} {side:+d} housing hood lens and bracket','CCTV');H.build(cable,f'CCTV {j+1:02d} {side:+d} cable loop','CCTV')
   H.R['cameras'].append({'object':o.name,'x':x,'y':y,'mount_z':20.22,'bottom_z':19.10});H.count('cctv_cameras')
 # Larger departure-view monitors are distinct from the small camera housings.
 for j,x in enumerate([-75,58,101]):
  for side in (-1,1):
   y=H.yc(x)+side*1.48;F=H.frame(x,y,19.42)@Matrix.Rotation(math.pi if side<0 else 0,4,'Z');mb=L.MeshBuilder()
   H.box(mb,(0,0,0),(.42,.76,.52),'cream',F)
   H.box(mb,(.226,0,0),(.035,.67,.43),'black',F);H.box(mb,(.247,0,0),(.012,.58,.34),'screen',F)
   H.box(mb,(.15,0,.30),(.82,.85,.04),'cream',F)
   for s in (-1,1):H.box(mb,(.20,s*.41,.02),(.72,.035,.53),'cream',F)
   H.box(mb,(-.23,0,.02),(.07,.48,.30),'silver',F)
   for zz in (-.09,-.045,0,.045,.09):H.box(mb,(-.272,0,zz),(.012,.34,.014),'seam',F)
   H.tube(mb,[(0,0,.28),(0,0,.81)],.040,'trim',F=F)
   for sy in (-.29,.29):H.tube(mb,[(-.10,sy,.29),(-.06,sy,.72),(0,0,.81)],.011,'steel',F=F)
   for z in (-.22,.22):
    for yy in (-.33,.33):H.box(mb,(-.216,yy,z),(.015,.028,.028),'trim',F)
   # Native schematic display, not a fabricated surveillance photograph.
   for yy in (-.16,.16):H.box(mb,(.255,yy,0),(.012,.008,.25),'silver',F)
   o=H.build(mb,f'platform departure monitor {j+1} {side:+d} with weather hood','Monitors');H.R['monitors'].append({'object':o.name,'x':x,'y':y});H.count('departure_monitors')

def main():
 global EDGES
 args=sys.argv[sys.argv.index('--')+1:];sc=bpy.data.scenes['Tokyo Station'];bpy.context.window.scene=sc
 if sc.get('V20_chuo'):raise RuntimeError('Start from V19')
 Path(args[2]).write_text(json.dumps(H.snapshot(),separators=(',',':')),encoding='utf8');H.setup();EDGES=roof_profile()
 acoustic_arches();end_passage();staff_room();room_clearance_fixes();paving_joints();ceiling();surveillance()
 from render_review_cams_v20 import cameras
 cameras();sc['V20_chuo']=json.dumps(H.R);sc['last_stage']='V20 Chuo curved canopy connections and platform fittings'
 guide=Path(__file__).parent.parent/'README_V20.txt'
 if guide.exists():bpy.data.texts.new('README_V20').write(guide.read_text(encoding='utf8'))
 bpy.context.view_layer.update();bpy.ops.file.pack_all();bpy.context.preferences.filepaths.save_version=0
 Path(args[0]).parent.mkdir(parents=True,exist_ok=True);bpy.ops.wm.save_as_mainfile(filepath=str(Path(args[0]).resolve()),compress=True)
 Path(args[1]).write_text(json.dumps(H.R,ensure_ascii=False,indent=2),encoding='utf8');print('V20_BUILD_OK',H.R['counts'],flush=True)
if __name__=='__main__':main()
