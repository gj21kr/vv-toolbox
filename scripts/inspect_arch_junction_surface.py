"""Inspect a declared synthetic branch region without changing the baseline case."""
import hashlib
import json
from pathlib import Path

import numpy as np

from vv_toolbox.case_io import load_case
from vv_toolbox.case_surface import build_case_surface
from vv_toolbox.junction_regions import inspect_junction_regions

ROOT = Path(__file__).resolve().parents[1]


def main():
    path = ROOT / 'exports/synthetic-arch-carotid-case/case.snapshot.json'
    before = path.read_bytes()
    case, revision = load_case(path)
    old = json.loads((ROOT/'docs/evidence/synthetic-arch-carotid-case.json').read_text())
    if revision != old['derived_revision']:
        raise ValueError('Synthetic candidate changed since the initial inspection')
    selected = old['selected_surface']['selected_edge_ids']
    edges = {e['id']: e for e in case['edges']}
    spacing = .6
    branch_id = 'estimated_arch_to_LCCA'
    branch = edges[branch_id]
    bridge_length = float(np.cumsum(np.linalg.norm(np.diff(branch['centerline_mm'],axis=0),axis=1))[-1])
    collar = 3*edges['synthetic_arch_before_LCCA']['radii_mm'][-1] + 2*spacing

    def portion(edge_id, endpoint, length):
        return dict(edge_id=edge_id,endpoint=endpoint,length_mm=float(length))

    def region(name, node, portions, rationale):
        return dict(id=name,case_sha256=revision,root_node_id=node,portions=portions,
                    rationale=rationale,evidence_refs=['docs/ARCH_CAROTID_JUNCTION.md',
                    'docs/evidence/synthetic-arch-carotid-case.json'])

    regions = [region('arch-LCCA',branch['start'],[
        portion('synthetic_arch_before_LCCA','end',collar),
        portion('synthetic_arch_after_LCCA','start',collar),
        portion(branch_id,'start',bridge_length),
        portion('FJ3483:e0','start',collar)],
        'Explicit synthetic compound junction. Same 3*parent radius+2*spacing numerical collar policy as ordinary junctions, extended across the declared short side-branch bridge. Not an anatomical ostium extent.')]
    neck = edges['estimated_L_carotid_gap']
    for end, other, endpoint in [('start','FJ3483:e0','end'),('end','FJ1682M:e0','end')]:
        i,j = (0 if end=='start' else -1),(0 if endpoint=='start' else -1)
        width = 3*max(neck['radii_mm'][i],edges[other]['radii_mm'][j])+2*spacing
        regions.append(region('neck-'+end,neck[end],[portion(neck['id'],end,width),
            portion(other,endpoint,width)],'Existing degree-2 numerical junction collar; no new source connectivity.'))
    output = ROOT/'exports/arch-junction-surface'
    output.mkdir(parents=True,exist_ok=True)
    (output/'regions.json').write_text(json.dumps(regions,indent=2)+'\n')
    clearance = inspect_junction_regions(case,selected,regions,margin_mm=2*spacing)
    report = dict(schema='vv-toolbox.arch-junction-surface/1',case_revision=revision,
        input_snapshot_sha256=hashlib.sha256(before).hexdigest(),regions=regions,
        selected_edge_ids=selected,spacing_mm=spacing,region_clearance=clearance,
        anatomical_acceptance='UNKNOWN',whole_case_collision='NOT RUN',default_adoption='NOT ACCEPTED')
    try:
        vertices,faces,metadata=build_case_surface(case,selected,spacing_mm=spacing,junction_regions=regions)
        np.savez_compressed(output/'surface.npz',vertices_mm=vertices,faces=faces,
                            metadata=np.array(json.dumps(metadata)))
        report['surface']=dict(status='PASS',vertices=len(vertices),triangles=len(faces),metadata=metadata,
            sha256=hashlib.sha256((output/'surface.npz').read_bytes()).hexdigest())
        import trimesh
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        mesh=trimesh.Trimesh(vertices=vertices,faces=faces,process=False)
        z0=case['nodes'][branch['start']]['position_mm'][2]
        fig,axes=plt.subplots(2,3,figsize=(12,8))
        sections=[]
        for ax,offset in zip(axes.flat,[-8.,0.,5.,10.,16.,24.]):
            section=mesh.section(plane_origin=[0,0,z0+offset],plane_normal=[0,0,1])
            contours=[] if section is None else section.discrete
            sections.append(dict(z_mm=z0+offset,contours_mm=[c.tolist() for c in contours]))
            for c in contours: ax.plot(c[:,0],c[:,1],color='firebrick')
            ax.set_title(f'Z = {z0+offset:.1f} mm'); ax.set_aspect('equal'); ax.grid(alpha=.2)
            ax.set_xlabel('LPS X mm'); ax.set_ylabel('LPS Y mm')
        fig.suptitle('Synthetic arch / LCCA union: actual mesh sections, not source anatomy')
        fig.tight_layout(); figure=output/'junction-sections.png'; fig.savefig(figure,dpi=150); plt.close(fig)
        report['sections']=sections
        report['figure']=dict(path=figure.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(figure.read_bytes()).hexdigest())
    except ValueError as error:
        report['surface']=dict(status='FAIL',reason=str(error),surface_published=False)
    if path.read_bytes()!=before:
        raise ValueError('Input snapshot changed')
    report['input_unchanged']=True
    (ROOT/'docs/evidence/arch-junction-surface.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('sections','regions','region_clearance','surface')}))
    print(json.dumps({'region_clearance':clearance,'surface':{k:v for k,v in report['surface'].items() if k!='metadata'}}))


if __name__=='__main__':
    main()
