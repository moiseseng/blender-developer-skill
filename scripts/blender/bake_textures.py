# SPDX-License-Identifier: MIT
"""
bake_textures.py - bake an object's (procedural) materials into a PBR texture set and, optionally,
rewire the object to a single baked material so glTF/FBX export carries real textures (Blender 4.2+ / 5.x).

Maps: basecolor (sRGB), roughness, metallic, normal (tangent, OpenGL +Y), ao, emissive (all Non-Color
except basecolor/emissive), plus an optional packed ORM (R=AO, G=Roughness, B=Metallic) for Unreal.
Base colour and metallic are routed through the Emission socket and baked as EMIT: the DIFFUSE colour
pass is black wherever Metallic is 1, and metallic has no bake pass at all.
Selected-to-active (high-poly to low-poly) is supported with `high_objects` + `cage_extrusion`.

CLI:
    blender -b scene.blend --python bake_textures.py -- --object SM_Crate_A[,SM_Crate_A_Lid] --out /path/textures
        [--size 2048] [--maps basecolor,roughness,metallic,normal,ao] [--samples 32] [--margin 16]
        [--high SM_Crate_A_High] [--cage-extrusion 0.02] [--prefix T_Crate_A] [--no-rewire] [--orm] [--save]

MCP:
    result = bake_textures.bake("SM_Crate_A", out_dir="...", size=2048, maps=("basecolor", "roughness", "normal"))

Requires one non-overlapping UV map on the low-poly object. Run mesh_audit first.
"""

import json
import os
import sys

import bpy

def _ensure_node_tree(mat):
    """Blender 5.x materials are node-based by default; older versions need use_nodes (removed in 6.0)."""
    if getattr(mat, "node_tree", None) is None:
        try:
            mat.use_nodes = True
        except AttributeError:
            pass


SUFFIX = dict(basecolor="BaseColor", roughness="Roughness", metallic="Metallic", normal="Normal",
              ao="AO", emissive="Emissive", orm="ORM")
NONCOLOR = {"roughness", "metallic", "normal", "ao", "orm"}


def _select_for_bake(lows, highs):
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for h in highs:
        h.hide_set(False)
        h.hide_render = False
        h.select_set(True)
    for low in lows:
        low.hide_set(False)
        low.hide_render = False
        low.select_set(True)
    bpy.context.view_layer.objects.active = lows[0]


class _Isolate:
    """Hide every other render-visible mesh from the bake (AO and selected-to-active rays see the whole scene)."""

    def __init__(self, keep):
        keep_ids = {o.name for o in keep}
        self.saved = [(o, o.hide_render) for o in bpy.context.scene.objects if o.type in {"MESH", "CURVE", "META"} and o.name not in keep_ids]
        for o, _h in self.saved:
            o.hide_render = True

    def restore(self):
        for o, h in self.saved:
            o.hide_render = h


def _principled(mat):
    for n in mat.node_tree.nodes:
        if n.type == "BSDF_PRINCIPLED":
            return n
    return None


def _ensure_materials(obj):
    """Every slot needs a node material so a target image node can be made active in each."""
    if not obj.material_slots:
        m = bpy.data.materials.new(obj.name + "_Mat")
        _ensure_node_tree(m)
        obj.data.materials.append(m)
    for slot in obj.material_slots:
        if slot.material is None:
            slot.material = bpy.data.materials.new(obj.name + "_Mat")
        _ensure_node_tree(slot.material)


def _new_image(name, size, float_buffer, noncolor):
    img = bpy.data.images.get(name)
    if img:
        bpy.data.images.remove(img)
    img = bpy.data.images.new(name, size, size, alpha=False, float_buffer=float_buffer)
    img.colorspace_settings.name = "Non-Color" if noncolor else "sRGB"
    img.generated_color = (0.5, 0.5, 1.0, 1.0) if "Normal" in name else (0, 0, 0, 1)
    return img


