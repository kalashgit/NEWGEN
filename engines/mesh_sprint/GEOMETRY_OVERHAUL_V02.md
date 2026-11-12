# LAST LIGHT — Mesh Sprint V0.2 Geometry Overhaul

**State: experimental high-speed geometry candidates, NOT Golden game assets.**

## What changed from V0.1

V0.1 tested synthetic throughput, but the resulting silhouettes were recognizably poor. V0.2 replaces **all 12 old family builders** with separate original procedural constructions. It is not a name-based generator and it does not infer a new catalog identity from a sprite image. Every model is built as three-dimensional mesh geometry.

| Family | Modeled geometry / preserved constraints |
|---|---|
| Avocado | Pear-shaped longitudinal half; convex skin back; real exposed rind and flesh annuli; recessed pit and modeled seed |
| Backpack | Variable-volume soft-body loft, protruding front pocket, formed zipper tracks, fabric ribbon shoulder straps, top handle, side pouches and seams |
| Axe | Curved tapered wooden haft; dimensioned forged head with front/back cheeks and thinning cutting bevel; metal eye/socket; visible edge |
| Armor | Anatomical taper, separate chest plates, reinforced shoulders, fabric harness straps, webbing, side fasteners and empty utility pouches |
| Shelf | Real steel uprights, tray return lips, under-shelf supports, diagonal rear beams, bolted feet; **no stored contents** |
| Bottle | Blown-glass profile, neck, rim, label, cap; no fluid model |
| Barrel | Rolled cylinder, four reinforcing ribs, closed sheet-metal top, weld seam; no stored contents |
| Crate | Four corner posts, discrete slatted walls with gaps, base, open **empty** interior |
| Helmet | Thin curved shell with open underside, brim, collar/ridge details and chin straps |
| Medkit | Sewn soft-volume bag, raised medical cross, closure and handle |
| Chair | Shaped seat and upholstery, actual angled leg/back posts and separate back slats |
| Canister | Sculpted jerrycan with embossed flutes, clearance through handle and separately constructed filler cap |

### Reusable advanced operators

Four geometry operators are available to authored `parts` recipes beyond legacy box / ellipsoid / lathe / tube / polygon_prism:

- `superloft`: ordered `(z, width_half, depth_half, center_y)` sections, optional `center_x`, variable cross-section exponent; capped body
- `ribbon`: ordered 3D path and varying widths, solid thickness and smooth authored transitions
- `beam`: oriented prism connecting endpoints with real thickness
- `forge_blade`: double-sided section loft, independent top/bottom heights and taper thickness, including near-zero sharpened profile

The compiler loads the sibling geometry library from its verified local path, so a standalone entry point and GitHub Actions/Python test harness resolve the same code. Operators fail closed on invalid/nonfinite dimensions, too many sections, out-of-order profiles, and self-inconsistent geometry. `--require-detailed` rejects custom recipes consisting exclusively of primitive boxes/ellipsoids. Even advanced custom recipes remain `custom_recipe_unreviewed` until evaluated.

### Comparison evidence

The exact V0.1 GLBs and newly built V0.2 GLBs are rendered using the same orthographic camera and a depth-buffered CPU preview, with no image-generation model. See `five_family_before_after.png`. Higher polygon counts are not scored as artistic correctness; judge identity, construction, silhouettes and missing elements in the images. The current tools do not compare to the canonical sprites automatically.

### Measured throughput (synthetic only)

Command:

```bash
python engines/mesh_sprint/factory.py --demo 2000 --out /tmp/v02-fresh --workers 4
python engines/mesh_sprint/verify.py --root /tmp/v02-fresh
python -m pytest tests -q
```

Observed run in the assistant's CPU environment: **2,000 actual GLBs / 5.0501 s** with four worker processes; 2,000 distinct byte hashes; independent file/geometry re-import 2,000/2,000, zero structural errors; **38 automated tests pass**. Comparison to V0.1's 2.1284 s has different file families/geometries and does not establish a controlled normalized performance comparison. GLB file uniqueness does not prove 2,000 unrelated identities.

These throughput timings exclude high-resolution material baking, multiple renders for all 2,000 assets, visual model evaluation, physics/collision generation, Godot integration, and any 4,347-item catalog ingestion. Therefore the **2,000 finished gameplay assets in 15 min requirement remains unproven**.

### QA is not Golden approval

All results have `golden_approved=false`, `review_state=generated_candidate`, `visual_qa=not_tested`, `gameplay_qa=not_tested`. Material zones are vertex-color only, not photorealistic UV/PBR textures. No Blender or real Godot runtime is available in the current benchmark container. Watertightness, interior reachability, rigging, and sprite-source silhouette fidelity are **not** certified here.

### Next work required

1. Integrate actual **4,347-item canonical V2 recipes**, source anchors and legal provenance; reject semantic mismatches.
2. Material/UV pipeline: consistent albedo, roughness, normal maps, correct tangent space, believable fabric/wood/steel/organic microtexture.
3. Multiview shape QA: fixed-camera render 8 or 16 headings, silhouette/feature comparisons to independently verified original source briefs, validate part contact and cavity geometry.
4. Automated defect localization, bounded recipe correction, holdout evaluation and fail/review queue.
5. Godot/Xogot gameplay QA: anchored 2:1 sprites, collisions and scale, equipped/held versions, sensible LODs and iPhone performance.
6. Stress test **2,000 distinct actual catalog recipes** including all QA, rather than synthetic variations.

**Integration policy:** Isolated draft branch/PR only. Do not merge, deploy, promote recipes or mark any asset Golden without founder review. Do not alter `main.tscn`, save data, or existing F12 world-scale visual standards.
