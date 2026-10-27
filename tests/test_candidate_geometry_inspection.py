import json
from pathlib import Path
import subprocess
import sys

import pytest

from vv_toolbox.case_io import save_case
from vv_toolbox.synthetic_routes import build_synthetic_routes
from test_synthetic_routes import fixture


@pytest.mark.parametrize('invalid', ['stale', 'overwrite', 'normalization'])
def test_audit_rejects_bad_binding_without_publishing(tmp_path, invalid):
    source, bridges = fixture()
    candidate = build_synthetic_routes(source, bridges, case_id='candidate')
    baseline_path, candidate_path = tmp_path/'baseline.json', tmp_path/'candidate.json'
    old = save_case(baseline_path, source)
    new = save_case(candidate_path, candidate)
    spec = dict(schema='vv-toolbox.candidate-geometry-audit/1',
                baseline=dict(snapshot=str(baseline_path), revision=old, focus_edge_ids=['a', 'b']),
                candidate=dict(snapshot=str(candidate_path), revision=new, focus_edge_ids=['a', 'b', 'bridge']),
                margin_mm=1.2, spacing_mm=.6, max_segment_pairs=10000)
    if invalid == 'stale': spec['candidate']['revision'] = '0'*64
    if invalid == 'normalization': spec['candidate_normalization'] = {'missing': 'a'}
    request = tmp_path/'request.json'; request.write_text(json.dumps(spec))
    output = candidate_path if invalid == 'overwrite' else tmp_path/'report.json'
    before = candidate_path.read_bytes()
    command = [sys.executable, str(Path(__file__).resolve().parents[1]/'scripts/inspect_candidate_geometry.py'),
               str(request), str(output), str(tmp_path/'artifacts')]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode != 0
    expected = {'stale': 'revision mismatch', 'overwrite': 'may not overwrite', 'normalization': 'normalization must map'}[invalid]
    assert expected in result.stderr
    assert candidate_path.read_bytes() == before
    assert not (tmp_path/'artifacts').exists()
    if invalid != 'overwrite': assert not output.exists()
