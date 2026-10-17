import bpy, bmesh
bpy.ops.wm.read_factory_settings(use_empty=True)
# bevel with NO affect/segments kwargs
bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
r = bmesh.ops.bevel(bm, geom=bm.edges[:] + bm.verts[:], offset=0.1)
print("BEVEL default kwargs on cube (edges+verts geom): faces", len(bm.faces), "verts", len(bm.verts), "new faces", len(r['faces']))
bm2 = bmesh.new(); bmesh.ops.create_cube(bm2, size=1.0)
r = bmesh.ops.bevel(bm2, geom=bm2.edges[:], offset=0.1)
print("BEVEL default kwargs (edges-only geom): faces", len(bm2.faces), "verts", len(bm2.verts))
bm3 = bmesh.new(); bmesh.ops.create_cube(bm3, size=1.0)
bmesh.ops.bevel(bm3, geom=bm3.edges[:], offset=0.1, affect='EDGES')
print("BEVEL affect=EDGES, no segments: faces", len(bm3.faces), "(26 = 1 segment)")
bm4 = bmesh.new(); bmesh.ops.create_cube(bm4, size=1.0)
bmesh.ops.bevel(bm4, geom=bm4.verts[:], offset=0.1, affect='VERTICES')
print("BEVEL affect=VERTICES explicit: faces", len(bm4.faces), "(14 = 6 + 8 corner tris)")
# socket_type='DEFAULT'
ng = bpy.data.node_groups.new("G", 'GeometryNodeTree')
try:
    s = ng.interface.new_socket("X", in_out='INPUT', socket_type='DEFAULT'); print("socket_type=DEFAULT ->", s.socket_type, s.bl_socket_idname)
except Exception as e:
    print("socket_type=DEFAULT error:", e)
try:
    s = ng.interface.new_socket("Y", in_out='INPUT'); print("socket_type omitted ->", s.socket_type)
except Exception as e:
    print("socket_type omitted error:", e)
