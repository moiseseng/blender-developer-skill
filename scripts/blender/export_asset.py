# SPDX-License-Identifier: MIT
"""
export_asset.py - export mesh objects with per-target presets and verify the result (Blender 4.2+ / 5.x).

Presets encode the axis, scale, smoothing and texture-path conventions each target expects, so the
same asset imports at the right size and orientation everywhere. Parameter names below were checked
against the Blender 5.2 operator definitions; references/export-targets.md explains the choices.

CLI:
    blender -b scene.blend --python export_asset.py -- --objects SM_Crate_A --asset Crate_A
        --out /path/assets/Crate_A/export --presets glb,fbx_unity,fbx_unreal,obj [--triangulate] [--no-verify]

MCP:
    result = export_asset.export(objects=["SM_Crate_A"], asset_name="Crate_A",
                                 out_dir="/path/assets/Crate_A/export", presets=["glb", "fbx_unity"])
"""

import json
import math
import os
import struct
import sys

import bpy

# Which Blender data to ship for a static asset. Lights/cameras never go into an asset file.
_FBX_COMMON = dict(
    use_selection=True,
    object_types={"MESH", "EMPTY", "ARMATURE"},
    use_mesh_modifiers=True,
    apply_unit_scale=True,
    global_scale=1.0,
    mesh_smooth_type="OFF",       # ship custom normals; importers rebuild smoothing from them
    use_tspace=True,              # tangents for normal maps (needs tris/quads only)
    add_leaf_bones=False,
    bake_anim=False,
    path_mode="COPY",
    embed_textures=False,
    use_custom_props=False,
    colors_type="SRGB",
)

PRESETS = {
    # glTF 2.0 is the reference PBR format: metres, Y-up, front -Y in Blender = +Z in glTF, metal/rough, OpenGL
    # normals. Godot, three.js, Babylon, Roblox and Blender round-trip it with no settings to remember.
    # export_extras carries custom properties (Godot import hints like "-col" live in object names anyway).
    "glb": dict(kind="gltf", ext=".glb", export_format="GLB", export_extras=True),
    "gltf": dict(kind="gltf", ext=".gltf", export_format="GLTF_SEPARATE", export_extras=True),
    # Unity: FBX, -Z forward / Y up, FBX_SCALE_NONE writes centimetre units that Unity imports 1:1 (its importer
    # shows scale factor 0.01 + "convert units"; that is normal). Unity rebuilds tangents (MikkTSpace) itself.
    # bake_space_transform removes the -89.98 deg X root rotation; the export() function turns it off automatically
    # when an armature is in the selection (the option is documented as broken for armatures). The alternative is
    # Unity's importer option "Bake Axis Conversion".
    "fbx_unity": dict(kind="fbx", ext=".fbx", axis_forward="-Z", axis_up="Y", apply_scale_options="FBX_SCALE_NONE",
                      use_space_transform=True, bake_space_transform=True, mesh_smooth_type="OFF", use_tspace=False),
    # Unreal: 1 UU = 1 cm, Z-up, +X forward in-engine; its importer converts the Y-up FBX itself (Convert Scene), so
    # no space-transform bake. FBX_SCALE_NONE gives 1 m -> 100 cm. Unreal expects smoothing groups or imported
    # normals: FACE smoothing + triangles + tangents. One FBX per prop: custom collision (UCX_<Mesh>_00) and sockets
    # import only for the first mesh in a file. Model facing -Y lands on Unreal -Y; tick "Force Front XAxis" or build
    # the asset facing +X when the engine's forward matters.
    "fbx_unreal": dict(kind="fbx", ext=".fbx", axis_forward="-Z", axis_up="Y", apply_scale_options="FBX_SCALE_NONE",
                       use_space_transform=True, bake_space_transform=False, mesh_smooth_type="FACE", use_tspace=True,
                       use_triangles=True),
    # Roblox 3D Importer (FBX/OBJ/glTF): Roblox's own Blender guide asks for "FBX Unit Scale" with every other scale
    # at 1.0, textures copied and embedded, no leaf bones. 1 stud = 0.28 m; the importer's "Scale unit" re-interprets.
    "fbx_roblox": dict(kind="fbx", ext=".fbx", axis_forward="-Z", axis_up="Y", apply_scale_options="FBX_SCALE_UNITS",
                       use_space_transform=True, bake_space_transform=False, mesh_smooth_type="OFF",
                       path_mode="COPY", embed_textures=True),
    # Generic FBX (DCC interchange): Blender defaults.
    "fbx": dict(kind="fbx", ext=".fbx", axis_forward="-Z", axis_up="Y", apply_scale_options="FBX_SCALE_NONE",
                use_space_transform=True, bake_space_transform=False),
    "obj": dict(kind="obj", ext=".obj"),
    # USD: Convert Orientation on so Y-up consumers (usdz viewers, most DCCs) get -Z forward / Y up.
    "usd": dict(kind="usd", ext=".usdc", convert_orientation=True, export_global_forward_selection="NEGATIVE_Z",
                export_global_up_selection="Y"),
    "usdz": dict(kind="usd", ext=".usdz", convert_orientation=True, export_global_forward_selection="NEGATIVE_Z",
                 export_global_up_selection="Y"),
    "stl": dict(kind="stl", ext=".stl"),
}


