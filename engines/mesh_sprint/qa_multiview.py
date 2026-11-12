#!/usr/bin/env python3
"""Actual GLB multi-view review sheets. This is NOT automated semantic visual QA.

Produces candidate evidence for NEWGEN's independent evaluator/founder gate.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def _renderer():
    src=Path(__file__).with_name('preview.py')
    spec=importlib.util.spec_from_file_location('_newgen_preview',src)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.render_glb


def render_review(root,out,limit=12,views=8,size=260):
    if views not in (4,8,16): raise ValueError('Views must be 4, 8 or 16')
    if not 1<=limit<=100: raise ValueError('Limit must be 1..100')
    from math import sin,cos,pi
    root=Path(root);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    models=sorted((root/'models').glob('*.glb'))[:limit]
    if not models:raise ValueError('No GLB candidates under models/')
    render=_renderer();manifest=[]
    font_path='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    font=ImageFont.truetype(font_path,14) if Path(font_path).exists() else None
    # Angle 0 is 45-degree front (Y negative); every image uses exactly the same
    # camera height and source geometry. No source image is embedded or fabricated.
    for path in models:
        cell=size+14
        contact=Image.new('RGB',(4*cell,((views+3)//4)*(cell+26)+42),(246,247,247))
        draw=ImageDraw.Draw(contact)
        draw.text((12,8),f'{path.stem}  |  UNAPPROVED  |  GLB MULTI-VIEW',fill=(29,38,43),font=font)
        for i in range(views):
            angle=-pi/2+pi/4+2*pi*i/views
            v=(cos(angle),sin(angle),.83)
            im=render(path,view=v,size=size)
            x=(i%4)*cell+7;y=(i//4)*(cell+26)+36
            contact.paste(im,(x,y))
            draw.text((x+5,y+size+3),f'view {i:02d} / {views:02d}',fill=(57,63,67),font=font)
        target=out/(path.stem+'_views.png');contact.save(target,optimize=True)
        manifest.append({'asset_id':path.stem,'source_glb':str(path),'render_sheet':target.name,
                         'view_count':views,'visual_qa':'NOT_TESTED_REQUIRES_REVIEW',
                         'source_identity_verified':False,'golden_approved':False})
    report={'assets':manifest,'review_state':'CANDIDATE_ONLY_NOT_GOLDEN',
            'limits':'CPU-rendered geometry and diffuse textures; not Blender/PBR comparison, not source-sprite similarity'}
    (out/'review_manifest.json').write_text(json.dumps(report,indent=2))
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--root',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    p.add_argument('--max',default=12,type=int)
    p.add_argument('--views',default=8,type=int)
    p.add_argument('--size',default=260,type=int)
    args=p.parse_args()
    r=render_review(args.root,args.out,args.max,args.views,args.size)
    print(json.dumps({'rendered':len(r['assets']),'approval':r['review_state']}))
