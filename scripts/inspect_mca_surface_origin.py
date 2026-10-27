"""Rebuild the exact MCA design with retained face-origin labels."""
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh
from vv_toolbox.case_io import load_case
from vv_toolbox.surface_neck_union import build_surface_neck_union
from vv_toolbox.surface_regularization import regularize_surface

ROOT=Path(__file__).resolve().parents[1]


def main():
    case,revision=load_case(ROOT/'exports/mca-profile-regularization/case.snapshot.json')
    previous=json.loads((ROOT/'docs/evidence/regularized-mca-sac.json').read_text())
    old_path=ROOT/'exports/regularized-mca-sac/surface.npz'
    old_bytes=old_path.read_bytes()
    if previous['case_revision']!=revision or hashlib.sha256(old_bytes).hexdigest()!=previous['artifact_sha256']:
        raise ValueError('previous geometry mismatch')
    print('Rebuilding MCA with source ownership',flush=True)
    vertices,faces,metadata=build_surface_neck_union(case,previous['specification'],spacing_mm=.15,
        ray_half_span_mm=1.,ray_step_mm=.05)
    vertices,faces,smoothing=regularize_surface(vertices,faces,iterations=10,
        max_displacement_mm=.15,max_volume_change_fraction=.02)
    labels=np.array(metadata['surface_origin']['face_labels'])
    mesh=trimesh.Trimesh(vertices=vertices,faces=faces,process=False)
    regions=[]
    for label in (0,1,2,3):
        selected=np.flatnonzero(labels==label)
        if not len(selected):
            regions.append(dict(label=label,faces=0,components=0))
            continue
        patch=mesh.submesh([selected],append=True,repair=False)
        counts=np.bincount(patch.edges_unique_inverse,minlength=len(patch.edges_unique))
        boundary=patch.edges_unique[counts==1]
        adjacency={}
        for a,b in boundary:
            adjacency.setdefault(int(a),[]).append(int(b))
            adjacency.setdefault(int(b),[]).append(int(a))
        remaining=set(adjacency);components=[]
        while remaining:
            stack=[min(remaining)];seen=set()
            while stack:
                node=stack.pop()
                if node in seen:continue
                seen.add(node);stack.extend(adjacency[node])
            remaining-=seen
            components.append(dict(vertices=len(seen),closed=all(len(adjacency[n])==2 for n in seen)))
        regions.append(dict(label=label,faces=len(selected),
            components=len(patch.split(only_watertight=False)),euler_number=int(patch.euler_number),
            nonmanifold_edges=int(np.count_nonzero(counts>2)),boundary_components=components))
    with np.load(old_path,allow_pickle=False) as old:
        same_vertices=np.array_equal(vertices,old['vertices_mm'])
        same_faces=np.array_equal(faces,old['faces'])
    out=ROOT/'exports/mca-surface-origin';out.mkdir(exist_ok=True)
    np.savez_compressed(out/'surface.npz',vertices_mm=vertices,faces=faces,
        metadata=np.array(json.dumps(dict(metadata,surface_regularization=smoothing))))
    report=dict(case_revision=revision,status='CANDIDATE',origin_counts=metadata['surface_origin']['counts'],
        regions=regions,vertices_identical_to_previous=same_vertices,faces_identical_to_previous=same_faces,
        previous_artifact_sha256=previous['artifact_sha256'],
        artifact_sha256=hashlib.sha256((out/'surface.npz').read_bytes()).hexdigest(),
        previous_input_unchanged=old_path.read_bytes()==old_bytes,app_applied=False,
        neck_boundary_approval='UNKNOWN',
        scope='face-index source provenance and mesh patch topology; not anatomical segmentation')
    (ROOT/'docs/evidence/mca-surface-origin.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':
    main()
