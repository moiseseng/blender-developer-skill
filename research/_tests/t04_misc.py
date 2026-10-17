import bpy, bmesh, math, os, warnings, struct
from mathutils import Vector, Matrix
import numpy as np
warnings.simplefilter("ignore")
OUT = "/Users/Game/blender-3d-team/research/_tests/_out"; os.makedirs(OUT, exist_ok=True)
def sec(t): print("\n=== " + t)
def tryp(label, fn):
    try: r = fn(); print("OK  ", label, "->", r); return r
    except Exception as ex: print("FAIL", label, "->", type(ex).__name__, str(ex)[:220]); return None
sc = bpy.context.scene; vl = bpy.context.view_layer
cube = bpy.data.objects["Cube"]
def select_only(o):
    for ob in bpy.data.objects: ob.select_set(False)
    o.select_set(True); vl.objects.active = o
select_only(cube)
sec("GN modifier attribute-style access (5.2)")
bpy.ops.object.shade_auto_smooth(angle=math.radians(30))
gm = cube.modifiers["Smooth by Angle"]
tryp("inputs.Input_1 type", lambda: type(gm.properties.inputs.Input_1).__name__)
tryp("inputs.Input_1 rna props", lambda: [p.identifier for p in gm.properties.inputs.Input_1.bl_rna.properties])
tryp("inputs.Input_1.value", lambda: gm.properties.inputs.Input_1.value)
tryp("set inputs.Input_1.value", lambda: (setattr(gm.properties.inputs.Input_1, 'value', math.radians(60)), gm.properties.inputs.Input_1.value))
tryp("inputs.Socket_1.value", lambda: gm.properties.inputs.Socket_1.value)
tryp("inputs.Input_1.type", lambda: gm.properties.inputs.Input_1.type)
tryp("inputs.Input_1.attribute_name", lambda: gm.properties.inputs.Input_1.attribute_name)
tryp("outputs rna props", lambda: [p.identifier for p in gm.properties.outputs.bl_rna.properties])
tryp("outputs.Output_2 props", lambda: [p.identifier for p in getattr(gm.properties.outputs,'Output_2').bl_rna.properties])
tryp("inputs['Input_1'] via getattr(obj, id)", lambda: getattr(gm.properties.inputs, 'Input_1').value)
tryp("old gm['Input_1']", lambda: gm["Input_1"])
tryp("modifier_apply(Smooth by Angle)", lambda: (bpy.ops.object.modifier_apply(modifier="Smooth by Angle"), [(a.name) for a in cube.data.attributes if 'sharp' in a.name]))
sec("Action slots / keyframes (5.0 removed action.fcurves)")
cube.animation_data_clear()
tryp("pref keyframe_new_interpolation_type", lambda: bpy.context.preferences.edit.keyframe_new_interpolation_type)
bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
cube.rotation_euler=(0,0,0); cube.keyframe_insert("rotation_euler", index=2, frame=1)
cube.rotation_euler=(0,0,math.tau); cube.keyframe_insert("rotation_euler", index=2, frame=97)
ad = cube.animation_data
tryp("slot attrs", lambda: [p.identifier for p in ad.action_slot.bl_rna.properties])
tryp("slot identifier/name_display", lambda: (ad.action_slot.identifier, ad.action_slot.name_display, ad.action_slot.target_id_type))
tryp("action attrs", lambda: [p.identifier for p in ad.action.bl_rna.properties])
def cb():
    act = ad.action
    cb = act.layers[0].strips[0].channelbag(ad.action_slot)
    return [(fc.data_path, fc.array_index, [kp.interpolation for kp in fc.keyframe_points]) for fc in cb.fcurves]
tryp("channelbag via layers/strips", cb)
from bpy_extras import anim_utils
tryp("anim_utils funcs", lambda: [n for n in dir(anim_utils) if 'channelbag' in n or 'slot' in n])
def cb2():
    c = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)
    for fc in c.fcurves:
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
    return [kp.interpolation for kp in c.fcurves[0].keyframe_points]
