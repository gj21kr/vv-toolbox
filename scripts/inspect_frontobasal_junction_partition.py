"""Reassemble the original FJ1690 junction and arms at shared port vertices."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.atlas import load_atlas
from vv_toolbox.junction_partition import partition_source_junction
from vv_toolbox.mesh_self_contact import inspect_self_contact
from vv_toolbox.surface_indexing import exact_vertex_index_copy


def main():
    root = Path(__file__).resolve().parents[1]
    prior_path = root/'docs/evidence/frontobasal-source-junction.json'
    prior = json.loads(prior_path.read_text())
    if prior['status'] != 'CANDIDATE':
        raise ValueError('Measured junction ports required')
    if hashlib.sha256((root/prior['artifact']).read_bytes()).hexdigest() != prior['sha256']:
        raise ValueError('Junction artifact changed')
    atlas = load_atlas()
    if atlas.metadata['sha256'] != prior['atlas_archive_sha256']:
        raise ValueError('Atlas identity changed')
    part = next(p for p in atlas.meshes if p['id'] == 'FJ1690')
    source, _ = exact_vertex_index_copy(trimesh.Trimesh(part['vertices'], part['faces'], process=False))
    result = dict(schema='vv-toolbox.frontobasal-junction-partition/1',
        parent_report_sha256=hashlib.sha256(prior_path.read_bytes()).hexdigest(),
        atlas_archive_sha256=atlas.metadata['sha256'], ports=prior['ports'],
        accepted_for_generation=False, scope='Complete unmodified source surface, conforming junction/arm partition',
        modified_arm_attachment='NOT RUN', surrounding_clearance='NOT RUN')
    try:
        mesh, lineage, labels, meta = partition_source_junction(source,
            [p['origin_mm'] for p in prior['ports']], [p['outward_normal'] for p in prior['ports']], prior['junction_mm'])
        contact = inspect_self_contact(mesh.vertices, mesh.faces)
        result.update(status='CANDIDATE', partition=meta, self_contact=contact,
            vertices=len(mesh.vertices), faces=len(mesh.faces),
            source_area_mm2=float(source.area), area_mm2=float(mesh.area),
            source_volume_mm3=float(source.volume), volume_mm3=float(mesh.volume))
        output = root/'exports/frontobasal-junction-partition.npz'
        with output.open('xb') as stream:
            np.savez_compressed(stream, vertices_mm=mesh.vertices, faces=mesh.faces,
                source_face_ids=lineage, face_region_labels=labels, metadata=np.array(json.dumps(meta)))
        result.update(artifact=str(output.relative_to(root)), sha256=hashlib.sha256(output.read_bytes()).hexdigest())
    except ValueError as error:
        result.update(status='FAIL', reason=str(error))
    (root/'docs/evidence/frontobasal-junction-partition.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ('status','reason','vertices','faces') if k in result}), flush=True)


if __name__ == '__main__':
    main()
