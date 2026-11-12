"""Foundry 360 batch planner: deterministic, fail-closed source verification.

Source: recovered original 360 GLB + Blender files inside the nested archive.
Generated atlases remain UNAPPROVED technical review candidates.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import struct
import zipfile
from pathlib import Path

ASSETS = 360
NAME = re.compile(r"ll_[a-z0-9_]{2,90}\Z")
SRC = "REAL_3D_SOURCES_NOT_2_5D_OR_GOLDEN_APPROVED"

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def read_catalog(z: zipfile.ZipFile) -> dict:
    raw = z.read("batch_report.json")
    catalog = json.loads(raw)
    if (catalog.get("schema") != 1 or
        catalog.get("source_plan_unique_count") != ASSETS or
        catalog.get("generated_3d_source_count") != ASSETS or
        catalog.get("status") != SRC):
        raise ValueError("Unverified or incomplete 360 source archive")
    items = catalog.get("items")
    if not isinstance(items, list) or len(items) != ASSETS:
        raise ValueError("Expected 360 model records")
    ids = [row.get("asset_id") for row in items]
    if any(not isinstance(i, str) or not NAME.fullmatch(i) for i in ids) or len(set(ids)) != ASSETS:
        raise ValueError("Invalid or duplicated model IDs")
    for item in items:
        k = item["asset_id"]
        for file in ("model.glb", "model.blend", "geometry_manifest.json"):
            if f"{k}/{file}" not in z.namelist():
                raise ValueError(f"Missing model source: {k}/{file}")
        digest = item.get("glb_sha256")
        if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise ValueError(f"Invalid GLB provenance: {k}")
    return catalog

def validate_state(state: dict | None, source_hash: str, known_ids: list[str]) -> list[str]:
    if state is None:
        return []
    if (state.get("schema_version") != 1 or
        state.get("source_plan_sha256") != source_hash or
        not isinstance(state.get("completed"), list)):
        raise ValueError("State missing, stale, or incompatible with source plan")
    completed = state["completed"]
    if len(completed) != len(set(completed)) or not set(completed).issubset(known_ids):
        raise ValueError("Unsafe or duplicated completed model IDs")
    return completed

def plan(archive: Path, state: dict | None, batch_size: int, output: Path) -> dict:
    if not 1 <= batch_size <= 4:
        raise ValueError("batch-size must be 1–4")
    output.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        catalog = read_catalog(z)
        ids = [r["asset_id"] for r in catalog["items"]]
        source_hash = catalog["source_plan_sha256"]
        completed = validate_state(state, source_hash, ids)
        todo = [r for r in catalog["items"] if r["asset_id"] not in set(completed)]
        selected = todo[:batch_size]
        assets = []
        for row in selected:
            k = row["asset_id"]
            info = z.getinfo(f"{k}/model.glb")
            if info.file_size > 10 * 1024 * 1024:
                raise ValueError(f"Unexpectedly large source GLB: {k}")
            data = z.read(info)
            if sha256(data) != row["glb_sha256"]:
                raise ValueError(f"GLB checksum mismatch: {k}")
            if len(data) < 20 or data[:4] != b"glTF" or struct.unpack_from("<I", data, 8)[0] != len(data):
                raise ValueError(f"Malformed GLB: {k}")
            folder = output / "models" / k
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "model.glb").write_bytes(data)
            original_blend = z.getinfo(f"{k}/model.blend")
            assets.append({
                "asset_id": k, "glb_path": str((folder / "model.glb").resolve()),
                "glb_sha256": row["glb_sha256"],
                "original_blend_size_bytes": original_blend.file_size,
                "geometry_status": row.get("geometry_status"),
                "candidate_only": True, "golden_approved": False,
            })
    doc = {
        "schema_version": 1, "status": "COMPLETE" if not selected else "READY",
        "source_plan_sha256": source_hash, "source_count": ASSETS,
        "completed_before": completed, "selected": assets,
        "remaining_before": ASSETS - len(completed),
        "golden_approved": False, "canonical_promoted": False,
        "f11_material_approved": False, "f12_world_scale_approved": False,
    }
    (output / "plan.json").write_text(json.dumps(doc, indent=2) + "\n")
    print(f"FOUNDRY_PLAN status={doc['status']} selected={len(selected)} remaining={len(todo)}")
    return doc

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--archive", type=Path, required=True)
    p.add_argument("--state", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--batch-size", type=int, default=2)
    a = p.parse_args()
    state = json.loads(a.state.read_text()) if a.state and a.state.exists() else None
    plan(a.archive, state, a.batch_size, a.output)

if __name__ == "__main__":
    main()
