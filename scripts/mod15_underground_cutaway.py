"""V15 native open-side underground presentation on the complete V14 model.

blender -b V14.blend -P mod15_underground_cutaway.py -- V15.blend report.json baseline.json
Originals are retained; mixed meshes are copied and only wall components removed.
This works in Solid viewport mode, independently of the old V9 shader section cut.
"""
import bpy,bmesh,sys,os,json,numpy as np
from mathutils import Matrix,Vector
sys.path.insert(0,os.path.dirname(__file__))
from v14lib import component_labels,world
import v9geo as G
from mod11_marunouchi import F as MF
from mod12_surface_trains import fingerprint

R={'revision':15,'retained':[],'edits':[],'presentation':'Both underground stations have native open side enclosures in the main scene.'}
SF=G.frame_matrix()
JR='V9 Sobu | '
STRUCT=JR+'box structure (slabs, walls, end walls, tunnel stubs, ventilation shaft)'
EPS=.00015

def collection(name,scene=None):
    scene=scene or bpy.data.scenes['Tokyo Station']
    c=bpy.data.collections.get(name)
    if c is None:c=bpy.data.collections.new(name);scene.collection.children.link(c)
    return c

def retire(o):
    name=o.name;cs=list(o.users_collection);links=[]
    for c in cs:
        roots=[s.name for s in bpy.data.scenes if c==s.collection]
        links.extend([{'scene':s} for s in roots] if roots else [{'collection':c.name}])
    o.name=name+' [before V15]';o['V15_original_name']=name
    for c in cs:c.objects.unlink(o)
    c=collection('V15_Replaced_hidden');c.objects.link(o)
    c.hide_render=True;c.hide_viewport=True;o.hide_render=True;o.hide_viewport=True
    R['retained'].append({'original':name,'retained':o.name,'links':links})
    return cs

def components(o,frame=None):
    v,lab,lo,hi=component_labels(o)
    if frame is not None:
        inv=np.array(frame.inverted());v=v@inv[:3,:3].T+inv[:3,3]
        lo[:]=np.inf;hi[:]=-np.inf;np.minimum.at(lo,lab,v);np.maximum.at(hi,lab,v)
    return lab,lo,hi

def contained(lo,hi,a,b):
    return np.all(lo>=np.array(a)-EPS,axis=1)&np.all(hi<=np.array(b)+EPS,axis=1)

def slab_boxes():
    """Explicit slab volumes, so disconnected grid faces are not mistaken for walls."""
    x0,x1=G.BOX_X;u0,u1=G.UPPER_X;yi,yo=G.WALL_IN,G.WALL_OUT
    boxes=[((x0-G.END_T,-yo,G.BASE_BOT),(x1+G.END_T,yo,G.INVERT)),
           ((x0,-yi,G.B4_SOFFIT),(x1,yi,G.B4_FLOOR)),
           ((x0,-yi,G.B3_SOFFIT),(u0,yi,G.LOWROOF_TOP)),
           ((u1,-yi,G.B3_SOFFIT),(x1,yi,G.LOWROOF_TOP))]
    for zb,zt in [(G.B3_SOFFIT,G.B3_FLOOR),(G.B2_SOFFIT,G.B2_FLOOR),(G.B1_SOFFIT,G.B1_FLOOR),(G.ROOF_SOFFIT,G.ROOF_TOP)]:
        boxes.append(((u0,-yi,zb),(u1,yi,zt)))
    c0,c1=G.B1_CORRIDOR_X
    for zb,zt in [(G.B1_SOFFIT,G.B1_FLOOR),(G.ROOF_SOFFIT,G.ROOF_TOP)]:
        boxes.append(((c0-.15,G.B1_CORRIDOR_Y-.15,zb),(c1+.15,-yo,zt)))
    boxes.append(((c0,G.B1_CORRIDOR_Y,G.B1_CEIL),(c1,-yo,G.B1_CEIL+.03)))
    for sign,end in [(-1,x0-G.END_T),(1,x1+G.END_T)]:
        a,b=sorted((end,end+sign*30))
        for yt in G.TRK.values():
            for zb,zt in [(G.BASE_BOT+1,G.INVERT),(-22,-21.4)]:
                boxes.append(((a,yt-2.9,zb),(b,yt+2.9,zt)))
    return boxes

def structure_wall_mask(lo,hi):
    keep=np.zeros(len(lo),dtype=bool)
    for a,b in slab_boxes():keep|=contained(lo,hi,a,b)
    # The vertical ventilation duct is a service object, not a perimeter wall.
    vx,vy=G.to_local(*G.VENT_XY_MODEL);r=G.VENT_HALF+.4
    keep|=contained(lo,hi,(vx-r,vy-r,G.B2_FLOOR),(vx+r,vy+r,G.VENT_TOP))
    return ~keep

def side_band(lo,hi,edge):
    return (lo[:,1]>=edge-EPS)|(hi[:,1]<=-edge+EPS)

