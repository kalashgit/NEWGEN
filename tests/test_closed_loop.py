"""Full independent pipeline gates for NEWGEN (technical only, not Golden)."""
import importlib.util
import json
from pathlib import Path
import numpy as np
import pytest
import trimesh
from PIL import Image

BASE=Path(__file__).resolve().parents[1]/'engines'/'mesh_sprint'

def load(name):
    path=BASE/(name+'.py')
    spec=importlib.util.spec_from_file_location('ng_test_'+name,path)
    x=importlib.util.module_from_spec(spec);spec.loader.exec_module(x);return x


@pytest.mark.parametrize('family',('avocado','backpack','axe'))
def test_recipe_architect_stable_and_no_fake_reference(family):
    a=load('recipe_architect').architect(family)
    b=load('recipe_architect').architect(family)
    assert a==b and a['source_evidence']['sprite_identity_verified'] is False
    assert len(a['geometry_parts'])>=4 and a['recipe_version']


def test_vision_screen_rejects_empty_and_proves_not_golden():
    d=load('vision_defects');a=load('recipe_architect').architect('axe')
    im=Image.new('RGB',(200,200),(241,242,241))
    r=d.detect(im,a)
    assert not r['structural_screen_pass'] and r['golden_approved'] is False
    assert r['reference_iou'] is None


def test_detector_silhouette_iou_math():
    d=load('vision_defects');im=Image.new('RGBA',(80,80),(0,0,0,0));img=np.asarray(im).copy();img[20:60,30:50]=[60,90,60,255]
    im=Image.fromarray(img,'RGBA')
    assert d.normalized_iou(im,im)>0.99


@pytest.mark.parametrize('family',('avocado','backpack','axe'))
def test_corrector_produces_distinct_sanitized_real_geometry(tmp_path,family):
    a=load('recipe_architect').architect(family);m=load('corrective_modeler')
    b0=m.construct(a,0);b1=m.construct(a,1)
    assert b1.components>b0.components
    p0,st0=m.export(b0,tmp_path/'v0',family+'_before')
    p1,st1=m.export(b1,tmp_path/'v1',family+'_after')
    assert p0.read_bytes()[:4]==b'glTF'
    assert st1['triangles']>st0['triangles']
    assert st1['geometry_audit']['pass'] is True
    assert st0['sha256']!=st1['sha256']
    assert len(trimesh.load(p1,force='scene').geometry)>1


def test_lod_and_sprite_packager_stays_candidate(tmp_path):
    a=load('recipe_architect').architect('avocado');m=load('corrective_modeler')
    p,_=m.export(m.construct(a,1),tmp_path/'builder',a['asset_id'])
    result=load('game_asset_factory').package(p,a,tmp_path/'assets'/a['asset_id'])
    assert len(result['lods'])==3
    assert all((tmp_path/'assets'/a['asset_id']/'model'/x['file']).exists() for x in result['lods'])
    assert result['lods'][0]['triangles']>result['lods'][2]['triangles']
    assert result['golden_approved'] is False
    assert result['gameplay_qa']=='NOT_RUN_NO_GODOT_RUNTIME'
    tscn=(tmp_path/'assets'/a['asset_id']/'asset.tscn').read_text()
    assert 'res://assets/'+a['asset_id']+'/model/' in tscn
    from PIL import Image
    im=Image.open(tmp_path/'assets'/a['asset_id']/'sprites'/'inventory.png')
    assert im.mode=='RGBA' and np.min(np.asarray(im)[:,:,3])==0


def test_end_to_end_three_assets_with_distinct_identity(tmp_path):
    # Integration test; slowest test but ensures the four stages work together.
    result=load('closed_loop').run(tmp_path)
    assert result['total']==3 and result['packaged']==3,[(x['family'],x['state'],x['qa']['defects']) for x in result['assets']]
    assert result['rejected']==0 and result['golden_approvals']==0
    for a in result['assets']:
        folder=tmp_path/'assets'/a['asset_id']
        m=json.loads((folder/'asset_manifest.json').read_text())
        assert len(m['lods'])==3 and len(m['sprite_views'])==8
        assert m['source_sprite_fidelity']=='NOT_VERIFIED'
    assert (tmp_path/'three_assets_actual_glb.png').exists()
