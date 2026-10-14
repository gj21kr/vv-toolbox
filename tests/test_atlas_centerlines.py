from types import SimpleNamespace
import numpy as np
from scipy.spatial import cKDTree
from vv_toolbox.model import tube_mesh,Segment,VesselGraph
from vv_toolbox.surface import network_mesh
from vv_toolbox.atlas_centerlines import extract_part,build_atlas_centerlines,proximity_links


def curved_part():
    t=np.linspace(0,np.pi*.8,60);points=np.column_stack([20*np.cos(t),20*np.sin(t),np.zeros(len(t))])
    v,f=tube_mesh(points,2.,sides=24)
    caps=[]
    for j in range(24):
        caps.extend([[len(v),j,(j+1)%24],[len(v)+1,len(v)-24+(j+1)%24,len(v)-24+j]])
    return dict(id='curve',layer='arterial',vertices=np.vstack([v,points[0],points[-1]]),faces=np.vstack([f,caps])),points


def test_medial_path_follows_curvature_and_preserves_input():
    p,expected=curved_part();original=p['vertices'].copy();r=extract_part(p)
    all_points=np.concatenate([e['points'] for e in r['edges']])
    assert cKDTree(expected).query(all_points)[0].max()<1.5
    length=sum(np.linalg.norm(np.diff(e['points'],axis=0),axis=1).sum() for e in r['edges'])
    assert 40<length<65
    assert r['part']['components']==1
    assert all(min(e['radii'])>0 for e in r['edges'])
    np.testing.assert_array_equal(original,p['vertices'])


def test_branch_skeleton_preserves_three_terminal_paths():
    nodes={'root':np.array([0.,0.,-15.]),'join':np.zeros(3),'a':np.array([-12.,0.,14.]),'b':np.array([12.,0.,14.])}
    edges=[Segment(x,u,v,np.linspace(nodes[u],nodes[v],24),2.) for x,u,v in [('trunk','root','join'),('a','join','a'),('b','join','b')]]
    vertices,faces=network_mesh(VesselGraph(nodes,edges,{}),spacing=.5)
    r=extract_part(dict(id='y',layer='arterial',vertices=vertices,faces=faces))
    assert sum(n['kind']=='terminal' for n in r['nodes'])>=3
    assert any(n['kind']=='junction' for n in r['nodes'])
    assert r['part']['components']==1


def test_open_source_reported_unresolved_without_substitute():
    p,_=curved_part();p['faces']=p['faces'][:-48]
    result=build_atlas_centerlines(SimpleNamespace(meshes=[p]))
    assert result['summary']['unresolved']==1
    assert result['edges']==[]


def test_candidate_links_never_join_different_circulations():
    nodes=[dict(id='a',part_id='A',point=[0,0,0],kind='terminal'),dict(id='b',part_id='B',point=[.5,0,0],kind='terminal')]
    edges=[dict(id='a',part_id='A',layer='arterial',start='a',end='a',points=[[0,0,0],[0,0,2]],radii=[1,1]),
           dict(id='b',part_id='B',layer='systemic_venous',start='b',end='b',points=[[.5,0,0],[.5,0,2]],radii=[1,1])]
    assert proximity_links(nodes,edges)==[]
    edges[1]['layer']='arterial'
    links=proximity_links(nodes,edges)
    assert links and all(e['status']=='candidate' for e in links)
