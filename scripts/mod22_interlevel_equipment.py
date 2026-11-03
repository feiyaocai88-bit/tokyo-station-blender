"""Chuo east-side equipment connected to the actual lower 3/4 canopy.
Requested visual assembly; positions and service function are not surveyed.
Called by mod22_chuo_roof, with its native mesh/material context already set up.
"""
import bpy,math,numpy as np
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
import v22lib as H
L=H.L

def build(G):
 roof=bpy.data.objects['V10 03-04 differentiated roof skin']
 tree=BVHTree.FromPolygons(H.world(roof),[tuple(p.vertices) for p in roof.data.polygons])
 def height(x,y):
  hit=tree.ray_cast(Vector((x,y,13)),Vector((0,0,-1)),5)[0]
  if hit is None:raise RuntimeError(f'No lower canopy bearing at {x}, {y}')
  return float(hit.z)
 records=[]
 for num,i in enumerate((2,4,6,10,12,16,18,22),1):
  fx=G.FRAMES[i];x=fx+.65;edge=G.outer(x,1);y=edge+.75;foot_y=edge+1.22;unit=f'{num:02d}'
  corners=[(x+dx,foot_y+dy,height(x+dx,foot_y+dy)) for dx,dy in [(-.50,-.52),(.50,-.52),(.50,.52),(-.50,.52)]]
  base=max(p[2] for p in corners);top=base+.18
  mb=L.MeshBuilder();v=[(xx,yy,z-.015) for xx,yy,z in corners]+[(xx,yy,top) for xx,yy,z in corners]
  mb.add(v,[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],H.I['silver'])
  for dx in (-.37,.37):
   for dy in (-.39,.39):H.cyl(mb,(x+dx,foot_y+dy,top+.035),.035,.05,'steel',6)
  curb=H.build(mb,f'interlevel {unit} sloped roof bearing and flashing','Interlevel_Curbs',unit=unit)
  box=L.MeshBuilder();H.box(box,(x,edge+.52,16.40),(.96,.68,1.45),'silver')
  # Lid, recessed access panel, grille blades, hinges and latches remain editable.
  H.box(box,(x,edge+.52,17.145),(1.06,.78,.07),'trim')
  H.box(box,(x,edge+.87,16.38),(.81,.028,1.13),'seam')
  H.box(box,(x,edge+.893,16.18),(.74,.025,.60),'silver')
  for z in np.linspace(16.58,16.92,7):H.box(box,(x,edge+.912,z),(.70,.065,.022),'trim')
  for z in (15.98,16.35):H.box(box,(x-.31,edge+.925,z),(.05,.035,.08),'steel')
  H.tube(box,[(x+.26,edge+.932,16.12),(x+.26,edge+.98,16.12),(x+.26,edge+.98,16.30),(x+.26,edge+.932,16.30)],.014,'trim',8)
  cabinet=H.build(box,f'interlevel {unit} external equipment cabinet','Interlevel_Equipment',unit=unit)
  # One connected rectangular riser with a dog-leg to a real roof-mounted curb.
  path=[(x,y,15.78),(x,y,base+1.05),(x,foot_y,base+.48),(x,foot_y,base+.08)]
  trunk=L.MeshBuilder();H.sweep(trunk,path,.48,.46,'silver')
  for z in np.arange(base+1.4,15.5,1.15):
   for dx in (-.26,.26):H.box(trunk,(x+dx,y,z),(.045,.54,.08),'trim')
   for dy in (-.25,.25):H.box(trunk,(x,y+dy,z),(.56,.045,.08),'trim')
  riser=H.build(trunk,f'interlevel {unit} connected down-riser and collars','Interlevel_Risers',unit=unit)
  bracket=L.MeshBuilder()
  # Two brackets physically join the cabinet and the portal post.
  for z in (15.92,16.90):
   G.beam(bracket,(fx,G.outer(fx,1)-.05,z),(fx,edge+.52,z),.12,.16,'steel')
   G.beam(bracket,(fx,edge+.52,z),(x+.14,edge+.52,z),.12,.16,'steel')
   H.box(bracket,(fx,G.outer(fx,1),z),(.35,.30,.28),'silver')
  # Lower rails and diagonal ties end on the roof bearing; upper ties meet
  # the cabinet support, so the riser is not an unsupported hanging rectangle.
  for dx in (-.38,.38):
   G.beam(bracket,(x+dx,foot_y,top-.06),(x+dx,y,15.94),.07,.09,'steel')
   for z in (base+2.0,base+3.8,15.45):
    G.beam(bracket,(x+dx,y-.10,z),(x,y,z),.06,.07,'steel')
  anchors=H.build(bracket,f'interlevel {unit} portal brackets and lower support rails','Interlevel_Brackets',unit=unit)
  cable=L.MeshBuilder()
  H.tube(cable,[(x+.35,edge+.80,15.90),(x+.35,y+.04,base+1.08),(x+.35,foot_y,top+.02)],.037,'steel',10)
  for z in np.arange(base+1.4,15.8,.9):H.box(cable,(x+.35,y+.04,z),(.11,.15,.035),'trim')
  H.build(cable,f'interlevel {unit} service conduit and clips','Interlevel_Conduits',unit=unit)
  records.append({'id':unit,'x':x,'frame_x':fx,'outer_y':edge,'foot_y':foot_y,'bearing_corners':corners,'curb_top':top,'riser_path':path,'objects':{'curb':curb.name,'cabinet':cabinet.name,'riser':riser.name,'brackets':anchors.name}})
 H.count('interlevel_equipment_connections',len(records));H.R['interlevel_connections']=records
 H.R['interlevel_basis']='User explicitly confirmed east-side equipment boxes and vertical supports connecting the Chuo viaduct to the lower platform canopy. Eight assemblies are fitted to existing roof surfaces; count, positions, dimensions and service function are interpreted, not measured.'
