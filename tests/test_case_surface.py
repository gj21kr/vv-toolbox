import numpy as np
import pytest
import trimesh

from vv_toolbox.case_surface import build_case_surface
from vv_toolbox.lesions import concentric_stenosis


def example():
    return {'schema':'vv-toolbox.case/1','case_id':'base','base_model_id':'fixture',
        'model_kind':'source','split':'unassigned','generation':None,
        'frame':{'id':'fixture','units':'mm','axes':'LPS','origin':'fixture'},
        'sources':[{'id':'s','sha256':'a'*64,'license_ref':'fixture'}],
        'nodes':{n:{'kind':'unresolved','evidence_status':'unresolved','position_mm':p}
                 for n,p in [('a',[0,0,0]),('b',[20,0,0])]},
        'edges':[{'id':'e','start':'a','end':'b','source_ids':['s'],
            'geometry_kind':'source','evidence_status':'unresolved',
            'anatomy':{'artery':'ACA','side':'L','segment':'A2','branch_id':'e'},
            'centerline_mm':[[0,0,0],[20,0,0]],'radii_mm':[2,2]}]}


def derived():
    return concentric_stenosis(example(),edge_id='e',lesion_id='l',case_id='derived',region='aca',
        center_mm=10,length_mm=10,severity_percent=50,measurement_method='local_baseline_diameter',
        sample_spacing_mm=.25,seed=1)


def test_stenosis_profile_to_closed_surface_and_actual_cross_section():
    vertices, faces, meta = build_case_surface(derived(), ['e'], spacing_mm=.2)
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    assert mesh.is_volume
    assert meta['provenance'] == 'estimated'
    section = mesh.section(plane_origin=[10,0,0], plane_normal=[1,0,0])
    assert len(section.discrete) == 1
    ring = section.discrete[0]
    diameter = np.ptp(ring[:,1:],axis=0)
    # Fixed engineering error tolerance for this .2 mm synthetic fixture only.
    assert np.all(np.abs(diameter - 2.0) < .3)
    from vv_toolbox.voxel_output import Grid, Surface, voxelize
    grid = Grid((5,5,5),(.5,.5,.5),(9.,-1.,-1.),'fixture')
    volume = voxelize([Surface(1,0,'estimated',vertices,faces,'fixture','synthetic profile fixture')],grid)
    assert volume.foreground[2,2,2]
    assert not volume.foreground[0,0,2]
    assert volume.provenance[2,2,2] == 2


def test_source_is_not_misrepresented_as_source_surface():
    with pytest.raises(ValueError, match='synthetic'):
        build_case_surface(example(), ['e'], spacing_mm=.2)


def test_resource_budget_and_resolution_enforced():
    case = derived()
    with pytest.raises(ValueError, match='budget'):
        build_case_surface(case, ['e'], spacing_mm=.2,max_grid_voxels=10)
    with pytest.raises(ValueError, match='spacing'):
        build_case_surface(case, ['e'], spacing_mm=1.5)


def test_cli_surface_archive_preserves_provenance(tmp_path):
    import json
    from vv_toolbox.case_cli import main
    from vv_toolbox.case_io import save_case
    source, output = tmp_path/'case.json', tmp_path/'surface.npz'
    save_case(source,derived())
    assert main(['surface',str(source),str(output),'--edges','e','--spacing-mm','.2']) == 0
    with np.load(output,allow_pickle=False) as data:
        metadata = json.loads(str(data['metadata']))
        assert metadata['provenance'] == 'estimated'
        assert metadata['edge_ids'] == ['e']
        assert trimesh.Trimesh(vertices=data['vertices_mm'],faces=data['faces'],process=False).is_volume


def test_declared_compound_junction_surface_and_remote_crossing_rejection():
    from test_junction_regions import fixture
    from vv_toolbox.case_io import case_digest
    case, regions = fixture()
    for edge in case['edges']:
        edge['radii_mm'] = [.4] * len(edge['centerline_mm'])
    regions[0]['case_sha256'] = case_digest(case)
    ids = [e['id'] for e in case['edges']]
    vertices, faces, metadata = build_case_surface(case, ids, spacing_mm=.2, junction_regions=regions)
    assert trimesh.Trimesh(vertices=vertices, faces=faces, process=False).is_volume
    assert metadata['graph_component_count'] == 1
    assert metadata['junction_clearance_screen']['regions'] == regions
    assert metadata['junction_clearance_screen']['inside_regions'] == 'NOT CHECKED'
    # A new crossing outside the allowed prefix must still block surface generation.
    case['edges'][3]['centerline_mm'] = [[0,1,0],[6,0,0],[0,11,0]]
    case['edges'][3]['radii_mm'] = [.4]*3
    regions[0]['case_sha256'] = case_digest(case)
    with pytest.raises(ValueError, match='junction-region clearance'):
        build_case_surface(case, ids, spacing_mm=.2, junction_regions=regions)


def test_cli_explicit_junctions_roundtrip_and_stale_declaration(tmp_path):
    import json
    from test_junction_regions import fixture
    from vv_toolbox.case_cli import main
    from vv_toolbox.case_io import case_digest, save_case
    case, regions = fixture()
    for edge in case['edges']:
        edge['radii_mm'] = [.4]*len(edge['centerline_mm'])
    regions[0]['case_sha256'] = case_digest(case)
    snapshot, declaration, output = [tmp_path/name for name in ('case.json','regions.json','surface.npz')]
    save_case(snapshot,case)
    declaration.write_text(json.dumps(regions))
    original = snapshot.read_bytes(),declaration.read_bytes()
    args=['surface',str(snapshot),str(output),'--edges',*[e['id'] for e in case['edges']],
          '--spacing-mm','.2','--junction-regions',str(declaration)]
    assert main(args)==0
    with np.load(output,allow_pickle=False) as saved:
        meta=json.loads(str(saved['metadata']))
        assert meta['junction_clearance_screen']['regions']==regions
    assert original==(snapshot.read_bytes(),declaration.read_bytes())
    regions[0]['case_sha256']='a'*64
    declaration.write_text(json.dumps(regions))
    rejected=tmp_path/'rejected.npz'
    args[2]=str(rejected)
    with pytest.raises(SystemExit):
        main(args)
    assert not rejected.exists()
