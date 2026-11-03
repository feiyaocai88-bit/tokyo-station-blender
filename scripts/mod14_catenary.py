"""Replace south conventional OCS with independent photo-interpreted portal rows.
Only exposed conventional-track supports beyond the last inherited row are edited.
No roof penetration or Shinkansen support is moved. Photo chainage is approximate;
mast lateral locations are adapted to the inherited track geometry and gauge.
"""
import bpy,bmesh,math,numpy as np
import v14lib as H
import mod6_catenary as C
GROUPS=[(['03','04','05','06'],[166.,199.,237.]),(['07','08','09','10'],[164.,204.,241.])]

def remove_parts(name,selector):
 o=bpy.data.objects[name];v,inv,lo,hi=H.component_labels(o);mask=selector((lo+hi)/2,lo,hi)
 if not np.any(mask):return 0
 q=H.copy_replace(o);bm=bmesh.new();bm.from_mesh(q.data);bm.verts.ensure_lookup_table()
 bmesh.ops.delete(bm,geom=[bm.verts[i] for i in np.flatnonzero(mask[inv])],context='VERTS');bm.to_mesh(q.data);bm.free()
 return int(mask.sum())

def resolve_wire(t,xs,start):
 # Dynamic programming selects registration offsets that keep every straight
 # contact span within the inherited pantograph's 0.28 m working envelope.
 opts=[np.array([start])]+[np.array([t.P(x)+o*t.N(x) for o in np.linspace(-.28,.28,57)]) for x in xs[1:]]
 cost=np.zeros(1);hist=[]
 for a,b in zip(opts[:-1],opts[1:]):
  dev=np.empty((len(a),len(b)))
  for i,p in enumerate(a):
   for j,q in enumerate(b):
    f=np.linspace(0,1,81);xx=p[0]+(q[0]-p[0])*f;yy=p[1]+(q[1]-p[1])*f
    dev[i,j]=max(abs(yy-np.interp(xx,C.GX,C.TGT[t.k])))
  total=np.maximum(cost[:,None],dev);idx=np.argmin(total,axis=0);cost=total[idx,np.arange(len(b))];hist.append(idx)
 j=int(np.argmin(cost));worst=float(cost[j]);points=[opts[-1][j]]
 for n in range(len(hist)-1,-1,-1):j=int(hist[n][j]);points.append(opts[n][j])
 points=points[::-1]
 assert worst<=.281,(t.k,worst)
 return points,worst

