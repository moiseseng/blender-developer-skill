import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _check import *
import bpy, bmesh, math
from mathutils import Vector, Matrix
reset_scene()

def block(name="SM_Block"):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0); return obj_from_bmesh(bm, name)
def cutter(name="Cutter", caps=True, r=0.2):
    bm = bmesh.new(); bmesh.ops.create_cone(bm, segments=32, radius1=r, radius2=r, depth=2.0, cap_ends=caps)
    return obj_from_bmesh(bm, name)
def bool_mod(base, cut, solver, op='DIFFERENCE', **kw):
    m = base.modifiers.new("Bool", 'BOOLEAN'); m.operation = op; m.solver = solver; m.object = cut
    for k, v in kw.items(): setattr(m, k, v)
    return m

for solver in ('FLOAT', 'EXACT', 'MANIFOLD'):
    b = block(f"blk_{solver}"); c = cutter(f"cut_{solver}")
    bool_mod(b, c, solver)
    report(b, f"boolean_DIFFERENCE_{solver}_closed_cutter", evaluated=True)
# open (non-manifold) cutter: who copes?
for solver in ('FLOAT', 'EXACT', 'MANIFOLD'):
    b = block(f"blk_open_{solver}"); c = cutter(f"cut_open_{solver}", caps=False)
    bool_mod(b, c, solver)
    report(b, f"boolean_DIFFERENCE_{solver}_OPEN_cutter", evaluated=True)
# self-intersecting cutter (two overlapping cylinders in one mesh): EXACT use_self
bm = bmesh.new()
bmesh.ops.create_cone(bm, segments=24, radius1=0.2, radius2=0.2, depth=2.0, cap_ends=True, matrix=Matrix.Translation((0.1, 0, 0)))
bmesh.ops.create_cone(bm, segments=24, radius1=0.2, radius2=0.2, depth=2.0, cap_ends=True, matrix=Matrix.Translation((-0.1, 0, 0)))
selfcut = obj_from_bmesh(bm, "cut_self")
for use_self in (False, True):
    b = block(f"blk_self_{use_self}"); bool_mod(b, selfcut, 'EXACT', use_self=use_self)
    report(b, f"boolean_EXACT_selfintersecting_cutter_use_self={use_self}", evaluated=True)
b = block("blk_hole"); bool_mod(b, selfcut, 'EXACT', use_self=True, use_hole_tolerant=True)
report(b, "boolean_EXACT_use_self+use_hole_tolerant", evaluated=True)

# cutter visibility: which hiding method keeps the boolean working in -b?
b = block("blk_hv"); c = cutter("cut_hv"); bool_mod(b, c, 'EXACT'); c.hide_viewport = True
report(b, "cutter_hide_viewport=True (monitor icon)", evaluated=True)
b = block("blk_hs"); c = cutter("cut_hs"); bool_mod(b, c, 'EXACT'); c.hide_set(True); c.hide_render = True; c.display_type = 'WIRE'
report(b, "cutter_hide_set(True)+hide_render+WIRE (eye icon)", evaluated=True)
b = block("blk_unlinked"); c = cutter("cut_unlinked"); bool_mod(b, c, 'EXACT')
bpy.context.scene.collection.objects.unlink(c)
report(b, "cutter_unlinked_from_scene", evaluated=True)
# collection operand
cutcol = ensure_collection("Cutters")
c1 = cutter("c1", r=0.15); c2 = cutter("c2", r=0.15); c2.location = (0.25, 0, 0)
for c in (c1, c2):
    bpy.context.scene.collection.objects.unlink(c); cutcol.objects.link(c)
b = block("blk_col"); m = b.modifiers.new("Bool", 'BOOLEAN'); m.operand_type = 'COLLECTION'; m.collection = cutcol; m.solver = 'EXACT'
report(b, "boolean_collection_operand_2_cutters", evaluated=True)

# cleanup pipeline on an EXACT result
b = block("SM_Block_Cut"); c = cutter("cut_final"); bool_mod(b, c, 'EXACT')
apply_stack(b); report(b, "cleanup_0_applied_EXACT")
bm = bmesh.new(); bm.from_mesh(b.data)
bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-4)
bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.0), verts=bm.verts[:], edges=bm.edges[:])
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
bm.to_mesh(b.data); bm.free(); report(b, "cleanup_1_remove_doubles+dissolve_limit+recalc")
bm = bmesh.new(); bm.from_mesh(b.data)
bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4], quad_method='BEAUTY', ngon_method='BEAUTY')
bm.to_mesh(b.data); bm.free(); report(b, "cleanup_2_triangulate_ngons_only")

# operator route in -b: modifier_apply needs a context override
b = block("blk_opapply"); c = cutter("cut_opapply"); m = bool_mod(b, c, 'EXACT')
with bpy.context.temp_override(object=b, active_object=b, selected_objects=[b], selected_editable_objects=[b]):
    res = bpy.ops.object.modifier_apply(modifier=m.name)
print("modifier_apply via temp_override:", res, "modifiers left:", len(b.modifiers))
report(b, "modifier_apply_operator_result")
print("DONE t03")
