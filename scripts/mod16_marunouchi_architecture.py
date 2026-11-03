"""Photograph-informed Marunouchi station architecture on the complete V15 scene.

-- output.blend build_report.json source_fingerprint.json
Keep all replaced originals and all unrelated station/train/underground geometry.
"""
import bpy,sys,os,json,math,re,numpy as np
from mathutils import Vector,Matrix
sys.path.insert(0,os.path.dirname(__file__))
import v16lib as H
from mod12_surface_trains import fingerprint
import mod_domes as D
L=H.L
# Inherited wing grids continue behind these projecting towers/gable returns.
# Do not add facade relief to a bay that is completely concealed by masonry.
OCCLUDED_FRIEZE_BAYS={'North outer wing front bay00 floor2 recessed glazing','South long wing last front bay00 floor2 recessed glazing','South long wing last front bay07 floor2 recessed glazing'}

def merge(dst,src,F):
 start=len(dst.v);dst.v.extend(tuple(F@Vector(v)) for v in src.v)
 dst.f.extend([[start+i for i in f] for f in src.f]);dst.mi.extend(src.mi);dst.sm.extend(src.sm);dst.uv.extend(src.uv)

def roof_niche_clearance():
 # Trim the inherited front roof pitch around the deep open niche. Polygon
 # clipping retains original UVs and material indices on the remaining roof.
 o=bpy.data.objects['V4 Architecture central slate roof with Atrium opening'];q=H.copy(o)
 verts=[];faces=[];uvs=[];mats=[];smooth=[];uv=o.data.uv_layers.active
 def clip(poly,axis,value,sign):
  out=[]
  for a,b in zip(poly,poly[1:]+poly[:1]):
   da=(a[0][axis]-value)*sign;db=(b[0][axis]-value)*sign
   if da>=-1e-7:out.append(a)
   if (da>1e-7 and db< -1e-7) or (da< -1e-7 and db>1e-7):
    t=da/(da-db);out.append((a[0].lerp(b[0],t),a[1].lerp(b[1],t)))
  return out
 for p in o.data.polygons:
  poly=[(o.matrix_world@o.data.vertices[o.data.loops[i].vertex_index].co,Vector(uv.data[i].uv) if uv else Vector((0,0))) for i in p.loop_indices]
  left=clip(poly,0,-2.75,-1);remaining=clip(poly,0,-2.75,1)
  right=clip(remaining,0,2.75,1);middle=clip(remaining,0,2.75,-1);back=clip(middle,1,-5.1,1)
  for piece in (left,right,back):
   if len(piece)<3:continue
   start=len(verts);verts.extend(q.matrix_world.inverted()@a for a,b in piece);faces.append(tuple(range(start,len(verts))));uvs.extend(b for a,b in piece);mats.append(p.material_index);smooth.append(p.use_smooth)
 me=bpy.data.meshes.new('V16 roof pitch trimmed behind central niche');me.from_pydata(verts,[],faces)
 for m in o.data.materials:me.materials.append(m)
 layer=me.uv_layers.new(name='UVMap')
 for i,co in enumerate(uvs):layer.data[i].uv=co
 for p,mi,sm in zip(me.polygons,mats,smooth):p.material_index=mi;p.use_smooth=sm
 q.data=me;me.update();H.count('central_roof_niche_clearance')

