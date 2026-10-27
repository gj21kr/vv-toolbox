"""Fixed-rim local fairing experiment with limits declared before execution."""
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh
from vv_toolbox.constrained_fairing import fair_surface
from vv_toolbox.patch_boundary import vertices_to_closed_curve_distance

ROOT=Path(__file__).resolve().parents[1]


def main():
    path=ROOT/'exports/mca-explicit-neck/surface.npz'
    raw=path.read_bytes()
    source=json.loads((ROOT/'docs/evidence/mca-explicit-neck.json').read_text())
    if hashlib.sha256(raw).hexdigest()!=source['artifact_sha256']:raise ValueError('source mismatch')
    with np.load(path,allow_pickle=False) as data:
        vertices,faces=data['vertices_mm'],data['faces']
        metadata=json.loads(str(data['metadata'].item()))
    ids=np.array(metadata['design_vertex_ids'])
    rim=vertices[ids]
    distances=vertices_to_closed_curve_distance(vertices,rim)
    free=np.setdiff1d(np.flatnonzero(distances<2.),ids)
    report=dict(source_sha256=source['artifact_sha256'],case_revision=source['case_revision'],
        config=dict(region_distance_mm=2.,strength=10.,max_displacement_mm=.3,max_volume_change_fraction=.02),
        app_applied=False)
    try:
        moved,metrics=fair_surface(vertices,faces,free,strength=10.,
            max_displacement_mm=.3,max_volume_change_fraction=.02)
        mesh=trimesh.Trimesh(vertices=moved,faces=faces,process=False)
        edges={tuple(sorted((int(a),int(b)))) for a,b in zip(ids,np.roll(ids,-1))}
        angles=[float(a*180/np.pi) for e,a in zip(mesh.face_adjacency_edges,mesh.face_adjacency_angles)
                if tuple(sorted(e.tolist())) in edges]
        if len(angles)!=len(ids) or not np.array_equal(moved[ids],rim):
            raise ValueError('design rim changed')
        out=ROOT/'exports/mca-neck-fairing';out.mkdir(exist_ok=True)
        np.savez_compressed(out/'surface.npz',vertices_mm=moved,faces=faces,
            metadata=np.array(json.dumps(dict(metadata,fairing=metrics))))
        report.update(status='CANDIDATE',metrics=metrics,design_rim_exact=True,
            seam_dihedral_p95_deg=float(np.percentile(angles,95)),seam_dihedral_max_deg=max(angles),
            artifact_sha256=hashlib.sha256((out/'surface.npz').read_bytes()).hexdigest(),
            smooth_junction='UNKNOWN',context_collision='NOT RUN')
    except ValueError as error:
        report.update(status='FAIL',reason=str(error))
    report['input_unchanged']=path.read_bytes()==raw
    (ROOT/'docs/evidence/mca-neck-fairing.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':
    main()
