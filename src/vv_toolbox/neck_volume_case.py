"""Create an explicitly derived case with capped authored neck volumes."""
from copy import deepcopy

import numpy as np

from .case_contract import validate_case
from .case_io import case_digest
from .case_source_surfaces import attach_surfaces
from .estimated_tube_volume import cap_estimated_neck


def derive_neck_volumes(case, *, max_planarity_mm):
    validate_case(case)
    records=case.get('inspection',{}).get('atlas_scene_capture',{}).get('estimated_metadata',{})
    targets={pid:record for pid,record in records.items()
             if record.get('kind')=='estimated-neck-connector'}
    if not targets:
        raise ValueError('Explicit estimated neck provenance required')
    parts=deepcopy(case.get('surface_parts',[]))
    if not set(targets)<={p['part_id'] for p in parts}:
        raise ValueError('Estimated neck surface missing')
    derivations={}
    for part in parts:
        pid=part['part_id']
        if pid not in targets:
            continue
        if part['provenance']!='estimated':
            raise ValueError('Neck volume cannot replace source geometry')
        capped=cap_estimated_neck(dict(id=pid,layer='arterial',metadata=targets[pid],
            vertices=np.asarray(part['vertices_mm']),faces=np.asarray(part['faces'])),
            max_planarity_mm=max_planarity_mm)
        part['vertices_mm']=capped['vertices'].tolist()
        part['faces']=capped['faces'].tolist()
        derivations[pid]=capped['metadata']['volume_derivation']
    result=deepcopy(case)
    parent=case_digest(case)
    result['case_id']=case['case_id']+'-neck-volumes'
    result['model_kind']='synthetic'
    result['generation']=dict(seed=0,generator_version='estimated-neck-volume-v1',
        config=dict(parent_case_revision=parent,parent_generation=deepcopy(case.get('generation')),
                    max_planarity_mm=max_planarity_mm))
    result.setdefault('inspection',{})['neck_volume_derivation']=dict(
        parent_case_revision=parent,parts=derivations,
        scope='Independent estimated closed volumes; existing source geometry and graph unchanged',
        source_lumen_union='NOT RUN',surrounding_contact='NOT RUN')
    return attach_surfaces(result,parts)