def central():
 prefixes=('Central high arch side pier','Central cross-storey arch','Central narrow curved pediment',
  'Central arch pilaster','Central arch capital','V3 Central projecting pilaster block','V3 Central stone pilaster foot',
  'V3 Central lower window curved crown','V3 Central inset window heavy sill',
  'Central roof oval dormer','Central roof ridge','Central roof crest finial','Central flanking turret roof','Central flanking finial')
 for o in H.ACTIVE:
  if o.hide_render:continue
  n=o.name
  small_circle=False
  if n.startswith(('Central','V3 central')) and o.type in ['MESH','CURVE']:
   lo,hi=H.bounds(o);small_circle=lo[0]>-1.1 and hi[0]<1.1 and lo[1]<-7 and lo[2]>22 and hi[2]<24.6
  tower_roof=n.startswith(('Central flanking tower -1','Central flanking tower 1')) and any(t in n for t in ['slate roof','rooflight'])
  if n.startswith(prefixes) or small_circle or tower_roof:H.retire(o)
  elif n.startswith('V3 Central recessed'):
   q=H.copy(o);q.location.y+=1.15
   for i,m in enumerate(q.data.materials):
    if m and 'patinated bronze frames' in m.name:q.data.materials[i]=H.M[H.I['sash']]
   H.count('central_recess_source_parts_set_back')
 # The combined finer sash object contains other windows: move only central
 # niche components, retaining the original merged mesh for restoration.
 o=bpy.data.objects.get('V3 central finer sash subdivisions')
 if o and not o.hide_render:
  q=H.copy(o);v=H.world(q);mask=(abs(v[:,0])<1.55)&(v[:,1]>-7.9)&(v[:,1]<-5.8)&(v[:,2]>7.5)&(v[:,2]<19.5)
  inv=q.matrix_world.inverted()
  for i in np.flatnonzero(mask):q.data.vertices[int(i)].co=inv@Vector((v[i,0],v[i,1]+1.15,v[i,2]))
  for i,m in enumerate(q.data.materials):
   if m and 'bronze' in m.name:q.data.materials[i]=H.M[H.I['sash']]
  q.data.update()
 body=L.MeshBuilder();detail=L.MeshBuilder()
 roof_niche_clearance()
 # New broad banded piers, with real 3.2 m deep returns to the existing inset wall.
 for side in (-1,1):
  H.box(body,(side*4.35,-7.0,11.05),(3.30,3.2,22.10),'brick')
  for z in [8.1,11.8,15.1,18.4,21.55]:H.box(detail,(side*4.35,-8.68,z),(3.38,.20,.24),'stone_light')
  for a,b in [(8.35,11.58),(12.02,14.86),(15.34,18.16),(18.64,21.30)]:
   H.box(detail,(side*4.35,-8.79,(a+b)/2),(1.08,.27,b-a),'stone')
  for z,w,d,h,key in [(21.96,3.56,1.0,.22,'stone'),(22.2,3.85,1.30,.25,'copper_dark'),(22.46,4.10,1.48,.18,'copper'),(22.60,4.22,1.55,.08,'copper_dark')]:
   H.box(detail,(side*4.35,-8.56,z),(w,d,h),key)
  H.rosette(detail,side*4.35,-8.99,21.05,.36,'patina')
  for xx in (side*4.35-.55,side*4.35+.55):H.capital(detail,xx,-8.81,21.34,.42)
  # Close the widened recess back to the original 4 m inset wall; no slivers
  # through to the trains behind the building.
  H.box(body,(side*2.37,-5.59,14.60),(.76,.72,13.60),'brick')
  H.box(detail,(side*2.69,-7.12,13.48),(.055,2.96,11.35),'stone')
 H.box(detail,(0,-7.10,7.77),(5.43,3.0,.18),'stone')
 # Spandrel between the deep niche arch and raised round pediment. Split strips
 # around the roundel so the window is a physical opening, not a pasted disc.
 xs=sorted(set(np.linspace(-4.2,4.2,141).tolist()+[-.64,.64]))
 def top(x):return 22.0+math.sqrt(max(0,4.2**2-x*x))
 def bottom(x):return 19.1+math.sqrt(max(0,1-(x/2.70)**2)) if abs(x)<2.70 else 22.0
 zc=23.25;rad=.64
 for a,b in zip(xs[:-1],xs[1:]):
  za,zb=bottom(a),bottom(b);ta,tb=top(a),top(b)
  if abs((a+b)/2)<rad:
   ha=math.sqrt(max(0,rad*rad-a*a));hb=math.sqrt(max(0,rad*rad-b*b))
   for lowa,lowb,hia,hib in [(za,zb,zc-ha,zc-hb),(zc+ha,zc+hb,ta,tb)]:H.extrude(body,[(a,lowa),(b,lowb),(b,hib),(a,hia)],-8.6,-5.85,'brick')
  elif ta>=za-.01 and tb>=zb-.01:H.extrude(body,[(a,za),(b,zb),(b,tb),(a,ta)],-8.6,-5.85,'brick')
 # Upper niche arch, voussoirs and a thick weathered-metal outer cornice.
 # Shallow segmental inner arch visible in the official close frontal photo.
 def niche_arch(a,b,y0,y1,key):
  H.extrude(detail,[(2.70*math.cos(a),19.1+math.sin(a)),(3.08*math.cos(a),19.1+1.36*math.sin(a)),(3.08*math.cos(b),19.1+1.36*math.sin(b)),(2.70*math.cos(b),19.1+math.sin(b))],y0,y1,key)
 for a,b in zip(np.linspace(0,math.pi,61)[:-1],np.linspace(0,math.pi,61)[1:]):niche_arch(a,b,-8.83,-5.85,'stone')
 for i in range(13):
  a=i*math.pi/13+.011;b=(i+1)*math.pi/13-.011
  for aa,bb in zip(np.linspace(a,b,6)[:-1],np.linspace(a,b,6)[1:]):niche_arch(aa,bb,-8.90,-8.79,'stone_light')
 for r0,r1,y0,y1,key in [(4.12,4.30,-9.03,-8.30,'copper_dark'),(4.30,4.50,-9.18,-8.12,'copper'),(4.49,4.58,-9.29,-8.0,'copper_dark'),(4.03,4.12,-8.95,-8.50,'copper')]:H.arc(detail,(0,22.0),r0,r1,y0,y1,key)
 for a in np.linspace(.16,math.pi-.16,19):
  H.rosette(detail,4.36*math.cos(a),-9.24,22+4.36*math.sin(a),.065,'copper_dark')
 H.arc(detail,(0,zc),.64,.85,-8.85,-8.53,'stone_light',0,math.tau,64)
 H.arc(detail,(0,zc),.53,.64,-8.88,-8.35,'copper_dark',0,math.tau,64)
 H.lathe(detail,[(.53,0),(.53,.035)],(0,0),'glass',48,H.frame(0,-8.35,zc))
 H.box(detail,(0,-8.48,zc),(.025,.04,1.04),'sash');H.box(detail,(0,-8.48,zc),(1.04,.04,.025),'sash')
 for a in np.linspace(0,math.tau,9)[:-1]:
  H.box(detail,(.99*math.cos(a),-8.68,zc+.99*math.sin(a)),(.14,.20,.14),'stone_light')
 H.rosette(detail,0,-9.0,26.88,.24,'copper_dark')
 H.lathe(detail,[(.18,26.94),(.14,27.15),(.22,27.25),(.06,27.48),(.01,27.65)],(0,-8.70),'copper',20)
 H.build(body,'Central deep arch masonry and open roundel','Central',role='niche_masonry')
 H.build(detail,'Central layered pediment banded piers voussoirs and roundel','Central',role='pediment_detail')
 # The photographed white attic turrets have flat, projecting cornices.
 for side in (-1,1):
  mb=L.MeshBuilder();x=side*18
  for z,w,d,h,key in [(20.72,6.25,16.0,.16,'stone'),(20.91,6.62,16.35,.22,'copper_dark'),(21.10,6.86,16.58,.16,'copper'),(21.20,7.00,16.70,.055,'copper_dark')]:H.box(mb,(x,-1.6,z),(w,d,h),key)
  for xx in np.linspace(x-2.6,x+2.6,7):H.box(mb,(xx,-9.79,20.53),(.21,.45,.22),'stone_light')
  for xx in (x-2.1,x-1.3,x-.4,x+.4,x+1.3,x+2.1):H.capital(mb,xx,-9.73,20.24,.40)
  H.tube(mb,[(x,-5.3,21.24),(x,-5.3,23.1)],.025,'iron')
  H.build(mb,('North' if side<0 else 'South')+' central turret flat cornice and brackets','Central',role='flat_turret')
 H.count('flat_attic_turrets',2)
 # Two genuine round attic roof dormers; remove the former rectangular boxes.
 for x in (-7.2,7.2):
  mb=L.MeshBuilder();F=H.frame(x,-5.75,23.12)
  L.lathe(mb,[(.68,-.8),(.68,.0),(.81,.04),(.83,.15),(.65,.22),(.55,.20)],(0,0),48,H.I['copper'],frame=F)
  H.lathe(mb,[(.55,-.03),(.55,0)],(0,0),'glass',40,F)
  H.box(mb,(x,-5.82,23.12),(.035,.06,1.08),'sash');H.box(mb,(x,-5.82,23.12),(1.08,.06,.035),'sash')
  for side in (-1,1):H.scroll(mb,x+side*.78,-5.91,22.68,.20,'copper',side)
  H.arc(mb,(x,23.12),.83,.94,-5.99,-5.60,'copper_dark',0,math.pi,40)
  H.build(mb,f'Central round roof dormer {x:+.1f}','Roof_Detail')
 H.count('central_round_roof_dormers',2)
 # Turned balusters in place of the wire-thin source railing.
 mb=L.MeshBuilder()
 for y in (-1.5,3.5):
  for x in np.linspace(-7.3,7.3,31):
   H.lathe(mb,[(.105,26.40),(.105,26.50),(.055,26.58),(.14,26.83),(.09,27.05),(.055,27.23),(.10,27.31),(.10,27.39)],(x,y),'copper_dark',12)
  H.box(mb,(0,y,26.39),(15.0,.32,.13),'copper');H.box(mb,(0,y,27.43),(15.1,.36,.14),'copper')
 for x in (-7.4,7.4):
  H.box(mb,(x,1,27.43),(.36,5.1,.14),'copper')
  for y in np.linspace(-1.2,3.2,9):H.lathe(mb,[(.09,26.45),(.06,26.58),(.12,26.86),(.06,27.19),(.09,27.38)],(x,y),'copper_dark',12)
 H.build(mb,'Central ridge turned balustrade with continuous caps','Roof_Detail');H.count('central_ridge_balusters',80)

