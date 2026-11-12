import importlib.util
import json
from pathlib import Path

import pytest
import trimesh

SOURCE=Path(__file__).resolve().parents[1]/'engines'/'mesh_sprint'/'factory.py'
spec=importlib.util.spec_from_file_location('mesh_sprint_factory',SOURCE)
f=importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)

@pytest.mark.parametrize('family',f.FAMILIES)
def test_every_family_exports_valid_glb(tmp_path,family):
    row={'asset_id':f'test_{family}','family':family,'seed':14,'variant':4}
    result=f.process_one((row,str(tmp_path)))
    assert result['status']=='built',result
    path=tmp_path/'models'/f'test_{family}.glb'
    assert path.read_bytes()[:4]==b'glTF'
    scene=trimesh.load(path,force='scene')
    assert len(scene.geometry)>0
    assert sum(len(g.faces) for g in scene.geometry.values())>8
    meta=json.loads((tmp_path/'metadata'/f'test_{family}.json').read_text())
    assert meta['golden_approved'] is False
    assert meta['review_state']=='generated_candidate'

def test_rebuild_deterministic_and_resumable(tmp_path):
    row={'asset_id':'stable','family':'backpack','seed':6,'variant':8}
    a=f.process_one((row,str(tmp_path)))
    data=(tmp_path/'models'/'stable.glb').read_bytes()
    b=f.process_one((row,str(tmp_path)))
    assert b['status']=='cached'
    assert b['sha256']==a['sha256']
    (tmp_path/'models'/'stable.glb').write_bytes(b'corrupt')
    c=f.process_one((row,str(tmp_path)))
    assert c['status']=='built'
    assert (tmp_path/'models'/'stable.glb').read_bytes()==data

def test_unknown_asset_fails_closed(tmp_path):
    r=f.process_one(({'asset_id':'mystery','family':'unknown','seed':0},str(tmp_path)))
    assert r['status']=='failed' and 'Unsupported/unknown' in r['error']

def test_explicit_recipe_compiles_and_tracks_parts(tmp_path):
    r=f.process_one(({'asset_id':'custom_1','parts':[{'op':'lathe','profile':[[0,.1],[.3,.1],[.5,.05]],'material':'plastic'}]},str(tmp_path)))
    assert r['status']=='built',r

def test_duplicate_id_rejected(tmp_path):
    file=tmp_path/'dupes.jsonl'
    file.write_text('{"asset_id":"a","family":"axe"}\n{"asset_id":"a","family":"axe"}\n')
    with pytest.raises(ValueError,match='Duplicate'):f.load_rows(file)

def test_no_storage_items_in_shelf(tmp_path):
    r=f.process_one(({'asset_id':'empty_shelf','family':'shelf'},str(tmp_path)))
    assert r['status']=='built'
    meta=json.loads((tmp_path/'metadata'/'empty_shelf.json').read_text())
    assert meta['parts'] >= 25  # structural beams, empty trays, diagonal braces
    assert meta['geometry_tier'] == 'detailed_procedural'
    sc=trimesh.load(tmp_path/'models'/'empty_shelf.glb',force='scene')
    assert len(sc.geometry)>0

def test_different_seeds_produce_distinct_geometry(tmp_path):
    hashes=[]
    for i in range(20):
        r=f.process_one(({'asset_id':f'unique_{i}','family':'helmet','seed':i},str(tmp_path)))
        assert r['status']=='built',r
        hashes.append(r['sha256'])
    assert len(set(hashes))==20
