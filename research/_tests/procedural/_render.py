"""Workbench contact-sheet render of named objects from a saved .blend (run: Blender -b file.blend --python _render.py -- out.png NAME1 NAME2 ...)"""
import bpy, sys, math
from mathutils import Vector
argv = sys.argv[sys.argv.index("--") + 1:]
out, names = argv[0], [n for n in argv[1:] if n != "KEEP"]; keep = "KEEP" in argv
sc = bpy.context.scene
objs = [o for o in sc.objects if o.type == 'MESH' and (o.name in names if names else o.name.startswith("SM_"))]
for o in sc.objects:
    o.hide_render = o not in objs
# lay out side by side on X with gaps
x = 0.0
for o in (sorted(objs, key=lambda o: o.name) if not keep else []):
    bpy.context.view_layer.update()
    w = o.dimensions.x if o.dimensions.x > 0 else 0.5
    o.location.x += x - (o.matrix_world.translation.x - o.location.x) ; x += w * 1.3
bpy.context.view_layer.update()
pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))); mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
c = (mn + mx) / 2; size = max((mx - mn).x, (mx - mn).z, (mx - mn).y)
cam = bpy.data.cameras.new("Cam"); cam_ob = bpy.data.objects.new("Cam", cam); sc.collection.objects.link(cam_ob); sc.camera = cam_ob
ext = mx - mn; aspect = 1400 / 600
cam.type = 'ORTHO'; cam.ortho_scale = max(ext.x + ext.y * 0.6, (ext.z + ext.y * 0.5) * aspect) * 1.15
d = Vector((-1, -1.6, 1.0)).normalized()
cam_ob.location = c + d * (size * 4); cam_ob.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
sc.render.engine = 'BLENDER_WORKBENCH'; sh = sc.display.shading
sh.light = 'STUDIO'; sh.color_type = 'SINGLE'; sh.single_color = (0.75, 0.75, 0.78); sh.show_cavity = True; sh.cavity_type = 'BOTH'
sh.show_object_outline = True; sh.show_shadows = True
sc.render.resolution_x = 1400; sc.render.resolution_y = 600; sc.render.film_transparent = False
sc.render.filepath = out; bpy.ops.render.render(write_still=True)
print("RENDERED", out, [o.name for o in objs])
