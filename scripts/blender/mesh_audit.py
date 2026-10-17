# SPDX-License-Identifier: MIT
"""
mesh_audit.py - technical QA audit for mesh objects (Blender 4.2+ / 5.x).

Checks geometry, transforms, pivot, UVs, materials, naming and budgets, and
returns a JSON-serialisable report with issues graded blocker / major / minor.

CLI (headless):
    blender -b scene.blend --python mesh_audit.py -- [--objects A,B] [--collection Name]
        [--asset-class small_prop] [--max-tris N] [--max-texture N] [--max-materials N]
        [--pivot bottom_center|center|any] [--name-regex RE] [--texture-size N]
        [--json out.json] [--md out.md]

MCP (execute_blender_code), after loading the module with scripts/blender/_load.py:
    result = mesh_audit.audit(objects=["SM_Crate_A"], asset_class="small_prop")

The budgets below are defaults only. references/budgets.md is the source of truth and
the asset brief overrides them per asset.
"""

import json
import math
import os
import re
import sys

import bpy
import bmesh
from mathutils import Vector, kdtree, geometry

# --------------------------------------------------------------------------- budgets

CLASS_BUDGETS = {
    #  class          max_tris  max_texture  max_materials  allow_ngons  allow_open
    "placeholder": dict(max_tris=500, max_texture=256, max_materials=1, allow_ngons=True, allow_open=True),
    "small_prop": dict(max_tris=1500, max_texture=1024, max_materials=1, allow_ngons=False, allow_open=False),
    "large_prop": dict(max_tris=6000, max_texture=2048, max_materials=2, allow_ngons=False, allow_open=False),
    "modular_piece": dict(max_tris=3000, max_texture=2048, max_materials=2, allow_ngons=False, allow_open=True),
    "character": dict(max_tris=30000, max_texture=2048, max_materials=4, allow_ngons=False, allow_open=False),
    "vehicle": dict(max_tris=40000, max_texture=4096, max_materials=4, allow_ngons=False, allow_open=False),
    "building": dict(max_tris=20000, max_texture=2048, max_materials=4, allow_ngons=False, allow_open=True),
    "hero": dict(max_tris=100000, max_texture=4096, max_materials=6, allow_ngons=False, allow_open=False),
    "cinematic": dict(max_tris=10**9, max_texture=8192, max_materials=99, allow_ngons=True, allow_open=True),
}

DEFAULT_NAME_REGEX = r"^(SM|SK|SMP|BLK)_[A-Z][A-Za-z0-9]*(_[A-Za-z0-9]+)*$"

# --------------------------------------------------------------------------- helpers


def _tri_count(mesh):
    return sum(max(len(p.vertices) - 2, 0) for p in mesh.polygons)


def _evaluated_mesh(obj, depsgraph):
    """Mesh with the modifier stack applied (what an exporter with apply=True ships)."""
    eval_obj = obj.evaluated_get(depsgraph)
    return eval_obj.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph), eval_obj


def _issue(issues, severity, code, message, obj_name=None):
    issues.append({"severity": severity, "code": code, "object": obj_name, "message": message})


def _bbox_local(mesh):
    xs = [v.co.x for v in mesh.vertices]
    ys = [v.co.y for v in mesh.vertices]
    zs = [v.co.z for v in mesh.vertices]
    if not xs:
        return None
    return (Vector((min(xs), min(ys), min(zs))), Vector((max(xs), max(ys), max(zs))))


