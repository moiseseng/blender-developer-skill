# SPDX-License-Identifier: MIT
"""
make_fixture.py - build a small test scene for the bundled scripts.

Creates one clean asset (SM_Crate_A: beveled 1 m crate, bottom-center pivot, UVs, named
material with a baked-style image) and one deliberately broken object (Cube.001: unapplied
scale and rotation, an n-gon, duplicate verts, a flipped face, no UVs, default material).

    blender -b --python make_fixture.py -- /path/out/fixture.blend
"""

import os
import sys

import bpy
import bmesh
from mathutils import Matrix, Vector

def _ensure_node_tree(mat):
    """Blender 5.x materials are node-based by default; older versions need use_nodes (removed in 6.0)."""
    if getattr(mat, "node_tree", None) is None:
        try:
            mat.use_nodes = True
        except AttributeError:
            pass


out = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "/tmp/fixture.blend"

for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)

# ---- good crate ---------------------------------------------------------------
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=1.0)
# move so the pivot (origin) is bottom-center
for v in bm.verts:
    v.co.z += 0.5
# Inset the faces to fake planks and bevel the edges so it reads as a crate.
faces = list(bm.faces)
res = bmesh.ops.inset_region(bm, faces=faces, thickness=0.06, depth=0.0, use_even_offset=True)
bmesh.ops.translate(bm, verts=list({v for f in faces for v in f.verts}), vec=(0, 0, 0))
inner = faces
for f in inner:
    bmesh.ops.translate(bm, verts=list(f.verts), vec=-f.normal * 0.02)
bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.01, segments=2, profile=0.7, affect="EDGES")
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
mesh = bpy.data.meshes.new("SM_Crate_A")
bm.to_mesh(mesh)
bm.free()
crate = bpy.data.objects.new("SM_Crate_A", mesh)
bpy.context.scene.collection.objects.link(crate)

# UVs via smart project (needs edit mode + selection in background mode).
bpy.context.view_layer.objects.active = crate
crate.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.smart_project(angle_limit=1.15192, island_margin=0.01)
bpy.ops.object.mode_set(mode="OBJECT")
bpy.ops.object.shade_smooth_by_angle(angle=0.523599)

mat = bpy.data.materials.new("M_Crate_Wood")
_ensure_node_tree(mat)
bsdf = mat.node_tree.nodes["Principled BSDF"]
img = bpy.data.images.new("T_Crate_BaseColor", 512, 512)
img.generated_type = "COLOR_GRID"
tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
tex.image = img
mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
rough = bpy.data.images.new("T_Crate_Roughness", 512, 512)
rough.colorspace_settings.name = "Non-Color"
tex2 = mat.node_tree.nodes.new("ShaderNodeTexImage")
tex2.image = rough
mat.node_tree.links.new(tex2.outputs["Color"], bsdf.inputs["Roughness"])
crate.data.materials.append(mat)

# ---- broken cube ----------------------------------------------------------------
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=1.0)
bm.faces.ensure_lookup_table()
# n-gon: dissolve an edge between two faces -> one 6-sided face
e = bm.faces[0].edges[0]
bmesh.ops.dissolve_edges(bm, edges=[e], use_verts=False)
bm.faces.ensure_lookup_table()
bm.verts.ensure_lookup_table()
# flip one face
bm.faces[1].normal_flip()
# duplicate vertex
v0 = bm.verts[0]
bm.verts.new(v0.co + Vector((1e-7, 0, 0)))
mesh2 = bpy.data.meshes.new("Cube.001")
bm.to_mesh(mesh2)
bm.free()
bad = bpy.data.objects.new("Cube.001", mesh2)
bad.scale = (2.0, 2.0, 0.5)
bad.rotation_euler = (0.0, 0.0, 0.7)
bad.location = (3.0, 0.0, 0.0)
bpy.context.scene.collection.objects.link(bad)
bad.data.materials.append(bpy.data.materials.new("Material"))

os.makedirs(os.path.dirname(out), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=out)
print("FIXTURE_SAVED=" + out)
