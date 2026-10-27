"""Compare neighboring source-face support for all 21 recorded contacts."""
import hashlib
import json
from pathlib import Path

import numpy as np

from vv_toolbox.atlas import load_atlas
from vv_toolbox.contact_footprint import compare_contact_footprints


def main():
    root=Path(__file__).resolve().parents[1]
    raw=(root/'docs/evidence/cerebral-loft-surroundings-window2mm.json').read_bytes()
    prior=json.loads(raw)
    loft_raw=(root/'docs/evidence/cerebral-smoothed-profile-lofts-window2mm.json').read_bytes()
    if hashlib.sha256(loft_raw).hexdigest()!=prior['loft_index_sha256']:
        raise ValueError('Loft index changed')
    atlas=load_atlas();parts={p['id']:p for p in atlas.meshes}
    if atlas.metadata['sha256']!=prior['atlas_archive_sha256']:
        raise ValueError('Reference atlas changed')
    rows=[]
    for record in prior['rows']:
        for pair in record['tested_pairs']:
            if pair['candidate']['status']!='CONTACT_DETECTED':continue
            if not pair['candidate']['complete'] or not pair['original_pair']['complete']:
                raise ValueError('Incomplete source/contact evidence')
            part=parts[pair['other_part_id']]
            triangles=np.asarray(part['vertices'])[np.asarray(part['faces'])]
            result=compare_contact_footprints(triangles,
                [p[1] for p in pair['original_pair']['contact_pairs']],
                [p[1] for p in pair['candidate']['contact_pairs']])
            rows.append(dict(edge_id=record['edge_id'],other_part_id=pair['other_part_id'],
                reference_triangle_sha256=hashlib.sha256(np.asarray(triangles,dtype='<f8').tobytes()).hexdigest(),
                comparison=result))
    output=dict(input_contact_report_sha256=hashlib.sha256(raw).hexdigest(),
                atlas_archive_sha256=atlas.metadata['sha256'],rows=rows,
                contact_area='NOT RUN',junction_acceptance='NOT RUN',original_modified=False)
    (root/'docs/evidence/cerebral-contact-footprints.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(dict(relations=len(rows),
        identical_face_sets=sum(r['comparison']['face_jaccard']==1 for r in rows),
        gained_faces=sum(r['comparison']['gained']['face_count'] for r in rows),
        lost_faces=sum(r['comparison']['lost']['face_count'] for r in rows),
        maximum_support_centroid_shift_mm=max(r['comparison']['support_centroid_shift_mm'] for r in rows))))


if __name__=='__main__':
    main()
