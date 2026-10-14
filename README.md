# VV Toolbox — Virtual Vessel Toolbox

A local vascular atlas workspace with artery/vein visualization, centerlines, vessel relationship candidates, and per-vessel shape editing. Inspired by the Python + browser workflow of [VH Toolbox](https://github.com/gerardponsmoll/vh-toolbox); this is an independent implementation.

## Quick start

Requires Python 3.11+ and a browser. On Windows:

```powershell
py -3 -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python scripts/acquire_atlas.py
.venv/Scripts/vv-toolbox --port 8093
```

On macOS/Linux, use `python3` and `.venv/bin/` instead. Open http://127.0.0.1:8093. The app and embedded 3D viewer bind to loopback ports 8093 and 8094. Initial preparation and the first centerline extraction can take several minutes; later extractions use a local cache. Stop with Ctrl+C. Dependencies are bounded, not fully locked.

Atlas acquisition explicitly downloads BodyParts3D assets into Git-ignored `reference-data/`. Source data, geometry, caches and local exports are **not bundled**. Review attribution and licensing in [ATLAS_ANATOMY.md](ATLAS_ANATOMY.md) and the downloaded source license before using or redistributing assets.

## Atlas workspace

1. **Select a vessel:** search by name/atlas ID or region.
2. **Vessel relationships:** click a named neighbor to focus it in 3D. Dashed links are proximity candidates, not confirmed anatomical connections or flow directions. The nearest four candidates are displayed with a total count.
3. **Modify selected vessel:** select a vessel in the panel and adjust radius (0.5–2), tortuosity (-1–1), and torsion (-180–180 degrees). Apply updates the surface and graph. Restore original removes the override.

Arteries are red and veins use blue shades. Estimated missing vessels retain provenance labels and can be hidden. Display options and source details are collapsible. Separate legacy schematic navigation is not exposed.

Edits start from original geometry, preserving source files. Endpoint/junction collars are protected approximately; short branches may change little. Torsion twists a path around its endpoint chord, not a prescribed clinical torsion metric. Edits can create collisions or invalid surfaces. See [modification limits](ATLAS_ANATOMY.md).

All tabs share the running workspace. Edits are in memory; restarting does not automatically restore them. `/api/export` exports the workspace including overrides and modified surfaces. The panel's centerline download exports the graph. Import/reload is not implemented.

## Scope

The selected source has 805 vascular parts: 804 centerlines were extracted and one open source surface remains unresolved. Some voxel-derived centerlines are coarse or disconnected. Missing neck connections and cerebral veins are estimated additions, not recovered anatomy. One atlas does not represent population variation.

This is research/illustrative software, not patient-specific anatomy, validated flow, catheter contact or clinical planning, or geometry certified for CFD/FEM/manufacturing. See [validation evidence](VALIDATION.md), [anatomical scope](ANATOMY_SCOPE.md), and [venous scope](VENOUS_EXTENSION.md).

## Python API

The authored synthetic generator remains a separate library API:

```python
from vv_toolbox import generate

graph = generate(radius_scale=1.0, tortuosity=0.3)
segments, length_mm = graph.route("right_femoral", "left_mca")
graph.validate()
document = graph.to_json()
```

It uses authored coordinates/radii rather than atlas geometry. Routes are undirected shortest paths, not blood flow or access feasibility. See [the optional reference adapter](REFERENCE_PIPELINE.md).

## Validation

```powershell
.venv/Scripts/python -m pytest -q
.venv/Scripts/python -m pip install "build>=1,<2"
.venv/Scripts/python -m build
```

CI runs tests and packaging. Browser verification and anatomical validation remain separate; see [VALIDATION.md](VALIDATION.md).

## Data boundary

Only source code, tests and documentation are tracked. Do not add patient images/identifiers, company geometry, credentials, external datasets or local exports. External source licenses remain separate. Runtime does not automatically download anatomy data or send it to external services.
