"""V21 all existing platform groups, from Street View and dated primary photographs.
Run once on the published V20 scene. -- output.blend build.json baseline.json
Photographic forms with estimated dimensions/positions, not a measured survey.
"""
import bpy,sys,math,json,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
sys.path.insert(0,str(Path(__file__).parent))
import v21lib as H
L=H.L
SC=None;P={};MASTS=[];STAIRS=[];ACTIVE=[];OCC=None
STYLES={'01-02':'Chuo slatted soffit and silver oval column covers','03-04':'haunched exposed steel, mixed old and clad columns','05-06':'barrel daylight strip and exposed purlins','07-08':'shallow pitched metal roof, paired channel supports','09-10':'transmitting PV roof, riveted portal beams','14-15':'narrow pitched Tokaido canopy and H columns','16-17':'wide pitched Tokaido canopy and H columns','18-19':'pitched Tokaido canopy, paired steel supports','20-21':'open central ridge with panelled side soffits','22-23':'raised central bay, stepped side soffits and local PV'}
def active_objects():
 hidden=set()
 def walk(c,h=False):
  h=h or c.hide_render
  if h:hidden.update(o.name for o in c.objects)
  for q in c.children:walk(q,h)
 walk(SC.collection)
 return [o for o in SC.objects if not o.hide_render and o.name not in hidden]
def retire_name(n):
 o=bpy.data.objects.get(n)
 if o and not o.hide_render:H.retire(o)
def free_stair(isl,x,y,pad=.4):
 for s in STAIRS:
  if s['island']!=isl:continue
  q=np.array([x,y])-s['c'];u=np.array(s['u']);v=np.array([-u[1],u[0]])
  if s['u0']-pad<q@u<s['u1']+pad and abs(q@v)<s['hv']+pad:return False
 return True
class Profile:
 def __init__(self,isl):
  self.isl=isl;self.shin=int(isl[:2])>=14;self.deck=bpy.data.objects[f'V3 Platform {isl} raised deck'];lo,hi=H.bounds(self.deck);self.z=float(hi[2]);self.floor=H.bvh(self.deck)
  old=json.loads(SC['V10_platform_context'])['roofs'][isl];self.x0,self.x1=old['sections'][0]
  if self.shin:self.x0=max(self.x0,float(lo[0])+.5);self.x1=min(self.x1,float(hi[0])-.5)
  self.eave=self.z+(5.35 if self.shin else 4.24)
  a,b=isl.split('-');self.a=a;self.b=b
  if not self.shin:
   src=bpy.data.objects[f'V8 canopy {isl} | roof deck and skylight'];w=H.world(src);q=w[abs(w[:,2]-old['eave_z'])<.002];self.xs=np.unique(np.round(q[:,0],4));self.w=[];self.e=[]
   for x in self.xs:
    t=q[abs(q[:,0]-x)<.002];self.w.append(float(t[:,1].min()));self.e.append(float(t[:,1].max()))
 def edges(self,x):
  if self.shin:return H.ty(self.a,x)+.95,H.ty(self.b,x)-.95
  return float(np.interp(x,self.xs,self.w)),float(np.interp(x,self.xs,self.e))
 def zroof(self,x,f):
  if self.isl=='05-06':
   u=(f-.5)/.27;return self.eave+.12+(.80*math.sqrt(max(0,1-u*u)) if abs(u)<1 else .05)
  if self.isl=='07-08':return self.eave+.05+.26*(1-abs(2*f-1))
  if self.isl=='09-10':return self.eave+.08+.76*(1-abs(2*f-1))
  if self.isl in ('20-21','22-23'):
   h=.26 if self.isl=='20-21' else .30
   return self.eave+.12+(.76 if abs(f-.5)<h else .13)*(1-abs(2*f-1))
  return self.eave+.06+(.48 if self.isl=='03-04' else .68)*(1-abs(2*f-1))
 def point(self,x,f,dz=0):
  a,b=self.edges(x);return (x,a+(b-a)*f,self.zroof(x,f)+dz)
 def holes(self,x):return [(y,.46) for mx,y,z0,z1 in MASTS if abs(x-mx)<.46 and z0<self.eave+.9 and z1>self.eave-.1]
 def floor_hit(self,x,y):return self.floor.ray_cast(Vector((x,y,self.z+.1)),Vector((0,0,-1)),.15)[0] is not None
def shell(mb,ps,k,th=.045):
 n=len(ps);v=ps+[(x,y,z-th) for x,y,z in ps];mb.add(v,[tuple(range(n)),tuple(range(2*n-1,n-1,-1))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],H.I[k])
