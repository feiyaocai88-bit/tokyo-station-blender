"""V21 -> V22: continuous Chuo envelope from the user's oblique aerial photo.
-- out.blend build.json baseline.json
Photo establishes shape and relative placement, not measured dimensions.
"""
import bpy,bmesh,sys,math,json,csv,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
sys.path.insert(0,str(Path(__file__).parent))
import v22lib as H
L=H.L;SC=None
X0=-140.5;X1=108.0;SPRING=20.35;CROWN=23.28;CAP_C=0.;CAP_L=22.;MASTS=[]
PORTALS=[];FRAMES=[];FIXINGS=[]
def edges(x):return H.ty('01',x)+1.59,H.ty('02',x)-1.59
def outer(x,s):return H.ty('01' if s<0 else '02',x)+s*1.94
def screen_top(x,s):
 oldh=2.2 if s<0 else 1.85;t=max(0,min(1,(x+140)/7,(116-x)/8))
 return 14.9+oldh+(3.55-oldh)*t
def flat(x,f):
 a,b=edges(x);return (x,a+(b-a)*f,CROWN+.045*(1-(2*f-1)**2))
def shoulder(x,s,t):
 a,b=edges(x);inside=a if s<0 else b;o=outer(x,s)
 return (x,o+(inside-o)*(1-math.cos(t)),SPRING+(CROWN-SPRING)*math.sin(t))
def cap(x,f):
 a,b=edges(x);a-=1.15;b+=1.15;u=(x-CAP_C)/(CAP_L/2)
 return (x,a+(b-a)*f,CROWN+.20+1.05*math.cos(math.pi*u/2)+.035*(1-(2*f-1)**2))

def roof_z(x,y):
 a,b=edges(x)
 if a<=y<=b:return flat(x,(y-a)/(b-a))[2]
 s=-1 if y<a else 1;d=abs(y-outer(x,s))/3.53
 return SPRING+(CROWN-SPRING)*math.sqrt(max(0,1-(1-d)**2))

def fixing_groups():
 # Read the actual mounting plates, including supports offset from the nominal
 # mast grid. Four plates (two messenger and two steady-arm tubes) per bay.
 _,_,lo,hi=H.component_labels(bpy.data.objects['V6 OCS | hangers, drop tubes, steady arms']);mid=(lo+hi)/2
 sel=(lo[:,2]>22.69)&(hi[:,2]<22.76)&(hi[:,1]<46)&(mid[:,0]>X0)&(mid[:,0]<X1)&(hi[:,0]-lo[:,0]<.3)&(hi[:,1]-lo[:,1]<.3)
 groups=[]
 for x,y,z in sorted(mid[sel].tolist()):
  if not groups or x-groups[-1][-1][0]>7:groups.append([])
  groups[-1].append((x,y))
 assert groups and all(len(g)==4 for g in groups),'Expected four existing mounting plates per Chuo bay'
 return [{'x':float(np.mean([p[0] for p in g])),'points':g} for g in groups]
def beam(mb,p,q,w=.12,h=.22,key='steel'):
 p=Vector(p);q=Vector(q);d=q-p;F=Matrix.Translation((p+q)/2)@d.to_track_quat('X','Z').to_matrix().to_4x4()
 H.box(mb,(0,0,0),(d.length,w*.12,h),key,F)
 for s in (-1,1):H.box(mb,(0,0,s*(h/2-.012)),(d.length,w,.024),key,F)
def material(key,c,rough=.5,metal=.1,trans=0):
 m=L.principled('V22 | '+key,c,rough=rough,metal=metal);H.I[key]=len(H.M);H.M.append(m)
 if trans:
  b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Transmission Weight'].default_value=trans;b.inputs['IOR'].default_value=1.45
 return m
def setup():
 H.setup()
 for k,c in [('mint',(.22,.43,.32)),('mint_light',(.235,.44,.33)),('mint_dark',(.205,.41,.30))]:material(k,c,.55,.28)
 material('smoked',(.095,.12,.105),.18,.05,.62);material('frame',(.62,.66,.64),.34,.65);material('cap_white',(.82,.84,.78),.51,.15)
 material('gasket',(.025,.031,.028),.7,.1)
