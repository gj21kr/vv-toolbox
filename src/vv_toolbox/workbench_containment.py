"""Read-only centerline comparison with the registered native Atlas surface."""
from .case_io import case_digest


def inspect_edge(case, edge_id):
    """Bind a declared source part and coordinate frame before querying geometry."""
    from .atlas import load_atlas, PINNED
    from .centerline_containment import inspect_centerline_containment
    import trimesh

    revision = case_digest(case)
    edge = next((e for e in case['edges'] if e['id'] == edge_id), None)
    if edge is None:
        raise ValueError('Select a known edge')
    report = dict(status='UNKNOWN', case_revision=revision, edge_id=edge_id,
                  scope='Selected centerline against its declared original Atlas surface',
                  anatomical_validation='NOT RUN', radius_surface_accuracy='NOT RUN',
                  surface_self_intersection='NOT RUN')
    frame = case['frame']
    expected_frame = dict(id='bodyparts3d_native_LPS', units='mm', axes='LPS',
                          origin='unchanged BodyParts3D native origin')
    if any(frame.get(k) != v for k, v in expected_frame.items()):
        return dict(report, reason='Native Atlas coordinate frame is not established')
    archive_hash = PINNED['isa_BP3D_4.0_obj_99.zip']
    bound_sources = [s for s in case['sources']
                     if s['id'] in edge.get('source_ids', []) and s['sha256'] == archive_hash]
    if not bound_sources:
        return dict(report, reason='Selected edge has no matching registered Atlas source hash')
    part_id = edge.get('source_part_id')
    if not isinstance(part_id, str) or not part_id:
        return dict(report, reason='No explicit original surface part is recorded')
    points = edge.get('centerline_mm')
    if points is None:
        return dict(report, reason='No centerline is available')
    if len(points) > 10000:
        return dict(report, reason='Interactive limit of 10000 centerline points exceeded')
    try:
        atlas = load_atlas()
    except (OSError, ValueError):
        return dict(report, reason='Registered Atlas files are unavailable or fail source verification')
    if atlas.metadata['sha256'] != archive_hash:
        return dict(report, reason='Loaded Atlas archive hash does not match the registered source')
    part = next((p for p in atlas.meshes if p['id'] == part_id), None)
    if part is None:
        return dict(report, reason='Declared original surface part is unavailable')
    mesh = trimesh.Trimesh(part['vertices'], part['faces'], process=False)
    result = inspect_centerline_containment(mesh, points, max_cells=20000)
    return dict(report, status=result['status'], source_part_id=part_id,
                atlas_archive_sha256=archive_hash, containment=result,
                reason=result.get('reason', 'Whole-interval numerical containment completed'))