def skins(p):
 isl=p.isl
 if isl in ('01-02','03-04'):return
 for o in list(ACTIVE):
  if o.get('island')==isl and o.get('V10_kind') in ('roof_skin','roof_detail','roof_penetration','roof_pv'):H.retire(o)
  elif isl=='05-06' and o.name.startswith('V11 05-06') and ('roof' in o.name or 'barrel' in o.name):H.retire(o)
 mb=L.MeshBuilder();detail=L.MeshBuilder();xs=sorted(set([p.x0,p.x1]+list(np.arange(p.x0,p.x1,1.6))+[max(p.x0,min(p.x1,x+s*.46)) for x,y,z0,z1 in MASTS for s in (-1,1) if p.x0<x<p.x1]))
 for a,b in zip(xs[:-1],xs[1:]):
  if b-a<1e-6:continue
  xm=(a+b)/2;w,e=p.edges(xm);holes=p.holes(xm);fs=[0,.5,1]
  if isl=='05-06':fs=sorted(set([0,.23,.77,1]+[.5+.27*math.cos(t) for t in np.linspace(0,math.pi,15)]))
  if isl=='09-10':fs=list(np.linspace(0,1,9))
  if isl in ('20-21','22-23'):fs=[0,.20,.24,.5,.76,.80,1]
  fs=sorted(set(fs+[max(0,min(1,(y+s*r-w)/(e-w))) for y,r in holes for s in (-1,1)]))
  for c,d in zip(fs[:-1],fs[1:]):
   if d-c<1e-6 or any(abs(w+(e-w)*(c+d)/2-y)<r+.001 for y,r in holes):continue
   key='white' if p.shin else 'cream';f=(c+d)/2
   if isl=='05-06':key='glazing' if .27<f<.73 else 'cream'
   if isl=='09-10':key='glazing'
   shell(mb,[p.point(a,c),p.point(b,c),p.point(b,d),p.point(a,d)],key)
   if isl=='09-10' and b-a>.35:
    # Cell fields leave real transmitting borders; no opaque base slab behind them.
    aa=a+.10;bb=b-.10;cc=c+.012;dd=d-.012
    if dd>cc:shell(detail,[p.point(aa,cc,.012),p.point(bb,cc,.012),p.point(bb,dd,.012),p.point(aa,dd,.012)],'dark',.016)
   if b-a>.7:
    H.beam(detail,p.point(a,c,.027),p.point(a,d,.027),.035,.035,'silver',section=False)
 for x,y,z0,z1 in MASTS:
  w,e=p.edges(x)
  if not(p.x0<x<p.x1 and w<y<e and z0<p.eave<z1):continue
  z=p.zroof(x,(y-w)/(e-w))
  for s in (-1,1):H.box(detail,(x+s*.49,y,z+.04),(.06,1.04,.10),'silver');H.box(detail,(x,y+s*.49,z+.04),(1.04,.06,.10),'silver')
  H.count('flashed_roof_openings')
 if isl=='22-23':
  for x in np.arange(-160,-110,2):
   for c,d in ((.27,.43),(.57,.73)):
    if p.holes(x+1):continue
    shell(detail,[p.point(x,c,.16),p.point(x+1.8,c,.16),p.point(x+1.8,d,.16),p.point(x,d,.16)],'dark',.06)
 H.build(mb,isl+' photo-profile roof with real glazing and mast openings','Roof_Skins',isl);H.build(detail,isl+' roof seams glazing frames and local PV','Roof_Details',isl)
 H.R['platforms'][isl]['roof_rebuilt']=True
def old_column_positions(isl):
 if int(isl[:2])>=14:return json.loads(SC['V5_shinkansen_roofs'])[isl]['columns']
 o=bpy.data.objects[f'V8 canopy {isl} | columns'];v,lab,lo,hi=H.component_labels(o)
 return [list((a[:2]+b[:2])/2) for a,b in zip(lo,hi) if b[2]-a[2]>2.5 and .40<b[0]-a[0]<.7 and .4<b[1]-a[1]<.7]
def guard(mb,F,z,width=.45):
 for s in (-1,1):
  H.box(mb,(0,s*(width/2+.018),z),(width,.025,.42),'red',F)
  # Short diagonal white strips are clipped to the panel edges.
  for b in np.arange(-width/2-.42,width/2,.16):
   poly=[(b,-.21),(b+.07,-.21),(b+.49,.21),(b+.42,.21)]
   for edge,greater in [(-width/2,True),(width/2,False)]:
    out=[]
    for a,c in zip(poly,poly[1:]+poly[:1]):
     ai=a[0]>=edge if greater else a[0]<=edge;ci=c[0]>=edge if greater else c[0]<=edge
     if ai:out.append(a)
     if ai!=ci:
      t=(edge-a[0])/(c[0]-a[0]);out.append((edge,a[1]+t*(c[1]-a[1])))
    poly=out
   if len(poly)>2:mb.add([tuple(F@Vector((x,s*(width/2+.035),z+y))) for x,y in poly],[tuple(range(len(poly)))],H.I['white'])
