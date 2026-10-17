# SPDX-License-Identifier: MIT
"""
render_review.py - review renders of an asset: beauty, clay and wireframe views plus a turntable,
tiled into one contact sheet so the result can be judged in a single image (Blender 4.2+ / 5.x).

Works headless: everything is rendered in a temporary scene that links the target objects, so the
working scene, its camera, lights and render settings are untouched.

CLI:
    blender -b scene.blend --python render_review.py -- --objects SM_Crate_A --out /path/renders
        [--modes beauty,clay,wireframe] [--views front,back,left,right,top,three_quarter]
        [--turntable 8] [--res 1280x720] [--engine BLENDER_EEVEE|CYCLES] [--samples 32] [--hdri path.exr]

MCP:
    result = render_review.review(objects=["SM_Crate_A"], out_dir="/path/renders", turntable_frames=8)
"""

import json
import math
import os
import sys

import bpy
from mathutils import Vector, Matrix

def _ensure_node_tree(mat):
    """Blender 5.x materials are node-based by default; older versions need use_nodes (removed in 6.0)."""
    if getattr(mat, "node_tree", None) is None:
        try:
            mat.use_nodes = True
        except AttributeError:
            pass


VIEWS = {
    # name: (direction the camera looks FROM, orthographic?)
    "front": (Vector((0, -1, 0)), True),
    "back": (Vector((0, 1, 0)), True),
    "left": (Vector((-1, 0, 0)), True),
    "right": (Vector((1, 0, 0)), True),
    "top": (Vector((0, 0, 1)), True),
    "three_quarter": (Vector((1, -1, 0.65)).normalized(), False),
    "three_quarter_back": (Vector((-1, 1, 0.65)).normalized(), False),
}


# --------------------------------------------------------------------------- helpers

def _targets(objects, collection):
    if objects:
        objs = [bpy.data.objects[n] for n in objects if n in bpy.data.objects]
    elif collection and collection in bpy.data.collections:
        objs = list(bpy.data.collections[collection].all_objects)
    else:
        objs = [o for o in bpy.context.scene.objects if o.select_get()] or list(bpy.context.scene.objects)
    return [o for o in objs if o.type == "MESH"]