def _geometry_checks(bm, budget, dup_distance=1e-5):
    """Topology defects on a bmesh. Boundary edges are reported apart from true non-manifold edges."""
    boundary_edges = 0
    nonmanifold_edges = 0  # > 2 faces
    wire_edges = 0  # 0 faces
    inconsistent_normal_edges = 0
    zero_length_edges = 0
    for e in bm.edges:
        n = len(e.link_faces)
        if n == 0:
            wire_edges += 1
        elif n == 1:
            boundary_edges += 1
        elif n > 2:
            nonmanifold_edges += 1
        elif n == 2:
            l1, l2 = e.link_loops[0], e.link_loops[1]
            # Consistent winding traverses a shared edge in opposite directions.
            if l1.vert == l2.vert:
                inconsistent_normal_edges += 1
        if e.calc_length() < 1e-7:
            zero_length_edges += 1

    loose_verts = sum(1 for v in bm.verts if not v.link_edges)
    ngons = sum(1 for f in bm.faces if len(f.verts) > 4)
    tris = sum(1 for f in bm.faces if len(f.verts) == 3)
    quads = sum(1 for f in bm.faces if len(f.verts) == 4)
    zero_area_faces = sum(1 for f in bm.faces if f.calc_area() < 1e-10)

    # Duplicate vertices (closer than dup_distance) via KD tree.
    duplicates = 0
    if len(bm.verts) > 1:
        kd = kdtree.KDTree(len(bm.verts))
        for i, v in enumerate(bm.verts):
            kd.insert(v.co, i)
        kd.balance()
        seen = set()
        for i, v in enumerate(bm.verts):
            if i in seen:
                continue
            group = [idx for (_co, idx, _d) in kd.find_range(v.co, dup_distance) if idx != i]
            if group:
                duplicates += len(group)
                seen.update(group)
                seen.add(i)

    # Whole-mesh inward normals heuristic: average of dot(normal, center-to-face) over faces.
    inward = None
    if bm.faces:
        center = sum((v.co for v in bm.verts), Vector()) / len(bm.verts)
        score = 0.0
        for f in bm.faces:
            d = f.calc_center_median() - center
            if d.length > 1e-9:
                score += f.normal.dot(d.normalized())
        inward = score < 0

    # Poles: verts with 5+ edges (ok in moderation), 6+ flagged.
    high_poles = sum(1 for v in bm.verts if len(v.link_edges) >= 6)

    return dict(
        boundary_edges=boundary_edges,
        nonmanifold_edges=nonmanifold_edges,
        wire_edges=wire_edges,
        loose_verts=loose_verts,
        inconsistent_normal_edges=inconsistent_normal_edges,
        zero_length_edges=zero_length_edges,
        zero_area_faces=zero_area_faces,
        duplicate_verts=duplicates,
        ngons=ngons,
        tris_faces=tris,
        quads=quads,
        quad_ratio=round(quads / len(bm.faces), 3) if bm.faces else 0.0,
        normals_mostly_inward=inward,
        high_valence_poles=high_poles,
    )


