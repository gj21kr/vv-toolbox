"""Read portable mask archives and check their coordinate/label consistency."""
import json
from pathlib import Path
import zipfile

import numpy as np

from .voxel_output import Grid


def load_volume(path, *, max_bytes=256*1024**2):
    """Return arrays and original metadata; does not revalidate source geometry.

    The byte limit bounds uncompressed archive payload, not process RSS.
    """
    if type(max_bytes) is not int or max_bytes <= 0:
        raise ValueError('positive archive byte limit required')
    with zipfile.ZipFile(Path(path)) as archive:
        entries = archive.infolist()
        if len({e.filename for e in entries}) != len(entries):
            raise ValueError('duplicate archive entries')
        if sum(e.file_size for e in entries) > max_bytes:
            raise ValueError('uncompressed archive exceeds byte limit')
    types = dict(foreground='bool', anatomical='uint32', instance='uint32',
                 provenance='uint8', overlap_count='uint32', membership='bool')
    with np.load(path, allow_pickle=False) as saved:
        metadata = json.loads(str(saved['metadata']))
        arrays = {k: saved[k] for k in types}
        extras = {'lesion_instance', 'lesion_metadata'} & set(saved.files)
        if extras and len(extras) != 2:
            raise ValueError('lesion labels and metadata must be paired')
        lesion_meta = json.loads(str(saved['lesion_metadata'])) if extras else None
        if extras:
            arrays['lesion_instance'] = saved['lesion_instance']
    if any(metadata.get(k) != v for k, v in dict(schema='vv-toolbox.mask/1', axes='LPS', units='mm', array_order='zyx').items()):
        raise ValueError('unsupported mask coordinates or schema')
    affine = np.asarray(metadata['voxel_xyz_to_world_mm'], dtype=float)
    if affine.shape != (4, 4):
        raise ValueError('invalid voxel affine')
    grid = Grid(tuple(metadata['shape_zyx']), tuple(metadata['spacing_xyz_mm']),
                tuple(affine[:3, 3].tolist()), metadata['frame_id'])
    if not np.array_equal(grid.affine_xyz, affine):
        raise ValueError('affine and spacing mismatch')
    instances = metadata['instances']
    ids = [s['instance_id'] for s in instances]
    if any(type(i) is not int or not 0 < i <= np.iinfo(np.uint32).max for i in ids) or ids != sorted(set(ids)):
        raise ValueError('unique increasing instance IDs required')
    for key, dtype in types.items():
        shape = (len(ids), *grid.shape_zyx) if key == 'membership' else grid.shape_zyx
        if arrays[key].shape != shape or arrays[key].dtype != np.dtype(dtype) or metadata['dtypes'][key] != dtype:
            raise ValueError(f'{key} shape or dtype mismatch')
    count = np.zeros(grid.shape_zyx, dtype=np.uint32)
    owner = np.zeros_like(count)
    anatomy = np.zeros_like(count)
    provenance = np.zeros(grid.shape_zyx, dtype=np.uint8)
    for row, spec in enumerate(instances):
        label = spec['anatomical_label']
        if type(label) is not int or not 0 <= label <= np.iinfo(np.uint32).max or spec['provenance'] not in ('source', 'estimated'):
            raise ValueError('invalid instance label or provenance')
        mask = arrays['membership'][row]
        first = mask & (count == 0)
        conflict = mask & (count > 0) & (anatomy != label)
        owner[first], anatomy[first] = spec['instance_id'], label
        anatomy[conflict] = 0
        provenance[mask] |= 1 if spec['provenance'] == 'source' else 2
        count[mask] += 1
    for key, expected in dict(foreground=count > 0, overlap_count=count, instance=owner,
                              anatomical=anatomy, provenance=provenance).items():
        if not np.array_equal(arrays[key], expected):
            raise ValueError(f'{key} disagrees with memberships')
    if extras:
        labels = arrays['lesion_instance']
        if labels.shape != grid.shape_zyx or labels.dtype != np.uint32 or not isinstance(lesion_meta, dict):
            raise ValueError('invalid aligned lesion labels')
        if np.any((labels > 0) & ~arrays['foreground']):
            raise ValueError('lesion labels outside foreground')
    return arrays, metadata, lesion_meta
