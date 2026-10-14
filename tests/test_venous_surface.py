"""Junction geometry regressions independent of display pixels."""
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components


def test_systemic_mesh_keeps_unmodeled_chamber_as_two_closed_components():
    from vv_toolbox.veins import generate_veins
    from vv_toolbox.surface import network_mesh
    from scipy.sparse import coo_matrix
    graph=generate_veins().systemic
    vertices,faces=network_mesh(graph)
    pairs=np.sort(np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]),axis=1)
    unique,counts=np.unique(pairs,axis=0,return_counts=True)
    assert np.all(counts==2)
    adjacency=coo_matrix((np.ones(len(unique)),(unique[:,0],unique[:,1])),shape=(len(vertices),len(vertices)))
    assert connected_components(adjacency,directed=False,return_labels=False)==2
from scipy.spatial import cKDTree

from vv_toolbox.model import Segment,VesselGraph
from vv_toolbox.surface import network_mesh,_venous_junctions


def branched_graph(samples=64):
    nodes={"a":np.array([0.,0.,-30.]),"j":np.zeros(3),"b":np.array([0.,0.,30.]),"side":np.array([25.,0.,0.])}
    edges=[Segment(name,start,end,np.linspace(nodes[start],nodes[end],samples),radius)
           for name,start,end,radius in [("ven_main_in","a","j",2),("ven_main_out","j","b",4),("ven_side","j","side",1)]]
    return VesselGraph(nodes,edges,{"radius_scale":1,"circulation":"systemic"})


def assert_closed_connected(vertices,faces):
    assert np.isfinite(vertices).all()
    assert len(np.unique(faces))==len(vertices)
    edges=np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]])
    _,counts=np.unique(np.sort(edges,axis=1),axis=0,return_counts=True)
    assert np.all(counts==2)
    adjacency=coo_matrix((np.ones(len(edges)),(edges[:,0],edges[:,1])),shape=(len(vertices),len(vertices))).tocsr()
    assert connected_components(adjacency,directed=False,return_labels=False)==1


def test_venous_continuation_is_geometric_not_largest_radius():
    graph=branched_graph()
    huge=Segment("ven_side","j","side",graph.segments[2].points,20)
    graph.segments[2]=huge
    continuation,_=_venous_junctions(graph)
    assert continuation["j"]=={"ven_main_in":3,"ven_main_out":3}
    graph.segments.reverse()
    assert _venous_junctions(graph)[0]==continuation


def test_symmetric_y_does_not_arbitrarily_choose_one_arm():
    nodes={"j":np.zeros(3),"left":np.array([-20.,0.,-20.]),"right":np.array([20.,0.,-20.]),"up":np.array([0.,0.,30.])}
    edges=[Segment(name,"j",name,np.linspace(nodes["j"],nodes[name],64),radius) for name,radius in [("left",6),("right",6),("up",10)]]
    graph=VesselGraph(nodes,edges,{"radius_scale":1,"circulation":"systemic"})
    continuation,_=_venous_junctions(graph)
    assert len(continuation["j"])==3
    assert len(set(continuation["j"].values()))==1


def test_venous_branch_is_fillet_blended_closed_and_not_radius_step():
    graph=branched_graph()
    vertices,faces=network_mesh(graph)
    assert_closed_connected(vertices,faces)
    # The opposite side of the branch meets at3mm, not a4mm parent end-cap lip.
    section=vertices[(np.abs(vertices[:,2])<.35)&(vertices[:,0]<-.5)]
    assert len(section)>4
    assert np.max(np.abs(np.linalg.norm(section[:,:2],axis=1)-3))<.45
    # The small branch remains a1mm tube away from its localized root fillet.
    section=vertices[(np.abs(vertices[:,0]-18)<.35)]
    assert len(section)>4
    assert np.max(np.abs(np.linalg.norm(section[:,1:],axis=1)-1))<.25


def test_fillets_do_not_inflate_when_centerline_sampling_increases():
    graphs=[branched_graph(count) for count in (16,128)]
    for graph in graphs:
        # Hold exact straight swept geometry fixed: varying-radius interpolation
        # has its own discretization error and must not confound this union test.
        graph.segments=[Segment(edge.name,edge.start,edge.end,edge.points,2) for edge in graph.segments]
    coarse,cf=network_mesh(graphs[0])
    dense,df=network_mesh(graphs[1])
    distances,_=cKDTree(dense).query(coarse)
    reverse,_=cKDTree(coarse).query(dense)
    assert max(distances.max(),reverse.max())<.005
    assert abs(volume(coarse,cf)/volume(dense,df)-1)<1e-5


def volume(vertices,faces):
    triangles=vertices[faces].astype(float)
    return abs(np.einsum('ij,ij->i',triangles[:,0],np.cross(triangles[:,1],triangles[:,2])).sum()/6)


def test_fillet_changes_equal_radius_root_separately_from_taper(monkeypatch):
    graph=branched_graph()
    graph.segments=[Segment(edge.name,edge.start,edge.end,edge.points,2) for edge in graph.segments]
    smooth,sf=network_mesh(graph)
    # Equal radii eliminate taper differences. Metadata only enables local fillets.
    graph.parameters.pop('circulation')
    monkeypatch.setattr('vv_toolbox.surface._arterial_junctions',lambda graph:{})
    hard,hf=network_mesh(graph)
    assert volume(smooth,sf)>volume(hard,hf)+.5
