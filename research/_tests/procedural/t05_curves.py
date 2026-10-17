import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _check import *
import bpy, bmesh, math
from mathutils import Vector, Matrix
reset_scene()

def bezier_pipe(name, points, radius, bevel_res=4, res_u=12, caps=True):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(points) - 1)
    for p, co in zip(sp.bezier_points, points):
        p.co = co; p.handle_left_type = p.handle_right_type = 'AUTO'
    cu.bevel_mode = 'ROUND'; cu.bevel_depth = radius; cu.bevel_resolution = bevel_res
    cu.resolution_u = res_u; cu.fill_mode = 'FULL'; cu.use_fill_caps = caps
    ob = bpy.data.objects.new(name, cu); bpy.context.scene.collection.objects.link(ob); return ob

cable = bezier_pipe("CU_Cable", [(0, 0, 1.0), (0.4, 0.1, 0.6), (0.8, -0.1, 0.55), (1.2, 0, 1.0)], radius=0.01)
bpy.context.view_layer.update(); print("curve object dims:", tuple(round(d, 3) for d in cable.dimensions))
me = evaluated_mesh(cable, "SM_Cable"); m_ob = bpy.data.objects.new("SM_Cable", me); bpy.context.scene.collection.objects.link(m_ob)
report(m_ob, "bezier_cable_r0.01_bevres4_resu12_caps_RAW")
bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5); bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:]); bm.to_mesh(me); bm.free()
report(m_ob, "bezier_cable_caps_after_remove_doubles (caps come in as disconnected fans)")
cu = cable.data; print('cable use_fill_caps:', cu.use_fill_caps, 'fill_mode:', cu.fill_mode, 'bevel_mode:', cu.bevel_mode)
dg = bpy.context.evaluated_depsgraph_get(); evc = cable.evaluated_get(dg)
print('evaluated cable type:', evc.type, 'data type:', type(evc.data).__name__)
try:
    tm = evc.to_mesh(); print('to_mesh ngons (caps?):', sum(1 for p in tm.polygons if len(p.vertices) > 4), 'faces', len(tm.polygons)); evc.to_mesh_clear()
except Exception as e: print('to_mesh err', e)
cu.use_fill_caps = False
me2 = evaluated_mesh(cable, 'SM_Cable_nocaps'); o2 = bpy.data.objects.new('SM_Cable_nocaps', me2); bpy.context.scene.collection.objects.link(o2)
report(o2, 'bezier_cable_use_fill_caps_False'); cu.use_fill_caps = True
pipe = bezier_pipe("CU_Pipe", [(0, 0, 0), (0, 0, 0.5), (0.5, 0, 0.5)], radius=0.04, bevel_res=8, res_u=16)
me = evaluated_mesh(pipe, "SM_Pipe"); m_ob = bpy.data.objects.new("SM_Pipe", me); bpy.context.scene.collection.objects.link(m_ob)
report(m_ob, "bezier_pipe_r0.04_bevres8")
# manual handles for a sharp-ish bend
cu = pipe.data; bp = cu.splines[0].bezier_points[1]; bp.handle_left_type = bp.handle_right_type = 'FREE'
bp.handle_left = (0, 0, 0.3); bp.handle_right = (0.2, 0, 0.5)
me = evaluated_mesh(pipe, "SM_Pipe_manual"); m_ob = bpy.data.objects.new("SM_Pipe_manual", me); bpy.context.scene.collection.objects.link(m_ob)
report(m_ob, "bezier_pipe_FREE_handles")
# POLY spline rope with sag, bevel_depth, no caps; plus taper object
cu = bpy.data.curves.new("CU_Rope", 'CURVE'); cu.dimensions = '3D'
sp = cu.splines.new('POLY'); n = 12; sp.points.add(n - 1)
for i, p in enumerate(sp.points):
    t = i / (n - 1); p.co = (t * 2.0, 0, 1.0 - 0.3 * math.sin(math.pi * t), 1.0)      # (x,y,z,w)
cu.bevel_depth = 0.015; cu.bevel_resolution = 3; cu.use_fill_caps = False; sp.use_smooth = True
rope = bpy.data.objects.new("CU_Rope", cu); bpy.context.scene.collection.objects.link(rope)
me = evaluated_mesh(rope, "SM_Rope"); m_ob = bpy.data.objects.new("SM_Rope", me); bpy.context.scene.collection.objects.link(m_ob)
report(m_ob, "poly_rope_12pts_bevel0.015_open")
# custom profile via bevel_object (a square profile curve) -> square duct
prof = bpy.data.curves.new("CU_Prof", 'CURVE'); prof.dimensions = '2D'
ps = prof.splines.new('POLY'); ps.points.add(3); ps.use_cyclic_u = True
for p, (x, y) in zip(ps.points, [(-0.05, -0.05), (0.05, -0.05), (0.05, 0.05), (-0.05, 0.05)]): p.co = (x, y, 0, 1)
prof_ob = bpy.data.objects.new("CU_Prof", prof); bpy.context.scene.collection.objects.link(prof_ob)
duct = bezier_pipe("CU_Duct", [(0, 0, 0), (0.5, 0, 0), (1.0, 0.3, 0)], radius=0.0)
duct.data.bevel_mode = 'OBJECT'; duct.data.bevel_object = prof_ob; duct.data.use_fill_caps = True
me = evaluated_mesh(duct, "SM_Duct"); m_ob = bpy.data.objects.new("SM_Duct", me); bpy.context.scene.collection.objects.link(m_ob)
report(m_ob, "bezier_bevel_object_square_duct_RAW")
bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5); bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:]); bm.to_mesh(me); bm.free()
report(m_ob, "bezier_bevel_object_duct_after_remove_doubles+recalc")
# operator conversion route in -b
with bpy.context.temp_override(object=cable, active_object=cable, selected_objects=[cable], selected_editable_objects=[cable]):
    res = bpy.ops.object.convert(target='MESH', keep_original=False)
print("convert op:", res, "type now:", cable.type); report(cable, "convert_operator_result")
print("DONE t05")
