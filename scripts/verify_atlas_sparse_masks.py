"""Reload every saved tile and verify channel, source and coordinate consistency."""
import json
from pathlib import Path
import numpy as np
from vv_toolbox.case_io import load_case
from vv_toolbox.voxel_tile_reader import iter_saved_tiles


def main():
    root=Path(__file__).resolve().parents[1];folder=root/'exports/atlas-source-masks-1mm'
    run=json.loads((root/'docs/evidence/atlas-sparse-mask-run.json').read_text())
    manifest=json.loads((folder/'manifest.json').read_text())
    case,revision=load_case(root/'exports/atlas-case-capture-ui/case.snapshot.json')
    context=manifest['context'];mapping=context['part_instances']
    if revision!=run['case_revision'] or revision!=context['case_revision']:raise ValueError('Case revision mismatch')
    parts={p['part_id']:p for p in case['surface_parts']}
    if set(mapping)!=set(parts) or context['excluded_parts']:raise ValueError('Incomplete source cohort')
    for ident,p in parts.items():
        if mapping[ident]['geometry_sha256']!=p['geometry_sha256'] or mapping[ident]['edge_ids']!=p['edge_ids']:
            raise ValueError('Source identity mismatch')
    reverse={r['instance_id']:ident for ident,r in mapping.items()}
    counts={key:0 for key in parts};foreground=overlap=unknown=tile_count=0
    for start,arrays,meta in iter_saved_tiles(folder,expected_manifest_sha256=run['manifest_sha256']):
        expected=np.asarray(manifest['origin_xyz_mm'])+np.asarray(start[::-1])*manifest['spacing_xyz_mm']
        affine=np.asarray(meta['voxel_xyz_to_world_mm'])
        if not np.allclose(affine[:3,3],expected,atol=1e-9,rtol=0):raise ValueError('Tile world origin mismatch')
        if not np.array_equal(affine[:3,:3],np.diag(manifest['spacing_xyz_mm'])):raise ValueError('Tile spacing mismatch')
        for k,instance in enumerate(meta['instances']):
            ident=reverse[instance['instance_id']]
            if instance['source_ref']!=f'case:{revision};part:{ident}' or instance['provenance']!='source':
                raise ValueError('Tile source binding mismatch')
            counts[ident]+=int(arrays['membership'][k].sum())
        foreground+=int(arrays['foreground'].sum());overlap+=int((arrays['overlap_count']>1).sum())
        unknown+=int((arrays['foreground']&(arrays['anatomical']==0)).sum());tile_count+=1
    if foreground!=run['foreground_voxels'] or tile_count!=run['tiles_written']:raise ValueError('Run summary differs from saved arrays')
    report=dict(schema='vv-toolbox.atlas-mask-reload/1',status='PASS',case_revision=revision,
        manifest_sha256=run['manifest_sha256'],tiles_verified=tile_count,selected_parts=len(parts),
        foreground_voxels=foreground,overlapping_voxels=overlap,unknown_anatomical_voxels=unknown,
        per_part_voxels=counts,zero_sampled_voxel_parts=sorted(k for k,v in counts.items() if not v),
        scope='Every saved tile: hashes, channels versus memberships, source identities and tile affine',
        geometric_mask_accuracy='NOT RUN',anatomical_validation='NOT RUN',
        limitation='1 mm voxel-center sampling can miss thin structures. This does not establish geometry fidelity or complete segment labels.')
    (root/'docs/evidence/atlas-mask-reload.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('per_part_voxels','zero_sampled_voxel_parts')}))
    print('zero_sampled_parts='+str(len(report['zero_sampled_voxel_parts'])))


if __name__=='__main__':main()
