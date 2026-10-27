import copy

import pytest

from vv_toolbox.atlas_annotations import (
    load_annotations, new_annotation_document, save_annotations, validate_annotations,
)


def document():
    return new_annotation_document("synthetic-test-fixture", "a" * 64)


def reviewed_document():
    data = new_annotation_document(
        "synthetic-test-fixture", "a" * 64, coordinate_frame_id="fixture-LPS",
        units="mm", frame_confirmed=True, units_confirmed=True,
    )
    data["boundaries"][0].update(
        position=[1.0, 2.0, 3.0], evidence_status="landmark_reviewed",
        source_refs=["fixture:landmark-review-1"], reason="",
    )
    return data


def test_template_is_unresolved_bilateral_and_roundtrips(tmp_path):
    data = document()
    assert len(data["boundaries"]) == 12
    assert {b["side"] for b in data["boundaries"]} == {"L", "R"}
    assert all(b["position"] is None and b["reason"] for b in data["boundaries"])
    path = tmp_path / "annotations.json"
    save_annotations(path, data)
    assert load_annotations(path) == data


def test_reviewed_coordinates_roundtrip_without_conversion(tmp_path):
    data = reviewed_document()
    path = tmp_path / "annotations.json"
    save_annotations(path, data)
    assert load_annotations(path) == data


@pytest.mark.parametrize("position", [[True, 2, 3], [float("nan"), 2, 3],
                                      [1, float("inf"), 3], [1, 2], [1, 2, "3"]])
def test_invalid_coordinates_rejected(position):
    data = reviewed_document()
    data["boundaries"][0]["position"] = position
    with pytest.raises(ValueError):
        validate_annotations(data)


@pytest.mark.parametrize("field,value", [("position", None), ("source_refs", [])])
def test_reviewed_requires_position_and_evidence(field, value):
    data = reviewed_document()
    data["boundaries"][0][field] = value
    with pytest.raises(ValueError):
        validate_annotations(data)


@pytest.mark.parametrize("field", ["frame_confirmed", "units_confirmed"])
def test_reviewed_requires_confirmed_coordinate_contract(field):
    data = reviewed_document()
    data["coordinate_frame"][field] = False
    with pytest.raises(ValueError):
        validate_annotations(data)


@pytest.mark.parametrize("patch", [{"position": [0, 0, 0]}, {"reason": ""}])
def test_unresolved_cannot_hide_placeholder_position_or_missing_reason(patch):
    data = document()
    data["boundaries"][0].update(patch)
    with pytest.raises(ValueError):
        validate_annotations(data)


def test_synthetic_position_cannot_be_saved_as_source_annotation():
    data = document()
    data["boundaries"][0].update(evidence_status="synthetic_estimate", position=[1, 2, 3])
    with pytest.raises(ValueError, match="source model"):
        validate_annotations(data)
    data["model_kind"] = "synthetic"
    validate_annotations(data)


def test_multiple_branch_boundaries_are_retained():
    data = document()
    base = next(b for b in data["boundaries"] if b["boundary_id"] == "B.L.MCA.M2_M3")
    for branch in ("branch1", "branch2", "branch3"):
        extra = copy.deepcopy(base)
        extra.update(boundary_id=base["boundary_id"] + "." + branch, branch_id=branch)
        data["boundaries"].append(extra)
    before = copy.deepcopy(data)
    validate_annotations(data)
    assert data == before and len(data["boundaries"]) == 15


def test_duplicate_id_and_frame_mismatch_rejected():
    data = document()
    data["boundaries"].append(copy.deepcopy(data["boundaries"][0]))
    with pytest.raises(ValueError, match="duplicate"):
        validate_annotations(data)
    data = document()
    data["boundaries"][0]["coordinate_frame_id"] = "other"
    with pytest.raises(ValueError, match="frame mismatch"):
        validate_annotations(data)


@pytest.mark.parametrize("contents", ["{broken", "[]", '{"schema_version":"999"}'])
def test_corruption_is_reported_not_replaced(tmp_path, contents):
    path = tmp_path / "annotations.json"
    path.write_text(contents, encoding="utf-8")
    with pytest.raises(ValueError):
        load_annotations(path)
    assert path.read_text(encoding="utf-8") == contents


def test_failed_save_preserves_existing_file(tmp_path):
    path = tmp_path / "annotations.json"
    data = document()
    save_annotations(path, data)
    before = path.read_bytes()
    data["boundaries"][0]["position"] = [0, 0, 0]
    with pytest.raises(ValueError):
        save_annotations(path, data)
    assert path.read_bytes() == before
    assert list(tmp_path.iterdir()) == [path]


def test_atomic_replace_failure_preserves_file_and_cleans_temp(tmp_path, monkeypatch):
    path = tmp_path / "annotations.json"
    save_annotations(path, document())
    before = path.read_bytes()

    def fail_replace(*args):
        raise OSError("simulated replace failure")

    monkeypatch.setattr("vv_toolbox.atlas_annotations.os.replace", fail_replace)
    with pytest.raises(OSError):
        save_annotations(path, reviewed_document())
    assert path.read_bytes() == before
    assert list(tmp_path.iterdir()) == [path]


def test_source_fingerprint_and_schema_version_are_required():
    data = document()
    data["source"]["sha256"] = "not-a-digest"
    with pytest.raises(ValueError):
        validate_annotations(data)
    data = document()
    data["schema_version"] = "2"
    with pytest.raises(ValueError):
        validate_annotations(data)
