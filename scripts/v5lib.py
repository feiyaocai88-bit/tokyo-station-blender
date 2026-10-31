"""Shared helpers for the Tokyo Station V5 modification modules (Blender 5.2)."""
import math
import bpy
import bmesh
from mathutils import Vector, Matrix

TAU = 2.0 * math.pi
SOUTH_DOME = (107.0, 0.415)
NORTH_DOME = (-104.0, 0.415)
LOG = []


def log(*a):
    s = " ".join(str(x) for x in a)
    LOG.append(s)
    print("[V5]", s, flush=True)


# ---------------------------------------------------------------- collections
def collection(name, parent=None, hide_render=False):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(col)
    col.hide_render = hide_render
    col.hide_viewport = False
    return col


def hidden_collection():
    return collection("V5_Replaced_V4_hidden", hide_render=True)


def retire(obj):
    """Hide a replaced object and park it in the V5 hidden collection (data kept)."""
    if obj is None:
        return
    hc = hidden_collection()
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    hc.objects.link(obj)
    obj.hide_render = True
    obj.hide_viewport = True
    obj["V5_retired"] = True


def link(obj, col):
    col.objects.link(obj)
    return obj


# ------------------------------------------------------------------ materials
def principled(name, color, rough=0.5, metal=0.0, spec=0.5, emission=None, strength=0.0):
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*color[:3], 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Specular IOR Level"].default_value = spec
    if emission is not None:
        b.inputs["Emission Color"].default_value = (*emission[:3], 1.0)
        b.inputs["Emission Strength"].default_value = strength
    m.diffuse_color = (*color[:3], 1.0)
    return m


def existing_mat(name):
    m = bpy.data.materials.get(name)
    if m is None:
        raise KeyError(name)
    return m


# --------------------------------------------------------------------- meshes
def mesh_object(name, verts, faces, col, mats=None, face_mats=None, uvs=None, smooth=False, uv_name="V5 metre UV"):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.validate(clean_customdata=False)
    if uvs is not None:
        uvl = me.uv_layers.new(name=uv_name)
        # uvs: list per face of list per corner (u,v)
        k = 0
        for fi, poly in enumerate(me.polygons):
            for ci, li in enumerate(poly.loop_indices):
                uvl.data[li].uv = uvs[fi][ci]
    if mats:
        for m in mats:
            me.materials.append(m)
    if face_mats is not None:
        me.polygons.foreach_set("material_index", face_mats)
    if smooth:
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    me.update()
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    return ob


class MeshBuilder:
    """Accumulate many primitives into one mesh (keeps object count low)."""

    def __init__(self):
        self.v, self.f, self.uv, self.mi, self.sm = [], [], [], [], []

    def add(self, verts, faces, mat=0, uvs=None, smooth=False):
        o = len(self.v)
        self.v.extend(verts)
        for i, f in enumerate(faces):
            self.f.append([o + j for j in f])
            self.mi.append(mat)
            self.sm.append(smooth)
            if uvs is not None:
                self.uv.append(uvs[i])
            else:
                # planar box-projection fallback (metre units)
                pts = [Vector(verts[j]) for j in f]
                n = (pts[1] - pts[0]).cross(pts[2] - pts[0])
                ax = max(range(3), key=lambda a: abs(n[a])) if n.length > 1e-12 else 2
                a, b = [(1, 2), (0, 2), (0, 1)][ax]
                self.uv.append([(p[a], p[b]) for p in pts])
        return o

    def build(self, name, col, mats, uv_name="V5 metre UV"):
        me = bpy.data.meshes.new(name)
        me.from_pydata([tuple(v) for v in self.v], [], [tuple(f) for f in self.f])
        uvl = me.uv_layers.new(name=uv_name)
        for fi, poly in enumerate(me.polygons):
            for ci, li in enumerate(poly.loop_indices):
                uvl.data[li].uv = self.uv[fi][ci]
        for m in mats:
            me.materials.append(m)
        me.polygons.foreach_set("material_index", self.mi)
        me.polygons.foreach_set("use_smooth", self.sm)
        me.validate(clean_customdata=False)
        me.update()
        ob = bpy.data.objects.new(name, me)
        col.objects.link(ob)
        return ob