def retire_sources():
 names=['V10 01-02 differentiated roof skin','V10 01-02 seams flashings gutters and glazing ribs','V10 01-02 flashed mast penetrations',
 'V10 01-02 roof equipment room at -88','V10 01-02 equipment room roof curbs -88',
 'V20 paired curved acoustic screen to canopy ribs','V20 arched rib posts anchor bolts and eave seats','V20 continuous eave attachment rails']
 for n in names:
  o=bpy.data.objects.get(n)
  if o and not o.hide_render:H.retire(o)
 H.R['retired_rooftop_house']='The former generic -88 m rooftop house is not supported by the supplied aerial view; retained hidden. The white transverse cover is a separate photo-derived feature at the central pavilion.'
def roof_skin():
 mb=L.MeshBuilder();trim=L.MeshBuilder()
 # The broad flat green strip has large sheet modules, no central skylight.
 xs=sorted(set([X0,X1]+list(np.arange(X0,X1,5.5))+[mx+s*.46 for mx,y,z0,z1 in MASTS for s in (-1,1) if X0+.46<mx<X1-.46]))
 for i,(a,b) in enumerate(zip(xs[:-1],xs[1:])):
  x=(a+b)/2;w,e=edges(x);hs=[(mx,y,.46) for mx,y,z0,z1 in MASTS if abs(x-mx)<.461 and z0<CROWN<z1]
  fs=sorted(set([0,1/3,.5,2/3,1]+[max(0,min(1,(y+s*r-w)/(e-w))) for mx,y,r in hs for s in (-1,1)]))
  for j,(f0,f1) in enumerate(zip(fs[:-1],fs[1:])):
   if f1-f0<1e-5 or any(abs(w+(e-w)*(f0+f1)/2-y)<r for mx,y,r in hs):continue
   H.shell(mb,[flat(a,f0),flat(b,f0),flat(b,f1),flat(a,f1)],.065,('mint','mint_light','mint','mint_dark')[(i+j)%4])
  # Transverse seams are cut around the shaft apertures as well.
  for f0,f1 in zip(fs[:-1],fs[1:]):
   if f1-f0<1e-5 or any(abs(w+(e-w)*(f0+f1)/2-y)<r for mx,y,r in hs):continue
   q0=flat(a,f0);q1=flat(a,f1);H.tube(trim,[(q0[0],q0[1],q0[2]+.012),(q1[0],q1[1],q1[2]+.012)],.018,'gasket',4)
 for f in (0,1/3,2/3,1):
  for a in np.arange(X0,X1,2):
   b=min(X1,a+2);x=(a+b)/2;y=flat(x,f)[1]
   if any(abs(x-mx)<1.5 and abs(y-my)<.5 for mx,my,_,_ in MASTS):continue
   H.tube(trim,[(xx,yy,zz+.026) for xx,yy,zz in [flat(a,f),flat(b,f)]],.025 if f in (0,1) else .015,'frame' if f in (0,1) else 'gasket',6)
 for x,y,z0,z1 in MASTS:
  w,e=edges(x)
  if not(X0<x<X1 and w<y<e and z0<CROWN<z1):continue
  z=flat(x,(y-w)/(e-w))[2]
  for s in (-1,1):
   H.box(trim,(x+s*.50,y,z+.035),(.08,1.08,.14),'frame');H.box(trim,(x,y+s*.50,z+.035),(1.08,.08,.14),'frame')
  H.R['masts'].append({'x':x,'y':y,'opening_half_width':.46,'roof_z':z})
 H.build(mb,'Chuo broad shallow mint roof sheets','Green_Roof');H.build(trim,'Chuo large panel seams and flashed mast openings','Roof_Trim')
 H.R['green_roof']={'x':[X0,X1],'edge_height':CROWN,'crown_rise':.045,'sheet_length':5.5,'centre_skylight':False}
