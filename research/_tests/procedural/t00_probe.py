import bpy, bmesh, sys
print("BLENDER", bpy.app.version_string)
# Boolean solver enum
bpy.ops.wm.read_factory_settings(use_empty=True)
me = bpy.data.meshes.new("m"); ob = bpy.data.objects.new("o", me); bpy.context.scene.collection.objects.link(ob)
mod = ob.modifiers.new("b", 'BOOLEAN')
print("BOOL solver enum:", [i.identifier for i in mod.bl_rna.properties['solver'].enum_items])
# Modifier types available
print("MOD types sample:", [i.identifier for i in ob.modifiers.bl_rna.functions['new'].parameters['type'].enum_items if i.identifier in ('BEVEL','WEIGHTED_NORMAL','SMOOTH_BY_ANGLE','NODES','SOLIDIFY','SCREW','SKIN','LATTICE','SIMPLE_DEFORM','DISPLACE','DECIMATE','TRIANGULATE','MIRROR','ARRAY','SUBSURF','CURVE','WELD','REMESH')])
# Smooth by angle: is it a modifier type or operator?
try:
    m2 = ob.modifiers.new("sba", 'SMOOTH_BY_ANGLE'); print("SMOOTH_BY_ANGLE modifier type OK", m2.type)
except Exception as e: print("SMOOTH_BY_ANGLE modifier:", e)
print("has bpy.ops.object.shade_smooth_by_angle:", hasattr(bpy.ops.object, 'shade_smooth_by_angle'), "shade_auto_smooth:", hasattr(bpy.ops.object, 'shade_auto_smooth'))
print("Mesh.shade_smooth method:", hasattr(me, 'shade_smooth'), "Mesh.shade_flat:", hasattr(me, 'shade_flat'))
print("Mesh.use_auto_smooth attr:", hasattr(me, 'use_auto_smooth'))
print("Mesh.normals_split_custom_set:", hasattr(me, 'normals_split_custom_set'))
print("Mesh.validate/update:", hasattr(me,'validate'), hasattr(me,'update'))
print("bmesh.ops has:", [n for n in ('create_cube','create_cone','create_circle','create_uvsphere','create_icosphere','create_grid','extrude_face_region','inset_region','inset_individual','bevel','bisect_plane','bridge_loops','spin','symmetrize','remove_doubles','recalc_face_normals','dissolve_limit','triangulate','smooth_vert','subdivide_edges','solidify','wireframe','holes_fill','edgenet_fill','grid_fill','mirror','poke','unsubdivide','scale','rotate','translate','duplicate','split_edges','contextual_create','join_triangles','connect_verts','weld_verts','delete','region_extend','planar_faces','average_vert_facedata','rotate_edges','reverse_faces','beautify_fill','offset_edgeloops','convex_hull','transform','pointmerge') if not hasattr(bmesh.ops, n)], "<- MISSING")
# GN node group interface
ng = bpy.data.node_groups.new("GN_Test", 'GeometryNodeTree')
s_in = ng.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
s_out = ng.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
f = ng.interface.new_socket("Count", in_out='INPUT', socket_type='NodeSocketInt'); f.default_value=5; f.min_value=1
print("GN interface OK:", [ (i.name, i.item_type, getattr(i,'in_out',None), getattr(i,'socket_type',None)) for i in ng.interface.items_tree])
print("identifier of Count:", f.identifier)
nm = ob.modifiers.new("gn", 'NODES'); nm.node_group = ng
print("mod[identifier] get:", nm[f.identifier])
# Node names check
for nt in ('GeometryNodeMeshLine','GeometryNodeInstanceOnPoints','GeometryNodeDistributePointsOnFaces','GeometryNodeRealizeInstances','GeometryNodeSetMaterial','GeometryNodeTransform','GeometryNodeMeshCylinder','GeometryNodeMeshGrid','GeometryNodeMeshCube','GeometryNodeSetShadeSmooth','GeometryNodeMergeByDistance','GeometryNodeMeshBoolean','GeometryNodeInputPosition','ShaderNodeMath','FunctionNodeRandomValue','GeometryNodeCurveToMesh','GeometryNodeCurvePrimitiveCircle','GeometryNodeSubdivisionSurface','GeometryNodeMeshToCurve','GeometryNodeInputNormal','GeometryNodeInputIndex','GeometryNodeSetPosition','GeometryNodeInputMeshFaceArea','GeometryNodeGroupInput','NodeGroupInput','NodeGroupOutput','GeometryNodeTransformGeometry','FunctionNodeAlignRotationToVector','FunctionNodeAlignEulerToVector','GeometryNodeRotateInstances','GeometryNodeScaleInstances','GeometryNodeJoinGeometry','FunctionNodeCombineTransform','GeometryNodeBevelMesh','GeometryNodeExtrudeMesh','GeometryNodeScaleElements','GeometryNodeFlipFaces','GeometryNodeDeleteGeometry','GeometryNodeSeparateGeometry','GeometryNodeDualMesh','GeometryNodeTriangulate','GeometryNodeMeshIcoSphere','GeometryNodeMeshUVSphere','GeometryNodeMeshCone','GeometryNodeMeshCircle','GeometryNodeResampleCurve','GeometryNodeFillCurve','GeometryNodeFilletCurve','GeometryNodeCurveQuadrilateral','GeometryNodeCurvePrimitiveBezierSegment','GeometryNodeSetCurveRadius','GeometryNodeCurvePrimitiveLine','GeometryNodeSplineParameter','GeometryNodeStoreNamedAttribute','ShaderNodeTexNoise','ShaderNodeVectorMath','ShaderNodeMapRange'):
    try:
        n = ng.nodes.new(nt); 
    except Exception as e:
        print("NODE MISSING:", nt, "->", str(e)[:80])
print("nodes created:", len(ng.nodes))
# new_from_object signature
print("new_from_object:", bpy.data.meshes.new_from_object.__doc__[:300])
# attribute names: sharp_face, bevel_weight_edge
print("Mesh attributes:", [a.name for a in me.attributes])
print("Object has set_origin? ops:", hasattr(bpy.ops.object,'origin_set'))
print("mathutils noise:", __import__('mathutils').noise.noise((0.1,0.2,0.3)))
print("DONE")
