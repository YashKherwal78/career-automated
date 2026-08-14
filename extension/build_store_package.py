#!/usr/bin/env python3
"""
Builds a Chrome Web Store-safe zip from this directory's dev manifest.

Why this exists: manifest.json (used for "Load unpacked" during
development) includes localhost:8000/localhost:5173 in host_permissions
and externally_connectable so the extension works against a local dev
server. Shipping those to the Store is pointless for real users and looks
bad in review (an unexplained localhost permission on a public listing
reads as suspicious) -- this script strips them and zips the rest,
without ever touching the dev manifest developers actually load unpacked.

Usage:
    python3 build_store_package.py
Produces:
    dist/careerautomated-autofill-<version>.zip
"""
import json
import shutil
import zipfile
from pathlib import Path

EXT_DIR = Path(__file__).parent
DIST_DIR = EXT_DIR / "dist"

# Files/dirs to include verbatim in the store package.
INCLUDE = [
    "background.js",
    "bridge-auth.js",
    "content-ashby.js",
    "content-greenhouse.js",
    "content-lever.js",
    "popup.html",
    "popup.js",
    "icons",
]

LOCALHOST_PATTERNS = {"http://localhost:8000/*", "http://localhost:5173/*"}


def build_store_manifest() -> dict:
    manifest = json.loads((EXT_DIR / "manifest.json").read_text())
    manifest["host_permissions"] = [
        p for p in manifest.get("host_permissions", []) if p not in LOCALHOST_PATTERNS
    ]
    manifest["externally_connectable"]["matches"] = [
        m for m in manifest["externally_connectable"]["matches"] if m not in LOCALHOST_PATTERNS
    ]
    manifest["content_scripts"] = [
        {**cs, "matches": [m for m in cs["matches"] if m not in LOCALHOST_PATTERNS]}
        for cs in manifest["content_scripts"]
    ]
    return manifest


def main():
    manifest = build_store_manifest()
    version = manifest["version"]

    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir()

    zip_path = DIST_DIR / f"careerautomated-autofill-{version}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))
        for item in INCLUDE:
            src = EXT_DIR / item
            if src.is_dir():
                for f in src.rglob("*"):
                    if f.is_file():
                        zf.write(f, f.relative_to(EXT_DIR))
            elif src.is_file():
                zf.write(src, item)

    print(f"Store package written to: {zip_path}")
    print("Verify before upload: unzip -l", zip_path)


if __name__ == "__main__":
    main()
