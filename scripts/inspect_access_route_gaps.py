"""Audit declared access-route legs on the current synthetic graph without snapping."""
from collections import deque
import argparse
import hashlib
from itertools import product
import json
from pathlib import Path

from vv_toolbox.case_io import load_case
from vv_toolbox.route_roles import resolve_source_roles

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',type=Path,default=ROOT/'exports/synthetic-arch-carotid-case/case.snapshot.json')
    parser.add_argument('--output',type=Path,default=ROOT/'docs/evidence/access-route-gaps.json')
    args=parser.parse_args()
    path=args.snapshot
    if args.output.resolve()==path.resolve():
        raise ValueError('Audit output must not overwrite snapshot')
    raw=path.read_bytes(); case,revision=load_case(path)
    inventory_path=ROOT/'docs/evidence/access-route-endpoints.json'
    inventory_raw=inventory_path.read_bytes(); inventory=json.loads(inventory_raw)
    sources={s['id']:s['sha256'] for s in case['sources']}
    if sources.get('bp3d')!=inventory['source_sha256'] or sources.get('bp3d-preview')!=inventory['preview_sha256']:
        raise ValueError('Source identity changed')
    edges={e['id']:e for e in case['edges']}
    source_roles={role:list(slot['edge_ids']) for role,slot in inventory['slots'].items()}
    roles=resolve_source_roles(case,source_roles,allow_declared_omissions=True)
    adjacency={n:[] for n in case['nodes']}
    for e in edges.values():
        adjacency[e['start']].append((e['end'],e['id']))
        adjacency[e['end']].append((e['start'],e['id']))

    def leg(first,second):
        # Allow only the two role edge sets and explicit synthetic bridges.
        # A route through an unrelated artery does not prove the intended leg.
        allowed=set(roles[first]+roles[second]+case['synthetic_route_inspection']['bridge_ids'])
        starts={edges[e][end] for e in roles[first] for end in ('start','end')}
        targets={edges[e][end] for e in roles[second] for end in ('start','end')}
        queue=deque((n,[]) for n in sorted(starts)); seen=set(starts)
        while queue:
            n,route=queue.popleft()
            if n in targets:
                return dict(from_role=first,to_role=second,status='GRAPH_LINK_PRESENT',
                    connecting_edges=route,anatomical_acceptance='UNKNOWN')
            for other,ident in adjacency[n]:
                if ident in allowed and other not in seen:
                    seen.add(other); queue.append((other,route+[ident]))
        return dict(from_role=first,to_role=second,status='MISSING_GRAPH_LINK',
            from_edges=roles[first],to_edges=roles[second],connecting_edges=[],
            next_action='Inspect source surfaces and author a separate evidenced synthetic junction; do not nearest-neighbour snap.')

    legs={}; routes=[]
    for femoral,carotid,target in product(('L','R'),('L','R'),('ACA_source','MCA_sphenoid_source')):
        chain=[f'{femoral}.femoral',f'{femoral}.external_iliac',f'{femoral}.common_iliac',
            'abdominal_aorta','descending_thoracic_aorta','aortic_arch']
        if carotid=='R': chain.append('brachiocephalic')
        chain += [f'{carotid}.common_carotid',f'{carotid}.internal_carotid',f'{carotid}.{target}']
        keys=[]
        for a,b in zip(chain,chain[1:]):
            key=a+' -> '+b
            if key not in legs: legs[key]=leg(a,b)
            keys.append(key)
        gaps=[key for key in keys if legs[key]['status']=='MISSING_GRAPH_LINK']
        routes.append(dict(femoral_side=femoral,carotid_side=carotid,target=target,role_chain=chain,
            leg_ids=keys,missing_leg_ids=gaps,status='INCOMPLETE' if gaps else 'LEG_LINKS_PRESENT',
            complete_ordered_route='NOT PROVEN',distal_segment_coverage='NOT ASSESSED'))
    if path.read_bytes()!=raw: raise ValueError('Input snapshot changed')
    result=dict(schema='vv-toolbox.access-route-gap-audit/1',case_revision=revision,
        source_inventory_sha256=hashlib.sha256(inventory_raw).hexdigest(),source_roles=source_roles,roles=roles,legs=legs,routes=routes,
        inputs_unchanged=True,source_modified=False,anatomical_acceptance='UNKNOWN',
        declared_source_omissions=[dict(edge_id=h['omitted_edge_id'],rationale=h['specification']['rationale'],
            evidence_refs=h['specification']['evidence_refs']) for h in case.get('synthetic_trunk_simplifications',[])],
        scope='Four access combinations, each to proximal ACA and named sphenoidal MCA source elements. Not A1-A3/M1-M3 completion.',
        limitation='Pairwise leg connectivity does not prove a single ordered non-retracing route; multi-edge role internal completeness is not asserted.')
    if args.output.resolve()==inventory_path.resolve():
        raise ValueError('Audit output must not overwrite inventory')
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(routes=len(routes),unique_legs=len(legs),present=[k for k,v in legs.items() if v['status']=='GRAPH_LINK_PRESENT'],
                         missing=[k for k,v in legs.items() if v['status']=='MISSING_GRAPH_LINK'])))


if __name__=='__main__': main()
