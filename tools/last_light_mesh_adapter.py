"""NEWGEN mesh_3d adapter for LAST LIGHT V3 catalog recipes (candidate GLBs only).

Run by the existing NEWGEN controller's *trusted, configured argv*. The controller
always verifies the GLB signature, scope and hash after this adapter returns.
No generated object is visually verified or Golden-approved by this stage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
from pathlib import Path

from integrations.last_light.last_light_mesh_factory_v1_1 import build

SCHEMA = "LAST_LIGHT_3D_MESH_RECIPE_V3_CANDIDATE"
ID_PATTERN = re.compile(r"ll_(\d{4})\Z")


class RecipeMismatch(ValueError):
    """Prevent running a catalog recipe on the wrong admitted reference."""


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def catalog_record(path: Path, asset_number: int) -> dict:
    if not path.is_file() or path.is_symlink():
        raise FileNotFoundError("Missing trusted V3 JSONL catalog: " + str(path))
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            doc = json.loads(line)
            if doc.get("asset_number") == asset_number:
                return doc
    raise RecipeMismatch(f"Asset #{asset_number} absent from catalog")


def validate_recipe(rec: dict, asset_id: str) -> None:
    match = ID_PATTERN.fullmatch(asset_id)
    if not match:
        raise RecipeMismatch("LAST LIGHT jobs require asset_id ll_0001 through ll_4347")
    if rec.get("schema") != SCHEMA or rec.get("asset_number") != int(match.group(1)):
        raise RecipeMismatch("V3 recipe schema or numeric identity mismatch")
    if rec.get("recipe_id") != f"LL-MESH-{int(match.group(1)):04d}":
        raise RecipeMismatch("Recipe identity mismatch")
    bbox = rec.get("coordinates_and_scale", {}).get("estimated_bbox_xyz_m")
    if not isinstance(bbox, list) or len(bbox) != 3 or any(
        not isinstance(v, (int, float)) or not math.isfinite(v) or not .0005 <= v <= 60
        for v in bbox
    ):
        raise ValueError("Invalid estimated dimensions")
    parts = rec.get("mesh_construction", {}).get("part_graph")
    if not isinstance(parts, list) or not 1 <= len(parts) <= 128:
        raise ValueError("Expected 1..128 candidate parts")
    for part in parts:
        if not isinstance(part, dict) or not isinstance(part.get("operator"), str):
            raise ValueError("Missing structured part operator")
        for key in ("center_normalized", "extent_normalized"):
            vector = part.get(key)
            if not isinstance(vector, list) or len(vector) != 3 or any(
                not isinstance(x, (int, float)) or not math.isfinite(x) or abs(x) > 4
                for x in vector
            ):
                raise ValueError("Invalid part coordinate: " + key)


def run(job_dir: Path, stage_dir: Path, asset_id: str, catalog: Path | None = None) -> dict:
    job_dir = job_dir.resolve(strict=True)
    stage_dir = stage_dir.resolve()
    if not stage_dir.is_relative_to(job_dir):
        raise ValueError("Stage directory must be below job directory")
    job = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
    if job.get("schema") != "newgen.job.v1" or job.get("asset_id") != asset_id:
        raise RecipeMismatch("Adapter invoked with wrong NEWGEN job identity")
    match = ID_PATTERN.fullmatch(asset_id)
    if not match or not 1 <= int(match.group(1)) <= 4347:
        raise RecipeMismatch("Expected LAST LIGHT job id ll_0001..ll_4347")

    # Re-check admitted source bytes. Never fetch external third-party art automatically.
    intake = Path(os.environ.get("NEWGEN_INTAKE_ROOT", "intake")).resolve()
    relative_ref = Path(job.get("reference", ""))
    if relative_ref.is_absolute() or ".." in relative_ref.parts:
        raise RecipeMismatch("Invalid reference path")
    source = (intake / relative_ref).resolve()
    if not source.is_relative_to(intake) or not source.is_file() or sha256(source) != job.get("source_sha256"):
        raise RecipeMismatch("Source image path/hash differs from NEWGEN admission")

    if catalog is not None:
        rec = catalog_record(catalog, int(match.group(1)))
    else:
        recipe_file = job_dir / "mesh_recipe_v3.json"
        if not recipe_file.is_file() or recipe_file.is_symlink():
            raise FileNotFoundError("No per-job V3 recipe; set NEWGEN_LAST_LIGHT_CATALOG")
        rec = json.loads(recipe_file.read_text(encoding="utf-8"))
    validate_recipe(rec, asset_id)
    stage_dir.mkdir(parents=True, exist_ok=True)
    target = stage_dir / (asset_id + ".glb")
    report = build(rec, str(target))
    if not target.is_file() or target.read_bytes()[:4] != b"glTF":
        raise ValueError("Generator did not produce a valid GLB header")
    if report.get("loaded_components", 0) < 1 or report.get("triangles", 0) < 1:
        raise ValueError("Generated GLB has no usable triangles")
    source_status = rec.get("reference", {}).get("copyright_status", "UNREVIEWED")
    assessment = {
        "schema": "newgen.last-light-mesh-report.v1",
        "asset_id": asset_id,
        "source_sha256": job["source_sha256"],
        "recipe_id": rec["recipe_id"],
        "recipe_sha256": hashlib.sha256(json.dumps(rec, sort_keys=True).encode()).hexdigest(),
        "glb_sha256": sha256(target),
        "geometry": report,
        "visual_comparison": "NOT_PERFORMED",
        "source_rights_status": source_status,
        "founder_golden_approved": False,
        "pipeline_scope": "MESH_STAGE_ONLY",
        "needs_downstream": ["model_3d", "visual_qa", "repair_3d", "gameplay_asset", "animation", "founder_approval"],
    }
    (stage_dir / "mesh_report.json").write_text(json.dumps(assessment, indent=2) + "\n", encoding="utf-8")
    (stage_dir / "result.json").write_text(json.dumps({
        "schema": "newgen.stage-result.v1", "status": "pass",
        "outputs": [target.name, "mesh_report.json"],
        "evidence": {"engine": "last-light-procedural-v1.1", "recipe_id": rec["recipe_id"],
                     "glb_sha256": assessment["glb_sha256"],
                     "visual_qa_passed": False, "golden_approved": False},
    }, indent=2) + "\n", encoding="utf-8")
    return assessment


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--job-dir", type=Path, required=True)
    p.add_argument("--stage-dir", type=Path, required=True)
    p.add_argument("--asset-id", required=True)
    p.add_argument("--catalog", type=Path, default=None)
    a = p.parse_args()
    catalog = a.catalog or (Path(os.environ["NEWGEN_LAST_LIGHT_CATALOG"]) if os.environ.get("NEWGEN_LAST_LIGHT_CATALOG") else None)
    run(a.job_dir, a.stage_dir, a.asset_id, catalog)


if __name__ == "__main__":
    main()
