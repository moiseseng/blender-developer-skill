import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _check import *
import bpy, bmesh, math
from mathutils import Vector, Matrix, noise
reset_scene()

# ---- boulder: icosphere + layered noise displacement along normals + smoothing
bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=4, radius=0.5); bm.normal_update()
for v in bm.verts:
    p = v.co
    d = 0.12 * noise.noise(p * 1.5) + 0.04 * noise.noise(p * 6.0 + Vector((7, 3, 1)))
    v.co += v.normal * d
bmesh.ops.scale(bm, vec=(1.0, 0.8, 0.6), verts=bm.verts[:])       # squash
report(snapshot(bm, "boulder_raw"), "organic_boulder_icosub4_noise")
bmesh.ops.smooth_vert(bm, verts=bm.verts[:], factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
bmesh.ops.smooth_vert(bm, verts=bm.verts[:], factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
ob = obj_from_bmesh(bm, "SM_Boulder"); ob.data.shade_smooth(); report(ob, "organic_boulder_smooth_vert_x2")

# ---- subdivided cube + noise = chunky rock (quads, good for subsurf)
bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=6, use_grid_fill=True); bm.normal_update()
for v in bm.verts:
    v.co += v.normal * 0.08 * noise.noise(v.co * 2.0)
bmesh.ops.smooth_vert(bm, verts=bm.verts[:], factor=0.7, use_axis_x=True, use_axis_y=True, use_axis_z=True)
ob = obj_from_bmesh(bm, "SM_Rock_Quad"); s = ob.modifiers.new("Subsurf", 'SUBSURF'); s.levels = 1
report(ob, "organic_cube_sub6_noise_subsurf1", evaluated=True)

# ---- metaballs -> mesh (blobby base mesh)
mb = bpy.data.metaballs.new("MB_Blob"); mb.resolution = 0.05; mb.threshold = 0.6
for co, r in [((0, 0, 0), 0.4), ((0.35, 0, 0.1), 0.3), ((-0.3, 0.1, 0.15), 0.25), ((0, 0.3, 0.3), 0.2)]:
    el = mb.elements.new(); el.co = co; el.radius = r
mb_ob = bpy.data.objects.new("MB_Blob", mb); bpy.context.scene.collection.objects.link(mb_ob)
me = evaluated_mesh(mb_ob, "SM_Blob"); blob = bpy.data.objects.new("SM_Blob", me); bpy.context.scene.collection.objects.link(blob)
report(blob, "organic_metaball_4_elements_res0.05")
bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(3), verts=bm.verts[:], edges=bm.edges[:])
bm.to_mesh(me); bm.free(); report(blob, "organic_metaball_dissolve_limit_3deg")

# ---- Skin modifier tree from an edge skeleton
bm = bmesh.new()
def chain(pts): 
    vs = [bm.verts.new(p) for p in pts]
    for a, b in zip(vs, vs[1:]): bm.edges.new((a, b))
    return vs
trunk = chain([(0, 0, 0), (0, 0, 0.8), (0.05, 0, 1.6), (0.1, 0.05, 2.3)])
b1 = chain([(0.05, 0, 1.6), (0.5, 0.1, 2.1), (0.9, 0.2, 2.4)]); bm.edges.new((trunk[2], b1[0]))
b2 = chain([(0.1, 0.05, 2.3), (-0.3, -0.3, 2.9), (-0.5, -0.6, 3.3)]); bm.edges.new((trunk[3], b2[0]))
bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-4)
bm.verts.ensure_lookup_table()
# radius by height: thick at root, thin at tips
radii = [0.12 * max(0.15, 1.0 - v.co.z / 3.5) for v in bm.verts]
tree = obj_from_bmesh(bm, "SM_Tree"); report(tree, "skin_0_skeleton_edges_only")
sk = tree.modifiers.new("Skin", 'SKIN'); sk.use_smooth_shade = True; sk.branch_smoothing = 0.5
print("skin layer exists:", len(tree.data.skin_vertices), "entries:", len(tree.data.skin_vertices[0].data))
for sv, r in zip(tree.data.skin_vertices[0].data, radii): sv.radius = (r, r)
root = min(range(len(tree.data.vertices)), key=lambda i: tree.data.vertices[i].co.z)
tree.data.skin_vertices[0].data[root].use_root = True
report(tree, "skin_1_skin_modifier", evaluated=True)
ss = tree.modifiers.new("Subsurf", 'SUBSURF'); ss.levels = 2
report(tree, "skin_2_skin>subsurf2", evaluated=True)
apply_stack(tree); report(tree, "skin_3_applied")

# ---- Lattice deformation (2x2x3 cage, taper + lean the top)
bm = bmesh.new(); bmesh.ops.create_cone(bm, segments=24, radius1=0.3, radius2=0.3, depth=1.0, cap_ends=True, matrix=Matrix.Translation((0, 0, 0.5)))
bmesh.ops.subdivide_edges(bm, edges=[e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > 0.5], cuts=6)
can = obj_from_bmesh(bm, "SM_Can"); report(can, "lattice_0_can_base")
lat = bpy.data.lattices.new("LT_Taper"); lat.points_u = lat.points_v = 2; lat.points_w = 3
lat_ob = bpy.data.objects.new("LT_Taper", lat); bpy.context.scene.collection.objects.link(lat_ob)
lat_ob.scale = (0.7, 0.7, 1.0); lat_ob.location = (0, 0, 0.5)         # cage covers the can (lattice spans -0.5..0.5)
for i, p in enumerate(lat.points):               # index order: u fastest, then v, then w
    w = i // (2 * 2)
    if w == 2: p.co_deform = (p.co_deform.x * 0.5 + 0.3, p.co_deform.y * 0.5, p.co_deform.z)   # top: shrink + lean +X
lm = can.modifiers.new("Lattice", 'LATTICE'); lm.object = lat_ob
report(can, "lattice_1_taper_lean_evaluated", evaluated=True)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_out"); os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "t08.blend"))
print("DONE t08")
