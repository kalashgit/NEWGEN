"""Optional local Blender subprocess adapter for the NEWGEN model_3d stage.

Requires an already validated, founder-source-grounded recipe in the job directory.
Never infers recipes from filename and never claims art approval.
"""
from __future__ import annotations
import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from newgen.recipe import read_recipe


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--job-dir", type=Path, required=True)
    p.add_argument("--stage-dir", type=Path, required=True)
    p.add_argument("--asset-id", required=True)
    a = p.parse_args()
    recipe_path = a.job_dir / "recipe.json"
    recipe = read_recipe(recipe_path)
    if recipe["asset_id"] != a.asset_id:
        raise ValueError("Recipe identity differs from admitted asset")
    blender = os.environ.get("NEWGEN_BLENDER_BIN") or shutil.which("blender")
    if not blender:
        raise RuntimeError("Blender executable unavailable")
    a.stage_dir.mkdir(parents=True, exist_ok=True)
    source = Path(__file__).resolve().parent / "recipe_blender.py"
    command = [blender, "--background", "--factory-startup", "--python", str(source),
               "--", "--recipe", str(recipe_path), "--output", str(a.stage_dir)]
    run = subprocess.run(command, capture_output=True, text=True, timeout=1600, check=False)
    (a.stage_dir / "blender.log").write_text((run.stdout + "\n" + run.stderr)[-100000:], encoding="utf-8")
    if run.returncode:
        raise RuntimeError("Blender failed with exit code " + str(run.returncode))
    stem = recipe["asset_id"]
    outputs = [stem + ".glb", stem + ".blend", "recipe_provenance.json"]
    for name in outputs:
        if not (a.stage_dir / name).is_file():
            raise RuntimeError("Missing generated output: " + name)
    (a.stage_dir / "result.json").write_text(json.dumps({
        "schema": "newgen.stage-result.v1", "status": "pass", "outputs": outputs,
        "evidence": {"generator": "newgen.recipe_blender.v1", "source": str(recipe_path),
                     "golden_approved": False}
    }, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
