"""Measure derived path bending and unchanged/interpolated source radius envelope."""
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh
from vv_toolbox.atlas import load_atlas
from vv_toolbox.case_io import load_case
from vv_toolbox.path_metrics import polyline_metrics
from vv_toolbox.centerline_containment import inspect_radius_envelope_containment


def main():
    root=Path(__file__).resolve().parents[1]
    previous=json.loads((root/'docs/evidence/frontobasal-path-adaptive.json').read_text())
    path=root/previous['artifact']
    if hashlib.sha256(path.read_bytes()).hexdigest()!=previous['sha256']:raise ValueError('Path hash mismatch')
    with np.load(path,allow_pickle=False) as data:
        original=data['original_points_mm'];candidate=data['candidate_points_mm']
    case,revision=load_case(root/'exports/atlas-case-inspection/all-arterial.snapshot.json')
    atlas=load_atlas()
    if revision!=previous['source_case_revision'] or atlas.metadata['sha256']!=previous['atlas_archive_sha256']:
        raise ValueError('Source identity mismatch')
    edge=next(e for e in case['edges'] if e['id']==previous['edge_id'])
    np.testing.assert_array_equal(original,np.asarray(edge['centerline_mm']))
    params=np.asarray(previous['projection']['source_parameters'])
    radii=np.interp(params,np.arange(len(original)),edge['radii_mm'])
    p=next(p for p in atlas.meshes if p['id']=='FJ1690')
    surface=trimesh.Trimesh(p['vertices'],p['faces'],process=False)
    envelope=inspect_radius_envelope_containment(surface,candidate,radii)
    report=dict(schema='vv-toolbox.frontobasal-path-quality/1',artifact_sha256=previous['sha256'],
        source_case_revision=revision,original_metrics=polyline_metrics(original),candidate_metrics=polyline_metrics(candidate),
        radius_policy='Retain source radius at original stations; linear interpolation at inserted source parameters',
        radii_mm=radii.tolist(),radius_envelope=envelope,accepted_for_generation=False,
        smoothness_acceptance='NOT DEFINED',tube_wall_containment='NOT RUN')
    (root/'docs/evidence/frontobasal-path-quality.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(original_turn=report['original_metrics']['maximum_turn_deg'],candidate_turn=report['candidate_metrics']['maximum_turn_deg'],
        envelope=envelope['status'],radius_exceedances=len(envelope.get('radius_exceedance_witnesses',[])))),flush=True)


if __name__=='__main__':main()
