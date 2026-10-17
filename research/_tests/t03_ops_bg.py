import bpy, bmesh, math, os, sys, warnings, traceback
from mathutils import Vector, Matrix
warnings.simplefilter("ignore")
OUT = "/Users/Game/blender-3d-team/research/_tests/_out"; os.makedirs(OUT, exist_ok=True)
def sec(t): print("\n=== " + t)
def tryp(label, fn):
    try: r = fn(); print("OK  ", label, "->", r); return r
    except Exception as ex: print("FAIL", label, "->", type(ex).__name__, str(ex)[:200]); return None
sc = bpy.context.scene; vl = bpy.context.view_layer
cube = bpy.data.objects["Cube"]
def select_only(o):
    for ob in bpy.data.objects: ob.select_set(False)
    o.select_set(True); vl.objects.active = o
select_only(cube)
sec("GPU backend / prefs")
tryp("gpu_backend", lambda: bpy.context.preferences.system.gpu_backend)
tryp("gpu_backend enum", lambda: [i.identifier for i in bpy.context.preferences.system.bl_rna.properties['gpu_backend'].enum_items])
tryp("cycles devices", lambda: [i.identifier for i in sc.cycles.bl_rna.properties['device'].enum_items])
sec("shade ops in background")
tryp("has shade_smooth_by_angle", lambda: hasattr(bpy.ops.object, "shade_smooth_by_angle"))
tryp("shade_smooth poll", lambda: bpy.ops.object.shade_smooth.poll())
tryp("shade_smooth(keep_sharp_edges=True)", lambda: bpy.ops.object.shade_smooth(keep_sharp_edges=True))
tryp("shade_smooth rna props", lambda: [p.identifier for p in bpy.ops.object.shade_smooth.get_rna_type().properties])
tryp("shade_auto_smooth poll", lambda: bpy.ops.object.shade_auto_smooth.poll())
tryp("shade_auto_smooth()", lambda: bpy.ops.object.shade_auto_smooth(angle=math.radians(30)))
tryp("cube modifiers", lambda: [(m.name, m.type, getattr(m,'node_group',None) and m.node_group.name) for m in cube.modifiers])
gm = cube.modifiers[-1] if cube.modifiers else None
if gm and gm.type == 'NODES':
    tryp("gn properties.inputs type", lambda: (type(gm.properties.inputs).__name__, list(gm.properties.inputs.keys()) if hasattr(gm.properties.inputs,'keys') else dir(gm.properties.inputs)))
    tryp("gn inputs rna props", lambda: [p.identifier for p in gm.properties.inputs.bl_rna.properties])
    for k in ("Socket_1","Input_1","Angle"):
        tryp(f"gn inputs['{k}']", lambda k=k: (type(gm.properties.inputs[k]).__name__, [a for a in dir(gm.properties.inputs[k]) if not a.startswith('_')]))
    tryp("gn node_group interface", lambda: [(s.name, s.identifier, s.in_out) for s in gm.node_group.interface.items_tree if s.item_type=='SOCKET'])
    tryp("gn inputs iteration", lambda: [(i.identifier if hasattr(i,'identifier') else str(i), getattr(i,'value',None)) for i in gm.properties.inputs])
    tryp("gn inputs['Socket_1'].value", lambda: gm.properties.inputs["Socket_1"].value)
    tryp("gn id_data", lambda: gm.properties.inputs.id_data)
    tryp("gn getattr Socket_1", lambda: getattr(gm.properties.inputs, "Socket_1"))
    tryp("gn inputs get('Socket_1')", lambda: gm.properties.inputs.get("Socket_1"))
    tryp("gn id_properties_ensure", lambda: dict(gm.properties.inputs.id_properties_ensure().to_dict()) if hasattr(gm.properties.inputs,'id_properties_ensure') else None)
    tryp("gn inputs.items()", lambda: [(k, type(v).__name__, getattr(v,'value','?')) for k,v in gm.properties.inputs.items()])
    tryp("gn inputs['Socket_1'] to_dict", lambda: gm.properties.inputs["Socket_1"].to_dict())
    tryp("gn inputs['Socket_1']['value']", lambda: gm.properties.inputs["Socket_1"]["value"])
    tryp("set inputs['Socket_1']['value']=0.3", lambda: gm.properties.inputs["Socket_1"].__setitem__("value", 0.3))
    tryp("gn inputs['Socket_1']['value'] after", lambda: gm.properties.inputs["Socket_1"]["value"])
    tryp("mesh attrs after op", lambda: [(a.name, a.domain, a.data_type) for a in cube.data.attributes])
