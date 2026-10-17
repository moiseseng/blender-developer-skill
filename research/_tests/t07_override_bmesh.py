import bpy, bmesh, math
def tryp(label, fn):
    try: r = fn(); print("OK  ", label, "->", r); return r
    except Exception as ex: print("FAIL", label, "->", type(ex).__name__, str(ex)[:160]); return None
sc = bpy.context.scene; vl = bpy.context.view_layer
cube = bpy.data.objects["Cube"]; cube.select_set(True); vl.objects.active = cube
print("=== ops that need a VIEW_3D context in -b")
win = bpy.context.window; v3d = next(a for a in win.screen.areas if a.type=='VIEW_3D'); reg = next(r for r in v3d.regions if r.type=='WINDOW')
for opname in ("view3d.camera_to_view_selected", "view3d.view_selected", "view3d.snap_cursor_to_selected", "object.origin_set", "mesh.primitive_cube_add"):
    mod, name = opname.split("."); op = getattr(getattr(bpy.ops, mod), name)
    print("poll no override:", opname, op.poll())
    def run():
        with bpy.context.temp_override(window=win, area=v3d, region=reg):
            return (op.poll(), op() if op.poll() else None)
    tryp("  with temp_override(VIEW_3D)", run)
print("=== bmesh chain, manifold check after each step")
bm = bmesh.new(); bmesh.ops.create_cube(bm, size=2.0)
def nm(tag):
    bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table()
    print(f"  {tag:<22} verts={len(bm.verts):3d} faces={len(bm.faces):3d} nonmanifold_edges={sum(1 for e in bm.edges if not e.is_manifold)}")
nm("create_cube")
bmesh.ops.bevel(bm, geom=bm.verts[:]+bm.edges[:]+bm.faces[:], offset=0.1, segments=2, affect='EDGES', profile=0.5, clamp_overlap=True); nm("bevel")
bmesh.ops.inset_region(bm, faces=bm.faces[:], thickness=0.05, depth=0.0, use_even_offset=True); nm("inset_region(all)")
top = [f for f in bm.faces if f.normal.z > 0.9]
r = bmesh.ops.extrude_face_region(bm, geom=top)
verts = [e for e in r["geom"] if isinstance(e, bmesh.types.BMVert)]
bmesh.ops.translate(bm, verts=verts, vec=(0,0,0.5)); nm("extrude_face_region")
bmesh.ops.delete(bm, geom=top, context='FACES') if False else None
nm("(orig faces kept?)")
# check: does extrude_face_region leave the original faces behind? count faces with same verts...
bm2 = bmesh.new(); bmesh.ops.create_cube(bm2, size=2.0)
top2 = [f for f in bm2.faces if f.normal.z > 0.9]
r2 = bmesh.ops.extrude_face_region(bm2, geom=top2)
v2 = [e for e in r2["geom"] if isinstance(e, bmesh.types.BMVert)]
bmesh.ops.translate(bm2, verts=v2, vec=(0,0,0.5))
print("  cube+extrude only: faces", len(bm2.faces), "nonmanifold", sum(1 for e in bm2.edges if not e.is_manifold), "-> original top face removed by op?", len(bm2.faces)==10)
bm2.free()
bmesh.ops.subdivide_edges(bm, edges=bm.edges[:5], cuts=1, use_grid_fill=True); nm("subdivide_edges(5)")
bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-4); nm("remove_doubles")
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:]); nm("recalc_face_normals")
bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1), verts=bm.verts[:], edges=bm.edges[:], delimit={'NORMAL'}); nm("dissolve_limit")
bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY'); nm("triangulate")
bm.free()
print("=== clean chain: subdivide all edges of a region instead of 5 arbitrary ones")
bm = bmesh.new(); bmesh.ops.create_cube(bm, size=2.0)
bmesh.ops.bevel(bm, geom=bm.edges[:], offset=0.1, segments=2, affect='EDGES', profile=0.5, clamp_overlap=True); nm("bevel(edges only)")
top = [f for f in bm.faces if f.normal.z > 0.9]
bmesh.ops.inset_region(bm, faces=top, thickness=0.2, depth=0.0, use_even_offset=True); nm("inset_region(top)")
top = [f for f in bm.faces if f.normal.z > 0.9 and f.calc_area() < 2.0]
r = bmesh.ops.extrude_face_region(bm, geom=top)
bmesh.ops.translate(bm, verts=[e for e in r["geom"] if isinstance(e, bmesh.types.BMVert)], vec=(0,0,-0.3)); nm("extrude inset down")
bmesh.ops.subdivide_edges(bm, edges=[e for e in bm.edges if all(v.co.z < -0.99 for v in e.verts)], cuts=1, use_grid_fill=True); nm("subdivide bottom edges")
bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-4); nm("remove_doubles")
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:]); nm("recalc_face_normals")
bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1), verts=bm.verts[:], edges=bm.edges[:]); nm("dissolve_limit")
bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY'); nm("triangulate")
me = bpy.data.meshes.new("clean"); bm.to_mesh(me); bm.free(); me.update()
print("  validate:", me.validate(verbose=True))