def columns(p):
 isl=p.isl;mb=L.MeshBuilder();ps=[]
 if isl in ('05-06','07-08','09-10'):
  ps=old_column_positions(isl)
  if isl=='09-10':ps=[(x,y+d) for x,y in ps for d in ((-.85,.85) if all(free_stair(isl,x,y+s*.85,.25) for s in (-1,1)) else (0,))]
  return ps
 if isl=='01-02':
  # Lower silver covers belong to Chuo; the existing V20 roof supports remain.
  for x,y in old_column_positions(isl):
   F=H.frame(isl,x,p.z,y)
   H.cyl(mb,(0,0,1.45),.35,2.9,'silver',24,F)
   for s in (-1,1):H.box(mb,(0,s*.344,1.2),(.19,.025,2.15),'stone',F)
   guard(mb,F,2.50,.48)
  H.build(mb,isl+' silver column casings and dark inserts','Columns',isl);return old_column_positions(isl)
 for o in list(ACTIVE):
  if o.get('island')==isl and o.get('V11_kind')=='platform_column':H.retire(o)
 for x,y0 in old_column_positions(isl):
  w,e=p.edges(x)
  for dy in ((-2.25,2.25) if p.shin and e-w>10 else (0,)):
   y=y0+dy
   if not free_stair(isl,x,y,.35) or not p.floor_hit(x,y):continue
   if any(abs(x-mx)<.65 and abs(y-my)<.65 for mx,my,_,_ in MASTS):continue
   top=p.eave-.48;F=H.frame(isl,x,p.z,y);h=top-p.z
   H.box(mb,(0,0,.05),(.66,.66,.10),'silver',F)
   if isl in ('20-21','22-23'):
    H.cyl(mb,(0,0,h/2),.34,h,'silver',20,F)
    for s in (-1,1):H.box(mb,(0,s*.333,min(h,3.5)/2),(.40,.028,min(h,3.5)),'stone',F)
   else:
    H.box(mb,(0,0,h/2),(.055,.40,h),'cream',F)
    for sx in (-1,1):H.box(mb,(sx*.19,0,h/2),(.035,.44,h),'cream',F)
   guard(mb,F,2.12,.46)
   for dx in (-.25,.25):
    for ddy in (-.25,.25):H.cyl(mb,(dx,ddy,.14),.027,.06,'silver',6,F)
   H.tube(mb,[(.27,.26,.18),(.27,.26,h-.05)],.034,'silver',F=F)
   for zz in np.arange(.5,h,.75):H.box(mb,(.27,.26,zz),(.12,.10,.03),'silver',F)
   ps.append((float(x),float(y)));H.count('new_column_sections')
 H.build(mb,isl+' observed steel sections and column finishes','Columns',isl);return ps
def canopy(p):
 isl=p.isl
 if isl=='01-02':columns(p);return
 if p.shin:retire_name('V10 '+isl+' retained steel and lights')
 else:
  retire_name('V8 canopy '+isl+' | structure (beams, purlins, gutters, trays, speakers)');retire_name('V8 canopy '+isl+' | light fittings')
 ps=columns(p);mb=L.MeshBuilder();utilities=L.MeshBuilder();lights=L.MeshBuilder();soffit=L.MeshBuilder()
 # Frames follow existing support stations rather than an unrelated new pole grid.
 for x in sorted(set(round(q[0],3) for q in ps)):
  w,e=p.edges(x);cy=(w+e)/2
  if not p.x0<x<p.x1:continue
  fs=list(np.linspace(.01,.99,15)) if isl=='05-06' else [0,.24,.5,.76,1]
  for a,b in zip(fs[:-1],fs[1:]):
   y0=w+(e-w)*a;y1=w+(e-w)*b
   if any(abs(x-mx)<.55 and min(y0,y1)-.2<my<max(y0,y1)+.2 and mz1>p.eave-.5 for mx,my,mz0,mz1 in MASTS):continue
   H.beam(mb,p.point(x,a,-.22),p.point(x,b,-.22),.16,.30 if isl!='09-10' else .40)
  for xx,yy in ps:
   if abs(xx-x)>.02:continue
   # Stem extensions and haunches join the existing column tops to the rafters.
   z0=(p.eave-.48) if p.shin or isl=='03-04' else (9.51 if isl=='05-06' else 9.72)
   target=p.zroof(x,(yy-w)/(e-w))-.26
   if target>z0:H.beam(mb,(x,yy,z0),(x,yy,target),.18,.23)
   for s in (-1,1):H.beam(mb,(x,yy,z0-.38),(x,yy+s*.85,target),.10,.16)
  if isl in ('03-04','09-10'):
   for y in np.arange(w+.25,e-.2,.28):
    z=p.zroof(x,(y-w)/(e-w))-.22
    for dx in (-.09,.09):H.cyl(mb,(0,0,0),.022,.025,'silver',6,Matrix.Translation((x+dx,y,z))@Matrix.Rotation(math.pi/2,4,'Y'))
   H.count('riveted_transverse_frames')
 # Longitudinal secondary framing follows the curved roof edge, with exposed tray rungs.
 for a in np.arange(p.x0,p.x1,3.0):
  b=min(a+3,p.x1);xm=(a+b)/2
  for f in (.10,.26,.42,.58,.74,.90):
   w,e=p.edges(xm);yy=w+(e-w)*f
   if any(abs(xm-mx)<2 and abs(yy-my)<.6 and z1>p.eave-.5 for mx,my,z0,z1 in MASTS):continue
   H.beam(mb,p.point(a,f,-.11),p.point(b,f,-.11),.07,.10)
  for s in (-1,1):
   y=H.yc(isl,xm)+s*(1.20 if not p.shin else 1.40);z=p.eave-.42
   for dy in (-.24,.24):H.beam(utilities,(a,H.yc(isl,a)+s*1.4+dy,z),(b,H.yc(isl,b)+s*1.4+dy,z),.035,.08,'silver',section=False)
   for xx in np.arange(a,b,.45):
    cy=H.yc(isl,xx)+s*1.4;H.box(utilities,(xx,cy,z-.02),(.035,.53,.025),'silver')
   for dy in (-.12,0,.12):H.tube(utilities,[(a,H.yc(isl,a)+s*1.4+dy,z+.055),(b,H.yc(isl,b)+s*1.4+dy,z+.055)],.018,'dark',n=6)
  if isl in ('20-21','22-23'):
   # Flanking panel soffits leave the central roof structure visible.
   w,e=p.edges(xm);mid=(w+e)/2
   for a0,b0 in ((w+.12,mid-1.3),(mid+1.3,e-.12)):
    for y0 in np.arange(a0,b0,1.1):
     y1=min(y0+1.08,b0);yy=(y0+y1)/2
     if any(abs(xm-mx)<2 and y0-.5<my<y1+.5 for mx,my,_,_ in MASTS):continue
     f0=(y0-w)/(e-w);f1=(y1-w)/(e-w)
     shell(soffit,[(xx,p.edges(xx)[0]+(p.edges(xx)[1]-p.edges(xx)[0])*ff,p.eave-.57) for xx,ff in [(a+.009,f0),(b-.009,f0),(b-.009,f1),(a+.009,f1)]],'white',.055)
  H.count('roof_service_bays')
 # Individual two-tube suspended fixtures, varied rows and spacing by canopy family.
 pitch=5.4 if isl in ('03-04','05-06') else 6.0 if not p.shin else 7.2
 for j,x in enumerate(np.arange(p.x0+2,p.x1-1,pitch)):
  w,e=p.edges(x)
  for s in (-1,1):
   y=H.yc(isl,x)+s*min(2.9,(e-w)*.28);F=H.frame(isl,x,p.z,y);z=p.eave-p.z-(.84 if isl in ('20-21','22-23') else .72)
   H.box(lights,(0,0,z),(2.35,.25,.06),'cream',F)
   for dy in (-.065,.065):H.box(lights,(0,dy,z-.04),(2.18,.045,.045),'light',F)
   for dx in (-.9,.9):H.tube(lights,[(dx,0,z+.02),(dx,0,z+.55)],.012,'silver',F=F)
   H.count('suspended_twin_tube_fittings')
  if j%8==3:H.lamp(isl+' canopy fill '+str(j),H.frame(isl,x,p.z),(0,0,z-.10),length=4,power=180)
 H.build(mb,isl+' exposed rafters haunches and purlins','Roof_Structure',isl);H.build(utilities,isl+' ladder cable trays and conduits','Roof_Utilities',isl);H.build(lights,isl+' individually suspended light rows','Roof_Lights',isl);H.build(soffit,isl+' segmented side soffits with open centre','Soffits',isl)
 H.R['platforms'][isl]['columns']=ps