def _uv_checks(bm, mesh, matrix_world, texture_size, grid=128):
    """Coverage, bounds, overlap (grid rasterisation) and texel density (px per metre)."""
    uv_layer = bm.loops.layers.uv.active
    report = dict(has_uv=uv_layer is not None, uv_layers=len(mesh.uv_layers))
    if uv_layer is None:
        return report

    scale = matrix_world.to_scale()
    uv_area_total = 0.0
    mesh_area_total = 0.0
    out_of_bounds = 0
    flipped = 0
    per_face_td = []
    cells = {}
    for f in bm.faces:
        loops = f.loops
        uvs = [l[uv_layer].uv.copy() for l in loops]
        cos = [matrix_world @ l.vert.co for l in loops]
        n = len(uvs)
        signed = 0.5 * sum(uvs[i].x * uvs[(i + 1) % n].y - uvs[(i + 1) % n].x * uvs[i].y for i in range(n))
        if signed < -1e-12:
            flipped += 1
        if any(u.x < -1e-4 or u.x > 1 + 1e-4 or u.y < -1e-4 or u.y > 1 + 1e-4 for u in uvs):
            out_of_bounds += 1
        uv_area = 0.0
        area3d = 0.0
        for i in range(1, len(uvs) - 1):
            uv_area += geometry.area_tri(uvs[0], uvs[i], uvs[i + 1])
            area3d += geometry.area_tri(cos[0], cos[i], cos[i + 1])
            # rasterise triangle on a grid to detect overlap
            tri = (uvs[0], uvs[i], uvs[i + 1])
            xs = [p.x for p in tri]
            ys = [p.y for p in tri]
            x0, x1 = max(int(min(xs) * grid), 0), min(int(max(xs) * grid) + 1, grid)
            y0, y1 = max(int(min(ys) * grid), 0), min(int(max(ys) * grid) + 1, grid)
            for gx in range(x0, x1):
                for gy in range(y0, y1):
                    p = Vector(((gx + 0.5) / grid, (gy + 0.5) / grid))
                    if geometry.intersect_point_tri_2d(p, *tri):
                        cells[(gx, gy)] = cells.get((gx, gy), 0) + 1
        uv_area_total += uv_area
        mesh_area_total += area3d
        if area3d > 1e-12 and uv_area > 1e-12:
            per_face_td.append(texture_size * math.sqrt(uv_area / area3d))

    covered = len(cells)
    overlapped = sum(1 for c in cells.values() if c > 1)
    td_mean = sum(per_face_td) / len(per_face_td) if per_face_td else 0.0
    td_std = math.sqrt(sum((t - td_mean) ** 2 for t in per_face_td) / len(per_face_td)) if per_face_td else 0.0
    report.update(
        uv_coverage=round(covered / (grid * grid), 3),
        uv_overlap_fraction=round(overlapped / covered, 3) if covered else 0.0,
        uv_faces_out_of_bounds=out_of_bounds,
        uv_flipped_faces=flipped,
        texel_density_px_per_m=round(td_mean, 1),
        texel_density_min=round(min(per_face_td), 1) if per_face_td else 0.0,
        texel_density_max=round(max(per_face_td), 1) if per_face_td else 0.0,
        texel_density_cv=round(td_std / td_mean, 3) if td_mean else 0.0,
        texture_size_assumed=texture_size,
        uv_area_total=round(uv_area_total, 4),
        mesh_area_m2=round(mesh_area_total, 4),
    )
    return report


_NONCOLOR_SOCKETS = {"Roughness", "Metallic", "Alpha", "Specular IOR Level", "Normal", "Height", "Color"}


def _image_targets(node_tree, img_node):
    """Which Principled/Normal Map sockets an image node ultimately feeds (one hop through Normal Map / Separate)."""
    targets = set()
    for out in img_node.outputs:
        for link in out.links:
            to = link.to_node
            if to.type == "BSDF_PRINCIPLED":
                targets.add(link.to_socket.name)
            elif to.type == "NORMAL_MAP":
                targets.add("Normal")
            elif to.type in {"SEPARATE_COLOR", "SEPRGB", "SEPARATE_RGB", "MATH", "MIX", "MIX_RGB", "INVERT", "DISPLACEMENT", "BUMP"}:
                for o2 in to.outputs:
                    for l2 in o2.links:
                        if l2.to_node.type == "BSDF_PRINCIPLED":
                            targets.add(l2.to_socket.name)
                        elif l2.to_node.type == "NORMAL_MAP":
                            targets.add("Normal")
    return targets