sec("modifier_apply in background")
bev = cube.modifiers.new("Bevel", 'BEVEL'); bev.width = 0.05; bev.segments = 2
tryp("modifier_apply poll", lambda: bpy.ops.object.modifier_apply.poll())
tryp("modifier_apply(Bevel)", lambda: bpy.ops.object.modifier_apply(modifier="Bevel"))
tryp("verts after", lambda: len(cube.data.vertices))
sec("evaluated mesh copy (no ops)")
sub = cube.modifiers.new("Sub", 'SUBSURF'); sub.levels = 1
dg = tryp("depsgraph", lambda: bpy.context.evaluated_depsgraph_get())
ev = cube.evaluated_get(dg)
tryp("eval verts", lambda: len(ev.data.vertices))
newme = tryp("new_from_object", lambda: bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg))
tryp("new mesh verts", lambda: len(newme.vertices))
tryp("to_mesh", lambda: len(ev.to_mesh().vertices)); ev.to_mesh_clear()
cube.modifiers.remove(sub)
sec("origin / transforms without ops")
cube.location = (1,2,3); cube.rotation_euler=(0,0,math.radians(45)); cube.scale=(2,2,2)
vl.update()
mw = cube.matrix_world.copy()
tryp("apply transform via mesh.transform", lambda: (cube.data.transform(mw), setattr(cube,'matrix_world', Matrix.Identity(4)), round(cube.dimensions.x,3)))
tryp("origin to geometry center", lambda: (lambda c: (cube.data.transform(Matrix.Translation(-c)), setattr(cube, 'location', cube.matrix_world @ c), cube.location.copy()))(sum((v.co for v in cube.data.vertices), Vector())/len(cube.data.vertices)))
tryp("origin_set poll", lambda: bpy.ops.object.origin_set.poll())
tryp("transform_apply poll", lambda: bpy.ops.object.transform_apply.poll())
sec("edit mode + UV ops in background")
tryp("mode_set EDIT", lambda: bpy.ops.object.mode_set(mode='EDIT'))
tryp("mesh.select_all", lambda: bpy.ops.mesh.select_all(action='SELECT'))
tryp("smart_project poll", lambda: bpy.ops.uv.smart_project.poll())
tryp("smart_project()", lambda: bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.02))
tryp("pack_islands poll", lambda: bpy.ops.uv.pack_islands.poll())
tryp("pack_islands()", lambda: bpy.ops.uv.pack_islands(margin=0.02, rotate=True))
tryp("uv.unwrap poll", lambda: bpy.ops.uv.unwrap.poll())
tryp("uv.unwrap()", lambda: bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.02))
tryp("uv.unwrap rna props", lambda: [p.identifier for p in bpy.ops.uv.unwrap.get_rna_type().properties])
tryp("mesh.mark_seam", lambda: bpy.ops.mesh.mark_seam(clear=False))
# temp_override with a VIEW_3D area
win = bpy.context.window; scr = win.screen
areas = [a.type for a in scr.areas]
print("screen areas:", areas)
v3d = next((a for a in scr.areas if a.type=='VIEW_3D'), None)
if v3d:
    reg = next(r for r in v3d.regions if r.type=='WINDOW')
    def ov():
        with bpy.context.temp_override(window=win, area=v3d, region=reg):
            return bpy.ops.uv.smart_project()
    tryp("smart_project under temp_override VIEW_3D", ov)
