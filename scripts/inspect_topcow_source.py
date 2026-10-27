"""Audit the official small TopCoW LargeIA annotation archive (run in Docker)."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import urllib.request
import zipfile
import re

import nibabel as nib
import numpy as np
import yaml

URL = 'https://zenodo.org/records/15692630/files/CTA_LargeIA.zip'
EXPECTED_MD5 = '83cf2f4df95738eb5f76c6eb6b78c3bf'


def main():
    root = Path('reference-data/topcow-largeia')
    root.mkdir(parents=True, exist_ok=True)
    archive = root / 'CTA_LargeIA.zip'
    if not archive.exists():
        with urllib.request.urlopen(URL, timeout=120) as response:
            archive.write_bytes(response.read())
    raw = archive.read_bytes()
    md5 = hashlib.md5(raw).hexdigest()
    if md5 != EXPECTED_MD5:
        raise ValueError(f'Archive MD5 mismatch: {md5}')
    result = {'url': URL, 'bytes': len(raw), 'md5': md5,
              'sha256': hashlib.sha256(raw).hexdigest(), 'files': [],
              'masks': [], 'edges': {}, 'roi': {}}
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            name = info.filename
            result['files'].append({'name': name, 'bytes': info.file_size})
            data = z.read(info)
            if name.endswith('.yml'):
                result['edges'][name] = yaml.safe_load(data)
            elif name.endswith('.txt'):
                result['roi'][name] = data.decode('utf-8')
            elif name.endswith('.nii.gz'):
                unpacked = gzip.decompress(data)
                img = nib.Nifti1Image.from_bytes(unpacked)
                values, counts = np.unique(np.asanyarray(img.dataobj), return_counts=True)
                result['masks'].append({
                    'name': name, 'shape': list(img.shape),
                    'dtype': str(img.get_data_dtype()),
                    'spacing': [float(x) for x in img.header.get_zooms()],
                    'units': list(img.header.get_xyzt_units()),
                    'axis_codes': list(nib.aff2axcodes(img.affine)),
                    'affine': img.affine.tolist(),
                    'qform_code': int(img.header['qform_code']),
                    'sform_code': int(img.header['sform_code']),
                    'labels': {str(int(v)): int(c) for v, c in zip(values, counts)},
                    'sha256': hashlib.sha256(data).hexdigest(),
                })
    groups = {}
    for item in result['files']:
        parent = str(Path(item['name']).parent)
        case = re.search(r'Tr(?:_ct_)?(\d{4})', item['name'])
        if case:
            groups.setdefault(parent, []).append(case.group(1))
    result['case_groups'] = groups
    result['case_groups_match'] = (len(groups) == 5 and
        all(len(ids) == 20 and len(set(ids)) == 20 for ids in groups.values()) and
        len({tuple(sorted(ids)) for ids in groups.values()}) == 1)
    result['edge_schema_valid'] = all(
        set(edge) == {'anterior', 'posterior'} and
        set(edge['anterior']) == {'L-A1', 'Acom', '3rd-A2', 'R-A1'} and
        set(edge['posterior']) == {'L-Pcom', 'L-P1', 'R-P1', 'R-Pcom'} and
        all(value in (0, 1) for region in edge.values() for value in region.values())
        for edge in result['edges'].values())
    out = Path('exports/source-audit')
    out.mkdir(parents=True, exist_ok=True)
    (out / 'topcow-largeia.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'bytes': result['bytes'], 'sha256': result['sha256'],
                      'files': len(result['files']), 'masks': len(result['masks']),
                      'edges': len(result['edges']), 'roi': len(result['roi']),
                      'case_groups_match': result['case_groups_match'],
                      'edge_schema_valid': result['edge_schema_valid']}))


if __name__ == '__main__':
    main()
