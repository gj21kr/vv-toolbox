"""Source-derived sac union with shared rim indices and preserved exterior."""
import hashlib
import numpy as np
import trimesh
from .bifurcation_saccular import validate_bifurcation_saccular_spec
from .source_neck_opening import build_source_neck_opening
from .curved_sac_patch import _build_rim_patch
from .mesh_self_contact import inspect_self_contact


def build_source_sac_union(case,spec,source_vertices,source_faces,*,source_part_id,axial_rings=32,max_contact_pairs=2000000):
    validate_bifurcation_saccular_spec(case,spec)
    if not isinstance(source_part_id,str) or not source_part_id:raise ValueError('Explicit source part ID required')
    source_vertices=np.asarray(source_vertices,float);source_faces=np.asarray(source_faces)
    neck=spec['neck']
    vertices,faces,opening=build_source_neck_opening(source_vertices,source_faces,neck['curve_mm'],neck['normal'])
    rim_ids=np.asarray(opening['neck_boundary_vertex_ids'])
    pv,pf,patch=_build_rim_patch(spec,vertices[rim_ids],opening['trace'],axial_rings=axial_rings,max_contact_pairs=max_contact_pairs)
    n=len(rim_ids)
    mapping=np.r_[rim_ids,np.arange(len(vertices),len(vertices)+len(pv)-n)]
    combined=np.vstack([vertices,pv[n:]])
    combined_faces=np.vstack([faces,mapping[pf]])
    mesh=trimesh.Trimesh(vertices=combined,faces=combined_faces,process=False)
    if not mesh.is_volume or len(mesh.split(only_watertight=False))!=1:
        raise ValueError('Source and dome must form one consistently oriented closed volume')
    contact=inspect_self_contact(combined,combined_faces,max_pairs=max_contact_pairs)
    if contact['status']!='NO_CONTACT_DETECTED':raise ValueError('Source-sac union self-contact failed or incomplete: '+str(contact))
    lineage=np.r_[opening['source_face_ids'],np.full(len(pf),-1)]
    preserved=np.asarray(opening['retained_output_face_ids'],dtype=np.int64)
    if not np.array_equal(combined[combined_faces[preserved]],source_vertices[source_faces[lineage[preserved]]]):
        raise ValueError('Retained source triangle coordinates changed')
    return combined,combined_faces,dict(schema='vv-toolbox.source-sac-union/1',status='CANDIDATE',
        case_revision=spec['case_revision'],frame=case['frame'].copy(),specification=spec,
        source_part_id=source_part_id,source_geometry_sha256=hashlib.sha256(source_vertices.astype('<f8').tobytes()+source_faces.astype('<i8').tobytes()).hexdigest(),
        opening=opening,dome=patch,source_face_ids=lineage.tolist(),self_contact=contact,
        retained_output_face_ids=preserved.tolist(),
        source_triangle_containment=opening['source_triangle_containment'],
        retained_triangle_identity='PASS',single_closed_volume='PASS',volume_mm3=float(mesh.volume),
        accepted_for_generation=False,
        limitation='Declared source identity; caller must bind original asset to case. Neck uses source-face partitions. '
                   'No surrounding clearance, branch patency or tangent continuity acceptance. Original case unchanged.')