def _material_checks(obj, issues):
    mats = []
    largest_texture = 0
    for slot in obj.material_slots:
        mat = slot.material
        if mat is None:
            _issue(issues, "major", "MAT_EMPTY_SLOT", "Empty material slot", obj.name)
            continue
        info = dict(name=mat.name, images=[])
        if mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type != "TEX_IMAGE":
                    continue
                img = node.image
                if img is None:
                    _issue(issues, "major", "TEX_NODE_EMPTY", f"Image node without image in material {mat.name}", obj.name)
                    continue
                w, h = img.size[0], img.size[1]
                exists = bool(img.packed_file) or (img.filepath and os.path.exists(bpy.path.abspath(img.filepath))) or img.source == "GENERATED"
                cs = img.colorspace_settings.name
                targets = _image_targets(mat.node_tree, node)
                data_like = targets & _NONCOLOR_SOCKETS and "Base Color" not in targets and "Emission Color" not in targets
                if data_like and cs not in {"Non-Color", "Linear Rec.709", "Raw"}:
                    _issue(issues, "major", "TEX_COLORSPACE", f"{img.name} feeds {sorted(targets)} but colorspace is {cs} (should be Non-Color)", obj.name)
                if ("Base Color" in targets) and cs == "Non-Color":
                    _issue(issues, "major", "TEX_COLORSPACE", f"{img.name} feeds Base Color but colorspace is Non-Color (should be sRGB)", obj.name)
                if not exists and not img.has_data:
                    _issue(issues, "blocker", "TEX_MISSING", f"Missing texture file: {img.filepath or img.name}", obj.name)
                if w and (w & (w - 1) or h & (h - 1)):
                    _issue(issues, "minor", "TEX_NOT_POW2", f"{img.name} is {w}x{h}, not a power of two", obj.name)
                largest_texture = max(largest_texture, w, h)
                info["images"].append(dict(name=img.name, size=[w, h], colorspace=cs, targets=sorted(targets), exists=bool(exists)))
        if re.match(r"^Material(\.\d+)?$", mat.name):
            _issue(issues, "minor", "MAT_DEFAULT_NAME", f"Material has default name {mat.name}", obj.name)
        mats.append(info)
    return mats, largest_texture


# --------------------------------------------------------------------------- main audit


def _parse_pivot(pivot):
    """'bottom_center' | 'Name=rule,Other=rule,default=rule' | dict -> (default_rule, {name: rule})."""
    if isinstance(pivot, dict):
        d = dict(pivot)
        return d.pop("default", "bottom_center"), d
    if "=" not in (pivot or ""):
        return pivot or "bottom_center", {}
    rules = {}
    default = "bottom_center"
    for part in pivot.split(","):
        k, _, v = part.partition("=")
        if k.strip() == "default":
            default = v.strip()
        else:
            rules[k.strip()] = v.strip()
    return default, rules


