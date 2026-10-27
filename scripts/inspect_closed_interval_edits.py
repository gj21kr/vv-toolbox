"""Fit interval probes to source topology with explicit contact/end protection."""
import hashlib
import io
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.atlas import load_atlas
from vv_toolbox.protected_preview import load_protected_preview
from vv_toolbox.protected_surface_fit import fit_protected_surface
from vv_toolbox.surface_indexing import exact_vertex_index_copy
from vv_toolbox.mesh_self_contact import inspect_self_contact


def main():
    root = Path(__file__).resolve().parents[1]
    load_protected_preview(root)
    protection_raw = (root / 'docs/evidence/protected-cerebral-fit.json').read_bytes()
    protection = json.loads(protection_raw)
    protected = {r['edge_id']: r for r in protection['rows']}
    edit_raw = (root / 'docs/evidence/profile-interval-edits.json').read_bytes()
    edits = json.loads(edit_raw)
    profile_raw = (root / 'docs/evidence/cerebral-smoothed-section-profiles-window2mm.json').read_bytes()
    if hashlib.sha256(profile_raw).hexdigest() != edits['profile_index_sha256']:
        raise ValueError('Profile index changed')
    profiles = {r['edge_id']: r for r in json.loads(profile_raw)['rows']}
    atlas = load_atlas()
    if atlas.metadata['sha256'] != protection['atlas_archive_sha256']:
        raise ValueError('Atlas changed')
    parts = {p['id']: p for p in atlas.meshes}
    rows = []
    for edit in edits['rows']:
        ident = edit['edge_id']
        source_entry = protected[ident]
        part = parts[source_entry['source_part_id']]
        source = trimesh.Trimesh(part['vertices'], part['faces'], process=False)
        data = (root / profiles[ident]['artifact']).read_bytes()
        if hashlib.sha256(data).hexdigest() != edit['profile_sha256']:
            raise ValueError('Profiles changed')
        points = np.array([p['origin_mm'] for p in json.loads(data)['profiles']])
        delta = np.diff(points, axis=0)
        lengths = np.linalg.norm(delta, axis=1)
        arc = np.r_[0., np.cumsum(lengths)]
        # Assign each source vertex its closest polyline location in native mm.
        relative = source.vertices[:, None] - points[:-1]
        fraction = np.clip(np.einsum('vsi,si->vs', relative, delta) / lengths**2, 0, 1)
        residual = relative - fraction[:, :, None] * delta
        nearest = np.argmin(np.einsum('vsi,vsi->vs', residual, residual), axis=1)
        location = arc[nearest] + fraction[np.arange(len(nearest)), nearest] * lengths[nearest]
        outside = np.flatnonzero((location <= edit['start_mm']) | (location >= edit['end_mm']))
        fixed = sorted(set(source_entry['protected_vertex_ids']) | set(outside.tolist()))
        raw = (root / edit['artifact']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != edit['sha256']:
            raise ValueError('Edited loft changed')
        target = trimesh.load(io.BytesIO(raw), file_type='ply', process=False)
        row = dict(edge_id=ident, factor=edit['factor'], target_sha256=edit['sha256'],
                   protected_vertex_ids=fixed, original_contact_vertices=len(source_entry['protected_vertex_ids']),
                   outside_interval_vertices=len(outside))
        try:
            candidate, metadata = fit_protected_surface(
                source, target, fixed, max_displacement_mm=.3, transition_rings=3)
        except ValueError as error:
            row.update(status='FAIL', reason=str(error))
        else:
            payload = candidate.export(file_type='ply')
            saved = trimesh.load(io.BytesIO(payload), file_type='ply', process=False)
            if not np.array_equal(saved.vertices[fixed], source.vertices[fixed]):
                raise ValueError('Protected serialization mismatch')
            normalized, topology = exact_vertex_index_copy(saved)
            contact = inspect_self_contact(normalized.vertices, normalized.faces)
            digest = hashlib.sha256(payload).hexdigest()
            path = root / 'exports/closed-interval-edits' / digest / 'surface.ply'
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists() and path.read_bytes() != payload:
                raise ValueError('Artifact mismatch')
            path.write_bytes(payload)
            row.update(status='CANDIDATE', metadata=metadata, topology=topology,
                       self_contact=contact, sha256=digest,
                       artifact=path.relative_to(root).as_posix())
        rows.append(row)
        print(json.dumps(dict(edge_id=ident, factor=edit['factor'], status=row['status'],
                              reason=row.get('reason'), self_contact=row.get('self_contact', {}).get('status'))),
              flush=True)
    report = dict(rows=rows, source_edits_sha256=hashlib.sha256(edit_raw).hexdigest(),
                  protection_report_sha256=hashlib.sha256(protection_raw).hexdigest(),
                  atlas_archive_sha256=atlas.metadata['sha256'], max_displacement_mm=.3,
                  transition_rings=3, original_modified=False,
                  achieved_section_scale='NOT RUN', surroundings='NOT RUN',
                  anatomical_validation='NOT RUN',
                  scope='Closed topology projections with original contact/end and nearest-path interval protection')
    (root / 'docs/evidence/closed-interval-edits.json').write_text(
        json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