def domes():
 for tag,cx in [('NORTH',-104.),('SOUTH',107.)]:
  for o in H.ACTIVE:
   if o.hide_render:continue
   n=o.name
   if n.startswith(tag+' dome clock gable') or n.startswith('V3 '+tag+' clock gable radial') or n.startswith(tag+' dome gable stone pilaster') or n.startswith('V3 '+tag+' dome balcony baluster') or n.startswith('V3 '+tag+' dome balcony top rail') or n.startswith('V3 '+tag+' dome balcony pier'):H.retire(o)
   elif n.startswith(tag+' dome grouped drum'):
    if any(s in n for s in ['base','lintel','pier']) and 'window' not in n:
     key='brick' if 'pier' in n else 'copper';H.recolor(o,{m.name:key for m in o.data.materials if m})
    elif any(s in n for s in ['deep jamb','outer frame','projecting sill','stone lintel']):H.recolor(o,{m.name:'copper' for m in o.data.materials if m})
  body=L.MeshBuilder();mb=L.MeshBuilder();zc=20.70
  poly=[(cx-3.65,16.0),(cx+3.65,16.0)]+[(cx+3.65*math.cos(a),zc+3.65*math.sin(a)) for a in np.linspace(0,math.pi,65)]
  H.extrude(body,poly,-13.29,-11.25,'brick')
  H.build(body,tag+' raised clock-gable masonry','Dome_Detail',role='clock_gable',new_hood_apex=25.15)
  # A deep metal archivolt projects in front of the masonry and returns into the
  # lower roof. Several separate profiles create the shadow bands seen in photos.
  for r0,r1,y0,y1,key in [(3.62,3.78,-13.75,-11.25,'copper_dark'),(3.78,4.10,-14.0,-10.90,'copper'),(4.10,4.27,-14.18,-10.70,'copper_dark'),(4.27,4.40,-14.28,-10.65,'copper'),(4.40,4.45,-14.35,-10.60,'copper_dark')]:H.arc(mb,(cx,zc),r0,r1,y0,y1,key)
  for i in range(13):
   a=i*math.pi/13+.018;b=(i+1)*math.pi/13-.018
   H.arc(mb,(cx,zc),3.12,3.64,-13.43,-12.95,'stone_light',a,b,5)
  for a in np.linspace(.12,math.pi-.12,21):H.rosette(mb,cx+3.94*math.cos(a),-14.06,zc+3.94*math.sin(a),.075,'copper_dark')
  for s in (-1,1):
   H.box(mb,(cx+s*3.91,-12.6,18.4),(.58,1.4,4.6),'brick')
   for z in (16.5,18.1,19.7,20.7):H.box(mb,(cx+s*3.92,-13.37,z),(.66,.23,.22),'stone_light')
   H.box(mb,(cx+s*4.35,-12.9,20.63),(1.4,2.1,.25),'copper')
   H.scroll(mb,cx+s*4.22,-14.02,20.45,.26,'copper',s)
  # Octagonal drum cornices and corner pilasters, preserving all window openings.
  cy=.415;co=math.cos(math.pi/8)
  for profile in [[(9.04,26.10),(9.20,26.20),(9.24,26.36),(9.60,26.50),(9.70,26.63),(9.70,26.72)],[(9.03,22.60),(9.20,22.68),(9.20,22.82),(9.03,22.92)]]:
   L.lathe(mb,[(r/co,z) for r,z in profile],(cx,cy),8,H.I['copper'],phase=math.pi/8,cap_top=False,cap_bottom=False,smooth=False)
  for a in np.linspace(0,math.tau,9)[:-1]+math.pi/8:
   x,y=cx+9.10/co*math.cos(a),cy+9.10/co*math.sin(a)
   F=Matrix.Translation((x,y,0))@Matrix.Rotation(a-math.pi/2,4,'Z')
   H.box(mb,(0,0,24.60),(.28,.22,3.02),'copper',F)
   H.box(mb,(0,0,26.13),(.45,.35,.20),'copper_dark',F)
  H.build(mb,tag+' deep layered clock archivolt voussoirs and drum cornices','Dome_Detail',role='clock_archivolt')
  # Fine ornamental balcony metalwork replaces the opaque white picket fence.
  mb=L.MeshBuilder();y=-13.36
  for z in (11.88,12.45,12.56):H.box(mb,(cx,y,z),(5.65,.07,.045),'iron')
  for x in np.linspace(cx-2.72,cx+2.72,17):
   H.tube(mb,[(x,y,11.88),(x,y,12.56)],.017,'iron',6)
  for x in np.linspace(cx-2.55,cx+2.55,12):
   H.scroll(mb,x-.10,y,12.18,.13,'iron');H.scroll(mb,x+.10,y,12.18,.13,'iron',-1)
  H.build(mb,tag+' fine iron balcony scrollwork','Dome_Detail')
  # Tall engaged round stone ornaments on the two front outer octagonal
  # corners are prominent in the contractor's front/oblique photographs.
  mb=L.MeshBuilder()
  for side in (-1,1):
   x,y=cx+side*12.48,-5.25
   H.lathe(mb,[(.10,8.55),(.38,8.85),(.56,9.20),(.64,9.70),(.64,19.73),(.73,19.80),(.73,20.05),(.66,20.16)],(x,y),'stone_light',40)
   H.lathe(mb,[(.69,20.12),(.82,20.23),(.82,20.37),(.69,20.44),(.66,20.71),(.51,21.01),(.20,21.21),(.07,21.29)],(x,y),'copper',40)
   H.lathe(mb,[(.13,21.27),(.13,21.40),(.045,21.48),(.045,22.92),(.025,23.14)],(x,y),'copper_dark',16)
   for z in (12.5,15.5,18.5):H.lathe(mb,[(.647,z-.014),(.647,z+.014)],(x,y),'stone',40)
  H.build(mb,tag+' front corner round stone ornaments with copper caps','Dome_Detail')
  H.count('engaged_round_corner_ornaments',2)
  # Round dormer copper housings, paired scrolls and leaf crowns on all 8 facets.
  deco=L.MeshBuilder()
  for k in range(8):
   one=L.MeshBuilder();th=k*math.pi/4;F=D.face_frame(cx,cy,th,D.apothem_at(29.15)+.30,29.15)@Matrix.Rotation(-math.pi/2,4,'X')
   for side in (-1,1):
    H.scroll(one,side*.92,-.16,-.36,.22,'copper',side)
    H.tube(one,[(side*.80,-.10,-.75),(side*1.12,-.12,-.47),(side*.95,-.10,.10)],.06,'copper')
   H.arc(one,(0,0),.91,1.01,-.20,.0,'copper_dark',.12,math.pi-.12,40)
   H.rosette(one,0,-.20,1.08,.15,'copper')
   H.lathe(one,[(.10,1.18),(.16,1.29),(.06,1.43),(.015,1.58)],(0,-.05),'copper_dark',16)
   H.box(one,(0,-.05,-.84),(1.05,.32,.14),'copper')
   merge(deco,one,F)
  H.build(deco,tag+' eight dormer scrolls leaf crowns and base flashings','Roof_Detail')
  H.count('ornamented_dome_dormers',8);H.count('rebuilt_clock_archivolts')

