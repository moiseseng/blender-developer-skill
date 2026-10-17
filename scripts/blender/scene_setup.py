# SPDX-License-Identifier: MIT
"""
scene_setup.py - start a clean, correctly configured asset scene (Blender 4.2+ / 5.x).

Metric units at 1 BU = 1 m, named collections per pipeline stage, optional reference
images loaded as image-empties, neutral render defaults, and the .blend saved where the
brief says. Running it twice on the same file is safe: existing collections are reused.

CLI:
    blender -b --python scene_setup.py -- --asset Crate_A --save /path/to/assets/Crate_A/source/Crate_A.blend
        [--refs ref1.png,ref2.jpg] [--no-clear]

MCP:
    result = scene_setup.setup(asset_name="Crate_A", save_path="...", reference_images=[...])
"""

import json
import os
import sys

import bpy

STAGE_COLLECTIONS = ("Reference", "Blockout", "Model", "Bake", "Export")


def _get_or_create_collection(name, parent):
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
    if coll.name not in parent.children:
        parent.children.link(coll)
    return coll


def clear_scene(keep_cameras_lights=False):
    for obj in list(bpy.data.objects):
        if keep_cameras_lights and obj.type in {"CAMERA", "LIGHT"}:
            continue
        bpy.data.objects.remove(obj, do_unlink=True)
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.curves, bpy.data.node_groups):
        for datablock in list(block):
            if datablock.users == 0:
                block.remove(datablock)


def add_reference_image(path, collection, index=0, size=1.0):
    """Load an image as an image-empty standing on the ground, spaced along +X."""
    img = bpy.data.images.load(path, check_existing=True)
    empty = bpy.data.objects.new("REF_" + os.path.splitext(os.path.basename(path))[0], None)
    empty.empty_display_type = "IMAGE"
    empty.data = img
    empty.empty_display_size = size
    empty.empty_image_offset = (-0.5, 0.0)
    empty.location = (index * (size * 1.2), 2.0, 0.0)
    empty.rotation_euler = (1.5707963, 0.0, 0.0)  # stand it up facing -Y
    empty.show_in_front = False
    collection.objects.link(empty)
    return empty


def setup(asset_name, save_path=None, reference_images=None, clear=True, unit_scale=1.0,
          render_engine="BLENDER_EEVEE", view_transform="Standard", resolution=(1280, 720)):
    scene = bpy.context.scene
    if clear:
        clear_scene()

    # Units: metric, 1 BU = 1 m. Every exporter and engine assumes this.
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = unit_scale
    scene.unit_settings.length_unit = "METERS"

    # Collections per stage, under a root named after the asset.
    root = _get_or_create_collection(asset_name, scene.collection)
    stages = {name: _get_or_create_collection(f"{asset_name}_{name}", root) for name in STAGE_COLLECTIONS}
    # Reference and Blockout never render or export.
    stages["Reference"].hide_render = True
    stages["Blockout"].hide_render = True

    refs = []
    for i, path in enumerate(reference_images or []):
        if os.path.exists(path):
            refs.append(add_reference_image(path, stages["Reference"], i).name)

    # Render defaults for review renders. Standard view transform keeps flat/stylized colors
    # exactly as authored; switch to AgX for realistic PBR review in render_review.
    if render_engine in {e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items} or render_engine == "CYCLES":
        try:
            scene.render.engine = render_engine
        except TypeError:
            pass
    scene.view_settings.view_transform = view_transform
    scene.render.resolution_x, scene.render.resolution_y = resolution
    scene.render.film_transparent = False

    saved = None
    if save_path:
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(save_path))
        saved = os.path.abspath(save_path)

    return dict(
        blender=bpy.app.version_string,
        asset=asset_name,
        collections={k: v.name for k, v in stages.items()},
        reference_images=refs,
        unit_scale=unit_scale,
        saved=saved,
    )


def _cli():
    import argparse
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(prog="scene_setup")
    p.add_argument("--asset", required=True)
    p.add_argument("--save")
    p.add_argument("--refs", help="comma-separated image paths")
    p.add_argument("--no-clear", action="store_true")
    a = p.parse_args(argv)
    rep = setup(a.asset, save_path=a.save, reference_images=a.refs.split(",") if a.refs else None, clear=not a.no_clear)
    print("SETUP_JSON=" + json.dumps(rep))


if __name__ == "__main__":
    _cli()