tryp("mode_set OBJECT", lambda: bpy.ops.object.mode_set(mode='OBJECT'))
tryp("uv layer data", lambda: (cube.data.uv_layers.active.name, tuple(round(x,3) for x in cube.data.uv_layers.active.data[0].uv), tuple(round(x,3) for x in cube.data.uv_layers.active.uv[0].vector)))
tryp("uv pin before ensure", lambda: len(cube.data.uv_layers.active.pin))
tryp("uv pin_ensure", lambda: (cube.data.uv_layers.active.pin_ensure(), len(cube.data.uv_layers.active.pin)))
sec("bmesh ops")
def bm_test():
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    r = bmesh.ops.bevel(bm, geom=bm.verts[:]+bm.edges[:]+bm.faces[:], offset=0.1, segments=2, affect='EDGES', profile=0.5, clamp_overlap=True)
    print("   bevel keys", list(r.keys()))
    r = bmesh.ops.inset_region(bm, faces=bm.faces[:], thickness=0.05, depth=0.0, use_even_offset=True)
    print("   inset keys", list(r.keys()))
    top = [f for f in bm.faces if f.normal.z > 0.9]
    r = bmesh.ops.extrude_face_region(bm, geom=top)
    verts = [e for e in r["geom"] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=verts, vec=(0,0,0.5))
    print("   extrude keys", list(r.keys()))
    r = bmesh.ops.subdivide_edges(bm, edges=bm.edges[:5], cuts=1, use_grid_fill=True)
    print("   subdivide keys", list(r.keys()))
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1), verts=bm.verts[:], edges=bm.edges[:], delimit={'NORMAL'})
    r = bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY')
    print("   triangulate keys", list(r.keys()))
    me = bpy.data.meshes.new("bm_out"); bm.to_mesh(me); bm.free(); me.update()
    ob = bpy.data.objects.new("BMObj", me); sc.collection.objects.link(ob)
    return (len(me.vertices), len(me.polygons))
tryp("bmesh pipeline", bm_test)
sec("measurement")
def measure(ob):
    me = ob.data
    tris = sum(len(p.vertices)-2 for p in me.polygons)
    me.calc_loop_triangles(); tris2 = len(me.loop_triangles)
    dims = tuple(round(d,3) for d in ob.dimensions)
    bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    bm = bmesh.new(); bm.from_mesh(me)
    nm_e = sum(1 for e in bm.edges if not e.is_manifold); nm_v = sum(1 for v in bm.verts if not v.is_manifold)
    loose_v = sum(1 for v in bm.verts if not v.link_edges); loose_e = sum(1 for e in bm.edges if not e.link_faces)
    bm.free()
    return dict(tris=tris, tris2=tris2, dims=dims, nonmanifold_edges=nm_e, nonmanifold_verts=nm_v, loose_v=loose_v, loose_e=loose_e, bbox_min=tuple(round(min(v[i] for v in bb),3) for i in range(3)))
