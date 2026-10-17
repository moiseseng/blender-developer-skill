import bpy, bmesh, math, sys, warnings
warnings.simplefilter("always")
sc = bpy.context.scene
# --- render engines: try setting directly
for e in ['CYCLES','BLENDER_WORKBENCH','BLENDER_EEVEE','BLENDER_EEVEE_NEXT']:
    try:
        sc.render.engine = e; print("ENGINE OK", e)
    except Exception as ex: print("ENGINE FAIL", e, "->", type(ex).__name__, str(ex)[:120])
print("engine enum static", [i.identifier for i in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items_static])
sc.render.engine = 'BLENDER_EEVEE'
# --- ImageFormatSettings media_type
ifs = sc.render.image_settings
print("has media_type", hasattr(ifs, "media_type"))
if hasattr(ifs, "media_type"):
    print("media_type enum", [i.identifier for i in ifs.bl_rna.properties['media_type'].enum_items], "current", ifs.media_type)
try:
    ifs.file_format = 'FFMPEG'; print("set FFMPEG without media_type OK ->", ifs.file_format)
except Exception as ex: print("set FFMPEG without media_type FAIL", type(ex).__name__, str(ex)[:160])
try:
    ifs.media_type = 'VIDEO'; ifs.file_format = 'FFMPEG'; print("after media_type=VIDEO file_format", ifs.file_format)
    ifs.media_type = 'IMAGE'; ifs.file_format = 'PNG'; print("back to IMAGE/PNG", ifs.file_format)
except Exception as ex: print("media_type FAIL", type(ex).__name__, str(ex)[:160])
try:
    ifs.file_format = 'OPEN_EXR'; ifs.color_depth = '32'; print("EXR 32 ok, color_mode", ifs.color_mode)
    ifs.file_format = 'PNG'; ifs.color_depth = '16'; print("PNG 16 ok")
    ifs.color_depth='8'
except Exception as ex: print("depth FAIL", ex)
# --- Image save signature
f = bpy.types.Image.bl_rna.functions
print("Image funcs", [fn.identifier for fn in f])
for name in ("save", "save_render", "scale", "pack", "reload", "filepath_from_user"):
    if name in f:
        print(name, "params:", [(p.identifier, p.type, getattr(p,'default',None)) for p in f[name].parameters])
# --- Material.use_nodes behavior
with warnings.catch_warnings(record=True) as w:
    m2 = bpy.data.materials.new("NoNodesSet")
    print("new material node_tree:", m2.node_tree, "use_nodes:", m2.use_nodes)
    print("warnings:", [str(x.message) for x in w])
print("Material props with 'node'", [p.identifier for p in bpy.types.Material.bl_rna.properties if 'node' in p.identifier])
print("Material.use_nodes desc:", bpy.types.Material.bl_rna.properties['use_nodes'].description)
# does Material have a way to create node tree? 
print("Material funcs", [fn.identifier for fn in bpy.types.Material.bl_rna.functions])
# World
w = bpy.data.worlds.new("W")
print("world node_tree", w.node_tree, "use_nodes attr", hasattr(w,'use_nodes'))
# --- exporters availability
for op in ("usd_export","obj_export","ply_export","stl_export","alembic_export","collada_export","usd_import","obj_import"):
    ok = hasattr(bpy.ops.wm, op)
    print("bpy.ops.wm."+op, ok)
    if ok:
        try:
            props = bpy.ops.wm.__getattr__(op).get_rna_type().properties
            print("   params:", sorted(p.identifier for p in props if p.identifier not in ('rna_type',)))
        except Exception as ex: print("   err", ex)