def frieze_unit(mb,lo,hi):
 x=float((lo[0]+hi[0])/2);y=float(lo[1])-.68;z=16.645
 # Fit the complete roundel inside the 16.55--16.74 m clear frieze band.
 # A shallow backing connects the relief to the wall, behind the ring.
 H.lathe(mb,[(.082,-.25),(.082,-.015)],(0,0),'stone',24,H.frame(x,y,z))
 H.ring(mb,(x,y,z),.065,.012,'stone_light',32)
 for dx in (-float(hi[0]-lo[0])*.56,float(hi[0]-lo[0])*.56):
  H.scroll(mb,x+dx,y,float(hi[2])+.17,.105,'stone_light',1 if dx>0 else -1)

def facade_details():
 mb=L.MeshBuilder();frieze=L.MeshBuilder()
 for o in H.ACTIVE:
  if o.hide_render or o.type not in ['MESH','CURVE']:continue
  n=o.name;arch=any(c.name.startswith(('V3 01','V3 02','V3 03','V4_Architecture','V5_Architecture_DomeRoofs')) for c in H.LINKS.get(n,[]))
  if not arch:continue
  lo,hi=H.bounds(o);c=(lo+hi)/2
  # Period painted sashes. The large merged subdivision meshes are included so
  # the fine glazing bars change together with their separate primary mullions.
  mapping={}
  for material in o.data.materials:
   if material is None:continue
   mn=material.name
   if mn=='V2 | patinated bronze frames' and any(t in n.lower() for t in ['mullion','transom','sash','window bars','dormer']):mapping[mn]='sash'
   elif mn in ['V2 | aged copper flashing','V4 Architecture | copper ribbon and flashing','V5 | weathered copper sheet']:
    mapping[mn]='copper'
  if mapping:H.recolor(o,mapping);H.count('architecture_material_copies')
  if 'front carved capital' in n:
   H.capital(mb,float(c[0]),float(lo[1])-.035,float(c[2]),max(.54,float(hi[0]-lo[0])*1.25));H.count('detailed_pilaster_capitals')
  if 'front bay' in n and 'floor2 recessed glazing' in n and n not in OCCLUDED_FRIEZE_BAYS:
   frieze_unit(frieze,lo,hi)
   H.count('third_floor_frieze_panels')
  if 'front bay' in n and 'floor1 triangular window crown' in n:
   x=float(c[0]);y=float(lo[1])-.025;z=float(hi[2])
   H.tube(mb,[(float(lo[0]),y,float(lo[2])+.025),(x,y,z+.035),(float(hi[0]),y,float(lo[2])+.025)],.045,'stone_light')
   H.rosette(mb,x,y-.03,z-.17,.11,'stone');H.count('second_floor_pediment_details')
 H.build(mb,'Facade carved capitals volutes and pediment mouldings','Facade_Detail')
 H.build(frieze,'Third floor frieze medallions and window scroll brackets','Facade_Detail')

