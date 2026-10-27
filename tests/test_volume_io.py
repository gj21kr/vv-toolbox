import json

import numpy as np
import pytest
import trimesh

from vv_toolbox.volume_cli import save_volume
from vv_toolbox.volume_io import load_volume
from vv_toolbox.voxel_output import Grid, Surface, voxelize


@pytest.fixture
def archive(tmp_path):
    mesh = trimesh.creation.box(extents=[2, 2, 2])
    surfaces = [Surface(2, 9, 'source', mesh.vertices, mesh.faces, 'fixture', 'box'),
                Surface(7, 12, 'estimated', mesh.vertices+.5, mesh.faces, 'fixture', 'shifted box')]
    volume = voxelize(surfaces, Grid((5, 5, 5), (1., 1., 1.), (-2., -2., -2.), 'fixture'))
    path = tmp_path/'volume.npz'
    save_volume(path, volume)
    return path, volume


def test_roundtrip_preserves_conflicts_memberships_and_coordinates(archive):
    path, volume = archive
    arrays, metadata, lesion_meta = load_volume(path)
    assert metadata == volume.metadata()
    assert lesion_meta is None
    for key, value in arrays.items():
        np.testing.assert_array_equal(value, getattr(volume, key))
    assert np.any(arrays['overlap_count'] == 2)
    assert np.all(arrays['anatomical'][arrays['overlap_count'] == 2] == 0)
    assert np.all(arrays['provenance'][arrays['overlap_count'] == 2] == 3)


@pytest.mark.parametrize('field', ['foreground', 'anatomical', 'instance', 'provenance', 'overlap_count', 'membership', 'affine', 'dtype'])
def test_corrupted_contract_rejected(archive, field):
    path, _ = archive
    with np.load(path, allow_pickle=False) as saved:
        data = {k: saved[k] for k in saved.files}
    if field in ('affine', 'dtype'):
        meta = json.loads(str(data['metadata']))
        if field == 'affine':
            meta['voxel_xyz_to_world_mm'][0][1] = .1
        else:
            meta['dtypes']['instance'] = 'float64'
        data['metadata'] = np.array(json.dumps(meta))
    else:
        data[field].flat[0] = not data[field].flat[0] if data[field].dtype == bool else 123
    np.savez_compressed(path, **data)
    with pytest.raises(ValueError):
        load_volume(path)


def test_uncompressed_payload_limit(archive):
    with pytest.raises(ValueError, match='byte limit'):
        load_volume(archive[0], max_bytes=100)
