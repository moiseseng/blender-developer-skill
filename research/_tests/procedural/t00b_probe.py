import bpy, bmesh
bpy.ops.wm.read_factory_settings(use_empty=True)
me = bpy.data.meshes.new("m"); ob = bpy.data.objects.new("o", me); bpy.context.scene.collection.objects.link(ob)
ng = bpy.data.node_groups.new("GN_Test", 'GeometryNodeTree')
ng.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
ng.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
f = ng.interface.new_socket("Count", in_out='INPUT', socket_type='NodeSocketInt'); f.default_value=5
nm = ob.modifiers.new("gn", 'NODES'); nm.node_group = ng
print("dir(NodesModifier) non-underscore:", [a for a in dir(nm) if not a.startswith('_') and a not in dir(bpy.types.Modifier)])
print("rna props:", [p.identifier for p in nm.bl_rna.properties])
print("rna funcs:", [p.identifier for p in nm.bl_rna.functions])
for cand in ('inputs','input_values','node_inputs','socket_values'):
    print(cand, hasattr(nm, cand))
try:
    sp = nm.bl_system_properties_get(do_create=True); print("system props:", sp, list(sp.keys()) if sp else None)
    if sp is not None:
        print("sp[Socket_2]:", sp.get("Socket_2"))
except Exception as e: print("sysprops err", e)
# Try path_resolve
try:
    print("path_resolve:", nm.path_resolve('["Socket_2"]'))
except Exception as e: print("path_resolve err:", e)
# shade smooth by angle in -b mode
bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0); bm.to_mesh(me); bm.free()
bpy.context.view_layer.objects.active = ob; ob.select_set(True)
try:
    r = bpy.ops.object.shade_auto_smooth(angle=0.523599); print("shade_auto_smooth:", r, [m.type for m in ob.modifiers], [m.name for m in ob.modifiers])
except Exception as e: print("shade_auto_smooth err:", e)
try:
    r = bpy.ops.object.shade_smooth_by_angle(angle=0.523599); print("shade_smooth_by_angle:", r, [a.name for a in me.attributes])
except Exception as e: print("shade_smooth_by_angle err:", e)
for m in ob.modifiers:
    if m.type=='NODES': print("mod", m.name, m.node_group.name if m.node_group else None, m.node_group.library if m.node_group else None)
print("Mesh attributes:", [(a.name, a.data_type, a.domain) for a in me.attributes])
