# Batch artifact integrity

New batch cases include `artifacts.json` alongside the case snapshot, surface,
optional whole mask and lesion ROI outputs. The manifest records:

- Case revision and source-case revision.
- Base model, batch/attempt seeds, attempted parameters and surface spacing.
- Selected/omitted edge coverage.
- Actual surface and mask check states, including NOT RUN and UNKNOWN.
- Every output file's byte length and SHA256.

The batch report stores `artifact_manifest_sha256` for each published case.
The manifest is written in the temporary case directory before publication, so
manifest-generation failure does not produce an accepted case directory.
Existing exports are not rewritten.

Verify a generated case using its digest from the separate batch report:

```text
python -m vv_toolbox.case_artifacts <case-folder> --expected-sha256 <artifact_manifest_sha256>
```

The verifier checks exact manifest/file bytes, required and unexpected files,
simple local filenames, and the validated case snapshot revision. It rejects
linked artifacts. PASS is explicitly limited to file integrity and case
revision; it does not promote embedded geometry UNKNOWN/NOT RUN states to PASS.
The report digest must be retained independently to detect replacement of the
manifest itself. These hashes are not a cryptographic signature of authorship.

## Verification

Docker command:

```text
python -m pytest tests/test_batch.py tests/test_batch_distribution.py -q
```

**PASS: 16 tests**, including:

- Successful whole-case surface/mask bundle verification.
- Surface self-intersection NOT RUN preserved in manifest quality.
- Changed, missing, unexpected and altered-manifest files rejected.
- CLI success and nonzero failure exit paths.
- Existing deterministic replay, accepted-count, failure-isolation and
  parameter-distribution tests.

The run emitted 62 existing NumPy/scikit-image deprecation warnings.
This focused run follows the earlier 802-case regression evidence; that earlier
full run does not cover this new manifest implementation.
