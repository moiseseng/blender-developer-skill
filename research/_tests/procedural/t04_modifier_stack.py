import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _check import *
import bpy, bmesh, math
from mathutils import Vector, Matrix
reset_scene()

# ---- L-bracket half (x in [0,0.2]) -> Mirror -> Array -> Bevel(harden) -> Weighted Normal
bm = bmesh.new()
L = [(0, 0), (0.2, 0), (0.2, 0.02), (0.02, 0.02), (0.02, 0.1), (0, 0.1)]      # (x, z) metres
f = bm.faces.new([bm.verts.new((x, 0, z)) for x, z in L])
r = bmesh.ops.extrude_face_region(bm, geom=[f])
bmesh.ops.translate(bm, verts=[g for g in r['geom'] if isinstance(g, bmesh.types.BMVert)], vec=(0, 0.1, 0))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
bmesh.ops.delete(bm, geom=[f for f in bm.faces if abs(f.calc_center_median().x) < 1e-6], context='FACES_ONLY')  # open seam at x=0
ob = obj_from_bmesh(bm, "SM_Bracket"); report(ob, "bracket_half_base_open_seam")
mir = ob.modifiers.new("Mirror", 'MIRROR'); mir.use_axis[0] = True; mir.use_clip = True; mir.use_mirror_merge = True; mir.merge_threshold = 1e-4
arr = ob.modifiers.new("Array", 'ARRAY'); arr.count = 3; arr.use_relative_offset = True; arr.relative_offset_displace = (0, 1.5, 0)
bev = ob.modifiers.new("Bevel", 'BEVEL'); bev.limit_method = 'ANGLE'; bev.angle_limit = math.radians(30)
bev.width = 0.003; bev.segments = 3; bev.profile = 0.5; bev.harden_normals = True; bev.use_clamp_overlap = True
wn = ob.modifiers.new("WeightedNormal", 'WEIGHTED_NORMAL'); wn.keep_sharp = True; wn.mode = 'FACE_AREA'
print("stack order:", [m.type for m in ob.modifiers])
report(ob, "bracket_Mirror>Array>Bevel>WeightedNormal_evaluated", evaluated=True)
ob.data.uv_layers.new(name='UVMap'); ob.data.attributes.new('panel_id', 'INT', 'FACE')
me_keep = evaluated_mesh(ob, "keep", preserve=True); me_drop = evaluated_mesh(ob, "drop", preserve=False)
for tag, m in (('preserve=True', me_keep), ('preserve=False', me_drop)):
    print(tag, 'has_custom_normals:', m.has_custom_normals, 'uv_layers:', len(m.uv_layers), 'attrs:', sorted(a.name for a in m.attributes if not a.name.startswith('.')))
bpy.data.meshes.remove(me_drop)
# Smooth by Angle (the 4.1+ replacement for Auto Smooth) via operator -> adds GN asset modifier
bpy.context.view_layer.objects.active = ob; ob.select_set(True)
bpy.ops.object.shade_auto_smooth(angle=math.radians(30))
sba = ob.modifiers[-1]; print("shade_auto_smooth added:", sba.name, sba.type, "linked lib:", bool(sba.node_group.library), "pinned last:", sba.use_pin_to_last)
report(ob, "bracket_+SmoothByAngle_modifier", evaluated=True)
applied = apply_stack(ob); report(applied, "bracket_apply_stack_in_place")
print("applied has_custom_normals:", applied.data.has_custom_normals, "sharp_edge attr:", 'sharp_edge' in applied.data.attributes)
# modifier-free variant: bake sharp edges by angle into the mesh
bpy.ops.object.shade_smooth_by_angle(angle=math.radians(30))
print("shade_smooth_by_angle -> sharp_edge count:", sum(1 for v in applied.data.attributes['sharp_edge'].data if v.value))

# ---- Bevel + Subdivision (holding edges from bevel) on a cube
bm = bmesh.new(); bmesh.ops.create_cube(bm, size=0.5); ob = obj_from_bmesh(bm, "SM_SubDBlock")
b = ob.modifiers.new("Bevel", 'BEVEL'); b.width = 0.02; b.segments = 2; b.limit_method = 'ANGLE'
s = ob.modifiers.new("Subdivision", 'SUBSURF'); s.levels = 2; s.render_levels = 2
ob.data.shade_smooth()
report(ob, "cube_Bevel(2seg)>Subsurf(2)", evaluated=True)

# ---- Solidify: grid -> shell
bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=10, y_segments=10, size=0.5); ob = obj_from_bmesh(bm, "SM_Panel")
so = ob.modifiers.new("Solidify", 'SOLIDIFY'); so.thickness = 0.02; so.offset = -1.0; so.use_even_offset = True; so.use_rim = True
report(ob, "grid_Solidify_0.02", evaluated=True)

