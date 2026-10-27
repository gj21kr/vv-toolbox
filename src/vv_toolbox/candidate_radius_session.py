"""Isolated radius edit transactions; original Atlas data is never mutated."""
import copy
import hashlib
import secrets

import numpy as np
import trimesh

from .union_radius import scale_selected_radius
from .centerline_containment import inspect_centerline_containment


class CandidateRadiusSession:
    """Caller serializes publish/apply/undo; computation uses detached snapshots."""

    def __init__(self, candidate):
        self._base = copy.deepcopy(candidate)
        self._current = copy.deepcopy(candidate)
        self._undo = []
        self._operations = []
        self._pending = None
        self.version = 0

    def current(self):
        return copy.deepcopy(self._current)

    def status(self):
        return dict(undo_available=bool(self._undo),
                    preview_token=self._pending['token'] if self._pending else None,
                    version=self.version)

    def snapshot(self, source_name):
        paths = self._current.get('source_centerlines', {})
        if source_name not in paths:
            raise ValueError('Explicit source centerline unavailable')
        return dict(version=self.version, candidate=self.current(), source_name=source_name)

    @staticmethod
    def compute(snapshot, *, scale, transition_mm, max_displacement_mm, progress=None, _validation_cache=None):
        if progress is not None and not callable(progress):
            raise ValueError('Progress callback must be callable')
        def emit(phase, completed, total):
            if progress is not None:
                progress(dict(phase=phase, completed=completed, total=total))
        emit('geometry', 0, 1)
        candidate = copy.deepcopy(snapshot['candidate'])
        candidate.pop('radius_context', None)
        source = snapshot['source_name']
        path = candidate['source_centerlines'][source]
        if path['case_revision'] != candidate['summary']['revision']:
            raise ValueError('Source path revision mismatch')
        mesh = trimesh.Trimesh(candidate['vertices_mm'], candidate['faces'], process=False)
        output, audit = scale_selected_radius(
            mesh, candidate['face_lineage'], source, path['points_mm'],
            scale=scale, transition_mm=transition_mm,
            max_displacement_mm=max_displacement_mm, _validation_cache=_validation_cache)
        emit('geometry', 1, 1)
        candidate['vertices_mm'] = output.vertices.copy()
        summary = candidate['summary']
        summary['parent_surface_sha256'] = summary.pop('surface_sha256', None) or summary.get('geometry_sha256')
        summary['geometry_sha256'] = hashlib.sha256(
            np.asarray(output.vertices, dtype='<f8').tobytes() +
            np.asarray(output.faces, dtype='<i8').tobytes()).hexdigest()
        # These inspections described the input surface, not this deformation.
        if 'access_union' in summary:
            access = summary['access_union']
            access.update(lineage_faces='NOT RUN', centerline_status='NOT RUN',
                          checked_paths=0, checked_segments=0, context_status='NOT RUN',
                          context_completed=0, contacts=[], unknown=[])
            edges = candidate.get('edges', [])
            expected = summary.get('access_graph', {}).get('edges')
            if not edges or len(edges) != expected or len({e['id'] for e in edges}) != expected:
                raise ValueError('Complete access graph required for radius editing')
            rows = []
            emit('centerlines', 0, expected)
            for edge in edges:
                rows.append(dict(edge_id=edge['id'], **inspect_centerline_containment(output, edge['centerline_mm'])))
                emit('centerlines', len(rows), expected)
            states = [row['status'] for row in rows]
            status = 'FAIL' if 'FAIL' in states else 'UNKNOWN' if any(s != 'PASS' for s in states) else 'PASS'
            audit['centerline_containment'] = dict(status=status, expected_edges=expected,
                                                 geometry_sha256=summary['geometry_sha256'], rows=rows)
            access.update(centerline_status=status, checked_paths=len(rows),
                          checked_segments=sum(row['segment_count'] for row in rows))
        else:
            summary['carotid_union'] = dict(
                self_contact=audit['self_contact']['status'], path_segments='NOT RUN',
                lineage_faces='NOT RUN', new_contacting_neighbors='NOT RUN')
        summary['radius_edit'] = audit
        summary['smoothness'] = 'NOT RUN'
        summary['anatomy'] = 'UNKNOWN'
        summary['read_only'] = True
        return dict(version=snapshot['version'], candidate=candidate, audit=audit)

    def publish(self, result):
        if result['version'] != self.version:
            raise ValueError('Scene changed while computing radius preview')
        token = secrets.token_hex(16)
        self._pending = dict(token=token, result=copy.deepcopy(result))
        return dict(token=token, audit=copy.deepcopy(result['audit']))

    def preview(self):
        if self._pending is None:
            raise ValueError('No radius preview')
        return copy.deepcopy(self._pending['result']['candidate'])

    def apply(self, token):
        if self._pending is None or not secrets.compare_digest(token, self._pending['token']):
            raise ValueError('Radius preview token mismatch')
        if self._pending['result']['version'] != self.version:
            raise ValueError('Radius preview is stale')
        self._undo.append(self.current())
        self._current = copy.deepcopy(self._pending['result']['candidate'])
        audit = self._pending['result']['audit']
        self._operations.append(dict(
            source_name=audit['source_name'], scale=audit['scale'],
            transition_mm=audit['transition_mm'], max_displacement_mm=audit['displacement_bound_mm'],
            output_geometry_sha256=self._current['summary']['geometry_sha256']))
        self._pending = None
        self.version += 1
        return self.current()

    def undo(self):
        if not self._undo:
            raise ValueError('No radius edit to undo')
        self._current = self._undo.pop()
        self._operations.pop()
        self._pending = None
        self.version += 1
        return self.current()

    def discard(self):
        self._pending = None

    def export_text(self):
        from .candidate_radius_io import encode_session
        if self._pending:
            raise ValueError('Apply or discard preview before saving')
        return encode_session(self._base, self._operations)
