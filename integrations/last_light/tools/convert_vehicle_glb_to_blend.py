"""Import exactly eight F11 candidates as native editable Blender masters.

The independent `.blend` files retain per-component meshes and source hashes.
Their presence never means that the founder has approved their appearance.
"""
import argparse
import hashlib
import sys
from pathlib import Path

import bpy

args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
p=argparse.ArgumentParser()
p.add_argument('--source',required=True,type=Path)
p.add_argument('--output',required=True,type=Path)
o=p.parse_args(args)
o.output.mkdir(parents=True,exist_ok=True)
models=sorted(o.source.glob('*.glb'))
if len(models)!=8:raise ValueError(f'expected 8 candidate GLBs, got {len(models)}')
for glb in models:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(glb.resolve()))
    meshes=[o for o in bpy.data.objects if o.type=='MESH']
    if len(meshes)<5 or sum(len(m.data.polygons) for m in meshes)<100:
        raise ValueError('missing component geometry in '+glb.name)
    scene=bpy.context.scene
    scene['ll_candidate_only']=True
    scene['ll_founder_golden_approved']=False
    scene['ll_original_geometry_recipe']='tools/vehicle_seed_batch.py'
    scene['ll_original_glb_sha256']=hashlib.sha256(glb.read_bytes()).hexdigest()
    bpy.context.preferences.filepaths.save_version=0
    target=o.output/(glb.stem+'.blend')
    bpy.ops.wm.save_as_mainfile(filepath=str(target.resolve()),compress=False)
    if target.stat().st_size<1000 or target.open('rb').read(7)!=b'BLENDER':
        raise ValueError('bad native .blend signature: '+target.name)
    print('LL_VEHICLE_NATIVE_SOURCE_PASS',glb.stem,len(meshes),flush=True)
print('LL_VEHICLE_NATIVE_BATCH_PASS',len(models),'native editable candidate sources',flush=True)
