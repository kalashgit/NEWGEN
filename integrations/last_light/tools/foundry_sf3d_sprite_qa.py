#!/usr/bin/env python3
"""Review-gated 16-heading F12 sprite packer with optional A/B baseline sheet."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


def pack(render: Path, out: Path, baseline: Path | None = None) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    atlas = Image.new("RGBA", (64 * 4, 64 * 4), (0, 0, 0, 0))
    defects = []
    hashes = []
    metrics = []
    for heading in range(16):
        src = render / f"heading_{heading:02d}.png"
        if not src.is_file():
            raise FileNotFoundError(f"missing required directional frame: {src.name}")
        with Image.open(src) as opened:
            if opened.mode != "RGBA":
                raise ValueError("directional renders must have real transparency")
            img = opened.resize((64, 64), Image.Resampling.LANCZOS)
        alpha = img.getchannel("A")
        values = alpha.get_flattened_data() if hasattr(alpha, "get_flattened_data") else alpha.getdata()
        occupancy = sum(1 for a in values if a >= 128) / 4096
        bounds = alpha.getbbox()
        metrics.append({"heading": heading, "coverage": round(occupancy, 4), "bounds": bounds})
        if bounds is None or occupancy < .025:
            defects.append(f"EMPTY_OR_TINY_HEADING_{heading:02d}")
        if occupancy > .80:
            defects.append(f"OVERSIZE_HEADING_{heading:02d}")
        hashes.append(hashlib.sha256(img.tobytes()).hexdigest())
        atlas.alpha_composite(img, ((heading % 4) * 64, (heading // 4) * 64))
        if heading == 0:
            img.save(out / "inventory_64.png")
    if len(set(hashes)) < 8:
        defects.append("INSUFFICIENT_VIEW_DIVERSITY")
    atlas.save(out / "world_atlas_16.png")
    preview = atlas.resize((1024, 1024), Image.Resampling.NEAREST)
    preview.save(out / "contact_sheet_16.png")
    if baseline is not None:
        with Image.open(baseline) as old:
            compare = Image.new("RGBA", (2048, 1024), "#1e1f22")
            compare.alpha_composite(old.convert("RGBA").resize((1024, 1024), Image.Resampling.NEAREST))
            compare.alpha_composite(preview, (1024, 0))
            compare.save(out / "baseline_vs_sf3d.png")
    result = {"status": "TECHNICAL_PASS_VISUAL_PENDING" if not defects else "TECHNICAL_FAIL",
              "golden_approved": False, "visual_review": "PENDING_FOUNDER",
              "not_a_style_approval": True, "sprite_count": 16,
              "distinct_frame_hashes": len(set(hashes)), "defects": defects,
              "per_view": metrics}
    (out / "sprite_qa.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    if defects:
        raise ValueError("sprite QA rejected: " + ", ".join(defects))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--baseline", type=Path)
    a = parser.parse_args()
    result = pack(a.render, a.out, a.baseline)
    print("LL_SF3D_16_SPRITES_PASS_VISUAL_PENDING", result["distinct_frame_hashes"])


if __name__ == "__main__":
    main()