def cameras():
 sc=bpy.data.scenes['Tokyo Station']
 specs=[('01 Central front',(0,-95,25),(0,-4,13),53),('02 South dome',(119,-88,29),(107,-1,21),58),
        ('03 North wing detail',(-58,-65,14),(-58,-5,10),31),('04 North dome',(-117,-88,29),(-104,-1,21),58),
        ('05 Whole Marunouchi',(20,-330,135),(5,0,14),350),('06 Roof details',(133,-47,52),(107,0,27),35),
        ('07 Central pedestrian view',(0,-80,3),(0,-5,13.5),46),('08 South dome pedestrian view',(107,-100,5),(107,0,23),55)]
 for name,pos,target,scale in specs:
  data=bpy.data.cameras.new('V16 '+name);data.type='ORTHO';data.ortho_scale=scale;data.clip_start=.05;data.clip_end=2500
  if name.startswith(('07','08')):
   # Ground-level orthographic rays start below the plaza in the lower frame;
   # a real perspective eye keeps the underground cutaway out of this view.
   data.type='PERSP';data.sensor_fit='HORIZONTAL';data.sensor_width=36;data.lens=(Vector(target)-Vector(pos)).length*36/scale
  cam=bpy.data.objects.new(data.name,data);H.col('Review_Cameras').objects.link(cam);cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam['V16_review']=True
 sc.camera=bpy.data.objects['V16 01 Central front'];sc.render.resolution_x=1440;sc.render.resolution_y=1100;sc.render.resolution_percentage=100
 for screen in bpy.data.screens:
  for area in screen.areas:
   if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'

