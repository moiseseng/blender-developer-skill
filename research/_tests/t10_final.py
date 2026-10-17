import bpy, os, struct, math
import numpy as np
OUT = "/Users/Game/blender-3d-team/research/_tests/_out"; os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene; vl = bpy.context.view_layer
def raw(p):  # reload as Non-Color so pixels are the stored codes
    i = bpy.data.images.load(p); i.colorspace_settings.name = 'Non-Color'; return round(float(i.pixels[0]), 3)
def fill(img, v):
    px = np.full(img.size[0]*img.size[1]*4, v, dtype=np.float32); px[3::4] = 1.0; img.pixels.foreach_set(px)
print("=== pixel encoding by buffer type (srgb(0.2) ~= 0.484)")
b = bpy.data.images.new("byte_srgb", 8, 8, float_buffer=False); fill(b, 0.2)
b.filepath_raw = os.path.join(OUT, "byte_srgb.png"); b.file_format = 'PNG'; b.save()
print("byte sRGB image: wrote 0.2 -> stored code", raw(b.filepath_raw), "(0.2 => pixels are sRGB codes; 0.484 => linear)")
f = bpy.data.images.new("float_srgb", 8, 8, float_buffer=True); fill(f, 0.2)
f.filepath_raw = os.path.join(OUT, "float_srgb.png"); f.file_format = 'PNG'; f.save()
print("float sRGB image: wrote 0.2 -> stored code", raw(f.filepath_raw), "| png bits", struct.unpack(">B", open(f.filepath_raw,"rb").read()[24:25])[0])
d = bpy.data.images.new("byte_data", 8, 8, float_buffer=False, is_data=True); fill(d, 0.2)
d.filepath_raw = os.path.join(OUT, "byte_data.png"); d.file_format = 'PNG'; d.save()
print("byte Non-Color image: wrote 0.2 -> stored code", raw(d.filepath_raw))
# 8-bit encoded colour from float buffer via save_render
sc.render.image_settings.file_format='PNG'; sc.render.image_settings.color_depth='8'; sc.render.image_settings.color_mode='RGBA'
p8 = os.path.join(OUT, "float_srgb_8bit.png"); f.save_render(p8, scene=sc)
print("float sRGB via save_render 8-bit: code", raw(p8), "| bits", struct.unpack(">B", open(p8,"rb").read()[24:25])[0])
print("=== save(filepath=) honours file_format?")
f.file_format = 'PNG'; p = os.path.join(OUT, "x_save_filepath.png"); f.save(filepath=p)
head = open(p, "rb").read(25); print("magic PNG?", head[:8] == b"\x89PNG\r\n\x1a\n", "| bit depth", head[24])
f.file_format = 'OPEN_EXR'; p2 = os.path.join(OUT, "x_exr_named_png.png"); f.save(filepath=p2)
h2 = open(p2, "rb").read(8); print("file_format=OPEN_EXR, filepath .png -> PNG magic?", h2 == b"\x89PNG\r\n\x1a\n", "| EXR magic?", h2[:4] == b"\x76\x2f\x31\x01")
print("=== ops run bare (no temp_override)")
cube = bpy.data.objects["Cube"]
for ob in bpy.data.objects: ob.select_set(False)
cube.select_set(True); vl.objects.active = cube
cube.location = (1, 0, 0); cube.scale = (2, 2, 2)
print("origin_set", bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS'))
print("transform_apply", bpy.ops.object.transform_apply(location=True, rotation=True, scale=True), "scale now", tuple(cube.scale))
print("camera_to_view_selected", bpy.ops.view3d.camera_to_view_selected())
print("primitive_cube_add", bpy.ops.mesh.primitive_cube_add(size=1.0, location=(5, 0, 0)), [o.name for o in bpy.data.objects])
