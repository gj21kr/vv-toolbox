"""Export explicit surface masks and optional aligned crops as portable NPZ."""
import argparse
import json
import os
from pathlib import Path
import tempfile

import numpy as np

from .voxel_output import Grid, Surface, voxelize, crop


def save_volume(path, volume, *, lesion_labels=None, lesion_metadata=None):
    """Publish a complete archive without overwriting an existing artifact."""
    extra = {}
    if lesion_labels is not None or lesion_metadata is not None:
        if (not isinstance(lesion_labels,np.ndarray) or lesion_labels.shape != volume.foreground.shape
                or lesion_labels.dtype != np.uint32 or not isinstance(lesion_metadata,dict)):
            raise ValueError('aligned uint32 lesion labels and metadata required')
        if np.any((lesion_labels > 0) & ~volume.foreground):
            raise ValueError('lesion lumen labels cannot lie outside foreground')
        extra = {'lesion_instance':lesion_labels,'lesion_metadata':np.array(json.dumps(lesion_metadata))}
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=target.parent, suffix='.npz.tmp')
    try:
        with os.fdopen(fd, 'wb') as stream:
            np.savez_compressed(stream, metadata=np.array(json.dumps(volume.metadata())), **extra,
                **{key: getattr(volume, key) for key in
                   ('foreground', 'anatomical', 'instance', 'provenance', 'overlap_count', 'membership')})
            stream.flush()
            os.fsync(stream.fileno())
        # Same-directory hard link commits a complete file and fails if it exists.
        os.link(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Rasterize explicit closed surfaces; no anatomy inference')
    parser.add_argument('manifest', type=Path, help='JSON containing grid and inline surfaces')
    parser.add_argument('output', type=Path)
    parser.add_argument('--max-bytes', type=int, default=256*1024**2)
    parser.add_argument('--case-snapshot', type=Path)
    parser.add_argument('--edge-instances', type=Path, help='Explicit JSON edge ID to surface instance ID list')
    parser.add_argument('--crop', type=int, nargs=6, metavar=('Z0', 'Y0', 'X0', 'Z1', 'Y1', 'X1'))
    args = parser.parse_args(argv)
    try:
        manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
        if manifest.get('schema') != 'vv-toolbox.surface-mask-input/1':
            raise ValueError('unsupported surface input schema')
        grid = Grid(**manifest['grid'])
        surfaces = [Surface(**s) for s in manifest['surfaces']]
        volume = voxelize(surfaces, grid, max_bytes=args.max_bytes)
        if args.crop:
            volume = crop(volume, args.crop[:3], args.crop[3:])
        labels, lesion_meta = None, None
        if bool(args.case_snapshot) != bool(args.edge_instances):
            raise ValueError('case-snapshot and edge-instances must be supplied together')
        if args.case_snapshot:
            from .case_io import load_case
            from .lesion_labels import label_lesion_lumen
            case, _ = load_case(args.case_snapshot)
            mapping = json.loads(args.edge_instances.read_text(encoding='utf-8'))
            labels, lesion_meta = label_lesion_lumen(volume,case,mapping,max_bytes=args.max_bytes)
            if lesion_meta['status'] != 'PASS':
                raise ValueError('lesion sampling unresolved; refine grid or choose a covering ROI')
        save_volume(args.output, volume,lesion_labels=labels,lesion_metadata=lesion_meta)
        print(json.dumps({'status': 'PASS', 'scope': 'explicit surface voxelization',
            'shape_zyx': list(volume.foreground.shape),
            'foreground_voxels': int(volume.foreground.sum()),
            'overlap_voxels': int((volume.overlap_count > 1).sum()),
            'anatomical_unknown_foreground_voxels': int((volume.foreground & (volume.anatomical == 0)).sum())}))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, str(exc) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
