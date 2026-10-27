"""Export exact registered case parts as bounded sparse mask tiles."""
import argparse
import math

import numpy as np

from .anatomical_labels import resolve_labels
from .case_contract import validate_case
from .case_io import case_digest, load_case
from .voxel_output import Grid, Surface
from .voxel_tiles import write_mask_tiles


def export_case_tiles(case, destination, *, spacing_mm, part_ids=None,
                      tile_shape_zyx=(32,32,32), max_bytes=256*1024**2, progress=None):
    validate_case(case)
    if not case.get('surface_parts') or case.get('lesions'):
        raise ValueError('Registered surfaces without unmaterialized lesions required')
    if type(spacing_mm) not in (int,float) or not math.isfinite(spacing_mm) or spacing_mm<=0:
        raise ValueError('Positive finite spacing required')
    by_id={p['part_id']:p for p in case['surface_parts']}
    chosen=sorted(by_id) if part_ids is None else part_ids
    if (not isinstance(chosen,list) or not chosen or any(not isinstance(i,str) for i in chosen)
            or len(set(chosen))!=len(chosen) or not set(chosen)<=set(by_id)):
        raise ValueError('Explicit unique registered part IDs required')
    parts=[by_id[i] for i in sorted(chosen)]
    edges=[i for p in parts for i in p['edge_ids']]
    labels,registry=resolve_labels(case,edges)
    revision=case_digest(case)
    surfaces=[];mapping={}
    low=np.full(3,np.inf);high=np.full(3,-np.inf)
    for instance,p in enumerate(parts,1):
        values={labels[e] for e in p['edge_ids']}
        if len(values)!=1:
            raise ValueError('Multiple segment labels require explicit surface partition')
        vertices=np.asarray(p['vertices_mm'],float)
        low=np.minimum(low,vertices.min(0));high=np.maximum(high,vertices.max(0))
        surfaces.append(Surface(instance,values.pop(),p['provenance'],vertices,
                                np.asarray(p['faces'],np.int64),case['frame']['id'],
                                f"case:{revision};part:{p['part_id']}"))
        mapping[p['part_id']]=dict(instance_id=instance,edge_ids=p['edge_ids'],
                                  geometry_sha256=p['geometry_sha256'])
    origin=low-spacing_mm
    shape=tuple(int(n) for n in (np.ceil((high-low)/spacing_mm).astype(object)+3)[::-1])
    grid=Grid(shape,(spacing_mm,)*3,tuple(origin),case['frame']['id'])
    context=dict(case_id=case['case_id'],case_revision=revision,
                 selected_parts=sorted(chosen),excluded_parts=sorted(set(by_id)-set(chosen)),
                 part_instances=mapping,segment_label_registry=registry,
                 source_inspection=case.get('inspection',{}),
                 lesion_presence='none_declared',lesion_labels='NOT APPLICABLE')
    return write_mask_tiles(destination,surfaces,grid,context=context,progress=progress,
                            tile_shape_zyx=tile_shape_zyx,max_bytes=max_bytes,
                            normalize_exact_indices=True)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case')
    parser.add_argument('destination')
    parser.add_argument('--spacing-mm',required=True,type=float)
    parser.add_argument('--parts',nargs='+')
    parser.add_argument('--tile-size',type=int,default=32)
    parser.add_argument('--max-mib',type=int,default=256)
    args=parser.parse_args(argv)
    case,_=load_case(args.case)
    result=export_case_tiles(case,args.destination,spacing_mm=args.spacing_mm,
                             part_ids=args.parts,tile_shape_zyx=(args.tile_size,)*3,
                             max_bytes=args.max_mib*1024**2)
    import json
    print(json.dumps(result))


if __name__=='__main__':
    main()
