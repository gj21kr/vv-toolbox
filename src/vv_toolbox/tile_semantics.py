"""Cross-check mask channels against preserved per-instance memberships."""
import numpy as np


def validate_tile_semantics(arrays,metadata):
    membership=arrays['membership'];instances=metadata['instances']
    if membership.dtype!=np.bool_ or membership.shape[0]!=len(instances):
        raise ValueError('Boolean membership rows must match instances')
    ids=[r['instance_id'] for r in instances]
    if len(ids)!=len(set(ids)) or any(type(i) is not int or not 0<i<=np.iinfo(np.uint32).max for i in ids):
        raise ValueError('Unique positive uint32 instance IDs required')
    shape=membership.shape[1:];foreground=np.any(membership,axis=0)
    expected_count=membership.sum(axis=0,dtype=np.uint32)
    owner=np.zeros(shape,np.uint32);anatomy=np.zeros(shape,np.uint32);provenance=np.zeros(shape,np.uint8)
    if instances:
        expanded=(len(ids),)+(1,)*len(shape)
        sentinel=np.iinfo(np.uint32).max
        owner=np.min(np.where(membership,np.asarray(ids,dtype=np.uint32).reshape(expanded),sentinel),axis=0)
        owner[~foreground]=0
        labels=[r['anatomical_label'] for r in instances]
        if any(type(i) is not int or not 0<=i<=sentinel for i in labels):raise ValueError('Invalid anatomical labels')
        labels=np.asarray(labels,np.uint32).reshape(expanded)
        minimum=np.min(np.where(membership,labels,sentinel),axis=0)
        maximum=np.max(np.where(membership,labels,0),axis=0)
        anatomy=np.where(foreground&(minimum==maximum),minimum,0).astype(np.uint32)
        for kind,code in (('source',1),('estimated',2)):
            selected=[i for i,row in enumerate(instances) if row['provenance']==kind]
            if selected:provenance[np.any(membership[selected],axis=0)]|=code
        if any(r['provenance'] not in ('source','estimated') for r in instances):raise ValueError('Unknown provenance')
    expected=dict(foreground=foreground,overlap_count=expected_count,instance=owner,anatomical=anatomy,provenance=provenance)
    for key,value in expected.items():
        if arrays[key].shape!=shape or not np.array_equal(arrays[key],value):
            raise ValueError('Tile channel conflicts with membership: '+key)
    return dict(status='PASS',foreground_voxels=int(foreground.sum()),
                overlapping_voxels=int((expected_count>1).sum()),
                instance_voxels={str(i):int(membership[k].sum()) for k,i in enumerate(ids)})