def audit(objects=None, collection=None, asset_class="small_prop", max_tris=None, max_texture=None,
          max_materials=None, pivot="bottom_center", name_regex=DEFAULT_NAME_REGEX, texture_size=None,
          evaluated=True, uv_grid=128, max_total_tris=None, asset_pivot=None, shared_uv=False):
    """Audit mesh objects. Returns a dict (JSON-serialisable).

    pivot: rule for every object, or per-object overrides 'SM_X_Lid=any,SM_X_Lock=any,default=bottom_center'.
    asset_pivot: 'bottom_center' checks the combined bounding box of all audited objects against the world
    origin (the asset's pivot), for assets made of several parts that share one origin.
    max_total_tris: budget for the sum of all audited objects (the brief's per-asset number).
    shared_uv: the objects share one texture/UV space; coverage is judged on the sum, not per object.
    """
    budget = dict(CLASS_BUDGETS.get(asset_class, CLASS_BUDGETS["small_prop"]))
    if max_tris is not None:
        budget["max_tris"] = int(max_tris)
    if max_texture is not None:
        budget["max_texture"] = int(max_texture)
    if max_materials is not None:
        budget["max_materials"] = int(max_materials)

    if objects:
        objs = [bpy.data.objects[n] for n in objects if n in bpy.data.objects]
        missing = [n for n in objects if n not in bpy.data.objects]
    elif collection and collection in bpy.data.collections:
        objs = list(bpy.data.collections[collection].all_objects)
        missing = []
    else:
        objs = list(bpy.context.scene.objects)
        missing = []
    objs = [o for o in objs if o.type == "MESH"]

    bpy.context.view_layer.update()  # matrix_world is stale after script-side transforms
    depsgraph = bpy.context.evaluated_depsgraph_get()
    issues = []
    per_object = []
    total_tris = 0
    name_re = re.compile(name_regex) if name_regex else None
    pivot_default, pivot_rules = _parse_pivot(pivot)
    world_pts = []

    for obj in objs:
        rec = dict(name=obj.name)
        pivot_rule = pivot_rules.get(obj.name, pivot_default)
        rec["pivot_rule"] = pivot_rule
        mesh_src = obj.data
        if evaluated:
            mesh, eval_obj = _evaluated_mesh(obj, depsgraph)
        else:
            mesh, eval_obj = mesh_src, None

        # --- transforms & pivot
        rot = obj.rotation_euler
        scl = obj.scale
        rec["location"] = [round(c, 4) for c in obj.location]
        rec["rotation_deg"] = [round(math.degrees(a), 2) for a in rot]
        rec["scale"] = [round(s, 4) for s in scl]
        if any(abs(a) > 1e-4 for a in rot):
            _issue(issues, "blocker", "XFORM_ROTATION", f"Rotation not applied: {rec['rotation_deg']}", obj.name)
        if any(abs(s - 1.0) > 1e-4 for s in scl):
            _issue(issues, "blocker", "XFORM_SCALE", f"Scale not applied: {rec['scale']}", obj.name)
        if any(s < 0 for s in scl):
            _issue(issues, "blocker", "XFORM_NEGATIVE_SCALE", "Negative scale flips normals on export", obj.name)

        bb = _bbox_local(mesh)
        if bb:
            mn, mx = bb
            dims = [round(abs((mx - mn)[i] * scl[i]), 4) for i in range(3)]
            rec["dimensions_m"] = dims
            tol = max(0.005 * max(dims), 0.001)
            cx, cy = (mn.x + mx.x) / 2, (mn.y + mx.y) / 2
            cz = (mn.z + mx.z) / 2
            rec["origin_offset_from_bottom_center"] = [round(cx, 4), round(cy, 4), round(mn.z, 4)]
            if pivot_rule == "bottom_center" and (abs(cx) > tol or abs(cy) > tol or abs(mn.z) > tol):
                _issue(issues, "major", "PIVOT_NOT_BOTTOM_CENTER",
                       f"Origin is off the bounding-box bottom-center by {rec['origin_offset_from_bottom_center']} m "
                       f"(bbox-based: a one-sided protrusion shifts it; use pivot overrides or asset_pivot for parts)", obj.name)
            if pivot_rule == "center" and (abs(cx) > tol or abs(cy) > tol or abs(cz) > tol):
                _issue(issues, "major", "PIVOT_NOT_CENTER", "Origin is not at the bounding-box center", obj.name)
            for v in mesh.vertices:
                world_pts.append(obj.matrix_world @ v.co)
            if max(dims) < 0.01:
                _issue(issues, "major", "SCALE_TINY", f"Largest dimension is {max(dims)} m: wrong unit scale?", obj.name)
            if max(dims) > 500:
                _issue(issues, "major", "SCALE_HUGE", f"Largest dimension is {max(dims)} m: wrong unit scale?", obj.name)
        else:
            _issue(issues, "blocker", "MESH_EMPTY", "Mesh has no vertices", obj.name)

        # --- counts
        tris = _tri_count(mesh)
        total_tris += tris
        rec.update(verts=len(mesh.vertices), faces=len(mesh.polygons), tris=tris)
        if tris > budget["max_tris"]:
            _issue(issues, "blocker", "BUDGET_TRIS", f"{tris} tris > budget {budget['max_tris']} ({asset_class})", obj.name)
        elif tris > 0.9 * budget["max_tris"]:
            _issue(issues, "minor", "BUDGET_TRIS_NEAR", f"{tris} tris is within 10% of budget {budget['max_tris']}", obj.name)

        # --- topology
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        geo = _geometry_checks(bm, budget)
        rec["geometry"] = geo
        if geo["nonmanifold_edges"]:
            _issue(issues, "blocker", "GEO_NONMANIFOLD", f"{geo['nonmanifold_edges']} edges shared by 3+ faces", obj.name)
        if geo["wire_edges"]:
            _issue(issues, "major", "GEO_WIRE_EDGES", f"{geo['wire_edges']} edges without faces", obj.name)
        if geo["loose_verts"]:
            _issue(issues, "major", "GEO_LOOSE_VERTS", f"{geo['loose_verts']} loose vertices", obj.name)
        if geo["inconsistent_normal_edges"]:
            _issue(issues, "blocker", "GEO_FLIPPED_FACES", f"{geo['inconsistent_normal_edges']} edges with inconsistent winding (flipped faces)", obj.name)
        if geo["normals_mostly_inward"]:
            _issue(issues, "major", "GEO_NORMALS_INWARD", "Normals point inward on average (recalculate outside)", obj.name)
        if geo["zero_area_faces"]:
            _issue(issues, "major", "GEO_ZERO_AREA", f"{geo['zero_area_faces']} zero-area faces", obj.name)
        if geo["zero_length_edges"]:
            _issue(issues, "major", "GEO_ZERO_LENGTH", f"{geo['zero_length_edges']} zero-length edges", obj.name)
        if geo["duplicate_verts"]:
            _issue(issues, "major", "GEO_DUPLICATE_VERTS", f"{geo['duplicate_verts']} duplicate vertices (merge by distance)", obj.name)
        if geo["ngons"] and not budget["allow_ngons"]:
            _issue(issues, "major", "GEO_NGONS", f"{geo['ngons']} n-gons (triangulation on export is unpredictable)", obj.name)
        if geo["boundary_edges"] and not budget["allow_open"]:
            _issue(issues, "minor", "GEO_OPEN_MESH", f"{geo['boundary_edges']} boundary edges (open mesh; fine if intentional)", obj.name)
        if geo["high_valence_poles"] > max(4, len(bm.verts) * 0.02):
            _issue(issues, "minor", "GEO_POLES", f"{geo['high_valence_poles']} vertices with 6+ edges (shading pinches)", obj.name)

        # --- shading
        smooth_faces = sum(1 for p in mesh.polygons if p.use_smooth)
        sharp_attr = mesh.attributes.get("sharp_edge")
        sharp_edges = sum(1 for v in sharp_attr.data if v.value) if sharp_attr else 0
        rec["shading"] = dict(smooth_faces=smooth_faces, flat_faces=len(mesh.polygons) - smooth_faces,
                              sharp_edges=sharp_edges, has_custom_normals=mesh.has_custom_normals)
        if 0 < smooth_faces < len(mesh.polygons) and sharp_edges == 0 and not mesh.has_custom_normals:
            _issue(issues, "minor", "SHADE_MIXED", "Mixed smooth/flat faces without sharp edges; check shading intent", obj.name)
        if smooth_faces == len(mesh.polygons) and sharp_edges == 0 and not mesh.has_custom_normals and geo["quads"] + geo["tris_faces"] + geo["ngons"] > 12:
            _issue(issues, "minor", "SHADE_ALL_SMOOTH", "All faces smooth with no sharp edges or custom normals: hard edges will look soft", obj.name)

        # --- modifiers
        mods = [dict(name=m.name, type=m.type, show_viewport=m.show_viewport, show_render=m.show_render) for m in obj.modifiers]
        rec["modifiers"] = mods
        if mods and not evaluated:
            _issue(issues, "minor", "MODS_UNAPPLIED", f"{len(mods)} modifiers not applied (exporters may apply them)", obj.name)

        # --- UVs
        tex_assumed = texture_size or budget["max_texture"]
        uvrep = _uv_checks(bm, mesh, obj.matrix_world, tex_assumed, grid=uv_grid)
        rec["uv"] = uvrep
        if not uvrep["has_uv"]:
            sev = "blocker" if asset_class not in {"placeholder"} else "minor"
            _issue(issues, sev, "UV_MISSING", "No UV map", obj.name)
        else:
            if uvrep["uv_faces_out_of_bounds"]:
                _issue(issues, "major", "UV_OUT_OF_BOUNDS", f"{uvrep['uv_faces_out_of_bounds']} faces outside 0-1 (ok only for tiling materials)", obj.name)
            if uvrep["uv_overlap_fraction"] > 0.02:
                _issue(issues, "major", "UV_OVERLAP", f"{round(uvrep['uv_overlap_fraction']*100,1)}% of covered UV space overlaps (ok only if mirrored on purpose)", obj.name)
            if uvrep["uv_coverage"] < 0.60 and not shared_uv:
                _issue(issues, "minor", "UV_LOW_COVERAGE", f"UV coverage {round(uvrep['uv_coverage']*100)}% (< 60%); pack tighter or shrink the texture", obj.name)
            if 0 < uvrep["uv_flipped_faces"] < len(mesh.polygons):
                _issue(issues, "minor", "UV_FLIPPED", f"{uvrep['uv_flipped_faces']} faces with mirrored UVs (fine if mirrored on purpose; not for lightmaps or decals)", obj.name)
            if uvrep["texel_density_cv"] > 0.35:
                _issue(issues, "major", "UV_DENSITY_UNEVEN", f"Texel density varies a lot (CV {uvrep['texel_density_cv']}); stretch or inconsistent island scale", obj.name)

        # --- materials
        mats, largest = _material_checks(obj, issues)
        rec["materials"] = mats
        if len(mats) > budget["max_materials"]:
            _issue(issues, "major", "BUDGET_MATERIALS", f"{len(mats)} materials > budget {budget['max_materials']}", obj.name)
        if largest > budget["max_texture"]:
            _issue(issues, "blocker", "BUDGET_TEXTURE", f"Largest texture {largest} px > budget {budget['max_texture']}", obj.name)
        if not mats and asset_class != "placeholder":
            _issue(issues, "major", "MAT_NONE", "No material assigned", obj.name)

        # --- naming
        if name_re and not name_re.match(obj.name):
            _issue(issues, "minor", "NAME_CONVENTION", f"Object name does not match {name_regex}", obj.name)
        if obj.data.name != obj.name and not obj.data.name.startswith(obj.name):
            _issue(issues, "minor", "NAME_MESH_DATA", f"Mesh data named {obj.data.name}; rename to match object", obj.name)

        bm.free()
        if eval_obj is not None:
            eval_obj.to_mesh_clear()
        per_object.append(rec)

    for n in missing:
        _issue(issues, "blocker", "OBJECT_MISSING", f"Object {n} not found", n)

    # Asset-level checks: combined pivot, total triangle budget, shared UV coverage.
    asset_bbox = None
    if world_pts:
        lo = [min(p[i] for p in world_pts) for i in range(3)]
        hi = [max(p[i] for p in world_pts) for i in range(3)]
        asset_bbox = [[round(v, 4) for v in lo], [round(v, 4) for v in hi]]
        if asset_pivot == "bottom_center":
            tol = max(0.005 * max(hi[i] - lo[i] for i in range(3)), 0.001)
            cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
            if abs(cx) > tol or abs(cy) > tol or abs(lo[2]) > tol:
                _issue(issues, "major", "ASSET_PIVOT",
                       f"Asset bounding box bottom-center is at {[round(cx, 4), round(cy, 4), round(lo[2], 4)]}, not the world origin")
    if max_total_tris is not None and total_tris > int(max_total_tris):
        _issue(issues, "blocker", "BUDGET_TOTAL_TRIS", f"{total_tris} tris in total > asset budget {max_total_tris}")
    uv_cov_sum = round(sum(o.get("uv", {}).get("uv_coverage", 0.0) for o in per_object), 3)
    if shared_uv and per_object and uv_cov_sum < 0.60:
        _issue(issues, "minor", "UV_LOW_COVERAGE", f"Combined UV coverage {round(uv_cov_sum*100)}% (< 60%) across the shared texture")

    counts = {s: sum(1 for i in issues if i["severity"] == s) for s in ("blocker", "major", "minor")}
    verdict = "blocked" if counts["blocker"] else ("needs_fixes" if counts["major"] else "pass")
    return dict(
        blender=bpy.app.version_string,
        asset_class=asset_class,
        budget=budget,
        pivot_rule=pivot,
        objects_audited=[o.name for o in objs],
        total_tris=total_tris,
        max_total_tris=max_total_tris,
        asset_bbox_world=asset_bbox,
        uv_coverage_combined=uv_cov_sum if shared_uv else None,
        verdict=verdict,
        issue_counts=counts,
        issues=issues,
        objects=per_object,
    )