tryp("set interpolation via channelbag", cb2)
tryp("fcurve_ensure_for_datablock", lambda: ad.action.fcurve_ensure_for_datablock(cube, "location", index=0).data_path)
sc.frame_set(49); tryp("frame 49 rot z deg", lambda: round(math.degrees(cube.matrix_world.to_euler().z),1))
sc.frame_set(1)
sec("depsgraph staleness")
cube.animation_data_clear(); cube.rotation_euler=(0,0,0)
cube.location = (5,0,0)
tryp("matrix_world before update", lambda: tuple(round(x,2) for x in cube.matrix_world.translation))
vl.update()
tryp("matrix_world after view_layer.update()", lambda: tuple(round(x,2) for x in cube.matrix_world.translation))
cube.location = (0,0,0); vl.update()
sec("camera look-at")
cam = bpy.data.objects["Camera"]
def lookat():
    cam.location = (6,-6,4)
    d = Vector((0,0,0)) - cam.location
    cam.rotation_euler = d.to_track_quat('-Z','Y').to_euler()
    vl.update()
    return tuple(round(math.degrees(a),1) for a in cam.rotation_euler)
tryp("look-at", lookat)
def fit():
    dg = bpy.context.evaluated_depsgraph_get()
    pts = [c for v in (cube.matrix_world @ Vector(b) for b in cube.bound_box) for c in v]
    loc, scale = cam.camera_fit_coords(dg, pts)
    cam.location = loc; return (tuple(round(x,2) for x in loc), scale)
tryp("fit after look-at", fit)
sec("attributes foreach / use_smooth mapping")
me = cube.data
me.shade_flat()
tryp("sharp_face exists", lambda: 'sharp_face' in me.attributes)
me.polygons.foreach_set("use_smooth", [True]*len(me.polygons)); me.update()
tryp("after foreach use_smooth True -> sharp_face", lambda: ('sharp_face' in me.attributes, list(me.attributes['sharp_face'].data.foreach_get('value', [False]*len(me.polygons)) or [])[:0] or [a.value for a in me.attributes['sharp_face'].data][:3] if 'sharp_face' in me.attributes else 'attr removed'))
a = me.attributes.new("my_weight", 'FLOAT', 'POINT')
vals = np.linspace(0,1,len(me.vertices), dtype=np.float32)
a.data.foreach_set("value", vals)
back = np.empty(len(me.vertices), dtype=np.float32); me.attributes["my_weight"].data.foreach_get("value", back)
tryp("custom attr roundtrip", lambda: (back[:3].round(3).tolist(), me.attributes["my_weight"].domain))
pos = np.empty(len(me.vertices)*3, dtype=np.float32); me.attributes["position"].data.foreach_get("vector", pos)
tryp("position via attributes (float32)", lambda: pos[:3].tolist())
tryp("vertices.co foreach_get float64 ok?", lambda: (lambda arr: (me.vertices.foreach_get("co", arr), arr[:3].tolist()))(np.empty(len(me.vertices)*3, dtype=np.float64)))
sec("collections / naming")
col = bpy.data.collections.new("Assets"); sc.collection.children.link(col)
ob = bpy.data.objects.new("Thing", bpy.data.meshes.new("Thing"))
col.objects.link(ob)
tryp("ob users_collection", lambda: [c.name for c in ob.users_collection])
ob2 = bpy.data.objects.new("Thing", bpy.data.meshes.new("Thing"))
tryp("dup name", lambda: (ob2.name, ob2.data.name))
tryp("rename modes", lambda: [i.identifier for i in bpy.types.ID.bl_rna.functions['rename'].parameters['mode'].enum_items])
tryp("rename ALWAYS", lambda: (ob2.rename("Thing", mode='ALWAYS'), ob2.name, ob.name))
tryp("rename NEVER on clash", lambda: ob.rename("Thing", mode='NEVER'))
tryp("remove object", lambda: (bpy.data.objects.remove(ob2, do_unlink=True), len(bpy.data.objects)))
tryp("select_all poll", lambda: bpy.ops.object.select_all.poll())
tryp("object.delete poll", lambda: bpy.ops.object.delete.poll())
sec("color management pitfall on save_render")
im = bpy.data.images.new("gray", 8, 8, float_buffer=True, is_data=True)
px = np.full(8*8*4, 0.5, dtype=np.float32); px[3::4]=1.0; im.pixels.foreach_set(px)
im.filepath_raw = os.path.join(OUT,"gray_save.exr"); im.file_format='OPEN_EXR'; im.save()
sc.render.image_settings.file_format='OPEN_EXR'; sc.render.image_settings.color_depth='32'
sc.view_settings.view_transform='AgX'
im.save_render(os.path.join(OUT,"gray_render_agx.exr"), scene=sc)
sc.render.image_settings.color_management='OVERRIDE'; sc.render.image_settings.view_settings.view_transform='Standard'
im.save_render(os.path.join(OUT,"gray_render_override.exr"), scene=sc)
sc.render.image_settings.color_management='FOLLOW_SCENE'
def rp(p):
    i = bpy.data.images.load(p); v = i.pixels[0]; return round(v,3)
