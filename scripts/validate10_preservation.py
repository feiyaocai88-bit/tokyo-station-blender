"""Fingerprint source geometry, then compare the revision.

Run with the source open: -- snapshot baseline.json
Run with the candidate open: -- compare baseline.json report.json
Stored basis and parent-inverse transforms are compared. matrix_world is a
dependency-graph cache and resets for hidden objects after reopening a .blend.
"""
import bpy, sys, json, hashlib, numpy as np
args=sys.argv[sys.argv.index('--')+1:]
cache={}; records={}
def mesh_hash(me):
 if me.name in cache:return cache[me.name]
 h=hashlib.sha256()
 for seq,prop,size,dtype in ((me.vertices,'co',3,np.float32),(me.edges,'vertices',2,np.int32),(me.loops,'vertex_index',1,np.int32),(me.polygons,'loop_total',1,np.int32),(me.polygons,'material_index',1,np.int32)):
  a=np.empty(len(seq)*size,dtype=dtype);seq.foreach_get(prop,a);h.update(a.tobytes())
 h.update(json.dumps([m.name if m else None for m in me.materials]).encode())
 cache[me.name]=h.hexdigest();return cache[me.name]
for o in bpy.data.objects:
 if o.name.startswith('V10 '):continue
 record={'type':o.type,'basis':[list(r) for r in o.matrix_basis],'parent_inverse':[list(r) for r in o.matrix_parent_inverse],'parent':o.parent.name if o.parent else None,'data':o.data.name if o.data else None}
 if o.type=='MESH':record['geometry']=mesh_hash(o.data)
 records[o.name]=record
if args[0]=='snapshot':
 json.dump(records,open(args[1],'w'),separators=(',',':'));print('SNAPSHOT',len(records),len(cache),flush=True)
else:
 original=json.load(open(args[1]));missing=[];changed=[]
 for n,r in original.items():
  if n not in records:missing.append(n)
  elif records[n]!=r:changed.append(n)
 diffs={n:{k:[original[n][k],records[n].get(k)] for k in original[n] if original[n][k]!=records[n].get(k)} for n in changed}
 result={'original_objects':len(original),'original_mesh_datablocks':len(cache),'missing_original_objects':missing,'changed_original_geometry_or_transforms':changed,'diffs':diffs,'pass':not missing and not changed}
 json.dump(result,open(args[2],'w'),indent=2);print(json.dumps(result),flush=True)
 if not result['pass']:raise AssertionError('Original geometry changed')
