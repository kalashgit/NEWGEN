"""Pure CPU contract tests: NO GPU, network, model download or paid credits."""
from __future__ import annotations

import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image, ImageDraw

test_dir = Path(__file__).resolve().parent
repo_root = test_dir.parents[1] if test_dir.name == "foundry_sf3d" else test_dir
sys.path.insert(0, str(repo_root / "tools" if (repo_root / "tools").is_dir() else repo_root))
import foundry_sf3d_experiment as sf
import foundry_sf3d_sprite_qa as sprites


def make_triangle_glb(path: Path) -> None:
    vertex_blob = struct.pack("<9f", 0, 0, 0, 1, 0, 0, 0, 1, 0)
    gltf = {
        "asset": {"version": "2.0"},
        "buffers": [{"byteLength": len(vertex_blob)}],
        "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": len(vertex_blob)}],
        "accessors": [{"bufferView": 0, "componentType": 5126, "count": 3,
                       "type": "VEC3", "min": [0, 0, 0], "max": [1, 1, 0]}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "mode": 4}]}],
        "nodes": [{"mesh": 0}], "scenes": [{"nodes": [0]}], "scene": 0,
    }
    json_blob = json.dumps(gltf).encode()
    json_blob += b" " * ((4 - len(json_blob) % 4) % 4)
    chunks = struct.pack("<I4s", len(json_blob), b"JSON") + json_blob
    chunks += struct.pack("<I4s", len(vertex_blob), b"BIN\x00") + vertex_blob
    path.write_bytes(b"glTF" + struct.pack("<II", 2, 12 + len(chunks)) + chunks)


class SF3DContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.image = self.root / "single.png"
        img = Image.new("RGBA", (128, 128))
        ImageDraw.Draw(img).ellipse((24, 16, 104, 110), fill=(143, 78, 32, 255))
        img.save(self.image)
        self.order = {
            "schema": sf.SCHEMA, "candidate_id": "test_skull_01",
            "source_rights": "founder_original", "rights_evidence": "Original test fixture",
            "source_image": "single.png", "source_sha256": sf.digest(self.image),
            "founder_golden_approved": False,
        }
        self.order_file = self.root / "order.json"
        self.write_order()

    def write_order(self):
        self.order_file.write_text(json.dumps(self.order))

    def test_isolated_prepare_is_staged_and_unapproved(self):
        result = sf.prepare(self.order_file, self.root / "candidate")
        self.assertEqual(result["inference_status"], "NOT_RUN")
        self.assertFalse(result["golden_approved"])
        with Image.open(self.root / "candidate/input.png") as prepared:
            self.assertEqual(prepared.size, (512, 512))

    def test_no_rights_evidence_fails_closed(self):
        self.order["rights_evidence"] = ""
        self.write_order()
        with self.assertRaises(ValueError):
            sf.prepare(self.order_file, self.root / "candidate")

    def test_no_automatic_founder_approval(self):
        self.order["founder_golden_approved"] = True
        self.write_order()
        with self.assertRaises(ValueError):
            sf.prepare(self.order_file, self.root / "candidate")

    def test_tampered_source_rejected(self):
        self.order["source_sha256"] = "0" * 64
        self.write_order()
        with self.assertRaises(ValueError):
            sf.prepare(self.order_file, self.root / "candidate")

    def test_no_full_sheet_input(self):
        Image.new("RGBA", (128, 128), (1, 2, 3, 255)).save(self.image)
        self.order["source_sha256"] = sf.digest(self.image)
        self.write_order()
        with self.assertRaises(ValueError):
            sf.prepare(self.order_file, self.root / "candidate")

    def test_no_duplicate_candidate_directory(self):
        sf.prepare(self.order_file, self.root / "candidate")
        with self.assertRaises(FileExistsError):
            sf.prepare(self.order_file, self.root / "candidate")

    def test_inference_requires_offline_weights_and_license(self):
        sf.prepare(self.order_file, self.root / "candidate")
        with self.assertRaises(ValueError):
            sf.infer(self.root / "candidate", self.root, self.root, 30, False)
        with self.assertRaises(FileNotFoundError):
            sf.infer(self.root / "candidate", self.root, self.root, 30, True)

    def test_offline_adapter_accepts_valid_mocked_sf3d_output(self):
        sf.prepare(self.order_file, self.root / "candidate")
        engine = self.root / "engine"
        engine.mkdir()
        (engine / "run.py").write_text("# mocked; not executed\n")
        weights = self.root / "weights"
        weights.mkdir()
        (weights / "config.yaml").write_text("# mock\n")
        (weights / "model.safetensors").write_bytes(b"fake")

        def generate(argv, **kwargs):
            self.assertEqual(argv[argv.index("--batch_size") + 1], "1")
            output = Path(argv[argv.index("--output-dir") + 1]) / "0"
            output.mkdir(parents=True)
            make_triangle_glb(output / "mesh.glb")
            return mock.Mock(returncode=0, stdout="mock inference\n", stderr="")

        with mock.patch.object(sf.subprocess, "run", side_effect=generate) as invoked:
            result = sf.infer(self.root / "candidate", engine, weights, 30, True)
        self.assertEqual(invoked.call_count, 1)
        self.assertEqual(result["inference_status"], "TECHNICAL_MESH_ONLY")
        self.assertFalse(result["golden_approved"])
        self.assertTrue((self.root / "candidate/candidate.glb").is_file())

    def test_invalid_glb_header_rejected(self):
        (self.root / "bad.glb").write_bytes(b"NOT GLB")
        with self.assertRaises(ValueError):
            sf.check_glb(self.root / "bad.glb")

    def test_visual_qa_requires_all_16_and_diverse_orientations(self):
        render = self.root / "frames"
        render.mkdir()
        for i in range(16):
            img = Image.new("RGBA", (128, 128))
            ImageDraw.Draw(img).rectangle((30+i, 20, 100, 100), fill=(80+i*4, 140, 60, 255))
            img.save(render / f"heading_{i:02d}.png")
        qa = sprites.pack(render, self.root / "sprites")
        self.assertEqual(qa["status"], "TECHNICAL_PASS_VISUAL_PENDING")
        self.assertEqual(qa["sprite_count"], 16)
        self.assertFalse(qa["golden_approved"])
        (render / "heading_15.png").unlink()
        with self.assertRaises(FileNotFoundError):
            sprites.pack(render, self.root / "missing")

    def test_identical_frames_fail(self):
        render = self.root / "frames"
        render.mkdir()
        img = Image.new("RGBA", (128, 128))
        ImageDraw.Draw(img).ellipse((30, 30, 100, 100), fill=(70, 80, 90, 255))
        for i in range(16):
            img.save(render / f"heading_{i:02d}.png")
        with self.assertRaisesRegex(ValueError, "INSUFFICIENT_VIEW_DIVERSITY"):
            sprites.pack(render, self.root / "sprites")


if __name__ == "__main__":
    unittest.main()