class _EmitRoute:
    """Temporarily drive Emission with a socket's input (link or constant) so EMIT bakes that channel."""

    def __init__(self, mats, socket_name):
        self.saved = []
        for m in mats:
            p = _principled(m)
            if not p:
                continue
            nt = m.node_tree
            src_sock = p.inputs[socket_name]
            emis = p.inputs["Emission Color"]
            strength = p.inputs["Emission Strength"]
            state = dict(mat=m, emis_links=[(l.from_socket, l.to_socket) for l in emis.links],
                         emis_default=tuple(emis.default_value), strength_links=[(l.from_socket, l.to_socket) for l in strength.links],
                         strength_default=strength.default_value, base_links=[(l.from_socket, l.to_socket) for l in p.inputs["Base Color"].links],
                         base_default=tuple(p.inputs["Base Color"].default_value))
            for l in list(emis.links) + list(strength.links):
                nt.links.remove(l)
            if src_sock.links:
                nt.links.new(src_sock.links[0].from_socket, emis)
            else:
                v = src_sock.default_value
                if isinstance(v, float):
                    emis.default_value = (v, v, v, 1.0)
                else:
                    emis.default_value = tuple(v)
            strength.default_value = 1.0
            # Kill base color so only emission contributes to the EMIT pass.
            for l in list(p.inputs["Base Color"].links):
                nt.links.remove(l)
            p.inputs["Base Color"].default_value = (0, 0, 0, 1)
            self.saved.append(state)

    def restore(self):
        for s in self.saved:
            nt = s["mat"].node_tree
            p = _principled(s["mat"])
            for sock_name in ("Emission Color", "Emission Strength", "Base Color"):
                for l in list(p.inputs[sock_name].links):
                    nt.links.remove(l)
            p.inputs["Emission Color"].default_value = s["emis_default"]
            p.inputs["Emission Strength"].default_value = s["strength_default"]
            p.inputs["Base Color"].default_value = s["base_default"]
            for a, b in s["emis_links"] + s["strength_links"] + s["base_links"]:
                nt.links.new(a, b)


def _bake_pass(lows, highs, mats, img, bake_type, margin, cage_extrusion, max_ray, pass_filter=None, normal_space="TANGENT"):
    nodes_added = []
    for m in mats:
        nt = m.node_tree
        node = nt.nodes.new("ShaderNodeTexImage")
        node.image = img
        node.name = "BAKE_TARGET"
        for n in nt.nodes:
            n.select = False
        node.select = True          # 5.0+: bakes only to the image node that is selected AND active
        nt.nodes.active = node
        nodes_added.append((nt, node))
    scene = bpy.context.scene
    bake = scene.render.bake
    bake.margin = margin
    bake.margin_type = "ADJACENT_FACES"
    bake.use_selected_to_active = bool(highs)
    bake.cage_extrusion = cage_extrusion
    bake.max_ray_distance = max_ray
    bake.use_clear = True
    bake.normal_space = normal_space
    bake.normal_r, bake.normal_g, bake.normal_b = "POS_X", "POS_Y", "POS_Z"  # OpenGL convention
    if pass_filter is not None:
        bake.use_pass_direct = "DIRECT" in pass_filter
        bake.use_pass_indirect = "INDIRECT" in pass_filter
        bake.use_pass_color = "COLOR" in pass_filter
    kwargs = dict(type=bake_type, margin=margin, use_selected_to_active=bool(highs), cage_extrusion=cage_extrusion,
                  max_ray_distance=max_ray, normal_space=normal_space, use_clear=True, target="IMAGE_TEXTURES", save_mode="INTERNAL")
    if pass_filter is not None:
        kwargs["pass_filter"] = set(pass_filter)
    _select_for_bake(lows, highs)
    res = bpy.ops.object.bake(**kwargs)
    for nt, node in nodes_added:
        nt.nodes.remove(node)
    return "FINISHED" in res


def _save(img, path):
    """PNG via Image.save(): byte buffers write 8-bit, float buffers write 16-bit, values untouched.
    (Do not use save_render for data maps: it runs the scene's view transform.)"""
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    return path


def pack_orm(ao_path, rough_path, metal_path, out_path):
    """R=AO, G=Roughness, B=Metallic (Unreal packing) via numpy."""
    import numpy as np
    imgs = []
    for p in (ao_path, rough_path, metal_path):
        if p and os.path.exists(p):
            im = bpy.data.images.load(p, check_existing=False)
            im.colorspace_settings.name = "Non-Color"
            w, h = im.size
            px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)[:, :, 0]
            bpy.data.images.remove(im)
        else:
            px = None
        imgs.append(px)
    ref = next(i for i in imgs if i is not None)
    h, w = ref.shape
    fill = [np.ones((h, w), np.float32), np.full((h, w), 0.5, np.float32), np.zeros((h, w), np.float32)]
    chans = [imgs[i] if imgs[i] is not None else fill[i] for i in range(3)]
    out = np.stack(chans + [np.ones((h, w), np.float32)], axis=-1)
    img = bpy.data.images.new("ORM_tmp", w, h, alpha=False)
    img.colorspace_settings.name = "Non-Color"
    img.pixels = out.ravel().tolist()
    img.filepath_raw = out_path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    return out_path