def side_enclosures():
 def pane(mb,points,s):
  pts=[Vector(p) for p in (points if s<0 else list(reversed(points)))];normal=(pts[1]-pts[0]).cross(pts[3]-pts[0]).normalized()
  vs=[tuple(p) for p in pts]+[tuple(p-normal*.024) for p in pts]
  mb.add(vs,[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],H.I['smoked'])
 for s,label in [(-1,'west'),(1,'east')]:
  mb=L.MeshBuilder();trim=L.MeshBuilder();xs=sorted(set([X0,X1]+list(np.arange(X0,X1,2.75))+FRAMES))
  ts=list(np.linspace(0,math.pi/2,33))
  for a,b in zip(xs[:-1],xs[1:]):
   if b-a<.001:continue
   # Real vertical glazing closes the gap between retained acoustic panels and
   # the curved shoulder. No end wall closes the train or staff entrances.
   pane(mb,[(a,outer(a,s),screen_top(a,s)-.28),(b,outer(b,s),screen_top(b,s)-.28),(b,outer(b,s),SPRING),(a,outer(a,s),SPRING)],s)
   for t0,t1 in zip(ts[:-1],ts[1:]):pane(mb,[shoulder(a,s,t0),shoulder(b,s,t0),shoulder(b,s,t1),shoulder(a,s,t1)],s)
   if min(abs(a-x) for x in FRAMES)>.35:
    H.sweep(trim,[(a,outer(a,s),screen_top(a,s))]+[shoulder(a,s,t) for t in ts],.032,.045,'gasket')
  for t in (0,.58,1.18,math.pi/2):H.tube(trim,[shoulder(float(x),s,t) for x in np.linspace(X0,X1,250)],.035,'frame',8)
  H.tube(trim,[(float(x),outer(float(x),s),screen_top(float(x),s)+.02) for x in np.linspace(X0,X1,250)],.035,'frame',8)
  H.build(mb,'Chuo '+label+' continuous dark curved glazing','Curved_Enclosure');H.build(trim,'Chuo '+label+' glazing mullions and longitudinal rails','Glazing_Frames')
 H.R['side_enclosure']={'spring_height':SPRING,'crown_height':CROWN,'outer_track_offset':1.94,'inner_track_offset':1.59,'material':'dark tinted glazing interpretation','longitudinal_extent':[X0,X1]}
def frame_path(x):
 a,b=edges(x)
 return [(x,outer(x,-1),14.99),(x,outer(x,-1),SPRING)]+[shoulder(x,-1,t) for t in np.linspace(0,math.pi/2,33)[1:]]+[flat(x,f) for f in np.linspace(0,1,7)[1:]]+[shoulder(x,1,t) for t in np.linspace(math.pi/2,0,33)[1:]]+[(x,outer(x,1),14.99)]

def inner_beam_path(x):
 p=[Vector(v) for v in frame_path(x)[1:-1]];result=[]
 for i,v in enumerate(p):
  tangent=(p[min(i+1,len(p)-1)]-p[max(0,i-1)]).normalized()
  normal=Vector((0,-tangent.z,tangent.y)).normalized()
  result.append(tuple(v-normal*.14))
 return result
def structure():
 ribs=L.MeshBuilder();fix=L.MeshBuilder();secondary=L.MeshBuilder();services=L.MeshBuilder()
 for x in FRAMES:
  pts=frame_path(x);H.sweep(ribs,pts,.24,.19,'frame')
  # Narrow flange lips and a web make the rings read as built steel sections.
  for dx in (-.14,.14):H.sweep(ribs,[(xx+dx,y,z) for xx,y,z in pts],.035,.25,'frame')
  for s in (-1,1):
   y=outer(x,s);H.box(fix,(x,y,14.99),(.55,.50,.18),'silver')
   for dx in (-.20,.20):
    for dy in (-.18,.18):H.cyl(fix,(x+dx,y+dy,15.11),.031,.055,'trim',6)
   # Exterior anchoring plates and a rainwater downpipe follow the photograph's
   # repeated side hardware; their dimensions are interpreted.
   H.box(fix,(x,y+s*.18,18.15),(.55,.28,.44),'silver')
   for dz in (-.12,0,.12):H.box(fix,(x,y+s*.334,18.15+dz),(.44,.035,.032),'steel')
   for dx in (-.20,.20):H.cyl(fix,(0,0,0),.027,.03,'trim',6,Matrix.Translation((x+dx,y+s*.35,18.15))@Matrix.Rotation(math.pi/2,4,'X'))
   H.tube(services,[(x+.32,y+s*.22,SPRING),(x+.32,y+s*.22,15.2),(x+.32,y+s*.38,15.0)],.043,'silver',10)
   for z in np.arange(15.4,SPRING,.85):H.box(services,(x+.32,y+s*.22,z),(.14,.16,.035),'steel')
  H.R['frames'].append({'x':float(x),'path':pts,'portal_aligned':any(abs(x-p)<.01 for p in PORTALS)})
 # Tie the new upper skin to the retained lower canopy framing. The original
 # ribbed soffit, suspended lights, columns, cameras and staff room stay intact.
 for x in FRAMES:
  a,b=edges(x)
  for y in (a+.40,b-.40):
   beam(secondary,(x,y,20.70),(x,y,CROWN-.13),.12,.16)
  beam(secondary,(x,a+.38,CROWN-.14),(x,b-.38,CROWN-.14),.14,.20)
 for a,b in zip(FRAMES[:-1],FRAMES[1:]):
  for side in (0,1):
   y0=edges(a)[side]+(.4 if side==0 else -.4);y1=edges(b)[side]+(.4 if side==0 else -.4)
   beam(secondary,(a,y0,CROWN-.16),(b,y1,CROWN-.16),.12,.18)
   beam(secondary,(a,y0,20.80),(b,y1,CROWN-.23),.06,.10)
 H.build(ribs,'Chuo full width continuous portal rings','Portal_Frames');H.build(fix,'Chuo portal feet gussets and fixing hardware','Portal_Anchors');H.build(secondary,'Chuo upper roof support trusses above retained soffit','Roof_Supports');H.build(services,'Chuo exterior rainwater pipes and clips','Drainage')
 H.count('full_width_portal_frames',len(FRAMES));H.count('curved_shoulders',2*len(FRAMES))
