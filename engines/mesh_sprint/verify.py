#!/usr/bin/env python3
"""Independent structural reimport and manifest validation. NOT visual/semantic QA."""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
import trimesh


def verify(root):
    root=Path(root)
    paths=sorted((root/'metadata').glob('*.json'))
    errors=[]
    sha_set=set()
    for path in paths:
        try:
            meta=json.loads(path.read_text())
            target=root/'models'/f"{meta['asset_id']}.glb"
            content=target.read_bytes()
            sha=hashlib.sha256(content).hexdigest()
            assert sha==meta['sha256'],'hash mismatch'
            assert content[:4]==b'glTF','not GLB'
            assert meta['golden_approved'] is False
            sc=trimesh.load(target,force='scene')
            assert len(sc.geometry)>0 and all(len(m.faces)>0 and len(m.vertices)>0 for m in sc.geometry.values())
            bounds=sc.bounds
            assert all(math.isfinite(float(c)) for v in bounds for c in v)
            sha_set.add(sha)
        except Exception as e:
            errors.append({'file':str(path),'error':str(e)})
    report={'checked':len(paths),'distinct_sha256':len(sha_set),'errors':errors,
            'visual_identity_tested':False,'golden_approved':False}
    (root/'independent_verify.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path);opts=p.parse_args()
    report=verify(opts.root);print(json.dumps(report,indent=2))
    sys.exit(0 if not report['errors'] and report['checked'] else 2)
