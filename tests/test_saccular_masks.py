from copy import deepcopy
import json

import numpy as np
import pytest

from test_lesions import inputs
from test_saccular_spec import parameters
from vv_toolbox.saccular import saccular_spec
from vv_toolbox.saccular_masks import build_saccular_masks
from vv_toolbox.case_io import save_case
from vv_toolbox.case_cli import main


def grid():
    return dict(shape_zyx=[9,12,27],spacing_xyz_mm=[1,1,1],
                origin_xyz_mm=[-3,-3,-4],frame_id='fixture')


@pytest.fixture(scope='module')
def exported(tmp_path_factory):
    path = tmp_path_factory.mktemp('sac-masks')
    case, _ = inputs()
    spec = saccular_spec(case,**parameters())
    source, design, config, output = [path/name for name in ('case.json','spec.json','grid.json','masks.npz')]
    save_case(source,case)
    design.write_text(json.dumps(spec));config.write_text(json.dumps(grid()))
    before = source.read_bytes()
    assert main(['saccular-masks',str(source),str(design),str(config),str(output),
                 '--surface-spacing-mm','.15']) == 0
    assert source.read_bytes() == before
    with np.load(output,allow_pickle=False) as archive:
        return {key:archive[key].copy() for key in archive.files}


def test_mask_labels_preserve_provenance_and_separate_baseline_parent(exported):
    labels, foreground = exported['lesion_instance'], exported['foreground']
    meta = json.loads(str(exported['lesion_metadata']))
    assert labels.shape == foreground.shape == (9,12,27)
    assert labels.dtype == np.uint32 and np.any(labels)
    assert not np.any((labels>0) & ~foreground)
    assert np.all(exported['anatomical']==0)
    assert np.all(exported['provenance'][foreground]==2)
    # World x=10,z=0, y=0 baseline, y=4 sac and y=8 background.
    assert foreground[4,3,13] and labels[4,3,13]==0
    assert foreground[4,7,13] and labels[4,7,13]==1
    assert not foreground[4,11,13] and labels[4,11,13]==0
    assert meta['status']=='CANDIDATE'
    assert meta['registry']==[dict(label=1,lesion_id='sac',edge_id='e')]
    assert meta['case_revision']==meta['surface']['case_revision']
    assert meta['specification_sha256']==meta['surface']['specification_sha256']


@pytest.mark.parametrize('options, message', [
    ({'grid_config':dict(grid(),frame_id='other')},'frame'),
    ({'grid_config':dict(grid(),shape_zyx=[3,3,3])},'cover'),
    ({'coverage':'unknown'},'coverage'),
    ({'max_bytes':100},'budget'),
])
def test_invalid_mask_requests_fail(options,message):
    case,_=inputs()
    spec=saccular_spec(case,**parameters())
    kwargs=dict(surface_spacing_mm=.15,grid_config=grid())
    kwargs.update(options)
    with pytest.raises(ValueError,match=message):
        build_saccular_masks(case,spec,**kwargs)


def test_stale_design_rejected_before_mask_generation():
    case,_=inputs()
    spec=saccular_spec(case,**parameters())
    altered=deepcopy(case)
    altered['edges'][0]['radii_mm']=[3,3]
    with pytest.raises(ValueError,match='stale'):
        build_saccular_masks(altered,spec,surface_spacing_mm=.15,grid_config=grid())


def test_roi_agrees_with_whole_grid_world_coordinates(exported):
    case,_=inputs()
    spec=saccular_spec(case,**parameters())
    roi=dict(shape_zyx=[5,8,7],spacing_xyz_mm=[1,1,1],origin_xyz_mm=[7,1,-2],frame_id='fixture')
    volume,labels,meta=build_saccular_masks(case,spec,surface_spacing_mm=.15,
                                         grid_config=roi,coverage='sac_roi')
    np.testing.assert_array_equal(volume.foreground,exported['foreground'][2:7,4:12,10:17])
    np.testing.assert_array_equal(labels,exported['lesion_instance'][2:7,4:12,10:17])
    assert meta['coverage']=='sac_roi'
    assert meta['checks']['sampled_lumen_connected']=='PASS'
    np.testing.assert_array_equal(volume.grid.affine_xyz[:3,3],[7,1,-2])
