#!/usr/bin/env python3
"""Portable GLB geometry/content fingerprints, ignoring JSON float spelling drift.

The same mesh may serialize e.g. extras.height as 0.21931712199461312 on
one CPU and 0.2193171219946131 on another while its glTF BIN geometry remains
bit-identical. Raw SHA still protects an individual archive; this independent
cross-run check preserves materials, names, nodes, binary geometry and rounded
descriptive float metadata before fingerprinting the file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

SCHEMA='last-light.glb-semantic-content-pin.v1'

def normalize(v):
    if isinstance(v,dict):return {k:normalize(x) for k,x in sorted(v.items())}
    if isinstance(v,list):return [normalize(x) for x in v]
    if type(v) is float:
        if not math.isfinite(v):raise ValueError('non-finite glTF JSON number')
        return round(v,8)
    return v

def digest_glb(path: Path) -> str:
    raw=path.read_bytes()
    if len(raw)<20 or raw[:4]!=b'glTF' or struct.unpack_from('<I',raw,4)[0]!=2:
        raise ValueError('invalid GLB v2: '+str(path))
    if struct.unpack_from('<I',raw,8)[0]!=len(raw):
        raise ValueError('GLB declared file length differs')
    offset=12;meta=None;body=[]
    while offset<len(raw):
        if offset+8>len(raw):raise ValueError('truncated GLB chunk')
        n,typ=struct.unpack_from('<I4s',raw,offset)
        offset+=8
        if offset+n>len(raw):raise ValueError('out-of-range GLB chunk')
        part=raw[offset:offset+n];offset+=n
        if typ==b'JSON':
            if meta is not None:raise ValueError('multiple JSON chunks')
            meta=json.loads(part)
        elif typ==b'BIN\x00':body.append(part)
        else:raise ValueError('unsupported GLB chunk type')
    if not isinstance(meta,dict) or not body:raise ValueError('GLB lacks JSON or geometry data')
    normalized=json.dumps(normalize(meta),sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
    h=hashlib.sha256()
    h.update(b'LAST_LIGHT_GLTF_SEMANTIC_V1\x00')
    h.update(struct.pack('<I',len(normalized)));h.update(normalized)
    for part in body:
        h.update(struct.pack('<I',len(part)));h.update(part)
    return h.hexdigest()

def index_models(model_dir:Path,source_path:Path|None=None)->dict:
    records={f.stem:digest_glb(f) for f in sorted(model_dir.glob('*.glb'))}
    if len(records)!=40 or len(set(records.values()))!=40:
        raise ValueError('expected exactly 40 unique GLB semantic files')
    source_sha=hashlib.sha256(source_path.read_bytes()).hexdigest() if source_path else None
    return {'schema':SCHEMA,'notion_canonical_ids':'PENDING',
            'golden_approved':False,'source_recipe_sha256':source_sha,
            'models':records}

def verify(model_dir:Path,pinned:Path,source_path:Path):
    expected=json.loads(pinned.read_text())
    actual=index_models(model_dir,source_path)
    if expected!=actual:raise ValueError('cross-run GLB geometry/material semantic drift or source code changed')
    return {'models':len(actual['models']),'strict_unique':len(set(actual['models'].values())),
            'golden_approved':False}

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('model_dir',type=Path)
    p.add_argument('--source',type=Path)
    p.add_argument('--write',type=Path)
    p.add_argument('--verify',type=Path)
    a=p.parse_args()
    if bool(a.write)==bool(a.verify):raise ValueError('supply exactly one of --write or --verify')
    if a.write:
        d=index_models(a.model_dir,a.source)
        a.write.parent.mkdir(parents=True,exist_ok=True)
        a.write.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
        print('LL_SEMANTIC_GLTF_PIN_CREATED',len(d['models']))
    else:
        if a.source is None:raise ValueError('source recipe code needed for verification')
        print('LL_SEMANTIC_GLTF_PIN_PASS',verify(a.model_dir,a.verify,a.source))
