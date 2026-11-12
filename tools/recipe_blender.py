"""Blender CLI: build genuine editable geometry from a validated NEWGEN recipe.

Example:
  blender -b --factory-startup --python tools/recipe_blender.py -- \
      --recipe recipes/examples/vehicle_battery_demo.json --output build/battery
"""
from __future__ import annotations
import argparse
import json
import math
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from newgen.recipe import read_recipe


def build(recipe: dict, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)

    bpy_mats = {}
    for name, spec in recipe["materials"].items():
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = spec["rgba"]
            bsdf.inputs["Metallic"].default_value = spec["metallic"]
            bsdf.inputs["Roughness"].default_value = spec["roughness"]
        mat.diffuse_color = spec["rgba"]
        bpy_mats[name] = mat

    for part in recipe["components"]:
        size = part["size"]
        pos = part["position"]
        kind = part["primitive"]
        if kind == "box":
            bpy.ops.mesh.primitive_cube_add(size=1, location=pos)
        elif kind == "cylinder":
            bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.5, depth=1, location=pos)
        elif kind == "sphere":
            bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=0.5, location=pos)
        elif kind == "cone":
            bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=0.5, radius2=0, depth=1, location=pos)
        obj = bpy.context.object
        obj.name = part["id"]
        obj.scale = size
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        obj.rotation_euler = [math.radians(x) for x in part.get("rotation_degrees", [0, 0, 0])]
        obj.data.materials.append(bpy_mats[part["material"]])
        bevel = part.get("bevel", 0)
        if bevel:
            modifier = obj.modifiers.new(name="Recipe bevel", type="BEVEL")
            modifier.width = min(bevel, min(size) * 0.24)
            modifier.segments = 2
            obj.modifiers.new(name="Weighted normals", type="WEIGHTED_NORMAL")

    bpy.ops.wm.save_as_mainfile(filepath=str((output / (recipe["asset_id"] + ".blend")).resolve()))
    bpy.ops.export_scene.gltf(
        filepath=str((output / (recipe["asset_id"] + ".glb")).resolve()),
        export_format="GLB"
    )
    (output / "recipe_provenance.json").write_text(
        json.dumps({"schema": "newgen.recipe-run.v1",
                    "asset_id": recipe["asset_id"], "components": len(recipe["components"]),
                    "status": "TECHNICAL_CANDIDATE_NOT_GOLDEN"}, indent=2) + "\n",
        encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recipe", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    build(read_recipe(args.recipe), args.output)


if __name__ == "__main__":
    main()
