"""Compare complete before/after context results without overwriting either run."""
import hashlib
import json
from pathlib import Path


def main():
    paths=[Path('docs/evidence')/name for name in
           ('carotid-radius-context.json','carotid-radius-context-broadphase.json')]
    reports=[json.loads(path.read_text()) for path in paths]
    tables=[]
    for report in reports:
        table={row['part_id']:row for row in report['rows']}
        if len(table)!=len(report['rows']):
            raise ValueError('Duplicate candidate ID')
        tables.append(table)
    if set(tables[0])!=set(tables[1]):
        raise ValueError('Candidate cohort differs')
    fields=('input_sha256','output_sha256','neighbor_count','status','new_or_extended_contacts',
            'unknown','remaining_contacts','rows')
    rows=[]
    for pid in sorted(tables[0]):
        old,new=tables[0][pid],tables[1][pid]
        differences=[field for field in fields if old[field]!=new[field]]
        rows.append(dict(part_id=pid,comparisons=old['neighbor_count'],
                         status='FAIL' if differences else 'PASS',different_fields=differences))
    result=dict(status='PASS' if all(row['status']=='PASS' for row in rows) else 'FAIL',
        rows=rows,comparisons=sum(row['comparisons'] for row in rows),
        files=[dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest()) for path in paths],
        scope='Exact candidate identities and complete per-neighbor contact/containment results',
        scope_exclusions=['Additional context hash metadata absent from original run'],
        optimized_elapsed_seconds=reports[1]['elapsed_seconds'],
        original_elapsed_seconds='NOT RECORDED',speedup='NOT CLAIMED')
    Path('docs/evidence/radius-context-broadphase-comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':
    main()
