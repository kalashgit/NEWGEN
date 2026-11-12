# NEWGEN Mesh Sprint V0.3 Integration Contract

## Intent

The mesh compiler is a **worker engine** within the future NEWGEN master. The master will eventually call independent sprite, construction-recipe, mesh, texture, validation and game-asset workers. This draft does NOT claim they are already connected.

## Inputs

- Stable original asset IDs; NEVER infer original design from an asset name alone.
- Versioned construction recipe: canonical LAST LIGHT V2 JSONL or explicit operator parts.
- Source-reference rights and inspection status are evidence fields, NOT permission to copy artwork.
- Declared node geometry and transforms, optional material PBR parameters.
- Unsupported operators raise errors; no silent primitive substitution.

## Outputs

- `models/{asset_id}.glb`: actual textured mesh from the supplied geometry.
- `metadata/{asset_id}.json`: SHA256, triangle count, material/UV details, canonical row, PBR, review warnings, and approval flags.
- `manifest.jsonl`, `report.json`, `failures.jsonl`: deterministic batch results.
- Multi-angle `*_views.png` and `review_manifest.json`: CPU previews, **not** source-sprite visual QA.

## Integration rules

1. Execute only reviewed/candidate recipes in a sandboxed worker. Do not call LLM/vision from inside the high-speed deterministic compiler.
2. Strict input validation and geometry auditing before GLB export. Failed assets go into a review queue.
3. Preserve the exact source sprite, original identifiers and construction-recipe lineage in orchestrator metadata; never assert inferred back-side geometry as observed.
4. Scene geometry normals, PBR textures and geometry checks are technical QA only. Semantic quality needs controlled 8/16-angle comparison with source images and human truth.
5. Future mesh-to-model agent must preserve part identity and emptiness of containers. Game-asset packaging must produce scale, LOD, pivot, collision and runtime compatibility separately.
6. Golden approval requires the founder's explicit action; assets are `generated_candidate` by default.

## Known limitations

- UVs are deterministic planar projections, not hand-authored island unwrapping; seams can occur.
- PBR textures are original procedural microstructure, not photogrammetric material captures.
- Empty space/attachment annotations from V2 are recorded as warnings, not physically proved by this compiler.
- The 4,347 source catalog is not bulk-ingested yet. Unseen operation coverage remains unknown.
- Only twelve illustrated family presets are available; no pretrained general mesh reconstruction model is connected.
- Real-time Godot integration and device performance remain untested.
