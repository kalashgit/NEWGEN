# NEWGEN Engine Adapter Contract — v1

Engine commands are configured in `config/engines.json` by the repo maintainer, not submitted through the web dashboard. Commands are **argv arrays** executed with `shell=False` and capped timeouts. Placeholders supported by the control plane: `{job_dir}`, `{stage_dir}`, `{asset_id}`, `{reference}`, `{attempt}`, `{recipe}`.

Each external adapter writes `<stage_dir>/result.json`:

```json
{
  "schema": "newgen.stage-result.v1",
  "status": "pass",
  "outputs": ["asset.glb", "asset.blend"],
  "evidence": {"method": "procedural", "recipe_version": "v1"}
}
```

Outputs must be regular, nonempty files **inside the stage directory**. The control plane records SHA-256 digests, validates GLB/Blender file signatures and rejects missing evidence.

- `sprite_2d`: initial built-in admission of founder original PNG/JPEG/WebP from the local, private `intake/`; replace with sprite generator when connected.
- `mesh_3d`: requires actual `.glb` with glTF magic.
- `model_3d`: requires actual `.glb` and editable `.blend` with valid file signatures.
- `visual_qa`: must produce `qa_report.json` in outputs with a boolean `passed`, a `metrics` object and optional `defects`. Failed QA triggers the repair engine and a bounded model-rerender retry. This is technical/visual candidate QA, never automatic Founder approval.
- `repair_3d`: must write a corrected versioned recipe or equivalent corrected engine inputs.
- `gameplay_asset`: requires at least a Godot `.tscn` and gameplay `.json` definition. Future adapters should also check collision, inventory, state machines, save/load, render layering and iPhone performance.

Engines may read the immutable admission job manifest at `{job_dir}/job.json` and stage outputs under its subfolders. No empty fake outputs, unsourced art, random external code or fabricated Golden flags.

The platform does NOT include a paid vision backend, hosted GPU, committed original source sprites, production-ready GPU executor, or remote public dashboard. These are separately authorized integrations.
