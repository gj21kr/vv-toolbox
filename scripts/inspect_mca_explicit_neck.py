"""Replace the sampled mixed band by two strips sharing the exact design rim."""
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh
from vv_toolbox.patch_boundary import patch_boundary_loops
from vv_toolbox.ring_stitch import stitch_rings

ROOT=Path(__file__).resolve().parents[1]


def ordered(ids,vertices,center,basis):
    ids=np.array(ids,dtype=int)
    xy=((vertices[ids]-center)@basis)[:,:2]
    area=np.sum(xy[:,0]*np.roll(xy[:,1],-1)-xy[:,1]*np.roll(xy[:,0],-1))
    if area<0:
        ids=ids[::-1];xy=xy[::-1]
    # Explicit engineering seam: closest angular sample to positive width.
    start=int(np.argmin(np.abs(np.arctan2(xy[:,1],xy[:,0]))))
    ids=np.roll(ids,-start)
    points=vertices[ids]
    lengths=np.linalg.norm(np.roll(points,-1,axis=0)-points,axis=1)
    if np.any(lengths<=1e-12):
        raise ValueError('degenerate boundary')
    angles=np.r_[0.,np.cumsum(lengths[:-1])]/lengths.sum()*2*np.pi
    return ids,angles


def main():
    evidence=json.loads((ROOT/'docs/evidence/mca-surface-origin.json').read_text())
    spec=json.loads((ROOT/'docs/evidence/regularized-mca-sac.json').read_text())['specification']
    path=ROOT/'exports/mca-surface-origin/surface.npz';raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=evidence['artifact_sha256']:
        raise ValueError('source surface mismatch')
    with np.load(path,allow_pickle=False) as data:
        original=data['vertices_mm'];faces=data['faces']
        metadata=json.loads(str(data['metadata'].item()))
    if metadata['case_revision']!=spec['case_revision']:
        raise ValueError('source case mismatch')
    labels=np.array(metadata['surface_origin']['face_labels'])
    if np.any(labels==3):
        raise ValueError('unsupported source faces')
    rim=np.array(metadata['attachment']['curve_mm'])
    vertices=np.vstack([original,rim])
    center=np.array(spec['neck']['center_mm'])
    basis=np.column_stack([spec['neck'][k] for k in ('width_axis','depth_axis','normal')])
    ring_ids,angles=ordered(np.arange(len(original),len(vertices)),vertices,center,basis)
    sides=[]
    for label in (0,1):
        loops=patch_boundary_loops(faces,np.flatnonzero(labels==label))
        if len(loops)!=1:
            raise ValueError('single source-region boundary required')
        sides.append(ordered(loops[0],vertices,center,basis))
    strips=[stitch_rings(*sides[0],ring_ids,angles),
            stitch_rings(ring_ids,angles,*sides[1])]
    retained=faces[labels!=2]
    combined=np.vstack([retained,*strips])
    mesh=trimesh.Trimesh(vertices=vertices,faces=combined,process=False)
    trimesh.repair.fix_normals(mesh,multibody=False)
    if not mesh.is_volume or len(mesh.split(only_watertight=False))!=1 or np.any(mesh.area_faces<=1e-12):
        raise ValueError('stitched surface fails closed-volume or face-area check')
    design_edges={tuple(sorted((int(a),int(b)))) for a,b in zip(ring_ids,np.roll(ring_ids,-1))}
    seam_angles=[float(angle*180/np.pi) for edge,angle in zip(mesh.face_adjacency_edges,mesh.face_adjacency_angles)
                 if tuple(sorted(edge.tolist())) in design_edges]
    if len(seam_angles)!=len(ring_ids):
        raise ValueError('design rim does not have two incident faces per edge')
    origin=np.r_[labels[labels!=2],np.full(sum(len(s) for s in strips),4)]
    out=ROOT/'exports/mca-explicit-neck';out.mkdir(exist_ok=True)
    result=dict(case_revision=metadata['case_revision'],frame=metadata['frame'],
        schema='vv-toolbox.explicit-neck/1',status='CANDIDATE',
        parent_artifact_sha256=evidence['artifact_sha256'],
        design_vertex_ids=ring_ids.tolist(),face_origin_labels=origin.tolist(),
        origin_legend={'0':'retained parent','1':'retained sac','4':'new connecting strip'},
        parameterization='normalized arc length; seam nearest positive neck width direction',
        replaced_faces=int(np.count_nonzero(labels==2)),new_faces=sum(len(s) for s in strips),
        original_vertices_unchanged=bool(np.array_equal(mesh.vertices[:len(original)],original)),
        design_curve_exact=bool(np.array_equal(mesh.vertices[len(original):],rim)),
        design_projected_width_depth_mm=np.ptp((rim-center)@basis,axis=0)[:2].tolist(),
        seam_dihedral_p95_deg=float(np.percentile(seam_angles,95)),
        seam_dihedral_max_deg=max(seam_angles),closed_volume='PASS',
        self_intersection='NOT RUN',smooth_junction='UNKNOWN',context_collision='NOT RUN',
        clinical_validation='NOT RUN',app_applied=False)
    np.savez_compressed(out/'surface.npz',vertices_mm=mesh.vertices,faces=mesh.faces,
                        metadata=np.array(json.dumps(result)))
    report={k:v for k,v in result.items() if k not in ('face_origin_labels','design_vertex_ids')}
    report.update(artifact_sha256=hashlib.sha256((out/'surface.npz').read_bytes()).hexdigest(),
                  input_unchanged=path.read_bytes()==raw)
    (ROOT/'docs/evidence/mca-explicit-neck.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':
    main()
