# LAST LIGHT — Stable Fast 3D image-to-sprite experiment

**Status: opt-in experimental integration. No GPU inference or founder visual approval has occurred.**

This isolated lane does not change the scheduled procedural generator, source cursors,
Notion canonical asset registry, Copilot dispatch, billing, or playable `main.tscn`.
Do not call it a replacement until artists compare the resulting *64×64 sprites*.

## One engine, one original asset per work order

The original reference should be a single complete, clean, rights-cleared object
in an RGBA PNG, preferably a near-orthographic view with transparent margins.
Do **not** submit a contact sheet, copy of Project Zomboid art, or externally
owned product logo. The reference image may not be redistributed publicly merely
because the resulting mesh is new.

Example `work_order.json` (replace checksum and values with real verified data):

```json
{
  "schema": "last-light.sf3d-experiment.v1",
  "candidate_id": "vehicle_battery_sf3d_01",
  "source_rights": "founder_original",
  "rights_evidence": "Founder-created isolated original sprite, source privately archived",
  "source_image": "vehicle_battery_original.png",
  "source_sha256": "REPLACE_WITH_REAL_64_CHARACTER_SHA256",
  "notion_work_order_url": "https://www.notion.so/REPLACE_WITH_REAL_WORK_ORDER",
  "founder_golden_approved": false
}
```

```bash
python tools/foundry_sf3d_experiment.py prepare \
  --work-order path/to/work_order.json --out build/sf3d/vehicle_battery_sf3d_01
```

The input is checksum-verified, isolated, alpha-checked and normalized to a
512×512 transparent reference. The manifest stays `NOT_RUN` until GPU inference.

## Inference is opt-in, local, and bounded

Install the **official** `Stability-AI/stable-fast-3d` project separately with its
compatible Python/CUDA dependencies. The model weights must already be cached
locally in a folder containing `config.yaml` and `model.safetensors`.
Read and verify the upstream [Stability AI Community License](https://github.com/Stability-AI/stable-fast-3d/blob/main/LICENSE.md),
including its registration condition for commercial use. Do not commit licensed
weights into the game repository. A suitable GPU with approximately 6 GB+ VRAM
is recommended for pilot inference; real performance/cost must be measured.

```bash
python tools/foundry_sf3d_experiment.py infer \
  --out build/sf3d/vehicle_battery_sf3d_01 \
  --sf3d-root /path/to/stable-fast-3d \
  --weights /path/to/previously-downloaded-sf3d-weights \
  --timeout-seconds 300 --license-verified
```

`infer` launches exactly one upstream input with `--batch_size 1`, captures logs,
rejects missing weights/invalid GLB/timeout/failed exit, records the GLB checksum,
and never edits the procedural engine or advances an autonomous cursor. Running
this on a rented GPU could incur hosting costs: there is no automatic paid dispatch.

## Blender → 16 views → original sprites

With real Blender installed, run:

```bash
blender -b --factory-startup -t 2 --python tools/foundry_sf3d_render.py -- \
  --candidate build/sf3d/vehicle_battery_sf3d_01/candidate.glb \
  --output build/sf3d/vehicle_battery_sf3d_01/render

python tools/foundry_sf3d_sprite_qa.py \
  --render build/sf3d/vehicle_battery_sf3d_01/render \
  --out build/sf3d/vehicle_battery_sf3d_01/sprites
```

This should output: `editable_candidate.blend` (mesh/material/light/camera source),
16 128px RGBA orthographic renders, 16-heading 64×64 atlas, `inventory_64.png`,
contact sheet and JSON technical QA. Supply `--baseline <existing-contact-sheet.png>`
to produce an explicit side-by-side review image.

## Admission gates before replacing existing production

1. **Source:** verified original or properly licensed input, Notion work order,
   exact image SHA and separate candidate identity; never automatically create
   a canonical ID or merge duplicates by position number.
2. **Geometry:** recognizable independently from 8–16 angles, plausible hidden
   surfaces, components separate where interaction/animation demands, clean UVs,
   no severe texture seams or hallucinated back geometry.
3. **Sprites:** real alpha, distinct view hashes, upper-left fixed lighting,
   material and pixel consistency, no inventory props inside a container,
   grounded color/wear, readable at actual 64×64 gameplay size.
4. **Gameplay:** verified collision footprint, optional opening animations,
   readable world scale, Godot 2D sprite import, memory/atlas and iPhone FPS.
5. **Visual A/B:** compare at least six different families against the current
   factory and record actual acceptance counts and failure causes. Technical
   pass is **not** a Golden pass; only explicit founder review can promote.
6. **Persistence:** archive source image if rights allow, local model weights
   provenance (not weights), GLB, editable `.blend`, 16 sprites, QA and manifest
   into authenticated durable storage before any scheduled publication.

The GitHub workflow for this lane runs only **CPU contract tests**, so a PR can
prove safety without installing CUDA or downloading multi-GB model weights.
Real SF3D inference, actual Blender rendering and artistic comparison remain
separate measured gates until a GPU runner and original isolated image are ready.
