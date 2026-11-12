"""Fail-closed tests for NEWGEN admission, orchestration and recipe validation."""
from __future__ import annotations
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from newgen import core
from newgen.recipe import RecipeError, validate


class ControlPlaneTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.intake = base / "intake"
        self.intake.mkdir()
        self.store = base / "state"
        self.patch = mock.patch.dict(os.environ, {
            "NEWGEN_DATA_ROOT": str(self.store),
            "NEWGEN_INTAKE_ROOT": str(self.intake),
            "NEWGEN_ENGINE_CONFIG": str(core.ROOT / "config" / "engines.json")
        })
        self.patch.start()
        self.addCleanup(self.patch.stop)
        (self.intake / "battery.png").write_bytes(b"\x89PNG\r\n\x1a\nfixture")

    def test_admission_and_fail_closed_unconfigured_mesh(self):
        job = core.create_job("vehicle_battery_001", "battery.png")
        self.assertEqual(job["status"], "queued")
        finished = core.run_one(job["id"])
        self.assertEqual(finished["status"], "blocked_unconfigured")
        self.assertFalse(finished["founder_golden_approved"])
        self.assertEqual(len(finished["artifacts"]), 1)
        self.assertEqual(finished["artifacts"][0]["stage"], "sprite_2d")
        self.assertIn("mesh_3d", finished["error"])
        self.assertEqual(core.retry_job(job["id"])["status"], "queued")

    def test_traversal_is_denied(self):
        for candidate in ("../secret.png", "/tmp/secret.png", "does_not_exist.png"):
            with self.assertRaises(core.PipelineError):
                core.create_job("vehicle_battery_001", candidate)

    def test_source_tampering_aborts(self):
        job = core.create_job("vehicle_battery_001", "battery.png")
        (self.intake / "battery.png").write_bytes(b"modified")
        finished = core.run_one(job["id"])
        self.assertEqual(finished["status"], "failed")
        self.assertIn("changed", finished["error"])

    def test_no_approval_before_technical_pipeline(self):
        job = core.create_job("vehicle_battery_001", "battery.png")
        with self.assertRaises(core.PipelineError):
            core.approve(job["id"], "founder_golden", "Founder")
        with self.assertRaises(core.PipelineError):
            core.approve(job["id"], "godot_iphone", "Founder")

    def test_adapter_output_must_be_scoped(self):
        folder = self.store / "stage"
        folder.mkdir(parents=True)
        (self.store / "outside.glb").write_bytes(b"glTF")
        with self.assertRaises(core.PipelineError):
            core._safe_output(folder, "../outside.glb")

    def test_approved_gate_order(self):
        job = core.create_job("vehicle_battery_001", "battery.png")
        job["status"] = "awaiting_founder_review"
        core._save(job)
        with self.assertRaises(core.PipelineError):
            core.approve(job["id"], "godot_iphone", "Founder")
        core.approve(job["id"], "founder_golden", "Founder")
        approved = core.approve(job["id"], "godot_iphone", "Device QA")
        self.assertEqual(approved["status"], "approved")
        self.assertTrue(approved["founder_golden_approved"])


class RecipeTests(unittest.TestCase):
    def setUp(self):
        self.example = json.loads(
            (core.ROOT / "recipes" / "examples" / "vehicle_battery_demo.json").read_text()
        )

    def test_valid_demonstration_recipe(self):
        self.assertEqual(validate(self.example)["asset_id"], "vehicle_battery_demo")

    def test_reject_arbitrary_primitive(self):
        self.example["components"][0]["primitive"] = "python_exec"
        with self.assertRaises(RecipeError):
            validate(self.example)

    def test_reject_nan(self):
        self.example["components"][0]["size"][0] = float("nan")
        with self.assertRaises(RecipeError):
            validate(self.example)

    def test_reject_duplicate_component_id(self):
        self.example["components"][1]["id"] = self.example["components"][0]["id"]
        with self.assertRaises(RecipeError):
            validate(self.example)


if __name__ == "__main__":
    unittest.main()
