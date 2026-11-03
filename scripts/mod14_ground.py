"""South approach: brick undercroft, Hato Bus frontage, paving and service detail.
Facade family follows Hato Bus's published Tokyo office photograph. Dimensions,
individual bays, fittings and buses are interpretive, adapted to the inherited piers.
"""
import bpy,math,numpy as np
from mathutils import Matrix,Vector
import v14lib as H

def wall_y(x):return float(H.ty('03',x))-2.75
def frame(x,y=None):
 y=wall_y(x) if y is None else y;a=math.atan2(wall_y(x+.25)-wall_y(x-.25),.5)
 return Matrix.Translation((x,y,0))@Matrix.Rotation(a,4,'Z')
def poly_strip(mb,xs,off0,off1,z,key,thick=.08):
 for a,b in zip(xs[:-1],xs[1:]):
  p=[(a,wall_y(a)+off0,z),(b,wall_y(b)+off0,z),(b,wall_y(b)+off1,z),(a,wall_y(a)+off1,z)]
  mb.add(p+[(x,y,z-thick) for x,y,z in p],[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],H.I[key])

def facade():
 shell=H.L.MeshBuilder();bricks=H.L.MeshBuilder();details=H.L.MeshBuilder();sign=H.L.MeshBuilder();rng=np.random.default_rng(1401)
 # The first bay starts after the original station return. Each arch has actual
 # depth and an inset shop/service facade, rather than an opaque painted arch.
 centers=np.arange(186,241,7.6);records=[]
 for i,x in enumerate(centers):
  F=frame(x);width=7.6;opening=5.4;r=opening/2;spring=1.15;rise=1.70;top=3.44
  def pt(u,v,z):return tuple(F@Vector((u,v,z)))
  for a in [-1,1]:H.box(shell,(a*(r+(width-opening)/4),.28,1.82),((width-opening)/2,.68,3.24),'mortar',F=F)
  # Masonry above a shallow elliptical arch, faceted at 7.5-degree increments.
  for j in range(24):
   t0=j*math.pi/24;t1=(j+1)*math.pi/24;u0,u1=r*math.cos(t0),r*math.cos(t1);z0,z1=spring+rise*math.sin(t0),spring+rise*math.sin(t1)
   vs=[pt(u0,-.06,z0),pt(u1,-.06,z1),pt(u1,-.06,top),pt(u0,-.06,top),pt(u0,.62,z0),pt(u1,.62,z1),pt(u1,.62,top),pt(u0,.62,top)]
   shell.add(vs,[(0,1,2,3),(4,7,6,5),(0,4,5,1),(3,2,6,7)],H.I['mortar'])
  # Real visible brick units and voussoirs at the arch edge.
  for row,z in enumerate(np.arange(.30,top-.06,.105)):
   for u in np.arange(-width/2+.12,width/2,.245):
    u+=.1225*(row%2)
    if u>width/2-.06:continue
    if abs(u)<r+.02 and z < spring+rise*math.sqrt(max(0,1-(min(abs(u)/r,1))**2))+.10:continue
    H.box(bricks,(u,-.075,float(z)),(.231,.08,.092),'brick_'+str(rng.choice(['a','b','c','d'])),F=F)
  for j in range(31):
   t=math.pi*(j+.5)/31;u=r*math.cos(t);z=spring+rise*math.sin(t)
   # Wedge ring, exposed on both front and soffit.
   aa=j*math.pi/31+.005;bb=(j+1)*math.pi/31-.005
   vs=[pt(rr*math.cos(t),v,spring+zz*math.sin(t)) for v in (-.14,.58) for rr,zz,t in [(r,rise,aa),(r,rise,bb),(r+.24,rise+.24,bb),(r+.24,rise+.24,aa)]]
   bricks.add(vs,[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(3,2,6,7)],H.I['brick_b'])
  # Inset bay wall; opening families vary: ticket windows, louvres, shutters.
  H.box(shell,(0,1.05,1.65),(opening, .20,2.90),'soffit',F=F)
  if i in (2,3):
   H.box(details,(0,.86,1.32),(4.72,.08,2.05),'window',F=F)
   for u in np.linspace(-2.38,2.38,5):H.box(details,(float(u),.78,1.32),(.055,.12,2.12),'steel',F=F)
   for z in [.31,1.26,2.35]:H.box(details,(0,.78,z),(4.81,.12,.05),'steel',F=F)
   H.box(details,(0,-.15,2.61),(3.90,.20,.30),'yellow',F=F)
   H.box(details,(0,.11,2.42),(5.25,1.40,.11),'yellow',F=F)
   for z in [.62,1.08]:H.box(details,(0,.70,z),(4.75,.018,.035),'red',F=F)
   H.text(sign,'HATO BUS' if i==2 else 'はとバス 東京営業所',pt(0,-.26,2.61),right=tuple(F.to_3x3()@Vector((1,0,0))),size=.24 if i==2 else .22,key='dark')
   for u in [-1.65,1.10]:
    H.box(details,(u,.69,1.65),(.72,.018,.91),'cream',F=F)
    for zz in np.arange(1.34,1.94,.095):H.box(details,(u,.675,float(zz)),(.55,.008,.015),'dark',F=F)
   for u in [-2.25,-.8,.8,2.25]:
    H.cyl(details,pt(u,-1.0,.65),.026,.90,'steel',12);H.cyl(details,pt(u,-1.0,.215),.16,.055,'steel',16)
   H.rod(details,pt(-2.25,-1,1.08),pt(2.25,-1,1.08),.022,'red',8)
   H.count('ticket_window_bays')
  elif i%3==1:
   H.box(details,(0,.82,1.41),(3.9,.16,2.2),'shutter',F=F)
   for z in np.arange(.36,2.49,.085):H.box(details,(0,.71,float(z)),(3.90,.045,.018),'steel',F=F)
   for u in [-2.02,2.02]:H.box(details,(u,.68,1.41),(.12,.18,2.3),'paint',F=F)
  else:
   H.box(details,(-.95,.78,1.35),(1.05,.10,2.12),'paint',F=F)
   H.box(details,(-.57,.68,1.35),(.03,.08,.18),'steel',F=F)
   H.box(details,(.95,.76,1.42),(1.75,.18,1.28),'dark',F=F)
   for z in np.arange(.86,2.01,.085):H.box(details,(.95,.60,float(z)),(1.65,.16,.035),'shutter',F=F)
  # Drip ledges, rainwater pipes with offsets and clamps, caged luminaires.
  H.box(details,(0,-.20,3.30),(7.56,.45,.14),'pale_stone',F=F)
  u=3.45;H.tube(details,[pt(u,.10,3.47),pt(u,-.28,3.11),pt(u,-.28,.38),pt(u,-.55,.23)],.055,'paint',10)
  for z in [.65,1.80,2.80]:H.box(details,(u,-.13,z),(.19,.32,.045),'steel',F=F)
  H.box(details,(0,-.29,3.04),(1.18,.20,.09),'dark',F=F);H.box(details,(0,-.30,2.98),(1.04,.16,.035),'lamp',F=F)
  records.append({'center_x':float(x),'wall_y':wall_y(x),'opening_m':opening,'z_range':[.2,3.44]})
 # Enclosed undercroft mass/ceiling: a service aisle remains along west frontage.
 poly_strip(shell,np.arange(182,244,2),1.2,151,.195,'floor',.18)
 poly_strip(shell,np.arange(182,244,2),2,151,3.41,'soffit',.12)
 for x in [183,205,232,242]:
  H.box(shell,(x,145,1.76),(.24,125,3.08),'concrete')
 H.build(shell,'south undercroft masonry and enclosure','Ground_Architecture','undercroft')
 H.build(bricks,'south brick arches and individual voussoirs','Ground_Architecture','brick_arches')
 H.build(details,'south bay windows shutters louvers and downpipes','Ground_Detail','frontage_fittings')
 H.build(sign,'Hato Bus ticket office lettering','Ground_Detail','wayfinding')
 H.R['ground']['bays']=records;H.count('brick_arch_bays',len(records))

