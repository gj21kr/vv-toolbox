"""Sparse spatial tiles with the same memberships as the dense mask sampler."""
from dataclasses import replace
import itertools
import math
import hashlib
import os
from pathlib import Path
import shutil
import tempfile

import numpy as np
import trimesh

from .surface_indexing import exact_vertex_index_copy
from .voxel_output import Grid, voxelize


def iter_mask_tiles(surfaces, grid, *, tile_shape_zyx=(32, 32, 32),
                    max_bytes=256*1024**2, normalize_exact_indices=False,
                    surface_tolerance_mm=1e-8):
    """Yield (start_zyx, volume) only for occupied tiles; missing tiles are zero.

    Consume one tile at a time. Caller-retained yielded volumes are not included
    in the memory budget. Every input surface is checked before any tile yields.
    """
    if (len(tile_shape_zyx)!=3 or any(type(n) is not int or n<=0 for n in tile_shape_zyx)
            or type(max_bytes) is not int or max_bytes<=0):
        raise ValueError('Positive tile dimensions and memory budget required')
    if type(normalize_exact_indices) is not bool:
        raise ValueError('Explicit exact-index normalization policy required')
    if (isinstance(surface_tolerance_mm,bool) or not isinstance(surface_tolerance_mm,(int,float))
            or not math.isfinite(surface_tolerance_mm) or surface_tolerance_mm<0):
        raise ValueError('Invalid surface tolerance')
    surfaces=list(surfaces)
    if not surfaces:
        raise ValueError('At least one surface required')
    ids=[s.instance_id for s in surfaces]
    if any(type(i) is not int or not 0<i<=np.iinfo(np.uint32).max for i in ids) or len(set(ids))!=len(ids):
        raise ValueError('Unique positive uint32 instance IDs required')
    # Reserve input-array copies, index remapping, and preprocessing workspace.
    geometry_bound=4*sum(np.asarray(s.vertices_mm).size*8+np.asarray(s.faces).size*8 for s in surfaces)
    if geometry_bound>=max_bytes:
        raise ValueError('Surface preprocessing exceeds memory budget')
    prepared=[]
    for s in sorted(surfaces,key=lambda s:s.instance_id):
        v,f=np.asarray(s.vertices_mm),np.asarray(s.faces)
        if (s.frame_id!=grid.frame_id or s.provenance not in ('source','estimated')
                or not isinstance(s.source_ref,str) or not s.source_ref.strip()
                or type(s.anatomical_label) is not int or not 0<=s.anatomical_label<=np.iinfo(np.uint32).max):
            raise ValueError('Valid surface frame, provenance and label required')
        if (v.ndim!=2 or v.shape[1]!=3 or v.dtype.kind not in 'ifu' or not np.isfinite(v).all()
                or f.ndim!=2 or f.shape[1]!=3 or len(f)<4 or not np.issubdtype(f.dtype,np.integer)
                or f.min()<0 or f.max()>=len(v)):
            raise ValueError('Valid surface arrays required')
        mesh=trimesh.Trimesh(v,f,process=False)
        if normalize_exact_indices:
            mesh,_=exact_vertex_index_copy(mesh)
        if not (mesh.is_watertight and mesh.is_winding_consistent and mesh.is_volume and np.all(mesh.area_faces>0)):
            raise ValueError(f'Closed oriented nondegenerate volume required: instance {s.instance_id}')
        surface=replace(s,vertices_mm=np.asarray(mesh.vertices),faces=np.asarray(mesh.faces))
        prepared.append((surface,mesh.vertices.min(0)-surface_tolerance_mm,
                         mesh.vertices.max(0)+surface_tolerance_mm))
    step=np.asarray(grid.spacing_xyz_mm)
    origin=np.asarray(grid.origin_xyz_mm)
    ranges=[range(0,n,t) for n,t in zip(grid.shape_zyx,tile_shape_zyx)]
    for start in itertools.product(*ranges):
        shape=tuple(min(t,n-a) for t,n,a in zip(tile_shape_zyx,grid.shape_zyx,start))
        low=origin+np.asarray(start[::-1])*step
        high=low+(np.asarray(shape[::-1])-1)*step
        active=[s for s,a,b in prepared if np.all(b>=low) and np.all(a<=high)]
        if not active:
            continue
        tile_grid=Grid(shape,grid.spacing_xyz_mm,tuple(low),grid.frame_id)
        volume=voxelize(active,tile_grid,max_bytes=max_bytes-geometry_bound,
                        surface_tolerance_mm=surface_tolerance_mm)
        if volume.foreground.any():
            yield start,volume


