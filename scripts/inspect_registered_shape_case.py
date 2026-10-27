"""Fixed full-case wall/graph deformation; no neighbor acceptance inferred."""
import json
from pathlib import Path
import time

from vv_toolbox.case_io import load_case, save_case
from vv_toolbox.registered_shape_edit import deform_registered_source


def main():
    root = Path(__file__).resolve().parents[1]
    case, parent = load_case(root/'exports/candidate-case-download/case.snapshot.json')
    parameters = dict(edge_id='FJ2074:e0', bend_mm=.25, bend_direction=[1,0,0], twist_deg=0.,
                      collar_mm=1., transition_mm=10., max_displacement_mm=1.)
    target = root/'docs/evidence/registered-shape-case.json'
    report = dict(status='RUNNING', parent_revision=parent, parameters=parameters,
                  scope='Full registered case deformation and bound path inspection; neighbors NOT RUN')
    target.write_text(json.dumps(report, indent=2)+'\n')
    started = time.perf_counter()
    try:
        result = deform_registered_source(case, **parameters)
        assert result['nodes'] == case['nodes']
        for old, new in zip(case['edges'], result['edges']):
            if old['id'] != parameters['edge_id']:
                assert old == new
        output = root/'exports/registered-shape-case/case.snapshot.json'
        output.parent.mkdir(parents=True, exist_ok=True)
        revision = save_case(output, result)
        loaded, read_revision = load_case(output)
        assert loaded == result and read_revision == revision
        audit = result['inspection']['registered_shape_edit']
        report.update(status='PASS', revision=revision, output=str(output.relative_to(root)),
            checked_paths=len(audit['checked_paths']), audit=audit['audit'],
            accepted_for_generation=audit['accepted_for_generation'])
    except Exception as error:
        report.update(status='FAIL', error=str(error))
        raise
    finally:
        report['elapsed_seconds'] = time.perf_counter()-started
        target.write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps({k:v for k,v in report.items() if k!='audit'}), flush=True)


if __name__ == '__main__':
    main()
