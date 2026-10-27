import json

import numpy as np
import pytest
import trimesh

from vv_toolbox.volume_cli import main


def test_surface_manifest_to_aligned_crop_archive(tmp_path, capsys):
    mesh = trimesh.creation.box(extents=[2, 2, 2])
    manifest = {'schema': 'vv-toolbox.surface-mask-input/1',
        'grid': {'shape_zyx': [5, 5, 5], 'spacing_xyz_mm': [1, 1, 1],
                 'origin_xyz_mm': [-2, -2, -2], 'frame_id': 'fixture'},
        'surfaces': [{'instance_id': 9, 'anatomical_label': 0, 'provenance': 'estimated',
                      'vertices_mm': mesh.vertices.tolist(), 'faces': mesh.faces.tolist(),
                      'frame_id': 'fixture', 'source_ref': 'synthetic box fixture'}]}
    source, output = tmp_path / 'input.json', tmp_path / 'mask.npz'
    source.write_text(json.dumps(manifest))
    args = [str(source), str(output), '--crop', '1', '1', '1', '4', '4', '4']
    assert main(args) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary['foreground_voxels'] == 27
    with np.load(output, allow_pickle=False) as saved:
        metadata = json.loads(str(saved['metadata']))
        assert saved['foreground'].shape == (3, 3, 3)
        assert saved['foreground'].all()
        assert not saved['anatomical'].any()
        assert np.all(saved['instance'] == 9)
        assert np.all(saved['provenance'] == 2)
        assert np.allclose(np.array(metadata['voxel_xyz_to_world_mm'])[:3, 3], [-1, -1, -1])
    before = output.read_bytes()
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2
    assert output.read_bytes() == before
    assert not list(tmp_path.glob('*.tmp'))
