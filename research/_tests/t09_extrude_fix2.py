import bpy, bmesh, math
from bmesh.types import BMVert, BMFace
def nm(bm, tag): print(f"  {tag:<30} verts={len(bm.verts):3d} faces={len(bm.faces):3d} nonmanifold_edges={sum(1 for e in bm.edges if not e.is_manifold)}")
print("=== baseline: cube, extrude one face, delete original")
bm = bmesh.new(); bmesh.ops.create_cube(bm, size=2.0)
top = [f for f in bm.faces if f.normal.z > 0.99]
r = bmesh.ops.extrude_face_region(bm, geom=top)
bmesh.ops.translate(bm, verts=[g for g in r["geom"] if isinstance(g, BMVert)], vec=(0,0,0.5))
nm(bm, "after extrude (orig kept)")
bmesh.ops.delete(bm, geom=top, context='FACES'); nm(bm, "after delete originals")
bm.free()
print("=== baseline 2: does use_keep_orig matter? / check selection-based idiom")
bm = bmesh.new(); bmesh.ops.create_cube(bm, size=2.0)
top = [f for f in bm.faces if f.normal.z > 0.99]
r = bmesh.ops.extrude_discrete_faces(bm, faces=top)
bmesh.ops.translate(bm, verts=[v for f in r["faces"] for v in f.verts], vec=(0,0,0.5))
nm(bm, "extrude_discrete_faces"); bm.free()
print("=== full chain with strict normal threshold")
bm = bmesh.new(); bmesh.ops.create_cube(bm, size=2.0)
bmesh.ops.bevel(bm, geom=bm.edges[:], offset=0.1, segments=2, affect='EDGES', profile=0.5, clamp_overlap=True); nm(bm, "bevel")
print("   faces with normal.z>0.9:", sum(1 for f in bm.faces if f.normal.z>0.9), "| >0.99:", sum(1 for f in bm.faces if f.normal.z>0.99))
top = [f for f in bm.faces if f.normal.z > 0.99]
r = bmesh.ops.inset_region(bm, faces=top, thickness=0.2, depth=0.0, use_even_offset=True); nm(bm, "inset_region(top)")
inner = [f for f in bm.faces if f.normal.z > 0.99 and f.calc_area() > 1.0]   # the inner inset face only
r = bmesh.ops.extrude_face_region(bm, geom=inner)
bmesh.ops.translate(bm, verts=[g for g in r["geom"] if isinstance(g, BMVert)], vec=(0,0,-0.3))
bmesh.ops.delete(bm, geom=inner, context='FACES'); nm(bm, "extrude inner down + delete")
bmesh.ops.subdivide_edges(bm, edges=[e for e in bm.edges if all(v.co.z < -0.99 for v in e.verts)], cuts=1, use_grid_fill=True); nm(bm, "subdivide bottom")
bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-4); nm(bm, "remove_doubles")
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:]); nm(bm, "recalc_face_normals")
bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1), verts=bm.verts[:], edges=bm.edges[:]); nm(bm, "dissolve_limit")
bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY'); nm(bm, "triangulate")
me = bpy.data.meshes.new("clean"); bm.to_mesh(me); bm.free(); me.update()
print("  validate:", me.validate(verbose=True), "tris:", sum(len(p.vertices)-2 for p in me.polygons))
