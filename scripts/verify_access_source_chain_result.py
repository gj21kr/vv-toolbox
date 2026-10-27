"""Independently reload split-source output and compare retained graph data."""
from pathlib import Path
import hashlib
import json

from vv_toolbox.case_io import load_case


def main():
    root=Path(__file__).resolve().parents[1]
    folder=root/'exports/access-source-chain'
    source,source_revision=load_case(folder/'input.snapshot.json')
    result,revision=load_case(folder/'result.snapshot.json')
    report=json.loads((root/'docs/evidence/access-source-chain.json').read_text())
    assert report['status']=='PASS'
    assert report['input_revision']==source_revision and report['output_revision']==revision
    assert source['nodes']==result['nodes']
    assert len(source['edges'])==len(result['edges'])==66
    old={e['id']:e for e in source['edges']};new={e['id']:e for e in result['edges']}
    assert set(old)==set(new)
    affected={'FJ2074:e0','FJ2074:engineering-second'}
    for ident,edge in old.items():
        updated=new[ident]
        if ident not in affected:
            assert updated==edge
        else:
            for key in ('start','end','anatomy','radii_mm','source_part_id','source_ids'):
                assert updated[key]==edge[key]
            assert updated['centerline_mm'][0]==edge['centerline_mm'][0]
            assert updated['centerline_mm'][-1]==edge['centerline_mm'][-1]
            assert len(updated['centerline_mm'])==len(edge['centerline_mm'])
    assert new['FJ2074:e0']['centerline_mm'][-1]==new['FJ2074:engineering-second']['centerline_mm'][0]
    for before,after in zip(source['surface_parts'],result['surface_parts']):
        for key in ('part_id','faces','face_lineage','edge_ids','frame_id'):
            assert before[key]==after[key]
    audit=result['inspection']['registered_shape_edit']
    checks=audit['checked_paths']
    assert len(checks)==66 and {row['edge_id'] for row in checks}==set(new)
    assert all(row['containment']['status']=='PASS' for row in checks)
    assert audit['accepted_for_generation'] is False and audit['neighboring_vessels']=='NOT RUN'
    evidence=dict(status='PASS',scope='Saved-case structure, provenance and reported complete path checks; not independent anatomical validation',
        input_revision=source_revision,output_revision=revision,checked_paths=66,graph_nodes_preserved=True,
        surface_topology_lineage_preserved=True,unselected_edges_preserved=True,
        output_sha256=hashlib.sha256((folder/'result.snapshot.json').read_bytes()).hexdigest(),
        accepted_for_generation=False,neighboring_vessels='NOT RUN')
    (root/'docs/evidence/access-source-chain-reload.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps(evidence))


if __name__=='__main__':main()