def adjust_roof_equipment(p):
 if not p.shin:return
 old=json.loads(SC['V10_platform_context'])['roofs'][p.isl]['eave_z']
 for o in list(ACTIVE):
  if not o.name.startswith('V10 '+p.isl+' '):continue
  if 'roof equipment room at' not in o.name and 'equipment room roof curbs' not in o.name:continue
  lo,hi=H.bounds(o);x=float((lo[0]+hi[0])/2);newx=x
  # The lower roof puts the house tops among the inherited portals. Keep the
  # whole house between portals, rather than passing an OCS beam through it.
  half=(hi[0]-lo[0])/2
  portals=sorted(set(round(mx,2) for mx,y,z0,z1 in MASTS if p.x0<mx<p.x1 and z1>p.eave and p.edges(mx)[0]-8<y<p.edges(mx)[1]+8))
  options=[(a+b)/2 for a,b in zip(portals[:-1],portals[1:]) if b-a>2*half+1.5]
  if options:newx=min(options,key=lambda q:abs(q-x))
  dy=H.yc(p.isl,newx)-H.yc(p.isl,x);dz=p.eave-old
  q=H.copy_source(o);q.location+=Vector((newx-x,dy,dz))
  q['island']=p.isl;q['V21_kind']='Roof_Equipment_Adjusted'
  H.R['equipment'].append({'object':q.name,'delta':[newx-x,dy,dz],'reason':'fit lowered canopy and portal bay; estimated position'})
 # Shorten only the high hanger rods. Furnishings and sign faces below 3.3 m
 # retain their exact position; copies preserve every original mesh.
 names=[f'V5 platform {p.isl} furniture and signs']
 for n in names:
  o=bpy.data.objects.get(n)
  if not o:continue
  verts=H.world(o);cut=p.z+3.30;top=float(verts[:,2].max());newtop=p.eave-.34
  if top<=newtop:continue
  q=H.copy_source(o);inv=q.matrix_world.inverted()
  for v,pt in zip(q.data.vertices,verts):
   if pt[2]>cut:pt[2]=cut+(pt[2]-cut)*(newtop-cut)/(top-cut);v.co=inv@Vector(pt)
  q['V21_kind']='Sign_Hangers_Adjusted';q['island']=p.isl

def shorten_shared_hangers():
 o=bpy.data.objects.get('V5 Shinkansen roofs | hanger rods for platform-number signs')
 if not o:return
 q=H.copy_source(o);inv=q.matrix_world.inverted()
 for v,pt in zip(q.data.vertices,H.world(o)):
  p=min((p for p in P.values() if p.shin),key=lambda p:abs(pt[1]-H.yc(p.isl,pt[0])))
  if pt[2]>p.eave-.4:pt[2]=p.eave-.4;v.co=inv@Vector(pt)
 q['V21_kind']='Sign_Hangers_Adjusted'

