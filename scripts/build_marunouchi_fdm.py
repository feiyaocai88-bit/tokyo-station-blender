"""Make the V22 Marunouchi exterior a single connected FDM solid at 1:1000.

Run with Python containing numpy/scipy/trimesh/manifold3d/shapely.
--source is produced by export_marunouchi_fdm_source.py. Source metres equal
output millimetres at this scale. Deliberate print adaptations are reported.
"""
import argparse,sys,json,re,time,math,zipfile
from pathlib import Path
import numpy as np
import trimesh
import manifold3d as mf
from shapely.geometry import MultiPoint,Polygon,LineString
from shapely.ops import unary_union

P=argparse.ArgumentParser();P.add_argument('--source',type=Path,required=True);P.add_argument('--out',type=Path,required=True)
A=P.parse_args();A.out.mkdir(parents=True,exist_ok=True)
D=np.load(A.source/'source_geometry.npz');V=D['vertices'].astype(float);F=D['faces']
META=json.loads((A.source/'source_objects.json').read_text(encoding='utf8'));rows=META['objects']
R={'scale':'1:1000','units':'mm','source_blend':META['source'],'base_thickness_mm':4.0,
   'target_nozzle_mm':0.4,'relief_min_width_target_mm':0.45,'support_column_min_mm':1.0,
   'counts':{},'skipped_objects':[],'repair_hulls':[],'failed_components':[],
   'adaptations':['Remove underground, tracks, trains and plaza outside the station footprint.',
     'Fill inaccessible building interiors and seal glazing as recessed facade relief.',
     'Thicken relief, entrance canopy plates, columns and slender finials for 0.4 mm FDM.',
     'Keep both domes, central entrance, continuous roof runs and the angled south wing.',
     'Fuse architecture to a 4 mm footprint-following base; do not change the V22 source.']}
def count(k,n=1):R['counts'][k]=R['counts'].get(k,0)+n
def raw(row):
    vs=row['vstart'];fs=row['fstart']
    return V[vs:vs+row['vcount']].copy(),F[fs:fs+row['fcount']]-vs
def hull2(v):return MultiPoint(v[:,:2]).convex_hull
def cross(poly):
    if poly.is_empty:return mf.CrossSection()
    if poly.geom_type=='MultiPolygon':return mf.CrossSection.batch_boolean([cross(p) for p in poly.geoms],mf.OpType.Add)
    return mf.CrossSection([np.asarray(poly.exterior.coords)[:-1]]+[np.asarray(r.coords)[:-1] for r in poly.interiors],mf.FillRule.EvenOdd)
def prism(poly,z0,z1):return mf.Manifold.extrude(cross(poly),z1-z0).translate((0,0,z0))
def cube(lo,hi):return mf.Manifold.cube(np.asarray(hi)-lo).translate(lo)
def manifold(mesh):
    mesh.remove_unreferenced_vertices()
    mesh.fix_normals(multibody=True)
    return mf.Manifold(mf.Mesh(np.asarray(mesh.vertices,dtype=np.float32),np.asarray(mesh.faces,dtype=np.uint32)))
def valid(m):return m.status()==mf.Error.NoError and not m.is_empty()

solids=[];foot=[];cores=[]
# Interior cores use the inherited floor polygons. Insets retain recesses in the
# exterior facade instead of burying the entire window surround in a new block.
for row in rows:
    n=row['name']
    if n.endswith('interior floor'):
        v,f=raw(row);poly=hull2(v);foot.append(poly)
        top=20.85 if 'flanking tower' in n else 17.45
        inner=poly.buffer(-.55,join_style=2)
        core=prism(inner,-.3,top);cores.append(core);count('inset_floor_cores')
