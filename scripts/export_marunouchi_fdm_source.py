"""Read-only extraction of visible Marunouchi architecture from V22.

Run in Blender: blender -b source.blend --python this_file -- output_directory
World metres become millimetres at 1:1000; no source scene is saved or modified.
"""
import bpy, json, sys
import numpy as np
from pathlib import Path

out=Path(sys.argv[sys.argv.index('--')+1]);out.mkdir(parents=True,exist_ok=True)
prefixes=('V3 01','V3 02','V3 03','V4_Architecture','V5_Architecture_DomeRoofs',
          'V16_','V17_','V11_Facade_Details','V13_Imperial_Architecture','V13_Imperial_Gate')
scene=bpy.data.scenes['Tokyo Station'];bpy.context.window.scene=scene
selected={}
def walk(c,hidden=False):
    hidden=hidden or c.hide_render
    if not hidden and c.name.startswith(prefixes):
        for o in c.objects:
            if not o.hide_render and o.type in ('MESH','CURVE','FONT'):
                selected.setdefault(o.name,{'o':o,'collections':[]})['collections'].append(c.name)
    for cc in c.children:walk(cc,hidden)
walk(scene.collection)
deps=bpy.context.evaluated_depsgraph_get()
verts=[];faces=[];rows=[];nv=0;nf=0
for i,(name,item) in enumerate(sorted(selected.items())):
    o=item['o'];ev=o.evaluated_get(deps);me=ev.to_mesh()
    if not me or not len(me.polygons):
        if me:ev.to_mesh_clear()
        continue
    me.calc_loop_triangles()
    v=np.empty(len(me.vertices)*3,dtype=np.float32);me.vertices.foreach_get('co',v);v=v.reshape(-1,3)
    mat=np.array(o.matrix_world,dtype=np.float64)
    v=(v@mat[:3,:3].T+mat[:3,3]).astype(np.float32)
    f=np.empty(len(me.loop_triangles)*3,dtype=np.int32);me.loop_triangles.foreach_get('vertices',f);f=f.reshape(-1,3)
    rows.append({'name':name,'collections':item['collections'],'vstart':nv,'vcount':len(v),'fstart':nf,'fcount':len(f),'lo':v.min(0).tolist(),'hi':v.max(0).tolist(),'matrix':mat.tolist(),'materials':[m.name if m else '' for m in me.materials]})
    verts.append(v);faces.append(f+nv);nv+=len(v);nf+=len(f)
    ev.to_mesh_clear()
    if i%2000==0:print('EXTRACT',i,'of',len(selected),flush=True)
np.savez_compressed(out/'source_geometry.npz',vertices=np.concatenate(verts),faces=np.concatenate(faces))
(out/'source_objects.json').write_text(json.dumps({'source':bpy.data.filepath,'scale':1000,'units':'millimeter','objects':rows},ensure_ascii=False,indent=2),encoding='utf8')
print('EXTRACT_DONE',len(rows),nv,nf,flush=True)
