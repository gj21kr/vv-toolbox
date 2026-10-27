import importlib
from pathlib import Path
import trimesh


def test_mesh_certificate_distinguishes_unknown_and_separate(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]/'scripts'))
    certify=importlib.import_module('verify_full_iliac_mesh').certify_separation
    a=trimesh.creation.box();b=trimesh.creation.box();b.apply_translation([10,0,0])
    result=certify(a,b)
    assert result['status']=='PASS' and result['triangle_pair_count']==144
    assert certify(b,a)['status']=='PASS'
    b.apply_translation([-10,0,0])
    assert certify(a,b)['status']=='UNKNOWN'


def test_nested_surface_not_accepted(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]/'scripts'))
    certify=importlib.import_module('verify_full_iliac_mesh').certify_separation
    outer=trimesh.creation.icosphere(subdivisions=2,radius=10)
    inner=trimesh.creation.icosphere(subdivisions=2,radius=1)
    result=certify(outer,inner)
    assert result['triangle_separation_bound_mm']>0
    assert result['status']=='UNKNOWN'
