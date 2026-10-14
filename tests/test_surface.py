import numpy as np
import pytest
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree
from vv_toolbox import generate
from vv_toolbox.surface import network_mesh
from vv_toolbox.model import Segment, VesselGraph


def test_local_radius_resolution_and_trunk_taper_at_branched_junction():
    nodes = {"a":np.array([0.,0.,0.]),"j":np.array([0.,0.,30.]),"b":np.array([0.,0.,60.]),"side":np.array([20.,0.,30.])}
    graph = VesselGraph(nodes,[
        Segment("aortic_arch","a","j",np.linspace(nodes["a"],nodes["j"],64),2),
        Segment("aortic_arch_proximal","j","b",np.linspace(nodes["j"],nodes["b"],64),4),
        Segment("branch","j","side",np.linspace(nodes["j"],nodes["side"],64),1),
    ],{"radius_scale":2})
    vertices,_ = network_mesh(graph)
    # Inspect the side opposite the branch: local trunk radius should meet at3mm.
    cross_section = vertices[(np.abs(vertices[:,2]-30)<0.4) & (vertices[:,0]<-0.5)]
    assert len(cross_section) > 4
    assert np.max(np.abs(np.linalg.norm(cross_section[:,:2],axis=1)-3)) < 0.4


@pytest.mark.parametrize("scale,tortuosity", [(0.5,1), (1,0.3), (2,0)])
def test_fused_surface_is_one_component_and_preserves_all_terminals(scale,tortuosity):
    graph = generate(scale,tortuosity)
    vertices,faces = network_mesh(graph)
    assert np.isfinite(vertices).all()
    assert len(np.unique(faces)) == len(vertices)
    edges = np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]])
    adjacency = coo_matrix((np.ones(len(edges)), (edges[:,0],edges[:,1])),shape=(len(vertices),len(vertices))).tocsr()
    assert connected_components(adjacency,directed=False,return_labels=False) == 1
    _, incidence = np.unique(np.sort(edges,axis=1),axis=0,return_counts=True)
    assert np.all(incidence == 2), "Closed display surface has a seam or nonmanifold edge"
    tree = cKDTree(vertices)
    bifurcation_distance,_ = tree.query(graph.nodes["aortic_bifurcation"])
    # Shared Y radius is sqrt(5²+5²)*scale, not the old abrupt 10mm parent cap.
    assert 6.5*scale < bifurcation_distance < 7.5*scale
    for edge in graph.segments:
        # Thin cerebral branches retain their own radius; large junction unions can
        # enclose a short branch inside an adjacent larger vessel legitimately.
        # Middle third excludes the intentional 30% endpoint-radius taper.
        distance,_ = tree.query(edge.points[20:-20])
        local_radius = max(e.radius_mm for e in graph.segments if {e.start,e.end} & {edge.start,edge.end})
        assert distance.max() < local_radius+0.45*max(1,scale)
        # Inside a large parent lumen, a small branch has no independent surface.
        # Evaluate its own-radius coverage outside both neighboring junction balls.
        interior = edge.points[20:-20]
        outside = np.ones(len(interior),dtype=bool)
        for node in (edge.start,edge.end):
            junction_radius = max(e.radius_mm for e in graph.segments if node in (e.start,e.end))
            outside &= np.linalg.norm(interior-graph.nodes[node],axis=1) > junction_radius+edge.radius_mm
        if outside.any():
            assert distance[outside].max() < edge.radius_mm+0.45*max(1,scale)
    for side in ("left","right"):
        for artery in ("mca","aca","pca"):
            distance,_ = tree.query(graph.nodes[f"{side}_{artery}"])
            assert 0.1 < distance < 2.1*scale
