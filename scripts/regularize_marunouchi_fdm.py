"""Remove sub-print-resolution coincident boolean seams with a 0.12 mm VDB pass.

Run in a clean background Blender instance on the generated print mesh, not on
the source station. Final validation/export is performed separately.
"""
import bpy,sys,time
import numpy as np
from pathlib import Path
out=Path(sys.argv[sys.argv.index('--')+1]).resolve();d=np.load(out/'print_mesh.npz')
bpy.ops.wm.read_factory_settings(use_empty=True)
me=bpy.data.meshes.new('Union before seam regularization');me.from_pydata(d['vertices'].tolist(),[],d['faces'].tolist());me.update()
o=bpy.data.objects.new('Marunouchi print regularization',me);bpy.context.scene.collection.objects.link(o)
bpy.context.view_layer.objects.active=o;o.select_set(True)
m=o.modifiers.new('0.12 mm print seam regularization','REMESH');m.mode='VOXEL';m.voxel_size=.12;m.adaptivity=.1
t=time.time();print('REGULARIZE_START',len(me.polygons),flush=True)
bpy.ops.object.modifier_apply(modifier=m.name)
print('REGULARIZE_DONE',len(o.data.polygons),round(time.time()-t,1),flush=True)
# VDB adaptivity collapses near-planar regions during meshing, avoiding a costly
# separate dissolve pass over millions of base-plane faces.
me=o.data;me.calc_loop_triangles()
v=np.empty(len(me.vertices)*3,dtype=np.float32);me.vertices.foreach_get('co',v)
f=np.empty(len(me.loop_triangles)*3,dtype=np.int32);me.loop_triangles.foreach_get('vertices',f)
np.savez_compressed(out/'regularized_mesh.npz',vertices=v.reshape(-1,3),faces=f.reshape(-1,3))
print('REGULARIZE_EXPORTED',len(me.vertices),len(me.loop_triangles),flush=True)