def streets():
 pave=H.L.MeshBuilder();lines=H.L.MeshBuilder();drains=H.L.MeshBuilder();furn=H.L.MeshBuilder();trees=H.L.MeshBuilder();xs=np.arange(182,254,1.5)
 poly_strip(pave,xs,-8,-.4,.205,'paving',.16)
 poly_strip(pave,xs,-23,-8,.145,'asphalt',.10)
 poly_strip(pave,xs,-25.5,-23,.205,'paving',.16)
 poly_strip(pave,xs,-.45,.45,.215,'paving',.17)
 for off in [-23,-8]:poly_strip(pave,xs,off-.09,off+.09,.285,'pale_stone',.15)
 # Paving slabs and curb joints are genuine shallow geometric grooves.
 for x in np.arange(182.1,252,.65):
  H.beam(lines,(x,wall_y(x)-7.85,.211),(x,wall_y(x)-.50,.211),.012,.008,'mortar')
 for off in np.arange(-7.3,-.5,.65):poly_strip(lines,xs,off-.006,off+.006,.212,'mortar',.008)
 for off in [-22.6,-8.45]:poly_strip(lines,xs,off-.055,off+.055,.152,'white',.009)
 for x in np.arange(184,250,5):poly_strip(lines,[x,x+2.7],-15.5,-15.38,.155,'white',.009)
 # Bus stopping boxes run along, not across, the railway.
 for i,x in enumerate([214,233]):
  for off in [-8.65,-11.65]:poly_strip(lines,[x-6,x+6],off-.06,off+.06,.158,'yellow',.012)
  for xx in [x-6,x+6]:H.beam(lines,(xx,wall_y(xx)-11.65,.16),(xx,wall_y(xx)-8.65,.16),.10,.014,'yellow')
  F=frame(x,wall_y(x)-10.15);H.text(lines,'BUS',tuple(F@Vector((0,0,.16))),right=tuple(F.to_3x3()@Vector((0,1,0))),up=tuple(F.to_3x3()@Vector((-1,0,0))),size=.70,key='white')
 # Open grates with recessed channels, inspection covers and patch seams.
 for x in np.arange(184,251,6):
  F=frame(x);H.box(drains,(0,-7.72,.213),(.90,.38,.025),'dark',F=F)
  for u in np.arange(-.42,.43,.065):H.box(drains,(float(u),-7.72,.234),(.025,.36,.024),'drain',F=F)
  H.count('road_drain_grates')
 for x,off in [(188,-5.8),(203,-5.8),(224,-5.8),(246,-5.8),(197,-18.0),(240,-19.0)]:
  y=wall_y(x)+off;z=.218 if off>-8 else .158;H.cyl(drains,(x,y,z),.32,.025,'drain',32);H.ring(drains,(x,y,z+.018),.28,.012,'steel')
  for dx in [-.16,-.08,0,.08,.16]:H.rod(drains,(x+dx,y-.20,z+.02),(x+dx,y+.20,z+.02),.006,'steel',5)
  H.count('inspection_covers')
 for x in np.arange(184,250,4):
  y=wall_y(x)-7.1;H.cyl(furn,(x,y,.72),.055,1.04,'steel',12);H.cyl(furn,(x,y,.82),.058,.09,'white',12)
  if 207<x<242:continue
  if x+4<250:H.rod(furn,(x,y,.93),(x+4,wall_y(x+4)-7.1,.93),.025,'steel',8)
 # Stop flags, small timetable panels, bins, utility cupboards and street lights.
 for i,x in enumerate([209,228,245]):
  y=wall_y(x)-6.7;H.cyl(furn,(x,y,1.6),.042,2.8,'paint',12);H.box(furn,(x,y-.05,2.8),(.65,.09,.55),'yellow')
  H.text(furn,str(i+1),(x,y-.101,2.82),size=.32,key='dark')
  H.box(furn,(x,y-.09,1.75),(.52,.11,.90),'white');H.box(furn,(x,y-.153,1.75),(.44,.012,.77),'cream')
  for z in np.arange(1.45,2.1,.10):H.box(furn,(x,y-.165,float(z)),(.33,.009,.016),'dark')
 for x in [187,215,248]:
  y=wall_y(x)-24.6;H.cyl(furn,(x,y,3.75),.09,7.08,'paint',16)
  H.tube(furn,[(x,y,6.7),(x,y,7.1),(x,y+1.5,7.4),(x,y+2,7.4)],.07,'paint',12)
  H.box(furn,(x,y+2.0,7.34),(.35,.82,.12),'paint');H.box(furn,(x,y+2.0,7.27),(.25,.60,.025),'lamp')
 for x in [192,237]:
  F=frame(x);H.box(furn,(0,-1.8,.75),(1.2,.55,1.08),'shutter',F=F)
  for u in [-.31,.31]:H.box(furn,(u,-2.09,.75),(.53,.025,.95),'paint',F=F)
  H.box(furn,(0,-1.8,1.32),(1.28,.63,.08),'paint',F=F)
 for x in [184,203,249]:
  y=wall_y(x)-24.8;H.box(trees,(x,y,.24),(1.45,1.4,.06),'soil');H.cyl(trees,(x,y,2.1),.11,3.8,'wood',10)
  import v13lib
  # Its ellipsoid helper uses the shared material list; no V13 setup/mutations.
  for j,(dx,dy,dz) in enumerate([(0,0,0),(.6,.1,-.35),(-.5,.2,-.2),(.1,-.6,-.2)]):v13lib.ellipsoid(trees,(x+dx,y+dy,4.4+dz),(1.0,.95,1.15),'hedge',seed=int(x)+j)
 H.build(pave,'south curved road sidewalk and raised curbs','Ground_Paving','pavement')
 H.build(lines,'south paving joints and bus stop road markings','Ground_Paving','markings')
 H.build(drains,'south grated gullies and inspection covers','Ground_Detail','drainage')
 H.build(furn,'south stop flags railings lights and utility cupboards','Ground_Detail','street_furniture')
 H.build(trees,'south perimeter tree pits','Ground_Detail','trees')

