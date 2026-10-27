from copy import deepcopy

import numpy as np
import pytest

from test_case_source_surfaces import registered
from test_estimated_tube_volume import tube
from vv_toolbox.case_source_surfaces import attach_surfaces
from vv_toolbox.case_io import case_digest,save_case,load_case
from vv_toolbox.neck_volume_case import derive_neck_volumes


def fixture():
    case,_=registered()
    parts=case.pop('surface_parts')
    part=tube()
    edge=deepcopy(case['edges'][0]);edge['id']='neck-edge'
    case['edges'].append(edge)
    parts.append(dict(part_id='neck',edge_ids=['neck-edge'],frame_id='fixture',provenance='estimated',
        source_ids=['s'],vertices_mm=part['vertices'].tolist(),faces=part['faces'].tolist()))
    case.update(model_kind='synthetic',generation=dict(seed=0,generator_version='fixture',config={}))
    case['inspection']=dict(atlas_scene_capture=dict(estimated_metadata={'neck':part['metadata']}))
    return attach_surfaces(case,parts)


def test_case_derivation_preserves_source_graph_and_parent_and_roundtrips(tmp_path):
    case=fixture();before=deepcopy(case)
    result=derive_neck_volumes(case,max_planarity_mm=.001)
    assert case==before
    assert result['edges']==case['edges'] and result['nodes']==case['nodes']
    assert result['surface_parts'][0]==case['surface_parts'][0]
    assert result['surface_parts'][1]['provenance']=='estimated'
    assert result['generation']['config']['parent_case_revision']==case_digest(case)
    save_case(tmp_path/'derived.json',result)
    assert load_case(tmp_path/'derived.json')[0]==result
    p=result['surface_parts'][1]
    import trimesh
    assert trimesh.Trimesh(p['vertices_mm'],p['faces'],process=False).is_volume


def test_invalid_later_neck_does_not_modify_input():
    case=fixture()
    parts=case.pop('surface_parts')
    bad=deepcopy(parts[1]);bad['part_id']='bad';bad['edge_ids']=['bad-edge']
    # Make one top-rim vertex nonplanar.
    used=np.unique(bad['faces'])
    index=next(int(i) for i in used if bad['vertices_mm'][i][2]>0)
    bad['vertices_mm'][index][2]+=.1
    edge=deepcopy(case['edges'][-1]);edge['id']='bad-edge';case['edges'].append(edge)
    case['inspection']['atlas_scene_capture']['estimated_metadata']['bad']=tube()['metadata']
    case=attach_surfaces(case,[*parts,bad]);before=deepcopy(case)
    with pytest.raises(ValueError,match='planarity'):
        derive_neck_volumes(case,max_planarity_mm=.001)
    assert case==before
