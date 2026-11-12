"""Validate genuine Blender frames and produce immutable technical atlas batches."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image

def digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def finalize(plan: dict, view_dir: Path, output: Path, run_id: str = "local") -> dict:
    if plan.get("schema_version") != 1 or plan.get("status") not in ("READY", "COMPLETE"):
        raise ValueError("Invalid planner schema")
    count = plan.get("source_count", 360)
    if not isinstance(count, int) or not 1 <= count <= 10000:
        raise ValueError("Invalid bounded source-count")
    completed = list(plan["completed_before"])
    if len(completed) + len(plan.get("selected", [])) > count:
        raise ValueError("Source completion exceeds catalog")
    output.mkdir(parents=True, exist_ok=True)
    reviews = []
    for asset in plan["selected"]:
        ident = asset["asset_id"]
        root = view_dir / ident
        metadata = json.loads((root / "render_metadata.json").read_text())
        if metadata.get("asset_id") != ident or metadata.get("source_sha256") != asset["glb_sha256"]:
            raise ValueError("Rendered model and source provenance mismatch")
        if metadata.get("frames") != 16 or metadata.get("golden_approved") is not False:
            raise ValueError("Unverified technical render metadata")
        res = metadata["resolution"]
        if res not in (128, 192, 256):
            raise ValueError("Unexpected sprite resolution")
        sheet = Image.new("RGBA", (4*res+5*4, 4*res+5*4), (0,0,0,0))
        hashes = []
        for i in range(16):
            p = root / f"{i:02d}.png"
            with Image.open(p) as source:
                source.load()
                rgba = source.convert("RGBA")
            if rgba.size != (res,res):
                raise ValueError(f"Wrong sprite dimensions {ident}/{i}")
            bounds = rgba.getchannel("A").getbbox()
            if not bounds:
                raise ValueError(f"Empty sprite {ident}/{i}")
            # Prevent atlas clipping and impossible object framing.
            if min(bounds[0], bounds[1], res-bounds[2], res-bounds[3]) < 2:
                raise ValueError(f"Clipped silhouette {ident}/{i}")
            x, y = i % 4, i // 4
            sheet.alpha_composite(rgba, (4 + x*(res+4), 4 + y*(res+4)))
            hashes.append(digest(p))
        folder = output / ident
        folder.mkdir(parents=True, exist_ok=True)
        atlas = folder / "atlas_16_headings.png"
        sheet.save(atlas, optimize=True)
        record = {
            "asset_id": ident, "source_glb_sha256": asset["glb_sha256"],
            "atlas_sha256": digest(atlas), "views": 16,
            "distinct_heading_images": len(set(hashes)),
            "renderer": "Blender Cycles CPU", "source_editable_blend_preserved_in_archive": True,
            "source_blend_size_bytes": asset["original_blend_size_bytes"],
            "status": "TECHNICAL_SPRITE_CANDIDATE",
            "f11_material_approved": False, "f12_world_scale_approved": False,
            "golden_approved": False, "gameplay_integrated": False,
        }
        (folder / "manifest.json").write_text(json.dumps(record, indent=2) + "\n")
        reviews.append(record)
        completed.append(ident)
    proposal = {
        "schema_version":1,"source_count":count,"source_plan_sha256":plan["source_plan_sha256"],
        "completed":completed,"last_run_id":str(run_id),
        "golden_approved":False, "remaining":count-len(completed),
    }
    (output / "next_state.json").write_text(json.dumps(proposal, indent=2) + "\n")
    report = {
        "run_id":str(run_id), "source_count":count, "source_plan_sha256":plan["source_plan_sha256"],
        "batch_count":len(reviews),"completed_total":len(completed),
        "remaining":count-len(completed),"generated":reviews,
        "golden_approved":False,"technical_candidate_only":True,
    }
    (output / "batch_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"FOUNDRY_BATCH_PASS count={len(reviews)} completed_total={len(completed)} remaining={report['remaining']}")
    return report

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--views", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--run-id", default="local")
    a = p.parse_args()
    finalize(json.loads(a.plan.read_text()), a.views, a.output, a.run_id)

if __name__ == "__main__":
    main()