tryp("measure cube", lambda: measure(cube))
tryp("measure BMObj", lambda: measure(bpy.data.objects["BMObj"]))
sec("Principled defaults & socket errors")
mat = bpy.data.materials.new("PBR"); nt = mat.node_tree; bsdf = nt.nodes["Principled BSDF"]
tryp("defaults", lambda: {k: (tuple(round(x,3) for x in bsdf.inputs[k].default_value) if hasattr(bsdf.inputs[k].default_value,'__len__') else round(bsdf.inputs[k].default_value,3)) for k in ("Base Color","Metallic","Roughness","IOR","Alpha","Specular IOR Level","Emission Color","Emission Strength","Coat Weight","Transmission Weight")})
tryp("inputs['Specular'] (old name)", lambda: bsdf.inputs['Specular'])
tryp("inputs['Emission'] (old name)", lambda: bsdf.inputs['Emission'])
tryp("material blend", lambda: (mat.surface_render_method, [i.identifier for i in mat.bl_rna.properties['surface_render_method'].enum_items], hasattr(mat,'blend_method'), hasattr(mat,'shadow_method')))
sec("image texture + colorspace + save")
tex = nt.nodes.new("ShaderNodeTexImage")
img = bpy.data.images.new("albedo", 64, 64, alpha=True, float_buffer=False)
import numpy as np
px = np.zeros((64*64*4,), dtype=np.float32); px[0::4]=0.8; px[1::4]=0.2; px[2::4]=0.1; px[3::4]=1.0
img.pixels.foreach_set(px); tex.image = img
nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
nrm = bpy.data.images.new("normal", 64, 64, alpha=False, float_buffer=False); nrm.colorspace_settings.name = 'Non-Color'
tryp("nrm colorspace", lambda: nrm.colorspace_settings.name)
tryp("Non-Color alias 'Linear'", lambda: setattr(nrm.colorspace_settings, 'name', 'Linear'))
tryp("img.file_format enum", lambda: [i.identifier for i in img.bl_rna.properties['file_format'].enum_items])
img.filepath_raw = os.path.join(OUT, "albedo.png"); img.file_format = 'PNG'
tryp("img.save()", lambda: (img.save(), os.path.getsize(img.filepath_raw)))
tryp("img.save(filepath=)", lambda: (img.save(filepath=os.path.join(OUT,"albedo2.png")), os.path.exists(os.path.join(OUT,"albedo2.png"))))
himg = bpy.data.images.new("height", 32, 32, alpha=False, float_buffer=True, is_data=True)
tryp("himg is_float", lambda: (himg.is_float, himg.depth, himg.colorspace_settings.name))
himg.filepath_raw = os.path.join(OUT, "height.exr"); himg.file_format = 'OPEN_EXR'
tryp("himg.save() exr", lambda: (himg.save(), os.path.getsize(himg.filepath_raw)))
tryp("exr depth check", lambda: (lambda i2: (i2.depth, i2.is_float))(bpy.data.images.load(himg.filepath_raw)))
# 16-bit PNG via save_render
sc.render.image_settings.file_format='PNG'; sc.render.image_settings.color_depth='16'; sc.render.image_settings.color_mode='RGBA'
tryp("save_render 16bit png", lambda: (himg.save_render(os.path.join(OUT,"height16.png"), scene=sc), os.path.getsize(os.path.join(OUT,"height16.png"))))
tryp("load height16 depth", lambda: bpy.data.images.load(os.path.join(OUT,"height16.png")).depth)
sc.render.image_settings.color_depth='8'
sec("camera fit + render")
cam = bpy.data.objects["Camera"]
coords = [cube.matrix_world @ Vector(c) for c in cube.bound_box]
flat = [c for v in coords for c in v]
tryp("camera_fit_coords", lambda: cam.camera_fit_coords(dg, flat))
def fit():
    loc, scale = cam.camera_fit_coords(bpy.context.evaluated_depsgraph_get(), flat)
    cam.location = loc; return tuple(round(x,2) for x in loc)
tryp("apply fit", fit)
sc.render.resolution_x = 64; sc.render.resolution_y = 64; sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG'
for eng, setup in (('BLENDER_WORKBENCH', lambda: None), ('BLENDER_EEVEE', lambda: setattr(sc.eevee,'taa_render_samples',4)), ('CYCLES', lambda: (setattr(sc.cycles,'samples',4), setattr(sc.cycles,'device','CPU')))):
    sc.render.engine = eng; setup()
    sc.render.filepath = os.path.join(OUT, f"render_{eng}.png")
    tryp(f"render {eng}", lambda: (bpy.ops.render.render(write_still=True), os.path.exists(sc.render.filepath) and os.path.getsize(sc.render.filepath)))
sec("world HDRI nodes")
w = bpy.data.worlds.new("Studio"); sc.world = w
tryp("world nodes", lambda: [(n.name, n.bl_idname) for n in w.node_tree.nodes])
env = w.node_tree.nodes.new("ShaderNodeTexEnvironment")
bg = w.node_tree.nodes.get("Background") or next(n for n in w.node_tree.nodes if n.bl_idname=='ShaderNodeBackground')
w.node_tree.links.new(env.outputs["Color"], bg.inputs["Color"]); bg.inputs["Strength"].default_value = 1.5
tryp("world ok", lambda: len(w.node_tree.links))
sec("turntable keyframes")
cube.rotation_euler = (0,0,0); cube.keyframe_insert("rotation_euler", index=2, frame=1)
cube.rotation_euler = (0,0,math.radians(360)); cube.keyframe_insert("rotation_euler", index=2, frame=97)
def lin():
    ad = cube.animation_data; act = ad.action
    fcs = [fc for fc in act.fcurves] if hasattr(act,'fcurves') else None
    return (act.name, ad.action_slot.name if ad.action_slot else None, len(fcs) if fcs else None)
