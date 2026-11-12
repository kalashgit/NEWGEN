# NEWGEN closed-loop V0.4 — executable, candidate-only

## Actual four-stage workflow

1. **Recipe architect:** Reads an *explicit original* text/design contract and creates a versioned deterministic recipe. The first three curated briefs are avocado, backpack, and axe. This is not source-sprite understanding or full 4,347-item V2 authoring; that is the next input needed.
2. **Vision-based defect detector:** Renders *actual GLB triangles* then analyzes segmentation, disconnected foreground islands, colored recognition markers, edge complexity, and silhouette bounds with OpenCV. If a sprite PNG is supplied, optional normalized silhouette IoU is measured. These image heuristics are **not a VLM** and do not establish semantic fidelity.
3. **Corrective 3D modeler:** Applies component-specific bounded geometry additions in metres (cut/pit details, leather webbing, engraved metal, grip wrappings), exports GLBs, re-renders, compares scores, and retains before/after evidence. If the quality screen fails, no game package is issued.
4. **Game-asset packager:** Exports full PBR GLB, two independently reimported geometry-clustered LODs, convex hull file, interim Godot box collider scene, eight *static* directional transparent renders, a transparent inventory image, and provenance/status metadata.

Every stage consumes the previous stage's actual artifact. No Golden promotion; no silent fallback for unsupported families; no model-hallucinated original art. During runs, each asset retains `iteration_0`, `iteration_1`, `qa.json`, `recipe.json`, and `asset_manifest.json`.

### Run

```bash
pip install -r engines/mesh_sprint/requirements.txt
pip install opencv-python-headless
python engines/mesh_sprint/closed_loop.py --out output/closed_loop
python -m pytest -q tests
```

Pass `--reference-dir ./refs` with owned `avocado.png`, `backpack.png`, `axe.png` to enable *silhouette-only* comparison. Reference PNG images should be original or rights-cleared. Missing / unmatched image does not pretend to be verified. All packaged Godot scenes use paths like `res://assets/NG-DEMO-AXE-001/model/NG-DEMO-AXE-001_LOD0.glb`; copy the generated `assets/` directory to the Godot project root.

### Explicit limitations

- The current three sample recipes are **curated demo contracts**, not 4,347 inspected sprites. No independent pretrained image-description or VLM model is installed; the detector is bounded OpenCV shape/feature screening only.
- LODs are automatic vertex clustering, not artist-reviewed UV/normal retopology. Wearable deformation, animations, actual pickup inventory events, and accurate collisions are not completed.
- Godot .tscn files are generated but Godot runtime import has **not** been tested on this runner. Box collisions are interim and must be verified in-game.
- Image edge-density success is an experimental engineering regression metric, **not evidence of artistic quality**. No source-sprite fidelity or founder Golden approval has been granted.
- This 3-model end-to-end test is not a full 2,000 asset / 15 minute production run.

### Next agent handoff

- Feed the approved, original LAST LIGHT sprite sets + canonical V2 recipes and identity-linked source evidence.
- Connect a real licensed/local vision-language model to produce semantic defect descriptions (tested against human-labeled holdouts).
- Add physically accurate collision generation, Godot/Xogot runtime headless acceptance and independent texturing/UV/animation QA before Golden stage.
- Maintain branch isolation; founder must explicitly authorize a merge into NEWGEN main.
