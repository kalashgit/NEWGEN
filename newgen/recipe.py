"""Validate declarative NEWGEN object recipes without executing arbitrary AI-authored code."""
from __future__ import annotations
import json
import math
import re
from pathlib import Path

PRIMITIVES = {"box", "cylinder", "sphere", "cone"}
NAME_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")


class RecipeError(ValueError):
    pass


def triple(value: object, label: str, minimum: float | None = None, maximum: float = 1000.0) -> list[float]:
    if not isinstance(value, list) or len(value) != 3:
        raise RecipeError(label + " must contain three numbers")
    if not all(isinstance(x, (float, int)) and not isinstance(x, bool) and math.isfinite(x) for x in value):
        raise RecipeError(label + " contains invalid numbers")
    if minimum is not None and any(x <= minimum for x in value):
        raise RecipeError(label + " must exceed " + str(minimum))
    if any(abs(x) > maximum for x in value):
        raise RecipeError(label + " is outside permitted bounds")
    return [float(x) for x in value]


def validate(recipe: dict) -> dict:
    if not isinstance(recipe, dict) or recipe.get("schema") != "newgen.recipe.v1":
        raise RecipeError("Invalid recipe schema")
    if not isinstance(recipe.get("asset_id"), str) or not NAME_RE.fullmatch(recipe["asset_id"]):
        raise RecipeError("Invalid canonical asset ID")
    if recipe.get("units") != "meters":
        raise RecipeError("Only meters are accepted")
    components = recipe.get("components")
    materials = recipe.get("materials")
    if not isinstance(components, list) or not 1 <= len(components) <= 256:
        raise RecipeError("Expected 1..256 components")
    if not isinstance(materials, dict) or not 1 <= len(materials) <= 64:
        raise RecipeError("Expected 1..64 materials")
    for key, mat in materials.items():
        if not isinstance(key, str) or not NAME_RE.fullmatch(key) or not isinstance(mat, dict):
            raise RecipeError("Malformed material")
        color = mat.get("rgba")
        if not isinstance(color, list) or len(color) != 4 or not all(
            isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and 0 <= x <= 1
            for x in color
        ):
            raise RecipeError("Invalid material color")
        for field in ("metallic", "roughness"):
            value = mat.get(field)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or not 0 <= value <= 1:
                raise RecipeError("Invalid " + field)
    ids = set()
    for part in components:
        if not isinstance(part, dict):
            raise RecipeError("Component must be an object")
        ident = part.get("id")
        if not isinstance(ident, str) or not NAME_RE.fullmatch(ident) or ident in ids:
            raise RecipeError("Invalid or duplicate component identifier")
        ids.add(ident)
        if part.get("primitive") not in PRIMITIVES:
            raise RecipeError("Unsupported primitive")
        if part.get("material") not in materials:
            raise RecipeError("Unknown referenced material")
        triple(part.get("size"), "size", 0.0001, 100.0)
        triple(part.get("position"), "position", maximum=100.0)
        triple(part.get("rotation_degrees", [0, 0, 0]), "rotation_degrees", maximum=360.0)
        bevel = part.get("bevel", 0.0)
        if not isinstance(bevel, (int, float)) or not math.isfinite(bevel) or not 0 <= bevel <= 2:
            raise RecipeError("Invalid bevel")
    return recipe


def read_recipe(path: Path) -> dict:
    return validate(json.loads(path.read_text(encoding="utf-8")))