def run():
 source=bpy.data.objects['V6 OCS | contact wires and messengers'];vv,inv,lo,hi=H.component_labels(source);anchors={}
 ext=C.rails_extent();cw=dict(__import__('json').loads(bpy.context.scene['V6_catenary_summary'])['contact_wire_z'])
 for ks,rows in GROUPS:
  for k in ks:
   # Find the retained contact tube terminating at the last old support.
   mids=(lo+hi)/2;dist=abs(mids[:,1]-H.ty(k,mids[:,0]));valid=(hi[:,0]<157)&(hi[:,0]>140)&(hi[:,2]<cw[k]+.02)&(lo[:,2]>cw[k]-.02)&(dist<.35)
   ci=np.flatnonzero(valid)[np.argmax(hi[valid,0])];vs=vv[inv==ci];end=vs[vs[:,0]>hi[ci,0]-.03].mean(0);anchors[k]=end[:2]
 removed={}
 def tail(c):return c[:,0]>157
 for name,zmax in [('contact wires and messengers',12.1),('droppers',12.1),('V-truss beams and cantilevers',13.5),('hangers, drop tubes, steady arms',13.5),('insulators',13.3)]:
  removed[name]=remove_parts('V6 OCS | '+name,lambda c,a,b:tail(c)&((a[:,2] if name=='V-truss beams and cantilevers' else b[:,2])<zmax))
 old_masts=[]
 o=bpy.data.objects['V6 OCS | masts'];v,iv,l,h=H.component_labels(o)
 for a,b in zip(l,h):
  if a[0]>157 and b[2]<14.5 and b[2]-a[2]>3:old_masts.append(((a+b)/2)[:2])
 def replaced_mast_parts(c,a,b):
  result=np.zeros(len(c),dtype=bool)
  for p in old_masts:result|=(np.linalg.norm(c[:,:2]-p,axis=1)<.65)
  return result
 removed['masts']=remove_parts('V6 OCS | masts',replaced_mast_parts)
 def old_straps(c,a,b):
  result=np.zeros(len(c),dtype=bool)
  for p in old_masts:result|=(np.linalg.norm(c[:,:2]-p,axis=1)<.8)
  return result
 removed['earthing']=remove_parts('V13 catenary mast grounding straps and anchor bolts',old_straps)
 P=C.Parts();records=[];mast_records=[];supports={};wire_records=[];extra=H.L.MeshBuilder()
 for ks,rows in GROUPS:
  for ix,x in enumerate(rows):
   left=float((H.ty(ks[0],x)+H.ty(ks[1],x))/2)
   right=float((H.ty(ks[2],x)+H.ty(ks[3],x))/2)
   zbase=4.606;zb=12.45
   C.build_truss(P,(x,left),(x,right),zb)
   C.build_cantilever(P,(x,left),(x,float(H.ty(ks[0],x))-1.15),zb,14.25)
   C.build_cantilever(P,(x,right),(x,float(H.ty(ks[3],x))+1.15),zb,14.25)
   for y in [left,right]:
    C.build_mast(P,x,y,zbase,14.30)
    H.box(extra,(x,y,zbase-.08),(.76,.76,.16),'concrete')
    H.tube(extra,[(x+.2,y,zbase+1.2),(x+.2,y,zbase+.15),(x+.5,y,zbase+.04)],.010,'copper',6)
    mast_records.append({'x':x,'y':y,'base_z':zbase,'top_z':14.36,'tracks':ks,'position_status':('cropped-edge adaptation 3 m inward; lateral position fitted to inherited track gauge' if x==241 else 'photo-interpreted longitudinal row; lateral position adapted to inherited track gauge')})
   refx=x if x!=241 else 244
   import sys,os
   sys.path.insert(0,os.path.join(os.path.dirname(__file__),'relayout'))
   from georef import model_to_px
   px,py=model_to_px(refx,50 if ks[0]=='03' else 85)
   records.append({'tracks':ks,'x_m':x,'photo_line_estimate_x_m':refx,'reference_mosaic_pixel':[float(px-512),float(py-768)],'longitudinal_estimate_tolerance_m':3.0,'status':'photo_interpreted' if x!=241 else 'model_end_adaptation_minus_3m','mast_y':[left,right]})
  if ks[0]=='07':
   # The inherited 7/8 approach curves more sharply than a 40 m straight
   # contact span permits. Keep a clearly labelled intermediate twin-arm
   # support; this extra pole is an engineering fit, not photo-verified.
   x=184.;y=float((H.ty('07',x)+H.ty('08',x))/2)
   C.build_mast(P,x,y,4.606,14.30)
   for k,sg in [('07',-1),('08',1)]:C.build_cantilever(P,(x,y),(x,float(H.ty(k,x))+sg*1.15),12.45,14.25)
   H.box(extra,(x,y,4.526),(.76,.76,.16),'concrete')
   mast_records.append({'x':x,'y':y,'base_z':4.606,'top_z':14.36,'tracks':['07','08'],'position_status':'unverified intermediate support required by inherited track curvature'})
   records.append({'tracks':['07','08'],'x_m':x,'status':'inherited_curve_constraint_not_photo_verified','mast_y':[y]})
  for k in ks:
   track_rows=sorted(rows+([184.] if k in ['07','08'] else []))
   t=C.Track(k,*ext[k]);start=anchors[k];xs=[float(start[0])]+track_rows+[t.x1-.20]
   pts,worst=resolve_wire(t,xs,start);zz=cw[k];ms0=zz+C.SYS_H;drop_count=0
   for i,(a,b) in enumerate(zip(pts[:-1],pts[1:])):
    C.tube(P.mb['wire'],(*a,zz),(*b,zz),C.R_CW,sides=6,mat=0)
    ln=float(np.linalg.norm(b-a));sag=C.SAG_44*(ln/44)**2 if i<len(pts)-2 else 0
    path=[]
    for f in np.linspace(0,1,max(3,int(ln/2.0)+1)):
     q=a+(b-a)*f;path.append(Vector((*q,ms0-4*sag*f*(1-f))))
    C.L.tube(P.mb['wire'],path,C.R_MS,sides=6,mat=1,smooth=True)
    for s in np.arange(3,ln-2,5):
     f=s/ln;q=a+(b-a)*f;C.tube(P.mb['dropper'],(*q,zz+C.R_CW),(*q,ms0-4*sag*f*(1-f)-C.R_MS),.0045,sides=4);drop_count+=1
    wire_records.append({'track':k,'start_xy':a.tolist(),'end_xy':b.tolist(),'contact_z':zz,'max_chain_offset_m':worst,'join_to_inherited':i==0})
   for x,p in zip(track_rows,pts[1:-1]):
    n=t.N(x);off=float((p-t.P(x))@n);pull=n*(1 if off>=0 else -1);angle=t.ang(x)
    # The staggered contact's normal offset has a small X component. A short
    # mounting saddle connects its hanger back to the transverse beam plane.
    q=p+.95*pull
    for r in [p,q]:C.tube(P.mb['beam'],(x,float(r[1]),12.45),(*r,12.45),.035,sides=8)
    C.support_fittings(P,p,pull,zz,ms0,12.45,'beam',track_dir=(math.cos(angle),math.sin(angle)))
    supports.setdefault(k,[]).append({'row_x':x,'contact_xy':p.tolist(),'messenger_z':ms0,'beam_z':12.45})
   H.count('reconnected_surface_tracks');H.count('new_droppers',drop_count)
 materials={'wire':['V6 | OCS contact wire (hard-drawn copper)','V6 | OCS messenger (stranded steel)'],'dropper':['V6 | OCS dropper (bronze)'],'mast':['V6 | OCS steel mast (grey paint)'],'beam':['V6 | OCS galvanised steel'],'fitting':['V6 | OCS fittings (bronze / steel)'],'insulator':['V6 | OCS insulator (glazed porcelain)']}
 for key,mb in P.mb.items():
  o=mb.build('V14 south OCS '+key,H.col('Catenary_South'),[bpy.data.materials[n] for n in materials[key]]);o['V14_kind']='catenary_'+key
 H.build(extra,'south mast plinths and bonding straps','Catenary_South','mast_fittings')
 H.R['catenary']={'removed_components':removed,'old_masts_replaced':len(old_masts),'old_mast_xy':[np.round(p,4).tolist() for p in old_masts],'new_masts':mast_records,'rows':records,'supports':supports,'contact_spans':wire_records,'unchanged_scope':'Chuo, central and north conventional supports, all Shinkansen supports and all canopy penetrations','all_masts_survey_verified':False,'source':'GSI seamlessphoto z18 tiles, origin (232844,103223), existing georef shifted (-512,-768); cross-check pelican 2020-10-25 overhead photo','method':'Digitized visible beam chainage; independent groups; lateral fit to inherited rail centerlines. Not a surveyed mast-base map.'}
 H.count('south_portal_rows',len(records));H.count('south_new_masts',len(mast_records));H.count('south_old_masts_replaced',len(old_masts))

from mathutils import Vector