for tag,cx in [('NORTH',-104.),('SOUTH',107.)]:
    vv=np.concatenate([raw(r)[0] for r in rows if r['name'].startswith(tag+' dome facet') and r['hi'][2]<18])
    poly=hull2(vv);foot.append(poly);cores.append(prism(poly.buffer(-.55,join_style=2),-.3,17.5))
    # The octagonal upper drum stays recessed behind its window and cornice rows.
    ang=np.arange(8)*math.pi/4+math.pi/8
    drum=Polygon(np.c_[cx+8.72/math.cos(math.pi/8)*np.cos(ang),.415+8.72/math.cos(math.pi/8)*np.sin(ang)])
    cores.append(prism(drum,17.1,26.95))
    # A solid convex octagonal dome has the exact original curved exterior.
    row=next(r for r in rows if r['name']==f'V5 {tag} dome curved octagonal slate shell')
    cores.append(mf.Manifold.hull_points(raw(row)[0]));count('solid_domes')
    # Reinforce the long spire from inside the original turned ornaments.
    for z0,z1,r0,r1 in [(34.5,36.2,.75,.68),(36.1,42.0,.65,.60),(41.9,46.1,.60,.40)]:
        cores.append(mf.Manifold.cylinder(z1-z0,r0,r1,24).translate((cx,.415,z0)))
    count('reinforced_spires')
central=Polygon([(-6,-5.20),(6,-5.20),(6,6.8),(-6,6.8)])
cores.append(prism(central,-.3,19.45));foot.append(central)
for row in rows:
    if 'connecting storey slabs' in row['name']:
        poly=hull2(raw(row)[0]);foot.append(poly);cores.append(prism(poly.buffer(-.15,join_style=2),-.3,17.4))
    if 'folded entrance canopy' in row['name'] or row['name']=='V13 Imperial round brick piers stone belts and recessed doorway':
        foot.append(hull2(raw(row)[0]))
solids.extend(cores)

def thicken(vertices,row):
    # Most inherited items are transformed primitive boxes. Work in their own
    # frame, so diagonal facade details are thickened across, not across the site.
    mat=np.asarray(row['matrix']);rot=mat[:3,:3].copy()
    lens=np.linalg.norm(rot,axis=0);rot=rot/np.where(lens>1e-8,lens,1)
    v=vertices@rot;lo=v.min(0);hi=v.max(0);s=hi-lo;cen=(lo+hi)*.5
    n=row['name'].lower()
    minimum=.45
    if 'column' in n and 'canopy' in n:minimum=1.0
    if 'balustrade' in n or 'baluster' in n or 'finial' in n:minimum=.8
    target=np.maximum(s,minimum)
    # Remove paper-thin glazing; the solid core supplies a recessed back face.
    # Broaden mullions in depth so they overlap that core instead of floating.
    if any(k in n for k in ('mullion','transom','sash')):target=np.maximum(s,.65)
    if np.any(s<minimum):
        safe=np.maximum(s,1e-8)
        v=(v-cen)*(target/safe)+cen
        count('thickened_components')
    return v@rot.T

start=time.time()
for index,row in enumerate(rows):
    n=row['name'];nl=n.lower()
    if any(k in nl for k in ('recessed glazing','room back','partial curtain','interior floor','finer sash','fine iron balcony scrollwork','frieze medallions','glazing seals')) or 'curved octagonal slate shell' in nl:
        R['skipped_objects'].append(n);continue
    v,f=raw(row)
    mesh=trimesh.Trimesh(v,f,process=True)
    mesh.update_faces(mesh.nondegenerate_faces());mesh.update_faces(mesh.unique_faces());mesh.remove_unreferenced_vertices()
    if not len(mesh.faces):continue
    parts=[mesh] if len(mesh.faces)<=12 else mesh.split(only_watertight=False,repair=False)
    for part in parts:
        if len(part.vertices)<3:continue
        dims=part.extents
        # Tiny detached carving becomes visual noise at this scale. Long
        # mouldings and major decorative silhouettes remain and are reinforced.
        if max(dims)<.48:count('subresolution_ornaments_removed');continue
        if np.count_nonzero(dims>.18)<2 and max(dims)<1.0:
            count('subresolution_ornaments_removed');continue
        if part.is_watertight:
            part.vertices=thicken(part.vertices,row)
            obj=manifold(part)
        else:
            # Close a surface component independently. Convex closure is used
            # only within that component, never across the complete building.
            vs=part.vertices.copy()
            _,ss,basis=np.linalg.svd(vs-vs.mean(0),full_matrices=False)
            if ss[-1]<1e-5:
                normal=basis[-1];th=.8 if 'canopy' in nl else .5
                vs=np.concatenate([vs+normal*th*.5,vs-normal*th*.5])
            obj=mf.Manifold.hull_points(vs)
            count('surface_components_closed')
            if len(R['repair_hulls'])<80:R['repair_hulls'].append({'name':n,'vertices':len(vs),'extent':dims.tolist()})
        if not valid(obj):
            # The render model has duplicated caps in some ornaments. A local
            # convex fallback repairs those without an approximate global remesh.
            obj=mf.Manifold.hull_points(part.vertices)
            if not valid(obj):R['failed_components'].append({'name':n,'extent':dims.tolist()});continue
            count('invalid_caps_repaired')
        solids.append(obj);count('source_components_used')
    if index%1500==0:print('CONVERT',index,'solids',len(solids),'seconds',round(time.time()-start,1),flush=True)