for n in ("gray_save.exr","gray_render_agx.exr","gray_render_override.exr"):
    tryp("pixel[0] of "+n, lambda n=n: rp(os.path.join(OUT,n)))
tryp("png bit depth of height16.png", lambda: struct.unpack(">B", open(os.path.join(OUT,"height16.png"),"rb").read()[24:25])[0])
sc.render.image_settings.file_format='PNG'; sc.render.image_settings.color_depth='8'
sec("bake (Cycles, background)")
def bake():
    sc.render.engine='CYCLES'; sc.cycles.samples=1; sc.cycles.device='CPU'
    mat = bpy.data.materials.new("BakeMat"); nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]; bsdf.inputs["Base Color"].default_value=(0.2,0.6,0.1,1)
    img = bpy.data.images.new("bake_tex", 32, 32)
    tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img; nt.nodes.active = tex
    me.materials.clear(); me.materials.append(mat)
    if not me.uv_layers: me.uv_layers.new(name="UVMap")
    select_only(cube)
    sc.render.bake.use_pass_direct=False; sc.render.bake.use_pass_indirect=False
    r = bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'}, margin=2, use_clear=True, target='IMAGE_TEXTURES', save_mode='INTERNAL')
    img.filepath_raw=os.path.join(OUT,"bake_diffuse.png"); img.file_format='PNG'; img.save()
    return (r, round(img.pixels[0],3), round(img.pixels[1],3), os.path.getsize(img.filepath_raw))
tryp("bake diffuse color", bake)
sec("misc 5.x")
tryp("scene.use_nodes", lambda: sc.use_nodes)
tryp("scene.compositing_node_group", lambda: sc.compositing_node_group)
tryp("has scene.node_tree", lambda: hasattr(sc, "node_tree"))
tryp("preferences.addon_enable exists", lambda: hasattr(bpy.ops.preferences, "addon_enable"))
tryp("extension ops", lambda: [o for o in dir(bpy.ops.extensions) if 'install' in o or 'enable' in o][:8])
import gpu
tryp("gpu.init exists", lambda: hasattr(gpu, "init"))
tryp("gpu.platform.backend_type_get before init", lambda: gpu.platform.backend_type_get())
tryp("Object.bound_box/dimensions", lambda: (len(cube.bound_box), tuple(round(d,2) for d in cube.dimensions)))
tryp("mesh.normals_domain", lambda: cube.data.normals_domain)
tryp("light types/props", lambda: (bpy.data.lights["Light"].type, bpy.data.lights["Light"].energy, hasattr(bpy.data.lights["Light"],'use_shadow')))
tryp("Image.save quality kw", lambda: [p.identifier for p in bpy.types.Image.bl_rna.functions['save'].parameters])
tryp("blend save", lambda: (bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,"test.blend"), compress=True), os.path.getsize(os.path.join(OUT,"test.blend"))))
