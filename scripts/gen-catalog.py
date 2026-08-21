#!/usr/bin/env python3
"""Generate catalog.json (ToeicCatalogManifest schemaVersion 1) from content JSON.

Port of the web repo's catalog-builder.ts output schema
(apps/server/src/entities/toeic-catalog/lib/catalog-builder.ts),
adapted to the migrated key names (audio/image instead of audioUrl/imageUrl,
values already relative to the data repo root).

Only catalog.json is produced (no grading index, no part-practice files).

Usage: python3 scripts/gen-catalog.py
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOEIC = ROOT / "toeic"
PART_NUMBERS = list(range(1, 8))
SERIES_RE = re.compile(r"^(ets|ybm)_(\d{2})$")
TEST_RE = re.compile(r"^test_(\d{2})$")
FLAT_PARTS = {1, 2, 5}


def series_info(dirname: str):
    m = SERIES_RE.match(dirname)
    return (dirname, 2000 + int(m.group(2))) if m else None


def read_part(path: pathlib.Path):
    """Return (question_count, media_by_group_id)."""
    raw = path.read_text()
    if not raw.strip():
        return None
    doc = json.loads(raw)
    key = "items" if any(path.name == f"part_{p}.json" for p in FLAT_PARTS) else "groups"
    collection = doc.get(key, [])
    count = 0
    media = {}
    if key == "items":
        for item in collection:
            count += 1
            m = {}
            if item.get("audio"):
                m["audio"] = item["audio"]
            if item.get("image"):
                m["image"] = item["image"]
            if m:
                media[item.get("id")] = m
    else:
        for group in collection:
            count += len(group.get("questions", []))
            m = {}
            if group.get("audio"):
                m["audio"] = group["audio"]
            if group.get("image"):
                m["image"] = group["image"]
            if m:
                media[group.get("id")] = m
    return count, media


def main() -> None:
    tests = []
    media_by_group_id = {}
    practice_counts = {p: 0 for p in PART_NUMBERS}
    practice_test_ids = {p: set() for p in PART_NUMBERS}

    for series_dir in sorted(d for d in TOEIC.iterdir() if d.is_dir()):
        info = series_info(series_dir.name)
        if not info:
            continue
        series, year = info
        for test_dir in sorted(d for d in series_dir.iterdir() if d.is_dir()):
            tm = TEST_RE.match(test_dir.name)
            if not tm:
                continue
            test_number = int(tm.group(1))
            test_id = f"{series.replace('_', '')}-t{test_number:02d}"
            parts = []
            for part_number in PART_NUMBERS:
                part_path = test_dir / f"part_{part_number}.json"
                if not part_path.exists():
                    continue
                result = read_part(part_path)
                if result is None:
                    continue
                count, media = result
                rel = part_path.relative_to(ROOT).as_posix()
                parts.append(
                    {
                        "number": part_number,
                        "path": rel,
                        "questionCount": count,
                    }
                )
                media_by_group_id.update(media)
                practice_counts[part_number] += count
                practice_test_ids[part_number].add(test_id)
            if not parts:
                continue
            tests.append(
                {
                    "id": test_id,
                    "year": year,
                    "testNumber": test_number,
                    "parts": parts,
                }
            )

    part_practice = []
    for part_number in PART_NUMBERS:
        entry = {
            "number": part_number,
            "path": f"part-practice/part_{part_number}.json",
            "questionCount": practice_counts[part_number],
        }
        entry["complete"] = (
            bool(tests)
            and practice_counts[part_number] > 0
            and len(practice_test_ids[part_number]) == len(tests)
        )
        part_practice.append(entry)

    manifest = {
        "schemaVersion": 1,
        "tests": tests,
        "partPractice": part_practice,
        "mediaByGroupId": media_by_group_id,
    }
    out = ROOT / "catalog.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(f"tests: {len(tests)}, parts total: {sum(len(t['parts']) for t in tests)}, media entries: {len(media_by_group_id)}")
    print(f"incomplete tests: {sum(1 for t in tests if len(t['parts']) != len(PART_NUMBERS))}")


main()
