# NEWGEN

NEWGEN is the master framework for connecting the independent game-making engines: prompt / 2D sprite generation, 3D construction recipes, 3D meshing, visual correction, 3D modeling, and game-asset packaging. Each engine is integrated as an isolated module with explicit inputs, outputs, QA evidence and approval gates. **This repository is not yet a unified finished game-making engine.**

## Registered module: Mesh Sprint V0.3 (experimental)

The `engines/mesh_sprint` module was imported from LAST LIGHT's isolated Mesh Sprint V0.2 development branch, then upgraded with:

- Original procedural PBR base-color and normal textures, UV coordinates and metallic/roughness material assignments.
- Subdivided/curved silhouettes, a hollow vest shell, chamfered support members and bounded organic surface relief.
- Deterministic, audited real GLB export with collapsed-face repair and independent Trimesh re-import.
- Canonical V2 construction recipe intake, parent/child geometry transforms, source provenance and blocked-operator failures.
- Multi-angle actual GLB review renders and immutable unapproved review status.

See [the Mesh Sprint engine documentation](engines/mesh_sprint/README.md), [the engine registry](engine_registry/mesh_sprint.json), and [integration contract](docs/MESH_SPRINT_INTEGRATION.md).

**Do not confuse synthetic GLB file throughput with reference-accurate finished game assets.** No module may auto-approve Golden assets, merge into a game, or publish third-party source artwork.