tryp("action/slot", lin)
def lin2():
    for fc in cube.animation_data.action.fcurves:
        for kp in fc.keyframe_points: kp.interpolation='LINEAR'
    return "linear set via action.fcurves (legacy, deprecated?)"
tryp("set LINEAR via action.fcurves", lin2)
def lin3():
    from bpy_extras import anim_utils
    cb = anim_utils.action_get_channelbag_for_slot(cube.animation_data.action, cube.animation_data.action_slot)
    return [fc.data_path for fc in cb.fcurves]
tryp("channelbag fcurves", lin3)
sec("exports")
select_only(cube)
tryp("gltf GLB", lambda: (bpy.ops.export_scene.gltf(filepath=os.path.join(OUT,"cube.glb"), export_format='GLB', use_selection=True, export_apply=True, export_yup=True, export_texcoords=True, export_normals=True, export_tangents=False, export_materials='EXPORT', export_image_format='AUTO'), os.path.getsize(os.path.join(OUT,"cube.glb"))))
tryp("gltf SEPARATE", lambda: (bpy.ops.export_scene.gltf(filepath=os.path.join(OUT,"cube.gltf"), export_format='GLTF_SEPARATE', use_selection=True), os.path.exists(os.path.join(OUT,"cube.gltf"))))
tryp("gltf EMBEDDED (removed?)", lambda: bpy.ops.export_scene.gltf(filepath=os.path.join(OUT,"cube_e.gltf"), export_format='GLTF_EMBEDDED', use_selection=True))
tryp("gltf export_format enum", lambda: [i.identifier for i in bpy.ops.export_scene.gltf.get_rna_type().properties['export_format'].enum_items])
tryp("fbx", lambda: (bpy.ops.export_scene.fbx(filepath=os.path.join(OUT,"cube.fbx"), use_selection=True, apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y', bake_space_transform=True, mesh_smooth_type='FACE', use_mesh_modifiers=True, path_mode='COPY', embed_textures=True, add_leaf_bones=False, object_types={'MESH','ARMATURE','EMPTY'}), os.path.getsize(os.path.join(OUT,"cube.fbx"))))
tryp("obj", lambda: (bpy.ops.wm.obj_export(filepath=os.path.join(OUT,"cube.obj"), export_selected_objects=True, apply_modifiers=True, export_uv=True, export_normals=True, export_materials=True, export_triangulated_mesh=False, forward_axis='NEGATIVE_Z', up_axis='Y', path_mode='COPY'), os.path.getsize(os.path.join(OUT,"cube.obj"))))
tryp("obj forward_axis enum", lambda: [i.identifier for i in bpy.ops.wm.obj_export.get_rna_type().properties['forward_axis'].enum_items])
tryp("usd", lambda: (bpy.ops.wm.usd_export(filepath=os.path.join(OUT,"cube.usdc"), selected_objects_only=True, export_materials=True, export_textures_mode='NEW', generate_preview_surface=True, export_uvmaps=True, export_normals=True, convert_orientation=False, evaluation_mode='RENDER'), os.path.getsize(os.path.join(OUT,"cube.usdc"))))
tryp("usd export_textures_mode enum", lambda: [i.identifier for i in bpy.ops.wm.usd_export.get_rna_type().properties['export_textures_mode'].enum_items])
tryp("usd old export_textures kw", lambda: bpy.ops.wm.usd_export(filepath=os.path.join(OUT,"x.usdc"), export_textures=True))
tryp("usd_export rna defaults", lambda: {k: getattr(bpy.ops.wm.usd_export.get_rna_type().properties[k],'default',None) for k in ('convert_orientation','export_global_forward_selection','export_global_up_selection','meters_per_unit','convert_scene_units','xform_op_mode','export_textures_mode','evaluation_mode','triangulate_meshes','relative_paths','use_instancing','export_subdivision')})
tryp("stl", lambda: (bpy.ops.wm.stl_export(filepath=os.path.join(OUT,"cube.stl"), export_selected_objects=True, apply_modifiers=True), os.path.getsize(os.path.join(OUT,"cube.stl"))))
print("\nOUT files:", sorted(os.listdir(OUT)))