# A shallow continuous base follows the footprint, including entrances, and is
# rounded at outer corners. It is not the very wide rectangular site slab.
outline=unary_union(foot).buffer(3.8,join_style=1,quad_segs=4)
if outline.geom_type!='Polygon':raise RuntimeError('Footprint must be one connected polygon')
outline=Polygon(outline.exterior).simplify(.025,preserve_topology=True)
base=prism(outline,-4.,.08)
solids.append(base)
key_plan=Polygon([(-5,-4),(-5,4),(0,2.5),(5,4),(5,-4),(0,-2.5)])
key_plan=key_plan.buffer(-.30,join_style=1,quad_segs=3).buffer(.30,join_style=1,quad_segs=3)
socket_plan=key_plan.buffer(.25,join_style=1,quad_segs=3)
ports=[];socket_cutters=[]
for side,normal,angle in [('plaza',-1,-90),('railway',1,90)]:
    for number,x in enumerate((-75.,75.),1):
        section=outline.intersection(LineString([(x,-100),(x,100)]))
        y=section.bounds[1] if normal<0 else section.bounds[3]
        center=(x,y+normal*.15)
        socket_cutters.append(prism(socket_plan,-4.2,-1.75).rotate((0,0,angle)).translate((*center,0)))
        ports.append({'id':('P' if side=='plaza' else 'R')+str(number),'neighbor':side,'source_boundary_xy_m':[x,y],'source_key_center_xy_m':list(center),'outward_normal_xy':[0,normal],'key_rotation_degrees':angle})
R['assembly']={'interface':'tokyo-fdm-v1','base_thickness_mm':4.,'nominal_seam_gap_mm':.30,'key_plan_max_mm':[10.,8.],'key_height_mm':1.9,'socket_depth_mm':2.25,'socket_side_clearance_mm':.25,'key_installation':'Insert from underside across matching module sockets; optional glue for handling. No snap latch.','ports':ports,'source_base_outline_xy_m':np.asarray(outline.exterior.coords).tolist()}
print('UNION_INPUT',len(solids),flush=True)
# Batches keep the peak memory and boolean complexity bounded.
reduced=[]
for i in range(0,len(solids),500):
    q=mf.Manifold.batch_boolean(solids[i:i+500],mf.OpType.Add)
    if not valid(q):raise RuntimeError('Invalid batch '+str(i))
    reduced.append(q);print('UNION_BATCH',i,'triangles',q.num_tri(),flush=True)
body=mf.Manifold.batch_boolean(reduced,mf.OpType.Add)
if not valid(body):raise RuntimeError('Final union invalid')
# Local closure of the render-only masonry surfaces can fill the deep central
# niche. Restore that photographed recess and two legible window levels as
# deliberately reinforced relief, before final regularization.
arch=[(-2.68,7.82),(2.68,7.82),(2.68,19.1)]+[(2.68*math.cos(a),19.1+math.sin(a)) for a in np.linspace(0,math.pi,41)]+[(-2.68,7.82)]
# Extrusion initially follows Z; rotate its section from XY to XZ and run along Y.
cutter=mf.Manifold.extrude(mf.CrossSection([arch]),4.5).rotate((90,0,0)).translate((0,-5.35,0))
body=body-cutter
relief=[]
for z0,z1,half in [(8.15,11.70,1.0),(14.8,18.40,.925)]:
    body=body-cube((-half,-5.65,z0),(half,-4.75,z1))
    for x in (-half-.20,half+.20):relief.append(cube((x-.225,-5.90,z0-.18),(x+.225,-4.60,z1+.18)))
    for z in (z0-.1,z1+.1):relief.append(cube((-half-.4,-5.94,z-.18),(half+.4,-4.60,z+.18)))
    relief.append(cube((-.225,-5.70,z0),(.225,-4.60,z1)))
    zm=z0+(z1-z0)*.6;relief.append(cube((-half,-5.70,zm-.20),(half,-4.60,zm+.20)))
