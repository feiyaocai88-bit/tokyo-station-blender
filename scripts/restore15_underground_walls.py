"""Restore V14 wall enclosures to the main scene and save to a new file."""
import bpy,sys,json,os
args=sys.argv[sys.argv.index('--')+1:]
if not args:raise RuntimeError('Provide a different output .blend path')
out=os.path.abspath(args[0])
if os.path.normcase(out)==os.path.normcase(os.path.abspath(bpy.data.filepath)):raise RuntimeError('Keep the cutaway file: save restoration to a different path')
sc=bpy.data.scenes['Tokyo Station'];r=json.loads(sc['V15_refinement'])
if sc.get('V15_walls_restored'):raise RuntimeError('Walls already restored')
hidden=bpy.data.collections['V15_Replaced_hidden']
for rec in r['retained']:
    q=bpy.data.objects.get(rec['original']);o=bpy.data.objects[rec['retained']]
    if q:
        q.name=rec['original']+' [V15 open version]';q.hide_render=True;q.hide_viewport=True
    if o.name in hidden.objects:hidden.objects.unlink(o)
    o.name=rec['original'];o.hide_render=False;o.hide_viewport=False
    for link in rec['links']:
        c=bpy.data.scenes[link['scene']].collection if 'scene' in link else bpy.data.collections[link['collection']]
        if o.name not in c.objects:c.objects.link(o)
sc['V15_walls_restored']=True;sc['last_stage']='V15 with original V14 wall enclosures restored'
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=out,compress=True)
print('V15_WALLS_RESTORED',out,flush=True)
