# NEWGEN — Unified Asset Intelligence Factory

A modular, **closed-loop** production platform connecting the 2D Sprite Generator, 3D Mesh Generator, component-aware 3D Modeling/Recipe Engine, independent Visual QA/Repair and Godot Gameplay Asset Factory.

**Current status:** first real local control-plane prototype; not yet an automated end-to-end mass-production asset factory.

## What's implemented

- Durable, source-hashed job admission and queue (`newgen/core.py`)
- Four configurable production-engine stages plus visual QA and recipe repair (`config/engines.json`)
- Bounded subprocess execution, artifact SHA-256 evidence and stage-specific output validation
- QA rejection and max-attempt correction logic; explicit Founder Golden and Godot/iPhone review gates
- Responsive localhost dashboard (`web/dashboard.html`) with queue, batch submissions, adapters, inspection, retries and approvals
- Declarative, allowlisted `newgen.recipe.v1` geometry language + genuine procedural Blender generator
- Preserved original LAST LIGHT procedural/experimental 3D scripts in `integrations/last_light/`
- CPU-only contract tests and GitHub Actions configuration

## Run dashboard (Python 3.11+, no additional packages)

```sh
python -m unittest discover -s tests -p "test_control_plane.py" -v
python -m newgen.server
# Open http://127.0.0.1:8765
```

Place an original PNG/JPEG/WebP in the untracked `intake/` folder, then enter its relative filename (e.g. `battery.png`) and a stable snake_case canonical asset ID in the dashboard. NEWGEN admits and hashes it. Because external mesh, model, visual QA and gameplay adapters are **not configured by default**, the worker stops explicitly at `blocked_unconfigured`, rather than inventing outputs.

```sh
# Blender-only isolated geometry experiment (requires Blender installed)
blender -b --factory-startup --python tools/recipe_blender.py -- \
  --recipe recipes/examples/vehicle_battery_demo.json --output build/battery
```

The included battery recipe is a synthetic four-component geometry demonstrator and **not** a model visually reconstructed from your original sprite. To connect the local Blender adapter to `model_3d`, configure:

```json
{"type":"external",
 "argv":["python","-m","tools.recipe_blender_adapter","--job-dir","{job_dir}","--stage-dir","{stage_dir}","--asset-id","{asset_id}"],
 "timeout_s":1800}
```

Its job requires a source-grounded, validated `{job_dir}/recipe.json` created by an upstream vision/recipe agent. The `mesh_3d` stage also needs a real adapter. Never configure paid inference or GPU calls without explicit approval.

## Documents

- [NEWGEN architecture](docs/ARCHITECTURE.md)
- [3D work handoff, original LAST LIGHT sources and next steps](docs/HANDOFF.md)
- [Engine integration contract](docs/ENGINE_CONTRACT.md)
- [Demonstration structured 3D recipe](recipes/examples/vehicle_battery_demo.json)
- [Original reconstructed and procedural LAST LIGHT code snapshot](integrations/last_light/)

## Safety and scale

Repo stays private. Original art should remain in private intake/storage, not committed unless specifically authorized. Dashboard is **localhost-only**, not a hosted service. For human approval actions, server must have a `NEWGEN_FOUNDER_TOKEN` environment variable; the dashboard prompts for the matching token only when approving. No auto-merges, no game-production changes, no provider billing.

The architecture targets reproducible, high-throughput pipelines across thousands of canonical models, but runtime, asset complexity, hardware, and quality gates prevent an honest promise of **instantaneous unlimited** production. Benchmark approved *gameplay assets*, not raw meshes.
