# SPDX-License-Identifier: MIT
"""
material_kit.py - tested building blocks for PBR and stylized materials in Blender 4.2+ / 5.x.

Colour helpers (hex/sRGB to scene-linear), a clean Principled material, procedural wear layers
(edge wear, cavity dirt, roughness breakup), a flat-palette material for low-poly work with per-face
UV assignment, the glTF occlusion output hook, and texture statistics for QA.

MCP / scripts:
    mat = material_kit.pbr_material("M_Crate_Wood", base_hex="#8A6A3C", roughness=0.65, metallic=0.0)
    material_kit.add_edge_wear(mat, metal_hex="#B8B8B8", radius=0.015, amount=0.5)
    material_kit.add_cavity_dirt(mat, dirt_hex="#2E2A24", distance=0.2, amount=0.6)
    material_kit.add_roughness_breakup(mat, spread=0.15)
    pal = material_kit.palette_material("M_Palette", ["#E63946", "#F1FAEE", "#A8DADC", "#457B9D", "#1D3557"])
    material_kit.assign_palette(obj, pal, {0: 0, 1: 3})   # face index -> palette index (missing faces -> 0)
    material_kit.texture_stats("/path/T_Crate_BaseColor.png")

All recipes follow references/pbr-texturing.md. Edge wear and cavity dirt use Bevel and AO shader
nodes, which only evaluate in Cycles: bake them (bake_textures.py) for EEVEE or export.
"""

import math
import os

import bpy


# --------------------------------------------------------------------------- colour

def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def linear_to_srgb(c):
    return c * 12.92 if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def hex_to_linear(hex_str, alpha=1.0):
    """'#RRGGBB' (sRGB) -> (r, g, b, a) scene-linear, ready for a colour socket default_value."""
    h = hex_str.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    return (srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b), alpha)


def linear_to_hex(rgba):
    return "#%02X%02X%02X" % tuple(int(round(max(0.0, min(1.0, linear_to_srgb(c))) * 255)) for c in rgba[:3])


# --------------------------------------------------------------------------- node helpers

def _ensure_node_tree(mat):
    if getattr(mat, "node_tree", None) is None:
        try:
            mat.use_nodes = True
        except AttributeError:
            pass


def _principled(mat):
    return next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)


def _new(nt, type_name, location=(0, 0), **props):
    node = nt.nodes.new(type_name)
    node.location = location
    for k, v in props.items():
        setattr(node, k, v)
    return node


def _source_of(socket):
    """(from_socket) feeding a socket, or None when it holds a constant."""
    return socket.links[0].from_socket if socket.links else None


def _constant_node(nt, socket, location):
    """Materialise a socket's current constant as a node so it can be mixed."""
    if socket.type == "RGBA":
        n = _new(nt, "ShaderNodeRGB", location)
        n.outputs[0].default_value = tuple(socket.default_value)
        return n.outputs[0]
    n = _new(nt, "ShaderNodeValue", location)
    n.outputs[0].default_value = float(socket.default_value)
    return n.outputs[0]


def _mix_into(nt, bsdf, socket_name, factor_socket, b_socket, location):
    """Insert a Mix (RGBA) node: A = whatever currently feeds the socket, B = b_socket, factor = mask."""
    target = bsdf.inputs[socket_name]
    a = _source_of(target) or _constant_node(nt, target, (location[0] - 200, location[1] + 120))
    mix = _new(nt, "ShaderNodeMix", location, data_type="RGBA", blend_type="MIX")
    nt.links.new(factor_socket, mix.inputs["Factor"])
    nt.links.new(a, mix.inputs[6])   # A (RGBA)
    if isinstance(b_socket, tuple):
        mix.inputs[7].default_value = b_socket
    else:
        nt.links.new(b_socket, mix.inputs[7])  # B (RGBA)
    for l in list(target.links):
        nt.links.remove(l)
    nt.links.new(mix.outputs[2], target)  # Result (RGBA)
    return mix


# --------------------------------------------------------------------------- materials

