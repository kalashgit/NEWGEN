# NEWGEN — Mesh Sprint v0.3.1 (Geometry Overhaul)

**Status: executable technical candidate factory, not visual/Golden production approval.**

A CPU-first Python compiler for versioned, original, parameterized 3D game asset recipes. It uses NumPy for geometry and Trimesh to export self-contained `.glb` files. **No paid API, cloud GPU, Blender process, online references, or AI call is made per asset.** Optional Blender rendering and F11/F12 review belong to the existing specialized downstream Foundry tools.

## Install and run

```bash
python -m pip install -r engines/mesh_sprint/requirements.txt
python engines/mesh_sprint/factory.py --demo 24 --out output/quick --workers 2
python engines/mesh_sprint/verify.py --root output/quick
python engines/mesh_sprint/factory.py --demo 2000 --out output/benchmark --workers 4
python engines/mesh_sprint/factory.py --input engines/mesh_sprint/examples/catalog_example.csv --out output/real --workers 4
pytest -q tests/test_factory.py tests/test_verify.py
```

`--demo N` creates **N deterministic synthetic geometry variants**, NOT N distinct catalog object designs and NOT N founder-approved game assets. This is a speed and structural regression, not a content-production claim. Every GLB/JSON sidecar is written atomically, and a rerun skips entries only if both the recipe hash and output SHA-256 match. Repaired corrupted outputs rebuild. Duplicate asset IDs reject before processing. Invalid/unsupported families fail closed rather than being misrepresented as the named item.

## V0.1 baseline benchmark (historical), measured on the assistant's container

- Hardware: isolated 5-logical-CPU environment; 4 worker processes; Python 3.13, NumPy and Trimesh 4.11.1.
- Fresh synthetic run: **2,000 candidate GLBs in 2.1284 seconds**, zero compiler failures; **2,000 unique GLB hashes** after fixing the initial duplicated-geometry defect.
- This satisfies the **synthetic compiler throughput** target of 2,000 outputs in 900 seconds on the benchmark environment. The 15-minute claim does **not** yet cover 2,000 item-specific detailed recipes, QA renders, human visual approvals, texture baking, collision authoring, 16-direction animation, Godot game integration, or asset sourcing.
- Geometry uniqueness is derived from deterministic shape/profile transforms. It is **not the same as 2,000 independent semantic game items**. Only 12 authored families are implemented.

See `report.json` from the selected run. Performance varies with mesh complexity, storage, material count, machine, and downstream QA.

## Canonical input

CSV, JSONL or JSON list. One record = one asset. Required: `asset_id`, plus `family` from 12 supported families or explicit `parts` JSON geometry recipe. Optional: `seed`, `variant`, `recipe_version`, `source_reference`.

Supported families: `avocado`, `backpack`, `axe`, `armor`, `shelf`, `bottle`, `barrel`, `crate`, `helmet`, `medkit`, `chair`, `canister`.

The V0.1 `parts` mode supports five base operators (expanded with four advanced V0.2 operators below): `box` (`location`, `dimensions`), `ellipsoid` (`location`, `radii`, optional `boxiness`), `lathe` (`profile` as `[z,r]` rings), `tube` (`points`, `radius`), and `polygon_prism` (`outline_xz`, `depth`). Every part also declares a material key. Validate the geometry visually before promoting. **This is a minimal independent recipe interface, not a blanket claim of compatibility with the existing Drive V2 schema.** A schema adapter and further geometry operators are required.

A complete example is in `engines/mesh_sprint/examples/custom_recipe.jsonl`. No unapproved name-only fallback or guessed category mapping is permitted for the 4,347 master-catalog rows.

## Outputs and safeguards

- `models/{asset_id}.glb` — actual 3D scene geometry and material vertex colors.
- `metadata/{asset_id}.json` — digest, geometry metrics, recipe version, provenance, candidate status.
- `manifest.jsonl`, `report.json`, `failures.jsonl` — export log and truthful coverage counts.
- `verify.py` — independent import/geometry/collision-free structural checks; not a visual evaluator.

Asset status: `generated_candidate`, `golden_approved=false`, `identity_verified=false`. Empty storage props are empty. Do not copy or trace Project Zomboid visual assets. Source references are research/provenance, not a license to redistribute their artwork.

