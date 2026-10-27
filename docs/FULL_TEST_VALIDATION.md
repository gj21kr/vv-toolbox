# Automated test validation

## Saved-case workbench integration regression

After the saved-case editor, relationship preview, smoothing, exact-coordinate
index normalization and whole-interval containment checker were added, a full
Docker run completed: **863 passed, 0 failed, 0 skipped**, 355 NumPy/scikit-image
deprecation warnings, 112.40 seconds.

```text
python -m pytest -q --junitxml=/workspace/docs/evidence/workbench-integration-full-tests.xml
```

The configured test selection is `tests` in `pyproject.toml`.
Evidence: [complete JUnit results](evidence/workbench-integration-full-tests.xml).
The run used the existing `vv-annotation-ui` container and the working tree at
HEAD `e42b0ef70460a06465007c1c74401701b00a6705`, including uncommitted changes.
No source edits were made during the run. The preserved user atlas snapshot
SHA256 was checked before this run and remained
`082a9178daee4d52c79aaa709cba91fbdc56cfb5767fef4801fd4b9bb22d1964`.

This is automated regression evidence. It does not establish a new live
browser verification, anatomical boundary approval, complete access routes or
surface geometry acceptance. The containment checker remains an offline tool;
its numerical results are not yet an editor acceptance gate.

## Output integration regression

After access-vessel labels, saved-case label commands, baseline batch generation
and lesion-free mask output were added, the working tree completed one full run:
**838 passed, 0 failed, 0 skipped**, 355 NumPy/scikit-image deprecation warnings,
108.73 seconds. The failure cap was not reached.

```text
python -m pytest tests -q --maxfail=5 --junitxml=/workspace/docs/evidence/output-integration-full-tests.xml
```

Evidence: [complete JUnit results](evidence/output-integration-full-tests.xml).
Runtime: existing `vv-annotation-ui` Docker container, Python 3.12.15 and Node
v22.23.3. Git HEAD remains `e42b0ef70460a06465007c1c74401701b00a6705`;
the result includes local changes and is not a test of that commit alone.
No source edits were made while this run was active.

The saved atlas-edit snapshot still has SHA256
`082a9178daee4d52c79aaa709cba91fbdc56cfb5767fef4801fd4b9bb22d1964`,
matching the previously recorded user snapshot. This run did not exercise
a new live browser workflow. It does not approve unresolved anatomical
boundaries, complete access routes, or experimental surface geometry.

## Earlier regression

The earlier working tree completed the full test selection and a follow-up of
the Node-dependent tests. This is regression evidence, not completion of all
development milestones.

| Run | Passed | Failed/errors | Skipped | Duration |
|---|---:|---:|---:|---:|
| All tests | 799 | 0 | 3 | 96.42 s |
| Node-dependent UI logic follow-up | 3 | 0 | 0 | 1.08 s |

All **802 unique test cases** have a passing result across these two runs.
Do not describe this as a single uninterrupted 802-pass run.

The follow-up covers both-end along-path relationships, more than four neighbors
on both sides, and separation of unresolved mapping slots from vessel diagrams.
The first run emitted 330 NumPy/scikit-image deprecation warnings; warnings are
retained in the log and have not been treated as failures.

## Environment and evidence

- Existing Docker container `vv-annotation-ui`; Python 3.12.15.
- Node v22.23.3 copied from the locally available official image
  `node@sha256:c3de60bf2f9dd0ac6370e6117950ff62d6e339527e7472301c9c78a017978392`.
- The temporary Node extraction container was removed.
- Python base image:
  `python@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1`.
- Git HEAD was `e42b0ef70460a06465007c1c74401701b00a6705`, with working-tree
  changes; these results do not describe that commit alone.

Commands run inside the container with `PYTHONPATH=src`:

```text
python -m pytest tests -q --maxfail=5 --junitxml=/workspace/exports/full-validation/pytest.xml
python -m pytest tests/test_endpoint_neighborhood.py tests/test_relationship_ui.py -q --junitxml=/workspace/exports/full-validation/ui-logic.xml
```

The failure cap was not reached; the first command completed the entire
selection. Raw JUnit records, logs, package versions and current source hashes
are tracked under `docs/evidence/full-validation/`. The hashes were captured
after the runs by `scripts/record_test_suite_evidence.py`; they are a record of
the observed working tree, not a pre-run immutable build manifest.

The live application and user snapshot were not modified by this test run.
Browser checks are recorded separately in `ATLAS_EDIT_CONTACT_GATE.md`.
Outstanding anatomical boundaries, full access-route acceptance, cross-section
accuracy and experimental geometry failures remain outstanding despite this
test result.
