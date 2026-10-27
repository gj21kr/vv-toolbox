"""Engineering split of an actual access path; no anatomical boundary claim."""
from copy import deepcopy
import json
from pathlib import Path
import time

from vv_toolbox.case_io import load_case,save_case,case_digest
from vv_toolbox.case_source_surfaces import attach_surfaces
from vv_toolbox.registered_shape_edit import deform_registered_source


def main():
    root=Path(__file__).resolve().parents[1]
    target=root/'docs/evidence/access-source-chain.json'
    folder=root/'exports/access-source-chain'
    if target.exists() or folder.exists():
        raise ValueError('Preserve existing inspection outputs')
    folder.mkdir(parents=True)
    started=time.perf_counter()
    original,parent=load_case(root/'exports/candidate-case-download/case.snapshot.json')
    case=deepcopy(original);parts=case.pop('surface_parts')
    edge=next(e for e in case['edges'] if e['id']=='FJ2074:e0')
    original_edge=deepcopy(edge);cut=len(edge['centerline_mm'])//2
    node_id='engineering-split:FJ2074';other=deepcopy(edge)
    case['nodes'][node_id]=dict(kind='segment_boundary',evidence_status='synthetic_estimate',
        position_mm=edge['centerline_mm'][cut],note='Engineering fixture only; not an anatomical segment boundary')
    other.update(id='FJ2074:engineering-second',start=node_id,
        centerline_mm=edge['centerline_mm'][cut:],radii_mm=edge['radii_mm'][cut:])
    edge.update(end=node_id,centerline_mm=edge['centerline_mm'][:cut+1],radii_mm=edge['radii_mm'][:cut+1])
    case['edges'].append(other)
    for part in parts:
        if edge['id'] in part['edge_ids']:part['edge_ids'].append(other['id'])
    case.update(case_id='access-source-chain-engineering-fixture',model_kind='synthetic',
        generation=dict(seed=0,generator_version='engineering-split/1',config=dict(parent_case_revision=parent,cut_station=cut)))
    case=attach_surfaces(case,parts)
    assert edge['centerline_mm']+other['centerline_mm'][1:]==original_edge['centerline_mm']
    assert case['surface_parts'][0]['geometry_sha256']==original['surface_parts'][0]['geometry_sha256']
    input_revision=save_case(folder/'input.snapshot.json',case)
    report=dict(status='RUNNING',scope='Actual access geometry with engineering split, not anatomical segmentation',
        parent_revision=parent,input_revision=input_revision,cut_station=cut,source_geometry_unchanged=True,
        source_path_reassembly_exact=True,accepted_for_generation=False)
    def write():
        temp=target.with_suffix('.tmp');temp.write_text(json.dumps(report,indent=2)+'\n');temp.replace(target)
    write()
    try:
        result=deform_registered_source(case,edge_id=edge['id'],bend_mm=.25,bend_direction=[1,0,0],
            twist_deg=0.,collar_mm=1.,transition_mm=10.,max_displacement_mm=1.)
        assert result['nodes']==case['nodes'] and case_digest(case)==input_revision
        affected={edge['id'],other['id']};old={e['id']:e for e in case['edges']}
        for changed in result['edges']:
            prior=old[changed['id']]
            if changed['id'] not in affected:assert changed==prior
            else:
                assert changed['centerline_mm'][0]==prior['centerline_mm'][0]
                assert changed['centerline_mm'][-1]==prior['centerline_mm'][-1]
                assert changed['radii_mm']==prior['radii_mm'] and changed['anatomy']==prior['anatomy']
        revision=save_case(folder/'result.snapshot.json',result)
        loaded,loaded_revision=load_case(folder/'result.snapshot.json')
        assert loaded==result and loaded_revision==revision
        audit=result['inspection']['registered_shape_edit']
        report.update(status='PASS',output_revision=revision,checked_paths=len(audit['checked_paths']),
            graph_nodes_preserved=True,unselected_edges_preserved=True,labels_radii_preserved=True,
            audit=audit['audit'],neighboring_vessels='NOT RUN')
    except Exception as exc:
        report.update(status='FAIL',error=str(exc));raise
    finally:
        report['elapsed_seconds']=time.perf_counter()-started;write()
        print(json.dumps({k:v for k,v in report.items() if k!='audit'}),flush=True)


if __name__=='__main__':main()
