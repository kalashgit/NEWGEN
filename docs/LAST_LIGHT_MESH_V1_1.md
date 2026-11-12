# LAST LIGHT V1.1 mesh factory — NEWGEN integration

**Status:** isolated real procedural GLB engine; NOT a complete reference-to-animated-gameplay pipeline. All geometry is a *candidate*; founder Golden approval, visual matching, rights review and actual Godot/iPhone QA remain pending.

## Two modes

### A. One-command catalog batch (fast, mesh only)

```bash
python -m pip install -r integrations/last_light/requirements-mesh.txt
export NEWGEN_LAST_LIGHT_CATALOG=/absolute/path/to/LAST_LIGHT_4347_3D_MESH_RECIPES_V3.jsonl
python -m integrations.last_light.last_light_mesh_factory_v1_1 --input "$NEWGEN_LAST_LIGHT_CATALOG" --root build/last_light_meshes
```

Produces a `glb/` directory (4,347 GLBs if all recipes succeed), `build_manifest.csv`, `build_summary.json`, and `failures.json`. Tests should use `--limit 5` before any full batch. This batch CLI does not perform visual comparison, independent QA, animation, `.blend` export or Godot import. Source JSONL stays private in Drive / local storage, not committed to Git.

### B. NEWGEN per-reference queue adapter (one press, mesh stage only)

```bash
python -m pip install -r integrations/last_light/requirements-mesh.txt
export NEWGEN_LAST_LIGHT_CATALOG=/absolute/path/to/LAST_LIGHT_4347_3D_MESH_RECIPES_V3.jsonl
export NEWGEN_ENGINE_CONFIG="$(pwd)/config/engines.last_light_local.json"
python -m newgen.server
```

1. Put a *licensed/founder-original* reference image in `intake/` (not Git). Do not automatically download research-only images from another game's wiki.
2. In the dashboard submit an asset with the exact canonical ID `ll_0002` (1–4,347) and the local image filename. The adapter selects the corresponding V3 JSONL recipe; image content is **not inferred** by this engine.
3. The queued controller runs source intake then the mesh adapter. The adapter compares the immutable SHA-256 source hash, validates recipe/asset identity and geometry dimensions, produces `ll_0002.glb`, `mesh_report.json`, and stage `result.json`.
4. The next `model_3d` stage remains **blocked_unconfigured** unless its Blender adapter and actual recipe conversion are configured. This is intentional: never claim a candidate GLB passed independent visual/animation/gameplay QA.

For a job-specific recipe instead of the shared catalog, create the trusted `{job_dir}/mesh_recipe_v3.json`, omit `NEWGEN_LAST_LIGHT_CATALOG`, then retry the job. Do not let web requests supply arbitrary executable operator names or shell commands.

## Mapping and provenance

- `ll_0002` ↔ `asset_number=2`, `recipe_id=LL-MESH-0002`
- Reproducible deterministic procedural geometry (NumPy + Trimesh, no GPU). Materials are original approximations, *not* copied artwork.
- Generator remains separate from the worker adapter so other engines can replace it without changing the NEWGEN control plane.
- Treat `reference.source_file_page` as evidence, not an approved production asset license.
- `mesh_report.json` records actual GLB SHA-256, reference hash, recipe hash, parts, triangle count, and pending gates.
- No assets, external reference art, credentials, or paid model services are committed by this integration.

## Production gaps before full one-press factory

`image/sprite understanding → part-level recipe grounding → this mesh stage → editable riggable Blender model → 16-view reference comparison/repair → skeleton/animation states → original material authoring → collision/LOD → Godot scene and behaviors → game-specific functional tests → founder Golden → iPhone QA`.

This V1.1 geometry factory *cannot* generate plausible skeletons or gameplay animations for 4,347 unrelated objects by itself. A later `animation` adapter and downstream Godot scene builder are separate milestones.

## Automated tests

```bash
python -m unittest discover -s tests -p 'test_control_plane.py' -v
python -m unittest discover -s tests -p 'test_last_light_mesh_adapter.py' -v
```

Test passes mean valid procedural GLB creation and interface contract—not golden-quality 3D reconstruction.
