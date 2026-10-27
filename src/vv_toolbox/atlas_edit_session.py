"""Local parameter snapshots for reproducible atlas edits, never source meshes."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import tempfile

import numpy as np

from .atlas_modification import DEFAULT_PARAMETERS, deform_part, validate_parameters
from .atlas_edit_checks import require_self_contact_clearance
from .case_io import _encode, _unique_object

SCHEMA = 'vv-toolbox.atlas-edit-session/1'
GENERATOR = 'anchor-preserving-centerline-field-v1'


class AtlasEditConflict(ValueError):
    pass


def canonical_modifications(value):
    if not isinstance(value, dict):
        raise ValueError('Expected atlas edit mapping')
    result = {}
    for pid, parameters in value.items():
        if not isinstance(pid, str) or not pid or not isinstance(parameters, dict) or set(parameters) != set(DEFAULT_PARAMETERS):
            raise ValueError('Expected complete vessel parameters')
        parameters = validate_parameters(parameters)
        if parameters != DEFAULT_PARAMETERS:
            result[pid] = parameters
    return result


def source_identity(metadata, original, parts):
    sha = metadata.get('sha256')
    if not isinstance(sha, str) or len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha.lower()):
        raise ValueError('Atlas source fingerprint unavailable')
    digest = hashlib.sha256()
    for part in sorted(parts, key=lambda p: p['id']):
        digest.update(_encode([part['id'], part['layer']]))
        for field, dtype in [('vertices', '<f8'), ('faces', '<i8')]:
            array = np.asarray(part[field], dtype=dtype)
            digest.update(_encode(list(array.shape)))
            digest.update(array.tobytes())
    return dict(archive_sha256=sha.lower(),
                original_centerlines_sha256=hashlib.sha256(_encode(original)).hexdigest(),
                original_geometry_sha256=digest.hexdigest())


def regenerate(parts, original, modifications):
    """Build all derived data before touching the live workspace."""
    from .atlas_centerlines import proximity_links
    from .atlas_topology import build_reference_topology
    modifications = canonical_modifications(modifications)
    by_id = {p['id']: p for p in parts if p['layer'] != 'context'}
    if not set(modifications) <= set(by_id):
        raise ValueError('Unknown atlas vessel in saved edits')
    graph = deepcopy(original)
    replacements, surfaces = {}, {}
    for pid, parameters in modifications.items():
        source_edges = [e for e in original['edges'] if e['part_id'] == pid]
        surfaces[pid], edges = deform_part(by_id[pid], source_edges, parameters)
        require_self_contact_clearance(surfaces[pid])
        replacements.update({e['id']: e for e in edges})
    graph['edges'] = [replacements.get(e['id'], e) for e in graph['edges']]
    graph['nodes'] = [n for n in graph['nodes'] if n['kind'] != 'candidate_attachment']
    nodes = {n['id']: n for n in graph['nodes']}
    for edge in graph['edges']:
        for end, idx in [('start', 0), ('end', -1)]:
            nodes[edge[end]]['point'] = edge['points'][idx]
            nodes[edge[end]]['radius'] = edge['radii'][idx]
    graph['links'] = proximity_links(graph['nodes'], graph['edges'])
    graph['reference_topology'] = build_reference_topology(parts, graph['links'])
    graph['summary'].update(nodes=len(graph['nodes']), candidate_links=len(graph['links']))
    graph['modifications'] = deepcopy(modifications)
    return graph, surfaces, modifications


class AtlasEditSession:
    def __init__(self, path):
        self.path = Path(path)
        self.revision = None

    def read(self, identity):
        envelope = json.loads(self.path.read_text(encoding='utf-8'), object_pairs_hook=_unique_object)
        if not isinstance(envelope, dict) or set(envelope) != {'schema', 'revision', 'payload'} or envelope['schema'] != SCHEMA:
            raise ValueError('Invalid atlas edit snapshot')
        payload = envelope['payload']
        if not isinstance(payload, dict) or set(payload) != {'source', 'generator', 'modifications'}:
            raise ValueError('Invalid atlas edit payload')
        revision = hashlib.sha256(_encode(payload)).hexdigest()
        if revision != envelope['revision']:
            raise ValueError('Atlas edit content hash mismatch')
        if payload['source'] != identity:
            raise ValueError('Atlas edit source fingerprint mismatch')
        if payload['generator'] != GENERATOR:
            raise ValueError('Atlas edit generator version mismatch')
        modifications = canonical_modifications(payload['modifications'])
        if modifications != payload['modifications']:
            raise ValueError('Atlas edits must omit unchanged vessels')
        return modifications, revision

    def save(self, identity, modifications):
        payload = dict(source=identity, generator=GENERATOR,
                       modifications=canonical_modifications(modifications))
        revision = hashlib.sha256(_encode(payload)).hexdigest()
        data = _encode(dict(schema=SCHEMA, revision=revision, payload=payload)) + b'\n'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock = self.path.with_name(self.path.name + '.lock')
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as error:
            raise AtlasEditConflict('Atlas edit writer lock exists') from error
        temporary = None
        try:
            os.close(fd)
            if self.path.exists():
                _, current = self.read(identity)
                if current != self.revision:
                    raise AtlasEditConflict('Saved edits changed; reload before saving')
            elif self.revision is not None:
                raise AtlasEditConflict('Previously saved edits are missing')
            fd, temporary = tempfile.mkstemp(dir=self.path.parent, prefix=self.path.name, suffix='.tmp')
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            temporary = None
            self.revision = revision
        finally:
            if temporary is not None:
                Path(temporary).unlink(missing_ok=True)
            lock.unlink(missing_ok=True)
        return revision
