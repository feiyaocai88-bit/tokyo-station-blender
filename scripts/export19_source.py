import bpy,sys,json,os,numpy as np
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
from v14lib import component_labels
sc=bpy.data.scenes['Tokyo Station'];bpy.context.window.scene=sc;out={}
names=['V4 unified perimeter and transport road','V4 Architecture adjacent opaque concourse roof','V4_Structure_Segmented_ground_concourse_shells','V14 south curved road sidewalk and raised curbs']
for name in names:
 o=bpy.data.objects.get(name)
 if not o:continue
 vs,labs,_,_=component_labels(o);rows=[]
 for i in np.unique(labs):
  p=vs[labs==i];rows.append({'lo':p.min(0).tolist(),'hi':p.max(0).tolist(),'n':len(p)})
 out[name]={'components':rows,'vertices':vs.tolist(),'faces':[list(p.vertices) for p in o.data.polygons],'materials':[m.name if m else None for m in o.data.materials],'face_mats':[p.material_index for p in o.data.polygons]}
from mathutils.bvhtree import BVHTree
trees=[]
for o in sc.objects:
 if o.hide_render or o.type!='MESH' or not any(c.name=='V3 01 | Architecture and real openings' for c in o.users_collection):continue
 if not any(w in o.name.lower() for w in ['wall','pier']):continue
 trees.append(BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(p.vertices) for p in o.data.polygons]))
profile=[]
for x in np.arange(-166,181,.5):
 hits=[t.ray_cast(Vector((x,30,3.2)),Vector((0,-1,0)),45)[0] for t in trees];hits=[h.y for h in hits if h is not None]
 profile.append([float(x),max(hits) if hits else 8.4])
out['rear_profile']=profile
Path(sys.argv[sys.argv.index('--')+1]).write_text(json.dumps(out),encoding='utf8')
print('V19_SOURCE_EXPORTED',flush=True)