def cctv(mb,F,h,dome=False):
 H.box(mb,(0,0,h),(.20,.20,.07),'silver',F)
 H.tube(mb,[(0,0,h),(0,0,h-.32)],.022,'silver',F=F)
 if dome:
  H.cyl(mb,(0,0,h-.36),.15,.09,'white',20,F)
  L.lathe(mb,[(.02,-.51),(.10,-.48),(.13,-.42),(.13,-.39)],(0,0),20,H.I['lens'],cap_top=True,cap_bottom=True,frame=F@Matrix.Translation((0,0,h)))
 else:
  C=F@Matrix.Translation((.12,0,h-.42))@Matrix.Rotation(.15,4,'Y')
  H.box(mb,(0,0,0),(.38,.18,.16),'cream',C);H.box(mb,(.06,0,.105),(.56,.24,.035),'cream',C)
  Q=C@Matrix.Translation((.20,0,0))@Matrix.Rotation(math.pi/2,4,'Y')
  H.cyl(mb,(0,0,0),.065,.025,'black',16,Q);H.cyl(mb,(0,0,.016),.045,.015,'lens',16,Q)
  H.tube(mb,[(-.11,0,h-.40),(-.27,0,h-.45),(-.22,0,h-.18),(0,0,h)],.010,'black',F=F)
 H.count('new_cctv')

def emergency(mb,F,side=1,round_column=False):
 y=side*(.53 if round_column else .28)
 H.box(mb,(0,y,1.37),(.26,.16,.54),'yellow',F)
 H.box(mb,(0,y+side*.09,1.45),(.19,.022,.15),'dark',F)
 H.cyl(mb,(0,0,0),.048,.026,'red',16,F@Matrix.Translation((0,y+side*.11,1.26))@Matrix.Rotation(math.pi/2,4,'X'))
 H.text('SOS',(0,y+side*.108,1.62),.065,'black',right=(-side,0,0),F=F)
 H.tube(mb,[(.15,y,1.12),(.15,y,.10)],.018,'silver',F=F);H.count('emergency_call_boxes')

def route_panel(mb,F,side=1,round_column=False):
 y=side*(.51 if round_column else .25)
 H.box(mb,(0,y,1.25),(.40,.05,.85),'silver',F)
 H.box(mb,(0,y+side*.033,1.25),(.36,.016,.80),'white',F)
 for j,k in enumerate(('orange','green','blue')):
  H.box(mb,(-.10+j*.1,y+side*.046,1.22),(.018,.009,.51),'%s'%k,F)
  for z in np.arange(1.0,1.49,.10):H.box(mb,(-.10+j*.1,y+side*.052,z),(.04,.010,.018),'dark',F)
 H.text('ご案内',(0,y+side*.052,1.57),.055,'black',right=(-side,0,0),F=F);H.count('column_route_maps')

def floor_detail(p):
 if p.isl=='01-02':return
 mb=L.MeshBuilder();marks=L.MeshBuilder();a,b=p.isl.split('-');edge=1.59
 # Short independently tested segments stop at existing stair apertures and
 # do not paint over the tactile strip or leave the actual deck polygon.
 for x in np.arange(p.x0+1,p.x1-.5,.9):
  w=H.ty(a,x)+edge+.70;e=H.ty(b,x)-edge-.70
  for y in np.arange(w,e,.40):
   if p.floor_hit(x,y) and p.floor_hit(x,y+.39) and free_stair(p.isl,x,y,.18):H.box(mb,(x,y+.195,p.z+.004),(.008,.39,.002),'joint')
 for x in np.arange(p.x0+1,p.x1-1,1.8):
  F=H.frame(p.isl,x,p.z)
  for y in np.arange(-4,4.1,.9):
   q=F@Vector((0,y,0))
   if all(p.floor_hit(q.x+dx,q.y) and free_stair(p.isl,q.x+dx,q.y,.18) for dx in (-.88,0,.88)):H.box(mb,(0,y,.004),(1.76,.008,.002),'joint',F)
 for j,x in enumerate(np.arange(p.x0+12,p.x1-7,20)):
  for s,k in ((1,a),(-1,b)):
   y=H.ty(k,x)+s*(edge+1.03)
   if not p.floor_hit(x,y) or not free_stair(p.isl,x,y,.35):continue
   F=H.frame(p.isl,x,p.z,y);key='blue' if p.shin else ('green' if p.isl in ('03-04','05-06') else 'orange')
   H.box(marks,(0,0,.008),(.68,.24,.006),key,F)
   H.text(str(j%16+1),(0,0,.012),.16,'white',right=(1,0,0),up=(0,1,0),F=F)
   for dx in (-.32,.32):H.box(marks,(dx,s*.65,.007),(.035,1.25,.005),key,F)
   H.count('boarding_position_marks')
 H.build(mb,p.isl+' tiled paving joints around stair apertures','Paving',p.isl);H.build(marks,p.isl+' boarding number and queue markings','Paving',p.isl)

