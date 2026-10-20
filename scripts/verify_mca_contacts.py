"""Native mesh-volume contact audit, not patient or anatomical validation.

Run inside a dependency container with trimesh, manifold3d, rtree, scipy, numpy.
No repairs, dilation, or source edits. Positive overlap is only model contact.
"""
import json
from pathlib import Path
import numpy as np
import trimesh
import importlib.metadata
from vv_toolbox.atlas import load_atlas

out = Path('exports/connection-audit')
atlas = load_atlas()
parts = {p['id']: p for p in atlas.meshes}
graph = json.loads((out/'source-graph.json').read_text())
selected = 'FJ1718'
ids = ['FJ1659','FJ1660','FJ1664','FJ1669','FJ1692','FJ1694','FJ1712','FJ1729']
def mesh(pid):
    p=parts[pid]
    return trimesh.Trimesh(vertices=p['vertices'].copy(), faces=p['faces'].copy(), process=True)
def paths(pid):
    return np.concatenate([e['points'] for e in graph['edges'] if e['part_id']==pid])
a=mesh(selected)
# Controlled checks distinguish volume overlap from disjoint or tangent solids.
unit=trimesh.creation.box()
for shift,expected in [(0.5,0.5),(1.0,0.0),(2.0,0.0)]:
    other=unit.copy(); other.apply_translation([shift,0,0])
    result=trimesh.boolean.intersection([unit,other],engine='manifold')
    assert abs(abs(result.volume)-expected)<1e-7
rows=[]
for pid in ids:
    b=mesh(pid)
    row=dict(id=pid,name=parts[pid]['name'],a_watertight=bool(a.is_watertight),b_watertight=bool(b.is_watertight),
             a_valid_volume=bool(a.is_volume),b_valid_volume=bool(b.is_volume))
    if a.is_volume and b.is_volume:
        overlap=trimesh.boolean.intersection([a,b],engine='manifold',check_volume=True)
        volume=float(abs(overlap.volume)) if len(overlap.faces) else 0.0
        row.update(intersection_volume=volume,intersection_faces=len(overlap.faces),
                   intersection_components=len(overlap.split()) if len(overlap.faces) else 0,
                   model_contact='positive_overlap' if volume>1e-8 else 'no_positive_overlap',
                   neighbor_centerline_samples_inside_selected=int(a.contains(paths(pid)).sum()),
                   selected_centerline_samples_inside_neighbor=int(b.contains(paths(selected)).sum()))
        if volume>1e-8:
            center=overlap.center_mass
            row['overlap_centroid']=center.tolist()
            edge=next(e for e in graph['edges'] if e['part_id']==selected)
            pts=np.array(edge['points']);arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(pts,axis=0),axis=1))]
            i=int(np.argmin(np.linalg.norm(pts-center,axis=1)))
            row['centroid_selected_path_fraction']=float(arc[i]/arc[-1])
    else:
        row['model_contact']='unresolved_invalid_volume'
    rows.append(row)
    print(json.dumps(row),flush=True)
report=dict(selected=selected,method='Manifold boolean intersection of welded native triangles; no dilation or repairs',
            clinical_validation=False,units='original source units; volume in source units cubed',
            limitations='Overlap can be an intentional modeling joint or accidental interpenetration; it does not establish anatomical parenthood or a lumen.',
            controlled_checks='PASS: overlapping, tangent, and separated unit boxes',
            dependencies={name:importlib.metadata.version(name) for name in ('numpy','scipy','trimesh','manifold3d','rtree')},
            source_hashes={p['id']:p['sha256'] for p in atlas.metadata['parts'] if p['id'] in [selected,*ids]},
            selected_concepts=parts[selected]['concept_memberships'],candidates=rows)
(out/'mca-volume-contacts.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
