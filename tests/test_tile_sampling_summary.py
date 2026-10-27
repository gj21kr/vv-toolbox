import json

import trimesh

from vv_toolbox.voxel_output import Grid, Surface, voxelize
from vv_toolbox.voxel_tiles import write_mask_tiles


def test_summary_tracks_membership_not_owner_and_reports_missed_source(tmp_path):
    mesh=trimesh.creation.box(extents=[2,2,2])
    thin=trimesh.creation.box(extents=[.1,.1,.1])
    surfaces=[Surface(i,0,'source',mesh.vertices,mesh.faces,'test',f'part:{i}') for i in (9,3)]
    surfaces.append(Surface(20,0,'source',thin.vertices+.5,thin.faces,'test','part:thin'))
    grid=Grid((5,5,5),(1.,1.,1.),(-2.,-2.,-2.),'test')
    expected=voxelize(surfaces,grid)
    result=write_mask_tiles(tmp_path/'tiles',iter(surfaces),grid,tile_shape_zyx=(2,2,2))
    summary=result['sampling_summary']
    assert summary==json.loads((tmp_path/'tiles/manifest.json').read_text())['sampling_summary']
    assert summary['status']=='ZERO_SAMPLED_INSTANCES'
    assert summary['zero_sampled_instance_ids']==[20]
    counts={r['instance_id']:r['sampled_voxels'] for r in summary['instances']}
    assert counts=={s.instance_id:int(expected.membership[k].sum()) for k,s in enumerate(surfaces)}
    assert counts[9]==counts[3]>0  # overlapping non-owner remains represented


def test_empty_bundle_reports_all_sources_and_fine_sampling_recovers(tmp_path):
    mesh=trimesh.creation.box(extents=[.1,.1,.1])
    surface=Surface(7,0,'source',mesh.vertices+.5,mesh.faces,'test','thin')
    for spacing,shape,missing in [(1.,(3,3,3),[7]),(.5,(5,5,5),[])]:
        result=write_mask_tiles(tmp_path/str(spacing),[surface],
            Grid(shape,(spacing,)*3,(0.,0.,0.),'test'))
        assert result['sampling_summary']['zero_sampled_instance_ids']==missing
        assert bool(result['tiles'])== (not missing)
        assert result['sampling_summary']['status']==('ZERO_SAMPLED_INSTANCES' if missing else 'ALL_INSTANCES_SAMPLED')