def pier_detail():
 src=bpy.data.objects['V4_Structure_Piers_caps_foundations'];v,inv,lo,hi=H.component_labels(src);b=H.L.MeshBuilder();fixtures=[]
 for a,z in zip(lo,hi):
  c=(a+z)/2
  if not (181<c[0]<244 and 35<c[1]<208 and a[2]>.15 and z[2]>2.5 and z[2]<8 and z[2]-a[2]>1.8 and z[0]-a[0]<3 and z[1]-a[1]<4):continue
  x,y=float(c[0]),float(a[1]-.10);zt=min(3.25,float(z[2]-.2))
  H.box(b,(x,y,.61),(min(float(z[0]-a[0]),1.3),.055,.60),'yellow')
  for dx in [-.4,0,.4]:H.box(b,(x+dx,y-.04,.62),(.12,.025,.59),'dark')
  H.tube(b,[(x,y-.1,.23),(x,y-.1,zt),(x+.35,y-.1,zt)],.033,'paint',10)
  for zz in [.6,1.7,2.7]:
   if zz<zt:H.box(b,(x,y-.02,zz),(.13,.22,.04),'steel')
  H.box(b,(x,y-.07,zt-.22),(.75,.25,.1),'paint');H.box(b,(x,y-.09,zt-.28),(.64,.18,.025),'lamp')
  fixtures.append([x,y,zt]);H.count('piers_with_service_fittings')
 H.build(b,'south pier protectors conduit clamps and soffit lamps','Ground_Detail','pier_fittings')
 H.R['ground']['pier_fixtures']=fixtures

