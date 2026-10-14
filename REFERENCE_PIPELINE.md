# Reference geometry workflow

This implements the research note's first step: inspect one original aortic reference before attempting whole-body atlas registration or deformation. It does not certify the authored whole-body model as anatomical.

## Available source

- Vascular Model Repository case `0011_H_AO_H`, [Stanford permanent record](https://purl.stanford.edu/kd053sz6270).
- Repository-labelled healthy adult control, age 23. A single MR-derived research case, not a population normal template.
- Original surface: 79,328 vertices and 158,652 triangles. Five independent native modeling paths and their planar contour files are read without drawing invented connecting vessels.
- Surface SHA256: `a4b8b423a43f99cc8cb88ebbdf81c697f3f119b92dfe19441cd34a2fbfd9db01`.
- The original VMR research-and-development license is retained in the downloaded `README-COPYRIGHT`. Source files stay local in ignored `reference-data/`; no patient imaging volume is downloaded or bundled in the package.
- Millimeters are obtained by scaling the source coordinates by ten. The cm interpretation is supported by the source image filename and SimVascular convention, not an explicit geometry unit attribute. Native anatomical axis orientation remains UNKNOWN; no atlas registration is implied.

Acquire the pinned files explicitly, then launch the existing viewer:

```powershell
.venv/Scripts/python scripts/acquire_reference.py
.venv/Scripts/python -m vv_toolbox.app --port 8093
```

Acquisition validates the pinned Stanford manifest and its file sizes/SHA1 checksums, records SHA256 hashes and preserves the license. Loading is offline and revalidates the source. Missing or changed files disable reference mode; no schematic substitute is displayed as the reference.

## Viewer and export

Choose **Standalone reference arch** in the source selector. Surface mode displays the original source triangles. Centerline mode displays the independent source paths. The exported reference bundle includes provenance, geometry hashes, path samples and radius profiles. Returning to the editable schematic restores its parameters without merging subjects or coordinate systems.

Contour radius is `sqrt(area/pi)` measured from the planar source polygon, then interpolated along the path. It is not a maximal-inscribed-sphere radius, an ellipse major/minor axis or a reconstruction of the original lumen. Outside contour coverage the nearest endpoint value is held and that limitation is recorded. The surface itself remains the original geometry.

The model now supports a radius at every centerline sample. Morphometry measures length, curvature and torsion with an explicit derivative estimator, and branch angles require a shared junction and an explicit arc-length window. Undefined measurements return UNKNOWN. Schematic arch type is measured separately from the requested construction preset and labelled as a centerline surrogate, not a clinical classification.

## Boundaries and next data-dependent stages

- Reference-path junction attachment and anatomical axes need verification before branch-angle or Type I–III assessment for this case.
- BodyParts3D atlas registration and artery/vein spatial collision checks are not implemented by simply overlaying different subjects.
- Existing A1–A3/M1–M3/P1–P3 schematic subdivisions remain estimated, not TopBrain annotations. Their exported definitions and the UI state this explicitly. A source label-map and an anatomical landmark protocol are needed before replacing them with validated segments.
- Population shape statistics, non-circular cross sections, reference-driven whole-body deformation and clinical acceptance remain unvalidated. Arbitrary error tolerances have not been introduced.

These boundaries follow the supplied research note; this delivery establishes a source-preserving reference and measurement pipeline rather than relabelling the old synthetic coordinates as measured anatomy.
