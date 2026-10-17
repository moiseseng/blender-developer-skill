# SPDX-License-Identifier: MIT
"""
_load.py - import the bundled Blender scripts from inside a running Blender (MCP execute_blender_code).

Paste into execute_blender_code, replacing SCRIPTS_DIR with the absolute path of this folder:

    SCRIPTS_DIR = "/path/to/blender-3d-team/scripts/blender"
    exec(open(SCRIPTS_DIR + "/_load.py").read())
    mesh_audit, export_asset, render_review, bake_textures, scene_setup, material_kit = load_all(SCRIPTS_DIR)
    result = mesh_audit.audit(objects=["SM_Crate_A"], asset_class="small_prop")

Each module exposes plain functions that return JSON-serialisable dicts, so `result` can be
assigned directly. Re-running load_all picks up edits to the scripts (no Blender restart).
"""

import importlib.util
import os
import sys


def load_module(scripts_dir, name):
    path = os.path.join(scripts_dir, name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def load_all(scripts_dir):
    names = ("mesh_audit", "export_asset", "render_review", "bake_textures", "scene_setup", "material_kit")
    return tuple(load_module(scripts_dir, n) for n in names)
