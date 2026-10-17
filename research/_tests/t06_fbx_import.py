import bpy, os
OUT = "/Users/Game/blender-3d-team/research/_tests/_out"
print("wm.fbx_import exists:", hasattr(bpy.ops.wm, "fbx_import"))
if hasattr(bpy.ops.wm, "fbx_import"):
    print("fbx_import params:", sorted(p.identifier for p in bpy.ops.wm.fbx_import.get_rna_type().properties if not p.identifier.startswith("filter_") and p.identifier not in ("rna_type",)))
print("import_scene.fbx (legacy) exists:", hasattr(bpy.ops.import_scene, "fbx"))
print("wm.gltf_import exists:", hasattr(bpy.ops.wm, "gltf_import"), "| import_scene.gltf:", hasattr(bpy.ops.import_scene, "gltf"))
# round-trip import the FBX written earlier
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
r = bpy.ops.wm.fbx_import(filepath=os.path.join(OUT, "cube.fbx"))
print("fbx_import result", r, [o.name for o in bpy.data.objects])
r = bpy.ops.import_scene.gltf(filepath=os.path.join(OUT, "cube.glb"))
print("gltf import result", r, [o.name for o in bpy.data.objects])
# mesh.from_pydata invalid data + validate
me = bpy.data.meshes.new("bad"); me.from_pydata([(0,0,0),(1,0,0),(0,1,0)], [], [(0,1,2),(0,1,9)])
print("validate fixed invalid:", me.validate(verbose=False), "polys now", len(me.polygons))