print("export_scene ops", [o for o in dir(bpy.ops.export_scene) if not o.startswith('_')])
print("export_mesh ops", [o for o in dir(bpy.ops.export_mesh) if not o.startswith('_')] if hasattr(bpy.ops,'export_mesh') else "no export_mesh")
print("import_scene ops", [o for o in dir(bpy.ops.import_scene) if not o.startswith('_')])
# --- boolean solver enum
cube = bpy.data.objects["Cube"]
bm = cube.modifiers.new("Bool", 'BOOLEAN')
print("boolean solver enum", [i.identifier for i in bm.bl_rna.properties['solver'].enum_items], "default", bm.solver)
cube.modifiers.remove(bm)
# --- GN modifier property access (5.2 change)
try:
    ng = bpy.data.node_groups.new("GN", 'GeometryNodeTree')
    ng.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    s = ng.interface.new_socket("Scale", in_out='INPUT', socket_type='NodeSocketFloat')
    print("socket identifier", s.identifier)
    gi = ng.nodes.new("NodeGroupInput"); go = ng.nodes.new("NodeGroupOutput")
    ng.links.new(gi.outputs[0], go.inputs[0])
    gm = cube.modifiers.new("GN", 'NODES'); gm.node_group = ng
    print("gm has properties attr", hasattr(gm, "properties"))
    try:
        print("dict access gm[s.identifier] ->", gm[s.identifier])
    except Exception as ex: print("dict access FAIL", type(ex).__name__, str(ex)[:120])
    try:
        print("gm.keys()", list(gm.keys()))
    except Exception as ex: print("keys FAIL", ex)
    if hasattr(gm, "properties"):
        print("properties type", type(gm.properties), [a for a in dir(gm.properties) if not a.startswith('_')][:30])
        try:
            inp = gm.properties.inputs[s.identifier]
            print("inputs[...] ->", inp, "value", inp.value, "type", inp.type)
            inp.value = 2.0; print("set value ->", gm.properties.inputs[s.identifier].value)
        except Exception as ex: print("properties.inputs FAIL", type(ex).__name__, str(ex)[:160])
    cube.modifiers.remove(gm)
except Exception as ex: print("GN block err", type(ex).__name__, ex)
# --- view transform
for vt in ['Standard','AgX','Filmic','Khronos PBR Neutral','False Color','Raw']:
    try: sc.view_settings.view_transform = vt; print("view_transform OK", vt)
    except Exception as ex: print("view_transform FAIL", vt, str(ex)[:80])
sc.view_settings.view_transform='AgX'
print("looks for AgX", [i.identifier for i in sc.view_settings.bl_rna.properties['look'].enum_items])
# --- mathutils buffer
import mathutils, numpy as np
v = mathutils.Vector((1,2,3)); print("numpy dtype of Vector", np.asarray(v).dtype, "v[::2]", list(v[::2]))
# --- modifier types
print("MODIFIER TYPES", [i.identifier for i in bpy.types.ObjectModifiers.bl_rna.functions['new'].parameters['type'].enum_items])
# --- color attributes / uv layers API
me = cube.data
uv = me.uv_layers.new(name="UVMap2"); print("uv layers", [u.name for u in me.uv_layers], "active", me.uv_layers.active.name)
print("uv layer attrs", [p.identifier for p in uv.bl_rna.properties])
print("MeshUVLoopLayer funcs", [fn.identifier for fn in uv.bl_rna.functions])
ca = me.color_attributes.new("Col", 'BYTE_COLOR', 'CORNER'); print("color attrs", [(c.name,c.data_type,c.domain) for c in me.color_attributes])
print("attr data_types", [i.identifier for i in bpy.types.AttributeGroupMesh.bl_rna.functions['new'].parameters['type'].enum_items])
print("attr domains", [i.identifier for i in bpy.types.AttributeGroupMesh.bl_rna.functions['new'].parameters['domain'].enum_items])
# --- bpy.app
print("bpy.app attrs", [a for a in dir(bpy.app) if not a.startswith('_')])
print("version_file", bpy.app.version_file, "version_cycle", bpy.app.version_cycle)
# --- Context in background
print("ctx window", bpy.context.window, "screen", bpy.context.screen, "area", bpy.context.area, "region", bpy.context.region)
print("windows", [w for w in bpy.context.window_manager.windows])
print("mode", bpy.context.mode, "active", bpy.context.active_object, "view_layer", bpy.context.view_layer.name)