def _bounds(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    center = (lo + hi) / 2
    radius = (hi - lo).length / 2
    return lo, hi, center, radius


def _look_at(obj, target):
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def _place_camera(cam, center, radius, direction, ortho, focal_mm=50.0, fit=1.15, aspect=16 / 9):
    """Frame a sphere of `radius` so it fits in BOTH frame dimensions (the FOV reported by Blender is the
    horizontal one for landscape renders; a tall object would be cropped otherwise)."""
    cam.data.lens = focal_mm
    cam.data.clip_end = max(1000.0, radius * 50)
    cam.data.sensor_fit = "AUTO"
    if ortho:
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = radius * 2 * fit / min(1.0, aspect if aspect < 1 else 1.0 / aspect) if aspect != 1 else radius * 2 * fit
        dist = radius * 4
    else:
        cam.data.type = "PERSP"
        fov = cam.data.angle                       # along the larger frame dimension
        half = math.tan(fov / 2)
        half_small = half * (min(aspect, 1 / aspect))  # tangent of the half-FOV along the smaller dimension
        dist = (radius * fit) / min(half, half_small)
    cam.location = center + direction.normalized() * dist
    _look_at(cam, center)
    if ortho and abs(direction.z) > 0.99:  # top view: keep +Y up on screen
        cam.rotation_euler = (0.0, 0.0, 0.0)


def _studio_lights(scene, center, radius):
    """Three-point area lights scaled to the asset. Energy scales with radius^2 so exposure stays constant."""
    lights = []
    e = 300.0 * max(radius, 0.25) ** 2
    for name, pos, energy, size in (
        ("Key", Vector((1.5, -1.5, 2.0)), e, 2.0),
        ("Fill", Vector((-2.0, -1.0, 1.0)), e * 0.35, 3.0),
        ("Rim", Vector((0.5, 2.0, 1.5)), e * 0.6, 1.5),
    ):
        data = bpy.data.lights.new("REVIEW_" + name, "AREA")
        data.energy = energy
        data.size = size * radius
        data.shape = "SQUARE"
        obj = bpy.data.objects.new("REVIEW_" + name, data)
        obj.location = center + pos * radius * 1.5
        _look_at(obj, center)
        scene.collection.objects.link(obj)
        lights.append(obj)
    return lights


def _world(scene, gray=0.35, hdri=None):
    world = bpy.data.worlds.new("REVIEW_World")
    _ensure_node_tree(world)
    nt = world.node_tree
    bg = nt.nodes.get("Background")
    if hdri and os.path.exists(hdri):
        env = nt.nodes.new("ShaderNodeTexEnvironment")
        env.image = bpy.data.images.load(hdri, check_existing=True)
        nt.links.new(env.outputs["Color"], bg.inputs["Color"])
        bg.inputs["Strength"].default_value = 1.0
    else:
        bg.inputs["Color"].default_value = (gray, gray, gray, 1.0)
        bg.inputs["Strength"].default_value = 1.0
    scene.world = world
    return world


def _ground(scene, center, lo, radius):
    """Shadow-catching ground plane (operator-free so it works from any context)."""
    half = radius * 6
    me = bpy.data.meshes.new("REVIEW_Ground")
    me.from_pydata([(-half, -half, 0), (half, -half, 0), (half, half, 0), (-half, half, 0)], [], [(0, 1, 2, 3)])
    me.update()
    plane = bpy.data.objects.new("REVIEW_Ground", me)
    plane.location = (center.x, center.y, lo.z - 0.0005)
    mat = bpy.data.materials.new("REVIEW_Ground")
    _ensure_node_tree(mat)
    bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.35, 0.35, 0.35, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.9
    mat.diffuse_color = (0.35, 0.35, 0.35, 1.0)
    me.materials.append(mat)
    scene.collection.objects.link(plane)
    return plane


def _clay_copies(scene, objs, wire):
    """Duplicates with a single gray material (and a wireframe shell when wire=True) for Workbench renders."""
    gray = bpy.data.materials.new("REVIEW_Clay")
    gray.diffuse_color = (0.8, 0.8, 0.8, 1.0)
    gray.roughness = 0.6
    black = bpy.data.materials.new("REVIEW_Wire")
    black.diffuse_color = (0.02, 0.02, 0.02, 1.0)
    copies = []
    dg = bpy.context.evaluated_depsgraph_get()
    for o in objs:
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), depsgraph=dg)
        body = bpy.data.objects.new("REVIEW_CLAY_" + o.name, me)
        body.matrix_world = o.matrix_world.copy()
        me.materials.clear()
        me.materials.append(gray)
        scene.collection.objects.link(body)
        copies.append(body)
        if wire:
            wm = bpy.data.meshes.new_from_object(o.evaluated_get(dg), depsgraph=dg)
            shell = bpy.data.objects.new("REVIEW_WIRE_" + o.name, wm)
            shell.matrix_world = o.matrix_world.copy()
            wm.materials.clear()
            wm.materials.append(black)
            mod = shell.modifiers.new("Wire", "WIREFRAME")
            mod.thickness = max(o.dimensions) * 0.004
            mod.use_replace = True
            mod.use_boundary = True
            mod.use_even_offset = True
            scene.collection.objects.link(shell)
            copies.append(shell)
    return copies


