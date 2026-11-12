#!/usr/bin/env python3
"""Run in Blender background: native editable source and 16 fixed-camera sprites.

blender -b --factory-startup --python tools/foundry_sf3d_render.py -- \
    --candidate build/sf3d/<id>/candidate.glb --output build/sf3d/<id>/render

The resulting 16 PNGs are *technical review images*, never Golden art.
"""
import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    if not args.candidate.is_file() or args.candidate.suffix.lower() != ".glb":
        raise FileNotFoundError("verified SF3D GLB required")
    args.output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(args.candidate.resolve()))
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not meshes:
        raise RuntimeError("empty imported mesh")
    for mesh in meshes:
        if not mesh.data.vertices:
            raise RuntimeError("zero-vertex object")

    bpy.context.view_layer.update()
    points = [mesh.matrix_world @ Vector(corner) for mesh in meshes for corner in mesh.bound_box]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    span = hi - lo
    largest = max(span)
    if not math.isfinite(largest) or largest < 1e-5:
        raise ValueError("degenerate model bounds")
    center = (lo + hi) / 2
    center.z = lo.z
    root = bpy.data.objects.new("LL_Original_Candidate_Rotation_Pivot", None)
    bpy.context.collection.objects.link(root)
    scale = 1.8 / largest
    for mesh in meshes:
        # Preserve each imported object's world-space transform and material assignment.
        original_matrix = mesh.matrix_world.copy()
        mesh.parent = root
        mesh.matrix_world = Matrix.Translation(-center) @ original_matrix
    root.scale = (scale, scale, scale)
    bpy.context.view_layer.update()

    world = bpy.data.worlds.new("LL_Neutral_World")
    bpy.context.scene.world = world
    world.use_nodes = True
    world.node_tree.nodes.get("Background").inputs[0].default_value = (0.28, 0.32, 0.38, 1)
    world.node_tree.nodes.get("Background").inputs[1].default_value = 0.6

    camera_data = bpy.data.cameras.new("LL_2_1_Orthographic_Camera")
    camera = bpy.data.objects.new("LL_2_1_Orthographic_Camera", camera_data)
    bpy.context.collection.objects.link(camera)
    target = Vector((0, 0, 0.9))
    # Equal X/Y azimuth, 35.264-degree elevation: true 2:1 isometric projection.
    camera.location = (4.0, -4.0, 4.9)
    direction = target - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 3.0
    bpy.context.scene.camera = camera

    lamp_data = bpy.data.lights.new("LL_Upper_Left_Key", type="AREA")
    lamp = bpy.data.objects.new("LL_Upper_Left_Key", lamp_data)
    bpy.context.collection.objects.link(lamp)
    lamp.location = (-3.5, -4.0, 7.0)
    lamp.rotation_euler = (Vector((0, 0, 0.8)) - lamp.location).to_track_quat("-Z", "Y").to_euler()
    lamp_data.energy = 450
    lamp_data.shape = "DISK"
    lamp_data.size = 4.0

    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.film_transparent = True
    scene.render.resolution_x = 128
    scene.render.resolution_y = 128
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "Standard"
    if hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = 32
    for heading in range(16):
        root.rotation_euler.z = math.radians(heading * 22.5)
        scene.render.filepath = str((args.output / f"heading_{heading:02d}.png").resolve())
        bpy.ops.render.render(write_still=True)
    root.rotation_euler.z = 0
    # Blender saves the editable geometry, material nodes, camera, lights, and pivot.
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str((args.output / "editable_candidate.blend").resolve()), compress=False)
    print("LL_SF3D_BLENDER_16_PASS", len(meshes), flush=True)


if __name__ == "__main__":
    main()
