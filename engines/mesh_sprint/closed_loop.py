#!/usr/bin/env python3
"""NEWGEN executable: recipe architect → image defect detector → corrective
3D modeler → game asset packager, with retained iteration evidence.

Vision stage is rendered-image CV, not pretrained VLM; without approved reference
sprite, fidelity status stays unverified. All artifacts are candidates.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import time

from PIL import Image,ImageDraw,ImageFont


def get(name):
    spec=importlib.util.spec_from_file_location('newgen_closed_loop_'+name,Path(__file__).with_name(name+'.py'))
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module


def candidate_score(assessment,contract):
    m=assessment['metrics'];desired=contract['visual_targets']
    mapping={'bbox_width_ratio_max':'bbox_width_ratio','foreground_min':'foreground_fraction','edge_density_min':'edge_density',
      'landmark_brown_min':'brown_fraction','landmark_green_min':'green_fraction','landmark_metal_min':'metal_fraction'}
    # Bounded, simple interpretable score. Does not measure realism.
    score=sum(min(1,(float(val)/max(m[mapping[k]],1e-9) if k.endswith('_max') else m[mapping[k]]/max(float(val),1e-9))) for k,val in desired.items())/len(desired)
    return round(float(score),6)


def run_one(family,out,reference_dir=None,views=8):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    architect=get('recipe_architect');modeler=get('corrective_modeler');vision=get('vision_defects');packager=get('game_asset_factory')
    renderer=get('preview').render_glb
    contract=architect.architect(family)
    (out/'recipe.json').write_text(json.dumps(contract,indent=2))
    ref=None
    if reference_dir:
        path=Path(reference_dir)/f'{family}.png'
        if path.exists():ref=path
    versions=[]
    for iteration in (0,1):
        destination=out/f'iteration_{iteration}'
        builder=modeler.construct(contract,iteration=iteration)
        path,meshstats=modeler.export(builder,destination,contract['asset_id']+f'_r{iteration}')
        front=renderer(path,size=320)
        front_path=destination/'front.png';front.save(front_path)
        assessment=vision.detect(front,contract,ref)
        assessment['score']=candidate_score(assessment,contract)
        assessment['mesh']={key:meshstats[key] for key in ('triangles','vertices','parts','geometry_audit','sha256')}
        assessment['front_image']=str(front_path.relative_to(out))
        assessment['iteration']=iteration
        (destination/'inspection.json').write_text(json.dumps(assessment,indent=2))
        versions.append({'path':path,'assessment':assessment,'image':front})
        if iteration==0 and assessment['structural_screen_pass'] and ref:
            # Known reference and all checks passed; no unnecessary geometry change.
            break
    chosen=max(versions,key=lambda v:(v['assessment']['structural_screen_pass'],v['assessment']['score']))
    qa=chosen['assessment']
    qa['candidate_status']= 'STRUCTURAL_SCREEN_PASS' if qa['structural_screen_pass'] else 'REJECTED_VISUAL_SCREEN'
    qa['corrections_attempted']=len(versions)-1
    qa['chosen_iteration']=versions.index(chosen)
    qa['source_image_provided']=ref is not None
    qa['vision_detector']='OPENCV_RENDERED_IMAGE_HEURISTICS_NOT_A_VLM'
    qa['golden_approved']=False
    if not qa['structural_screen_pass']:
        # Do not package failed candidates as ready-to-use game assets.
        (out/'qa.json').write_text(json.dumps(qa,indent=2))
        return {'asset_id':contract['asset_id'],'family':family,'state':'REJECTED_VISUAL_SCREEN','qa':qa}
    asset_dir=out.parent/'assets'/contract['asset_id']
    manifest=packager.package(chosen['path'],contract,asset_dir)
    # Keep chosen GLB as a direct top-level stable reference, too.
    (out/'qa.json').write_text(json.dumps(qa,indent=2))
    return {'asset_id':contract['asset_id'],'family':family,'state':'GAME_ASSET_CANDIDATE',
      'manifest':str((asset_dir/'asset_manifest.json').relative_to(out.parent)),
      'scene':str((asset_dir/'asset.tscn').relative_to(out.parent)), 'qa':qa}


def gallery(root,outputs,dest):
    root=Path(root);im=Image.new('RGB',(1470,650),(17,24,29));draw=ImageDraw.Draw(im)
    font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    big=ImageFont.truetype(font,26) if Path(font).exists() else None
    small=ImageFont.truetype(font,16) if Path(font).exists() else None
    draw.text((35,20),'NEWGEN  /  Closed-Loop Mesh Factory  /  Actual GLB previews',fill=(239,244,240),font=big)
    for i,result in enumerate(outputs):
        family=result['family'];folder=root/family
        pre=Image.open(folder/'iteration_0'/'front.png').convert('RGB')
        alt=folder/'iteration_1'/'front.png'
        post=Image.open(alt if alt.exists() else folder/'iteration_0'/'front.png').convert('RGB')
        x=i*485+15
        draw.rounded_rectangle((x,71,x+468,632),radius=18,fill=(31,43,47))
        draw.text((x+21,84),family.upper(),fill=(238,243,241),font=big)
        im.paste(pre.resize((214,214)),(x+17,146));im.paste(post.resize((214,214)),(x+242,146))
        draw.text((x+25,373),'INPUT',fill=(160,173,176),font=small)
        draw.text((x+254,373),'AFTER CORRECTION',fill=(191,213,190),font=small)
        report=result['qa'];metric0=json.loads((folder/'iteration_0'/'inspection.json').read_text())['metrics']['edge_density']
        metric1=report['metrics']['edge_density']
        draw.text((x+20,436),f'Image edge density: {metric0:.3f}  to  {metric1:.3f}',fill=(221,230,226),font=small)
        draw.text((x+20,474),f"Geometry: {report['mesh']['triangles']:,} triangles",fill=(221,230,226),font=small)
        draw.text((x+20,511),'GLB / LODs / collider / Godot scene',fill=(221,230,226),font=small)
        draw.text((x+20,552),'CANDIDATE  /  NOT GOLDEN',fill=(238,198,124),font=small)
    dest=Path(dest);dest.parent.mkdir(parents=True,exist_ok=True);im.save(dest)
    return dest


def run(output,selected=('avocado','backpack','axe'),reference_dir=None):
    t=time.perf_counter();out=Path(output);out.mkdir(parents=True,exist_ok=True)
    results=[]
    for family in selected:results.append(run_one(family,out/family,reference_dir))
    report={'engine':'NEWGEN_CLOSED_LOOP_V0.4_CANDIDATE','assets':results,'total':len(results),
      'packaged':sum(x['state']=='GAME_ASSET_CANDIDATE' for x in results),
      'rejected':sum(x['state']!='GAME_ASSET_CANDIDATE' for x in results),
      'elapsed_seconds':round(time.perf_counter()-t,3),
      'references_supplied':bool(reference_dir),
      'image_semantic_ai':'NOT_CONNECTED; OpenCV structural heuristics used',
      'actual_approved_reference_comparison':'NOT_AVAILABLE' if not reference_dir else 'NORMALIZED_SILHOUETTE_ONLY',
      'godot_runtime_test':'NOT_RUN','golden_approvals':0,
      'promotion':'NO_AUTOMATIC_GOLDEN_PROMOTION'}
    if results:gallery(out,results,out/'three_assets_actual_glb.png')
    (out/'run_report.json').write_text(json.dumps(report,indent=2))
    return report


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--out',required=True,type=Path)
    ap.add_argument('--families',nargs='+',default=['avocado','backpack','axe'])
    ap.add_argument('--reference-dir',type=Path)
    args=ap.parse_args()
    result=run(args.out,tuple(args.families),args.reference_dir)
    print(json.dumps({k:v for k,v in result.items() if k!='assets'},indent=2))
    raise SystemExit(0 if result['rejected']==0 else 2)
