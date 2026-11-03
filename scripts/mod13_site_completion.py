"""V13 on final V12: site/railway corrections and ground-to-Metro access.
blender -b V12.blend --python-exit-code 1 -P this.py -- V13.blend build.json baseline.json
"""
import bpy,bmesh,sys,os,json
sys.path.insert(0,os.path.dirname(__file__))
import v13lib as H
import mod13_railway as railway
import mod13_entrance as entrance
import mod13_metro_access as metro
from mod12_surface_trains import fingerprint
MAIN=bpy.context.scene

def access_labels(sc,cam):
    ink=bpy.data.materials.get('V13 | diagram_ink') or H.material('diagram_ink',(.035,.09,.15),1)
    bsdf=ink.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Emission Color'].default_value=(.035,.09,.15,1);bsdf.inputs['Emission Strength'].default_value=.5
    font=next((f for f in bpy.data.fonts if 'NotoSansJP' in f.name),None)
    for label,pos in [('M8  GROUND',(-145,-102,4.5)),('M7  GROUND',(-33,-145,4.5)),('B1  CONCOURSE',(3,-145,-.8)),('B2  MARUNOUCHI LINE',(38,-144,-5))]:
        d=bpy.data.curves.new('V13 cutaway label '+label,'FONT');d.body=label;d.size=3;d.align_x='CENTER';d.align_y='CENTER';d.resolution_u=3
        if font:d.font=font
        d.materials.append(ink);o=bpy.data.objects.new(d.name,d);sc.collection.objects.link(o);o.location=pos;o.rotation_euler=cam.rotation_euler


def studies():
    H.camera('01 central imperial entrance',(0,-64,14.0),(0,-8.5,10.5),40)
    H.camera('02 imperial gate and round piers',(1.5,-20,3.8),(0,-7,3.0),44)
    H.camera('03 north service alley',(-212,51,33),(-165,17,9),52)
    H.camera('04 corrected Chuo screen ends',(192,-12,47),(94,31,15),48)
    H.camera('05 track fastenings and ballast',(191,float(H.ty('09',184))-4,9),(184,float(H.ty('09',184)),5.15),44)
    H.camera('06 M8 ground entrance',(-157,-106,9),(-139,-94,.25),42)
    H.camera('07 M7 ground entrance',(-47,-151,8),(-29,-139,.4),43)
    H.camera('08 M8 stairs to B1',(-144.2,-94,3.0),(-137.5,-94,-4.0),21)
    H.camera('09 service tower end grilles',(-196,30,21),(-179.5,17,12.6),55)
    H.camera('10 roofscape and catenary',(250,281,181),(0,96,12),49)
    sc=bpy.data.scenes.new('V13 Metro access cutaway');sc.world=MAIN.world.copy();sc.view_settings.view_transform=MAIN.view_settings.view_transform
    # Access geometry and the original B1/B2 station share unchanged transforms.
    for c in bpy.data.collections:
        if c.name.startswith('V13_Metro_Access_Detail'):
            for o in c.objects:
                if 'B1 passage lighting and guidance' in o.name:
                    q=o.copy();q.data=o.data.copy();q.name=o.name+' cutaway floor guidance';sc.collection.objects.link(q)
                    bm=bmesh.new();bm.from_mesh(q.data)
                    bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.calc_center_median().z>-3],context='FACES')
                    bm.to_mesh(q.data);bm.free()
                else:sc.collection.objects.link(o)
        elif c.name.startswith(('V13_Metro_Entrances','V13_Metro_Access_Floor','V13_Metro_Access_Lights')):
            sc.collection.children.link(c)
        elif c.name.startswith('V11_Metro_') and not any(t in c.name for t in ['Work','Walls','Ceiling','Review','Replaced']):
            if 'Concourse' in c.name:
                for o in c.objects:
                    if 'light panels' not in o.name:sc.collection.objects.link(o)
            else:sc.collection.children.link(c)
    # Preserve B1 slabs, omit roof slabs, so the stair connections can be inspected.
    src=bpy.data.objects.get('V11 M17 B1 slab and B2 ceilings with stair openings')
    if src:
        q=src.copy();q.data=src.data.copy();q.name='V13 cutaway B1 floor with original openings';sc.collection.objects.link(q)
        bm=bmesh.new();bm.from_mesh(q.data);fs=[f for f in bm.faces if f.calc_center_median().z < -6.18]
        bmesh.ops.delete(bm,geom=fs,context='FACES');bm.to_mesh(q.data);bm.free()
    for o in MAIN.objects:
        if o.type=='LIGHT' and o.data.type=='SUN':sc.collection.objects.link(o)
    # Low section walls make the turning passage legible without hiding the path.
    walls=H.L.MeshBuilder()
    for e in H.R['entrances']:
        for a,b in zip(e['passage_waypoints'][:-1],e['passage_waypoints'][1:]):
            from mathutils import Vector
            import math
            d=Vector((b[0]-a[0],b[1]-a[1],0));n=Vector((-d.y,d.x,0)).normalized()*1.78
            for sign in (-1,1):H.beam(walls,(a[0]+sign*n.x,a[1]+sign*n.y,-5.37),(b[0]+sign*n.x,b[1]+sign*n.y,-5.37),.18,.8,'metro_tile')
    walls.build('V13 access cutaway low walls',sc.collection,H.M)
    cam=H.camera('11 continuous Metro access cutaway',(-175,-285,155),(-47,-121,-4),49,ortho=210,scene=sc)
    access_labels(sc,cam)
    H.camera('12 Metro B1 entrance connection',(-80,-137.68,-4.15),(-52,-134,-4.15),24)
    H.R['review_cameras']=[o.name for o in bpy.data.objects if o.type=='CAMERA' and o.get('V13_scene')]
    MAIN.camera=bpy.data.objects['V13 01 central imperial entrance']
    sc.camera=bpy.data.objects['V13 11 continuous Metro access cutaway']

