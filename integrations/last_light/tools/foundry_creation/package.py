"""Package verified new 3D Blender sources + technical atlas as one durable release asset."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import struct
import zipfile
from pathlib import Path

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def bundle(plan: dict, render: dict, sources: Path, atlas_root: Path, output: Path):
    if plan.get("generator_kind")!="DETERMINISTIC_BLENDER_PROCEDURAL_SOURCE":
        raise ValueError("Untrusted source plan")
    if plan.get("golden_approved") is not False or render.get("golden_approved") is not False:
        raise ValueError("Never bundle Golden/production claims")
    selected=plan.get("selected",[])
    verified=render.get("generated",[])
    if not 1<=len(selected)<=4 or len(verified)!=len(selected):
        raise ValueError("Incorrect candidate batch size")
    if [x["asset_id"] for x in selected]!=[x["asset_id"] for x in verified]:
        raise ValueError("Source/render identity mismatch")
    if render.get("source_plan_sha256")!=plan.get("catalog_sha256") or render.get("source_count")!=plan.get("total"):
        raise ValueError("Source/render catalog mismatch")
    assert plan["total"]==512
    output.parent.mkdir(parents=True,exist_ok=True)
    listing=[]
    with zipfile.ZipFile(output,"w",zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for spec, frame in zip(selected,verified):
            aid=spec["asset_id"]
            if not re.fullmatch(r"ll_generated_[a-z_]+_[0-9]{3}",aid):
                raise ValueError("Invalid new source ID")
            root=sources/aid
            meta=json.loads((root/"source_manifest.json").read_text())
            if (meta["asset_id"]!=aid or meta["seed"]!=spec["seed"]
                or meta.get("source_kind")!="NEW_ORIGINAL_PROCEDURAL_BLENDER_MESH"
                or meta.get("golden_approved") is not False
                or meta.get("source_editable") is not True
                or meta.get("geometry_object_count",0)<15):
                raise ValueError("Missing actual editable Blender provenance")
            if frame.get("golden_approved") is not False or frame.get("status")!="TECHNICAL_SPRITE_CANDIDATE":
                raise ValueError("Invalid sprite QA status")
            if frame.get("distinct_heading_images",0)<4:
                raise ValueError("Insufficient directional variation")
            blend=root/"model.blend"
            glb=root/"model.glb"
            atlas=atlas_root/aid/"atlas_16_headings.png"
            manifest=atlas_root/aid/"manifest.json"
            if (not blend.is_file() or not glb.is_file() or not atlas.is_file()
                or not manifest.is_file()):
                raise ValueError("Missing real source/export/render")
            bb=blend.read_bytes()
            gb=glb.read_bytes()
            if ((bb[:7]!=b"BLENDER" and bb[:4]!=bytes.fromhex("28b52ffd"))
                or gb[:4]!=b"glTF" or len(gb)<20
                or struct.unpack_from("<I",gb,8)[0]!=len(gb)):
                raise ValueError("Corrupt Blender or GLB signature")
            if sha(blend)!=meta["blend_sha256"] or sha(glb)!=meta["glb_sha256"]:
                raise ValueError("Source file hashes diverged")
            if sha(glb)!=frame["source_glb_sha256"] or sha(atlas)!=frame["atlas_sha256"]:
                raise ValueError("Sprite provenance diverged")
            if json.loads(manifest.read_text())!=frame:
                raise ValueError("Independent sprite manifest mismatch")
            for name,path in (
                ("model.blend",blend),("model.glb",glb),
                ("source_manifest.json",root/"source_manifest.json"),
                ("atlas_16_headings.png",atlas),("atlas_manifest.json",manifest)
            ):
                z.write(path,f"assets/{aid}/{name}")
            listing.append({
                "asset_id":aid,"archetype":spec["archetype"],"family":spec["family"],
                "seed":spec["seed"],"blend_sha256":meta["blend_sha256"],
                "glb_sha256":meta["glb_sha256"],"atlas_sha256":frame["atlas_sha256"],
                "status":"UNAPPROVED_NEW_EDITABLE_3D_CANDIDATE",
            })
        z.writestr("batch_report.json",json.dumps(render,indent=2))
        z.writestr("generator_plan.json",json.dumps(plan,indent=2))
        z.writestr("README.txt","Original editable Blender model variants and technical F12-inspired sprite previews. Not Golden; no gameplay acceptance.\n")
    check=zipfile.ZipFile(output).testzip()
    if check is not None:
        raise ValueError("ZIP integrity check failed")
    report={
        "schema_version":1,"catalog_sha256":plan["catalog_sha256"],
        "total":plan["total"],"completed_before":plan["completed_before"],
        "batch_count":len(selected),"batch":listing,
        "archive_sha256":sha(output),"archive_size_bytes":output.stat().st_size,
        "source_editable":True,"golden_approved":False,
        "canonical_promoted":False,"gameplay_integrated":False,
    }
    (output.parent/"package_manifest.json").write_text(json.dumps(report,indent=2)+"\n")
    print("FOUNDRY_CREATED_SOURCE_PACKAGE",len(selected),output.stat().st_size)
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--plan",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    p.add_argument("--sources",type=Path,required=True)
    p.add_argument("--atlases",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    bundle(json.loads(a.plan.read_text()),json.loads(a.report.read_text()),a.sources,a.atlases,a.output)

if __name__=="__main__":
    main()