def rewire_to_baked(obj, files, mat_name):
    """Replace all material slots with one material that reads the baked images."""
    mat = bpy.data.materials.new(mat_name)
    _ensure_node_tree(mat)
    nt = mat.node_tree
    bsdf = _principled(mat)
    x = -600
    for key, path in files.items():
        if key in {"orm"} or not path:
            continue
        img = bpy.data.images.load(path, check_existing=True)
        img.colorspace_settings.name = "Non-Color" if key in NONCOLOR else "sRGB"
        node = nt.nodes.new("ShaderNodeTexImage")
        node.image = img
        node.location = (x, 300 - 300 * list(files).index(key))
        node.label = SUFFIX[key]
        if key == "basecolor":
            nt.links.new(node.outputs["Color"], bsdf.inputs["Base Color"])
        elif key == "roughness":
            nt.links.new(node.outputs["Color"], bsdf.inputs["Roughness"])
        elif key == "metallic":
            nt.links.new(node.outputs["Color"], bsdf.inputs["Metallic"])
        elif key == "emissive":
            nt.links.new(node.outputs["Color"], bsdf.inputs["Emission Color"])
            bsdf.inputs["Emission Strength"].default_value = 1.0
        elif key == "normal":
            nm = nt.nodes.new("ShaderNodeNormalMap")
            nm.location = (x + 300, -600)
            nt.links.new(node.outputs["Color"], nm.inputs["Color"])
            nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
        elif key == "ao":
            # glTF carries occlusion separately; Blender's exporter picks it up from a glTF Settings group.
            # Keep it unlinked here (multiplying into base color double-darkens in engines that apply AO).
            pass
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    return mat


def _default_prefix(names):
    """SM_TreasureChest_Body, SM_TreasureChest_Lid -> T_TreasureChest."""
    parts = names[0].split("_")
    if parts and parts[0] in {"SM", "SK", "SMP", "BLK"}:
        parts = parts[1:]
    return "T_" + (parts[0] if parts else names[0])


