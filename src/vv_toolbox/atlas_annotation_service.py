"""Local draft boundary editing; research use only, not for clinical decision."""
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
import threading

from .atlas_annotations import new_annotation_document, validate_annotations


class AnnotationConflict(ValueError):
    pass


def require_renderable_frame(document):
    frame = document['coordinate_frame']
    if not (frame['id'] == 'bodyparts3d_native_LPS' and frame['units'] == 'mm'
            and frame['frame_confirmed'] is True and frame['units_confirmed'] is True):
        raise ValueError('3D candidate display requires confirmed bodyparts3d_native_LPS coordinates in mm; reload or review the source coordinate contract.')


class AnnotationStore:
    """Source-bound drafts with optimistic revisions; no anatomical approval API."""
    def __init__(self, path, source_sha256):
        self.path = Path(path)
        self.source_sha256 = source_sha256
        self.lock = threading.RLock()

    def read(self):
        with self.lock:
            if not self.path.exists():
                return dict(revision='new', document=new_annotation_document(
                    'bodyparts3d-4.0', self.source_sha256,
                    coordinate_frame_id='bodyparts3d_native_LPS', units='mm',
                    frame_confirmed=True, units_confirmed=True), candidate_positions={})
            data = self.path.read_bytes()
            value = json.loads(data)
            if not isinstance(value, dict) or set(value) != {'document', 'candidate_positions'}:
                raise ValueError('Invalid annotation draft envelope')
            validate_annotations(value['document'])
            if value['document']['source'] != {'id': 'bodyparts3d-4.0', 'sha256': self.source_sha256}:
                raise ValueError('Annotation source fingerprint mismatch')
            self._candidates(value['candidate_positions'], value['document'])
            value['revision'] = hashlib.sha256(data).hexdigest()
            return value

    @staticmethod
    def _candidates(candidates, document):
        ids = {b['boundary_id'] for b in document['boundaries']}
        if not isinstance(candidates, dict) or not set(candidates) <= ids:
            raise ValueError('Unknown draft boundary')
        for xyz in candidates.values():
            if not isinstance(xyz, list) or len(xyz) != 3 or any(
                type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 1000000 for v in xyz
            ):
                raise ValueError('Draft position requires three finite source coordinates')

    def update(self, raw):
        if not isinstance(raw, dict) or set(raw) != {'revision', 'boundary_id', 'reason', 'review_note', 'source_refs', 'candidate_position'}:
            raise ValueError('Expected boundary draft fields')
        for key in ('reason', 'review_note'):
            if not isinstance(raw[key], str) or len(raw[key]) > 4000:
                raise ValueError('Invalid note length')
        if not raw['reason'].strip():
            raise ValueError('Unresolved reason is required')
        if not isinstance(raw['source_refs'], list) or len(raw['source_refs']) > 20 or any(
            not isinstance(ref, str) or not ref.strip() or len(ref) > 1000 for ref in raw['source_refs']
        ):
            raise ValueError('Invalid references')
        with self.lock:
            value = self.read()
            if raw['revision'] != value['revision']:
                raise AnnotationConflict('Annotations changed; reload before saving')
            boundary = next((b for b in value['document']['boundaries'] if b['boundary_id'] == raw['boundary_id']), None)
            if boundary is None:
                raise ValueError('Unknown boundary')
            if boundary['evidence_status'] != 'unresolved':
                raise ValueError('Only unresolved drafts can be edited here')
            for key in ('reason', 'review_note', 'source_refs'):
                boundary[key] = copy.deepcopy(raw[key])
            if raw['candidate_position'] is None:
                value['candidate_positions'].pop(raw['boundary_id'], None)
            else:
                value['candidate_positions'][raw['boundary_id']] = raw['candidate_position']
            validate_annotations(value['document'])
            self._candidates(value['candidate_positions'], value['document'])
            value.pop('revision')
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = None
            try:
                with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=self.path.parent, delete=False) as stream:
                    temporary = Path(stream.name)
                    json.dump(value, stream, ensure_ascii=False, allow_nan=False, indent=2)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, self.path)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
            return self.read()
