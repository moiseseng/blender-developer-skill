import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _check import *
import bpy, bmesh, math
from mathutils import Vector, Matrix, noise
reset_scene()

# ---- faceted low-poly rock: noisy icosphere -> Decimate COLLAPSE -> shade_flat
bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=3, radius=0.5); bm.normal_update()
for v in bm.verts: v.co += v.normal * 0.15 * noise.noise(v.co * 2.0)
rock = obj_from_bmesh(bm, "SM_Rock_LP"); report(rock, "stylized_0_rock_hi")
d = rock.modifiers.new("Decimate", 'DECIMATE'); d.decimate_type = 'COLLAPSE'; d.ratio = 0.12; d.use_collapse_triangulate = True
apply_stack(rock); rock.data.shade_flat(); report(rock, "stylized_1_rock_decimate_0.12_flat")
print("all faces flat:", not any(p.use_smooth for p in rock.data.polygons))

# ---- chunky bevels (toy look): chamfer vs rounded, width = 15% of the block
for seg in (1, 4):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=0.5)
    bmesh.ops.bevel(bm, geom=bm.edges[:], offset=0.075, segments=seg, profile=0.5, affect='EDGES', clamp_overlap=True)
    ob = obj_from_bmesh(bm, f"SM_Toy_{seg}"); 
    if seg > 1: ob.data.shade_smooth()
    report(ob, f"stylized_2_chunky_bevel_seg{seg}")

# ---- exaggerated proportions: scale a vertex group about a pivot (head 1.6x on a blockout)
bm = bmesh.new()
bmesh.ops.create_cone(bm, segments=12, radius1=0.25, radius2=0.18, depth=0.9, cap_ends=True, matrix=Matrix.Translation((0, 0, 0.45)))   # body
bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=0.22, matrix=Matrix.Translation((0, 0, 1.1)))                         # head
report(snapshot(bm, "fig0"), "stylized_3_figure_blockout")
head = [v for v in bm.verts if v.co.z > 0.88]; pivot = Vector((0, 0, 1.0))      # pivot = neck
# bmesh.ops.scale 'space' convention: single vert at z=2, pivot z=1, scale 2 -> 3.0 if scaled about pivot
for sign, lab in ((-1, 'Translation(-pivot)'), (1, 'Translation(+pivot)')):
    t = bmesh.new(); tv = t.verts.new((0, 0, 2.0))
    bmesh.ops.scale(t, vec=(2, 2, 2), space=Matrix.Translation(Vector((0, 0, 1.0)) * sign), verts=[tv])
    print(f'bmesh.ops.scale space={lab}: vert z 2.0 -> {tv.co.z:.3f}  (3.0 = about pivot, 4.0 = about origin)'); t.free()
# (old confounded test kept for the log)
bm_a = bm.copy(); bmesh.ops.scale(bm_a, vec=(1.6, 1.6, 1.6), space=Matrix.Translation(-pivot), verts=[v for v in bm_a.verts if v.co.z > 0.88])
print("space=Translation(-pivot): head zmin after:", round(min(v.co.z for v in bm_a.verts if v.co.z > 0.88), 3), "(pivot 1.0 fixed -> ~0.81 expected if scaling about pivot)")
bm_b = bm.copy(); bmesh.ops.scale(bm_b, vec=(1.6, 1.6, 1.6), space=Matrix.Translation(pivot), verts=[v for v in bm_b.verts if v.co.z > 0.88])
print("space=Translation(+pivot): head zmin after:", round(min(v.co.z for v in bm_b.verts if v.co.z > 0.88), 3))
for v in head: v.co = pivot + (v.co - pivot) * 1.6              # explicit, convention-free
fig = obj_from_bmesh(bm, "SM_Figure"); report(fig, "stylized_4_figure_head_x1.6_manual")
bm_a.free(); bm_b.free()

# ---- stylized shortcut: shade flat + limited dissolve keeps faceting cheap
bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=0.4)
ob = obj_from_bmesh(bm, "SM_Gem"); ob.data.shade_flat(); report(ob, "stylized_5_lowpoly_gem_10x6")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_out"); os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "t09.blend"))
print("DONE t09")
