"""Local case data workspace, deliberately separate from the Atlas scene."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import threading

from .atlas_case import build_atlas_case
from .case_io import case_digest, load_case, save_case


class CaseWorkspaceConflict(ValueError):
    pass


class CaseWorkspace:
    def __init__(self, path):
        self.path = Path(path)
        self.case = None
        self.revision = None
        self.version = 0
        self.lock = threading.RLock()

    def status(self):
        with self.lock:
            case = self.case
            return {'version': self.version, 'loaded': case is not None,
                    'saved_revision': self.revision, 'file_exists': self.path.exists(),
                    'rendered': False, 'includes_atlas_edits': bool(case and case.get('inspection',{}).get('atlas_scene_capture',{}).get('includes_edits')),
                    'includes_estimates': bool(case and case.get('inspection',{}).get('atlas_scene_capture',{}).get('includes_estimates')),
                    'summary': None if case is None else {
                        'case_id': case['case_id'], 'model_kind': case['model_kind'],
                        'nodes': len(case['nodes']), 'edges': len(case['edges']),
                        'surface_parts': len(case.get('surface_parts',[])),
                        'unresolved_edges': sum(e['evidence_status'] == 'unresolved' for e in case['edges']),
                        'digest': case_digest(case)}}

    def update(self, request, *, preview=None, metadata=None, surface_parts=None,
               modifications=None, interval_edits=None):
        with self.lock:
            if not isinstance(request, dict) or set(request) != {'action', 'version'}:
                raise ValueError('Expected case action and workspace version')
            if type(request['version']) is not int or request['version'] != self.version:
                raise CaseWorkspaceConflict('Case workspace changed; refresh before retrying')
            action = request['action']
            if action in ('prepare','prepare_current'):
                if preview is None or metadata is None:
                    raise ValueError('Original Atlas centerlines are not ready')
                bindings = {}
                preview_ids = {p['id'] for p in preview['parts']}
                for part in metadata['parts']:
                    if part['layer'] != 'arterial' or part['id'] not in preview_ids:
                        continue
                    sides = set(re.findall(r'\b(left|right)\b', part['name'].lower()))
                    side = {'left': 'L', 'right': 'R'}[next(iter(sides))] if len(sides) == 1 else 'unknown'
                    bindings[part['id']] = {'artery': part['name'], 'side': side,
                        'identity_refs': [f"BodyParts3D element {part['id']}; OBJ SHA256 {part['sha256']}"]}
                if action=='prepare_current' and surface_parts is not None:
                    estimated_ids={p['id'] for p in preview['parts'] if p.get('status')=='AUTHORED_ESTIMATE'}
                    for part in surface_parts:
                        if part['layer']!='arterial' or part['id'] not in estimated_ids:
                            continue
                        record=part.get('metadata',{})
                        if record.get('original_atlas_geometry') is not False or not record.get('kind'):
                            raise ValueError('Explicit estimated geometry provenance required')
                        record_hash=hashlib.sha256(json.dumps(record,sort_keys=True,allow_nan=False).encode()).hexdigest()
                        bindings[part['id']]={'artery':part.get('name',part['id']),'side':'unknown',
                            'identity_refs':[f"Authored estimate {record['kind']}; metadata SHA256 {record_hash}"]}
                digest = hashlib.sha256(json.dumps(preview, sort_keys=True, separators=(',', ':'),
                                                   allow_nan=False).encode()).hexdigest()
                case = build_atlas_case(preview, bindings,
                    source={'id': 'bp3d', 'sha256': metadata['sha256'], 'license_ref': 'BodyParts3D CC BY 4.0'},
                    extraction_source={'id': 'bp3d-preview', 'sha256': digest,
                                       'license_ref': 'BodyParts3D derived medial preview; canonical JSON hash'},
                    frame={'id': 'bodyparts3d_native_LPS', 'units': 'mm', 'axes': 'LPS',
                           'origin': 'unchanged BodyParts3D native origin', 'confirmed': True},
                    case_id='bp3d-arterial-workspace', base_model_id='bodyparts3d-4.0',
                    allow_estimated=action=='prepare_current')
                if action == 'prepare_current':
                    if surface_parts is None:
                        raise ValueError('Current Atlas surfaces required')
                    from .atlas_case_surfaces import capture_surfaces
                    case = capture_surfaces(case,surface_parts,modifications=modifications,
                                            interval_edits=interval_edits)
                self.case = case
            elif action == 'reload':
                case, revision = load_case(self.path)
                supported = case['model_kind']=='source' or (
                    case.get('generation',{}).get('generator_version')=='atlas-surface-capture-v1'
                    and bool(case.get('surface_parts')))
                if (not supported or metadata is None or
                        case['frame']['id'] != 'bodyparts3d_native_LPS' or
                        not any(s['id'] == 'bp3d' and s['sha256'] == metadata['sha256']
                                for s in case['sources'])):
                    raise ValueError('Saved data does not match the active source Atlas')
                self.case, self.revision = case, revision
            elif action == 'save':
                if self.case is None:
                    raise ValueError('Prepare or reload a case first')
                try:
                    self.revision = save_case(self.path, self.case, expected_revision=self.revision)
                except ValueError as error:
                    if 'conflict' in str(error) or 'missing' in str(error) or 'lock' in str(error):
                        raise CaseWorkspaceConflict(str(error)) from error
                    raise
            else:
                raise ValueError('Unknown case action')
            self.version += 1
            return self.status()

    def download(self):
        with self.lock:
            if self.case is None:
                raise ValueError('Prepare or reload a case first')
            return {'schema': 'vv-toolbox.case-snapshot/1', 'revision': case_digest(self.case),
                    'case': deepcopy(self.case)}
