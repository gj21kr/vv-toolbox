"""Fixed-parameter smoothing of the downloaded registered bend case."""
import json
import time
from pathlib import Path

from vv_toolbox.case_io import load_case, save_case
from vv_toolbox.label_workbench import process_request


def main():
    root = Path(__file__).resolve().parents[1]
    input_path = root/'exports/bend-case-download/case.snapshot.json'
    source, revision = load_case(input_path)
    parameters = dict(edge_id='FJ2074:e0', sigma_mm=.5, max_displacement_mm=.3)
    target = root/'docs/evidence/saved-bend-smoothing.json'
    report = dict(status='RUNNING', parent_revision=revision, parameters=parameters,
                  scope='Single registered centerline edit; fixed surface; not anatomy acceptance')
    target.write_text(json.dumps(report, indent=2)+'\n')
    started = time.perf_counter()
    try:
        result = process_request(dict(action='smooth', snapshot=input_path.read_text(), parameters=parameters))
        case = result['snapshot']['case']
        assert case['surface_parts'][0]['vertices_mm'] == source['surface_parts'][0]['vertices_mm']
        assert case['surface_parts'][0]['faces'] == source['surface_parts'][0]['faces']
        assert case['nodes'] == source['nodes']
        assert case['inspection']['access_candidate'] == source['inspection']['access_candidate']
        for before, after in zip(source['edges'], case['edges']):
            if before['id'] != parameters['edge_id']:
                assert before == after
        output = root/'exports/saved-bend-smoothing/case.snapshot.json'
        output.parent.mkdir(parents=True, exist_ok=True)
        save_case(output, case)
        loaded, saved_revision = load_case(output)
        assert loaded == case
        report.update(status='PASS', revision=saved_revision, file=str(output.relative_to(root)),
            metrics=case['centerline_regularization']['metrics'],
            inspection=case['inspection']['centerline_edit'],
            parent_context_status=case['inspection']['access_candidate']['context']['status'])
    except Exception as error:
        report.update(status='FAIL', error=str(error))
        raise
    finally:
        report['elapsed_seconds'] = time.perf_counter()-started
        target.write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps({k:v for k,v in report.items() if k!='inspection'}), flush=True)


if __name__ == '__main__':
    main()
