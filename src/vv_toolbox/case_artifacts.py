"""Content-bound generated case bundles; byte integrity is not geometry approval."""
import hashlib
import json
from pathlib import Path

from .case_io import _encode, _unique_object, load_case

SCHEMA = 'vv-toolbox.case-artifacts/1'
MANIFEST = 'artifacts.json'


def _digest(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(folder, *, case_revision, generation, coverage, quality):
    """Write inside a pending directory, before its atomic publication."""
    folder = Path(folder)
    _, revision = load_case(folder/'case.snapshot.json')
    if revision != case_revision:
        raise ValueError('Case revision differs from artifact manifest')
    files = {}
    for path in sorted(folder.iterdir()):
        if path.name == MANIFEST or path.is_symlink() or not path.is_file():
            raise ValueError('Unexpected entry in pending artifact bundle')
        files[path.name] = dict(bytes=path.stat().st_size, sha256=_digest(path))
    if not {'case.snapshot.json','surface.npz'} <= set(files):
        raise ValueError('Case snapshot and surface are required')
    manifest = dict(schema=SCHEMA, case_revision=case_revision, generation=generation,
                    surface_coverage=coverage, quality=quality, files=files,
                    integrity_scope='Exact file bytes and case revision; not anatomical or clinical acceptance')
    encoded = _encode(manifest)
    with (folder/MANIFEST).open('xb') as stream:
        stream.write(encoded)
    return hashlib.sha256(encoded).hexdigest()


def verify_manifest(folder, *, expected_sha256):
    """Verify against the digest stored outside this bundle (e.g. batch report)."""
    folder = Path(folder)
    path = folder/MANIFEST
    if path.is_symlink() or _digest(path) != expected_sha256:
        raise ValueError('Artifact manifest hash mismatch')
    manifest = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=_unique_object)
    if (not isinstance(manifest,dict) or manifest.get('schema') != SCHEMA
            or set(manifest) != {'schema','case_revision','generation','surface_coverage','quality','files','integrity_scope'}
            or not isinstance(manifest.get('files'), dict)):
        raise ValueError('Invalid artifact manifest')
    files = manifest['files']
    if not {'case.snapshot.json','surface.npz'} <= set(files):
        raise ValueError('Required artifacts missing from manifest')
    for name, record in files.items():
        if (not isinstance(name,str) or name in ('', '.', '..', MANIFEST)
                or '/' in name or '\\' in name or ':' in name):
            raise ValueError('Artifact names must be simple file names')
        artifact = folder/name
        if artifact.is_symlink() or not artifact.is_file():
            raise ValueError(f'Missing or linked artifact: {name}')
        if not isinstance(record,dict) or record.get('bytes') != artifact.stat().st_size or record.get('sha256') != _digest(artifact):
            raise ValueError(f'Artifact bytes differ: {name}')
    if {p.name for p in folder.iterdir()} != set(files) | {MANIFEST}:
        raise ValueError('Unexpected files in artifact bundle')
    _, revision = load_case(folder/'case.snapshot.json')
    if revision != manifest.get('case_revision'):
        raise ValueError('Artifact case revision mismatch')
    return dict(status='PASS', scope='File integrity and case revision only',
                artifact_count=len(files), case_revision=revision,
                quality=manifest['quality'])


def verify_masks(folder, *, expected_sha256, max_bytes=256*1024**2):
    """Verify bundle integrity, then saved mask coordinates and memberships."""
    import numpy as np
    from .volume_io import load_volume
    verified = verify_manifest(folder, expected_sha256=expected_sha256)
    folder = Path(folder)
    case, _ = load_case(folder/'case.snapshot.json')
    lesions = {entry['lesion_id']: entry['edge_id'] for entry in case.get('lesions', [])}
    names = sorted(p.name for p in folder.iterdir()
                   if p.name == 'mask.npz' or (p.name.startswith('lesion-roi-') and p.suffix == '.npz'))
    if not names:
        raise ValueError('Bundle contains no mask archives')
    results = []
    for name in names:
        arrays, metadata, lesion_meta = load_volume(folder/name, max_bytes=max_bytes)
        if lesion_meta is None or lesion_meta.get('case_revision') != verified['case_revision']:
            raise ValueError(f'Mask case revision mismatch: {name}')
        if metadata['frame_id'] != case['frame']['id'] or lesion_meta.get('grid') != metadata:
            raise ValueError(f'Mask frame or lesion grid mismatch: {name}')
        registry = lesion_meta.get('registry', [])
        if (not isinstance(registry, list) or len(registry) != len(lesions)
                or {entry['lesion_id']: entry['edge_id'] for entry in registry} != lesions):
            raise ValueError(f'Mask lesion registry differs from case: {name}')
        labels = [entry['label'] for entry in registry]
        if (any(type(label) is not int or label <= 0 for label in labels)
                or len(set(labels)) != len(labels)
                or not set(np.unique(arrays['lesion_instance'])).issubset({0, *labels})):
            raise ValueError(f'Mask has unknown or duplicate lesion labels: {name}')
        for entry in registry:
            if int(np.count_nonzero(arrays['lesion_instance'] == entry['label'])) != entry['sampled_voxels']:
                raise ValueError(f'Mask lesion voxel count mismatch: {name}')
        results.append(dict(file=name, shape_zyx=metadata['shape_zyx'],
                            foreground_voxels=int(arrays['foreground'].sum())))
    return dict(status='PASS', scope='File integrity, case revision and mask coordinate/label consistency; not source geometry validation',
                case_revision=verified['case_revision'], masks=results)


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    parser.add_argument('--expected-sha256', required=True,
                        help='artifact_manifest_sha256 from the batch report')
    parser.add_argument('--validate-masks', action='store_true',
                        help='Also reload and check masks against saved memberships')
    args = parser.parse_args(argv)
    try:
        verifier = verify_masks if args.validate_masks else verify_manifest
        print(json.dumps(verifier(args.folder, expected_sha256=args.expected_sha256)))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(2, str(error)+'\n')


if __name__ == '__main__':
    main()
