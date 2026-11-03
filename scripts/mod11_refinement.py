"""Apply V11 to the V10 deliverable. Blender --background V10.blend -P this.py -- output.blend report.json [baseline.json]."""
import bpy,os,sys,json,hashlib,numpy as np
sys.path.insert(0,os.path.dirname(__file__))
import v11lib as H
import mod11_surface as surface
import mod11_rollingstock as rollingstock
import mod11_marunouchi as metro

def fingerprint():
    records={};cache={}
    for o in bpy.data.objects:
        r={'type':o.type,'basis':[list(v) for v in o.matrix_basis],'parent_inverse':[list(v) for v in o.matrix_parent_inverse], 'parent':o.parent.name if o.parent else None}
        if o.type=='MESH':
            me=o.data
            if me.name not in cache:
                hh=hashlib.sha256()
                for seq,prop,size,dtype in [(me.vertices,'co',3,np.float32),(me.edges,'vertices',2,np.int32),(me.loops,'vertex_index',1,np.int32),(me.polygons,'loop_total',1,np.int32),(me.polygons,'material_index',1,np.int32)]:
                    a=np.empty(len(seq)*size,dtype=dtype);seq.foreach_get(prop,a);hh.update(a.tobytes())
                hh.update(json.dumps([m.name if m else None for m in me.materials]).encode());cache[me.name]=hh.hexdigest()
            r['geometry']=cache[me.name]
        records[o.name]=r
    return records

def cameras():
    H.camera('01 Marunouchi plaza',(-219,-285,163),(0,3,5),46)
    H.camera('02 differentiated roofs',(273,294,202),(5,87,8),47)
    H.camera('03 plaza ventilation',(-100,-135,22),(-57,-79,2.8),45)
    y=float(H.yc('09-10',-91))
    H.camera('04 paired platform columns',(-91,y,7.95),(-60,float(H.yc('09-10',-60)),7.9),29)
    y=float(H.ty('05',-100))
    H.camera('05 platform open underside',(-103,y+.05,5.5),(-86,float(H.ty('05',-86))+1.75,5.8),38)
    H.camera('06 utility enclosure',(-185,-79,27),(-143,-33,7),42)
    H.camera('07 station facade',(-70,-52,14),(-58,-5,10),48)
    H.camera('08 JR rolling stock',(-88,48.8,11.4),(-64,52,7.9),45)
    H.camera('09 rooftop services',(197,224,69),(76,136,14),55)

def main():
    sc=H.SC
    if sc.get('V11_refinement'):raise RuntimeError('Open the V10 input, not an already modified V11 file.')
    args=sys.argv[sys.argv.index('--')+1:]
    if len(args)>2:json.dump(fingerprint(),open(args[2],'w',encoding='utf8'),separators=(',',':'))
    H.setup();surface.run();rollingstock.run();metro.run();cameras()
    H.REPORT['approximations']=[
        'Photo-referenced interpretation, not a measured survey or a single-date digital twin.',
        'Platform column group selection, roof dimensions, heritage column positions and utility enclosure dimensions are inferred from photographs and the existing diorama.',
        'Google panorama: Ito Imaji, March 2018; older April 2015 Google imagery used only for street-side context, not current plaza paving.',
        'Metro topology follows Tokyo Metro April 2026 diagram; bearing follows existing model with approximately 7.35 m westward adjustment to clear inherited Sobu end walls; station extents and depths are estimated.',
        'JR transfer branches are schematic stubs, not a complete underground route survey.',
        'Vehicle details are a native-mesh visual interpretation; small mechanical assemblies and train dimensions are simplified.'
    ]
    H.REPORT['new_mesh_objects']=sum(o.type=='MESH' and o.name.startswith('V11 ') for o in bpy.data.objects)
    sc['V11_refinement']=json.dumps(H.REPORT,ensure_ascii=False)
    sc['V11_accuracy']='Photo-referenced interpretation. See sources_and_licenses/detail_refinement_v11.json and README_V11.txt.'
    guide=os.path.join(os.path.dirname(H.HERE),'README_V11.txt')
    if os.path.isfile(guide):
        tx=bpy.data.texts.get('README_V11_中文') or bpy.data.texts.new('README_V11_中文');tx.clear();tx.write(open(guide,encoding='utf8').read())
    sc.camera=bpy.data.objects['V11 01 Marunouchi plaza']
    bpy.context.view_layer.update();bpy.ops.file.pack_all();bpy.context.preferences.filepaths.save_version=0
    out=os.path.abspath(args[0]);os.makedirs(os.path.dirname(out),exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=out,compress=True)
    if len(args)>1:json.dump(H.REPORT,open(args[1],'w',encoding='utf8'),ensure_ascii=False,indent=2)
    print('V11_BUILD_OK',out,json.dumps(H.REPORT['counts']),flush=True)

if __name__=='__main__':main()
