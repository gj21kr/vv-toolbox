"""Explain unresolved neighbor prerequisites, binding the entire context hash."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.atlas import load_atlas
from vv_toolbox.atlas_neck import build_neck_repairs
from vv_toolbox.disjoint_containment import _SurfaceValidationCache


def main():
    root=Path('docs/evidence');path=root/'femoral-anterior-context.json'
    context=json.loads(path.read_text());atlas=load_atlas();neck,_=build_neck_repairs(atlas)
    parts={p['id']:p for p in [*atlas.meshes,*neck]
           if p['id'] not in context['excluded_union_sources']
           and p['layer'] in ('arterial','systemic_venous','hepatic_portal')}
    digest=hashlib.sha256()
    for name,part in sorted(parts.items()):
        encoded=name.encode('utf-8');digest.update(len(encoded).to_bytes(8,'little'));digest.update(encoded)
        for array in (np.asarray(part['vertices'],dtype='<f8'),np.asarray(part['faces'],dtype='<i8')):
            digest.update(str(array.shape).encode('ascii'));digest.update(array.tobytes())
    if digest.hexdigest()!=context['context_sha256'] or len(parts)!=context['neighbor_count']:
        raise ValueError('Context geometry changed; prior unknown inventory is stale')
    report=dict(status='RUNNING',context_sha256=context['context_sha256'],
        parent_report_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),rows=[],
        source_modified=False,anatomical_validation='NOT RUN')
    output=root/'context-unknown-surface-diagnostics.json';cache=_SurfaceValidationCache()
    for name in context['unknown']:
        part=parts[name]
        _,reason,validation=cache.validate(trimesh.Trimesh(part['vertices'],part['faces'],process=False))
        report['rows'].append(dict(part_id=name,label=part.get('name',name),reason=reason,
            validation=validation,status='UNKNOWN' if reason else 'INPUT_VALID',
            pair_clearance='NOT RUN'))
        output.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(dict(part_id=name,reason=reason,
            self_contact=validation['self_contact'] if isinstance(validation['self_contact'],str)
            else validation['self_contact']['status'])),flush=True)
    report.update(status='UNKNOWN',inspection_status='COMPLETE')
    output.write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    main()
