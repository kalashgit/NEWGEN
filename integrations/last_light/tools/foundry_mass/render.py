"""Real headless Blender technical 16-heading render from existing GLB meshes.

Outputs are review sprites only: NOT F11-baked, not F12 world-scale,
not gameplay-integrated, and never Golden approved.
"""
from __future__ import annotations
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

def scene_for(asset: dict, resolution: int, samples: int, lighting_mode: str = "legacy"):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=asset["glb_path"])
    scene = bpy.context.scene
    objects = [o for o in scene.objects if o.type == "MESH"]
    if not objects:
        raise ValueError("GLB contains no mesh")
    bpy.context.view_layer.update()
    corners = [o.matrix_world @ Vector(c) for o in objects for c in o.bound_box]
    lo = Vector(tuple(min(v[i] for v in corners) for i in range(3)))
    hi = Vector(tuple(max(v[i] for v in corners) for i in range(3)))
    dims = hi - lo
    if max(dims) <= 0 or not all(math.isfinite(v) for v in (*lo, *hi)):
        raise ValueError("GLB bounds invalid")
    if max(dims) > 100:
        raise ValueError("Unreviewed source scale beyond 100 meters")
    anchor = bpy.data.objects.new("FOUNDry_technical_origin", None)
    scene.collection.objects.link(anchor)
    for obj in list(scene.objects):
        if obj != anchor and obj.parent is None:
            obj.parent = anchor
    anchor.location = Vector((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z))
    bpy.context.view_layer.update()

    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.view_settings.view_transform = "Standard"

    world = bpy.data.worlds.new("FOUNDry_Neutral_Fill")
    world.use_nodes = True
    world.node_tree.nodes.get("Background").inputs["Color"].default_value = (0.54, 0.56, 0.58, 1) if lighting_mode == "studio" else (0.25, 0.26, 0.29, 1)
    world.node_tree.nodes.get("Background").inputs["Strength"].default_value = 0.85 if lighting_mode == "studio" else 0.5
    scene.world = world

    cam_data = bpy.data.cameras.new("FOUNDry_Iso")
    cam = bpy.data.objects.new("FOUNDry_Iso", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam_data.type = "ORTHO"
    # Fit to source bounds for diagnostic sprites only; this is deliberately
    # NOT F12 fixed 80x40 pixels-per-meter world-scale certification.
    diagonal = math.sqrt(sum(float(v) ** 2 for v in dims))
    cam_data.ortho_scale = max(0.25, diagonal * 1.55)
    cam_data.clip_end = 1500

    light_data = bpy.data.lights.new("FOUNDry_Upper_Left", "AREA")
    light = bpy.data.objects.new("FOUNDry_Upper_Left", light_data)
    scene.collection.objects.link(light)
    light_data.energy = 1800 if lighting_mode == "studio" else 450
    light_data.shape = "DISK"
    light_data.size = max(2, diagonal * 1.5)
    fill = None
    if lighting_mode == "studio":
        scene.view_settings.exposure = 0.3
        fill_data = bpy.data.lights.new("FOUNDry_Studio_Bounce", "AREA")
        fill = bpy.data.objects.new("FOUNDry_Studio_Bounce", fill_data)
        scene.collection.objects.link(fill)
        fill_data.energy = 480
        fill_data.shape = "DISK"
        fill_data.size = max(2, diagonal * 1.8)
    return scene, cam, light, fill, dims

def render_asset(asset: dict, root: Path, resolution: int, samples: int, lighting_mode: str = "legacy"):
    scene, cam, light, fill, dims = scene_for(asset, resolution, samples, lighting_mode)
    folder = root / asset["asset_id"]
    folder.mkdir(parents=True, exist_ok=True)
    target = Vector((0, 0, dims.z * 0.5))
    elevation = math.asin(0.5)  # F12-inspired 30-degree camera elevation
    for heading in range(16):
        angle = heading * math.tau / 16
        facing = Vector((math.cos(angle), math.sin(angle), 0))
        right = Vector((-math.sin(angle), math.cos(angle), 0))
        cam.location = target + facing * 8 * math.cos(elevation) + Vector((0, 0, 8 * math.sin(elevation)))
        direction = target - cam.location
        cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        # Light follows screen-space upper-left as camera changes heading.
        light.location = target + facing * 4 - right * 3 + Vector((0, 0, 7))
        light.rotation_euler = (target - light.location).to_track_quat("-Z", "Y").to_euler()
        if fill:
            fill.location = target - facing * 3 + right * 4 + Vector((0, 0, 5))
            fill.rotation_euler = (target - fill.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str((folder / f"{heading:02d}.png").resolve())
        bpy.ops.render.render(write_still=True)
    (folder / "render_metadata.json").write_text(json.dumps({
        "asset_id": asset["asset_id"], "frames": 16,
        "resolution": resolution, "samples": samples,
        "engine": "CYCLES_CPU", "lighting_mode": lighting_mode,
        "actual_heading_degrees": [i * 22.5 for i in range(16)],
        "source_sha256": asset["glb_sha256"], "diagnostic": True,
        "f11_approved": False, "f12_world_scale_approved": False,
        "golden_approved": False, "dimensions_m": list(map(float, dims)),
    }, indent=2) + "\n")
    print("FOUNDRY_RENDERED", asset["asset_id"], "16")
    
def main():
    argv = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--resolution", type=int, default=192)
    p.add_argument("--samples", type=int, default=4)
    p.add_argument("--lighting-mode", choices=("legacy", "studio"), default="legacy")
    opt = p.parse_args(argv)
    if opt.resolution not in (128, 192, 256) or not 1 <= opt.samples <= 16:
        raise ValueError("Render budget outside approved envelope")
    plan = json.loads(opt.plan.read_text())
    if plan.get("schema_version") != 1 or plan.get("status") not in ("READY", "COMPLETE"):
        raise ValueError("Invalid Foundry source plan")
    for asset in plan["selected"]:
        render_asset(asset, opt.output, opt.resolution, opt.samples, opt.lighting_mode)

if __name__ == "__main__":
    main()
