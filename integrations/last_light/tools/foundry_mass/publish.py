"""Validate + copy technical candidates into a *separate* GitHub review branch.

This does not grant Golden approval or touch the default branch.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

IDENT = re.compile(r"ll_[a-z0-9_]{2,90}\Z")

def stage(source: Path, destination: Path) -> int:
    report=json.loads((source / "batch_report.json").read_text())
    state=json.loads((source / "next_state.json").read_text())
    if (report.get("technical_candidate_only") is not True or report.get("golden_approved") is not False
        or state.get("golden_approved") is not False or state.get("schema_version") != 1):
        raise ValueError("Unapproved technical-candidate provenance contract violated")
    generated=report.get("generated")
    if not isinstance(generated,list) or len(generated) != report.get("batch_count") or len(generated)>4:
        raise ValueError("Invalid batch count")
    existing=destination/"foundry_mass/state.json"
    prior=json.loads(existing.read_text()) if existing.exists() else {
        "schema_version":1,"source_plan_sha256":state["source_plan_sha256"],"completed":[]}
    if prior.get("schema_version") != 1 or prior.get("source_plan_sha256") != state["source_plan_sha256"]:
        raise ValueError("Source revision/cursor mismatch")
    old=prior.get("completed")
    new=state.get("completed")
    ids=[x.get("asset_id") for x in generated]
    if not isinstance(old,list) or not isinstance(new,list) or new != old+ids or len(set(new)) != len(new):
        raise ValueError("Stale, repeated or invalid cursor progression")
    if len(new)>360 or report.get("completed_total") != len(new) or report.get("remaining")!=360-len(new):
        raise ValueError("Invalid completed/remaining counts")
    if not generated:
        return 0
    # Perform all validation before writing any outputs.
    for entry in generated:
        ident=entry["asset_id"]
        if not IDENT.fullmatch(ident) or entry.get("golden_approved") is not False:
            raise ValueError("Invalid asset identity/approval")
        target=destination/"foundry_candidates"/ident
        if target.exists():
            raise ValueError("Never overwrite existing archived candidate")
        atlas=source/ident/"atlas_16_headings.png"
        meta=source/ident/"manifest.json"
        if not atlas.is_file() or not meta.is_file():
            raise ValueError("Missing candidate files")
        if hashlib.sha256(atlas.read_bytes()).hexdigest()!=entry["atlas_sha256"]:
            raise ValueError("Candidate atlas checksum mismatch")
        if json.loads(meta.read_text())!=entry:
            raise ValueError("Candidate manifest mismatch")
    for entry in generated:
        ident=entry["asset_id"]
        target=destination/"foundry_candidates"/ident
        target.mkdir(parents=True)
        for name in ("atlas_16_headings.png","manifest.json"):
            shutil.copyfile(source/ident/name, target/name)
    existing.parent.mkdir(parents=True,exist_ok=True)
    existing.write_text(json.dumps(state,indent=2)+"\n")
    reports=destination/"foundry_mass/reports"
    reports.mkdir(parents=True,exist_ok=True)
    runid=report.get("run_id")
    if not isinstance(runid,str) or not re.fullmatch(r"[0-9]{1,18}",runid):
        raise ValueError("Invalid workflow run ID")
    (reports/f"{runid}.json").write_text(json.dumps(report,indent=2)+"\n")
    print("FOUNDRY_PUBLISH_STAGED",len(generated),len(new))
    return len(generated)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--destination",type=Path,required=True)
    a=p.parse_args()
    stage(a.source,a.destination)

if __name__=="__main__":
    main()