# A physical recessed circular attic window remains visible in the arched crown.
round_cut=mf.Manifold.cylinder(3.0,.55,.55,40).rotate((90,0,0)).translate((0,-7.3,23.25))
body=body-round_cut
body=mf.Manifold.batch_boolean([body,*relief],mf.OpType.Add)
count('central_niche_and_window_levels_restored')
body=mf.Manifold.batch_boolean([body,*socket_cutters],mf.OpType.Subtract)
count('underside_connector_sockets',len(socket_cutters))
print('UNION_DONE',body.num_tri(),flush=True)
parts=body.decompose();parts.sort(key=lambda q:q.volume(),reverse=True)
R['components_before_cleanup']=[{'volume':p.volume(),'bounds':p.bounding_box()} for p in parts]
# Only the base-connected largest body is printable as one part. Report any
# detached slivers; substantial detached components require explicit repair.
big=[p for p in parts[1:] if p.volume()>.75]
if big:
    print('DETACHED_SUBSTANTIAL',[(p.volume(),p.bounding_box()) for p in big],flush=True)
    connectors=[]
    for p in big:
        x0,y0,z0,x1,y1,z1=p.bounding_box()
        if z0>19 and z1<24 and max(x1-x0,y1-y0)<3:
            cx=(x0+x1)/2;cy=(y0+y1)/2
            connectors.append(cube((cx-.48,cy-.48,17.1),(cx+.48,cy+.48,z0+.5)))
            count('floating_chimneys_connected')
        else:raise RuntimeError('Substantial detached feature needs explicit repair')
    body=mf.Manifold.batch_boolean([body,*connectors],mf.OpType.Add)
    parts=body.decompose();parts.sort(key=lambda q:q.volume(),reverse=True)
R['detached_components_removed']=len(parts)-1
R['detached_volume_removed_mm3']=sum(p.volume() for p in parts[1:])
body=parts[0].simplify(.018).translate((0,0,4.0))
m=body.to_mesh64();mesh=trimesh.Trimesh(np.asarray(m.vert_properties)[:,:3],np.asarray(m.tri_verts),process=False)
mesh.fix_normals();lo,hi=mesh.bounds
mesh.apply_translation((-(lo[0]+hi[0])/2,-(lo[1]+hi[1])/2,-lo[2]))
R['source_to_print_translation_mm']=[float(-(lo[0]+hi[0])/2),float(-(lo[1]+hi[1])/2),4.0]
for port in R['assembly']['ports']:
    port['local_key_center_xy_mm']=[a+b for a,b in zip(port['source_key_center_xy_m'],R['source_to_print_translation_mm'][:2])]
np.savez_compressed(A.source/'union_debug.npz',vertices=mesh.vertices,faces=mesh.faces)
print('MESH_CHECK',mesh.is_watertight,mesh.is_winding_consistent,mesh.volume,body.status(),flush=True)
assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0
surface_parts=mesh.split(only_watertight=False,repair=False)
surface_parts.sort(key=lambda p:abs(p.volume),reverse=True)
R['zero_volume_boolean_slivers_removed']=len(surface_parts)-1
if any(abs(p.volume)>.001 for p in surface_parts[1:]):raise RuntimeError('Unexpected disconnected solid after simplification')
mesh=surface_parts[0]
assert mesh.is_watertight
R['model_dimensions_mm']=mesh.extents.tolist();R['triangles']=len(mesh.faces);R['vertices']=len(mesh.vertices)
R['watertight']=bool(mesh.is_watertight);R['consistent_winding']=bool(mesh.is_winding_consistent);R['connected_components']=1
R['solid_volume_mm3']=float(mesh.volume);R['bounds_mm']=mesh.bounds.tolist()
mesh.export(A.out/'Marunouchi_1-1000.stl')
np.savez_compressed(A.out/'print_mesh.npz',vertices=mesh.vertices,faces=mesh.faces)
# Find a rotation with clearance in the 300 x 320 common nozzle region. Use a
# five-millimetre border for the first-layer/brim allowance before placement.
best=None
for angle in np.arange(-90,90.01,.25):
    rad=math.radians(angle);rot=np.array([[math.cos(rad),-math.sin(rad)],[math.sin(rad),math.cos(rad)]])
    xy=mesh.vertices[:,:2]@rot.T;extent=xy.max(0)-xy.min(0)
    score=max(extent[0]/290,extent[1]/310)
    if best is None or score<best[0]:best=(score,float(angle),extent)
