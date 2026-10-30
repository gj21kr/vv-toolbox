"""Regenerate four source centerlines without substituting historical exports."""
import hashlib
import json
import platform
from importlib.metadata import version
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from vv_toolbox.atlas import load_atlas
from vv_toolbox.atlas_centerlines import build_atlas_centerlines


def main():
    root=Path(__file__).resolve().parents[1]
    atlas=load_atlas()
    selected={'FJ1690','FJ1654','FJ1655','FJ1695'}
    parts=[p for p in atlas.meshes if p['id'] in selected]
    if len(parts)!=4: raise ValueError('Expected four source parts')
    subset=SimpleNamespace(metadata=atlas.metadata,meshes=parts)
    graph=build_atlas_centerlines(subset,cache_dir=root/'reference-data/bodyparts3d/centerline-cache',
        progress=lambda n,total:print(f'Extracted {n}/{total}',flush=True))
    output=root/'exports/frontobasal-restored'
    output.mkdir(parents=True,exist_ok=True)
    path=output/'centerlines.json'
    path.write_text(json.dumps(graph,indent=2,allow_nan=False)+'\n')
    contacts=json.loads((root/'docs/evidence/frontobasal-source-contacts.json').read_text())
    if contacts['atlas_archive_sha256']!=atlas.metadata['sha256']:
        raise ValueError('Contact source mismatch')
    measurements=[]
    for row in contacts['rows']:
        for i,patch in enumerate(row['frontobasal_support']['components']):
            center=np.array(patch['support_centroid_mm'])
            matches=[]
            for edge in graph['edges']:
                if edge['part_id']!='FJ1690': continue
                points=np.asarray(edge['points'])
                delta=np.diff(points,axis=0)
                squared=np.einsum('ij,ij->i',delta,delta)
                t=np.clip(np.einsum('ij,ij->i',center-points[:-1],delta)/np.maximum(squared,1e-24),0,1)
                closest=points[:-1]+t[:,None]*delta
                dist=np.linalg.norm(closest-center,axis=1)
                j=int(np.argmin(dist))
                lengths=np.linalg.norm(delta,axis=1)
                matches.append(dict(edge_id=edge['id'],distance_mm=float(dist[j]),
                    arclength_from_start_mm=float(lengths[:j].sum()+t[j]*lengths[j]),
                    edge_length_mm=float(lengths.sum()),nearest_point_mm=closest[j].tolist()))
            measurements.append(dict(neighbor_id=row['neighbor_id'],support_component=i,
                nearest_centerline=min(matches,key=lambda m:m['distance_mm']) if matches else None))
    report=dict(schema='vv-toolbox.frontobasal-centerline-restoration/1',
        atlas_archive_sha256=atlas.metadata['sha256'],
        source_identities=atlas.metadata['source_identities'],
        contact_report_sha256=hashlib.sha256((root/'docs/evidence/frontobasal-source-contacts.json').read_bytes()).hexdigest(),
        artifact=str(path.relative_to(root)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        runtime=dict(python=platform.python_version(),packages={n:version(n) for n in ['numpy','scipy','scikit-image','trimesh']}),
        summary=graph['summary'],parts=graph['parts'],support_projections=measurements,
        historical_export_equivalence='NOT VERIFIED',historical_exports_overwritten=False,
        accepted_for_generation=False,anatomical_junction_validation='NOT RUN',
        scope='Regenerated voxel centerlines of four original parts. Support-centroid proximity is not an ostium or a patent lumen.')
    (root/'docs/evidence/frontobasal-centerline-restoration.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(summary=graph['summary'],projections=measurements)),flush=True)


if __name__=='__main__': main()
