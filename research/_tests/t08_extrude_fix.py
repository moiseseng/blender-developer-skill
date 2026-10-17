import bpy, bmesh, math
bm = bmesh.new(); bmesh.ops.create_cube(bm, size=2.0)
def nm(tag): print(f"  {tag:<28} verts={len(bm.verts):3d} faces={len(bm.faces):3d} nonmanifold_edges={sum(1 for e in bm.edges if not e.is_manifold)}")
bmesh.ops.bevel(bm, geom=bm.edges[:], offset=0.1, segments=2, affect='EDGES', profile=0.5, clamp_overlap=True); nm("bevel")
top = [f for f in bm.faces if f.normal.z > 0.9]
bmesh.ops.inset_region(bm, faces=top, thickness=0.2, depth=0.0, use_even_offset=True); nm("inset_region(top)")
top = [f for f in bm.faces if f.normal.z > 0.9 and f.calc_area() < 2.0]
r = bmesh.ops.extrude_face_region(bm, geom=top)
new_verts = [e for e in r["geom"] if isinstance(e, bmesh.types.BMVert)]
bmesh.ops.translate(bm, verts=new_verts, vec=(0,0,-0.3))
bmesh.ops.delete(bm, geom=top, context='FACES')          # remove originals left behind
nm("extrude + delete originals")
bmesh.ops.subdivide_edges(bm, edges=[e for e in bm.edges if all(v.co.z < -0.99 for v in e.verts)], cuts=1, use_grid_fill=True); nm("subdivide bottom")
bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-4); nm("remove_doubles")
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:]); nm("recalc_face_normals")
bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1), verts=bm.verts[:], edges=bm.edges[:]); nm("dissolve_limit")
bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY'); nm("triangulate")
me = bpy.data.meshes.new("clean"); bm.to_mesh(me); bm.free(); me.update()
print("  validate:", me.validate(verbose=True), "tris:", sum(len(p.vertices)-2 for p in me.polygons))
# delete contexts enum
print("delete contexts (docs):", "VERTS EDGES FACES_ONLY EDGES_FACES FACES REGION FACES_KEEP_BOUNDARY TAGGED_ONLY")
