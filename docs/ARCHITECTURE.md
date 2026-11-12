# NEWGEN — System Architecture and Engineering Milestones

```
Original 2D reference / sprites
    ↓ [1] 2D SPRITE ENGINE or verified founder-original intake
    ↓ [2] 3D MESH ENGINE (GLB geometry candidate)
    ↓ [3] 3D MODEL/RECIPE ENGINE (hierarchy, materials, editable BLEND)
    ↓ [4] VISUAL QA (matched reference and 16-view diagnostic renders)
         ↳ fail: targeted RECIPE REPAIR → rebuild → compare (bounded)
    ↓ [5] GAME ASSET FACTORY (Godot 2D isometric atlas, components, states, collision, placement, save identity)
    ↓ independent technical QA → FOUNDER GOLDEN approval → Godot/iPhone QA
```

All engines must be opt-in swappable adapters; share immutable source ID + checksum, versioned recipe/part registry, actual artifact hashes and evidence. A stage can be technically valid while failing visual acceptance. A cloud GPU only speeds inference, it does not fix bad geometry. Never automatically promote GOLDEN or modify LAST LIGHT main.

Control plane needs: persistent bounded queue, explicit states, paid-provider approvals, per-stage timeout, max QA attempts, worker lease/locks, batches, cost logging, independent evaluation, abort/retry, dashboard with references, previews and founder approval. Engine binaries run in isolated workers, not via web-request-submitted shell commands.

Prioritize five proof objects: battery, cabinet, chair, food and door. Only scale after real Godot import, collision, interaction and iPhone performance. Throughput must be benchmarked per accepted gameplay asset; near-instantaneous unlimited output is not guaranteed.