def to_markdown(report):
    lines = [f"# Mesh audit - verdict: **{report['verdict']}**",
             "",
             f"Blender {report['blender']} - class `{report['asset_class']}` - budget {report['budget']['max_tris']} tris per object"
             + (f", {report['max_total_tris']} total" if report.get('max_total_tris') else "")
             + f" / {report['budget']['max_texture']} px / {report['budget']['max_materials']} materials - pivot rule `{report['pivot_rule']}`"
             + f" - total tris {report['total_tris']}",
             "",
             "| Object | Tris | Dims (m) | Quads % | UV cov | Texel px/m | Mats | Issues |",
             "|---|---|---|---|---|---|---|---|"]
    for o in report["objects"]:
        n_issues = sum(1 for i in report["issues"] if i["object"] == o["name"])
        uv = o.get("uv", {})
        lines.append(f"| {o['name']} | {o['tris']} | {'x'.join(str(d) for d in o.get('dimensions_m', []))} | "
                     f"{int(o['geometry']['quad_ratio']*100)} | {uv.get('uv_coverage', '-')} | {uv.get('texel_density_px_per_m', '-')} | "
                     f"{len(o['materials'])} | {n_issues} |")
    lines += ["", "## Issues", ""]
    if not report["issues"]:
        lines.append("None.")
    for sev in ("blocker", "major", "minor"):
        for i in report["issues"]:
            if i["severity"] == sev:
                lines.append(f"- **{sev}** `{i['code']}` {i['object'] or ''}: {i['message']}")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- CLI