def equipment(p):
 mb=L.MeshBuilder();ps=H.R['platforms'][p.isl].get('columns',old_column_positions(p.isl))
 # Equipment is attached to existing support stations. Repeated equipment
 # quantities are an interpretation, not individually surveyed inventory.
 for j,(x,y) in enumerate(ps):
  if j%4==1:
   F=H.frame(p.isl,x,p.z,y);emergency(mb,F,round_column=p.isl in ('01-02','20-21','22-23'))
  if j%4==3:route_panel(mb,H.frame(p.isl,x,p.z,y),-1,round_column=p.isl in ('01-02','20-21','22-23'))
 if p.isl!='01-02':
  for j,x in enumerate(np.arange(p.x0+11,p.x1-5,32)):
   F=H.frame(p.isl,x,p.z,H.yc(p.isl,x)-1.8)@Matrix.Rotation(math.pi*(j%2),4,'Z');cctv(mb,F,p.eave-p.z-.42,p.isl in ('20-21','22-23'))
   # Roof loudspeaker, separate grille and folded mounting bracket.
   S=H.frame(p.isl,x,p.z,H.yc(p.isl,x)+1.8)
   H.box(mb,(0,0,p.eave-p.z-.80),(.28,.24,.24),'cream',S)
   for yy in np.arange(-.09,.10,.035):H.box(mb,(.146,yy,p.eave-p.z-.8),(.012,.015,.18),'dark',S)
   H.tube(mb,[(0,0,p.eave-p.z-.67),(0,0,p.eave-p.z-.35)],.018,'silver',F=S)
 H.build(mb,p.isl+' column emergency boxes maps CCTV and speakers','Platform_Equipment',p.isl)

def free_room(p,x,length,width):
 F=H.frame(p.isl,x,p.z);pts=[]
 for xx in np.linspace(-length/2-.5,length/2+.5,15):
  for yy in np.linspace(-width/2-1.10,width/2+1.10,13):
   q=F@Vector((xx,yy,.06))
   if not p.floor_hit(q.x,q.y) or not free_stair(p.isl,q.x,q.y,.3):return False
   pts.append(q)
 for o,lo,hi in OCC:
  if hi[2]<p.z+.15 or lo[2]>p.z+3.05 or hi[0]<x-length/2-1 or lo[0]>x+length/2+1:continue
  if hi[1]<min(q.y for q in pts) or lo[1]>max(q.y for q in pts):continue
  if o.type=='EMPTY':return False
  tree=None
  for q in pts:
   if not lo[0]-.03<q.x<hi[0]+.03 or not lo[1]-.03<q.y<hi[1]+.03:continue
   if tree is None:tree=H.bvh(o)
   if tree.ray_cast(q,Vector((0,0,1)),3.05)[0] is not None:return False
 return True

def waiting_room(p):
 if p.isl not in ('07-08','14-15','16-17','18-19','20-21','22-23'):return
 length=6.2;width=2.6
 candidates=sorted(np.arange(p.x0+18,p.x1-18,3.5),key=lambda x:abs(x-43))
 x=next((float(x) for x in candidates if free_room(p,float(x),length,width)),None)
 if x is None:H.R['platforms'][p.isl]['waiting_room']='no unobstructed inherited bay';return
 F=H.frame(p.isl,x,p.z);mb=L.MeshBuilder();furn=L.MeshBuilder();w=width/2;l=length/2
 H.box(mb,(0,0,.035),(length,width,.07),'tile',F);H.box(mb,(0,0,2.85),(length+.12,width+.12,.16),'white',F)
 for y in (-w,w):
  H.box(mb,(0,y,.24),(length,.09,.40),'silver',F);H.box(mb,(0,y,2.55),(length,.10,.35),'silver',F)
  for xx in np.linspace(-l,l,5):H.box(mb,(xx,y,1.47),(.055,.09,2.4),'silver',F)
  for a,b in zip(np.linspace(-l,l,5)[:-1],np.linspace(-l,l,5)[1:]):H.box(mb,((a+b)/2,y,1.4),(b-a-.06,.022,1.91),'glass',F)
  # Native glass safety band.
  H.box(mb,(0,y*1.013,1.1),(length,.012,.035),'white',F)
 for s in (-1,1):
  xx=s*l
  for yy in (-w,w):H.box(mb,(xx,yy,1.45),(.09,.08,2.76),'silver',F)
  H.box(mb,(xx,0,2.52),(.09,width,.50),'silver',F)
  for yy in (-.97,.97):H.box(mb,(xx,yy,1.35),(.025,.60,1.95),'glass',F)
  for yy in (-.65,.65):H.box(mb,(xx,yy,1.23),(.065,.055,2.25),'silver',F)
  # Recessed sliding leaves leave a 1.25 m open doorway at each end.
  for yy in (-1.00,1.00):H.box(mb,(xx-s*.08,yy,1.2),(.025,.60,2.1),'glass',F)
  H.text('待合室  Waiting Room',(xx+s*.065,0,2.54),.16,'black',right=(0,s,0),F=F)
 for xx in np.arange(-2.3,2.31,.58):
  H.box(furn,(xx,.75,.46),(.50,.47,.08),'seat',F);H.box(furn,(xx,.97,.76),(.50,.065,.53),'seat',F)
  for dy in (.60,.91):H.tube(furn,[(xx,dy,.10),(xx,dy,.43)],.026,'silver',F=F)
 for xx in (-1.8,1.8):H.box(furn,(xx,0,2.74),(1.0,.32,.035),'light',F)
 H.box(furn,(0,0,2.72),(.80,.60,.08),'white',F)
 for yy in np.arange(-.23,.24,.055):H.box(furn,(0,yy,2.673),(.65,.025,.012),'dark',F)
 H.build(mb,p.isl+' glazed waiting room with open sliding doors','Waiting_Rooms',p.isl);H.build(furn,p.isl+' waiting room seats lighting and air diffuser','Room_Interiors',p.isl)
 H.R['rooms'].append({'island':p.isl,'frame':[list(q) for q in F],'length':length,'width':width,'walkway_sample_offset':w+.70,'estimated_position':True});H.count('glazed_waiting_rooms')

