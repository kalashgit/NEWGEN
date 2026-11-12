# LAST LIGHT → PHYSICAL OBJECT INTELLIGENCE
## Strategic vision and engineering handoff
**Prepared:** 11 November 2026  
**Audience:** Next development worker / Claude Code / Codex  
**Decision:** Prioritize understanding and reconstructing **existing physical objects**, not autonomous invention of new products.

## 1. Executive directive
Build a reusable **Physical Object Intelligence Engine** that takes authorized 2D reference images, identifies the visible parts of an existing object, infers plausible hidden geometry with explicit uncertainty, creates a structured construction recipe, builds an editable 3D model, renders it from matched viewpoints, and improves it through measured visual comparison. LAST LIGHT is the first production and evaluation environment; games are the initial application, not the technology's limit.

**North star:** *Observe → Understand → Decompose → Reconstruct → Render → Compare → Correct → Verify.*

The system should eventually reconstruct component-aware digital representations suitable for visualization, digital twins, simulation preparation, AR/VR and robotics datasets. Do not claim engineering-grade mechanical or physical accuracy from an image alone; require measurements, multiple views and external validation for those uses.

## 2. Why this matters
A conventional image-to-3D generator creates a visually plausible mesh. The target system preserves **construction knowledge**: components, proportions, material assignments, spatial relationships, joints, assumptions, evidence, recipe history and quality outcomes. This can be reused across object families and exported to different downstream applications.

## 3. Current LAST LIGHT foundation (verify before acting)
- Repository: `kalashgit/last-light-godot`.
- Existing Foundry includes procedural Blender geometry, GLB and editable `.blend` outputs, isometric directional sprite rendering, manifest/atlas checks and GitHub Actions-based technical tests.
- Relevant draft work: PR #111 (distinct sprite intake and eight technical models) and PR #112 (opt-in Stable Fast 3D experiment and 16-view QA). Both were previously draft/unmerged; **re-check live status and exact SHAs**.
- Previous eight-image TripoSR CPU pilot yielded real GLBs, but the visual reconstructions were not good enough for Golden approval. Technical validity does not equal visual fidelity.
- The source research catalog includes many references, variants and duplicates. **Do not treat reference count as unique 3D model count.** Canonical identities must be reconciled.
- Existing game target: original 2.5D isometric Godot experience on iPhone, primarily rendered with sprites produced from 3D masters. Preserve `res://main.tscn` and playable baseline.
- Art policy: Golden approval is an explicit founder decision; technical QA, visual approval and Godot/iPhone acceptance are separate gates.

## 4. Proposed architecture
1. **Authorized reference intake** — original image(s), checksum, provenance, rights, canonical identity, object family.
2. **Visual observation agent** — list visible components, outlines, colors, material cues, perspective, occlusions and uncertainties; distinguish observed from inferred details.
3. **Object decomposition** — construct a hierarchical component graph, spatial relations, approximate dimensions and likely assembly; record alternate hypotheses.
4. **Recipe compiler** — versioned, validated JSON schema with an allowlist of geometric operations, materials, transforms, connections and output requirements. Avoid arbitrary generated code execution.
5. **Geometry engine** — Blender Python constructs editable multi-part models; reusable family primitives; export `.blend`, `.glb`, metadata and thumbnails.
6. **Visual evaluator** — compare reference and matched-camera renders for silhouette, proportions, components, color/material, occlusion and readability; use independent review where possible.
7. **Correction agent** — identify localized defects, modify relevant recipe components, rerender and preserve the best measured iteration; bounded retries and fail-closed review.
8. **Knowledge library** — store verified recipes, reusable templates, failures, correction deltas and evidence without confusing hypotheses with confirmed facts.
9. **Application exporters** — LAST LIGHT sprites and Godot asset metadata first; later interoperable scene formats and digital-twin/simulation annotations.

## 5. Minimum data contract
Each object record must include:
- `canonical_asset_id`, `family`, `source_refs`, `source_sha256`, `rights_status`, `recipe_version`.
- `observations[]` with `visible_evidence`, `confidence`, `image_region` and source-view reference.
- `inferences[]` with `hypothesis`, `uncertainty`, `alternatives` and `validation_needed`.
- `components[]` with primitive/mesh operation, dimensions, transforms, parent, material, symmetry, joints and attachment points.
- `coordinate_system`, `units`, `scale_basis`, `pivot`, `camera_calibration`, `render_profile`.
- `materials[]`, `texture_sources`, `originality_status`, `variants[]`, `states[]`.
- `evaluation` containing matched-view metrics, human findings, defects, correction history and acceptance status.
- `outputs` with reproducible artifact hashes, `.blend`, `.glb`, sprite sheets and logs.

**Critical rule:** A single sprite cannot prove unseen surfaces, internal structure, actual mass, strength or manufacturability. Label those as assumptions; do not hallucinate verified facts.

