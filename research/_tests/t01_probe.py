import bpy, bmesh, sys
print("VERSION", bpy.app.version, bpy.app.version_string, "python", sys.version.split()[0])
print("BACKGROUND", bpy.app.background)
# default scene content
print("OBJECTS", [o.name for o in bpy.data.objects])
# Mesh attributes
m = bpy.data.meshes.new("probe")
m.from_pydata([(0,0,0),(1,0,0),(1,1,0),(0,1,0)], [], [(0,1,2,3)])
print("validate", m.validate(verbose=True)); m.update()
print("has use_auto_smooth", hasattr(m, "use_auto_smooth"))
print("has auto_smooth_angle", hasattr(m, "auto_smooth_angle"))
print("has calc_normals_split", hasattr(m, "calc_normals_split"))
print("has free_normals_split", hasattr(m, "free_normals_split"))
print("has calc_normals", hasattr(m, "calc_normals"))
print("has set_sharp_from_angle", hasattr(m, "set_sharp_from_angle"))
print("has shade_smooth", hasattr(m, "shade_smooth"))
print("has shade_flat", hasattr(m, "shade_flat"))
print("has calc_loop_triangles", hasattr(m, "calc_loop_triangles"))
print("has normals_split_custom_set", hasattr(m, "normals_split_custom_set"))
print("has corner_normals", hasattr(m, "corner_normals"))
print("has vertex_normals", hasattr(m, "vertex_normals"))
print("has polygon_normals", hasattr(m, "polygon_normals"))
print("has use_mirror_topology", hasattr(m, "use_mirror_topology"))
print("has uv_layers", hasattr(m, "uv_layers"))
print("has vertex_colors", hasattr(m, "vertex_colors"))
print("has color_attributes", hasattr(m, "color_attributes"))
print("attributes after from_pydata", [(a.name, a.domain, a.data_type) for a in m.attributes])
print("poly use_smooth", [p.use_smooth for p in m.polygons])
m.shade_smooth()
print("attributes after shade_smooth", [(a.name, a.domain, a.data_type) for a in m.attributes])
m.set_sharp_from_angle(angle=0.5)
print("attributes after set_sharp_from_angle", [(a.name, a.domain, a.data_type) for a in m.attributes])
# Mesh attribute types
try:
    print("MeshPolygon has material_index", hasattr(m.polygons[0], "material_index"))
    print("MeshPolygon has use_smooth", hasattr(m.polygons[0], "use_smooth"))
except Exception as e: print("poly err", e)
# Render engines
print("ENGINES", [i.identifier for i in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items])
sc = bpy.context.scene
print("scene.render.engine default", sc.render.engine)
print("has scene.eevee", hasattr(sc, "eevee"))
print("eevee props", sorted([p.identifier for p in sc.eevee.bl_rna.properties if not p.identifier.startswith("rna")]))
print("cycles device", sc.cycles.device, "samples", sc.cycles.samples)
print("render.image_settings.file_format", sc.render.image_settings.file_format)
print("file formats", [i.identifier for i in bpy.types.ImageFormatSettings.bl_rna.properties['file_format'].enum_items])
print("color_depth", [i.identifier for i in bpy.types.ImageFormatSettings.bl_rna.properties['color_depth'].enum_items])
print("view_settings.view_transform", sc.view_settings.view_transform, "look", sc.view_settings.look)
print("view_transforms", [i.identifier for i in sc.view_settings.bl_rna.properties['view_transform'].enum_items])
print("display_device", sc.display_settings.display_device)
# Principled BSDF sockets
mat = bpy.data.materials.new("M"); mat.use_nodes = True
print("mat.use_nodes attr", hasattr(mat, "use_nodes"))
nt = mat.node_tree
print("default nodes", [(n.name, n.bl_idname) for n in nt.nodes])
bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
print("PRINCIPLED INPUTS", [s.name for s in bsdf.inputs])
print("PRINCIPLED OUTPUTS", [s.name for s in bsdf.outputs])
print("input identifiers", [s.identifier for s in bsdf.inputs])
# colorspaces
img = bpy.data.images.new("tex", 4, 4, alpha=True, float_buffer=False)
print("colorspace names", [i.identifier for i in img.colorspace_settings.bl_rna.properties['name'].enum_items])
print("default colorspace", img.colorspace_settings.name)
print("image props", [p.identifier for p in img.bl_rna.properties if 'file' in p.identifier or 'format' in p.identifier])
print("Image.save sig doc:", bpy.types.Image.save.__doc__)
print("Image.save_render sig doc:", bpy.types.Image.save_render.__doc__)
# context
print("has temp_override", hasattr(bpy.context, "temp_override"))
print("context.window", bpy.context.window, "screen", bpy.context.screen, "area", bpy.context.area)
print("wm windows", len(bpy.context.window_manager.windows))
# view layer / collection
print("collections", [c.name for c in bpy.data.collections], "scene coll", sc.collection.name)
# ops polls
cube = bpy.data.objects["Cube"] if "Cube" in bpy.data.objects else None
if cube:
    bpy.ops.object.select_all(action='DESELECT'); cube.select_set(True); bpy.context.view_layer.objects.active = cube
    print("shade_smooth poll", bpy.ops.object.shade_smooth.poll())
    print("shade_auto_smooth poll", bpy.ops.object.shade_auto_smooth.poll())
    r = bpy.ops.object.shade_auto_smooth(angle=0.523599)
    print("shade_auto_smooth result", r, [ (md.name, md.type) for md in cube.modifiers])
    print("has shade_smooth_by_angle op", hasattr(bpy.ops.object, "shade_smooth_by_angle"))
    print("mesh attrs after op", [(a.name, a.domain, a.data_type) for a in cube.data.attributes])
    print("modifier types", [i.identifier for i in bpy.types.ObjectModifiers.bl_rna.functions['new'].parameters['type'].enum_items])
