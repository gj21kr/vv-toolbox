"""Measure every centered-path station including actual endpoint planes."""
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh
from vv_toolbox.atlas import load_atlas
from vv_toolbox.source_sections import extract_source_sections
from vv_toolbox.section_radius_profile import section_radius_profile
from vv_toolbox.centerline_containment import inspect_radius_envelope_containment


def main():
    root=Path(__file__).resolve().parents[1]
    parent=json.loads((root/'docs/evidence/frontobasal-centering.json').read_text())
    path=root/parent['artifact']
    if hashlib.sha256(path.read_bytes()).hexdigest()!=parent['sha256']:raise ValueError('Path mismatch')
    with np.load(path,allow_pickle=False) as data:points=data['candidate_points_mm']
    atlas=load_atlas()
    if atlas.metadata['sha256']!=parent['atlas_archive_sha256']:raise ValueError('Atlas mismatch')
    part=next(p for p in atlas.meshes if p['id']=='FJ1690');mesh=trimesh.Trimesh(part['vertices'],part['faces'],process=False)
    sections=extract_source_sections(mesh,points,include_endpoints=True)
    profile=section_radius_profile(sections,len(points));envelopes={}
    if profile['measured_count']==len(points):
        for definition in ['area_equivalent_radius_mm','center_boundary_distance_mm']:
            radii=np.asarray([r[definition] for r in profile['stations']])
            envelopes[definition]=inspect_radius_envelope_containment(mesh,points,radii)
    report=dict(schema='vv-toolbox.frontobasal-endpoint-sections/1',parent_artifact_sha256=parent['sha256'],
        atlas_archive_sha256=atlas.metadata['sha256'],sections=sections,radius_profile=profile,
        radius_envelopes=envelopes,accepted_for_generation=False,app_applied=False)
    (root/'docs/evidence/frontobasal-endpoint-sections.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(sections['counts'],{k:v['status'] for k,v in envelopes.items()},flush=True)


if __name__=='__main__':main()