def bake(object_name, out_dir, size=2048, maps=("basecolor", "roughness", "metallic", "normal", "ao"), samples=32,
         margin=16, high_objects=None, cage_extrusion=0.0, max_ray_distance=0.0, prefix=None, rewire=True,
         orm=False, save_blend=False, isolate=True):
    """Bake one texture set. object_name: a name or a list of names whose UVs share one 0-1 space (one
    texture for the whole asset). With high_objects (selected-to-active) exactly one low object is allowed.
    isolate hides every other render-visible object during the bake (AO and rays see only the asset)."""
    names = [object_name] if isinstance(object_name, str) else list(object_name)
    lows = [bpy.data.objects.get(n) for n in names]
    if any(o is None or o.type != "MESH" for o in lows):
        return {"error": f"mesh object(s) not found: {[n for n, o in zip(names, lows) if o is None or o.type != 'MESH']}"}
    if any(not o.data.uv_layers for o in lows):
        return {"error": "an object has no UV map; unwrap first"}
    highs = [bpy.data.objects[n] for n in (high_objects or []) if n in bpy.data.objects]
    if highs and len(lows) > 1:
        return {"error": "selected-to-active baking takes one low-poly object at a time"}
    prefix = prefix or _default_prefix(names)
    os.makedirs(out_dir, exist_ok=True)

    scene = bpy.context.scene
    prev_engine = scene.render.engine
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.device = "CPU"
    scene.cycles.use_denoising = False

    source_objs = highs if highs else lows
    for o in source_objs + lows:
        _ensure_materials(o)
    # The image node must be active in the materials that are *baked from* (the highs in selected-to-active,
    # otherwise the lows themselves); the image is written through the selected objects' UVs.
    mats = list({s.material for o in (lows if highs else source_objs) for s in o.material_slots if s.material})
    iso = _Isolate(lows + highs) if isolate else None

    files = {}
    log = []
    try:
        for key in maps:
            if key not in SUFFIX or key == "orm":
                continue
            path = os.path.join(out_dir, f"{prefix}_{SUFFIX[key]}.png")
            img = _new_image(f"{prefix}_{SUFFIX[key]}", size, float_buffer=(key == "normal"), noncolor=key in NONCOLOR)
            ok = False
            if key == "basecolor":
                # Not DIFFUSE+COLOR: a Principled surface with Metallic 1 has no diffuse colour and bakes black.
                # Routing Base Color through Emission captures the authored colour for metals and dielectrics alike.
                src_mats = list({s.material for o in source_objs for s in o.material_slots if s.material})
                route = _EmitRoute(src_mats, "Base Color")
                try:
                    ok = _bake_pass(lows, highs, mats, img, "EMIT", margin, cage_extrusion, max_ray_distance)
                finally:
                    route.restore()
            elif key == "roughness":
                ok = _bake_pass(lows, highs, mats, img, "ROUGHNESS", margin, cage_extrusion, max_ray_distance)
            elif key == "normal":
                ok = _bake_pass(lows, highs, mats, img, "NORMAL", margin, cage_extrusion, max_ray_distance, normal_space="TANGENT")
            elif key == "ao":
                ok = _bake_pass(lows, highs, mats, img, "AO", margin, cage_extrusion, max_ray_distance)
            elif key == "emissive":
                ok = _bake_pass(lows, highs, mats, img, "EMIT", margin, cage_extrusion, max_ray_distance)
            elif key == "metallic":
                src_mats = list({s.material for o in source_objs for s in o.material_slots if s.material})
                route = _EmitRoute(src_mats, "Metallic")
                try:
                    ok = _bake_pass(lows, highs, mats, img, "EMIT", margin, cage_extrusion, max_ray_distance)
                finally:
                    route.restore()
            if ok:
                _save(img, path)
                files[key] = path
                log.append(f"{key}: ok -> {os.path.basename(path)}")
            else:
                log.append(f"{key}: bake failed")
            bpy.data.images.remove(img)
    finally:
        if iso:
            iso.restore()
        scene.render.engine = prev_engine

    if orm and any(k in files for k in ("ao", "roughness", "metallic")):
        files["orm"] = pack_orm(files.get("ao"), files.get("roughness"), files.get("metallic"),
                                os.path.join(out_dir, f"{prefix}_ORM.png"))

    baked_mat = None
    if rewire and files:
        mat = rewire_to_baked(lows[0], files, "M_" + prefix[2:] + "_Baked")
        for o in lows[1:]:
            o.data.materials.clear()
            o.data.materials.append(mat)
        baked_mat = mat.name

    if save_blend and bpy.data.filepath:
        bpy.ops.wm.save_mainfile()

    return dict(blender=bpy.app.version_string, objects=names, size=size, samples=samples, files=files,
                baked_material=baked_mat, selected_to_active=bool(highs), isolated=bool(isolate), log=log)


def _cli():
    import argparse
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(prog="bake_textures")
    p.add_argument("--object", required=True, help="object name, or comma-separated names sharing one UV space")
    p.add_argument("--out", required=True)
    p.add_argument("--size", type=int, default=2048)
    p.add_argument("--maps", default="basecolor,roughness,metallic,normal,ao")
    p.add_argument("--samples", type=int, default=32)
    p.add_argument("--margin", type=int, default=16)
    p.add_argument("--high", help="comma-separated high-poly object names (selected-to-active)")
    p.add_argument("--cage-extrusion", type=float, default=0.0)
    p.add_argument("--max-ray", type=float, default=0.0)
    p.add_argument("--prefix")
    p.add_argument("--no-rewire", action="store_true")
    p.add_argument("--orm", action="store_true")
    p.add_argument("--save", action="store_true")
    p.add_argument("--no-isolate", action="store_true", help="let other scene objects affect AO / rays")
    a = p.parse_args(argv)
    rep = bake(a.object.split(",") if "," in a.object else a.object, a.out, size=a.size, maps=tuple(a.maps.split(",")),
               samples=a.samples, margin=a.margin, high_objects=a.high.split(",") if a.high else None,
               cage_extrusion=a.cage_extrusion, max_ray_distance=a.max_ray, prefix=a.prefix, rewire=not a.no_rewire,
               orm=a.orm, save_blend=a.save, isolate=not a.no_isolate)
    print(json.dumps(rep, indent=2))
    print("BAKE_JSON=" + json.dumps(rep))


if __name__ == "__main__":
    _cli()
