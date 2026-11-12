import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('llverify',ROOT/'engines'/'mesh_sprint'/'verify.py')
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)

def test_independent_verify(tmp_path):
    spec2=importlib.util.spec_from_file_location('llfactory',ROOT/'engines'/'mesh_sprint'/'factory.py')
    f=importlib.util.module_from_spec(spec2);spec2.loader.exec_module(f)
    assert f.process_one(({'asset_id':'valid','family':'axe','seed':12},str(tmp_path)))['status']=='built'
    result=v.verify(tmp_path)
    assert result['checked']==1 and result['errors']==[]
    assert result['distinct_sha256']==1

def test_corruption_detected(tmp_path):
    spec2=importlib.util.spec_from_file_location('llfactory',ROOT/'engines'/'mesh_sprint'/'factory.py')
    f=importlib.util.module_from_spec(spec2);spec2.loader.exec_module(f)
    f.process_one(({'asset_id':'damaged','family':'avocado','seed':9},str(tmp_path)))
    (tmp_path/'models'/'damaged.glb').write_bytes(b'corrupt')
    assert len(v.verify(tmp_path)['errors'])==1