if best[0]>1:raise RuntimeError('Does not fit the H2C shared area with margin')
plate=mesh.copy();plate.apply_transform(trimesh.transformations.rotation_matrix(math.radians(best[1]),[0,0,1]))
cen=plate.bounds.mean(0);plate.apply_translation([175-cen[0],160-cen[1],0])
R['plate_rotation_degrees']=best[1];R['plate_dimensions_mm']=plate.extents.tolist();R['plate_bounds_mm']=plate.bounds.tolist()
R['H2C_common_xy_limits_mm']=[[25,0],[325,320]];R['minimum_xy_clearance_mm']=float(min(plate.bounds[0,0]-25,325-plate.bounds[1,0],plate.bounds[0,1],320-plate.bounds[1,1]))
# Standard 3MF, millimetres, one object; no machine start code or network action.
def save_3mf(path,mm):
    v=''.join(f'<vertex x="{x:.6f}" y="{y:.6f}" z="{z:.6f}"/>' for x,y,z in mm.vertices)
    t=''.join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a,b,c in mm.faces)
    xml='<?xml version="1.0" encoding="UTF-8"?><model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><metadata name="Title">Tokyo Station Marunouchi 1:1000 FDM</metadata><resources><object id="1" type="model" name="Marunouchi single connected solid"><mesh><vertices>'+v+'</vertices><triangles>'+t+'</triangles></mesh></object></resources><build><item objectid="1"/></build></model>'
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        z.writestr('[Content_Types].xml','<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        z.writestr('_rels/.rels','<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr('3D/3dmodel.model',xml)
save_3mf(A.out/'Marunouchi_H2C_1-1000.3mf',plate)
# A small pair of coupons contains the same underside sockets, plus one key.
# The coupon seam has the same 0.30 mm gap as future neighboring station tiles.
key=prism(key_plan,0,1.9)
def asmesh(s):
    sm=s.to_mesh64();return trimesh.Trimesh(np.asarray(sm.vert_properties)[:,:3],np.asarray(sm.tri_verts),process=True)
km=asmesh(key);assert km.is_watertight;km.export(A.out/'Connector_key.stl')
coupon_left=cube((-13,-7,0),(-.15,7,4))-prism(socket_plan,-.2,2.25)
coupon_right=cube((.15,-7,0),(13,7,4))-prism(socket_plan,-.2,2.25)
left=asmesh(coupon_left);right=asmesh(coupon_right);right.apply_translation((7,0,0))
test_key=km.copy();test_key.apply_translation((0,17,0))
coupons=trimesh.util.concatenate([left,right,test_key]);coupons.export(A.out/'Connector_fit_test.stl')
coupon_plate=coupons.copy();coupon_center=coupon_plate.bounds.mean(0)
coupon_plate.apply_translation((175-coupon_center[0],160-coupon_center[1],0))
save_3mf(A.out/'Connector_fit_test.3mf',coupon_plate)
(A.out/'assembly_interfaces.json').write_text(json.dumps({'coordinate_units':'millimeter at 1:1000','source_to_print_translation_mm':R['source_to_print_translation_mm'],**R['assembly']},ensure_ascii=False,indent=2),encoding='utf8')
R['elapsed_seconds']=time.time()-start
(A.out/'validation.json').write_text(json.dumps(R,ensure_ascii=False,indent=2),encoding='utf8')
print('PRINT_BUILD_DONE',json.dumps({k:v for k,v in R.items() if k not in ('skipped_objects','repair_hulls','components_before_cleanup','failed_components')},ensure_ascii=False),flush=True)