## 6. Golden visual and gameplay standards
- Original LAST LIGHT visual identity: 2.5D isometric, grounded realistic materials, crisp pixel edges, upper-left lighting, consistent scale, restrained color, subtle wear, transparent backgrounds.
- World assets: directional renders as required (existing Foundry targets 16 views); inventory icons typically 64×64.
- Isolated object policy: do not add unrelated contents or props to empty shelves, cabinets, drawers, crates or containers.
- A Golden 3D model and sprites are **not yet a gameplay asset**. Gameplay compilation adds identity, placement footprint, collisions, interactions, item/container properties, state transitions, depth sorting, persistence and mobile optimization.
- Do not infer gameplay balance values solely from image appearance. Use approved family rules and design data.

## 7. Immediate validation program
**Phase A — One-object end-to-end:** Use the authorized founder vehicle-battery reference already in the intake archive. Produce actual observation evidence, a component graph, validated JSON recipe, editable Blender model, GLB, matched-view render, 16-direction sheet, native-size comparison and a defect/correction log. Do not substitute unrelated artwork.

**Phase B — Generalization:** Test a canteen and a cast-iron skillet (or other authorized, distinct families). Show that the engine handles different shapes without bespoke hardcoding for every item.

**Phase C — Reusable families:** Build a verified primitive/component library for cans, bottles, boxes, cabinets, seating, doors, tools and mechanical assemblies. Demonstrate that family variants reuse a stable master rather than inflate unique-model counts.

**Phase D — Gameplay bridge:** Compile five representative Golden assets into Godot: cabinet, chair, food item, vehicle battery and door. Test spawn, render order, collision, interaction, state changes and save/reload in the five-building lab, then test on iPhone.

## 8. Acceptance gates and measurements
- **Source fidelity:** real authorized input pixels inspected; source checksums and evidence preserved.
- **Recipe validity:** schema and allowlisted-operation validation; no untrusted code execution.
- **Geometry:** actual multi-part 3D topology, scale/pivot correctness, editable source, reproducible export and Godot import.
- **Visual:** independently assessed silhouette, component count/placement, matched-view shape and materials; compare before/after correction; no silent regression.
- **Generalization:** holdout assets from unseen families and difficult viewpoints; no reliance only on memorized templates.
- **Reliability:** bounded retries, idempotent jobs, durable claims, exact provenance and artifact integrity.
- **Cost:** compute time and marginal cost **per visually approved asset**, not per generated mesh.
- **Approval:** `technical_candidate` → `founder_visual_approved` → `godot_integrated` → `iphone_verified`; never collapse statuses.

Do not invent quantitative success thresholds after seeing results. Pre-register a small evaluation set and pass/fail criteria before each benchmark.

## 9. Cost, safety and workflow boundaries
Current disclosed cash budget: **€6.50**. Target €0 infrastructure spending initially. Prefer existing public-repository GitHub Actions capacity and CPU Blender work, subject to actual quotas. No paid GPU, inference API, VPS, Copilot credit burn, merge, deployment or production asset promotion without explicit authorization. Keep founder reference artwork in authorized private storage; do not publish restricted source pixels or third-party IP in a public repository. Preserve the existing Godot playable baseline.

## 10. What the next worker should deliver
1. Audit current GitHub branches, relevant PRs, Foundry tools and tests; report exact head SHAs and blockers.
2. Write a brief architecture decision record and a versioned object-recipe schema.
3. Implement a **small, real end-to-end** reference-to-recipe-to-Blender-to-render-to-correction pipeline.
4. Generate downloadable, independently inspectable artifacts for the battery pilot and two holdout families.
5. Produce a visual comparison contact sheet, defects, revision history, metrics, compute/cost ledger and reproducible commands.
6. Create an isolated draft PR with CI tests. Do not merge or promote assets.
7. Clearly distinguish **implemented**, **tested**, **visually approved**, **gameplay integrated**, and **future research**.

## 11. Explicit non-goals for the next sprint
- Autonomous invention of new products.
- Claiming real-world mechanical/structural certification from visual reconstruction.
- Mass-generating thousands of unreviewed meshes.
- Replacing the existing game or switching to runtime 3D gameplay.
- Spending the €6.50 without approval.

## 12. Long-term research roadmap
**R1 — Visual reconstruction:** consistent, high-quality component-aware 3D from 2D references.  
**R2 — Multi-view physical representation:** dimensions, joints, assembly graphs, uncertainty-aware inferred geometry and reference measurements.  
**R3 — Digital twins:** real object measurements, behavior/state data, external sensor inputs and validated fidelity.  
**R4 — Simulation-ready assets:** mass/friction/constraints from measured or validated data; robotics/AR/VR export.  
**R5 — Scalable object knowledge infrastructure:** reusable verified object-family representations, provenance, evaluation history and enterprise interfaces.

**Strategic statement:** LAST LIGHT is the proving ground. The larger product is an intelligence system for reconstructing and understanding existing physical objects—not merely an image-to-mesh generator.
