import hashlib
import importlib.util
import json
import struct
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools/foundry_mass" / (name + ".py"))
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m

queue = load("queue")
finalize = load("finalize")
publish = load("publish")

class MassBatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.archive = self.root / "synthetic_source.zip"
        glb = struct.pack("<4sII", b"glTF", 2, 20) + bytes(8)
        self.glb = glb
        self.rows = [
            {"asset_id": f"ll_test_{i:03}", "glb_sha256": hashlib.sha256(glb).hexdigest(),
             "geometry_status": "GEOMETRY_SOURCE_EXPORTED_NEEDS_VISUAL_RECONSTRUCTION_QA"}
            for i in range(360)
        ]
        self.write_source()

    def tearDown(self):
        self.tmp.cleanup()

    def write_source(self):
        source = {"schema":1,"source_plan_unique_count":360,
                  "generated_3d_source_count":360,"status":queue.SRC,
                  "source_plan_sha256":"a"*64,"items":self.rows}
        with zipfile.ZipFile(self.archive, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr("batch_report.json", json.dumps(source))
            for item in self.rows:
                d=item["asset_id"]
                z.writestr(f"{d}/model.glb", self.glb)
                z.writestr(f"{d}/model.blend", b"BLENDER" + bytes(10))
                z.writestr(f"{d}/geometry_manifest.json", "{}")

    def test_deterministic_first_batch(self):
        result = queue.plan(self.archive, None, 2, self.root / "plan")
        self.assertEqual(result["status"], "READY")
        self.assertEqual([r["asset_id"] for r in result["selected"]], ["ll_test_000","ll_test_001"])
        self.assertFalse(result["golden_approved"])

    def test_skip_only_verified_completions(self):
        state = {"schema_version":1,"source_plan_sha256":"a"*64,
                 "completed":["ll_test_000","ll_test_001"]}
        result = queue.plan(self.archive, state, 2, self.root/"plan2")
        self.assertEqual([r["asset_id"] for r in result["selected"]], ["ll_test_002","ll_test_003"])

    def test_all_completed_stops_not_repeats(self):
        state = {"schema_version":1,"source_plan_sha256":"a"*64,
                 "completed":[r["asset_id"] for r in self.rows]}
        result = queue.plan(self.archive, state, 2, self.root/"done")
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(result["selected"], [])

    def test_stale_state_rejected(self):
        with self.assertRaises(ValueError):
            queue.plan(self.archive, {"schema_version":1,"source_plan_sha256":"b"*64,
                                      "completed":[]}, 2, self.root/"stale")

    def test_fake_completion_rejected(self):
        with self.assertRaises(ValueError):
            queue.plan(self.archive, {"schema_version":1,"source_plan_sha256":"a"*64,
                                      "completed":["ll_not_real"]}, 2, self.root/"fake")

    def test_modified_glb_rejected(self):
        self.rows[0]["glb_sha256"] = "0"*64
        self.write_source()
        with self.assertRaises(ValueError):
            queue.plan(self.archive, None, 1, self.root/"badglb")

    def test_invalid_batch_limit_rejected(self):
        for size in (0, 5, 1000):
            with self.assertRaises(ValueError):
                queue.plan(self.archive, None, size, self.root/"badlimit")

    def render_mock(self, plan, clip=False):
        views = self.root / "views"
        for item in plan["selected"]:
            root = views / item["asset_id"]
            root.mkdir(parents=True, exist_ok=True)
            (root/"render_metadata.json").write_text(json.dumps({
                "asset_id":item["asset_id"],"source_sha256":item["glb_sha256"],
                "frames":16,"golden_approved":False,"resolution":128
            }))
            for i in range(16):
                im=Image.new("RGBA",(128,128),(0,0,0,0))
                left=0 if clip and i==0 else 24
                for y in range(30,90):
                    for x in range(left,94):
                        im.putpixel((x,y),(120+i,150,90,255))
                im.save(root/f"{i:02d}.png")
        return views

    def test_real_alpha_atlas_and_progression(self):
        p=queue.plan(self.archive,None,1,self.root/"plan")
        report=finalize.finalize(p,self.render_mock(p),self.root/"out","123")
        self.assertEqual(report["batch_count"],1)
        self.assertEqual(report["remaining"],359)
        self.assertFalse(report["golden_approved"])
        atlas=self.root/"out"/p["selected"][0]["asset_id"]/"atlas_16_headings.png"
        self.assertTrue(atlas.exists())

    def test_clipping_fails_closed(self):
        p=queue.plan(self.archive,None,1,self.root/"plan")
        with self.assertRaises(ValueError):
            finalize.finalize(p,self.render_mock(p,clip=True),self.root/"badout")

    def test_candidate_publication_never_overwrites_existing(self):
        p=queue.plan(self.archive,None,1,self.root/"plan")
        source=self.root/"out"
        finalize.finalize(p,self.render_mock(p),source,"123")
        dest=self.root/"archived"
        self.assertEqual(publish.stage(source,dest),1)
        self.assertTrue((dest/"foundry_mass/state.json").is_file())
        self.assertTrue((dest/"foundry_candidates/ll_test_000/atlas_16_headings.png").is_file())
        with self.assertRaises(ValueError):
            publish.stage(source,dest)

    def test_tampered_atlas_cannot_advance_cursor(self):
        p=queue.plan(self.archive,None,1,self.root/"plan")
        source=self.root/"out"
        finalize.finalize(p,self.render_mock(p),source,"123")
        (source/"ll_test_000/atlas_16_headings.png").write_bytes(b"forged")
        dest=self.root/"archived"
        with self.assertRaises(ValueError):
            publish.stage(source,dest)
        self.assertFalse((dest/"foundry_mass/state.json").exists())

if __name__=="__main__":
    unittest.main()
