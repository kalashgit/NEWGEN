"""Regression gates for advanced geometry, not a substitute for human visual QA."""
import importlib.util
import json
import numpy as np
from pathlib import Path
import pytest
import trimesh

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('mesh_sprint_factory_quality', ROOT/'engines'/'mesh_sprint'/'factory.py')
f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
q=f._quality_geometry()


def test_every_supported_family_has_real_advanced_builder():
    assert set(q.BUILDERS)==set(f.FAMILIES)

@pytest.mark.parametrize('family',f.FAMILIES)
def test_high_detail_models_are_real_and_keep_approval_closed(tmp_path,family):
    result=f.process_one(({'asset_id':family,'family':family,'seed':5193,'require_detailed':True},str(tmp_path)))
    assert result['status']=='built',result
    meta=json.loads((tmp_path/'metadata'/f'{family}.json').read_text())
    assert meta['geometry_tier']=='detailed_procedural'
    assert meta['visual_qa']=='not_tested'
    assert meta['gameplay_qa']=='not_tested'
    assert meta['golden_approved'] is False
    assert meta['triangles']>=80
    assert meta['materials']>=2
    sc=trimesh.load(tmp_path/'models'/f'{family}.glb',force='scene')
    assert len(sc.geometry)>=2


def test_procedural_axe_is_physically_tapered_at_sharp_end():
    b=f.MeshBuilder();q.axe(b,seed=23)
    v=np.asarray(b.groups['steel'][0][0],dtype=float)
    near_tip=v[v[:,0]<-.44]
    near_eye=v[(v[:,0]>-.04)&(v[:,0]<.09)]
    assert np.ptp(near_tip[:,1])<.005
    assert np.ptp(near_eye[:,1])>8*np.ptp(near_tip[:,1])


def test_advanced_recipe_operators_compile(tmp_path):
    row={'asset_id':'advanced_ops','seed':11,'parts':[
        {'op':'superloft','material':'fabric','sections':[[0,.2,.1,0],[.3,.23,.13,0],[.5,.1,.08,0]],'segments':20},
        {'op':'ribbon','material':'leather','points':[[-.1,.1,.4],[0,.2,.42],[.1,.1,.4]],'widths':[.03,.05,.03]},
        {'op':'beam','material':'wood','start':[0,0,0],'end':[.2,.1,.3],'width':.04,'depth':.03},
        {'op':'forge_blade','material':'steel','x':[0,.1,.2],
          'top_z':[.3,.29,.28],'bottom_z':[.1,.11,.13],'thickness':[.002,.02,.07]}
    ],'require_detailed':True}
    out=f.process_one((row,str(tmp_path)))
    assert out['status']=='built',out
    meta=json.loads((tmp_path/'metadata'/'advanced_ops.json').read_text())
    assert meta['geometry_tier']=='custom_recipe_unreviewed'
    assert meta['parts']==4


def test_strict_gate_rejects_only_box_ellipsoid_recipe(tmp_path):
    row={'asset_id':'low_detail','family':'backpack','require_detailed':True,
         'parts':[{'op':'box','material':'fabric','location':[0,0,.3],'dimensions':[.3,.2,.6]}]}
    r=f.process_one((row,str(tmp_path)))
    assert r['status']=='failed' and 'primitive-only' in r['error']


def test_bad_loft_and_blade_rejected(tmp_path):
    rows=[
        {'asset_id':'bad_loft','parts':[{'op':'superloft','material':'steel',
         'sections':[[.2,.2,.2,0],[.1,.4,.2,0]]}]},
        {'asset_id':'bad_blade','parts':[{'op':'forge_blade','material':'steel',
         'x':[0,.3,.1],'top_z':[.3,.3,.3],
         'bottom_z':[.1,.1,.1],'thickness':[.01,.03,.05]}]},
    ]
    for row in rows:
        result=f.process_one((row,str(tmp_path)))
        assert result['status']=='failed'


def test_seed_changes_detail_not_structure(tmp_path):
    hashes=[];counts=[]
    for seed in range(9):
        row={'asset_id':f'seed_{seed}','family':'backpack','seed':seed}
        r=f.process_one((row,str(tmp_path)))
        hashes.append(r['sha256']);counts.append(r['triangles'])
    assert len(set(hashes))==9
    assert len(set(counts))==1