def write_mask_tiles(destination, surfaces, grid, *, context=None, progress=None, **options):
    """Publish a new sparse tile directory after every tile succeeds.

    Missing tiles represent background, never uncomputed data in a completed
    manifest. A caller must retain the returned manifest hash for integrity checks.
    """
    from .case_io import _encode
    destination=Path(destination)
    destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.exists():
        raise FileExistsError('Mask tile destination already exists')
    lock=destination.with_name(destination.name+'.lock')
    fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    temporary=None
    try:
        os.close(fd)
        temporary=Path(tempfile.mkdtemp(prefix='.'+destination.name+'-',dir=destination.parent))
        tiles=[]
        surfaces=list(surfaces)
        sampled_counts={s.instance_id:0 for s in surfaces}
        fields=('foreground','anatomical','instance','provenance','overlap_count','membership')
        for start,volume in iter_mask_tiles(surfaces,grid,**options):
            for i,instance in enumerate(volume.instances):
                sampled_counts[instance['instance_id']]+=int(volume.membership[i].sum())
            name='tile-'+'-'.join(map(str,start))+'.npz'
            path=temporary/name
            with path.open('xb') as stream:
                np.savez_compressed(stream,**{k:getattr(volume,k) for k in fields})
            digest=hashlib.sha256()
            with path.open('rb') as stream:
                for block in iter(lambda:stream.read(1024*1024),b''):
                    digest.update(block)
            tiles.append(dict(file=name,start_zyx=list(start),metadata=volume.metadata(),
                              sha256=digest.hexdigest(),bytes=path.stat().st_size))
            if progress is not None:
                progress(len(tiles),start)
        sampling_summary=dict(
            status='ZERO_SAMPLED_INSTANCES' if any(n==0 for n in sampled_counts.values()) else 'ALL_INSTANCES_SAMPLED',
            instances=[dict(instance_id=s.instance_id,source_ref=s.source_ref,
                            sampled_voxels=sampled_counts[s.instance_id])
                       for s in sorted(surfaces,key=lambda s:s.instance_id)],
            zero_sampled_instance_ids=sorted(i for i,n in sampled_counts.items() if n==0),
            limitation='Voxel-center coverage only; zero counts may reflect sampling or grid exclusion. Positive counts do not prove geometric fidelity.')
        manifest=dict(schema='vv-toolbox.sparse-mask-tiles/1',complete=True,
            frame_id=grid.frame_id,shape_zyx=list(grid.shape_zyx),
            spacing_xyz_mm=list(grid.spacing_xyz_mm),origin_xyz_mm=list(grid.origin_xyz_mm),
            tile_shape_zyx=list(options.get('tile_shape_zyx',(32,32,32))),
            exact_index_normalization=options.get('normalize_exact_indices',False),
            omitted_tiles='all-zero background; all grid tiles evaluated or excluded by surface bounds',
            tiles=tiles,context=context,sampling_summary=sampling_summary,
            anatomical_validation='NOT RUN',self_intersection='NOT RUN')
        encoded=_encode(manifest)
        with (temporary/'manifest.json').open('xb') as stream:
            stream.write(encoded);stream.flush();os.fsync(stream.fileno())
        if destination.exists():
            raise FileExistsError('Mask tile destination appeared during generation')
        temporary.rename(destination);temporary=None
        return dict(status='WRITTEN',tiles=len(tiles),sampling_summary=sampling_summary,
                    manifest_sha256=hashlib.sha256(encoded).hexdigest())
    finally:
        if temporary is not None:
            shutil.rmtree(temporary)
        lock.unlink()