def integrated_catenary():
 # Only Chuo transverse steel within the new enclosure changes. Contact wires,
 # droppers, insulators, lower steady arms and every mast retain their geometry.
 old=bpy.data.objects['V6 OCS | V-truss beams and cantilevers'];v,labels,lo,hi=H.component_labels(old);mid=(lo+hi)/2
 chosen=(lo[:,2]>22.55)&(mid[:,0]>X0-.1)&(mid[:,0]<X1+.1)&(hi[:,1]<46)
 q=H.copy_source(old);bm=bmesh.new();bm.from_mesh(q.data);bm.verts.ensure_lookup_table()
 bmesh.ops.delete(bm,geom=[v for v,sel in zip(bm.verts,chosen[labels]) if sel],context='VERTS');bm.to_mesh(q.data);bm.free();q.data.update();q['V22_kind']='OCS_Copy'
 mb=L.MeshBuilder()
 for x in PORTALS:
  pts=inner_beam_path(x)
  H.sweep(mb,pts,.50,.12,'steel')
  H.count('integrated_contact_support_beams')
 H.build(mb,'Chuo internal transverse contact support beams','Catenary_Supports')
 # Move only the top end rings and mounting plates of the existing rods. All
 # lower vertices (<=22.65 m), wire clamps, electrical lines and insulators stay.
 old=bpy.data.objects['V6 OCS | hangers, drop tubes, steady arms'];v,labels,lo,hi=H.component_labels(old);mid=(lo+hi)/2
 sel=(hi[:,2]>22.70)&(hi[:,1]<46)&(mid[:,0]>X0)&(mid[:,0]<X1)&(hi[:,0]-lo[:,0]<.3)&(hi[:,1]-lo[:,1]<.3)
 copied=H.copy_source(old);copied['V22_kind']='Hanger_Copy';moved=0;fixes=[]
 for part in np.flatnonzero(sel):
  x,y=mid[part,:2];group=min(FIXINGS,key=lambda g:abs(g['x']-x));path=np.array(inner_beam_path(group['x']));top=float(np.interp(y,path[:,1],path[:,2]))-.05;delta=top-22.77
  # A mounting plate translates with its tube top; the rod's lower ring stays.
  ids=np.flatnonzero((labels==part)&(v[:,2]>22.65))
  for idx in ids:copied.data.vertices[int(idx)].co.z+=delta
  moved+=len(ids)
  if lo[part,2]>22.69:fixes.append({'x':float(x),'y':float(y),'top_z':top,'frame_x':group['x']})
 copied.data.update()
 H.R['catenary']={'replaced_object':q.name,'removed_components':int(chosen.sum()),'portal_stations':PORTALS,'hanger_top_attachments':fixes,'upper_hanger_vertices_adjusted':moved,'unchanged':['mast positions and meshes','contact wires and messengers','droppers','lower hanger/steady-arm vertices at or below 22.65 m','insulators'],'reason':'Exposed Chuo trusses are replaced by inner curved beams. Only hanger upper ends and mounting plates are adapted to those beams. Existing wire, mast, insulator and lower steady-arm coordinates stay unchanged. This is a model adaptation, not a survey.'}
