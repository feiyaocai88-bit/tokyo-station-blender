"""Read-only audit of native surface mast meshes in the complete V15 model.

blender -b model.blend --python-exit-code 1 -P scripts/audit_surface_catenary.py -- report.json masts.csv
No scene objects, transforms, visibility or .blend files are changed or saved.
This checks model relationships; it does not measure real-world mast coordinates.
"""
import csv, hashlib, json, sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).parent))
import v14lib as H
import mod6_catenary as C

MAST_OBJECTS = ('V6 OCS | masts', 'V8 OCS | masts at the level change', 'V14 south OCS mast')


def bvh(o, vertices=None, faces=None):
    v = H.world(o) if vertices is None else vertices
    f = [tuple(p.vertices) for p in o.data.polygons] if faces is None else faces
    return BVHTree.FromPolygons(v.tolist(), f)


def closest_track(x, y, chuo, extents):
    result = []
    for k in C.ORDER:
        if (k in C.CHUO) != chuo:
            continue
        x0, x1, _ = extents[k]
        if not x0-.5 <= x <= x1+.5:
            continue
        xx = np.r_[x0, C.GX[(C.GX>x0)&(C.GX<x1)], x1]
        pts = np.c_[xx, np.interp(xx, C.GX, C.TGT[k])]
        a, d = pts[:-1], np.diff(pts, axis=0)
        t = np.clip(np.sum((np.array([x,y])-a)*d, axis=1)/np.sum(d*d, axis=1), 0, 1)
        distance = float(np.linalg.norm(a+t[:,None]*d-[x,y], axis=1).min())
        result.append((distance, k))
    return sorted(result)


