"""Strict canonical LAST LIGHT V2 recipe adapter for the NEWGEN mesh compiler.

Only actual supported geometric operations are accepted. All drafts remain unapproved.
Unsupported operations reject intake; no box substitution, auto-guess, or name fallback.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
import jsonschema

SCHEMA_PATH=Path(__file__).resolve().parents[2]/'contracts'/'last_light_v2.schema.json'
OPS={'box','ellipsoid','lathe','tube','polygon_prism','superloft','ribbon','beam','forge_blade'}
IDENT=re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,110}\Z')


def _local_transform(node):
    t=node['transform']
    pos=np.asarray(t['position_xyz'],float)
    scale=np.asarray(t['scale_xyz'],float)
    rot=np.asarray(t['rotation_deg_xyz'],float)
    if (pos.shape!=(3,) or scale.shape!=(3,) or rot.shape!=(3,) or
        not np.isfinite(pos).all() or not np.isfinite(scale).all() or
        not np.isfinite(rot).all() or np.any(scale<=0) or np.max(np.abs(pos))>50 or
        np.max(scale)>100 or np.max(np.abs(rot))>36000):
        raise ValueError('Invalid V2 transform')
    matrix=np.eye(4)
    matrix[:3,:3]=Rotation.from_euler('xyz',rot,degrees=True).as_matrix()@np.diag(scale)
    matrix[:3,3]=pos
    return matrix


def adapt(data, schema=None):
    if schema is None:
        schema=json.loads(SCHEMA_PATH.read_text())
    jsonschema.validate(data,schema)
    asset_id=str(data['mesh_recipe_id'])
    if not IDENT.fullmatch(asset_id):
        raise ValueError('Invalid V2 mesh_recipe_id for stable file identifier')
    material_specs={m['slot']:m for m in data['materials']}
    if len(material_specs)!=len(data['materials']):
        raise ValueError('Duplicate material slots')
    geom=data['geometry']
    nodes={n['part_id']:n for n in geom['nodes']}
    if len(nodes)!=len(geom['nodes']) or not nodes:
        raise ValueError('V2 node list empty or duplicate part_id')
    assembled={};visiting=set()
    def resolve(nid):
        if nid in assembled:return assembled[nid]
        if nid in visiting:raise ValueError('Cycle in V2 part parent chain')
        if nid not in nodes:raise ValueError('Unknown V2 parent: '+nid)
        visiting.add(nid)
        node=nodes[nid]
        parent=node['parent_id']
        local=_local_transform(node)
        assembled[nid]=(resolve(parent)@local) if parent is not None else local
        visiting.remove(nid)
        return assembled[nid]
    parts=[];warnings=[]
    for node in geom['nodes']:
        op=node['operation']
        if op not in OPS:
            raise ValueError(f'V2 operator not executable, must develop real geometry: {op} ({node["part_id"]})')
        material=node['material_slot']
        if material not in material_specs:
            raise ValueError('V2 material slot has no declared PBR material: '+material)
        if node['evidence'] in ('GENERIC_PHYSICAL_PRIOR','UNOBSERVED_ASSUMPTION'):
            warnings.append('low_evidence:'+node['part_id'])
        if node['confidence']<.75:
            warnings.append('low_confidence:'+node['part_id'])
        params=node['parameters']
        # The compiler validates op-specific params, including shapes and dimensions.
        if any(key in params for key in ('op','operator','material','_matrix')):
            raise ValueError('V2 parameters cannot override protected node fields')
        parts.append({'op':op,'material':material,'_matrix':resolve(node['part_id']).tolist(),**params})
    for edge in geom['attachments']:
        if edge['from_part'] not in nodes or edge['to_part'] not in nodes:
            raise ValueError('V2 attachment references missing part')
        warnings.append('attachment_not_physically_verified:'+edge['from_part']+':'+edge['to_part'])
    if geom['mandatory_negative_spaces']:
        warnings.append('mandatory_negative_spaces_not_physically_verified')
    if data.get('status') not in ('DRAFT_VISION_INSPECTED',):
        warnings.append('draft_or_blocked_recipe_status:'+str(data.get('status')))
    if data['source_reference']['inspection_status']!='INSPECTED':
        warnings.append('source_not_inspected')
    if any(m['mapping']=='pending' for m in data['materials']):
        warnings.append('material_mapping_pending')
    return {'asset_id':asset_id,'family':data['archetype'].lower(),
            'recipe_version':data['schema'],'canonical_catalog_row':data['canonical_catalog_row'],
            'source_filename':data['source_filename'],
            'source_reference':data['source_reference']['url'] or '',
            'material_specs':material_specs,'parts':parts,
            'v2_review_warnings':warnings,
            'require_detailed':True}