def pbr_material(name, base_hex="#808080", roughness=0.5, metallic=0.0, emissive_hex=None, emissive_strength=0.0):
    """A clean metal/rough Principled material with linear colour values. Overwrites an existing name."""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    _ensure_node_tree(mat)
    nt = mat.node_tree
    bsdf = _principled(mat)
    if bsdf is None:
        bsdf = _new(nt, "ShaderNodeBsdfPrincipled", (0, 0))
        out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None) or _new(nt, "ShaderNodeOutputMaterial", (300, 0))
        nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = hex_to_linear(base_hex)
    bsdf.inputs["Roughness"].default_value = max(0.0, min(1.0, roughness))
    bsdf.inputs["Metallic"].default_value = 1.0 if metallic >= 0.5 else 0.0 if metallic <= 0.5 else metallic
    if emissive_hex:
        bsdf.inputs["Emission Color"].default_value = hex_to_linear(emissive_hex)
        bsdf.inputs["Emission Strength"].default_value = emissive_strength
    mat.diffuse_color = hex_to_linear(base_hex)  # viewport / Workbench colour
    mat.roughness = roughness
    mat.metallic = metallic
    return mat


def add_edge_wear(mat, metal_hex="#B4B4B4", radius=0.015, amount=0.5, noise_scale=25.0, metal_roughness=0.35):
    """Chipped paint on convex edges: Bevel-normal edge mask x noise -> mixes bare metal into colour,
    metallic and roughness. amount 0..1 widens the chipped band. Cycles-only nodes: bake before export."""
    nt = mat.node_tree
    bsdf = _principled(mat)
    x, y = -900, 500
    bevel = _new(nt, "ShaderNodeBevel", (x, y), samples=8)
    bevel.inputs["Radius"].default_value = radius
    geo = _new(nt, "ShaderNodeNewGeometry", (x, y - 200))
    dot = _new(nt, "ShaderNodeVectorMath", (x + 200, y), operation="DOT_PRODUCT")
    nt.links.new(bevel.outputs["Normal"], dot.inputs[0])
    nt.links.new(geo.outputs["Normal"], dot.inputs[1])
    rng = _new(nt, "ShaderNodeMapRange", (x + 400, y))
    rng.inputs["From Min"].default_value = 1.0 - 0.12 * (0.5 + amount)
    rng.inputs["From Max"].default_value = 0.999
    rng.inputs["To Min"].default_value = 1.0
    rng.inputs["To Max"].default_value = 0.0
    nt.links.new(dot.outputs["Value"], rng.inputs["Value"])
    noise = _new(nt, "ShaderNodeTexNoise", (x + 200, y - 300))
    noise.inputs["Scale"].default_value = noise_scale
    noise.inputs["Detail"].default_value = 6.0
    noise.inputs["Roughness"].default_value = 0.6
    ramp = _new(nt, "ShaderNodeValToRGB", (x + 400, y - 300))
    ramp.color_ramp.elements[0].position = 0.42
    ramp.color_ramp.elements[1].position = 0.58
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    mask = _new(nt, "ShaderNodeMath", (x + 650, y - 100), operation="MULTIPLY")
    nt.links.new(rng.outputs["Result"], mask.inputs[0])
    nt.links.new(ramp.outputs["Color"], mask.inputs[1])
    mask.label = "EdgeWearMask"
    _mix_into(nt, bsdf, "Base Color", mask.outputs["Value"], hex_to_linear(metal_hex), (x + 900, y))
    _mix_into(nt, bsdf, "Metallic", mask.outputs["Value"], (1.0, 1.0, 1.0, 1.0), (x + 900, y - 250))
    _mix_into(nt, bsdf, "Roughness", mask.outputs["Value"], (metal_roughness,) * 3 + (1.0,), (x + 900, y - 500))
    return mask


def add_cavity_dirt(mat, dirt_hex="#2E2A24", distance=0.2, amount=0.6, noise_scale=8.0):
    """Dirt accumulating in concavities: inverted AO x noise. Pushes roughness up and metallic to 0 there."""
    nt = mat.node_tree
    bsdf = _principled(mat)
    x, y = -900, -300
    ao = _new(nt, "ShaderNodeAmbientOcclusion", (x, y), samples=8, inside=False, only_local=True)
    ao.inputs["Distance"].default_value = distance
    inv = _new(nt, "ShaderNodeInvert", (x + 200, y))
    nt.links.new(ao.outputs["AO"], inv.inputs["Color"])
    noise = _new(nt, "ShaderNodeTexNoise", (x + 200, y - 250))
    noise.inputs["Scale"].default_value = noise_scale
    mul = _new(nt, "ShaderNodeMath", (x + 400, y), operation="MULTIPLY")
    nt.links.new(inv.outputs["Color"], mul.inputs[0])
    nt.links.new(noise.outputs["Fac"], mul.inputs[1])
    ramp = _new(nt, "ShaderNodeValToRGB", (x + 600, y))
    ramp.color_ramp.elements[0].position = 0.15
    ramp.color_ramp.elements[1].position = 0.15 + 0.6 * (1.0 - amount) + 0.1
    nt.links.new(mul.outputs["Value"], ramp.inputs["Fac"])
    ramp.label = "CavityDirtMask"
    _mix_into(nt, bsdf, "Base Color", ramp.outputs["Color"], hex_to_linear(dirt_hex), (x + 900, y))
    _mix_into(nt, bsdf, "Roughness", ramp.outputs["Color"], (0.9, 0.9, 0.9, 1.0), (x + 900, y - 250))
    _mix_into(nt, bsdf, "Metallic", ramp.outputs["Color"], (0.0, 0.0, 0.0, 1.0), (x + 900, y - 500))
    return ramp