# --------------------------------------------------------------------------- selection helpers

def _select_only(objs):
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.hide_set(False)
        o.hide_viewport = False
        o.select_set(True)
    if objs:
        bpy.context.view_layer.objects.active = objs[0]


def _resolve(objects, collection):
    if objects:
        objs = [bpy.data.objects[n] for n in objects if n in bpy.data.objects]
    elif collection and collection in bpy.data.collections:
        objs = list(bpy.data.collections[collection].all_objects)
    else:
        objs = [o for o in bpy.context.scene.objects if o.select_get()] or list(bpy.context.scene.objects)
    return [o for o in objs if o.type in {"MESH", "EMPTY", "ARMATURE"}]


def _has_normal_map(objs):
    for o in objs:
        if o.type != "MESH":
            continue
        for slot in o.material_slots:
            m = slot.material
            if m and m.use_nodes and any(n.type == "NORMAL_MAP" for n in m.node_tree.nodes):
                return True
    return False


def _world_bbox(objs):
    import mathutils
    pts = []
    for o in objs:
        if o.type != "MESH":
            continue
        for c in o.bound_box:
            pts.append(o.matrix_world @ mathutils.Vector(c))
    if not pts:
        return None
    return [[round(min(p[i] for p in pts), 4) for i in range(3)], [round(max(p[i] for p in pts), 4) for i in range(3)]]