def underground():
 import v9geo as G
 from mod11_marunouchi import F as MF,DECK as MZ,STAIRS as MS
 for isl,(w,e) in G.ISL.items():
  tag='Sobu '+isl;cy=(w+e)/2;F=G.frame_matrix();mb=L.MeshBuilder();floor=L.MeshBuilder();roof=L.MeshBuilder();z=G.DECK
  # Column-mounted items are below and between the original numbered bands.
  for j,x in enumerate(G.COL_X):
   if not -150<x<150:continue
   for s in (-1,1):
    Q=F@Matrix.Translation((x,cy+s*G.COL_ROW_OFF,z))
    if j%4==1:emergency(mb,Q,s,True)
    if j%4==3:route_panel(mb,Q,s,True)
   if j%4==0:cctv(mb,F@Matrix.Translation((x,cy-1.9,z)),2.87,True)
  # Thin seams sit on the existing underside; ceiling apertures stay unchanged.
  ceil=bpy.data.objects['V9 Sobu | B5 ceilings, bulkheads, track walls, soffit beams'];tree=H.bvh(ceil)
  for x in np.arange(-150,151,1.2):
   for y in np.arange(w+.35,e-.3,.4):
    q=F@Vector((x,y,G.B5_CEIL-.12))
    hit=tree.ray_cast(q,Vector((0,0,1)),.16)[0]
    if hit is not None:H.box(roof,(x,y,G.B5_CEIL-.004),(.009,.38,.005),'joint',F)
  deck=H.bvh(bpy.data.objects['V9 Sobu | B5 island platforms 1-2 and 3-4'])
  for j,x in enumerate(np.arange(-146,148,5.6)):
   for y in (w+1.0,w+1.48,e-1.48,e-1):
    q=F@Vector((x,y,z+.04))
    if deck.ray_cast(q,Vector((0,0,-1)),.08)[0] is not None:H.box(floor,(x,y,z+.006),(.32,.32,.008),('blue','green','orange','cream')[j%4],F)
  H.build(mb,tag+' emergency phones route maps and ceiling cameras','Underground_Equipment',tag);H.build(roof,tag+' subdivided cream ceiling panels','Underground_Ceiling',tag);H.build(floor,tag+' coloured square tile inlays','Underground_Paving',tag)
  H.R['platforms'][tag]={'style':'round cream columns, framed maps, yellow emergency phones, mosaic floor, cream ceiling','side_walls_restored':False}
 tag='Metro M17';mb=L.MeshBuilder();ceiling=L.MeshBuilder();status=L.MeshBuilder()
 for j,x in enumerate(np.arange(-58,61,6)):
  if any(min(a,a+s*13)-1<x<max(a,a+s*13)+1 for a,s in MS):continue
  for s in (-1,1):
   F=MF@Matrix.Translation((x,s*2.45,MZ))
   if j%3==0:emergency(mb,F,s,True)
   else:route_panel(mb,F,s,True)
  if j%3==1:cctv(mb,MF@Matrix.Translation((x,0,MZ)),3.05,True)
 tree=H.bvh(bpy.data.objects['V11 M17 B1 slab and B2 ceilings with stair openings'])
 for x in np.arange(-61,61,.60):
  for y in np.arange(-3.95,3.96,.3):
   q=MF@Vector((x,y,-7.12))
   if tree.ray_cast(q,Vector((0,0,1)),.16)[0] is not None:H.box(ceiling,(x,y,-7.006),(.018,.285,.010),'joint',MF)
 # Status lamps sit on the existing red-end gate modules, not in the walkway.
 for x in np.linspace(-58,58,18):
  for s in (-1,1):
   H.box(status,(x,s*3.92,MZ+1.30),(.15,.09,.06),'dark',MF);H.box(status,(x,s*3.92,MZ+1.338),(.09,.05,.017),'light',MF)
 H.build(mb,'M17 column maps call boxes and dome cameras','Underground_Equipment',tag);H.build(ceiling,'M17 individual slatted ceiling joints','Underground_Ceiling',tag);H.build(status,'M17 platform gate status lamps','Underground_Equipment',tag)
 H.R['platforms'][tag]={'style':'low white slatted ceiling, red-trimmed half-height gates, granite columns','side_walls_restored':False}

