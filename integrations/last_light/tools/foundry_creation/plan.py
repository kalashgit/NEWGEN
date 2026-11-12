"""Deterministic 512-source mass-creation queue. No AI/model billing.

Eight editable procedural archetypes × 64 reproducible geometry variants.
Each source is still a technical candidate until independent artistic acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

VERSION = "last-light-foundry-procedural-v1"
ARCHETYPES = (
    ("F01", "industrial_locker"),
    ("F01", "tool_chest"),
    ("F01", "warehouse_shelf"),
    ("F01", "utility_cabinet"),
    ("F08", "portable_generator"),
    ("F08", "vending_machine"),
    ("F08", "street_dumpster"),
    ("F04", "raised_planter"),
)
VARIANTS = 64
TOTAL = len(ARCHETYPES) * VARIANTS
CATALOG_SHA256 = hashlib.sha256(json.dumps({
    "version": VERSION, "archetypes": ARCHETYPES, "variants": VARIANTS
}, separators=(",", ":"), sort_keys=True).encode()).hexdigest()

def catalog():
    # Round robin to produce different silhouettes in every small batch.
    for variant in range(VARIANTS):
        for family, archetype in ARCHETYPES:
            ident = f"ll_generated_{archetype}_{variant:03d}"
            seed = int(hashlib.sha256(f"{VERSION}:{ident}".encode()).hexdigest()[:8], 16)
            yield {
                "asset_id": ident,
                "family": family,
                "archetype": archetype,
                "variant": variant,
                "seed": seed,
                "geometry_contract": VERSION,
                "golden_approved": False,
            }

def make_plan(state, batch_size):
    if not isinstance(batch_size, int) or not 1 <= batch_size <= 4:
        raise ValueError("Batch must contain 1–4 model sources")
    items = list(catalog())
    ids = [x["asset_id"] for x in items]
    if len(ids) != TOTAL or len(set(ids)) != TOTAL:
        raise ValueError("Source catalog duplicate or missing ID")
    completed = []
    if state is not None:
        if (state.get("schema_version") != 1
            or state.get("catalog_sha256") != CATALOG_SHA256
            or state.get("total") != TOTAL
            or not isinstance(state.get("completed"), list)):
            raise ValueError("Stale, invalid, or mismatched catalog cursor")
        completed = state["completed"]
        if completed != ids[:len(completed)]:
            raise ValueError("Cursor must be exact ordered prefix, not arbitrary skip list")
    selected = items[len(completed):len(completed)+batch_size]
    return {
        "schema_version": 1, "catalog_sha256": CATALOG_SHA256,
        "total": TOTAL, "completed_before": completed,
        "selected": selected,
        "remaining_before": TOTAL-len(completed),
        "status": "COMPLETE" if not selected else "READY",
        "canonical_promoted": False, "golden_approved": False,
        "real_ai_calls": 0,
        "generator_kind": "DETERMINISTIC_BLENDER_PROCEDURAL_SOURCE",
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=2)
    args = parser.parse_args()
    state = json.loads(args.state.read_text()) if args.state and args.state.exists() else None
    result = make_plan(state, args.batch_size)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+"\n")
    print("FOUNDRY_CREATE_PLAN", result["status"], len(result["selected"]), result["remaining_before"])

if __name__=="__main__":
    main()
