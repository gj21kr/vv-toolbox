"""Retain sampled voxel-source ownership on union triangles."""
import numpy as np
from scipy.ndimage import map_coordinates


def label_union_faces(vertices_zyx,faces,parent_mask,sac_mask,spacing_mm):
    vertices=np.asarray(vertices_zyx,dtype=float)
    faces=np.asarray(faces)
    parent=np.asarray(parent_mask);sac=np.asarray(sac_mask)
    if (parent.ndim!=3 or parent.shape!=sac.shape or parent.dtype!=bool or sac.dtype!=bool
            or vertices.ndim!=2 or vertices.shape[1]!=3 or not np.isfinite(vertices).all()
            or faces.ndim!=2 or faces.shape[1]!=3 or not len(faces)
            or not np.issubdtype(faces.dtype,np.integer) or faces.min()<0 or faces.max()>=len(vertices)
            or not np.isfinite(spacing_mm) or spacing_mm<=0):
        raise ValueError('valid local surface and boolean source masks required')
    triangles=vertices[faces]/spacing_mm
    probes=np.concatenate([triangles,triangles.mean(axis=1)[:,None,:]],axis=1)
    if np.any(probes<0) or np.any(probes>np.array(parent.shape)-1):
        raise ValueError('surface outside source grid')
    coords=probes.reshape(-1,3).T
    p=map_coordinates(parent.astype(float),coords,order=1,mode='nearest').reshape(-1,4)
    s=map_coordinates(sac.astype(float),coords,order=1,mode='nearest').reshape(-1,4)
    difference=p-s
    labels=np.full(len(faces),2,dtype=np.uint8)
    labels[np.all(difference>1e-6,axis=1)]=0
    labels[np.all(difference<-1e-6,axis=1)]=1
    labels[np.all((p+s)<=1e-6,axis=1)]=3
    return dict(schema='vv-toolbox.surface-origin/1',face_labels=labels.tolist(),
        label_names={'0':'parent_dominant','1':'sac_dominant','2':'mixed_or_tied','3':'unsupported'},
        counts={name:int(np.count_nonzero(labels==i)) for i,name in enumerate(
            ['parent_dominant','sac_dominant','mixed_or_tied','unsupported'])},
        method='trilinear occupancy comparison at three vertices and centroid',
        scope='source participation before surface smoothing; face index lineage only',
        anatomical_neck_boundary='UNKNOWN',
        limitation='Sampled ownership is not exact triangle partition or anatomical labeling; mixed faces retain uncertainty.')
