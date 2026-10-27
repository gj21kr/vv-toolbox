"""Audit every graph junction in a saved Atlas case without inventing links."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np

from vv_toolbox.case_io import load_case


def inspect(case):
    adjacency={key:[] for key in case['nodes']}
    for edge in case['edges']:
        for key in set((edge['start'],edge['end'])):adjacency[key].append(edge)
    rows=[]
    for key,edges in sorted(adjacency.items()):
        if len(edges)<3:continue
        node=case['nodes'][key];reasons=[];branches=[]
        if node['position_mm'] is None:reasons.append('unresolved junction position')
        for edge in sorted(edges,key=lambda e:e['id']):
            item=dict(edge_id=edge['id'],anatomy=edge['anatomy'],source_ids=edge['source_ids'],
                      evidence_status=edge['evidence_status'],length_mm=None,endpoint_gap_mm=None)
            if edge['start']==edge['end']:reasons.append(edge['id']+': self loop')
            if edge['centerline_mm'] is None:reasons.append(edge['id']+': unresolved centerline')
            else:
                points=np.asarray(edge['centerline_mm']);lengths=np.linalg.norm(np.diff(points,axis=0),axis=1)
                item['length_mm']=float(lengths.sum())
                if not np.isfinite(lengths).all() or np.any(lengths<=1e-9):
                    reasons.append(edge['id']+': nonfinite or duplicate stations')
                if node['position_mm'] is not None:
                    endpoint=points[0 if edge['start']==key else -1]
                    gap=float(np.linalg.norm(endpoint-node['position_mm']))
                    item['endpoint_gap_mm']=gap
                    if gap>1e-6:reasons.append(edge['id']+': centerline does not meet junction')
            branches.append(item)
        rows.append(dict(node_id=key,node_evidence_status=node['evidence_status'],
            incident_edge_count=len(edges),structural_status='FAIL' if reasons else 'PASS',
            reasons=reasons,branches=branches,anatomical_acceptance='UNKNOWN',
            manual_design_status='NOT PROVIDED',geometry_generation='NOT RUN'))
    targets=[]
    for source in ('FJ1654','FJ1654M','FJ1692','FJ1692M'):
        selected=[e for e in case['edges'] if e['id'].startswith(source+':')]
        nodes=sorted({key for e in selected for key in (e['start'],e['end'])})
        targets.append(dict(source_part_id=source,edge_ids=[e['id'] for e in selected],
            nodes=[dict(node_id=key,incident_edge_count=len(adjacency[key])) for key in nodes],
            bifurcation_node_count=sum(len(adjacency[key])>=3 for key in nodes)))
    return dict(node_count=len(case['nodes']),edge_count=len(case['edges']),
        degree_histogram={str(k):v for k,v in sorted(Counter(map(len,adjacency.values())).items())},
        junction_count=len(rows),structural_pass_count=sum(r['structural_status']=='PASS' for r in rows),
        junctions=rows,cerebral_target_sources=targets,
        node_evidence_counts=dict(Counter(r['node_evidence_status'] for r in rows)),
        scope='All degree >= 3 nodes; structural inputs only, not anatomical bifurcation approval',
        status='INSPECTED',accepted_for_generation=False)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('snapshot',type=Path)
    parser.add_argument('report',type=Path)
    args=parser.parse_args()
    before=args.snapshot.read_bytes();case,revision=load_case(args.snapshot)
    report=inspect(case)
    if args.snapshot.read_bytes()!=before:raise RuntimeError('Input changed during inspection')
    report.update(schema='vv-toolbox.atlas-bifurcation-inputs/1',case_revision=revision,
                  input_sha256=hashlib.sha256(before).hexdigest(),input_unchanged=True)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='junctions'}))


if __name__=='__main__':main()
