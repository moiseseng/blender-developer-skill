"""Shared self-check helpers for procedural bpy tests (Blender 5.2, -b mode).
Import:  import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from _check import *
"""
import bpy, bmesh, math
from mathutils import Vector, Matrix

def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = 'METRIC'
    bpy.context.scene.unit_settings.scale_length = 1.0

def ensure_collection(name, parent=None):
    parent = parent or bpy.context.scene.collection
    col = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if col.name not in parent.children:
        parent.children.link(col)
    return col

def obj_from_bmesh(bm, name, collection=None, free=True):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    if free: bm.free()
    me.update()
    ob = bpy.data.objects.new(name, me)
    (collection or bpy.context.scene.collection).objects.link(ob)
    return ob

def snapshot(bm, name, collection=None):
    """Copy the live bmesh into a new object (for stage-by-stage reporting)."""
    return obj_from_bmesh(bm.copy(), name, collection)

def evaluated_mesh(ob, name=None, preserve=True):
    """New Mesh datablock = ob with its whole modifier stack applied. Works in -b."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=preserve, depsgraph=dg)
    me.name = name or (ob.data.name + "_applied")
    return me

def apply_stack(ob):
    """Replace ob.data with the evaluated result and drop the modifiers (in place)."""
    me = evaluated_mesh(ob, ob.data.name)
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    if old.users == 0:
        bpy.data.meshes.remove(old)
    return ob

def origin_to_bottom_center(ob):
    """Move the pivot to bbox bottom-center by shifting verts; world placement is kept."""
    me = ob.data
    xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]; zs = [v.co.z for v in me.vertices]
    off = Vector(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, min(zs)))
    me.transform(Matrix.Translation(-off))
    ob.matrix_world = ob.matrix_world @ Matrix.Translation(off)
    me.update()

def apply_transforms(ob):
    """Bake loc/rot/scale into the mesh (equivalent of Ctrl+A All Transforms)."""
    ob.data.transform(ob.matrix_world)
    ob.matrix_world = Matrix.Identity(4)
    ob.data.update()

def mesh_stats(me, matrix=None):
    matrix = matrix or Matrix.Identity(4)
    me.calc_loop_triangles()
    st = dict(verts=len(me.vertices), faces=len(me.polygons), tris=len(me.loop_triangles),
              ngons=sum(1 for p in me.polygons if len(p.vertices) > 4))
    if me.vertices:
        cs = [matrix @ v.co for v in me.vertices]
        mn = Vector((min(c.x for c in cs), min(c.y for c in cs), min(c.z for c in cs)))
        mx = Vector((max(c.x for c in cs), max(c.y for c in cs), max(c.z for c in cs)))
        d = mx - mn
        st['dims'] = f"{d.x:.3f}x{d.y:.3f}x{d.z:.3f}"; st['zmin'] = round(mn.z, 4)
    else:
        st['dims'] = "0x0x0"; st['zmin'] = 0
    bm = bmesh.new(); bm.from_mesh(me); bm.normal_update()
    st['nonmanifold'] = sum(1 for e in bm.edges if not e.is_manifold)
    st['boundary'] = sum(1 for e in bm.edges if e.is_boundary)
    st['loose'] = sum(1 for v in bm.verts if not v.link_edges)
    before = [f.normal.copy() for f in bm.faces]
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    # faces whose winding had to be flipped to make the mesh consistent/outward
    st['flipped'] = sum(1 for f, n in zip(bm.faces, before) if f.normal.dot(n) < 0)
    bm.free()
    return st

def report(ob, label, evaluated=False, world=True):
    bpy.context.view_layer.update()
    if evaluated:
        dg = bpy.context.evaluated_depsgraph_get(); me = ob.evaluated_get(dg).data
    else:
        me = ob.data
    s = mesh_stats(me, ob.matrix_world if world else None)
    print(f"RESULT|{label}|verts={s['verts']}|faces={s['faces']}|tris={s['tris']}|ngons={s['ngons']}"
          f"|dims={s['dims']}|zmin={s['zmin']}|nonmanifold={s['nonmanifold']}|boundary={s['boundary']}"
          f"|loose={s['loose']}|flipped={s['flipped']}")
    return s
