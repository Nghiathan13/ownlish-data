#!/usr/bin/env python3
"""Reorder media keys in content JSON: id, number, audio, image (then the rest).

Only dicts that carry an "id" (items, groups, segments) are touched;
all other keys keep their existing relative order.

Usage: python3 scripts/reorder-keys.py
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
ORDER = ("id", "number", "audio", "image")


def walk(node) -> None:
    if isinstance(node, dict):
        for key in list(node.keys()):
            walk(node[key])
        if "id" in node:
            head = [k for k in ORDER if k in node]
            rest = [k for k in node if k not in ORDER]
            old = dict(node)
            node.clear()
            node.update({k: old[k] for k in head + rest})
    elif isinstance(node, list):
        for item in node:
            walk(item)


def main() -> None:
    files = sorted(ROOT.glob("toeic/**/*.json")) + sorted(ROOT.glob("dictation/**/*.json"))
    n = 0
    for f in files:
        try:
            data = json.loads(f.read_text())
        except json.JSONDecodeError:
            continue  # empty placeholder part files
        walk(data)
        f.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        n += 1
    print(f"reordered {n} files")


main()
