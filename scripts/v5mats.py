"""Procedural materials for Tokyo Station V5 (Blender 5.2 shader nodes)."""
import bpy


def _n(nt, typ, loc, **props):
    n = nt.nodes.new(typ)
    n.location = loc
    for k, v in props.items():
        setattr(n, k, v)
    return n


def _math(nt, op, a=None, b=None, loc=(0, 0), clamp=False):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    n.location = loc
    n.use_clamp = clamp
    for i, x in enumerate((a, b)):
        if x is None:
            continue
        if isinstance(x, (int, float)):
            n.inputs[i].default_value = x
        else:
            nt.links.new(x, n.inputs[i])
    return n.outputs[0]


def fish_scale_slate(name="V5 | Ogatsu-type natural slate fish-scale (gyorin-buki)",
                     tile_w=0.28, course_h=0.16, arc=0.62,
                     dark=(0.030, 0.032, 0.037), light=(0.062, 0.066, 0.074)):
    """Scalloped slate: round-bottomed tiles in half-bond courses, tile-wise colour, edge shadow + bump.
    Uses the object's active-render UV in metres: u horizontal along the roof, v up the slope."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    out = nt.nodes.get("Material Output")
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.location = (1400, 0)
    out.location = (1700, 0)
    tc = _n(nt, "ShaderNodeTexCoord", (-1600, 0))
    sep = _n(nt, "ShaderNodeSeparateXYZ", (-1400, 0))
    nt.links.new(tc.outputs["UV"], sep.inputs[0])
    X = _math(nt, "DIVIDE", sep.outputs[0], tile_w, (-1200, 120))
    Y = _math(nt, "DIVIDE", sep.outputs[1], course_h, (-1200, -60))
    row = _math(nt, "FLOOR", Y, None, (-1000, -60))
    ly = _math(nt, "FRACT", Y, None, (-1000, -200))
    # offset for current row: 0.5 * (row mod 2) using floored modulo
    half = _math(nt, "FLOORED_MODULO", row, 2.0, (-800, 0))
    off = _math(nt, "MULTIPLY", half, 0.5, (-650, 0))
    xr = _math(nt, "ADD", X, off, (-500, 100))
    col = _math(nt, "FLOOR", xr, None, (-350, 160))
    lx = _math(nt, "SUBTRACT", _math(nt, "FRACT", xr, None, (-350, 60)), 0.5, (-200, 60))
    # arc bottom of this course: yb = arc*(1 - sqrt(max(0,1-(2lx)^2)))
    t = _math(nt, "MULTIPLY", lx, 2.0, (-50, 60))
    t2 = _math(nt, "MULTIPLY", t, t, (100, 60))
    s = _math(nt, "SQRT", _math(nt, "MAXIMUM", _math(nt, "SUBTRACT", 1.0, t2, (250, 60)), 0.0, (400, 60)), None, (550, 60))
    yb = _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", 1.0, s, (700, 60)), arc, (850, 60))
    d_up = _math(nt, "SUBTRACT", ly, yb, (1000, 0))           # signed distance above this course's arc
    m_up = _math(nt, "GREATER_THAN", d_up, 0.0, (1000, -150))  # 1 -> on this course's tile
    # lower course tile id (row-1), offset flips
    rowb = _math(nt, "SUBTRACT", row, 1.0, (-800, -300))
    offb = _math(nt, "MULTIPLY", _math(nt, "FLOORED_MODULO", rowb, 2.0, (-650, -300)), 0.5, (-500, -300))
    colb = _math(nt, "FLOOR", _math(nt, "ADD", X, offb, (-350, -300)), None, (-200, -300))
    # chosen tile id
    inv = _math(nt, "SUBTRACT", 1.0, m_up, (1150, -150))
    cid = _math(nt, "ADD", _math(nt, "MULTIPLY", col, m_up, (1150, 200)), _math(nt, "MULTIPLY", colb, inv, (1150, 100)), (1300, 150))
    rid = _math(nt, "ADD", _math(nt, "MULTIPLY", row, m_up, (1150, -250)), _math(nt, "MULTIPLY", rowb, inv, (1150, -350)), (1300, -300))
    comb = _n(nt, "ShaderNodeCombineXYZ", (1450, -100))
    nt.links.new(cid, comb.inputs[0])
    nt.links.new(rid, comb.inputs[1])
    wn = _n(nt, "ShaderNodeTexWhiteNoise", (1600, -100))
    wn.noise_dimensions = '3D'
    nt.links.new(comb.outputs[0], wn.inputs["Vector"])
    # colour per tile
    ramp = _n(nt, "ShaderNodeValToRGB", (1750, -100))
    ramp.color_ramp.elements[0].color = (*dark, 1)
    ramp.color_ramp.elements[1].color = (*light, 1)
    nt.links.new(wn.outputs["Value"], ramp.inputs[0])
    # edge shadow: just below an arc (d_up in (-0.10, 0)) darken; just above (0..0.05) lighten slightly
    shadow = _math(nt, "MULTIPLY", _math(nt, "LESS_THAN", d_up, 0.0, (1000, -450)),
                   _math(nt, "GREATER_THAN", d_up, -0.10, (1000, -550)), (1150, -500))
    shade = _math(nt, "SUBTRACT", 1.0, _math(nt, "MULTIPLY", shadow, 0.55, (1300, -500)), (1450, -500))
    mixc = _n(nt, "ShaderNodeMix", (1900, -150))
    mixc.data_type = 'RGBA'
    mixc.blend_type = 'MULTIPLY'
    mixc.inputs["Factor"].default_value = 1.0
    ia = next(i for i in mixc.inputs if i.identifier == "A_Color")
    ib = next(i for i in mixc.inputs if i.identifier == "B_Color")
    oc = next(o for o in mixc.outputs if o.identifier == "Result_Color")
    nt.links.new(ramp.outputs["Color"], ia)
    sh_rgb = _n(nt, "ShaderNodeCombineColor", (1750, -450))
    for i in range(3):
        nt.links.new(shade, sh_rgb.inputs[i])
    nt.links.new(sh_rgb.outputs[0], ib)
    # height for bump: tile thickness step at the arc + slight random tilt
    e = _math(nt, "ADD", _math(nt, "MULTIPLY", d_up, m_up, (1150, -700)),
              _math(nt, "MULTIPLY", _math(nt, "ADD", d_up, 1.0, (1000, -800)), inv, (1150, -800)), (1300, -750))
    hgt = _math(nt, "ADD", _math(nt, "MINIMUM", _math(nt, "MULTIPLY", e, 6.0, (1450, -750)), 1.0, (1600, -750)),
                _math(nt, "MULTIPLY", wn.outputs["Value"], 0.25, (1600, -880)), (1750, -800))
    bump = _n(nt, "ShaderNodeBump", (2000, -600))
    bump.inputs["Strength"].default_value = 0.65
    bump.inputs["Distance"].default_value = 0.006
    nt.links.new(hgt, bump.inputs["Height"])
    # fine grain noise for roughness
    noise = _n(nt, "ShaderNodeTexNoise", (1750, 300))
    noise.inputs["Scale"].default_value = 60.0
    nt.links.new(tc.outputs["UV"], noise.inputs["Vector"])
    rough = _math(nt, "ADD", 0.42, _math(nt, "MULTIPLY", noise.outputs["Fac"], 0.22, (1900, 300)), (2050, 300))
    rough2 = _math(nt, "ADD", rough, _math(nt, "MULTIPLY", wn.outputs["Value"], 0.12, (2050, 150)), (2200, 250))
    bsdf.location = (2400, 0)
    out.location = (2700, 0)
    nt.links.new(oc, bsdf.inputs["Base Color"])
    nt.links.new(rough2, bsdf.inputs["Roughness"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Specular IOR Level"].default_value = 0.55
    m.diffuse_color = (0.045, 0.048, 0.055, 1)
    m["V5_note"] = "Fish-scale (gyorin-buki) slate per restoration specification for dome/central roofs; tile size is a visual estimate."
    return m


def copper(name="V5 | weathered copper sheet", base=(0.20, 0.16, 0.12), patina=(0.13, 0.20, 0.18), patina_amt=0.35):
    """Darkened copper with blotchy early patina (restored 2012, ~14 years of weathering)."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    tc = _n(nt, "ShaderNodeTexCoord", (-900, 0))
    noise = _n(nt, "ShaderNodeTexNoise", (-700, 0))
    noise.inputs["Scale"].default_value = 3.0
    noise.inputs["Detail"].default_value = 6.0
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    ramp = _n(nt, "ShaderNodeValToRGB", (-450, 0))
    ramp.color_ramp.elements[0].position = 0.45
    ramp.color_ramp.elements[0].color = (*base, 1)
    ramp.color_ramp.elements[1].position = 0.75
    ramp.color_ramp.elements[1].color = (*[base[i] * (1 - patina_amt) + patina[i] * patina_amt for i in range(3)], 1)
    nt.links.new(noise.outputs["Fac"], ramp.inputs[0])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Metallic"].default_value = 0.55
    b.inputs["Roughness"].default_value = 0.42
    m.diffuse_color = (*base, 1)
    return m


def plaster_gradient(name, c_low, c_high, z_low, z_high, rough=0.8):
    """Interior plaster with a vertical colour gradient (world Z) - used for the graded yolk-yellow dome ceiling."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    tc = _n(nt, "ShaderNodeTexCoord", (-900, 0))
    sep = _n(nt, "ShaderNodeSeparateXYZ", (-700, 0))
    geo = _n(nt, "ShaderNodeNewGeometry", (-1100, 0))
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    mr = _n(nt, "ShaderNodeMapRange", (-500, 0))
    mr.inputs["From Min"].default_value = z_low
    mr.inputs["From Max"].default_value = z_high
    nt.links.new(sep.outputs[2], mr.inputs["Value"])
    ramp = _n(nt, "ShaderNodeValToRGB", (-250, 0))
    ramp.color_ramp.elements[0].color = (*c_low, 1)
    ramp.color_ramp.elements[1].color = (*c_high, 1)
    nt.links.new(mr.outputs["Result"], ramp.inputs[0])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    m.diffuse_color = (*c_low, 1)
    return m