def add_roughness_breakup(mat, spread=0.15, scale=4.0):
    """Large blotches + speckle + micro noise mapped to +-spread around the current roughness."""
    nt = mat.node_tree
    bsdf = _principled(mat)
    x, y = -900, -1100
    n1 = _new(nt, "ShaderNodeTexNoise", (x, y))
    n1.inputs["Scale"].default_value = scale
    n1.inputs["Detail"].default_value = 8.0
    n1.inputs["Roughness"].default_value = 0.7
    vor = _new(nt, "ShaderNodeTexVoronoi", (x, y - 250))
    vor.inputs["Scale"].default_value = scale * 15
    n3 = _new(nt, "ShaderNodeTexNoise", (x, y - 500))
    n3.inputs["Scale"].default_value = scale * 50
    m1 = _new(nt, "ShaderNodeMath", (x + 250, y - 250), operation="MULTIPLY_ADD")
    nt.links.new(vor.outputs["Distance"], m1.inputs[0])
    m1.inputs[1].default_value = 0.3
    nt.links.new(n1.outputs["Fac"], m1.inputs[2])
    m2 = _new(nt, "ShaderNodeMath", (x + 450, y - 250), operation="MULTIPLY_ADD")
    nt.links.new(n3.outputs["Fac"], m2.inputs[0])
    m2.inputs[1].default_value = 0.15
    nt.links.new(m1.outputs["Value"], m2.inputs[2])
    target = bsdf.inputs["Roughness"]
    base = _source_of(target)
    rng = _new(nt, "ShaderNodeMapRange", (x + 700, y - 250))
    rng.inputs["From Min"].default_value = 0.0
    rng.inputs["From Max"].default_value = 1.45
    rng.inputs["To Min"].default_value = -spread
    rng.inputs["To Max"].default_value = spread
    nt.links.new(m2.outputs["Value"], rng.inputs["Value"])
    add = _new(nt, "ShaderNodeMath", (x + 900, y - 250), operation="ADD", use_clamp=True)
    if base is not None:
        nt.links.new(base, add.inputs[0])
    else:
        add.inputs[0].default_value = float(target.default_value)
    nt.links.new(rng.outputs["Result"], add.inputs[1])
    for l in list(target.links):
        nt.links.remove(l)
    nt.links.new(add.outputs["Value"], target)
    return add


# --------------------------------------------------------------------------- palette (low-poly)

def palette_material(name, hex_colors, cols=None, roughness=0.75, image_name=None):
    """One tiny image of flat colour cells + Closest interpolation. Returns the material; the image is
    stored as `mat['palette_cols']` / `mat['palette_rows']` for assign_palette."""
    n = len(hex_colors)
    cols = cols or min(n, 8)
    rows = math.ceil(n / cols)
    img = bpy.data.images.new(image_name or ("T_" + name[2:] if name.startswith("M_") else "T_" + name) + "_Palette", cols, rows, alpha=False)
    px = [0.0] * (cols * rows * 4)
    for i, hx in enumerate(hex_colors):
        r, c = divmod(i, cols)
        lin = hex_to_linear(hx)
        # byte images store sRGB codes: write the sRGB values directly
        h = hx.lstrip("#")
        srgb = [int(h[j:j + 2], 16) / 255.0 for j in (0, 2, 4)]
        base = ((rows - 1 - r) * cols + c) * 4
        px[base:base + 4] = [srgb[0], srgb[1], srgb[2], 1.0]
    img.pixels = px
    img.pack()
    mat = pbr_material(name, base_hex=hex_colors[0], roughness=roughness, metallic=0.0)
    nt = mat.node_tree
    bsdf = _principled(mat)
    tex = _new(nt, "ShaderNodeTexImage", (-400, 0), interpolation="Closest")
    tex.image = img
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    mat["palette_cols"] = cols
    mat["palette_rows"] = rows
    mat["palette_hex"] = list(hex_colors)
    return mat


