# SPDX-License-Identifier: MIT
"""
smoke.py - end-to-end smoke test for the bundled scripts: build a beveled cube, audit it, bake a
tiny texture set, export GLB + FBX and render a review sheet. Used by scripts/doctor.sh.

    blender -b --python smoke.py -- /tmp/out
"""

import os
import sys

import bpy
import bmesh

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(here))
out = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "/tmp/smoke"
os.makedirs(out, exist_ok=True)

from _load import load_all  # noqa: E402

def _ensure_node_tree(mat):
    """Blender 5.x materials are node-based by default; older versions need use_nodes (removed in 6.0)."""
    if getattr(mat, "node_tree", None) is None:
        try:
            mat.use_nodes = True
        except AttributeError:
            pass


mesh_audit, export_asset, render_review, bake_textures, scene_setup, material_kit = load_all(os.path.dirname(here))

scene_setup.setup("Smoke", save_path=None)

bm = bmesh.new()
bmesh.ops.create_cube(bm, size=0.5)
for v in bm.verts:
    v.co.z += 0.25
bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.02, segments=2, affect="EDGES")
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
me = bpy.data.meshes.new("SM_Smoke_Cube")
bm.to_mesh(me)
bm.free()
obj = bpy.data.objects.new("SM_Smoke_Cube", me)
bpy.data.collections["Smoke_Model"].objects.link(obj)
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.smart_project(angle_limit=1.15192, island_margin=0.02)
bpy.ops.object.mode_set(mode="OBJECT")
bpy.ops.object.shade_smooth_by_angle(angle=0.6)
mat = material_kit.pbr_material("M_Smoke", base_hex="#D9532E", roughness=0.55, metallic=0.0)
material_kit.add_roughness_breakup(mat, spread=0.1)
me.materials.append(mat)
stats = material_kit.texture_stats  # used below

audit = mesh_audit.audit(objects=["SM_Smoke_Cube"], asset_class="small_prop")
assert audit["verdict"] != "blocked", audit["issues"]
bake = bake_textures.bake("SM_Smoke_Cube", os.path.join(out, "textures"), size=128, samples=4,
                          maps=("basecolor", "roughness", "normal"))
assert len(bake["files"]) == 3, bake
st = stats(bake["files"]["normal"])
assert st["bit_depth"] == 16 and st["blue_min"] > 0.5, st
exp = export_asset.export(objects=["SM_Smoke_Cube"], asset_name="Smoke", out_dir=os.path.join(out, "export"),
                          presets=["glb", "fbx_unity"])
assert all("error" not in f for f in exp["files"]), exp
assert exp["files"][0].get("bbox_matches_scene"), exp["files"][0]
rev = render_review.review(objects=["SM_Smoke_Cube"], out_dir=os.path.join(out, "renders"), resolution=(320, 180),
                           views=("three_quarter", "front"), samples=4)
assert rev["contact_sheet"] and os.path.exists(rev["contact_sheet"]), rev
print("SMOKE_OK", out)
