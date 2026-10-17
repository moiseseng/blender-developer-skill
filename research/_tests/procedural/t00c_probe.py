import bpy, bmesh
bpy.ops.wm.read_factory_settings(use_empty=True)
me = bpy.data.meshes.new("m"); ob = bpy.data.objects.new("o", me); bpy.context.scene.collection.objects.link(ob)
bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=4, y_segments=4, size=1.0); bm.to_mesh(me); bm.free()
ng = bpy.data.node_groups.new("GN_Test", 'GeometryNodeTree')
ng.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
ng.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
f = ng.interface.new_socket("Count", in_out='INPUT', socket_type='NodeSocketInt'); f.default_value=5
s = ng.interface.new_socket("Scale", in_out='INPUT', socket_type='NodeSocketFloat'); s.default_value=0.2
o = ng.interface.new_socket("Mat", in_out='INPUT', socket_type='NodeSocketMaterial')
gi = ng.nodes.new('NodeGroupInput'); go = ng.nodes.new('NodeGroupOutput')
ng.links.new(gi.outputs['Geometry'], go.inputs['Geometry'])
nm = ob.modifiers.new("gn", 'NODES'); nm.node_group = ng
inp = nm.properties.inputs
print("inputs type:", type(inp).__name__, "rna props:", [x.identifier for x in inp.bl_rna.properties])
print("dir:", [a for a in dir(inp) if not a.startswith('_')][:40])
print("identifiers:", f.identifier, s.identifier, o.identifier)
try:
    it = getattr(inp, f.identifier); print("getattr OK:", it, [(x.identifier, getattr(it, x.identifier)) for x in it.bl_rna.properties if x.identifier!='rna_type'])
except Exception as e: print("getattr err:", e)
try:
    it = inp[f.identifier]; print("[] OK:", it)
except Exception as e: print("[] err:", e)
try:
    print("path_resolve:", nm.path_resolve(f'properties.inputs.{f.identifier}.value'))
except Exception as e: print("path_resolve err:", e)
getattr(inp, f.identifier).value = 12; print("int set:", getattr(inp, f.identifier).value)
getattr(inp, s.identifier).value = 0.33; print("float set:", getattr(inp, s.identifier).value)
mat = bpy.data.materials.new("M_Test"); getattr(inp, o.identifier).value = mat; print("mat set:", getattr(inp, o.identifier).value)
print("input types enum:", [i.identifier for i in getattr(inp, f.identifier).bl_rna.properties['type'].enum_items] if 'type' in getattr(inp, f.identifier).bl_rna.properties else 'no type prop')
dg = bpy.context.evaluated_depsgraph_get(); ev = ob.evaluated_get(dg); print("eval verts:", len(ev.data.vertices))
