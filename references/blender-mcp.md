# Blender MCP: how Claude drives Blender

Verified against the official Blender MCP extension source (`lab_blender_org/mcp`, version 1.0.3,
Blender 5.2.2 LTS) and against the tools exposed in a Claude Code session. Blender's own page:
https://www.blender.org/lab/mcp-server/

## The three execution modes

| Mode | Precondition | Tool / command | Persistence |
|---|---|---|---|
| Live MCP | Blender GUI open, extension enabled, bridge server running on `localhost:9876` | `mcp__Blender__execute_blender_code(code)` | Changes live in the open file until you save (`bpy.ops.wm.save_mainfile()`) |
| Background MCP | MCP server can find Blender (`BLENDER_PATH` env var or `blender` on PATH of the MCP server process) | `mcp__Blender__execute_blender_code_for_cli(blend_file, code)` | A fresh `blender --background <file>` per call: the code must save, or the work is lost |
| Headless CLI | Blender installed | `bash scripts/blender_run.sh <script.py> [file.blend] -- args` | Whatever the script writes |

Detect the mode at the start of a phase:

1. Call `get_objects_summary`. If it returns collections, you are live. The error
   `Cannot connect to Blender at localhost:9876` means the GUI is not open or the bridge is stopped.
2. If not live, try `execute_blender_code_for_cli` with a one-liner. The error `Blender executable not
   found at 'blender'. Set the BLENDER_PATH environment variable` means the MCP server cannot find Blender:
   tell the user once (a symlink `ln -s /Applications/Blender.app/Contents/MacOS/Blender /usr/local/bin/blender`
   or `BLENDER_PATH` in the MCP server config fixes it) and use the CLI.
3. The CLI works whenever `scripts/doctor.sh` finds Blender. It is the default for autonomous work: it is
   deterministic and leaves no state in a GUI the user may be editing.

Prefer live mode when the user is watching or wants to tweak things by hand between passes; prefer the
CLI for every build-script run, bake and export, because the result is reproducible from the repo.

## execute_blender_code semantics (from the source)

- The code runs with `exec()` in a namespace where `result = {}` is predefined. Set `result` to a
  **JSON-serialisable dict** to return data. Returning a Blender object fails (`not JSON-serializable`);
  return names, numbers and lists instead.
- `print()` output comes back as `stdout`; exceptions come back as the full traceback in `message`.
- Long jobs (a Cycles render started with `INVOKE_DEFAULT`): define a callable `check_is_finished()` in the
  code that returns `None` while running and a dict when done. The server polls it on its timer and holds
  the connection up to one hour. In background mode deferred responses are not supported; call blocking
  operators instead (`bpy.ops.render.render(write_still=True)`).
- A weak sandbox blocks `sys.exit()`, `bpy.ops.wm.quit_blender`, `wm.read_factory_settings`,
  `wm.read_factory_userpref` and `wm.read_userpref`. Everything else runs with full `bpy` access, so
  treat the open file as the user's: inspect before changing, keep their names, never delete objects
  without saying so.
- Each call is independent. Module-level variables do not survive between calls unless you stash them on
  `bpy.app.driver_namespace` or in a scene custom property. Re-import the bundled scripts in every call.

Loading the bundled scripts inside a call:

```python
SCRIPTS_DIR = "<plugin root>/scripts/blender"
exec(open(SCRIPTS_DIR + "/_load.py").read())
mesh_audit, export_asset, render_review, bake_textures, scene_setup, material_kit = load_all(SCRIPTS_DIR)
result = mesh_audit.audit(objects=["SM_Crate_A"], asset_class="small_prop")
```

Running a build script in live mode (so the user sees the model appear):

```python
import runpy, sys
sys.argv = ["build.py", "--", "--save", "/abs/path/assets/Crate_A/source/Crate_A.blend"]
runpy.run_path("/abs/path/assets/Crate_A/scripts/build.py", run_name="__main__")
result = {"ok": True}
```

## Looking at the result

Claude judges quality by looking, so every modeling pass ends with an image:

- `render_thumbnail_to_path(output_path)`: small, fast render with the scene's camera. Then open the file
  with the Read tool.
- `render_viewport_to_path(output_path)`: full render with the current settings and camera.
- `get_screenshot_of_area_as_image(area_ui_type="VIEW_3D")`: what the user sees, including overlays
  (wireframe, statistics). Live mode only.
- `scripts/blender/render_review.py`: the review sheet (beauty, clay with cavity, wireframe; orthographic
  front/right/top plus a 3/4 view; optional turntable). Works in every mode and needs no camera in the
  file. This is the one to use for reviews; the others are for quick looks.
- Baked textures: open the PNGs with the Read tool. When reading pixel values back inside Blender for
  checks, set `image.colorspace_settings.name = "Non-Color"` *before* reading `pixels`, or sRGB files
  come back linearised (0.5 reads as 0.214).

## Other tools

- `get_objects_summary`, `get_object_detail_summary(name)`: hierarchy, transforms, modifiers, materials,
  visibility. Use them before touching a user's file.
- `jump_to_view3d_object_by_name`, `jump_to_tab_by_name`: move the user's view (live mode).
- `get_blendfile_summary_*`: datablocks, missing files, linked libraries, path info, usage guess. Run the
  missing-files one before any export.
- `search_api_docs`, `get_python_api_docs(identifier)`, `search_manual_docs`: the bundled Blender 5.2 API
  and manual. They work without Blender running. Check any operator argument you are not sure about
  here instead of guessing: the 4.x to 5.x transition renamed and removed things
  (`references/blender-python.md` lists the ones that matter).

## Background-mode rules that bite

- No window, no 3D viewport area: operators that need one (`view3d.*`, some `uv.*` in the UV editor)
  fail with "context is incorrect". Use `bpy.context.temp_override(...)` with an area in live mode, or
  avoid the operator: `bmesh` and the data API cover modeling; `uv.unwrap`, `uv.smart_project`,
  `uv.pack_islands` work from Edit mode without a UV editor.
- Selection and the active object are explicit state: set them before every operator that needs them
  (`obj.select_set(True)`, `view_layer.objects.active = obj`) and set the mode (`object.mode_set`).
- EEVEE, Workbench and Cycles all render headless on macOS and Linux (tested: 0.3 s for a 320x240
  frame of each). Cycles bakes are CPU in background mode; set samples low (8 to 32) for data maps.
- `bpy.app.timers` do not fire in background mode; the MCP extension's bridge server does not start
  there either (that is why `_for_cli` spawns a process per call).

## Starting the bridge in the GUI (for the user)

Edit > Preferences > Get Extensions: install "MCP" from the Blender extensions platform (Blender Lab).
System > Network: "Allow Online Access" must be on, or the server refuses to start with
"Online access must be enabled in the system preferences". Preferences > Add-ons > MCP shows the Start /
Stop button and the port (default 9876). Auto Start is on by default; the server starts one second after
Blender opens.
