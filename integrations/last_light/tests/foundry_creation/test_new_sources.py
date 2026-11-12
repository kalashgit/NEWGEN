"""Tests for real new Blender-source creation pipeline and its immutable queue."""
import hashlib
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tools/foundry_creation"))
import plan
import publish
import package

class NewSourceFactoryContracts(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
    def tearDown(self):
        self.temp.cleanup()

    def test_catalog_512_unique_new_models(self):
        items=list(plan.catalog())
        self.assertEqual(len(items),512)
        self.assertEqual(len({x["asset_id"] for x in items}),512)
        self.assertEqual(len({x["seed"] for x in items}),512)
        self.assertEqual({x["family"] for x in items},{"F01","F04","F08"})
        self.assertTrue(all(x["golden_approved"] is False for x in items))

    def test_every_batch_starts_with_distinct_archetypes(self):
        p=plan.make_plan(None,4)
        self.assertEqual(len({x["archetype"] for x in p["selected"]}),4)
        self.assertEqual(p["remaining_before"],512)
        self.assertFalse(p["golden_approved"])
        self.assertEqual(p["real_ai_calls"],0)

    def test_cursor_advances_without_repeats(self):
        a=plan.make_plan(None,2)
        s={"schema_version":1,"catalog_sha256":plan.CATALOG_SHA256,"total":512,
           "completed":[x["asset_id"] for x in a["selected"]]}
        b=plan.make_plan(s,2)
        self.assertTrue(set(x["asset_id"] for x in a["selected"]).isdisjoint(
            x["asset_id"] for x in b["selected"]))

    def test_cursor_rejects_stale_or_skipped_ids(self):
        s={"schema_version":1,"catalog_sha256":plan.CATALOG_SHA256,
           "total":512,"completed":["ll_generated_fake_999"]}
        with self.assertRaises(ValueError):
            plan.make_plan(s,2)
        s["completed"]=[]
        s["catalog_sha256"]="0"*64
        with self.assertRaises(ValueError):
            plan.make_plan(s,2)

    def test_completed_512_sources_stops_work(self):
        s={"schema_version":1,"catalog_sha256":plan.CATALOG_SHA256,
           "total":512,"completed":[x["asset_id"] for x in plan.catalog()]}
        p=plan.make_plan(s,2)
        self.assertEqual(p["selected"],[])
        self.assertEqual(p["status"],"COMPLETE")

    def test_batch_budget_bounds(self):
        for count in (0,5,50,-1):
            with self.assertRaises(ValueError):
                plan.make_plan(None,count)

    def test_immutable_publish_cursor(self):
        p=plan.make_plan(None,2)
        m={"catalog_sha256":p["catalog_sha256"],"total":512,
           "golden_approved":False,"canonical_promoted":False,
           "batch":[{"asset_id":x["asset_id"]} for x in p["selected"]]}
        dst=self.root/"dst"
        s=publish.stage(p,m,dst,"foundry-created-123")
        self.assertEqual(s["remaining"],510)
        self.assertEqual(len(s["completed"]),2)
        with self.assertRaises(ValueError):
            publish.stage(p,m,dst,"foundry-created-124")

    def test_no_unapproved_art_promotions(self):
        p=plan.make_plan(None,1)
        m={"catalog_sha256":p["catalog_sha256"],"total":512,
           "golden_approved":True,"canonical_promoted":False,
           "batch":[{"asset_id":p["selected"][0]["asset_id"]}]}
        with self.assertRaises(ValueError):
            publish.stage(p,m,self.root/"dst","foundry-created-123")

    def test_invalid_release_identifiers_rejected(self):
        p=plan.make_plan(None,1)
        m={"catalog_sha256":p["catalog_sha256"],"total":512,
           "golden_approved":False,"canonical_promoted":False,
           "batch":[{"asset_id":p["selected"][0]["asset_id"]}]}
        with self.assertRaises(ValueError):
            publish.stage(p,m,self.root/"dst","../../unexpected")

    def test_bundle_contains_blend_glb_and_original_atlas(self):
        p=plan.make_plan(None,1)
        spec=p["selected"][0]
        aid=spec["asset_id"]
        root=self.root/"sources"/aid
        view=self.root/"atlases"/aid
        root.mkdir(parents=True)
        view.mkdir(parents=True)
        blend=b"BLENDER"+b"0"*1500
        glb=struct.pack("<4sII",b"glTF",2,20)+bytes(8)
        atlas=b"\x89PNG\r\n\x1a\n"+b"fake-intentional-fixture"
        (root/"model.blend").write_bytes(blend)
        (root/"model.glb").write_bytes(glb)
        (view/"atlas_16_headings.png").write_bytes(atlas)
        sha=lambda x:hashlib.sha256(x).hexdigest()
        frame={
            "asset_id":aid,"source_glb_sha256":sha(glb),
            "atlas_sha256":sha(atlas),"distinct_heading_images":8,
            "golden_approved":False,"status":"TECHNICAL_SPRITE_CANDIDATE"
        }
        (view/"manifest.json").write_text(json.dumps(frame))
        source={**spec,
            "source_kind":"NEW_ORIGINAL_PROCEDURAL_BLENDER_MESH",
            "source_editable":True,"geometry_object_count":25,
            "golden_approved":False,
            "blend_sha256":sha(blend),"glb_sha256":sha(glb)}
        (root/"source_manifest.json").write_text(json.dumps(source))
        report={"golden_approved":False,"source_plan_sha256":p["catalog_sha256"],
                "source_count":512,"generated":[frame]}
        bundlepath=self.root/"bundle.zip"
        result=package.bundle(p,report,self.root/"sources",self.root/"atlases",bundlepath)
        self.assertEqual(result["batch_count"],1)
        import zipfile
        with zipfile.ZipFile(bundlepath) as z:
            self.assertIn("assets/"+aid+"/model.blend",z.namelist())
            self.assertIn("assets/"+aid+"/model.glb",z.namelist())
            self.assertIn("assets/"+aid+"/atlas_16_headings.png",z.namelist())
            self.assertIsNone(z.testzip())
        # Any model/source mismatch blocks packaging.
        (root/"model.glb").write_bytes(glb[:-1]+b"x")
        with self.assertRaises(ValueError):
            package.bundle(p,report,self.root/"sources",self.root/"atlases",
                           self.root/"bad.zip")

if __name__=="__main__":
    unittest.main()
