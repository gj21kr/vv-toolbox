import json

import numpy as np
import pytest

from test_case_source_surfaces import registered
from vv_toolbox.case_tiles import export_case_tiles
from vv_toolbox.voxel_tile_reader import iter_saved_tiles


def test_case_export_read_retains_case_geometry_and_label_identity(tmp_path):
    case,_=registered()
    result=export_case_tiles(case,tmp_path/'tiles',spacing_mm=.5,tile_shape_zyx=(3,4,5))
    manifest=json.loads((tmp_path/'tiles/manifest.json').read_text())
    assert manifest['context']['selected_parts']==['p']
    assert manifest['context']['part_instances']['p']['geometry_sha256']==case['surface_parts'][0]['geometry_sha256']
    count=0
    for start,arrays,meta in iter_saved_tiles(tmp_path/'tiles',expected_manifest_sha256=result['manifest_sha256']):
        count+=int(arrays['foreground'].sum())
        assert np.all(arrays['provenance'][arrays['foreground']]==1)
        assert not arrays['anatomical'].any()
        assert meta['instances'][0]['source_ref'].endswith(';part:p')
    assert count>0


def test_changed_later_tile_rejected_before_any_output(tmp_path):
    case,_=registered()
    result=export_case_tiles(case,tmp_path/'tiles',spacing_mm=.5,tile_shape_zyx=(3,4,5))
    manifest=json.loads((tmp_path/'tiles/manifest.json').read_text())
    path=tmp_path/'tiles'/manifest['tiles'][-1]['file']
    content=bytearray(path.read_bytes());content[-1]^=1;path.write_bytes(content)
    with pytest.raises(ValueError,match='data hash'):
        next(iter_saved_tiles(tmp_path/'tiles',expected_manifest_sha256=result['manifest_sha256']))


def test_unknown_selection_does_not_publish_output(tmp_path):
    case,_=registered()
    with pytest.raises(ValueError,match='part IDs'):
        export_case_tiles(case,tmp_path/'tiles',spacing_mm=1.,part_ids=['absent'])
    assert not (tmp_path/'tiles').exists()


def test_reader_bounds_decompression_memory(tmp_path):
    case,_=registered()
    result=export_case_tiles(case,tmp_path/'tiles',spacing_mm=1.)
    with pytest.raises(ValueError,match='memory budget'):
        next(iter_saved_tiles(tmp_path/'tiles',expected_manifest_sha256=result['manifest_sha256'],max_tile_bytes=1))
