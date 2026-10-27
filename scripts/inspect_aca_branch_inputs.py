"""Bind the next ACA junction inputs without approving specimen connectivity."""
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.atlas import load_atlas
from vv_toolbox.atlas_topology import reference_junctions
from vv_toolbox.case_io import load_case
from vv_toolbox.surface_indexing import exact_vertex_index_copy


def main():
    record=json.loads(Path('docs/evidence/atlas-neck-volume-case.json').read_text())
    case,revision=load_case(record['derived_case_file'])
    parts={p['part_id']:p for p in case['surface_parts']}
    atlas=load_atlas()
    names={p['id']:p['name'] for p in atlas.metadata['parts']}
    junctions=reference_junctions(atlas.metadata['parts'])
    context=json.loads(Path('docs/evidence/left-carotid-aca-context.json').read_text())
    if context['source_case_revision']!=revision:
        raise ValueError('Source/context revisions differ')
    contacts={row['neighbor_id']:row for row in context['rows']}
    rows=[]
    for pid in ('FJ1655','FJ1676M','FJ1690M','FJ1699M'):
        part=parts[pid]
        mesh,topology=exact_vertex_index_copy(trimesh.Trimesh(
            np.asarray(part['vertices_mm']),np.asarray(part['faces']),process=False))
        references=[]
        for junction in junctions:
            ids={i for member in junction['members'] for i in member['part_ids']}
            if {pid,'FJ1654M'}<=ids:
                references.append(dict(id=junction['id'],source_url=junction['source_url'],
                                       specimen_status=junction['specimen_status']))
        rows.append(dict(part_id=pid,name=names[pid],geometry_sha256=part['geometry_sha256'],
                         vertices=len(mesh.vertices),faces=len(mesh.faces),positive_volume=bool(mesh.is_volume),
                         topology=topology,context_status=contacts[pid]['status'],
                         reference_relations=references,specimen_connection='UNKNOWN',
                         anatomical_segment_boundary='UNKNOWN'))
    Path('docs/evidence/aca-branch-inputs.json').write_text(json.dumps(dict(
        source_case_revision=revision,rows=rows,
        scope='Source identity, closed-surface prerequisites and existing reference relation coverage',
        anatomical_validation='NOT RUN',live_scene_changed=False),indent=2)+'\n')
    print(json.dumps([{key:r[key] for key in ('part_id','name','positive_volume','reference_relations')} for r in rows]))


if __name__=='__main__':
    main()
