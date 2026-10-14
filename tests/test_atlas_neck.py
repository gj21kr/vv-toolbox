from types import SimpleNamespace
import json
import numpy as np
from vv_toolbox.model import tube_mesh
from vv_toolbox.atlas_neck import build_neck_repairs


def cylinder(id,z0,z1,radius):
    points=np.column_stack([np.zeros(20),np.zeros(20),np.linspace(z0,z1,20)])
    v,f=tube_mesh(points,radius,sides=32)
    return dict(id=id,vertices=v,faces=f,name=id,layer='arterial')


def test_estimated_connector_has_anchored_endpoints_tangents_and_positive_radii():
    meshes=[cylinder('FJ3564',0,20,3),cylinder('FJ1682',80,100,2)]
    originals=[(p['vertices'].copy(),p['faces'].copy()) for p in meshes]
    parts,report=build_neck_repairs(SimpleNamespace(meshes=meshes))
    assert len(parts)==1 and report['original_meshes_modified'] is False
    json.dumps(report,allow_nan=False)
    p=parts[0];m=p['metadata'];points=np.array(m['centerline'])
    np.testing.assert_allclose(points[[0,-1]],m['endpoint_centers'])
    for tangent,axis in zip([points[1]-points[0],points[-1]-points[-2]],m['endpoint_axes']):
        assert np.dot(tangent/np.linalg.norm(tangent),axis)>.999
    assert np.min(m['radius_profile'])>0 and np.isfinite(p['vertices']).all()
    np.testing.assert_allclose(m['endpoint_radii'],[3,2],rtol=.01)
    assert 0<points[0,2]<20 and 80<points[-1,2]<100
    radii=np.array(m['radius_profile'])
    assert abs(radii[1]-radii[0])<.001 and abs(radii[-1]-radii[-2])<.001
    for mesh,(v,f) in zip(meshes,originals):
        np.testing.assert_array_equal(mesh['vertices'],v);np.testing.assert_array_equal(mesh['faces'],f)
    assert len([x for x in report['missing'] if x['status']=='MISSING_IDENTIFIED_UPPER_TARGET'])==2


def test_missing_sources_are_explicit_and_create_no_geometry():
    parts,report=build_neck_repairs(SimpleNamespace(meshes=[]))
    assert not parts and report['status']=='UNAVAILABLE'
    assert len(report['missing'])==6


def test_estimated_venous_network_has_shared_joins_source_anchors_and_closed_surface():
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    meshes=[cylinder('FJ3585',0,20,3),cylinder('FJ3485',0,20,3)]
    for mesh,x in zip(meshes,[-20,20]):
        mesh['vertices'][:,0]+=x;mesh['layer']='systemic_venous'
    meshes.append(dict(id='head_bounds_fixture',name='head',layer='arterial',
                       vertices=np.array([[-50,-50,50],[50,50,150]],float),faces=np.empty((0,3),int)))
    original=[m['vertices'].copy() for m in meshes]
    parts,report=build_neck_repairs(SimpleNamespace(meshes=meshes))
    part=next(p for p in parts if p['layer']=='systemic_venous')
    meta=part['metadata'];graph=meta['graph'];segments={e['id']:e for e in graph['segments']}
    assert meta['original_atlas_geometry'] is False and meta['anatomy_validated'] is False
    for side in ('left','right'):
        extension=segments[side+'_internal_jugular_extension'];points=np.array(extension['points_mm'])
        tangent=points[1]-points[0];tangent/=np.linalg.norm(tangent)
        assert np.dot(tangent,meta['anchor_axes'][side])>.995
        assert 0<points[0,2]<20
        previous=extension
        for suffix in ('sigmoid_lower','sigmoid_upper','transverse_sinus'):
            following=segments[side+'_'+suffix]
            np.testing.assert_array_equal(previous['points_mm'][-1],following['points_mm'][0])
            assert previous['radius_profile_mm'][-1]==following['radius_profile_mm'][0]
            p=np.array(previous['points_mm']);q=np.array(following['points_mm'])
            a=p[-1]-p[-2];b=q[1]-q[0]
            assert np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b))>.995
            previous=following
    assert {'straight_sinus','superior_sagittal_anterior','superior_sagittal_posterior'}<=set(segments)
    f=part['faces'];v=part['vertices']
    pairs=np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1)
    unique,counts=np.unique(pairs,axis=0,return_counts=True)
    assert np.all(counts==2)
    adjacency=coo_matrix((np.ones(len(unique)),(unique[:,0],unique[:,1])),shape=(len(v),len(v)))
    assert connected_components(adjacency,directed=False,return_labels=False)==1
    for mesh,values in zip(meshes,original):np.testing.assert_array_equal(mesh['vertices'],values)
    assert all(x['status']=='MISSING_IDENTIFIED_UPPER_TARGET' for x in report['unresolved'] if x['kind']=='internal_jugular_to_sigmoid')
    json.dumps(report,allow_nan=False)