def main():
    if MAIN.get('V13_refinement'):raise RuntimeError('Start with the final V12 deliverable.')
    args=sys.argv[sys.argv.index('--')+1:]
    if len(args)>2:json.dump(fingerprint(),open(args[2],'w',encoding='utf8'),separators=(',',':'))
    H.setup();railway.run();print('V13_RAILWAY_OK',flush=True)
    entrance.run();print('V13_ENTRANCE_OK',flush=True)
    metro.run();print('V13_METRO_OK',flush=True);studies()
    H.R['limitations']=['Photographic interpretation, not a measured or single-date reconstruction.','Mast coordinates remain inherited obstacle-adjusted procedural locations, explicitly audited as unmeasured.','Metro M7/M8 topology connects to the inherited shifted B1 frame; passage lengths and surface positions are approximate.','Building-integrated M9/M10 exits beyond this station/plaza scope are not rebuilt.','V12 surface trains and all original source geometry are retained.']
    MAIN['V13_refinement']=json.dumps(H.R,ensure_ascii=False);MAIN['V13_accuracy']='See README_V13.txt and sources_and_licenses/site_completion_v13.json. Mast positions and exit dimensions are not surveyed.'
    # Stale V3 metadata said there was no underground station despite V9/V11.
    MAIN['limitations']='Interpretive multi-epoch diorama. Includes JR Sobu/Yokosuka and Metro Marunouchi underground stations; utility, mast and passage positions are approximate.'
    MAIN['last_stage']='V13 site corrections and connected Metro access, 2026-11-03'
    guide=os.path.join(os.path.dirname(__file__),'..','README_V13.txt')
    if os.path.isfile(guide):tx=bpy.data.texts.new('README_V13_中文');tx.write(open(guide,encoding='utf8').read())
    bpy.context.view_layer.update();bpy.ops.file.pack_all();bpy.context.preferences.filepaths.save_version=0
    out=os.path.abspath(args[0]);os.makedirs(os.path.dirname(out),exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=out,compress=True)
    json.dump(H.R,open(args[1],'w',encoding='utf8'),ensure_ascii=False,indent=2)
    print('V13_BUILD_OK',H.R['counts'],flush=True)
if __name__=='__main__':main()
