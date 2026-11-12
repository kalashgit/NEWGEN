#!/usr/bin/env python3
"""Independent geometry, source-pinning and sprite acceptance; no Golden grant."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image

from foundry_601_650 import ACTIVE_RECIPES, produce, verify as verify_catalog


def check(path: Path) -> dict:
    root=path.resolve()
    data=json.loads((root/'candidate_manifest.json').read_text())
    catalog=produce();verify_catalog(catalog)
    if (data.get('schema')!='last-light.vehicle-seed-3d.v1' or
        data.get('status')!='TECHNICAL_CANDIDATE_NOT_GOLDEN' or
        data.get('founder_golden_approved') is not False or
        data.get('notion_canonical_ids')!='UNRESOLVED'):
        raise ValueError('invalid candidate-only gate')
    assets=data['assets']
    if len(assets)!=8 or tuple(a['recipe_key'] for a in assets)!=ACTIVE_RECIPES:
        raise ValueError('expected eight unique approved-for-technical-QA recipe concepts')
    hashes=set();total_components=0;total_triangles=0
    with Image.open(root/'inventory_8_items_64px.png') as atlas:
        if atlas.size!=(256,128) or atlas.mode!='RGBA':raise ValueError('invalid inventory sprite atlas')
        for idx,rec in enumerate(assets):
            rel=Path(rec['glb']);f=(root/rel).resolve()
            if rel.is_absolute() or not f.is_relative_to(root) or not f.exists():raise ValueError('invalid GLB path')
            blob=f.read_bytes();digest=hashlib.sha256(blob).hexdigest()
            if blob[:4]!=b'glTF' or digest!=rec['sha256'] or digest in hashes:raise ValueError('corrupted or duplicate GLB')
            hashes.add(digest)
            scene=trimesh.load(str(f),force='scene')
            meshes=list(scene.geometry.values())
            nfaces=sum(len(m.faces) for m in meshes)
            if len(meshes)!=rec['component_count'] or len(meshes)<5 or nfaces!=rec['triangles'] or nfaces<100:
                raise ValueError('missing independent authored geometry')
            if not np.isfinite(scene.bounds).all() or min(np.ptp(scene.bounds,axis=0))<.02:
                raise ValueError('degenerate model bounds')
            if rec['golden_approved'] or rec['notion_id'] is not None:
                raise ValueError('unapproved Golden/canonical promotion')
            with Image.open(root/rec['sprite_64']) as image:
                if image.mode!='RGBA' or image.size!=(64,64):raise ValueError('wrong sprite encoding')
                ratio=(np.asarray(image.getchannel('A'))>0).mean()
                if ratio<.02 or ratio>.96:raise ValueError('blank or solid-color sprite')
                area=((idx%4)*64,(idx//4)*64,(idx%4+1)*64,(idx//4+1)*64)
                if image.tobytes()!=atlas.crop(area).tobytes():raise ValueError('atlas cell drift')
            with Image.open(root/rec['atlas_8']) as image:
                if image.size!=(64,512) or image.mode!='RGBA':raise ValueError('wrong 8-way world atlas')
                for heading in range(8):
                    if image.crop((0,heading*64,64,(heading+1)*64)).getchannel('A').getbbox() is None:
                        raise ValueError('missing directional pixels')
            total_components+=len(meshes);total_triangles+=nfaces
    return {'original_models':8,'unique_glb_hashes':len(hashes),'component_meshes':total_components,
        'triangles':total_triangles,'inventory_sprites':8,'world_frames':64,
        'golden_approved':0,'iphone_fps_verified':False}

if __name__=='__main__':
    print('LL_VEHICLE_MODEL_QA_PASS',json.dumps(check(Path(sys.argv[1])),sort_keys=True))