## Development roadmap to genuine 4,347 catalog assets

1. **Recipe intake:** Map the master catalog to canonical IDs, reference images and original identity evidence. Parse/validate the Drive recipe V2 schema and reject missing/unknown geometries; prefer family-specific construction recipes.
2. **Geometry execution:** Add spline/sweep, bevels, sewn fabric, tapered surfaces, knife/axe-head edge contours, strap seams, hollow interiors, functional hinges and modular armor shaping. Avoid generic box approximations for objects such as backpacks.
3. **Closed-loop QA:** Render fixed 8/16 headings in persistent Blender workers; compare outlines and material regions against independently authorized design briefs, flag identity failures, revise *only* failing components. Keep author approvals separate.
4. **Throughput gate:** Benchmark *2,000 different catalog recipes*, including staging, GLB export, technical QA, thumbnails, and manifest packaging, on the intended hardware. Report p50/p95 latency, peak RSS, unique identifiers, failure rate, true end-to-end wall time.
5. **Gameplay gate:** Export anchored Godot 2:1 isometric sprites, materials, mesh scaling/collisions and held/world variants; validate in a real Godot runtime and iPhone Xogot. Existing `main.tscn` and saved gameplay remain untouched until founder review.

## Integration

This feature is deliberately isolated under `engines/mesh_sprint/`. It neither changes `main.tscn` nor takes over the existing `tools/foundry_mass/` and `tools/foundry_creation/` pipelines. The user must explicitly approve any promotion, gameplay integration or merge.

Open-source references: [Trimesh](https://github.com/mikedh/trimesh) (MIT license; used as dependency, not vendored), [Trimesh GLB export API](https://trimesh.org/trimesh.exchange.gltf.html), [Blender background automation](https://docs.blender.org/manual/en/dev/advanced/command_line/). Review the actual current licenses before vendoring or redistributing any external code or artwork.

## V0.2 geometry overhaul (stacked draft)

Every one of the 12 family presets now uses original shaped geometry, instead of the V0.1 simple silhouettes. See [GEOMETRY_OVERHAUL_V02.md](GEOMETRY_OVERHAUL_V02.md). Added 
`quality_geometry.py` with variable-section lofts, tapered axe bevels, fabric ribbons, prismatic diagonal beams and full sample-family construction templates. Custom recipes may use `superloft`, `ribbon`, `beam`, and `forge_blade`.

```bash
python engines/mesh_sprint/factory.py --demo 12 --out output/v02_pilot --workers 2 --require-detailed
python engines/mesh_sprint/verify.py --root output/v02_pilot
python -m pip install Pillow
python engines/mesh_sprint/preview.py --glb output/v02_pilot/models/benchmark_00001_backpack.glb --out output/backpack.png
python -m pytest tests -q
```

**The speed test does not include CPU preview rendering, advanced material baking, visual QA or Godot import.** The candidate status is unchanged, and the current catalog V2 schema still needs a proper adapter.


## V0.3 NEWGEN master-engine integration

The NEWGEN branch adds original procedural PBR textures and normal maps, cleanup of
collapsed triangles, denser curved volume geometry, hollow protective vest geometry,
chamfered beams, and canonical LAST LIGHT V2 recipe ingestion. The V2 adapter is
strict and **does not** substitute primitive boxes for missing geometry operators.

```bash
python -m pip install -r engines/mesh_sprint/requirements.txt
python engines/mesh_sprint/factory.py --demo 12 --workers 2 --out output/newgen_mesh_candidates
python engines/mesh_sprint/verify.py --root output/newgen_mesh_candidates
python engines/mesh_sprint/qa_multiview.py --root output/newgen_mesh_candidates --out output/review --max 5 --views 8
python engines/mesh_sprint/factory.py --input engines/mesh_sprint/examples/canonical_v2_sample.jsonl --out output/v2_test --workers 1 --require-detailed
python -m pytest -q tests
```

The source catalog V2 schema is in `contracts/last_light_v2.schema.json`.
The NEWGEN module interface is in `engine_registry/mesh_sprint.json`; the source LAST LIGHT repo is not modified.

The normal map and diffuse preview are not proof of PBR fidelity or full gameplay
quality. Only explicit founder review can promote candidate assets to Golden.