def box(mb, cx, cy, cz, sx, sy, sz, mat=0, rotz=0.0, frame=None):
    """Axis box (size sx,sy,sz) centred at c; optional rotation about z or full frame matrix."""
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    loc = [(-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
           (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz)]
    M = frame if frame is not None else (Matrix.Translation((cx, cy, cz)) @ Matrix.Rotation(rotz, 4, 'Z'))
    vs = [tuple(M @ Vector(p)) for p in loc]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return mb.add(vs, faces, mat)


def lathe(mb, profile, center, segments=24, mat=0, smooth=True, cap_top=False, cap_bottom=False, phase=0.0, frame=None):
    """Revolve (r, z) profile around a vertical axis at center (x, y)."""
    cx, cy = center[0], center[1]
    verts, faces, uvs = [], [], []
    n = len(profile)
    for i in range(segments):
        a = phase + TAU * i / segments
        ca, sa = math.cos(a), math.sin(a)
        for r, z in profile:
            p = Vector((r * ca, r * sa, z))
            if frame is not None:
                p = frame @ p
            else:
                p = Vector((cx + p.x, cy + p.y, p.z))
            verts.append(tuple(p))
    # cumulative profile length for v
    L = [0.0]
    for k in range(1, n):
        L.append(L[-1] + math.hypot(profile[k][0] - profile[k - 1][0], profile[k][1] - profile[k - 1][1]))
    for i in range(segments):
        i2 = (i + 1) % segments
        for k in range(n - 1):
            a, b, c, d = i * n + k, i2 * n + k, i2 * n + k + 1, i * n + k + 1
            faces.append((a, b, c, d))
            u0 = TAU * i / segments * max(profile[k][0], 0.05)
            u1 = TAU * (i + 1) / segments * max(profile[k][0], 0.05)
            uvs.append([(u0, L[k]), (u1, L[k]), (u1, L[k + 1]), (u0, L[k + 1])])
    if cap_bottom and profile[0][0] > 1e-6:
        faces.append(tuple(i * n for i in reversed(range(segments))))
        uvs.append([(0, 0)] * segments)
    if cap_top and profile[-1][0] > 1e-6:
        faces.append(tuple(i * n + n - 1 for i in range(segments)))
        uvs.append([(0, 0)] * segments)
    mb.add(verts, faces, mat, uvs)
    if smooth:
        for k in range(len(faces)):
            mb.sm[-1 - k] = True


def tube(mb, path, radius, sides=8, mat=0, closed=False, smooth=True):
    """Sweep a circle along a polyline path (list of Vectors)."""
    pts = [Vector(p) for p in path]
    m = len(pts)
    verts, faces = [], []
    prev_n = None
    for i, p in enumerate(pts):
        if i == 0:
            t = (pts[1] - pts[0])
        elif i == m - 1:
            t = (pts[-1] - pts[-2])
        else:
            t = (pts[i + 1] - pts[i - 1])
        t.normalize()
        if prev_n is None:
            ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
            n = t.cross(ref).normalized()
        else:
            n = (prev_n - t * prev_n.dot(t)).normalized()
        b = t.cross(n).normalized()
        prev_n = n
        for s in range(sides):
            a = TAU * s / sides
            verts.append(tuple(p + (n * math.cos(a) + b * math.sin(a)) * radius))
    for i in range(m - 1):
        for s in range(sides):
            s2 = (s + 1) % sides
            faces.append((i * sides + s, i * sides + s2, (i + 1) * sides + s2, (i + 1) * sides + s))
    faces.append(tuple(reversed(range(sides))))
    faces.append(tuple((m - 1) * sides + s for s in range(sides)))
    mb.add(verts, faces, mat)
    if smooth:
        for k in range(len(faces) - 2):
            mb.sm[-3 - k] = True


def prism(mb, outline, z0, z1, mat=0, frame=None):
    """Extrude a 2D outline (CCW list of (x,y)) between z0 and z1."""
    n = len(outline)
    verts = []
    for z in (z0, z1):
        for x, y in outline:
            p = Vector((x, y, z))
            verts.append(tuple(frame @ p if frame is not None else p))
    faces = [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    return mb.add(verts, faces, mat)


def set_face_slope_uvs(me, uv_name="V5 slope UV", scale=1.0):
    """Per-face UV: v up the slope, u horizontal, in metres (for slate courses)."""
    uvl = me.uv_layers.get(uv_name) or me.uv_layers.new(name=uv_name)
    me.uv_layers.active = uvl
    for poly in me.polygons:
        n = poly.normal
        up = Vector((0, 0, 1))
        s = up - n * up.dot(n)
        if s.length < 1e-6:
            s = Vector((0, 1, 0))
        s.normalize()
        t = s.cross(n).normalized()
        for li in poly.loop_indices:
            p = me.vertices[me.loops[li].vertex_index].co
            uvl.data[li].uv = (p.dot(t) * scale, p.dot(s) * scale)
    for i, l in enumerate(me.uv_layers):
        l.active_render = (l.name == uv_name)
    return uvl