def assign_palette(obj, mat, face_to_index, default_index=0):
    """Collapse each face's UVs to the centre of its palette cell. face_to_index: {face_index: palette_index}
    or a callable(polygon) -> palette_index."""
    me = obj.data
    if mat.name not in [m.name for m in me.materials if m]:
        me.materials.append(mat)
    slot = [m.name for m in me.materials].index(mat.name)
    cols, rows = int(mat["palette_cols"]), int(mat["palette_rows"])
    uv = me.uv_layers.active or me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        idx = face_to_index(poly) if callable(face_to_index) else face_to_index.get(poly.index, default_index)
        r, c = divmod(int(idx), cols)
        u, v = (c + 0.5) / cols, (rows - 1 - r + 0.5) / rows
        for li in poly.loop_indices:
            uv.uv[li].vector = (u, v)
        poly.material_index = slot
    me.update()
    return slot


# --------------------------------------------------------------------------- glTF occlusion

def gltf_occlusion_output(mat, ao_image):
    """Hook an AO image into the 'glTF Material Output' group so the glTF exporter writes occlusion."""
    nt = mat.node_tree
    grp = bpy.data.node_groups.get("glTF Material Output")
    if grp is None:
        grp = bpy.data.node_groups.new("glTF Material Output", "ShaderNodeTree")
        grp.interface.new_socket("Occlusion", in_out="INPUT", socket_type="NodeSocketFloat")
        grp.nodes.new("NodeGroupInput")
    node = _new(nt, "ShaderNodeGroup", (300, -400))
    node.node_tree = grp
    tex = _new(nt, "ShaderNodeTexImage", (0, -400))
    tex.image = ao_image
    ao_image.colorspace_settings.name = "Non-Color"
    nt.links.new(tex.outputs["Color"], node.inputs["Occlusion"])
    return node


# --------------------------------------------------------------------------- QA

def texture_stats(path, kind=None):
    """Numbers the tech artist checks. kind: basecolor | roughness | metallic | normal | ao (guessed from name)."""
    import numpy as np
    name = os.path.basename(path).lower()
    kind = kind or next((k for k in ("basecolor", "roughness", "metallic", "normal", "ao", "orm", "emissive") if k in name.replace("_", "")), "unknown")
    img = bpy.data.images.load(path, check_existing=False)
    is_float = img.is_float
    img.colorspace_settings.name = "Non-Color"  # read stored codes untouched
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    bpy.data.images.remove(img)
    rgb = px[:, :, :3]
    rep = dict(path=path, kind=kind, size=[w, h], bit_depth=16 if is_float else 8,
               power_of_two=(w & (w - 1) == 0) and (h & (h - 1) == 0),
               mean=[round(float(v), 3) for v in rgb.mean(axis=(0, 1))],
               min=[round(float(v), 3) for v in rgb.min(axis=(0, 1))],
               max=[round(float(v), 3) for v in rgb.max(axis=(0, 1))],
               std=[round(float(v), 4) for v in rgb.std(axis=(0, 1))])
    flags = []
    if kind == "basecolor":
        codes = rgb * 255.0
        lum = codes.mean(axis=2)
        dark = float((lum < 30).mean())
        bright = float((lum > 240).mean())
        rep.update(pct_below_30=round(dark * 100, 2), pct_above_240=round(bright * 100, 2))
        if dark > 0.05:
            flags.append("more than 5% of pixels darker than sRGB 30 (unused UV space or crushed albedo)")
        if bright > 0.02:
            flags.append("pixels brighter than sRGB 240")
    if kind == "metallic":
        mid = float(((rgb[:, :, 0] > 0.1) & (rgb[:, :, 0] < 0.9)).mean())
        rep.update(pct_mid_grey=round(mid * 100, 2))
        if mid > 0.05:
            flags.append("metallic not bimodal: >5% grey pixels")
    if kind == "roughness":
        m = float(rgb[:, :, 0].mean())
        if m < 0.25 or m > 0.85:
            flags.append(f"roughness mean {m:.2f} outside 0.25-0.85")
        if rep["std"][0] < 0.01:
            flags.append("roughness is flat (no breakup)")
    if kind == "normal":
        blue_min = float(rgb[:, :, 2].min())
        rep.update(blue_min=round(blue_min, 3))
        if blue_min <= 0.5:
            flags.append("normal map blue channel <= 0.5 somewhere (not a tangent-space OpenGL normal)")
        vec = rgb * 2.0 - 1.0
        length = np.sqrt((vec ** 2).sum(axis=2))
        rep.update(vector_length_mean=round(float(length.mean()), 3))
    rep["flags"] = flags
    return rep