def main():
 args=sys.argv[sys.argv.index('--')+1:];sc=bpy.data.scenes['Tokyo Station'];bpy.context.window.scene=sc
 if sc.get('V16_refinement'):raise RuntimeError('Start from the final V15 input')
 json.dump(H.snapshot(),open(args[2],'w'),separators=(',',':'))
 H.setup();central();print('V16_CENTRAL_DONE',flush=True);domes();print('V16_DOMES_DONE',flush=True);facade_details();print('V16_FACADE_DONE',flush=True);cameras()
 H.R['reference']='Kajima restoration completion exterior album images 01,02,04,06,08,09,13; Tokyo Station City external-wall details; JRE Design project description.'
 H.R['limitations']=['Photographic interpretation fitted to inherited station footprint and floor heights, not measured facade reconstruction.','Fine carving and sheet-metal profiles are simplified native geometry.','The aerial reference predates the present plaza; no obsolete plaza arrangement is copied.','V15 underground cutaways, V14 ground/catenary and all rolling stock remain.']
 H.R['changes']=['Raised and deepened central pediment and niche; widened banded piers; opened roundel.','Flat projecting cornices replace central attic turret hip roofs.','Two round central attic dormers and turned ridge balustrades.','Deep layered clock archivolts, brick-coloured octagonal drums and copper cornices.','Sixteen dormer scroll/crown assemblies and two fine iron balconies.','Painted sashes, carved pilaster capitals, frieze medallions and pediment details.']
 sc['V16_refinement']=json.dumps(H.R,ensure_ascii=False);sc['last_stage']='V16 Marunouchi photographic architecture refinement, 2026-11-03'
 p=os.path.join(os.path.dirname(__file__),'..','README_V16.txt')
 if os.path.isfile(p):tx=bpy.data.texts.new('README_V16_中文');tx.write(open(p,encoding='utf8').read())
 bpy.context.view_layer.update();bpy.ops.file.pack_all();bpy.context.preferences.filepaths.save_version=0
 os.makedirs(os.path.dirname(os.path.abspath(args[0])),exist_ok=True);bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args[0]),compress=True)
 json.dump(H.R,open(args[1],'w',encoding='utf8'),ensure_ascii=False,indent=2);print('V16_BUILD_OK',H.R['counts'],flush=True)

if __name__=='__main__':main()
