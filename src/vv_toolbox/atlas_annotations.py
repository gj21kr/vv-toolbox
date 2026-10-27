"""Source-bound cerebral boundary annotations; research use only, not for clinical decision.

Coordinates retain their declared frame and units. This module never estimates
anatomical positions or interprets a saved review as clinical validation.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
import re
import tempfile


SCHEMA_VERSION = "1.0"
BOUNDARIES = {
    "ACA": {
        "A1_A2": "acom_attachment",
        "A2_A3": "callosal_rostrum_genu_transition",
        "A3_A4": "callosal_superior_surface_transition",
    },
    "MCA": {
        "M1_M2": "limen_insulae_genu",
        "M2_M3": "insular_opercular_transition",
        "M3_M4": "sylvian_cortical_exit",
    },
}
SCHEMES = {"ACA": "aca_five_segment_topographic_v1", "MCA": "mca_topographic_v1"}
STATUSES = {"unresolved", "name_candidate", "source_annotation", "landmark_reviewed", "synthetic_estimate"}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def new_annotation_document(
    source_id: str,
    source_sha256: str,
    *,
    coordinate_frame_id: str = "unknown",
    units: str = "unknown",
    frame_confirmed: bool = False,
    units_confirmed: bool = False,
) -> dict:
    """Create unresolved placeholders, not inferred positions or branch counts."""
    document = {
        "schema": "vv_toolbox.cerebral_boundaries",
        "schema_version": SCHEMA_VERSION,
        "model_kind": "source",
        "source": {"id": source_id, "sha256": source_sha256},
        "coordinate_frame": {
            "id": coordinate_frame_id, "units": units,
            "frame_confirmed": frame_confirmed, "units_confirmed": units_confirmed,
        },
        "boundaries": [],
    }
    for side in ("L", "R"):
        for artery, transitions in BOUNDARIES.items():
            for transition, landmark in transitions.items():
                document["boundaries"].append({
                    "boundary_id": f"B.{side}.{artery}.{transition}",
                    "artery": artery, "side": side, "transition": transition,
                    "segmentation_scheme": SCHEMES[artery],
                    "branch_id": None, "landmark_type": landmark,
                    "position": None, "coordinate_frame_id": coordinate_frame_id,
                    "source_refs": [], "evidence_status": "unresolved",
                    "reason": "Specimen landmark position has not been reviewed.",
                    "review_note": "",
                })
    validate_annotations(document)
    return document


def validate_annotations(document: dict) -> None:
    """Reject malformed or falsely located annotations without changing input."""
    _require(isinstance(document, dict), "annotation document must be an object")
    _require(document.get("schema") == "vv_toolbox.cerebral_boundaries", "unknown schema")
    _require(document.get("schema_version") == SCHEMA_VERSION, "unsupported schema version")
    _require(document.get("model_kind") in ("source", "synthetic"), "invalid model_kind")
    source = document.get("source")
    _require(isinstance(source, dict), "source is required")
    _require(_text(source.get("id")), "source.id is required")
    digest = source.get("sha256")
    _require(isinstance(digest, str) and re.fullmatch(r"[0-9a-fA-F]{64}", digest) is not None,
             "source.sha256 must be a SHA256 digest")
    frame = document.get("coordinate_frame")
    _require(isinstance(frame, dict), "coordinate_frame is required")
    _require(_text(frame.get("id")), "coordinate frame id is required")
    _require(frame.get("units") in ("mm", "cm", "m", "unknown"), "invalid coordinate units")
    for key in ("frame_confirmed", "units_confirmed"):
        _require(type(frame.get(key)) is bool, f"{key} must be boolean")
    _require(not frame["frame_confirmed"] or frame["id"].lower() != "unknown", "unknown frame cannot be confirmed")
    _require(not frame["units_confirmed"] or frame["units"] != "unknown", "unknown units cannot be confirmed")
    boundaries = document.get("boundaries")
    _require(isinstance(boundaries, list), "boundaries must be a list")
    seen = set()
    for boundary in boundaries:
        _require(isinstance(boundary, dict), "boundary must be an object")
        ident = boundary.get("boundary_id")
        _require(_text(ident), "boundary_id is required")
        _require(ident not in seen, "duplicate boundary_id")
        seen.add(ident)
        artery, side, transition = (boundary.get(k) for k in ("artery", "side", "transition"))
        _require(isinstance(artery, str) and artery in BOUNDARIES, "invalid artery")
        _require(side in ("L", "R"), "invalid side")
        _require(isinstance(transition, str) and transition in BOUNDARIES[artery], "invalid transition")
        prefix = f"B.{side}.{artery}.{transition}"
        _require(ident == prefix or (ident.startswith(prefix + ".") and _text(ident[len(prefix) + 1:])),
                 "boundary_id does not match its side and transition")
        _require(boundary.get("segmentation_scheme") == SCHEMES[artery], "invalid segmentation scheme")
        _require(boundary.get("landmark_type") == BOUNDARIES[artery][transition], "invalid landmark_type")
        _require("branch_id" in boundary and (boundary["branch_id"] is None or _text(boundary["branch_id"])), "invalid branch_id")
        _require(boundary.get("coordinate_frame_id") == frame["id"], "boundary coordinate frame mismatch")
        _require("position" in boundary, "position is required")
        position = boundary["position"]
        if position is not None:
            _require(isinstance(position, list) and len(position) == 3, "position must be null or xyz list")
            _require(all(type(v) in (int, float) and math.isfinite(v) for v in position), "position must contain finite numbers")
        status = boundary.get("evidence_status")
        _require(isinstance(status, str) and status in STATUSES, "invalid evidence_status")
        refs = boundary.get("source_refs")
        _require(isinstance(refs, list) and all(_text(ref) for ref in refs), "source_refs must be a list of references")
        _require(isinstance(boundary.get("review_note"), str), "review_note is required")
        _require(isinstance(boundary.get("reason"), str), "reason is required")
        if status in ("unresolved", "name_candidate"):
            _require(position is None and _text(boundary["reason"]), "unresolved positions require null and a reason")
        if status in ("source_annotation", "landmark_reviewed"):
            _require(bool(refs), "source or reviewed annotations require source references")
        if status == "landmark_reviewed":
            _require(position is not None and frame["frame_confirmed"] and frame["units_confirmed"],
                     "reviewed position requires coordinates and confirmed frame and units")
        if status == "synthetic_estimate":
            _require(document["model_kind"] == "synthetic", "synthetic estimates cannot annotate the source model")
            _require(position is not None and _text(boundary["reason"]), "synthetic estimate requires position and reason")


def load_annotations(path: str | Path) -> dict:
    """Load and validate JSON; corrupt files are never replaced by defaults."""
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_annotations(document)
    return document


def save_annotations(path: str | Path, document: dict) -> None:
    """Validate before an atomic replacement, preserving the file on failure."""
    validate_annotations(document)
    payload = json.dumps(document, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    target = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=target.parent,
                                         prefix=f".{target.name}.", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
