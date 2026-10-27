import hashlib
import itertools
import json
from types import SimpleNamespace

import numpy as np
import pytest
import trimesh

from vv_toolbox import atlas
from vv_toolbox.protected_preview import load_protected_preview


def setup(root,monkeypatch):
    evidence=root/'docs/evidence';evidence.mkdir(parents=True)
    exports=root/'exports';exports.mkdir()
    parts=[];rows=[];hashes={}
    for i in range(8):
        mesh=trimesh.creation.box();mesh.apply_translation([i*4,0,0])
        ident=f'part{i}'
        parts.append(dict(id=ident,layer='arterial',vertices=mesh.vertices.copy(),faces=mesh.faces.copy()))
        mesh.vertices[1]+=[.01,0,0]
        data=mesh.export(file_type='ply');path=exports/f'{ident}.ply';path.write_bytes(data)
        digest=hashlib.sha256(data).hexdigest();hashes[ident]=digest
        rows.append(dict(source_part_id=ident,edge_id=f'{ident}:e0',artifact=f'exports/{ident}.ply',
                         sha256=digest,status='CANDIDATE',protected_vertex_ids=[0],
                         self_contact=dict(status='NO_CONTACT_DETECTED',
                             coverage='all distinct triangle pairs',contact_pairs=[])))
    raw=json.dumps(dict(atlas_archive_sha256='a'*64,rows=rows)).encode()
    (evidence/'protected-cerebral-fit.json').write_bytes(raw)
    scene=dict(input_candidate_report_sha256=hashlib.sha256(raw).hexdigest(),
               atlas_archive_sha256='a'*64,replacement_sha256=hashes,rows=[],
               bounds_separated_pairs=list(itertools.combinations(sorted(hashes),2)))
    (evidence/'protected-cerebral-scene.json').write_text(json.dumps(scene))
    monkeypatch.setattr(atlas,'load_atlas',lambda:SimpleNamespace(meshes=parts,metadata={'sha256':'a'*64}))
    return scene


def test_exact_source_and_candidate_are_distinct_readonly_meshes(tmp_path,monkeypatch):
    setup(tmp_path,monkeypatch)
    source=load_protected_preview(tmp_path,reference=True)
    candidate=load_protected_preview(tmp_path)
    assert np.array_equal(source['faces'],candidate['faces'])
    assert not np.array_equal(source['vertices_mm'],candidate['vertices_mm'])
    assert source['summary']['protected_comparison']['reference']
    assert candidate['summary']['protected_comparison']['affected_pairs']==28
    assert candidate['summary']['read_only'] and candidate['edges']==[]
    from vv_toolbox.app import Workspace
    workspace=Workspace.__new__(Workspace)
    workspace.source='candidate';workspace.candidate=candidate
    assert '28조합' in workspace.description(None)
    workspace.candidate=source
    assert '원본 비교' in workspace.description(None)


@pytest.mark.parametrize('damage',['coverage','artifact','index_hash'])
def test_stale_or_incomplete_evidence_rejected(tmp_path,monkeypatch,damage):
    scene=setup(tmp_path,monkeypatch)
    if damage=='coverage':scene['bounds_separated_pairs'].pop()
    elif damage=='index_hash':scene['input_candidate_report_sha256']='0'*64
    else:(tmp_path/'exports/part0.ply').write_bytes(b'changed')
    (tmp_path/'docs/evidence/protected-cerebral-scene.json').write_text(json.dumps(scene))
    with pytest.raises(ValueError):load_protected_preview(tmp_path)