def contact_sheet(paths, out_path, cols=3, label_height=0):
    """Tile PNGs of equal size into one image using numpy (bundled with Blender)."""
    import numpy as np
    imgs = []
    for p in paths:
        img = bpy.data.images.load(p, check_existing=False)
        w, h = img.size
        px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
        imgs.append(px)
        bpy.data.images.remove(img)
    if not imgs:
        return None
    h, w = imgs[0].shape[0], imgs[0].shape[1]
    rows = math.ceil(len(imgs) / cols)
    sheet = np.full((rows * h, cols * w, 4), (0.1, 0.1, 0.1, 1.0), dtype=np.float32)
    for i, px in enumerate(imgs):
        r, c = divmod(i, cols)
        # image rows are bottom-up in Blender; place row 0 at the top of the sheet
        y0 = (rows - 1 - r) * h
        sheet[y0:y0 + h, c * w:(c + 1) * w, :] = px[:h, :w, :]
    out = bpy.data.images.new("REVIEW_Sheet", cols * w, rows * h, alpha=True)
    out.pixels = sheet.ravel().tolist()
    out.filepath_raw = out_path
    out.file_format = "PNG"
    out.save()
    bpy.data.images.remove(out)
    return out_path


# --------------------------------------------------------------------------- main

def review(objects=None, collection=None, out_dir="renders", modes=("beauty", "clay", "wireframe"),
           views=("three_quarter", "front", "right", "top"), turntable_frames=0, resolution=(1280, 720),
           engine="BLENDER_EEVEE", samples=32, hdri=None, view_transform="Standard", focal_mm=50.0,
           ground=True, sheet=True, transparent=False, fit=1.15):
    objs = _targets(objects, collection)
    if not objs:
        return {"error": "no mesh objects to render"}
    os.makedirs(out_dir, exist_ok=True)
    bpy.context.view_layer.update()
    src_scene = bpy.context.scene

    # Temporary scene that links the originals (no copies) plus the review rig.
    scene = bpy.data.scenes.new("REVIEW_TMP")
    if bpy.context.window:
        bpy.context.window.scene = scene
    for o in objs:
        scene.collection.objects.link(o)
    lo, hi, center, radius = _bounds(objs)
    radius = max(radius, 0.05)
    cam_data = bpy.data.cameras.new("REVIEW_Cam")
    cam = bpy.data.objects.new("REVIEW_Cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    lights = _studio_lights(scene, center, radius)
    _world(scene, hdri=hdri)
    scene.render.resolution_x, scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA" if transparent else "RGB"
    scene.render.film_transparent = transparent
    try:
        scene.view_settings.view_transform = view_transform
    except TypeError:
        pass
    scene.view_settings.look = "None"

    extra = []
    if ground:
        extra.append(_ground(scene, center, lo, radius))

    outputs = {}

    aspect = resolution[0] / float(resolution[1])

    def _render(mode, view_name, direction, ortho, path):
        _place_camera(cam, center, radius, direction, ortho, focal_mm=focal_mm, fit=fit, aspect=aspect)
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True, scene=scene.name)
        outputs.setdefault(mode, []).append(path)

    def _set_mode(mode):
        for o in objs:
            o.hide_render = mode != "beauty"
        for c in clay:
            c.hide_render = mode == "beauty" or (mode == "clay" and c.name.startswith("REVIEW_WIRE_"))
        if mode == "beauty":
            scene.render.engine = engine
            if engine == "CYCLES":
                scene.cycles.samples = samples
                scene.cycles.use_denoising = True
                scene.cycles.device = "CPU"
            else:
                scene.eevee.taa_render_samples = samples
        else:
            scene.render.engine = "BLENDER_WORKBENCH"
            sh = scene.display.shading
            sh.light = "STUDIO"
            sh.color_type = "MATERIAL"
            sh.show_cavity = True
            sh.cavity_type = "BOTH"
            sh.cavity_ridge_factor = 1.0
            sh.cavity_valley_factor = 1.0
            sh.show_shadows = True
            sh.show_specular_highlight = True
            scene.display.render_aa = "8"

    clay = []
    sheet_path = None
    try:
        clay = _clay_copies(scene, objs, wire="wireframe" in modes) if ({"clay", "wireframe"} & set(modes)) else []
        for mode in modes:
            _set_mode(mode)
            for v in views:
                direction, ortho = VIEWS[v]
                _render(mode, v, direction, ortho, os.path.join(out_dir, f"{mode}_{v}.png"))
            if mode == "beauty" and turntable_frames:
                for i in range(turntable_frames):
                    ang = 2 * math.pi * i / turntable_frames
                    d = Vector((math.sin(ang), -math.cos(ang), 0.55)).normalized()
                    _render("turntable", f"{i:02d}", d, False, os.path.join(out_dir, f"turntable_{i:02d}.png"))
        if sheet:
            ordered = [p for m in ("beauty", "clay", "wireframe") for p in outputs.get(m, [])]
            if ordered:
                sheet_path = contact_sheet(ordered, os.path.join(out_dir, "contact_sheet.png"), cols=len(views))
            if outputs.get("turntable"):
                contact_sheet(outputs["turntable"], os.path.join(out_dir, "turntable_sheet.png"), cols=4)
    finally:
        # Cleanup even when a render fails: unlink originals, delete rig and temp scene, restore the user's scene.
        for o in objs:
            o.hide_render = False
        for o in clay + extra + lights + [cam]:
            data = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            if data and data.users == 0:
                if isinstance(data, bpy.types.Mesh):
                    bpy.data.meshes.remove(data)
                elif isinstance(data, bpy.types.Light):
                    bpy.data.lights.remove(data)
                elif isinstance(data, bpy.types.Camera):
                    bpy.data.cameras.remove(data)
        world = scene.world
        if bpy.context.window:
            bpy.context.window.scene = src_scene
        bpy.data.scenes.remove(scene)
        if world and world.users == 0:
            bpy.data.worlds.remove(world)
        for m in list(bpy.data.materials):
            if m.name.startswith("REVIEW_") and m.users == 0:
                bpy.data.materials.remove(m)

    return dict(
        blender=bpy.app.version_string,
        objects=[o.name for o in objs],
        bounds=dict(min=[round(c, 4) for c in lo], max=[round(c, 4) for c in hi], radius=round(radius, 4)),
        renders=outputs,
        contact_sheet=sheet_path,
        turntable_sheet=os.path.join(out_dir, "turntable_sheet.png") if outputs.get("turntable") else None,
        engine=engine,
        resolution=list(resolution),
    )


