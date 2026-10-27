"""Separate neck, strip interior and strip-to-retained-mesh angle measurements."""
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh

ROOT=Path(__file__).resolve().parents[1]


def main():
    rows=[]
    for name in ('mca-explicit-neck','mca-neck-fairing'):
        evidence=json.loads((ROOT/f'docs/evidence/{name}.json').read_text())
        path=ROOT/f'exports/{name}/surface.npz'
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=evidence['artifact_sha256']:
            raise ValueError('candidate hash mismatch')
        with np.load(path,allow_pickle=False) as data:
            v,f=data['vertices_mm'],data['faces']
            meta=json.loads(str(data['metadata'].item()))
        mesh=trimesh.Trimesh(vertices=v,faces=f,process=False)
        ids=np.array(meta['design_vertex_ids'])
        design={tuple(sorted((int(a),int(b)))) for a,b in zip(ids,np.roll(ids,-1))}
        seam=np.array([tuple(sorted(e.tolist())) in design for e in mesh.face_adjacency_edges])
        patch=np.array(meta['face_origin_labels'])==4
        pairs=patch[mesh.face_adjacency]
        groups=dict(design_seam=seam,strip_outer_join=np.sum(pairs,axis=1)==1,
                    strip_interior=(np.sum(pairs,axis=1)==2)&~seam)
        angles=np.degrees(mesh.face_adjacency_angles)
        report=dict(candidate=name,artifact_sha256=evidence['artifact_sha256'],angles={})
        ring_lengths=np.linalg.norm(v[np.roll(ids,-1)]-v[ids],axis=1)
        report['design_ring_edge_length_mm']=dict(minimum=float(ring_lengths.min()),
            median=float(np.median(ring_lengths)),maximum=float(ring_lengths.max()))
        for label,mask in groups.items():
            chosen=np.flatnonzero(mask)
            maximum=chosen[np.argmax(angles[chosen])]
            report['angles'][label]=dict(edge_count=len(chosen),p95_deg=float(np.percentile(angles[chosen],95)),
                max_deg=float(angles[maximum]),worst_edge_vertex_ids=mesh.face_adjacency_edges[maximum].tolist(),
                worst_adjacent_face_ids=mesh.face_adjacency[maximum].tolist())
        triangles=v[f[patch]]
        squared=np.sum((np.roll(triangles,-1,axis=1)-triangles)**2,axis=(1,2))
        quality=4*np.sqrt(3)*mesh.area_faces[patch]/squared
        report['strip_triangle_quality']=dict(minimum=float(quality.min()),p05=float(np.percentile(quality,5)),
            definition='4 sqrt(3) area / sum squared edge lengths; 1 equilateral, tends to 0 degenerate')
        report['input_unchanged']=raw==path.read_bytes()
        rows.append(report)
    result=dict(scope='engineering mesh quality; not anatomical or clinical acceptance',candidates=rows)
    (ROOT/'docs/evidence/neck-transition-quality.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':
    main()