def _tri_count(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    total = 0
    for o in objs:
        if o.type != "MESH":
            continue
        me = o.evaluated_get(dg).to_mesh()
        total += sum(max(len(p.vertices) - 2, 0) for p in me.polygons)
        o.evaluated_get(dg).to_mesh_clear()
    return total


# --------------------------------------------------------------------------- GLB inspection

def inspect_glb(path):
    """Parse a .glb header without external libraries: counts, bbox (converted back to Z-up), images."""
    with open(path, "rb") as fh:
        magic, _version, _length = struct.unpack("<4sII", fh.read(12))
        if magic != b"glTF":
            return {"error": "not a GLB"}
        chunk_len, chunk_type = struct.unpack("<II", fh.read(8))
        doc = json.loads(fh.read(chunk_len).decode("utf-8"))
    accessors = doc.get("accessors", [])
    verts = 0
    tris = 0
    mins, maxs = [], []
    for mesh in doc.get("meshes", []):
        for prim in mesh.get("primitives", []):
            pos = prim.get("attributes", {}).get("POSITION")
            if pos is not None:
                acc = accessors[pos]
                verts += acc["count"]
                if "min" in acc:
                    mins.append(acc["min"])
                    maxs.append(acc["max"])
            idx = prim.get("indices")
            tris += (accessors[idx]["count"] // 3) if idx is not None else (accessors[pos]["count"] // 3 if pos is not None else 0)
    bbox = None
    if mins:
        lo = [min(m[i] for m in mins) for i in range(3)]
        hi = [max(m[i] for m in maxs) for i in range(3)]
        # glTF is Y-up: (x, y, z)_gltf = (x, z, -y)_blender  ->  blender = (x, -z, y)
        bbox = [[round(lo[0], 4), round(-hi[2], 4), round(lo[1], 4)], [round(hi[0], 4), round(-lo[2], 4), round(hi[1], 4)]]
    return dict(
        generator=doc.get("asset", {}).get("generator"),
        nodes=len(doc.get("nodes", [])),
        meshes=len(doc.get("meshes", [])),
        primitives=sum(len(m.get("primitives", [])) for m in doc.get("meshes", [])),
        materials=[m.get("name") for m in doc.get("materials", [])],
        images=len(doc.get("images", [])),
        textures=len(doc.get("textures", [])),
        vertices=verts,
        triangles=tris,
        bbox_blender_space=bbox,
        extensions_used=doc.get("extensionsUsed", []),
    )


def inspect_fbx(path):
    """Re-import an FBX into a throwaway scene with the 5.x C++ importer and report what an engine would see:
    object names, bounding size in metres, root rotation (should be 0,0,0) and scale."""
    import mathutils
    src = bpy.context.scene
    tmp = bpy.data.scenes.new("EXPORT_VERIFY_TMP")
    report = {}
    try:
        with bpy.context.temp_override(scene=tmp):
            if bpy.context.window:
                bpy.context.window.scene = tmp
            if hasattr(bpy.ops.wm, "fbx_import"):
                bpy.ops.wm.fbx_import(filepath=path)
            else:
                bpy.ops.import_scene.fbx(filepath=path)
        objs = [o for o in tmp.objects if o.type == "MESH"]
        bpy.context.view_layer.update()
        pts = [o.matrix_world @ mathutils.Vector(c) for o in objs for c in o.bound_box]
        dims = [round(max(p[i] for p in pts) - min(p[i] for p in pts), 3) for i in range(3)] if pts else None
        roots = [o for o in tmp.objects if o.parent is None]
        report = dict(
            objects=[o.name for o in tmp.objects],
            dims_m=dims,
            root_rotation_deg=[[round(math.degrees(a), 2) for a in o.rotation_euler] for o in roots],
            root_scale=[[round(s, 4) for s in o.scale] for o in roots],
            triangles=sum(sum(max(len(p.vertices) - 2, 0) for p in o.data.polygons) for o in objs),
            materials=sorted({m.name for o in objs for m in o.data.materials if m}),
        )
    except Exception as ex:
        report = {"error": str(ex)}
    finally:
        for o in list(tmp.objects):
            data = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            if data is not None and data.users == 0:
                try:
                    (bpy.data.meshes if isinstance(data, bpy.types.Mesh) else bpy.data.armatures).remove(data)
                except Exception:
                    pass
        if bpy.context.window:
            bpy.context.window.scene = src
        bpy.data.scenes.remove(tmp)
    return report


# --------------------------------------------------------------------------- export

def export(objects=None, collection=None, asset_name=None, out_dir=".", presets=("glb",), triangulate=False,
           draco=False, verify=True, overrides=None):
    objs = _resolve(objects, collection)
    if not objs:
        return {"error": "no objects to export"}
    asset_name = asset_name or objs[0].name
    overrides = overrides or {}
    os.makedirs(out_dir, exist_ok=True)
    _select_only(objs)

    pre = dict(bbox=_world_bbox(objs), tris=_tri_count(objs), objects=[o.name for o in objs])
    files = []
    for key in presets:
        if key not in PRESETS:
            files.append(dict(preset=key, error="unknown preset"))
            continue
        preset = dict(PRESETS[key])
        preset.update(overrides.get(key, {}))
        kind = preset.pop("kind")
        ext = preset.pop("ext")
        sub = os.path.join(out_dir, key)
        os.makedirs(sub, exist_ok=True)
        path = os.path.join(sub, asset_name + ext)
        entry = dict(preset=key, path=path)
        try:
            if kind == "gltf":
                kwargs = dict(
                    filepath=path, export_format=preset["export_format"], use_selection=True,
                    export_apply=True, export_yup=True, export_texcoords=True, export_normals=True,
                    export_tangents=_has_normal_map(objs), export_materials="EXPORT",
                    export_image_format="AUTO", export_animations=False, export_skins=False,
                    export_morph=False, export_cameras=False, export_lights=False, export_extras=False,
                    export_draco_mesh_compression_enable=bool(draco),
                )
                if preset["export_format"] == "GLTF_SEPARATE":
                    kwargs["export_texture_dir"] = "textures"
                kwargs.update({k: v for k, v in preset.items() if k not in {"export_format"}})
                bpy.ops.export_scene.gltf(**kwargs)
            elif kind == "fbx":
                kwargs = dict(_FBX_COMMON)
                kwargs.update(filepath=path, use_triangles=bool(triangulate))
                kwargs.update(preset)
                if kwargs.get("bake_space_transform") and any(o.type == "ARMATURE" for o in objs):
                    kwargs["bake_space_transform"] = False  # documented as broken with armatures
                    entry["note"] = "bake_space_transform disabled: armature in selection"
                bpy.ops.export_scene.fbx(**kwargs)
            elif kind == "obj":
                bpy.ops.wm.obj_export(
                    filepath=path, export_selected_objects=True, apply_modifiers=True, export_uv=True,
                    export_normals=True, export_materials=True, export_pbr_extensions=True, path_mode="COPY",
                    forward_axis="NEGATIVE_Z", up_axis="Y", export_triangulated_mesh=bool(triangulate),
                    global_scale=1.0, **{k: v for k, v in preset.items()})
            elif kind == "usd":
                kwargs = dict(
                    filepath=path, selected_objects_only=True, export_materials=True, export_textures_mode="NEW",
                    relative_paths=True, evaluation_mode="RENDER", export_meshes=True, export_lights=False,
                    export_cameras=False, export_animation=False, triangulate_meshes=bool(triangulate),
                    convert_orientation=False)
                kwargs.update(preset)
                bpy.ops.wm.usd_export(**kwargs)
            elif kind == "stl":
                bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True, apply_modifiers=True,
                                      global_scale=1.0, forward_axis="NEGATIVE_Z", up_axis="Y", **preset)
            entry["bytes"] = os.path.getsize(path) if os.path.exists(path) else 0
            if verify and ext == ".glb" and os.path.exists(path):
                entry["glb"] = inspect_glb(path)
                b = entry["glb"].get("bbox_blender_space")
                if b and pre["bbox"]:
                    entry["bbox_matches_scene"] = all(abs(b[j][i] - pre["bbox"][j][i]) < 1e-3 for j in range(2) for i in range(3))
            if verify and ext == ".fbx" and os.path.exists(path):
                entry["fbx"] = inspect_fbx(path)
                if preset.get("bake_space_transform"):
                    entry["fbx"]["note"] = ("bake_space_transform=True: Blender's own importer shows a 90 deg X root and 0.01 scale "
                                            "by construction; Unity imports it with zero rotation. Dimensions are what to check.")
                dims_src = [round(pre["bbox"][1][i] - pre["bbox"][0][i], 3) for i in range(3)] if pre["bbox"] else None
                entry["dims_match_scene"] = (dims_src is not None and entry["fbx"].get("dims_m") is not None
                                             and all(abs(entry["fbx"]["dims_m"][i] - dims_src[i]) < 2e-3 for i in range(3)))
        except Exception as ex:  # keep going with other presets; report the failure
            entry["error"] = str(ex)
        files.append(entry)

    # Shipped textures alongside (COPY mode) are listed so the manifest can reference them.
    shipped = []
    for root, _dirs, names in os.walk(out_dir):
        for n in names:
            if n.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".exr", ".tga")):
                shipped.append(os.path.relpath(os.path.join(root, n), out_dir))

    report = dict(blender=bpy.app.version_string, asset=asset_name, source=pre, files=files, textures=sorted(shipped))
    with open(os.path.join(out_dir, "export.json"), "w") as fh:   # make_manifest.py and the README read this
        json.dump(report, fh, indent=2)
    return report


def _cli():
    import argparse
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(prog="export_asset")
    p.add_argument("--objects")
    p.add_argument("--collection")
    p.add_argument("--asset")
    p.add_argument("--out", required=True)
    p.add_argument("--presets", default="glb")
    p.add_argument("--triangulate", action="store_true")
    p.add_argument("--draco", action="store_true")
    p.add_argument("--no-verify", action="store_true")
    a = p.parse_args(argv)
    rep = export(objects=a.objects.split(",") if a.objects else None, collection=a.collection, asset_name=a.asset,
                 out_dir=a.out, presets=a.presets.split(","), triangulate=a.triangulate, draco=a.draco,
                 verify=not a.no_verify)
    print(json.dumps(rep, indent=2))
    print("EXPORT_JSON=" + json.dumps(rep))


if __name__ == "__main__":
    _cli()
