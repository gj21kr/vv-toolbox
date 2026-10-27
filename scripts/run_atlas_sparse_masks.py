"""Fixed all-source Atlas engineering run; measured execution, not anatomy approval."""
import json
from pathlib import Path
import resource
import time

from vv_toolbox.case_io import load_case
from vv_toolbox.case_tiles import export_case_tiles
from vv_toolbox.voxel_tile_reader import iter_saved_tiles


def main():
    started=time.monotonic()
    report=Path('docs/evidence/atlas-sparse-mask-run.json')
    case,revision=load_case('exports/atlas-case-capture-ui/case.snapshot.json')
    if len(case['surface_parts'])!=517 or any(p['provenance']!='source' for p in case['surface_parts']):
        raise ValueError('Frozen 517-source-part cohort required')
    state=dict(status='RUNNING',case_revision=revision,surface_parts=517,spacing_mm=1.,
               tile_shape_zyx=[32,32,32],max_algorithm_bytes=256*1024**2,
               scope='All 517 captured original arterial surfaces; estimated neck connectors excluded',
               anatomical_validation='NOT RUN',tiles_written=0)
    def save():
        state['elapsed_seconds']=round(time.monotonic()-started,3)
        state['peak_process_rss_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        report.write_text(json.dumps(state,indent=2)+'\n')
    def progress(count,start):
        if count==1 or count%16==0:
            state.update(tiles_written=count,last_start_zyx=list(start));save()
            print(json.dumps({k:state[k] for k in ('status','tiles_written','elapsed_seconds')}),flush=True)
    save()
    try:
        result=export_case_tiles(case,'exports/atlas-source-masks-1mm',spacing_mm=1.,
                                 tile_shape_zyx=(32,32,32),max_bytes=256*1024**2,progress=progress)
        foreground=0
        for _,arrays,_ in iter_saved_tiles('exports/atlas-source-masks-1mm',
                                          expected_manifest_sha256=result['manifest_sha256']):
            foreground+=int(arrays['foreground'].sum())
        state.update(status='PASS',tiles_written=result['tiles'],foreground_voxels=foreground,
                     manifest_sha256=result['manifest_sha256'],file_integrity='PASS')
    except Exception as error:
        state.update(status='FAIL',error=f'{type(error).__name__}: {error}')
        raise
    finally:
        save()
        print(json.dumps(state),flush=True)


if __name__=='__main__':
    main()
