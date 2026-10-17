#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
make_manifest.py - write docs/manifest.json for an asset folder: every delivered file with size and
SHA-256, the counts from the last audit and export JSON, tool versions, and the README's numbers.

    python3 scripts/make_manifest.py assets/Crate_A [--version 1.0.0] [--blender "5.2.2 LTS"]

Plain Python (no bpy). Reads docs/qa/audit.json and export/export.json when present.
"""

import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys

DELIVERED_DIRS = ("source", "export", "textures", "renders", "docs", "scripts")
DELIVERED_FILES = ("README.md", "CHANGELOG.md", "LICENSE.txt", "THIRD_PARTY_NOTICES.txt")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("asset_dir")
    p.add_argument("--version", default="1.0.0")
    p.add_argument("--blender", default=None)
    a = p.parse_args()
    root = os.path.abspath(a.asset_dir)
    name = os.path.basename(root)

    files = []
    for d in DELIVERED_DIRS:
        base = os.path.join(root, d)
        for dirpath, _dirs, names in os.walk(base):
            for n in sorted(names):
                if n.startswith(".") or n.endswith((".blend1", ".pyc")):
                    continue
                fp = os.path.join(dirpath, n)
                files.append(dict(path=os.path.relpath(fp, root), bytes=os.path.getsize(fp), sha256=sha256(fp)))
    for n in DELIVERED_FILES:
        fp = os.path.join(root, n)
        if os.path.exists(fp):
            files.append(dict(path=n, bytes=os.path.getsize(fp), sha256=sha256(fp)))

    audit = {}
    ap = os.path.join(root, "docs", "qa", "audit.json")
    if os.path.exists(ap):
        with open(ap) as fh:
            audit = json.load(fh)
    export = {}
    ep = os.path.join(root, "export", "export.json")
    if os.path.exists(ep):
        with open(ep) as fh:
            export = json.load(fh)

    blender = a.blender or audit.get("blender") or export.get("blender")
    git = None
    try:
        git = subprocess.check_output(["git", "-C", root, "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        pass

    manifest = dict(
        asset=name,
        version=a.version,
        date=datetime.date.today().isoformat(),
        blender=blender,
        git_commit=git,
        audit=dict(verdict=audit.get("verdict"), total_tris=audit.get("total_tris"), asset_class=audit.get("asset_class"),
                   budget=audit.get("budget"), objects=[dict(name=o["name"], tris=o["tris"], verts=o["verts"],
                                                            dimensions_m=o.get("dimensions_m"), materials=[m["name"] for m in o.get("materials", [])])
                                                       for o in audit.get("objects", [])]) if audit else None,
        exports=[dict(preset=f.get("preset"), path=os.path.relpath(f["path"], root) if f.get("path") else None, bytes=f.get("bytes"),
                      verified=f.get("bbox_matches_scene", f.get("dims_match_scene"))) for f in export.get("files", [])] if export else None,
        files=files,
        total_bytes=sum(f["bytes"] for f in files),
    )
    out = os.path.join(root, "docs", "manifest.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as fh:
        json.dump(manifest, fh, indent=2)
    print(f"wrote {out}: {len(files)} files, {manifest['total_bytes']} bytes")


if __name__ == "__main__":
    sys.exit(main())