def main():
 global SC,ACTIVE,MASTS,STAIRS,OCC
 import csv
 args=sys.argv[sys.argv.index('--')+1:];SC=bpy.data.scenes['Tokyo Station'];bpy.context.window.scene=SC
 if SC.get('V21_platforms'):raise RuntimeError('Start from V20')
 Path(args[2]).write_text(json.dumps(H.snapshot(),separators=(',',':')),encoding='utf8');H.setup()
 ACTIVE=active_objects();STAIRS=[q for q in json.loads(SC['V6_platform_keepouts']) if q['kind']=='stairwell']
 with (Path(__file__).parent.parent/'validation/surface_catenary_masts.csv').open() as f:MASTS=[tuple(float(q[k]) for k in ('x','y','base_z','top_z')) for q in csv.DictReader(f)]
 for isl,style in STYLES.items():
  p=Profile(isl);P[isl]=p;H.R['platforms'][isl]={'style':style,'deck_z':p.z,'eave_z':p.eave,'extent':[p.x0,p.x1],'surveyed_positions':False}
  skins(p);canopy(p);adjust_roof_equipment(p);floor_detail(p);equipment(p);print('V21_SURFACE_OK',isl,flush=True)
 shorten_shared_hangers();bpy.context.view_layer.update()
 OCC=[]
 for o in active_objects():
  if o.type=='MESH':lo,hi=H.bounds(o)
  elif o.type=='EMPTY' and o.instance_collection:
   q=np.array(o.matrix_world.translation);lo=q-np.array([.24,.24,0]);hi=q+np.array([.24,.24,1.85])
  else:continue
  if hi[2]>6.35 and lo[2]<11.5:OCC.append((o,lo,hi))
 for p in P.values():waiting_room(p);print('V21_ROOM_CHECK',p.isl,flush=True)
 underground();finish_details()
 from render_review_cams_v21 import cameras
 cameras(H.R);SC['V21_platforms']=json.dumps(H.R);SC['last_stage']='V21 individually referenced surface and underground platforms'
 guide=Path(__file__).parent.parent/'README_V21.txt'
 if guide.exists():bpy.data.texts.new('README_V21').write(guide.read_text(encoding='utf8'))
 bpy.context.view_layer.update();bpy.ops.file.pack_all();bpy.context.preferences.filepaths.save_version=0
 Path(args[0]).parent.mkdir(parents=True,exist_ok=True);bpy.ops.wm.save_as_mainfile(filepath=str(Path(args[0]).resolve()),compress=True)
 Path(args[1]).write_text(json.dumps(H.R,ensure_ascii=False,indent=2),encoding='utf8');print('V21_BUILD_OK',H.R['counts'],flush=True)
def finish_details():
 """Resolve visible underside levels and support the reused roof-room curbs."""
 from mod11_marunouchi import F as MF,DECK as MZ
 n='V21 M17 individual slatted ceiling joints';o=bpy.data.objects.get(n)
 if o and o.get('V21_kind')=='Underground_Ceiling':bpy.data.objects.remove(o,do_unlink=True)
 tree=H.bvh(bpy.data.objects['V11 M17 B1 slab and B2 ceilings with stair openings']);mb=L.MeshBuilder()
 for x in np.arange(-60.8,60.8,1.20):
  for y in np.arange(-3.98,3.99,.14):
   hits=[tree.ray_cast(MF@Vector((x+dx,y,-7.20)),Vector((0,0,1)),.19)[0] for dx in (-.57,0,.57)]
   if all(q is not None for q in hits):H.box(mb,(x,y,float(hits[1].z)-.005),(1.18,.012,.008),'joint',MF)
 H.build(mb,'M17 individual slatted ceiling joints','Underground_Ceiling','Metro M17')
 o=bpy.data.objects.get('V21 M17 platform gate status lamps')
 if o and o.get('V21_kind')=='Underground_Equipment':bpy.data.objects.remove(o,do_unlink=True)
 mb=L.MeshBuilder()
 for centre in [-45+18*i for i in range(6)]:
  for door in (-5.4,0,5.4):
   x=centre+door+.75
   for s in (-1,1):
    H.box(mb,(x,s*4.12,MZ+1.23),(.15,.18,.06),'dark',MF);H.box(mb,(x,s*4.12,MZ+1.267),(.09,.10,.017),'light',MF)
 H.build(mb,'M17 platform gate status lamps','Underground_Equipment','Metro M17')
 for o in list(bpy.data.objects):
  if o.get('V21_kind')=='Lighting' and any(p.shin and p.isl in o.name for p in P.values()):o.data.energy=400
 H.R['counts']['roof_room_support_pedestals']=0
 for p in P.values():
  if not p.shin:continue
  old=bpy.data.objects.get('V21 '+p.isl+' roof-room support pedestals')
  if old and old.get('V21_kind')=='Roof_Room_Supports':bpy.data.objects.remove(old,do_unlink=True)
  mb=L.MeshBuilder()
  for o in list(SC.objects):
   if o.get('V21_kind')!='Roof_Equipment_Adjusted' or o.get('island')!=p.isl or 'roof curbs' not in o.name:continue
   lo,hi=H.bounds(o)
   # Short service pedestals physically bridge the old room's raised floor to
   # the new pitched skin. Never imply that this offset is measured on site.
   for x in (float(lo[0]+.24),float(hi[0]-.24)):
    for y in (float(lo[1]+.24),float(hi[1]-.24)):
     w,e=p.edges(x);bottom=p.zroof(x,(y-w)/(e-w))-.04;top=float(hi[2])+.01
     if top>bottom:
      H.box(mb,(x,y,(top+bottom)/2),(.28,.28,top-bottom),'silver');H.box(mb,(x,y,bottom+.05),(.40,.40,.05),'silver');H.count('roof_room_support_pedestals')
  H.build(mb,p.isl+' roof-room support pedestals','Roof_Room_Supports',p.isl)
if __name__=='__main__':main()
