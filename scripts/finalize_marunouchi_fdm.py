"""Flatten the base, validate serialized files and export the final FDM assets."""
import sys,json,math,zipfile,io
from pathlib import Path
import numpy as np
import trimesh
import manifold3d as mf
from scipy.spatial import ConvexHull

out=Path(sys.argv[1]).resolve()
R=json.loads((out/'validation.json').read_text(encoding='utf8'))
d=np.load(out/'regularized_mesh.npz')
mesh=trimesh.Trimesh(d['vertices'],d['faces'],process=True)
print('VOXEL_MESH',len(mesh.faces),mesh.is_watertight,flush=True)
parts=mesh.split(only_watertight=False,repair=False);parts.sort(key=lambda q:abs(q.volume),reverse=True)
R['regularization_detached_slivers_removed']=len(parts)-1
if any(abs(q.volume)>1. for q in parts[1:]):raise RuntimeError('Regularization detached a significant feature')
mesh=parts[0];mesh.fix_normals();assert mesh.is_watertight
# VDB's broad bottom face is planar; its numerical offset is below 1 micrometre.
# Keep its float32-safe topology instead of introducing tiny clipping triangles.
assert abs(mesh.bounds[0,2])<.001
mesh.vertices[:,2]-=mesh.bounds[0,2]
assert mesh.is_watertight and mesh.is_winding_consistent
assert len(mesh.split(only_watertight=False,repair=False))==1
assert abs(mesh.bounds[0,2])<1e-5
stl=mesh.export(file_type='stl')
back=trimesh.load(io.BytesIO(stl),file_type='stl',force='mesh',process=True)
np.savez_compressed(out/'serialized_check.npz',vertices=back.vertices,faces=back.faces)
print('STL_CHECK',back.is_watertight,back.is_winding_consistent,back.volume,flush=True)
assert back.is_watertight and back.is_winding_consistent and back.volume>0
assert len(back.split(only_watertight=False,repair=False))==1
(out/'Marunouchi_1-1000.stl').write_bytes(stl)
np.savez_compressed(out/'print_mesh.npz',vertices=back.vertices,faces=back.faces)
mesh=back
# Optimize on the planar convex hull, not on all vertices. The common nozzle
# rectangle starts at X=25, not at the left edge of the overall H2C build plate.
xy=mesh.vertices[:,:2];xy=xy[ConvexHull(xy).vertices]
best=None
for deg in np.arange(-90,90.001,.25):
    a=math.radians(deg);rot=np.array([[math.cos(a),-math.sin(a)],[math.sin(a),math.cos(a)]])
    p=xy@rot.T;ext=np.ptp(p,axis=0);score=max(ext[0]/290,ext[1]/310)
    if best is None or score<best[0]:best=(score,float(deg),ext)
assert best[0]<1
plate=mesh.copy();plate.apply_transform(trimesh.transformations.rotation_matrix(math.radians(best[1]),[0,0,1]))
cent=plate.bounds.mean(0);plate.apply_translation([175-cent[0],160-cent[1],0])
verts=''.join(f'<vertex x="{x:.6f}" y="{y:.6f}" z="{z:.6f}"/>' for x,y,z in plate.vertices)
tris=''.join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a,b,c in plate.faces)
xml='<?xml version="1.0" encoding="UTF-8"?><model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><metadata name="Title">Tokyo Station Marunouchi 1:1000 FDM</metadata><resources><object id="1" type="model" name="Marunouchi single connected solid"><mesh><vertices>'+verts+'</vertices><triangles>'+tris+'</triangles></mesh></object></resources><build><item objectid="1"/></build></model>'
with zipfile.ZipFile(out/'Marunouchi_H2C_1-1000.3mf','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    z.writestr('[Content_Types].xml','<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    z.writestr('_rels/.rels','<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    z.writestr('3D/3dmodel.model',xml)
R.update({'regularization_voxel_mm':.12,'final_simplification_tolerance_mm':0,'model_dimensions_mm':mesh.extents.tolist(),'triangles':len(mesh.faces),'vertices':len(mesh.vertices),'watertight':bool(mesh.is_watertight),'consistent_winding':bool(mesh.is_winding_consistent),'connected_components':1,'solid_volume_mm3':float(mesh.volume),'bounds_mm':mesh.bounds.tolist(),'plate_rotation_degrees':best[1],'plate_dimensions_mm':plate.extents.tolist(),'plate_bounds_mm':plate.bounds.tolist(),'stl_roundtrip_watertight':True,'stl_roundtrip_single_component':True,'flat_base_z_mm':0.0})
R['minimum_xy_clearance_mm']=float(min(plate.bounds[0,0]-25,325-plate.bounds[1,0],plate.bounds[0,1],320-plate.bounds[1,1]))
(out/'validation.json').write_text(json.dumps(R,ensure_ascii=False,indent=2),encoding='utf8')
print('FINAL_EXPORT_OK',json.dumps({k:R[k] for k in ('model_dimensions_mm','plate_dimensions_mm','plate_rotation_degrees','triangles','watertight','stl_roundtrip_watertight','minimum_xy_clearance_mm')}),flush=True)
