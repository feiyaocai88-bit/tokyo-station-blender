"""Generate clipped street surfaces. CPython + Shapely 2.1+; source.json output.json.
The source is a local V18 mesh export; coordinates fit that model, not a survey.
The generated JSON is checked into the repository, so Blender needs no Shapely.
"""
import json,math,sys,random
from pathlib import Path
from shapely.geometry import Polygon,LineString,box,Point
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles
def rounded(path,r=8,n=10):
 out=[path[0]]
 for i,b in enumerate(path[1:-1],1):
  a=path[i-1];c=path[i+1];la=math.dist(a,b);lc=math.dist(b,c);d=min(r,la*.35,lc*.35)
  p=tuple(b[k]+(a[k]-b[k])*d/la for k in (0,1));q=tuple(b[k]+(c[k]-b[k])*d/lc for k in (0,1))
  for j in range(n+1):
   t=j/n;out.append(tuple((1-t)**2*p[k]+2*t*(1-t)*b[k]+t*t*q[k] for k in (0,1)))
 out.append(path[-1]);return out
def pieces(p):return [p] if p.geom_type=='Polygon' else [q for q in getattr(p,'geoms',[]) if q.geom_type=='Polygon']
def rounded_poly(p,f=.18,n=5):
 out=[]
 for i,b in enumerate(p):
  a=p[i-1];c=p[(i+1)%len(p)];u=tuple(b[k]+(a[k]-b[k])*f for k in (0,1));v=tuple(b[k]+(c[k]-b[k])*f for k in (0,1))
  for j in range(n+1):
   t=j/n;out.append(tuple((1-t)**2*u[k]+2*t*(1-t)*b[k]+t*t*v[k] for k in (0,1)))
 return Polygon(out)
def top(data,material=None):
 ps=[];vs=data['vertices']
 for i,f in enumerate(data['faces']):
  p=[vs[j] for j in f]
  if material and material not in data['materials'][data['face_mats'][i]]:continue
  if max(q[2] for q in p)-min(q[2] for q in p)>.001 or min(q[2] for q in p)<.1:continue
  q=Polygon([(v[0],v[1]) for v in p]).buffer(0)
  if q.area>.001:ps.append(q)
 return unary_union(ps)
def record(p):return [{'outer':[[round(x,5),round(y,5)] for x,y in q.exterior.coords],'holes':[[[round(x,5),round(y,5)] for x,y in h.coords] for h in q.interiors]} for q in pieces(p)]
def mesh(p):
 vs=[];fs=[];idx={}
 for q in pieces(p):
  for t in constrained_delaunay_triangles(q).geoms:
   # Constrained edges share vertices across every bay; no T junctions or caps
   # across holes are introduced by clipping unconstrained triangles.
   for cut in pieces(t):
    coords=list(cut.exterior.coords)[:-1];face=[]
    for x,y in coords:
     key=(round(x,5),round(y,5))
     if key not in idx:idx[key]=len(vs);vs.append(key)
     face.append(idx[key])
    if len(face)>=3:fs.append(face)
 return {'v':vs,'f':fs}
def main():
 source=json.load(open(sys.argv[1],encoding='utf8'))
 paths={'front':([(-212,-129),(205,-129)],12.0),'north':(rounded([(-176,-144),(-164,-113),(-162,-61),(-164,-35),(-181,-10),(-193,1),(-193,223.4384)]),12.0),'south':(rounded([(179,-144),(164,-111),(162,-62),(170,-29),(199,2),(222,26),(248.5,48),(248.5,223.4384)]),10.0)}
 new=unary_union([LineString(p).buffer(w/2,cap_style='flat',join_style='round') for p,w in paths.values()])
 primary=new
 south=top(source['V14 south curved road sidewalk and raised curbs'],'asphalt')
 new=unary_union([new,south]);new=new.buffer(2.8,join_style='round').buffer(-2.8,join_style='round').intersection(box(-214,-144,254,223.4384))
 # Keep the inherited underbridge footways and V14 south shop pavement clear.
 protected=[box(-202,15.8,-199,224),box(-187,15.8,-184,224)]
 new=new.difference(unary_union(protected)).buffer(0)
 north=rounded_poly([(-127,-112),(-127,-55),(-119,-39),(-54,-39),(-43,-48),(-43,-111),(-52,-120),(-118,-120)])
 southsquare=rounded_poly([(49,-105),(49,-48),(59,-36),(106,-36),(153,-78),(153,-100),(140,-116),(66,-116)])
 connects=[Polygon([(-166,-59),(-121,-58),(-115,-47),(-164,-46)]),Polygon([(145,-83),(173,-64),(179,-73),(151,-92)])]
 concrete=unary_union(connects).difference(new).buffer(0)
 old=top(source['V4 unified perimeter and transport road'])
 whole=unary_union([old.intersection(box(-214,-144,254,16)),new.buffer(3.0,join_style='round')]).intersection(box(-214,-144,254,223.4384))
 metro=unary_union([box(-146.1,-97.6,-129.0,-90.4),box(-35.8,-142.3,-19.1,-135.8)])
 oldpaving=top(source['V14 south curved road sidewalk and raised curbs'],'paving').difference(primary)
 protect=unary_union([north,southsquare,concrete,new,metro,box(-45,-123.5,55,-34),box(-158,-34,184,-10.3),box(-184.8,10.72,-167.2,23.3),box(182.72,10.22,201.28,21.8),box(182,44.3,243,208),oldpaving,*protected])
 infill=whole.difference(protect).buffer(0)
 kerbs=[]
 junctions=unary_union([concrete.buffer(.35),north.buffer(.2),southsquare.buffer(.2),metro,box(-214,-145,-208,230),box(202,-140,207,-120),box(-205,220,235,225)])
 for q in pieces(new):
  for ring in [q.exterior,*q.interiors]:
   line=LineString(ring.coords).difference(junctions)
   for l in ([line] if line.geom_type=='LineString' else getattr(line,'geoms',[])):
    if l.geom_type=='LineString' and l.length>.2:kerbs.append(list(l.coords))
 tiles=[];rng=random.Random(1901)
 for x in range(-214,254,2):
  for y in range(-144,224,2):
   t=box(x+.01,y+.01,x+1.99,y+1.99).intersection(infill)
   for q in pieces(t):
    if q.area>.04:tiles.append({'p':list(q.exterior.coords)[:-1],'shade':rng.choice(['white','pale','pale','mid'])})
 result={'revision':19,'basis':'Continuous carriageways fitted to V18 geometry; kerb/road/furniture coordinates are interpretive.', 'paths':{k:{'points':p,'width':w} for k,(p,w) in paths.items()},'asphalt':mesh(new),'asphalt_outline':record(new),'primary':mesh(primary),'primary_outline':record(primary),'concrete':mesh(concrete),'infill':mesh(infill),'infill_outline':record(infill),'kerbs':kerbs,'tiles':tiles,'rear_profile':source['rear_profile'],'areas':{'asphalt':new.area,'concrete_connections':concrete.area,'paving_infill':infill.area},'components':len(pieces(new))}
 Path(sys.argv[2]).write_text(json.dumps(result,separators=(',',':')),encoding='utf8');print('V19_STREET_PLAN',result['areas'],'components',result['components'],'tiles',len(tiles))
if __name__=='__main__':main()
