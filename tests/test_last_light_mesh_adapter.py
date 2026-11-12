"""CPU-only real GLB tests for the LAST LIGHT V3 NEWGEN adapter."""
from __future__ import annotations
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.last_light_mesh_adapter import RecipeMismatch, run, validate_recipe


def sample_recipe():
    return {
        "schema": "LAST_LIGHT_3D_MESH_RECIPE_V3_CANDIDATE", "recipe_id": "LL-MESH-0002",
        "asset_number": 2, "reference_id": "PZWIKI-ICON-0002",
        "asset_filename": "Acorn.png", "product_name": "Acorn",
        "reference": {"source_file_page": "https://example.invalid/acorn", "copyright_status": "REFERENCE_ONLY"},
        "interpretation": {"archetype": "seed", "classification_basis": "human_review_candidate", "object_state_tokens": []},
        "coordinates_and_scale": {"estimated_bbox_xyz_m": [0.035, 0.027, 0.05]},
        "mesh_construction": {"generator_mode": "organic_sculpt", "part_graph": [{
            "part_id": "nut", "operator": "organic_ovoid", "center_normalized": [0,0,0.5],
            "extent_normalized": [0.8,0.8,0.8], "material_role": "organic_shell", "enabled_if": "always"
        }]}
    }


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.job_dir = root / "jobs" / "j1"
        self.job_dir.mkdir(parents=True)
        self.stage_dir = self.job_dir / "mesh_3d" / "attempt_01"
        self.intake = root / "intake"; self.intake.mkdir()
        image = self.intake / "acorn.png"
        image.write_bytes(b"\x89PNG\r\n\x1a\nfixture")
        self.sha = hashlib.sha256(image.read_bytes()).hexdigest()
        self.env = mock.patch.dict(os.environ, {"NEWGEN_INTAKE_ROOT": str(self.intake)})
        self.env.start(); self.addCleanup(self.env.stop)
        (self.job_dir / "job.json").write_text(json.dumps({
            "schema":"newgen.job.v1", "asset_id":"ll_0002", "reference":"acorn.png", "source_sha256":self.sha
        }))
        (self.job_dir / "mesh_recipe_v3.json").write_text(json.dumps(sample_recipe()))

    def test_real_glb_and_stage_evidence(self):
        report = run(self.job_dir, self.stage_dir, "ll_0002")
        self.assertEqual((self.stage_dir / "ll_0002.glb").read_bytes()[:4], b"glTF")
        self.assertGreater(report["geometry"]["triangles"], 0)
        self.assertFalse(report["founder_golden_approved"])
        result = json.loads((self.stage_dir / "result.json").read_text())
        self.assertEqual(result["outputs"], ["ll_0002.glb", "mesh_report.json"])

    def test_reject_mismatched_identity(self):
        with self.assertRaises(RecipeMismatch):
            run(self.job_dir, self.stage_dir, "ll_0003")
        self.assertFalse((self.stage_dir / "ll_0003.glb").exists())

    def test_reject_wrong_dimensions_and_operator(self):
        bad = sample_recipe(); bad["coordinates_and_scale"]["estimated_bbox_xyz_m"][1] = float("nan")
        with self.assertRaises(ValueError): validate_recipe(bad, "ll_0002")
        bad = sample_recipe(); bad["mesh_construction"]["part_graph"][0]["operator"] = None
        with self.assertRaises(ValueError): validate_recipe(bad, "ll_0002")

    def test_reject_tampered_source(self):
        (self.intake / "acorn.png").write_bytes(b"modified")
        with self.assertRaises(RecipeMismatch): run(self.job_dir, self.stage_dir, "ll_0002")

    def test_reject_escape_stage_dir(self):
        with self.assertRaises(ValueError): run(self.job_dir, self.intake, "ll_0002")

    def test_catalog_lookup(self):
        catalog = self.intake / "catalog.jsonl"
        catalog.write_text(json.dumps(sample_recipe()) + "\n")
        report = run(self.job_dir, self.stage_dir, "ll_0002", catalog=catalog)
        self.assertEqual(report["recipe_id"], "LL-MESH-0002")


if __name__ == "__main__":
    unittest.main()