def main():
    args = sys.argv[sys.argv.index('--')+1:]
    sc = bpy.data.scenes['Tokyo Station']
    hidden = set()
    def walk(c, inherited=False):
        hide = inherited or c.hide_render
        if hide:
            hidden.update(o.name for o in c.objects)
        for child in c.children:
            walk(child, hide)
    walk(sc.collection)
    active = [o for o in sc.objects if o.type=='MESH' and not o.hide_render and o.name not in hidden]
    extents = C.rails_extent()
    meshes, rows = {}, []
    for name in MAST_OBJECTS:
        o = bpy.data.objects[name]
        assert o in active, 'Missing active mast mesh: '+name
        v, inv, lo, hi = H.component_labels(o)
        meshes[name] = (v, inv, lo, hi)
        for ci, (a,b) in enumerate(zip(lo,hi)):
            if b[2]-a[2]<3 or max(b[0]-a[0], b[1]-a[1])>.7:
                continue
            x, y = ((a+b)/2)[:2]
            distances = closest_track(x, y, a[2]>12, extents)
            distance, k = distances[0]
            radius = float(max(b[0]-a[0], b[1]-a[1])/2)
            margin = min(d-radius-(2.6 if track in C.SHIN else 2.3) for d,track in distances)
            zone = 'Chuo' if a[2]>12 else ('Shinkansen' if k in C.SHIN else 'conventional')
            status = 'inherited_procedural_unverified'
            if name.startswith('V14'):
                status = ('model_end_adaptation' if abs(x-241)<.01 else
                          'curve_constraint_unverified' if abs(x-184)<.01 else
                          'V14_photo_chainage_estimate_lateral_fitted')
            rows.append(dict(object=name, component=ci, x=float(x), y=float(y), base_z=float(a[2]),
                top_z=float(b[2]), zone=zone, nearest_track=k, shaft_radius_or_halfwidth=radius,
                track_center_distance_m=distance, shaft_face_clearance_m=distance-radius,
                minimum_margin_to_all_same_level_track_targets_m=margin,
                model_clearance_target_m=2.6 if k in C.SHIN else 2.3, evidence=status,
                surveyed_coordinate=False, base_supports=[], base_attachment=None, obstacle_hits=[]))
    rows.sort(key=lambda m: (['Chuo','conventional','Shinkansen'].index(m['zone']),m['x'],m['y']))
    shaft_bvh = {}
    for n,m in enumerate(rows,1):
        m['id'] = 'M%03d'%n
        v,inv,lo,hi = meshes[m['object']]
        o = bpy.data.objects[m['object']]
        faces = [tuple(p.vertices) for p in o.data.polygons if inv[p.vertices[0]]==m['component']]
        shaft_bvh[m['id']] = bvh(o,v,faces)
    print('Native mast shafts:', len(rows), flush=True)

    # Actual mesh-surface intersection tests. AABB tests only prune candidates.
    tested_obstacles, roof_pairs, roof_hits = [], 0, []
    roofs = [o for o in active if 'differentiated roof skin' in o.name or
             o.name=='V11 05-06 curved green roof with low side wings']
    for o in active:
        if not o.name.startswith(('V10 ','V11 ','V8 Platform','V5 Shinkansen')):
            continue
        is_roof = o in roofs
        if not is_roof and any(s in o.name.lower() for s in
            ['roof skin','curved green roof','mast penetration','roof seams','roof curbs',
             'retained steel','seams flashings','ground','road','tree','plant','grass','car ']):
            continue
        bb=np.array([o.matrix_world@Vector(c) for c in o.bound_box]);lo,hi=bb.min(0),bb.max(0)
        if hi[2]<4 or lo[2]>30:
            continue
        cand=[m for m in rows if lo[0]-.28<=m['x']<=hi[0]+.28 and lo[1]-.28<=m['y']<=hi[1]+.28
              and lo[2]<m['top_z'] and hi[2]>m['base_z']+.12]
        if not cand:
            continue
        tested_obstacles.append(o.name);other=bvh(o)
        for m in cand:
            if is_roof:
                roof_pairs+=1
            overlap=shaft_bvh[m['id']].overlap(other)
            if overlap:
                hit=dict(id=m['id'],object=o.name,triangle_pairs=len(overlap))
                if is_roof:
                    roof_hits.append(hit)
                else:
                    m['obstacle_hits'].append(hit)

    room_hits=[]
    rooms=[o for o in active if 'roof equipment room at' in o.name]
    for name in ['V6 OCS | V-truss beams and cantilevers','V6 OCS | masts']:
        o=bpy.data.objects[name];v,inv,lo,hi=meshes.get(name) or H.component_labels(o)
        for room in rooms:
            rv=H.world(room);rlo,rhi=rv.min(0),rv.max(0)
            sel=np.flatnonzero(np.all(hi>=rlo,axis=1)&np.all(lo<=rhi,axis=1))
            if not len(sel):
                continue
            take=np.isin(inv,sel)
            faces=[tuple(p.vertices) for p in o.data.polygons if take[p.vertices[0]]]
            pairs=bvh(o,v,faces).overlap(bvh(room,rv))
            if pairs:
                room_hits.append(dict(structure=name,room=room.name,triangle_pairs=len(pairs)))
    print('Shaft, roof and rooftop-room mesh checks complete',flush=True)

    # Footing centre rays; the 28 Chuo edge masts instead connect sideways to the
    # deck. Verify their existing bracket surfaces actually intersect that deck.
    for o in active:
        if o.name.startswith(('V6 OCS','V8 OCS','V14 south OCS','V13 catenary','V5 track')):
            continue
        bb=np.array([o.matrix_world@Vector(c) for c in o.bound_box]);lo,hi=bb.min(0),bb.max(0)
        cand=[m for m in rows if lo[0]-.01<=m['x']<=hi[0]+.01 and lo[1]-.01<=m['y']<=hi[1]+.01
              and lo[2]<m['base_z']+.12 and hi[2]>m['base_z']-.5]
        if not cand:
            continue
        other=bvh(o)
        for m in cand:
            p,n,i,d=other.ray_cast(Vector((m['x'],m['y'],m['base_z']+.11)),Vector((0,0,-1)),.62)
            if p is not None:
                m['base_supports'].append(dict(object=o.name,vertical_gap_m=round(m['base_z']-p.z,5)))
    for m in rows:
        if m['base_supports']:
            m['base_attachment']='footing_on_model_surface'
            continue
        if m['zone']!='Chuo':
            continue
        name='V3 Track '+m['nearest_track']+' curved viaduct'
        deck=bpy.data.objects[name];o=bpy.data.objects[m['object']]
        v,inv,lo,hi=meshes[m['object']];c=(lo+hi)/2
        take=(abs(c[:,0]-m['x'])<.3)&(abs(c[:,1]-m['y'])<1.1)&(lo[:,2]>m['base_z']+.1)&(hi[:,2]<m['base_z']+1.6)&((hi[:,1]-lo[:,1])>.6)
        faces=[tuple(p.vertices) for p in o.data.polygons if take[inv[p.vertices[0]]]]
        pairs=bvh(o,v,faces).overlap(bvh(deck)) if faces else []
        if pairs:
            m['base_attachment']='existing_side_brackets_intersect_viaduct'
            m['base_supports'].append(dict(object=name,bracket_triangle_pairs=len(pairs)))
    checks=[
        dict(name='native_shafts_extracted',pass_=len(rows)==175,count=len(rows)),
        dict(name='model_shaft_clearance_targets',pass_=all(m['minimum_margin_to_all_same_level_track_targets_m']>=-1e-4 for m in rows)),
        dict(name='shafts_vs_selected_platform_facilities',pass_=not any(m['obstacle_hits'] for m in rows)),
        dict(name='shafts_vs_roof_skins',pass_=not roof_hits,candidate_pairs=roof_pairs),
        dict(name='portal_steel_vs_rooftop_equipment_rooms',pass_=not room_hits,rooms=len(rooms)),
        dict(name='footings_or_existing_side_brackets',pass_=all(m['base_attachment'] for m in rows)),
    ]
    for c in checks:
        c['pass']=bool(c.pop('pass_'))
    counts={z:sum(m['zone']==z for m in rows) for z in ['Chuo','conventional','Shinkansen']}
    evidence={s:sum(m['evidence']==s for m in rows) for s in sorted(set(m['evidence'] for m in rows))}
    report=dict(audit_date='2026-11-03',input_file=Path(bpy.data.filepath).name,
        input_sha256=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),
        geometry_changed=False,real_world_coordinates_verified=False,
        purpose='Model geometry audit and evidence classification, not a pole-location survey.',
        counts=counts,evidence_counts=evidence,checks=checks,masts=rows,
        roof_hits=roof_hits,rooftop_room_hits=room_hits,tested_obstacle_meshes=tested_obstacles,
        limitations=[
            'The 162 inherited masts retain procedural chainages. None is promoted to a photo-verified coordinate by this audit.',
            'V14 has 10 masts on five photo-interpreted longitudinal rows (legacy +/-3 m estimate), two on a cropped-end adaptation and one extra for model curvature. All lateral coordinates are fitted to model tracks.',
            'Roof-hung and viaduct-soffit contact-wire registrations are not standalone masts and are excluded from the count of 175.',
            '2.30/2.60 m are inherited model design targets, not a claim of compliance with a railway engineering standard.',
            'Tests cover native shaft surfaces against listed platform meshes, roof skins, eight rooftop rooms and model bases; they are not an exhaustive evaluated-scene collision or structural analysis.',
            'Available aerial/oblique photographs do not reveal every mast footing; roof frames, shadows and overhead conductors must not be treated as surveyed mast coordinates.',
        ])
    Path(args[0]).parent.mkdir(parents=True,exist_ok=True)
    Path(args[0]).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    fields=['id','zone','object','x','y','base_z','top_z','nearest_track','shaft_face_clearance_m',
            'model_clearance_target_m','base_attachment','evidence','surveyed_coordinate']
    with open(args[1],'w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader()
        for m in rows:
            writer.writerow({k:round(v,5) if isinstance(v,float) else v for k,v in m.items()})
    print(json.dumps(dict(counts=counts,evidence=evidence,checks=checks)),flush=True)
    if not all(c['pass'] for c in checks):
        raise RuntimeError('Audit has model failures; inspect the report.')


if __name__=='__main__':
    main()