def b1_mask(lo,hi):
    ceiling=(lo[:,2]>=G.B1_CEIL-EPS)&(hi[:,2]<=G.B1_CEIL+.03+EPS)
    return ~ceiling & (side_band(lo,hi,G.WALL_IN-.031)|
        ((hi[:,0]<=G.B1_HALL_X[0]+EPS)&(lo[:,0]>=G.B1_HALL_X[0]-.151))|
        ((lo[:,0]>=G.B1_HALL_X[1]-EPS)&(hi[:,0]<=G.B1_HALL_X[1]+.151)))

def edit(name,reason,selector,frame=None):
    o=bpy.data.objects[name];lab,lo,hi=components(o,frame);mask=np.asarray(selector(lo,hi),dtype=bool)
    if not mask.any():raise RuntimeError('No selected wall components: '+name)
    if mask.all():raise RuntimeError('Mixed mesh would be emptied: '+name)
    q=o.copy();q.data=o.data.copy();cs=retire(o);q.name=name
    for c in cs:c.objects.link(q)
    q.hide_render=False;q.hide_viewport=False;q['V15_modified_copy']=True;q['V15_change']=reason
    bm=bmesh.new();bm.from_mesh(q.data);bm.verts.ensure_lookup_table()
    ids=np.flatnonzero(mask[lab]);bmesh.ops.delete(bm,geom=[bm.verts[int(i)] for i in ids],context='VERTS')
    bm.to_mesh(q.data);bm.free();q.data.update()
    R['edits'].append({'object':name,'reason':reason,'removed_components':int(mask.sum()),'kept_components':int((~mask).sum()),'removed_vertices':len(ids),'remaining_vertices':len(q.data.vertices)})
    return q

def remove(name,reason):
    o=bpy.data.objects[name];n=len(o.data.vertices);retire(o)
    R['edits'].append({'object':name,'reason':reason,'whole_object':True,'removed_vertices':n,'remaining_vertices':0})

def open_walls():
    remove(JR+'box west wall (hide for the cutaway view)','JR west exterior diaphragm wall')
    edit(STRUCT,'JR east/end walls, upper perimeter and tunnel side/end enclosures',structure_wall_mask,SF)
    edit(JR+'B5 ceilings, bulkheads, track walls, soffit beams','B5 track-wall cladding; retain ceiling and beams',lambda lo,hi:side_band(lo,hi,18.60),SF)
    edit(JR+'B5 light fittings','Fixtures attached only to the removed track walls',lambda lo,hi:side_band(lo,hi,18.35),SF)
    edit(JR+'signs (station names, departure boards, track numbers, exits, stop boards, signals)',
         'Track-wall posters/name boards and corridor end-wall sign; retain overhead and column signs',
         lambda lo,hi:side_band(lo,hi,18.59),SF)
    edit(JR+'B4 concourse (ceiling, partitions, doors)','B4 perimeter partitions and their doors; preserve ceiling',
         lambda lo,hi:~((lo[:,2]>=G.B4_CEIL-EPS)&(hi[:,2]<=G.B4_CEIL+.03+EPS)),SF)
    edit(JR+'B1 concourse (ceiling, walls, ticket gates, ventilation-shaft cladding)',
         'B1 perimeter and end walls; preserve gates, ceiling and ventilation duct',b1_mask,SF)
    # These grid walls consist of individual faces. Their source material is used
    # only on partitions in this mesh, never on the switchgear, tanks or fans.
    name=JR+'B2-B3 machine rooms (partitions, switchgear, tanks, fans)'
    o=bpy.data.objects[name];lab,lo,hi=components(o,SF);partition=np.zeros(len(lo),dtype=bool)
    for p in o.data.polygons:
        if o.data.materials[p.material_index].name=='V9 | cast-in-place concrete (box structure)':partition[lab[p.vertices[0]]]=True
    edit(name,'Equipment-room partition walls; preserve all switchgear, tanks, fans and ducts',lambda lo,hi:partition,SF)
    remove('V11 M17 track walls with red band and station names','M17 both trackside walls and wall decoration')
    edit('V11 M17 B1 concourse roof and side walls','M17 B1 side walls; retain roof and access apertures',lambda lo,hi:hi[:,2]<-2.58)
    edit('V11 M17 B1 concourse ticket gates balustrades and transfer branches','JR transfer-branch side walls; preserve gates, floor, roof and hanging signs',
         lambda lo,hi:(lo[:,1]>6)&((hi[:,2]-lo[:,2])>3)&((hi[:,0]-lo[:,0])<.18),MF)
    for code,cy in [('M7',-139),('M8',-94)]:
        remove('V13 '+code+' tiled stairwell retaining walls',code+' underground stairwell retaining walls')
        edit('V13 '+code+' B1 passage walls and roof',code+' passage perimeter; preserve continuous roof',lambda lo,hi:hi[:,2]<-2.54)
        edit('V13 '+code+' handrails stair nosings tactile paving and lights',code+' tile grout on removed stairwell walls',
             lambda lo,hi:(np.abs(np.abs((lo[:,1]+hi[:,1])/2-cy)-1.553)<.001)&((hi[:,1]-lo[:,1])<.014))