# ---- Screw: lathe a profile (vase) and a thread
prof = [(0.0, 0.0), (0.06, 0.0), (0.08, 0.05), (0.05, 0.15), (0.04, 0.2), (0.06, 0.25), (0.0, 0.25)]
bm = bmesh.new(); vs = [bm.verts.new((x, 0, z)) for x, z in prof]
for a, b2 in zip(vs, vs[1:]): bm.edges.new((a, b2))
ob = obj_from_bmesh(bm, "SM_Vase")
sc = ob.modifiers.new("Screw", 'SCREW'); sc.angle = math.tau; sc.steps = 32; sc.render_steps = 32; sc.axis = 'Z'
sc.use_merge_vertices = True; sc.merge_threshold = 1e-4; sc.use_normal_calculate = True; sc.use_smooth_shade = True
report(ob, "screw_vase_lathe_32steps", evaluated=True)
bm = bmesh.new(); a = bm.verts.new((0.05, 0, 0)); b2 = bm.verts.new((0.06, 0, 0.002)); c = bm.verts.new((0.05, 0, 0.004))
bm.edges.new((a, b2)); bm.edges.new((b2, c)); ob = obj_from_bmesh(bm, "SM_Thread")
sc = ob.modifiers.new("Screw", 'SCREW'); sc.angle = math.tau; sc.screw_offset = 0.004; sc.iterations = 10; sc.steps = 16; sc.render_steps = 16
sc.use_normal_calculate = True
report(ob, "screw_thread_pitch4mm_x10", evaluated=True)

# ---- Curve + Array(FIT_CURVE) + Curve modifier: pipe segments along a bezier
cu = bpy.data.curves.new("CU_Path", 'CURVE'); cu.dimensions = '3D'
sp = cu.splines.new('BEZIER'); sp.bezier_points.add(3)
for p, co in zip(sp.bezier_points, [(0, 0, 0), (0.5, 0.2, 0.1), (1.0, -0.2, 0.3), (1.5, 0, 0.3)]):
    p.co = co; p.handle_left_type = p.handle_right_type = 'AUTO'
path = bpy.data.objects.new("CU_Path", cu); bpy.context.scene.collection.objects.link(path)
bm = bmesh.new()
bmesh.ops.create_cone(bm, segments=12, radius1=0.03, radius2=0.03, depth=0.1, cap_ends=False,
                      matrix=Matrix.Translation((0.05, 0, 0)) @ Matrix.Rotation(math.radians(90), 4, 'Y'))  # segment along +X
seg = obj_from_bmesh(bm, "SM_PipeSeg")
ar = seg.modifiers.new("Array", 'ARRAY'); ar.fit_type = 'FIT_CURVE'; ar.curve = path; ar.use_relative_offset = True; ar.relative_offset_displace = (1, 0, 0)
ar.use_merge_vertices = True
cm = seg.modifiers.new("Curve", 'CURVE'); cm.object = path; cm.deform_axis = 'POS_X'
report(seg, "pipe_Array(FIT_CURVE)>Curve_along_bezier", evaluated=True)

# ---- SimpleDeform TAPER on a subdivided cube
bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0); bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=4, use_grid_fill=True)
bmesh.ops.translate(bm, verts=bm.verts[:], vec=(0, 0, 0.5)); ob = obj_from_bmesh(bm, "SM_Taper")
sd = ob.modifiers.new("Taper", 'SIMPLE_DEFORM'); sd.deform_method = 'TAPER'; sd.factor = -0.6; sd.deform_axis = 'Z'
report(ob, "cube_sub4_SimpleDeform_TAPER_-0.6", evaluated=True)
dg = bpy.context.evaluated_depsgraph_get(); ev = ob.evaluated_get(dg).data
print("taper top width:", round(max(v.co.x for v in ev.vertices if v.co.z > 0.99) - min(v.co.x for v in ev.vertices if v.co.z > 0.99), 3))

# ---- Displace with procedural texture
bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=0.5); ob = obj_from_bmesh(bm, "SM_Rock")
tex = bpy.data.textures.new("T_Clouds", 'CLOUDS'); tex.noise_scale = 0.3
dp = ob.modifiers.new("Displace", 'DISPLACE'); dp.texture = tex; dp.strength = 0.08; dp.mid_level = 0.5; dp.texture_coords = 'LOCAL'
report(ob, "uvsphere_Displace_clouds_0.08", evaluated=True)

# ---- Decimate planar + Triangulate
bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0); bmesh.ops.triangulate(bm, faces=bm.faces[:]); ob = obj_from_bmesh(bm, "SM_Dec")
report(ob, "cube_pre_triangulated")
dc = ob.modifiers.new("Decimate", 'DECIMATE'); dc.decimate_type = 'DISSOLVE'; dc.angle_limit = math.radians(5)
report(ob, "cube_Decimate_DISSOLVE_5deg", evaluated=True)
tr = ob.modifiers.new("Triangulate", 'TRIANGULATE'); tr.quad_method = 'BEAUTY'; tr.ngon_method = 'BEAUTY'; tr.min_vertices = 4
report(ob, "cube_Decimate>Triangulate_export", evaluated=True)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_out"); os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "t04.blend"))
print("DONE t04")
