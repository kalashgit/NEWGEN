#!/usr/bin/env python3
"""Fail-closed, single-asset Stable Fast 3D experiment. Never auto-publish or approve.

Designed for an *offline*, independently provided SF3D checkout and model weights.
No paid service, network request, Copilot dispatch, or production cursor mutation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

from PIL import Image

SCHEMA = "last-light.sf3d-experiment.v1"
ID_RE = re.compile(r"^[a-z][a-z0-9_]{3,63}$")
RIGHTS = {"founder_original", "licensed_for_original_derivatives"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_work_order(path: Path) -> dict:
    order = json.loads(path.read_text(encoding="utf-8"))
    if order.get("schema") != SCHEMA:
        raise ValueError("work order schema mismatch")
    if not isinstance(order.get("candidate_id"), str) or not ID_RE.fullmatch(order["candidate_id"]):
        raise ValueError("invalid candidate ID")
    if order.get("source_rights") not in RIGHTS or not str(order.get("rights_evidence", "")).strip():
        raise ValueError("source rights and evidence are mandatory")
    if order.get("founder_golden_approved") is not False:
        raise ValueError("experimental assets must remain Golden-unapproved")
    if order.get("notion_work_order_url") is not None and not str(order["notion_work_order_url"]).startswith("https://"):
        raise ValueError("invalid Notion work order URL")
    source = Path(order["source_image"])
    if not source.is_absolute():
        source = path.parent / source
    source = source.resolve(strict=True)
    if source.suffix.lower() != ".png" or not source.is_file():
        raise ValueError("single isolated transparent PNG required, not a sheet")
    if digest(source) != order.get("source_sha256"):
        raise ValueError("image checksum mismatch")
    with Image.open(source) as img:
        if img.mode != "RGBA" or not (64 <= img.width <= 2048 and 64 <= img.height <= 2048):
            raise ValueError("RGBA input must be 64..2048 pixels per edge")
        alpha = img.getchannel("A")
        bounds = alpha.getbbox()
        if bounds is None:
            raise ValueError("empty input")
        opaque = sum(1 for a in alpha.get_flattened_data() if a >= 128) if hasattr(alpha, "get_flattened_data") else sum(1 for a in alpha.getdata() if a >= 128)
        if not (0.02 <= opaque / (img.width * img.height) <= 0.90):
            raise ValueError("object alpha coverage incompatible with isolated reference")
        if bounds == (0, 0, img.width, img.height):
            raise ValueError("input reaches all image edges; isolate the object first")
    return order | {"_resolved_source": str(source)}


def prepare(order_file: Path, out: Path) -> dict:
    order = read_work_order(order_file)
    if out.exists() and any(out.iterdir()):
        raise FileExistsError("output must be a new or empty candidate directory")
    out.mkdir(parents=True, exist_ok=True)
    source = Path(order.pop("_resolved_source"))
    with Image.open(source) as original:
        img = original.convert("RGBA")
        bbox = img.getchannel("A").getbbox()
        assert bbox is not None
        cut = img.crop(bbox)
        edge = max(cut.size)
        square = Image.new("RGBA", (edge, edge), (0, 0, 0, 0))
        square.alpha_composite(cut, ((edge - cut.width) // 2, (edge - cut.height) // 2))
        # SF3D expects the object to occupy most of the frame. Thumbnail()
        # never enlarges small source sprites and would leave a tiny object.
        square = square.resize((448, 448), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
        canvas.alpha_composite(square, ((512 - square.width) // 2, (512 - square.height) // 2))
        canvas.save(out / "input.png")
    manifest = {
        "schema": SCHEMA,
        "candidate_id": order["candidate_id"],
        "source_rights": order["source_rights"],
        "rights_evidence": order["rights_evidence"],
        "notion_work_order_url": order.get("notion_work_order_url"),
        "source_sha256": order["source_sha256"],
        "prepared_input_sha256": digest(out / "input.png"),
        "generator": "Stability-AI/stable-fast-3d",
        "inference_status": "NOT_RUN",
        "sprite_status": "NOT_RENDERED",
        "visual_review": "PENDING",
        "golden_approved": False,
        "gameplay_review": "PENDING",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def check_glb(path: Path) -> dict:
    data = path.read_bytes()
    if len(data) < 32 or data[:4] != b"glTF" or struct.unpack_from("<I", data, 4)[0] != 2:
        raise ValueError("invalid GLB header")
    if struct.unpack_from("<I", data, 8)[0] != len(data):
        raise ValueError("GLB size mismatch")
    json_len, json_type = struct.unpack_from("<I4s", data, 12)
    if json_type != b"JSON" or json_len < 2 or 20 + json_len > len(data):
        raise ValueError("missing GLB JSON chunk")
    gltf = json.loads(data[20:20 + json_len].decode("utf-8").strip())
    if gltf.get("asset", {}).get("version") != "2.0" or not gltf.get("meshes"):
        raise ValueError("GLB does not contain a glTF 2.0 mesh")
    if not gltf.get("buffers") or not gltf.get("bufferViews") or not gltf.get("accessors"):
        raise ValueError("GLB geometry buffer metadata missing")
    if not any(primitive.get("attributes", {}).get("POSITION") is not None
               for mesh in gltf["meshes"] for primitive in mesh.get("primitives", [])):
        raise ValueError("GLB mesh primitives missing")
    binary_offset = 20 + json_len
    if binary_offset + 8 > len(data):
        raise ValueError("GLB binary data missing")
    binary_len, binary_type = struct.unpack_from("<I4s", data, binary_offset)
    if binary_type != b"BIN\x00" or binary_offset + 8 + binary_len != len(data):
        raise ValueError("GLB binary chunk mismatch")
    if gltf["buffers"][0].get("byteLength", 0) > binary_len:
        raise ValueError("GLB geometry bytes truncated")
    return {"mesh_count": len(gltf["meshes"]), "glb_sha256": digest(path)}


def infer(out: Path, root: Path, weights: Path, seconds: int, license_verified: bool) -> dict:
    if not license_verified:
        raise ValueError("explicit SF3D license verification required")
    if not (1 <= seconds <= 600):
        raise ValueError("strict runtime budget is 1..600 seconds per asset")
    manifest_path = out / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if manifest["inference_status"] != "NOT_RUN" or manifest["golden_approved"] is not False:
        raise ValueError("cannot rerun or promote an existing candidate")
    if digest(out / "input.png") != manifest["prepared_input_sha256"]:
        raise ValueError("prepared input was modified")
    if not (root / "run.py").is_file():
        raise FileNotFoundError("offline SF3D run.py not installed")
    if not (weights / "config.yaml").is_file() or not (weights / "model.safetensors").is_file():
        raise FileNotFoundError("locally cached SF3D weights required; no implicit downloads")
    raw = out / "_raw_sf3d"
    raw.mkdir(exist_ok=False)
    argv = [sys.executable, str((root / "run.py").resolve()), str((out / "input.png").resolve()),
            "--pretrained-model", str(weights.resolve()), "--output-dir", str(raw.resolve()),
            "--texture-resolution", "1024", "--remesh_option", "none", "--batch_size", "1"]
    try:
        process = subprocess.run(argv, cwd=root, timeout=seconds, capture_output=True, text=True, check=False)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("SF3D per-asset timeout; candidate rejected") from exc
    (out / "sf3d.log").write_text((process.stdout + "\n" + process.stderr)[-32000:])
    mesh = raw / "0" / "mesh.glb"
    if process.returncode != 0 or not mesh.is_file():
        raise RuntimeError(f"SF3D failed, exit={process.returncode}; see sf3d.log")
    info = check_glb(mesh)
    shutil.copy2(mesh, out / "candidate.glb")
    manifest.update(inference_status="TECHNICAL_MESH_ONLY", sprite_status="NOT_RENDERED",
                    model_sha256=info["glb_sha256"], model_mesh_count=info["mesh_count"],
                    visual_review="PENDING", golden_approved=False)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["prepare", "infer"])
    parser.add_argument("--work-order", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--sf3d-root", type=Path)
    parser.add_argument("--weights", type=Path)
    parser.add_argument("--timeout-seconds", type=int, default=300)
    parser.add_argument("--license-verified", action="store_true")
    args = parser.parse_args()
    if args.stage == "prepare":
        if args.work_order is None:
            parser.error("--work-order required for prepare")
        result = prepare(args.work_order, args.out)
    else:
        if args.sf3d_root is None or args.weights is None:
            parser.error("--sf3d-root and --weights required for infer")
        result = infer(args.out, args.sf3d_root, args.weights, args.timeout_seconds, args.license_verified)
    print("LL_SF3D_CANDIDATE", result["candidate_id"], result["inference_status"])


if __name__ == "__main__":
    main()
