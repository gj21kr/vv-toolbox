"""Independent generated-lesion lumen labels, constrained by vessel membership."""
import math

import numpy as np

from .case_contract import validate_case
from .case_io import case_digest


def label_lesion_lumen(volume, case, edge_instances, *, max_bytes=256*1024**2, required_lesion_ids=None):
    """Label lumen by nearest station on its explicitly mapped source edge.

    The caller's edge->surface-instance mapping is an explicit input, never
    inferred by proximity. One instance cannot represent multiple source edges.
    Labels denote affected lumen, not plaque, removed tissue, or clinical GT.
    """
    validate_case(case)
    from .lesions import require_profile_lesions
    require_profile_lesions(case)
    if case['model_kind'] != 'synthetic' or volume.grid.frame_id != case['frame']['id']:
        raise ValueError('synthetic case and matching coordinate frame required')
    lesions = case.get('lesions', [])
    if len({l['lesion_id'] for l in lesions}) != len(lesions):
        raise ValueError('unique lesion records required')
    required = {l['lesion_id'] for l in lesions} if required_lesion_ids is None else set(required_lesion_ids)
    if (lesions and not required) or not required <= {l['lesion_id'] for l in lesions}:
        raise ValueError('known nonempty required lesion IDs required')
    count = math.prod(volume.grid.shape_zyx)
    if type(max_bytes) is not int or max_bytes < count*4 + 2*1024**2:
        raise ValueError('lesion label memory budget exceeded')
    instance_index = {entry['instance_id']:i for i,entry in enumerate(volume.instances)}
    if not isinstance(edge_instances,dict):
        raise ValueError('explicit edge instance map required')
    assigned = set()
    for ids in edge_instances.values():
        if not isinstance(ids,list) or not ids or any(type(i) is not int or i not in instance_index for i in ids):
            raise ValueError('known instance IDs required')
        if len(set(ids)) != len(ids) or assigned & set(ids):
            raise ValueError('union instances cannot label multiple edges')
        assigned.update(ids)
    edges = {e['id']:e for e in case['edges']}
    if any(key not in edges for key in edge_instances):
        raise ValueError('unknown mapped edge')
    output = np.zeros(count,dtype=np.uint32)
    registry = []
    for label, lesion in enumerate(sorted(lesions,key=lambda x:x['lesion_id']),1):
        ident = lesion['edge_id']
        if ident not in edge_instances:
            raise ValueError('every lesion needs an explicit edge instance mapping')
        start, stop = lesion['support_interval_mm']
        if not all(type(s) in (int,float) and math.isfinite(s) for s in (start,stop)) or not 0 <= start < stop:
            raise ValueError('invalid lesion interval')
        edge = edges[ident]
        if edge['centerline_mm'] is None:
            raise ValueError('lesion edge geometry required')
        points = np.asarray(edge['centerline_mm'],dtype=float)
        lengths = np.linalg.norm(np.diff(points,axis=0),axis=1)
        stations = np.r_[0,np.cumsum(lengths)]
        if stop > stations[-1]:
            raise ValueError('lesion extends beyond edge')
        members = [volume.membership[instance_index[i]].reshape(-1) for i in edge_instances[ident]]
        voxels = 0
        for offset in range(0,count,2048):
            indices = np.arange(offset,min(offset+2048,count))
            admitted = np.zeros(len(indices),dtype=bool)
            for member in members:
                admitted |= member[indices]
            admitted &= volume.foreground.reshape(-1)[indices]
            indices = indices[admitted]
            if not len(indices):
                continue
            zyx = np.array(np.unravel_index(indices,volume.grid.shape_zyx)).T
            world = zyx[:,::-1]*np.asarray(volume.grid.spacing_xyz_mm)+np.asarray(volume.grid.origin_xyz_mm)
            best = np.full(len(indices),np.inf)
            nearest_station = np.zeros(len(indices))
            for i,(a,b) in enumerate(zip(points,points[1:])):
                v = b-a
                t = np.clip(((world-a)@v)/(v@v),0,1)
                distance2 = np.sum((world-(a+t[:,None]*v))**2,axis=1)
                take = distance2 < best
                best[take] = distance2[take]
                nearest_station[take] = stations[i]+t[take]*lengths[i]
            selected = indices[(nearest_station > start) & (nearest_station < stop)]
            if np.any(output[selected]):
                raise ValueError('lesion voxel overlap; output not published')
            output[selected] = label
            voxels += len(selected)
        registry.append({'label':label,'lesion_id':lesion['lesion_id'],'edge_id':ident,
                         'sampled_voxels':voxels,'sampling_status':'PASS' if voxels else 'UNKNOWN'})
    return output.reshape(volume.grid.shape_zyx), {
        'schema':'vv-toolbox.lesion-labels/1','case_revision':case_digest(case),
        'definition':'generated affected lumen; nearest edge station strictly inside lesion support',
        'mapping_provenance':'explicit caller-supplied edge-to-surface instance mapping',
        'status':'PASS' if all(r['sampled_voxels'] for r in registry if r['lesion_id'] in required) else 'UNKNOWN',
        'sampling_status':('NOT APPLICABLE' if not lesions else
            'PASS' if all(r['sampled_voxels'] for r in registry if r['lesion_id'] in required) else 'UNKNOWN'),
        'lesion_presence':'present' if lesions else 'none_declared',
        'required_lesion_ids':sorted(required),
        'registry':registry,'edge_instances':edge_instances,
        'grid':volume.metadata(),'clinical_validity':'NOT RUN'}
