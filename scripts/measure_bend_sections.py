"""Paired bend sections at corresponding source-polyline stations."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.case_io import load_case
from vv_toolbox.source_sections import extract_source_sections


def main():
    root = Path('docs/evidence')
    read = lambda name: json.loads((root/name).read_text())
    graph_check = read('access-bend-graph.json')
    parent = read('resampled-access-protected.json')
    edit = read('access-shape-edit-bend.json')
    before_graph, before_revision = load_case('exports/femoral-anterior-graph/case.snapshot.json')
    after_graph, after_revision = load_case(graph_check['graph_file'])
    if before_revision != graph_check['parent_graph_revision'] or after_revision != graph_check['graph_revision']:
        raise ValueError('Paired graph revision mismatch')
    if edit['parent_surface_sha256'] != parent['output_sha256']:
        raise ValueError('Bend surface parent mismatch')
    before = next(e for e in before_graph['edges'] if e.get('source_part_id') == 'FJ2074')
    after = next(e for e in after_graph['edges'] if e['id'] == before['id'])
    original = np.asarray(before['centerline_mm'])
    changed = np.asarray(after['centerline_mm'])
    if original.shape != changed.shape:
        raise ValueError('Corresponding path stations required')
    arc = np.r_[0., np.cumsum(np.linalg.norm(np.diff(original, axis=0), axis=1))]
    stations = np.linspace(0., arc[-1], 33)
    paths = [np.column_stack([np.interp(stations, arc, p[:, k]) for k in range(3)]) for p in (original, changed)]
    profiles = []
    hashes = []
    for index, record in enumerate((parent, edit)):
        artifact = Path(record['artifact'])
        hashes.append(hashlib.sha256(artifact.read_bytes()).hexdigest())
        if index == 0 and hashes[-1] != parent['output_sha256']:
            raise ValueError('Parent artifact hash mismatch')
        with np.load(artifact, allow_pickle=False) as data:
            vertices, faces = data['vertices'], data['faces']
        if index == 1 and hashlib.sha256(vertices.astype('<f8').tobytes()+faces.astype('<i8').tobytes()).hexdigest() != graph_check['geometry_sha256']:
            raise ValueError('Bend graph/surface hash mismatch')
        profiles.append(extract_source_sections(trimesh.Trimesh(vertices, faces, process=False), paths[index])['profiles'])
    if any(len(p) != 31 for p in profiles):
        raise ValueError('Incomplete paired section coverage')
    rows = []
    for a, b in zip(*profiles):
        if a['index'] != b['index']:
            raise ValueError('Paired station indices differ')
        row = dict(index=a['index'], original_arclength_mm=float(stations[a['index']]), before=a, after=b,
                   status='MEASURED' if a['status'] == b['status'] == 'MEASURED' else 'UNKNOWN')
        if row['status'] == 'MEASURED':
            row['equivalent_radius_ratio'] = b['area_equivalent_radius_mm']/a['area_equivalent_radius_mm']
        rows.append(row)
    ratios = [r['equivalent_radius_ratio'] for r in rows if r['status'] == 'MEASURED']
    report = dict(status='MEASURED' if len(ratios) == 31 else 'UNKNOWN', rows=rows,
        before_graph_revision=before_revision, after_graph_revision=after_revision,
        artifact_sha256=hashes, measured_sections=len(ratios),
        radius_ratio_range=[min(ratios), max(ratios)] if ratios else None,
        scope='31 corresponding source-arclength stations; separate local normal planes before/after; not continuous radius bounds',
        radius_preservation_acceptance='NOT RUN', anatomical_validation='NOT RUN')
    (root/'access-bend-sections.json').write_text(json.dumps(report, indent=2)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    measured = [r for r in rows if r['status'] == 'MEASURED']
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), layout='constrained')
    positions = [r['original_arclength_mm'] for r in measured]
    for key, label in [('before', 'Original'), ('after', 'Bend candidate')]:
        axes[0].plot(positions, [r[key]['area_equivalent_radius_mm'] for r in measured], label=label)
    axes[0].set(xlabel='Original path station (mm)', ylabel='Area-equivalent radius (mm)')
    axes[0].legend()
    axes[1].plot(positions, [r['equivalent_radius_ratio'] for r in measured], '.-', color='#a52842')
    axes[1].axhline(1, color='gray', linestyle='--', label='Unchanged radius')
    axes[1].set(xlabel='Original path station (mm)', ylabel='After / before radius')
    axes[1].ticklabel_format(axis='y', style='plain', useOffset=False)
    axes[1].legend()
    fig.suptitle('Femoral bend 0.25 mm | 31 sampled sections | acceptance NOT RUN')
    image = Path('exports/access-shape-edit-bend/section-comparison.png')
    fig.savefig(image, dpi=160)
    plt.close(fig)
    report.update(image=str(image), image_sha256=hashlib.sha256(image.read_bytes()).hexdigest())
    (root/'access-bend-sections.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k != 'rows'}), flush=True)


if __name__ == '__main__':
    main()