def camera(name,frame,pos,target,scene,ortho=100):
    name='V15 '+name;d=bpy.data.cameras.new(name);d.type='ORTHO';d.ortho_scale=ortho;d.clip_start=.05;d.clip_end=2500
    o=bpy.data.objects.new(name,d);collection('V15_Review_Cameras').objects.link(o)
    o.location=frame@Vector(pos);o.rotation_euler=(frame@Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
    if o.name not in scene.objects:scene.collection.objects.link(o)
    o['V15_scene']=scene.name;scene.camera=o
    return o

def study(name,colnames,frame,lights):
    sc=bpy.data.scenes.new(name);main=bpy.data.scenes['Tokyo Station']
    sc.world=main.world.copy();sc.world.name=name+' world'
    if sc.world.use_nodes:
        bg=next((n for n in sc.world.node_tree.nodes if n.type=='BACKGROUND'),None)
        if bg:bg.inputs['Color'].default_value=(.34,.38,.43,1);bg.inputs['Strength'].default_value=.65
    for n in colnames:
        c=bpy.data.collections.get(n)
        if c:sc.collection.children.link(c)
    sc.view_settings.view_transform='AgX';sc.render.engine='CYCLES';sc.cycles.samples=64;sc.cycles.use_denoising=True
    sc['description']='Linked inspection view of V15 open-side geometry. Floors, platforms, trains and columns are present; originals are in V15_Replaced_hidden in the main scene.'
    for i,(pos,target,power,size) in enumerate(lights):
        d=bpy.data.lights.new(name+' fill '+str(i),'AREA');d.energy=power;d.shape='DISK';d.size=size
        o=bpy.data.objects.new(d.name,d);sc.collection.objects.link(o);o.location=frame@Vector(pos)
        o.rotation_euler=(frame@Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
    return sc

def cameras():
    main=bpy.data.scenes['Tokyo Station']
    jr=study('V15 JR open sides',['V9_Sobu_Underground_Station','V9_Sobu_Trains','V9_Sobu_People','V9_Sobu_Lights'],SF,
             [((0,48,-12),(0,0,-17),6500,45),((30,-45,-10),(15,0,-17),5000,40)])
    metro=study('V15 Metro open sides',['V11_Metro_'+s for s in ['Platform','Track','Walls','Ceiling','Columns','Stairs','Platform_Doors','Concourse','Fixtures','Trains','Lights']]+
                ['V13_Metro_'+s for s in ['Access_Shell','Access_Floor','Access_Detail','Access_Lights','Entrances']],MF,
                [((0,-32,-1),(0,0,-8),2500,30),((0,30,-1),(0,0,-8),2500,30)])
    camera('01 JR layered side',SF,(40,155,-5),(10,0,-16),jr,110)
    camera('02 JR opposite side',SF,(-30,-160,-6),(10,0,-16),jr,120)
    camera('03 M17 platform and concourse',MF,(12,-100,-2),(-15,0,-7.5),metro,65)
    camera('04 M8 entrance and passage',Matrix.Identity(4),(-155,-117,2),(-135,-94,-2.5),metro,24)
    # Horizontal sight lines keep the foreground display-ground plate from
    # obscuring the upper underground storeys in the complete main scene.
    main.camera=camera('05 full model underground side',SF,(40,155,-16),(10,0,-16),main,110)
    main.render.resolution_x=1600;main.render.resolution_y=760;main.render.resolution_percentage=100
    main['V9_cut_y']=0.0
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                space=area.spaces.active;space.region_3d.view_perspective='CAMERA';space.shading.color_type='MATERIAL';space.overlay.show_extras=False
    return main

def main():
    args=sys.argv[sys.argv.index('--')+1:];sc=bpy.data.scenes['Tokyo Station']
    if sc.get('V15_refinement'):raise RuntimeError('Build from the final V14 input')
    if len(args)>2:json.dump(fingerprint(),open(args[2],'w'),separators=(',',':'))
    open_walls();print('V15_WALLS_OPEN',len(R['edits']),flush=True);cameras()
    R['preserved']='Complete V14 source geometry retained, including trains, floors, stairs, columns, surface buildings and ground details. Hidden originals are restoration sources.'
    sc['V15_refinement']=json.dumps(R,ensure_ascii=False);sc['last_stage']='V15 underground open-side presentation, 2026-11-03'
    sc['V15_display_note']='Intentional exhibition cutaway of side enclosures, not a claim that the real stations lack retaining walls.'
    p=os.path.join(os.path.dirname(__file__),'..','README_V15.txt')
    if os.path.isfile(p):tx=bpy.data.texts.new('README_V15_中文');tx.write(open(p,encoding='utf8').read())
    bpy.context.window.scene=sc;bpy.context.view_layer.update();bpy.ops.file.pack_all();bpy.context.preferences.filepaths.save_version=0
    out=os.path.abspath(args[0]);os.makedirs(os.path.dirname(out),exist_ok=True);bpy.ops.wm.save_as_mainfile(filepath=out,compress=True)
    json.dump(R,open(args[1],'w',encoding='utf8'),ensure_ascii=False,indent=2);print('V15_BUILD_OK',flush=True)

if __name__=='__main__':main()
