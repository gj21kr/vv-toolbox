from dataclasses import replace

import numpy as np
import pytest
import trimesh

from vv_toolbox.voxel_output import Grid, Surface, voxelize
from vv_toolbox.voxel_tiles import iter_mask_tiles
from vv_toolbox.voxel_tiles import write_mask_tiles


def fixture():
    mesh=trimesh.creation.box(extents=[3,2,2])
    a=Surface(3,1,'source',mesh.vertices,mesh.faces,'test','fixture-a')
    b=Surface(9,2,'estimated',mesh.vertices+[1,0,0],mesh.faces,'test','fixture-b')
    grid=Grid((9,10,15),(.5,.5,.5),(-3.,-2.,-2.),'test')
    return [a,b],grid


@pytest.mark.parametrize('tile_shape',[(2,3,4),(5,7,9),(20,20,20)])
def test_sparse_tiles_equal_dense_masks_including_overlaps(tile_shape):
    surfaces,grid=fixture()
    dense=voxelize(surfaces,grid)
    fields=('foreground','anatomical','instance','provenance','overlap_count')
    actual={k:np.zeros_like(getattr(dense,k)) for k in fields}
    membership=np.zeros_like(dense.membership)
    mapping={s.instance_id:i for i,s in enumerate(surfaces)}
    for start,tile in iter_mask_tiles(surfaces,grid,tile_shape_zyx=tile_shape):
        slices=tuple(slice(a,a+n) for a,n in zip(start,tile.grid.shape_zyx))
        for k in fields:
            actual[k][slices]=getattr(tile,k)
        for i,record in enumerate(tile.instances):
            membership[(mapping[record['instance_id']],*slices)]=tile.membership[i]
    for k in fields:
        assert np.array_equal(actual[k],getattr(dense,k)),k
    assert np.array_equal(membership,dense.membership)


def test_exact_index_normalization_preserves_geometry_and_mask():
    surfaces,grid=fixture()
    original=surfaces[0]
    split=replace(original,vertices_mm=original.vertices_mm[original.faces].reshape(-1,3),
                  faces=np.arange(original.faces.size).reshape(-1,3))
    before=split.vertices_mm.copy()
    with pytest.raises(ValueError,match='Closed'):
        list(iter_mask_tiles([split],grid))
    tiles=list(iter_mask_tiles([split],grid,normalize_exact_indices=True))
    assert len(tiles)==1
    assert np.array_equal(tiles[0][1].foreground,voxelize([original],grid).foreground)
    assert np.array_equal(split.vertices_mm,before)


def test_invalid_surface_outside_grid_is_not_silently_ignored():
    surfaces,grid=fixture()
    bad=replace(surfaces[0],instance_id=12,vertices_mm=surfaces[0].vertices_mm+100,
                faces=surfaces[0].faces[:-1])
    with pytest.raises(ValueError,match='Closed'):
        next(iter_mask_tiles([surfaces[0],bad],grid))


def test_low_memory_budget_rejects_before_any_tile():
    surfaces,grid=fixture()
    with pytest.raises(ValueError,match='memory budget'):
        next(iter_mask_tiles(surfaces,grid,max_bytes=100))


def test_sparse_bundle_hashes_and_arrays(tmp_path):
    import hashlib
    import json
    surfaces,grid=fixture()
    destination=tmp_path/'masks'
    result=write_mask_tiles(destination,surfaces,grid,tile_shape_zyx=(3,4,5))
    raw=(destination/'manifest.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==result['manifest_sha256']
    manifest=json.loads(raw)
    assert manifest['complete'] and manifest['tiles']
    restored=np.zeros(grid.shape_zyx,dtype=bool)
    for tile in manifest['tiles']:
        path=destination/tile['file']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==tile['sha256']
        with np.load(path,allow_pickle=False) as data:
            slices=tuple(slice(a,a+n) for a,n in zip(tile['start_zyx'],data['foreground'].shape))
            restored[slices]=data['foreground']
    assert np.array_equal(restored,voxelize(surfaces,grid).foreground)
    with pytest.raises(FileExistsError):
        write_mask_tiles(destination,surfaces,grid)
    assert (destination/'manifest.json').read_bytes()==raw


def test_failed_bundle_does_not_publish_or_leave_lock(tmp_path):
    surfaces,grid=fixture()
    bad=replace(surfaces[1],faces=surfaces[1].faces[:-1])
    with pytest.raises(ValueError,match='Closed'):
        write_mask_tiles(tmp_path/'masks',[surfaces[0],bad],grid)
    assert list(tmp_path.iterdir())==[]


def test_write_failure_after_first_tile_removes_partial_output(tmp_path,monkeypatch):
    surfaces,grid=fixture()
    original=np.savez_compressed
    calls=[]
    def failing(stream,**arrays):
        calls.append(1)
        if len(calls)==2:
            raise OSError('simulated output failure')
        return original(stream,**arrays)
    monkeypatch.setattr(np,'savez_compressed',failing)
    with pytest.raises(OSError,match='simulated output failure'):
        write_mask_tiles(tmp_path/'masks',surfaces,grid,tile_shape_zyx=(2,3,4))
    assert len(calls)==2 and list(tmp_path.iterdir())==[]