def _cli():
    import argparse
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(prog="render_review")
    p.add_argument("--objects")
    p.add_argument("--collection")
    p.add_argument("--out", required=True)
    p.add_argument("--modes", default="beauty,clay,wireframe")
    p.add_argument("--views", default="three_quarter,front,right,top")
    p.add_argument("--turntable", type=int, default=0)
    p.add_argument("--res", default="1280x720")
    p.add_argument("--engine", default="BLENDER_EEVEE")
    p.add_argument("--samples", type=int, default=32)
    p.add_argument("--hdri")
    p.add_argument("--view-transform", default="Standard")
    p.add_argument("--no-ground", action="store_true")
    p.add_argument("--transparent", action="store_true")
    p.add_argument("--fit", type=float, default=1.15, help="margin factor around the asset's bounding sphere (1.0 = touching)")
    a = p.parse_args(argv)
    w, h = (int(x) for x in a.res.lower().split("x"))
    rep = review(objects=a.objects.split(",") if a.objects else None, collection=a.collection, out_dir=a.out,
                 modes=tuple(a.modes.split(",")), views=tuple(a.views.split(",")), turntable_frames=a.turntable,
                 resolution=(w, h), engine=a.engine, samples=a.samples, hdri=a.hdri, view_transform=a.view_transform,
                 ground=not a.no_ground, transparent=a.transparent, fit=a.fit)
    print(json.dumps(rep, indent=2))
    print("REVIEW_JSON=" + json.dumps(rep))


if __name__ == "__main__":
    _cli()
