"""Five fixed correction iterations against measured source section targets."""
import hashlib
import json
import numpy as np
import trimesh
from inspect_atlas_edit_sections import load_candidate, sections, containment, ROOT
from vv_toolbox.atlas_modification import _anchor_weight
from vv_toolbox.section_radius_correction import correct_radially
from vv_toolbox.mesh_self_contact import inspect_self_contact


def main():
    prior, source, edited, edges, paths, meshes = load_candidate()
    if len(edges) != 1:
        raise ValueError('Single-path correction experiment only')
    original, path = edges[0], paths[0]
    source_sections = sections(meshes[0], original)
    if any(s['status'] != 'MEASURED' for s in source_sections):
        raise ValueError('Source sections incomplete')
    target = np.array([s['metrics']['area_equivalent_radius_mm'] *
                       path['radii'][s['index']]/original['radii'][s['index']]
                       for s in source_sections])
    p = np.asarray(original['points'])
    length = np.linalg.norm(np.diff(p,axis=0),axis=1).sum()
    collars = list(np.maximum(np.asarray(original['radii'])[[0,-1]]*1.5, min(length*.04,2.)))
    anchors = [p[0],p[-1]]
    widths = list(collars)
    for region in prior['protected_regions']:
        anchors.append(region['center_mm'])
        collars.append(region['radius_mm'])
        widths.append(region['transition_width_mm'])
    weights = _anchor_weight(source['vertices'],anchors,collars,widths,blend='product')
    vertices = np.asarray(edited['vertices']).copy()
    rows = []
    for iteration in range(6):
        mesh = trimesh.Trimesh(vertices,edited['faces'],process=False)
        measured = sections(mesh,path)
        if any(s['status']!='MEASURED' for s in measured):
            rows.append(dict(iteration=iteration,status='INCOMPLETE_SECTIONS'))
            break
        radius = np.array([s['metrics']['area_equivalent_radius_mm'] for s in measured])
        relative = radius/target-1.
        contact = inspect_self_contact(vertices,edited['faces'])
        row = dict(iteration=iteration,
                   maximum_absolute_relative_target_error=float(np.abs(relative).max()),
                   median_absolute_relative_target_error=float(np.median(np.abs(relative))),
                   self_contact=contact, sections=measured,
                   containment=containment(mesh,np.asarray(path['points'])),
                   fixed_vertices_exact=bool(np.array_equal(vertices[weights==0],source['vertices'][weights==0])))
        rows.append(row)
        print(json.dumps({k:v for k,v in row.items() if k not in ('sections','self_contact','containment')} |
                         dict(contact_pairs=len(contact['contact_pairs']))),flush=True)
        if iteration < 5:
            gains=np.ones(len(path['points']))
            gains[1:-1]=target/radius
            vertices=correct_radially(vertices,path['points'],gains,weights)
    report=dict(part_id=prior['part_id'],parameters=prior['parameters'],
                starting_surface_sha256=prior['surface_sha256']['after'],
                source_export_sha256=prior['input_export_sha256'],
                target_area_radii_mm=target.tolist(),rows=rows,
                final_surface_sha256=hashlib.sha256(np.asarray(vertices[edited['faces']],dtype='<f8').tobytes()).hexdigest(),
                live_workspace_modified=False,
                limitation='Single MCA, five predetermined iterations. Target uses source measured area radius times reported local scale. Surrounding-vessel intersections NOT RUN.')
    (ROOT/'docs/evidence/atlas-mca-section-correction.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    main()
