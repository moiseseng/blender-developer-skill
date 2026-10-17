import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _check import *
import bpy, bmesh, math
from mathutils import Vector, Matrix
reset_scene()

# ---- Lathe (spin) a bottle profile: (radius, height) in meters, in the XZ plane
profile = [(0.0, 0.0), (0.035, 0.0), (0.04, 0.01), (0.04, 0.18), (0.03, 0.22), (0.015, 0.24),
           (0.015, 0.29), (0.018, 0.30), (0.0, 0.30)]
bm = bmesh.new()
vs = [bm.verts.new((x, 0.0, z)) for x, z in profile]
for a, b in zip(vs, vs[1:]): bm.edges.new((a, b))
STEPS = 32
bmesh.ops.spin(bm, geom=bm.verts[:] + bm.edges[:], cent=(0, 0, 0), axis=(0, 0, 1), dvec=(0, 0, 0),
               angle=math.tau, steps=STEPS, use_merge=True)
report(snapshot(bm, "bottle_raw"), "spin_bottle_raw_before_remove_doubles")
bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)      # collapse axis duplicates
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
off_axis = sum(1 for x, z in profile if x > 0)
print(f"EXPECT verts = {STEPS}*{off_axis} + 2 axis = {STEPS*off_axis + 2}")
report(obj_from_bmesh(bm, "SM_Bottle"), "spin_bottle_clean")

# ---- Tire via spin of a circle cross-section around Z
bm = bmesh.new()
bmesh.ops.create_circle(bm, segments=12, radius=0.08,
                        matrix=Matrix.Translation((0.30, 0, 0)) @ Matrix.Rotation(math.radians(90), 4, 'X'))
bmesh.ops.spin(bm, geom=bm.verts[:] + bm.edges[:], cent=(0, 0, 0), axis=(0, 0, 1), angle=math.tau, steps=48, use_merge=True)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
report(obj_from_bmesh(bm, "SM_Tire"), "spin_tire_torus_48x12")

# ---- Partial spin (90 deg arc) e.g. a pipe elbow from a circle
bm = bmesh.new()
bmesh.ops.create_circle(bm, segments=16, radius=0.03, matrix=Matrix.Translation((0.1, 0, 0)) @ Matrix.Rotation(math.radians(90), 4, 'X'))
bmesh.ops.spin(bm, geom=bm.verts[:] + bm.edges[:], cent=(0, 0, 0), axis=(0, 0, 1), angle=math.radians(90), steps=8, use_merge=False)
report(obj_from_bmesh(bm, "SM_Elbow"), "spin_elbow_90deg_open_ends")

# ---- bridge_loops between two circles = tapered tube
bm = bmesh.new()
bmesh.ops.create_circle(bm, segments=24, radius=0.5)
bmesh.ops.create_circle(bm, segments=24, radius=0.3, matrix=Matrix.Translation((0, 0, 1.0)))
bmesh.ops.bridge_loops(bm, edges=bm.edges[:])
report(obj_from_bmesh(bm, "SM_Tube"), "bridge_loops_tapered_tube")

# ---- symmetrize: half shape on +X, which direction string copies where?
def half():
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0.5, 0, 0)))
    bmesh.ops.create_cube(bm, size=0.4, matrix=Matrix.Translation((0.8, 0.5, 0.3)))   # asymmetric bump
    on_plane = [f for f in bm.faces if abs(f.calc_center_median().x) < 1e-6]
    bmesh.ops.delete(bm, geom=on_plane, context='FACES_ONLY')   # open the seam: a face ON the mirror plane becomes an interior face
    return bm
for d in ('X', '-X'):
    bm = half()
    bmesh.ops.symmetrize(bm, input=bm.verts[:] + bm.edges[:] + bm.faces[:], direction=d, dist=1e-4)
    report(obj_from_bmesh(bm, f"sym_{d}"), f"symmetrize_direction_{d}_from_plusX_half")
# ---- bmesh.ops.mirror alternative (duplicate + mirror + merge at seam)
bm = half()
geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
r = bmesh.ops.mirror(bm, geom=geom, matrix=Matrix.Identity(4), merge_dist=1e-4, axis='X')
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
report(obj_from_bmesh(bm, "mirror_op"), "bmesh_mirror_op_X_merged")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_out"); os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "t02.blend"))
print("DONE t02")
