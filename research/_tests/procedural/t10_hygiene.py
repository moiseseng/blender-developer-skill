import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _check import *
import bpy, bmesh, math
from mathutils import Vector, Matrix
reset_scene()
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_out"); os.makedirs(OUT, exist_ok=True)

ASSET = "Crate"; SIZE = 0.8                     # real-world metres
col = ensure_collection(f"SM_{ASSET}")
# body: box with inset planks, built centred then pivot moved to bottom-centre
bm = bmesh.new(); bmesh.ops.create_cube(bm, size=SIZE)
bmesh.ops.inset_individual(bm, faces=bm.faces[:], thickness=0.04, depth=0.0, use_even_offset=True)
bmesh.ops.inset_individual(bm, faces=[f for f in bm.faces if f.calc_area() > 0.3], thickness=0.0, depth=-0.01)
body = obj_from_bmesh(bm, f"SM_{ASSET}_Body", col)
body.location = (3.0, 2.0, 0.0); body.scale = (1, 1, 1.25)   # messy placement (scale left unapplied)
report(body, "hygiene_0_body_WORLD_bbox_before"); report(body, "hygiene_0_body_LOCAL_mesh_before", world=False)
apply_transforms(body); report(body, "hygiene_1_apply_transforms_LOCAL (z scale 1.25 baked)", world=False)
print("matrix_world identity:", body.matrix_world == Matrix.Identity(4), "scale:", tuple(body.scale))
origin_to_bottom_center(body); report(body, "hygiene_2_origin_bottom_center_LOCAL (zmin 0)", world=False)
print("origin now at world:", tuple(round(c, 3) for c in body.matrix_world.translation), '(= old bbox bottom-centre; mesh did not move in world space)')
body.location = (0, 0, 0)       # final placement = pivot on the ground at origin
report(body, "hygiene_3_placed_at_origin_WORLD")
# lid part, named + collected
bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Diagonal((SIZE * 1.05, SIZE * 1.05, 0.05, 1)))
lid = obj_from_bmesh(bm, f"SM_{ASSET}_Lid", col); origin_to_bottom_center(lid); lid.location = body.matrix_world.translation + Vector((0, 0, SIZE * 1.25))
lid.parent = body; lid.matrix_parent_inverse = body.matrix_world.inverted()
report(lid, "hygiene_4_lid")
print("collection contents:", [o.name for o in col.objects], "dims body:", tuple(round(d, 3) for d in body.dimensions))

# ---- self-check catches: loose vert, non-manifold edge, flipped face, ngon
bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
bm.verts.new((5, 5, 5))                                           # loose vert
bm.verts.ensure_lookup_table(); v0 = bm.verts[0]; v = bm.verts.new((2, 0, 0)); bm.edges.new((v, v0))   # adding verts invalidates the lookup table       # dangling wire edge (non-manifold)
bm.faces.ensure_lookup_table(); bmesh.ops.reverse_faces(bm, faces=[bm.faces[0]])                  # one flipped face
bad = obj_from_bmesh(bm, "SM_Bad"); report(bad, "hygiene_5_bad_mesh_detected")
print("validate() changed data:", bad.data.validate(verbose=False))
bm = bmesh.new(); bm.from_mesh(bad.data)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_edges], context='VERTS')
bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context='EDGES')
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_edges], context='VERTS')
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:]); bm.to_mesh(bad.data); bm.free()
report(bad, "hygiene_6_bad_mesh_fixed")

# ---- export sanity (glTF + FBX) in -b
for o in bpy.data.objects: o.select_set(o.name.startswith("SM_Crate"))
r = bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "SM_Crate.glb"), export_format='GLB', use_selection=True, export_apply=True, export_yup=True)
print("gltf:", r, os.path.getsize(os.path.join(OUT, "SM_Crate.glb")), "bytes")
r = bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, "SM_Crate.fbx"), use_selection=True, apply_scale_options='FBX_SCALE_ALL', bake_space_transform=True, use_mesh_modifiers=True)
print("fbx:", r, os.path.getsize(os.path.join(OUT, "SM_Crate.fbx")), "bytes")
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "t10_hygiene.blend"))
print("DONE t10")
