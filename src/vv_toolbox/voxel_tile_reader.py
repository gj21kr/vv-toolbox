"""Verify and stream sparse tile bundles without allocating a whole-body mask."""
import hashlib
import json
from pathlib import Path
import zipfile

import numpy as np

from .case_io import _unique_object
from .voxel_output import Grid
from .tile_semantics import validate_tile_semantics


def iter_saved_tiles(folder, *, expected_manifest_sha256, max_tile_bytes=256*1024**2):
    folder=Path(folder)
    manifest=folder/'manifest.json'
    if manifest.is_symlink():
        raise ValueError('Linked manifest not allowed')
    raw=manifest.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected_manifest_sha256:
        raise ValueError('Tile manifest hash mismatch')
    data=json.loads(raw,object_pairs_hook=_unique_object)
    if data.get('schema')!='vv-toolbox.sparse-mask-tiles/1' or data.get('complete') is not True:
        raise ValueError('Complete tile manifest required')
    if type(max_tile_bytes) is not int or max_tile_bytes<=0:
        raise ValueError('Positive tile read budget required')
    grid=Grid(tuple(data['shape_zyx']),tuple(data['spacing_xyz_mm']),
              tuple(data['origin_xyz_mm']),data['frame_id'])
    steps=data['tile_shape_zyx']
    if len(steps)!=3 or any(type(n) is not int or n<=0 for n in steps):
        raise ValueError('Invalid tile layout')
    names=set()
    # Verify every file before yielding any output.
    for tile in data['tiles']:
        start=tile['start_zyx']
        if (len(start)!=3 or any(type(a) is not int or not 0<=a<n or a%t
                                for a,n,t in zip(start,grid.shape_zyx,steps))):
            raise ValueError('Invalid tile coordinates')
        shape=[min(t,n-a) for a,n,t in zip(start,grid.shape_zyx,steps)]
        if tile['metadata']['shape_zyx']!=shape or tile['metadata']['frame_id']!=grid.frame_id:
            raise ValueError('Tile grid differs from global layout')
        name=tile['file']
        if name!='tile-'+'-'.join(map(str,tile['start_zyx']))+'.npz' or name in names:
            raise ValueError('Invalid or repeated tile name')
        names.add(name)
        path=folder/name
        if path.is_symlink() or not path.is_file() or path.stat().st_size!=tile['bytes']:
            raise ValueError('Missing or changed tile file')
        digest=hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda:stream.read(1024*1024),b''):
                digest.update(block)
        if digest.hexdigest()!=tile['sha256']:
            raise ValueError('Tile data hash mismatch')
    if {p.name for p in folder.iterdir()}!=names|{'manifest.json'}:
        raise ValueError('Unexpected tile bundle files')
    for tile in data['tiles']:
        path=folder/tile['file']
        with zipfile.ZipFile(path) as archive:
            if sum(i.file_size for i in archive.infolist())>max_tile_bytes:
                raise ValueError('Tile decompression exceeds memory budget')
        with np.load(path,allow_pickle=False) as arrays:
            fields=('foreground','anatomical','instance','provenance','overlap_count','membership')
            if set(arrays.files)!=set(fields):
                raise ValueError('Tile arrays differ from mask contract')
            values={key:arrays[key] for key in fields}
        shape=tuple(tile['metadata']['shape_zyx'])
        for key,value in values.items():
            expected=(len(tile['metadata']['instances']),*shape) if key=='membership' else shape
            if value.shape!=expected or str(value.dtype)!=tile['metadata']['dtypes'][key]:
                raise ValueError('Tile array shape or dtype mismatch')
        validate_tile_semantics(values,tile['metadata'])
        yield tuple(tile['start_zyx']),values,tile['metadata']