def _cli():
    import argparse
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(prog="mesh_audit")
    p.add_argument("--objects", help="comma-separated object names")
    p.add_argument("--collection")
    p.add_argument("--asset-class", default="small_prop", choices=sorted(CLASS_BUDGETS))
    p.add_argument("--max-tris", type=int)
    p.add_argument("--max-texture", type=int)
    p.add_argument("--max-materials", type=int)
    p.add_argument("--pivot", default="bottom_center", help="bottom_center|center|any, or per-object 'SM_X_Lid=any,default=bottom_center'")
    p.add_argument("--asset-pivot", choices=["bottom_center", "none"], default=None, help="check the combined bbox of all objects against the world origin")
    p.add_argument("--max-total-tris", type=int, help="budget for the sum of all audited objects")
    p.add_argument("--shared-uv", action="store_true", help="objects share one texture: judge UV coverage on the sum")
    p.add_argument("--name-regex", default=DEFAULT_NAME_REGEX)
    p.add_argument("--texture-size", type=int)
    p.add_argument("--source", action="store_true", help="audit source mesh instead of evaluated (modifiers applied)")
    p.add_argument("--uv-grid", type=int, default=128, help="UV overlap raster size; 64 for 50k+ face meshes")
    p.add_argument("--json")
    p.add_argument("--md")
    a = p.parse_args(argv)
    rep = audit(objects=a.objects.split(",") if a.objects else None, collection=a.collection,
                asset_class=a.asset_class, max_tris=a.max_tris, max_texture=a.max_texture,
                max_materials=a.max_materials, pivot=a.pivot, name_regex=a.name_regex,
                texture_size=a.texture_size, evaluated=not a.source, uv_grid=a.uv_grid,
                max_total_tris=a.max_total_tris, asset_pivot=(a.asset_pivot if a.asset_pivot != "none" else None),
                shared_uv=a.shared_uv)
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(rep, fh, indent=2)
    md = to_markdown(rep)
    if a.md:
        with open(a.md, "w") as fh:
            fh.write(md)
    print(md)
    print("AUDIT_JSON=" + json.dumps(rep))


if __name__ == "__main__":
    _cli()
