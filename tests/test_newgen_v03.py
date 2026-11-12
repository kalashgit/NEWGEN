"""NEWGEN v0.3: real PBR export, fail-closed canonical V2, geometry hierarchy tests."""
import copy
import json
import importlib.util
from pathlib import Path
import numpy as np
import pytest
import trimesh

ROOT=Path(__file__).resolve().parents[1]
FACTORY=ROOT/'engines/mesh_sprint/factory.py'
spec=importlib.util.spec_from_file_location('mesh_factory_v03',FACTORY)
f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
vspec=importlib.util.spec_from_file_location('ll_v2_adapter_v03',ROOT/'engines/mesh_sprint/v2_adapter.py')
a=importlib.util.module_from_spec(vspec);vspec.loader.exec_module(a)


def test_every_family_has_real_pbr_texture_and_valid_normals(tmp_path):
    for family in f.FAMILIES:
        result=f.process_one(({'asset_id':'pbr_'+family,'family':family,'seed':17},str(tmp_path)))
        assert result['status']=='built',result
        sc=trimesh.load(tmp_path/'models'/('pbr_'+family+'.glb'),force='scene')
        assert sc.geometry
        for mesh in sc.geometry.values():
            assert hasattr(mesh.visual,'material')
            mat=mesh.visual.material
            assert mat.baseColorTexture is not None
            assert mat.normalTexture is not None
            assert len(mesh.visual.uv)==len(mesh.vertices)
            assert np.isfinite(mesh.visual.uv).all()
            assert 0<=mat.metallicFactor<=1
            assert 0<=mat.roughnessFactor<=1
        meta=json.loads((tmp_path/'metadata'/('pbr_'+family+'.json')).read_text())
        assert meta['uv_mapped'] is True
        assert meta['geometry_audit']['pass'] is True
        assert meta['visual_qa']=='not_tested'
        assert meta['golden_approved'] is False


def _recipe():
    return json.loads((ROOT/'engines/mesh_sprint/examples/canonical_v2_sample.jsonl').read_text())


def test_canonical_v2_schema_parses_and_preserves_transform_and_warnings(tmp_path):
    raw=_recipe()
    adapted=a.adapt(raw)
    assert len(adapted['parts'])==2
    assert any('negative_spaces' in s for s in adapted['v2_review_warnings'])
    assert any('source_not_inspected' in s for s in adapted['v2_review_warnings'])
    assert np.isclose(adapted['parts'][0]['_matrix'][0][3],.1)
    assert np.isclose(adapted['parts'][1]['_matrix'][0][3],.1) # parent's translation
    result=f.process_one((adapted,str(tmp_path)))
    assert result['status']=='built',result
    s=trimesh.load(tmp_path/'models'/'newgen_test_shelf_001.glb',force='scene')
    assert s.bounds[0][0] > -.5
    meta=json.loads((tmp_path/'metadata'/'newgen_test_shelf_001.json').read_text())
    assert meta['canonical_catalog_row']==1
    assert meta['v2_review_warnings']
    assert meta['golden_approved'] is False


def test_v2_invalid_unknown_operator_refused():
    raw=_recipe()
    raw['geometry']['nodes'][0]['operation']='make_magic_asset'
    with pytest.raises(ValueError,match='operator not executable'):
        a.adapt(raw)


def test_v2_unknown_parent_and_cycle_refused():
    raw=_recipe()
    raw['geometry']['nodes'][0]['parent_id']='missing_parent'
    with pytest.raises(ValueError,match='Unknown V2 parent'):
        a.adapt(raw)
    raw=_recipe()
    raw['geometry']['nodes'][0]['parent_id']='shelf'
    with pytest.raises(ValueError,match='Cycle'):
        a.adapt(raw)


def test_v2_pipeline_file_intake(tmp_path):
    rows=f.load_rows(ROOT/'engines/mesh_sprint/examples/canonical_v2_sample.jsonl')
    assert len(rows)==1 and len(rows[0]['parts'])==2
    result=f.process_one((rows[0],str(tmp_path)))
    assert result['status']=='built',result


def test_generic_geometry_audit_rejects_unnormalized_degenerate_faces():
    geo=f._quality_geometry()
    spec2=importlib.util.spec_from_file_location('finish',ROOT/'engines/mesh_sprint/geometry_finish.py')
    m=importlib.util.module_from_spec(spec2);spec2.loader.exec_module(m)
    v=np.array([[0,0,0],[1,0,0],[0,1,0]])
    face=np.array([[0,1,1],[0,1,2]])
    _,faces,removed=m.sanitize_faces(v,face)
    assert removed==1 and len(faces)==1


def test_custom_material_slot_compiles(tmp_path):
    row={'asset_id':'custom_metal','material_specs':{
        'bronze_aged':{'pbr':{'base_rgba':[.54,.33,.17,1], 'metallic':.74, 'roughness':.62}}},
        'parts':[{'op':'forge_blade','material':'bronze_aged','x':[0,.1,.2],
                  'top_z':[.3,.30,.28],'bottom_z':[.1,.1,.13], 'thickness':[.003,.015,.06]}]}
    result=f.process_one((row,str(tmp_path)))
    assert result['status']=='built',result
    s=trimesh.load(tmp_path/'models'/'custom_metal.glb',force='scene')
    assert any(abs(mesh.visual.material.metallicFactor-.74)<1e-5 for mesh in s.geometry.values())


def test_multiview_review_is_not_auto_approved(tmp_path):
    s=importlib.util.spec_from_file_location('newgen_multiview',ROOT/'engines/mesh_sprint/qa_multiview.py')
    q=importlib.util.module_from_spec(s);s.loader.exec_module(q)
    result=f.process_one(({'asset_id':'review_avocado','family':'avocado'},str(tmp_path)))
    assert result['status']=='built'
    report=q.render_review(tmp_path,tmp_path/'review',limit=1,views=4,size=120)
    assert report['review_state']=='CANDIDATE_ONLY_NOT_GOLDEN'
    assert report['assets'][0]['visual_qa']=='NOT_TESTED_REQUIRES_REVIEW'
    assert (tmp_path/'review/review_avocado_views.png').exists()
    assert not report['assets'][0]['golden_approved']