def white_cover():
 mb=L.MeshBuilder();frame=L.MeshBuilder();curb=L.MeshBuilder();a=CAP_C-CAP_L/2;b=CAP_C+CAP_L/2
 xs=np.linspace(a,b,49)
 for x0,x1 in zip(xs[:-1],xs[1:]):
  for f0,f1 in zip(np.linspace(0,1,13)[:-1],np.linspace(0,1,13)[1:]):H.shell(mb,[cap(x0,f0),cap(x1,f0),cap(x1,f1),cap(x0,f1)],.085,'cap_white')
 for f in (0,.16,.5,.84,1):
  pts=[(x,y,z-.10) for x,y,z in [cap(float(x),f) for x in xs]];H.tube(frame,pts,.065,'frame',10)
 for x in (a,b):
  pts=[cap(x,float(f)) for f in np.linspace(0,1,33)];H.sweep(frame,pts,.12,.22,'frame')
 # Low bearing curbs and struts attach to the supported mint roof, not thin air.
 for x in (a+.55,CAP_C,b-.55):
  w,e=edges(x)
  for y in (w+.20,e-.20):
   f=(y-(w-1.15))/(e-w+2.30);top=cap(x,f)[2]-.12;bottom=flat(x,(y-w)/(e-w))[2]-.02
   H.box(curb,(x,y,(top+bottom)/2),(.22,.22,top-bottom),'frame');H.box(curb,(x,y,bottom+.06),(.50,.50,.10),'silver')
 # A raised white cover is visible in the photo, but its engineering purpose
 # cannot be determined from this one view; deliberately avoid naming a room.
 H.build(mb,'Chuo raised transverse white cover','White_Cover');H.build(frame,'Chuo white cover rolled rims and arched underside ribs','White_Cover_Frames');H.build(curb,'Chuo white cover bearing curbs and support struts','White_Cover_Supports')
 H.R['white_cover']={'centre_x':CAP_C,'length':CAP_L,'overhang_beyond_green_edges':1.15,'edge_z':CROWN+.20,'centre_z':CROWN+1.25,'function':'unverified; reconstructed only as the visible raised white roof form','position_basis':'approximately aligned to the central station pavilion in the supplied oblique image'}
def main():
 global SC,MASTS,PORTALS,FRAMES,FIXINGS
 args=sys.argv[sys.argv.index('--')+1:];out=Path(args[0]).resolve();report=Path(args[1]).resolve();baseline=Path(args[2]).resolve();SC=bpy.data.scenes['Tokyo Station'];bpy.context.window.scene=SC
 if SC.get('V22_chuo_roof'):raise RuntimeError('Start from V21')
 baseline.write_text(json.dumps(H.snapshot(),separators=(',',':')),encoding='utf8');setup()
 with (Path(__file__).parent.parent/'validation/surface_catenary_masts.csv').open() as f:
  MASTS=[tuple(float(q[k]) for k in ('x','y','base_z','top_z')) for q in csv.DictReader(f) if q['zone']=='Chuo']
 FIXINGS=fixing_groups();PORTALS=[g['x'] for g in FIXINGS]
 infill=[float(x) for a,b in zip(PORTALS[:-1],PORTALS[1:]) for x in np.linspace(a,b,5 if b-a>33 else 3)[1:-1]]
 FRAMES=sorted(set([X0,X1]+PORTALS+infill))
 retire_sources();roof_skin();side_enclosures();structure();integrated_catenary();white_cover()
 import mod22_interlevel_equipment
 mod22_interlevel_equipment.build(sys.modules[__name__])
 from render_review_cams_v22 import cameras
 cameras();SC['V22_chuo_roof']=json.dumps(H.R);SC['last_stage']='V22 continuous Chuo roof envelope and raised transverse white cover'
 guide=Path(__file__).parent.parent/'README_V22.txt'
 if guide.exists():bpy.data.texts.new('README_V22').write(guide.read_text(encoding='utf8'))
 bpy.context.view_layer.update();bpy.ops.file.pack_all();bpy.context.preferences.filepaths.save_version=0;out.parent.mkdir(parents=True,exist_ok=True)
 bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True);report.write_text(json.dumps(H.R,ensure_ascii=False,indent=2),encoding='utf8');print('V22_BUILD_OK',H.R['counts'],flush=True)
if __name__=='__main__':main()
