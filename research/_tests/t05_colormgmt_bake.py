import bpy, os, math, struct, warnings
import numpy as np
warnings.simplefilter("ignore")
OUT = "/Users/Game/blender-3d-team/research/_tests/_out"; os.makedirs(OUT, exist_ok=True)
def tryp(label, fn):
    try: r = fn(); print("OK  ", label, "->", r); return r
    except Exception as ex: print("FAIL", label, "->", type(ex).__name__, str(ex)[:220]); return None
sc = bpy.context.scene; vl = bpy.context.view_layer
cube = bpy.data.objects["Cube"]
def png_depth(p): return struct.unpack(">B", open(p,"rb").read()[24:25])[0]
def rp(p):
    i = bpy.data.images.load(p); px = np.empty(len(i.pixels), dtype=np.float32); i.pixels.foreach_get(px); return (round(float(px[0]),3), i.colorspace_settings.name, i.depth)
print("=== 8-bit data map: Image.save vs save_render (AgX)")
rough = bpy.data.images.new("rough", 8, 8, float_buffer=False, is_data=True)
px = np.full(8*8*4, 0.5, dtype=np.float32); px[3::4]=1.0; rough.pixels.foreach_set(px)
rough.filepath_raw = os.path.join(OUT,"rough_save.png"); rough.file_format='PNG'; rough.save()
sc.view_settings.view_transform='AgX'; sc.render.image_settings.file_format='PNG'; sc.render.image_settings.color_depth='8'; sc.render.image_settings.color_management='FOLLOW_SCENE'
rough.save_render(os.path.join(OUT,"rough_render_agx.png"), scene=sc)
sc.render.image_settings.color_management='OVERRIDE'; sc.render.image_settings.view_settings.view_transform='Standard'
rough.save_render(os.path.join(OUT,"rough_render_std.png"), scene=sc)
sc.render.image_settings.color_management='FOLLOW_SCENE'
for n in ("rough_save.png","rough_render_agx.png","rough_render_std.png"):
    tryp(n, lambda n=n: (rp(os.path.join(OUT,n)), "png bits", png_depth(os.path.join(OUT,n))))
# re-load with Non-Color and read raw
i = bpy.data.images.load(os.path.join(OUT,"rough_save.png")); i.colorspace_settings.name='Non-Color'
tryp("rough_save reloaded as Non-Color pixel", lambda: round(i.pixels[0],3))
i2 = bpy.data.images.load(os.path.join(OUT,"rough_render_agx.png")); i2.colorspace_settings.name='Non-Color'
tryp("rough_render_agx reloaded as Non-Color pixel", lambda: round(i2.pixels[0],3))
print("=== sRGB color map: Image.save roundtrip")
alb = bpy.data.images.new("alb", 8, 8, float_buffer=False)  # sRGB
px = np.full(8*8*4, 0.5, dtype=np.float32); px[3::4]=1.0; alb.pixels.foreach_set(px)
alb.filepath_raw = os.path.join(OUT,"alb_save.png"); alb.file_format='PNG'; alb.save()
tryp("alb pixel after save (in-memory)", lambda: round(alb.pixels[0],3))
tryp("alb reload", lambda: rp(os.path.join(OUT,"alb_save.png")))
print("=== float image -> Image.save PNG bit depth")
f = bpy.data.images.new("f", 8, 8, float_buffer=True, is_data=True)
f.filepath_raw = os.path.join(OUT,"float_save.png"); f.file_format='PNG'; f.save()
tryp("float->PNG via Image.save bits", lambda: png_depth(os.path.join(OUT,"float_save.png")))
print("=== bake verification")
def bake():
    sc.render.engine='CYCLES'; sc.cycles.samples=1; sc.cycles.device='CPU'
    me = cube.data
    mat = bpy.data.materials.new("BakeMat"); nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]; bsdf.inputs["Base Color"].default_value=(0.2,0.6,0.1,1)
    img = bpy.data.images.new("bake_tex", 32, 32)
    tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img; nt.nodes.active = tex
    me.materials.clear(); me.materials.append(mat)
    for ob in bpy.data.objects: ob.select_set(False)
    cube.select_set(True); vl.objects.active = cube
    sc.render.bake.use_pass_direct=False; sc.render.bake.use_pass_indirect=False; sc.render.bake.use_pass_color=True
    r = bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'}, margin=4, use_clear=True, target='IMAGE_TEXTURES', save_mode='INTERNAL')
    px = np.empty(len(img.pixels), dtype=np.float32); img.pixels.foreach_get(px)
    rgb = px.reshape(-1,4)[:, :3]; covered = rgb[(rgb.sum(axis=1) > 0)]
    img.filepath_raw=os.path.join(OUT,"bake_diffuse.png"); img.file_format='PNG'; img.save()
    return (r, "covered px", len(covered), "mean rgb", covered.mean(axis=0).round(3).tolist() if len(covered) else None, "colorspace", img.colorspace_settings.name)
tryp("bake diffuse color", bake)
print("=== shade_auto_smooth idempotency")
cube.modifiers.clear()
bpy.ops.object.shade_auto_smooth(angle=0.5); bpy.ops.object.shade_auto_smooth(angle=0.7)
tryp("modifiers after 2 calls", lambda: [(m.name, round(m.properties.inputs.Input_1.value,2)) for m in cube.modifiers])
print("=== keyframe pref interpolation")
bpy.context.preferences.edit.keyframe_new_interpolation_type='LINEAR'
cube.animation_data_clear(); cube.keyframe_insert("location", frame=1); cube.location.x=1; cube.keyframe_insert("location", frame=10)
from bpy_extras import anim_utils
ad = cube.animation_data; cb = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)
tryp("interp with pref LINEAR", lambda: [kp.interpolation for kp in cb.fcurves[0].keyframe_points])
print("=== gltf export_apply with Smooth by Angle + normals check")
cube.animation_data_clear()
p = os.path.join(OUT,"cube_smooth.glb")
tryp("gltf", lambda: (bpy.ops.export_scene.gltf(filepath=p, export_format='GLB', use_selection=True, export_apply=True), os.path.getsize(p)))
print("=== gpu.init in background")
import gpu
tryp("gpu.init()", lambda: gpu.init())
tryp("backend after init", lambda: gpu.platform.backend_type_get())
