# NEWGEN — LAST LIGHT 3D Research Handoff

Mission: understand and reconstruct EXISTING physical objects from founder-authored reference imagery using image perception → part-level recipe → Blender procedural modeling → 16-direction render → visual comparison → bounded recipe correction → gameplay integration. Do not prioritize inventing new products.

Original project: https://github.com/kalashgit/last-light-godot

Legacy prototype source: draft PR #112 at `4f39aced29a7b3a3b5c7086ebbbaf7fa2ef21de5`, draft PR #111 at `91128ba48de60458c0d8dd3c211866d33aab63e1`.

The prior SF3D experiment has an offline opt-in adapter and Blender renderer but **no verified actual SF3D model inference**; model weights are gated. Earlier CPU TripoSR GLBs were experimental and NOT Golden. Do not invent Golden approvals.

Production goal: ~4,327 remaining referenced assets (canonical unique masters require deduplication), 16-view isometric sprites, editable .blend, actual .glb, Godot resources, gameplay properties, collision, physical scale, state/interaction, independent visual QA, save/load and iPhone acceptance.

Founder original visual standard: upper-left light, crisp isometric pixel art, realistic materials, consistent scale, one object per reference cell, empty storage remains empty, original fictional branding.

New repo design: four plug-in engines `sprite_2d`, `mesh_3d`, `model_3d`, `gameplay_asset`, plus QA/repair feedback. These imported scripts are preserved as **opt-in research starting points**, not pre-connected live cloud engines. Keep private art and artifacts private; never merge/deploy or bill without approval. Founder stated budget €6.50.
