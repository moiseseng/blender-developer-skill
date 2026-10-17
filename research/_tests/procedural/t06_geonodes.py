import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _check import *
import bpy, bmesh, math
from mathutils import Vector, Matrix
reset_scene()

def link(ng, a, b):
    try:
        return ng.links.new(a, b)
    except Exception as e:
        print("LINK FAIL", a.node.name, a.name, "->", b.node.name, b.name, e); raise

def socket_id(ng, name, in_out='INPUT'):
    for it in ng.interface.items_tree:
        if it.item_type == 'SOCKET' and it.in_out == in_out and it.name == name: return it.identifier
    raise KeyError(name)

def set_input(mod, name, value):
    """5.2 API: modifier.properties.inputs.<identifier>.value (modifier[identifier] no longer works)."""
    getattr(mod.properties.inputs, socket_id(mod.node_group, name)).value = value

# ---- Group 1: bolt row. Mesh Line -> Instance on Points(cylinder) -> Realize -> Set Material -> Join with input
ng = bpy.data.node_groups.new("GN_BoltRow", 'GeometryNodeTree')
ng.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
ng.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
s = ng.interface.new_socket("Count", in_out='INPUT', socket_type='NodeSocketInt'); s.default_value = 6; s.min_value = 1
s = ng.interface.new_socket("Spacing", in_out='INPUT', socket_type='NodeSocketFloat'); s.default_value = 0.05; s.subtype = 'DISTANCE'
s = ng.interface.new_socket("Bolt Radius", in_out='INPUT', socket_type='NodeSocketFloat'); s.default_value = 0.01
ng.interface.new_socket("Material", in_out='INPUT', socket_type='NodeSocketMaterial')
n = ng.nodes
gi = n.new('NodeGroupInput'); go = n.new('NodeGroupOutput')
line = n.new('GeometryNodeMeshLine'); line.mode = 'OFFSET'
print("MeshLine inputs:", [i.name for i in line.inputs], "outputs:", [o.name for o in line.outputs])
xyz = n.new('ShaderNodeCombineXYZ')
cyl = n.new('GeometryNodeMeshCylinder'); cyl.inputs['Vertices'].default_value = 6; cyl.inputs['Depth'].default_value = 0.008
print("Cylinder inputs:", [i.name for i in cyl.inputs])
iop = n.new('GeometryNodeInstanceOnPoints'); print("InstanceOnPoints inputs:", [i.name for i in iop.inputs])
real = n.new('GeometryNodeRealizeInstances'); print("Realize inputs:", [i.name for i in real.inputs])
setm = n.new('GeometryNodeSetMaterial'); smooth = n.new('GeometryNodeSetShadeSmooth')
xf = n.new('GeometryNodeTransform'); print("Transform inputs:", [i.name for i in xf.inputs])
xf.inputs['Translation'].default_value = (0, 0, 0.5)        # lift bolts onto the top face of a 1m cube
join = n.new('GeometryNodeJoinGeometry')
link(ng, gi.outputs['Count'], line.inputs['Count'])
link(ng, gi.outputs['Spacing'], xyz.inputs['X']); link(ng, xyz.outputs['Vector'], line.inputs['Offset'])
link(ng, gi.outputs['Bolt Radius'], cyl.inputs['Radius'])
link(ng, line.outputs['Mesh'], iop.inputs['Points']); link(ng, cyl.outputs['Mesh'], iop.inputs['Instance'])
link(ng, iop.outputs['Instances'], real.inputs['Geometry'])
link(ng, real.outputs['Geometry'], setm.inputs['Geometry']); link(ng, gi.outputs['Material'], setm.inputs['Material'])
link(ng, setm.outputs['Geometry'], smooth.inputs['Geometry']); link(ng, smooth.outputs['Geometry'], xf.inputs['Geometry'])
link(ng, gi.outputs['Geometry'], join.inputs['Geometry']); link(ng, xf.outputs['Geometry'], join.inputs['Geometry'])
link(ng, join.outputs['Geometry'], go.inputs['Geometry'])

bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0); ob = obj_from_bmesh(bm, "SM_Hull")
mat = bpy.data.materials.new("M_Bolt")
mod = ob.modifiers.new("Bolts", 'NODES'); mod.node_group = ng
set_input(mod, "Count", 8); set_input(mod, "Spacing", 0.1); set_input(mod, "Material", mat)
print("input identifiers:", [(it.name, it.identifier) for it in ng.interface.items_tree if it.item_type == 'SOCKET'])
print("read back Count:", getattr(mod.properties.inputs, socket_id(ng, "Count")).value)
report(ob, "GN_boltrow_count8_realized_evaluated", evaluated=True)
applied = bpy.data.objects.new("SM_Hull_Applied", evaluated_mesh(ob)); bpy.context.scene.collection.objects.link(applied)
report(applied, "GN_boltrow_applied_mesh")
print("material slots on applied:", [m.name if m else None for m in applied.data.materials])
# without Realize Instances: what survives new_from_object?
ng.links.remove([l for l in ng.links if l.to_node == real][0]); link(ng, iop.outputs['Instances'], setm.inputs['Geometry'])
report(ob, "GN_boltrow_NO_realize_evaluated", evaluated=True)
dg = bpy.context.evaluated_depsgraph_get(); ev = ob.evaluated_get(dg)
print("instances in evaluated geometry (ev.data is mesh only):", ev.type, len(ev.data.vertices), "-> instances are dropped by new_from_object unless realized")

# ---- Group 2: scatter rivets on faces. Distribute Points on Faces -> Instance on Points (rotation from normal) -> Realize
ng2 = bpy.data.node_groups.new("GN_Scatter", 'GeometryNodeTree')
ng2.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
ng2.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
s = ng2.interface.new_socket("Density", in_out='INPUT', socket_type='NodeSocketFloat'); s.default_value = 20.0
s = ng2.interface.new_socket("Seed", in_out='INPUT', socket_type='NodeSocketInt'); s.default_value = 0
n = ng2.nodes; gi = n.new('NodeGroupInput'); go = n.new('NodeGroupOutput')
dist = n.new('GeometryNodeDistributePointsOnFaces'); dist.distribute_method = 'RANDOM'
print("Distribute inputs:", [i.name for i in dist.inputs], "outputs:", [o.name for o in dist.outputs])
ico = n.new('GeometryNodeMeshIcoSphere'); ico.inputs['Radius'].default_value = 0.02; ico.inputs['Subdivisions'].default_value = 1
iop = n.new('GeometryNodeInstanceOnPoints'); real = n.new('GeometryNodeRealizeInstances'); join = n.new('GeometryNodeJoinGeometry')
link(ng2, gi.outputs['Geometry'], dist.inputs['Mesh']); link(ng2, gi.outputs['Density'], dist.inputs['Density']); link(ng2, gi.outputs['Seed'], dist.inputs['Seed'])
link(ng2, dist.outputs['Points'], iop.inputs['Points']); link(ng2, dist.outputs['Rotation'], iop.inputs['Rotation'])
link(ng2, ico.outputs['Mesh'], iop.inputs['Instance']); link(ng2, iop.outputs['Instances'], real.inputs['Geometry'])
link(ng2, gi.outputs['Geometry'], join.inputs['Geometry']); link(ng2, real.outputs['Geometry'], join.inputs['Geometry'])
link(ng2, join.outputs['Geometry'], go.inputs['Geometry'])
bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0); ob2 = obj_from_bmesh(bm, "SM_Rivets")
mod2 = ob2.modifiers.new("Scatter", 'NODES'); mod2.node_group = ng2; set_input(mod2, "Density", 30.0); set_input(mod2, "Seed", 7)
report(ob2, "GN_scatter_density30_cube_6m2", evaluated=True)
# attribute-driven input (type='ATTRIBUTE')
inp = getattr(mod2.properties.inputs, socket_id(ng2, "Density"))
print("input item props:", [(p.identifier, getattr(inp, p.identifier)) for p in inp.bl_rna.properties if p.identifier != 'rna_type'])
# Random Value node identifiers (5.2 notes say these changed)
rv = n.new('FunctionNodeRandomValue'); rv.data_type = 'FLOAT'
print("RandomValue FLOAT inputs:", [(i.name, i.identifier, i.enabled) for i in rv.inputs], "outputs:", [(o.name, o.identifier, o.enabled) for o in rv.outputs])
cmp = n.new('FunctionNodeCompare'); print("Compare inputs:", [(i.name, i.identifier, i.enabled) for i in cmp.inputs])
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_out"); os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "t06.blend"))
print("DONE t06")
