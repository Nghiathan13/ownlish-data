#!/usr/bin/env python3
"""Migrate absolute Supabase storage URLs to relative paths in content JSON.

audioUrl -> audio, imageUrl -> image.
Values become paths relative to the data repo root (ownlish-data/).
Other URL keys (e.g. youtube "url") are left untouched.

Usage: python3 scripts/migrate-media-paths.py [--dry-run]
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PREFIX = re.compile(r"^https://[a-z0-9]+\.supabase\.co/storage/v1/object/public/")


def migrate(path: pathlib.Path) -> bool:
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return False  # empty/placeholder part file — skip, app handles absence
    changed = False

    def walk(node) -> None:
        nonlocal changed
        if isinstance(node, dict):
            for key, value in list(node.items()):
                if key in ("audioUrl", "imageUrl") and isinstance(value, str):
                    m = PREFIX.match(value)
                    if m:
                        rel = value[m.end() :]
                        assert rel and not rel.startswith("/"), f"bad url: {value!r}"
                        node[key.replace("Url", "")] = rel
                        del node[key]
                        changed = True
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)
    if changed:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    return changed


def main() -> None:
    dry = "--dry-run" in sys.argv
    files = sorted(ROOT.glob("toeic/**/*.json")) + sorted(ROOT.glob("dictation/**/*.json"))
    migrated = sum(1 for f in files if not dry and migrate(f))
    if dry:
        print(f"DRY-RUN: {len(files)} json files scanned, 0 written")
    else:
        left = sum(1 for f in files if "supabase.co/storage" in f.read_text())
        audio = sum(f.read_text().count('"audio"') for f in files)
        image = sum(f.read_text().count('"image"') for f in files)
        print(f"migrated {migrated}/{len(files)} files; storage refs left: {left}; audio keys: {audio}, image keys: {image}")


main()