def coach():
 """A parked yellow sightseeing coach gives the stopping bay its street scale."""
 b=H.L.MeshBuilder();x=233.;F=frame(x,wall_y(x)-10.15);F.translation.z=-.055
 def pt(u,v,z):return tuple(F@Vector((u,v,z)))
 # Native shell strips leave the side glazing and wheel openings exposed.
 H.box(b,(0,0,1.02),(11.9,2.42,.18),'yellow',F=F)
 H.box(b,(0,0,1.52),(11.9,2.42,.84),'yellow',F=F)
 H.box(b,(0,0,3.43),(11.85,2.46,.18),'yellow',F=F)
 H.box(b,(0,0,1.11),(11.6,2.25,.10),'floor',F=F)
 for side in [-1,1]:
  yy=side*1.225
  # Lower skirt consists of sections between the wheel wells.
  for a,c in [(-5.9,-4.35),(-3.05,3.55),(4.85,5.9)]:H.box(b,((a+c)/2,yy,.72),(c-a,.08,.45),'yellow',F=F)
  for j,u in enumerate(np.linspace(-5.35,5.20,10)):
   H.box(b,(float(u),yy,2.57),(1.10,.035,1.43),'window',F=F)
   H.box(b,(float(u)+.57,yy,2.57),(.055,.07,1.50),'dark',F=F)
  for z in [1.88,3.32]:H.box(b,(0,yy,z),(11.8,.065,.045),'dark',F=F)
  for u in np.arange(-2.5,3.1,1.40):
   H.box(b,(float(u),side*1.267,1.43),(1.30,.018,.72),'yellow',F=F)
   H.box(b,(float(u),side*1.282,1.60),(.22,.015,.035),'dark',F=F)
  # Side branding, rear engine grilles and mirrors.
  H.text(b,'HATO BUS',pt(-.7,side*1.285,1.47),right=tuple(F.to_3x3()@Vector((-side,0,0))),size=.31,key='dark')
  for z in np.arange(1.15,1.78,.09):H.box(b,(-5.05,side*1.276,float(z)),(1.30,.025,.022),'dark',F=F)
  H.rod(b,pt(5.35,side*1.22,3.12),pt(5.6,side*1.55,3.00),.035,'dark',8)
  H.box(b,(5.6,side*1.55,2.82),(.16,.20,.38),'dark',F=F)
 for u in [-3.7,4.2]:
  for side in [-1,1]:
   H.rod(b,pt(u,side*1.02,.69),pt(u,side*1.30,.69),.49,'rubber',28)
   H.rod(b,pt(u,side*1.305,.69),pt(u,side*1.32,.69),.285,'steel',24)
   H.rod(b,pt(u,side*1.325,.69),pt(u,side*1.35,.69),.11,'dark',16)
   for a in np.linspace(0,math.tau,9)[:-1]:H.rod(b,pt(u+.19*math.cos(a),side*1.33,.69+.19*math.sin(a)),pt(u+.19*math.cos(a),side*1.35,.69+.19*math.sin(a)),.023,'steel',6)
 H.box(b,(5.91,0,2.56),(.04,2.28,1.47),'window',F=F)
 H.box(b,(-5.91,0,2.55),(.04,2.25,1.4),'yellow',F=F)
 for yy in [-.82,.82]:
  H.box(b,(5.96,yy,1.16),(.04,.50,.18),'lamp',F=F)
  H.box(b,(-5.96,yy,1.0),(.04,.30,.13),'red',F=F)
  H.rod(b,pt(5.96,yy*.45,1.90),pt(5.96,yy*.8,2.56),.013,'dark',6)
 H.box(b,(5.98,0,.83),(.035,.40,.20),'green',F=F)
 H.box(b,(5.98,0,1.50),(.035,1.4,.17),'dark',F=F)
 H.box(b,(-1.0,0,3.66),(2.2,1.4,.28),'paint',F=F)
 for xx in np.arange(-1.8,-.1,.13):H.box(b,(float(xx),0,3.81),(.035,1.15,.025),'dark',F=F)
 for u in np.arange(-4.7,3.5,.86):
  for yy in [-.74,.74]:
   H.box(b,(float(u),yy,1.70),(.58,.55,.13),'blue',F=F);H.box(b,(float(u)-.24,yy,2.08),(.12,.55,.76),'blue',F=F)
 H.build(b,'parked yellow sightseeing coach with cabin and wheel wells','Ground_Vehicles','coach')
 H.count('sightseeing_coaches')

def lighting():
 for i,(x,y,zt) in enumerate(H.R['ground']['pier_fixtures']):
  if i%4:continue
  d=bpy.data.lights.new('V14 undercroft LED '+str(i),'AREA');d.energy=65;d.shape='RECTANGLE';d.size=.64;d.size_y=.18;d.color=(.92,.95,1.0)
  o=bpy.data.objects.new(d.name,d);H.col('Ground_Lights').objects.link(o);o.location=(x,y-.10,zt-.34);o['V14_kind']='undercroft_light'
  H.count('undercroft_area_lights')

def run():
 # These two inherited schematic transverse strips ran through the new street.
 # Retain originals hidden and replace their function with the longitudinal walk.
 for name in ['V4 south underbridge walkway -1','V4 south underbridge walkway 1']:H.retire(bpy.data.objects[name])
 facade();streets();pier_detail();coach();lighting()
 H.R['ground']['extent_x_m']=[182,253]
 H.R['ground']['reference']='Hato Bus Tokyo office photograph + GSI seamless orthophoto'
 H.R['ground']['accuracy']='Brick arch/window typology and longitudinal street verified; bay count, furniture, internal service layout and dimensions interpreted to fit the existing model. No transverse public street is asserted here.'
