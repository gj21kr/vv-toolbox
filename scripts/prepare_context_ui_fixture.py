"""Small actual numerical context result for controlled browser transport tests."""
from pathlib import Path

from test_registered_context import fixture
from vv_toolbox.registered_context import inspect_registered_context,context_fingerprint,case_with_context
from vv_toolbox.case_io import save_case

parent,case,neighbors=fixture()
report=inspect_registered_context(case,parent,neighbors,expected_context_sha256=context_fingerprint(neighbors),
                                  expected_neighbor_ids=['distant'])
folder=Path('exports/context-job-ui');folder.mkdir(parents=True,exist_ok=True)
save_case(folder/'input.snapshot.json',case)
save_case(folder/'result.snapshot.json',case_with_context(case,report))
