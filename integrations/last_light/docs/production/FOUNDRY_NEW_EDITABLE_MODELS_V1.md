# Foundry AI — Genuine new editable Blender asset source factory V1

This is a production candidate, not Golden-approved art. It creates **new geometry source files** with original procedural recipes, not just 2.5D renders of the prior 360 masters.

## Continuous execution
- On GitHub Actions default branch, the scheduler runs hourly at minute 08 UTC (best effort).
- Creates two NEW distinct editable 3D masters per scheduled batch, each with a source GLB and SHA-256 provenance report; PR test creates one.
- Generates 16 genuine Blender Cycles isometric diagnostic views and checks PNG alpha, object framing, atlas authenticity and per-source checksums.
- Stores every successful batch as an **unpublished draft GitHub Release** containing editable .blend, exported .glb, material assignments, production metadata and an atlas. A protected worktree advances the ordered cursor on the isolated branch foundry/generated-sources-v1 only *after* archive success. Failed batches repeat source IDs rather than falsely marking them completed.
- The catalogue consists of 8 archetypes with 64 seeded variants each (512 total): industrial lockers, tool chests, warehouse shelves, utility cabinets, portable generators, vending machines, street dumpsters, raised planters.
- Jobs stop creating duplicates once all 512 catalog identities are completed.

## Distinguish the 3 automation levels
1. **Automated processing of old assets:** existing 360-GLB-to-sprite pipeline.
2. **Autonomous creation of new source geometry:** this PR, using deterministic procedural Blender recipes. No AI-model calls or model API usage required, and new editable Blender geometry is genuinely generated.
3. **AI-driven creative engineering / quality refinement:** STILL NOT ACTIVE. Needs a permitted Codex/Claude coding-agent login on a VPS or paid API key, a controlled sandbox, and independent review. OpenMausBot remains optional orchestration; no server is provisioned here.

## Quality and honesty
The models use parametric proportions, constructed multi-part geometry, and surface material assignments. They are not comparable to professionally sculpted detailed hero assets until individually reviewed. Exported textures are material candidates; F11 professional PBR calibration and F12 fixed world scale aren't established. Game readability, collisions, actual player interactions, rights and iPhone testing remain Golden gates. Never promote to main gameplay, or call them finished without signed review.

## Safety and cost
Repository is presently public; standard GitHub-hosted Actions runners are free for public repositories, but storage/release limits, rate limits and abuse prevention still apply. Schedules may delay. No Vercel deployment, paid model inference, cloud VPS, secrets or production merges are performed by this workflow. Any external provider/paid agent requires explicit user authorization.

## Acceptance
- Unit contract tests prove unique identities, replay-safe cursor, reproducible seeds, tamper rejection, ZIP source assembly.
- PR must pass a REAL Blender source generation of a sample locker, GLB export, 16 heading previews, Pillow atlas verification, source bundle integrity.
- Post-merge production readiness requires an authentic scheduled run with a nonpublished release and independently verified branch state.
