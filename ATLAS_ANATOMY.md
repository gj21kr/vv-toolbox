# Shared-coordinate anatomy correction

The workspace starts in the editable graph and vessel modification mode. The persistent Atlas reference button opens BodyParts3D when its optional local data are available; returning to the editor preserves authored parameters. Arteries, systemic veins, portal veins and heart context come from the same atlas coordinate system. Individual original parts are not translated to achieve clearance. User-authorized estimates of missing vessels are overlaid separately and can be hidden.

This is a reference adult anatomical model, not patient-specific anatomy or clinical acceptance. Source mesh simplification, coverage and units are described in the inspector. Source part identifiers and attribution accompany the export. Source-mesh medial paths and an explicit candidate graph are now available as described below; atlas shape editing and verified inter-part anatomical connectivity are not yet available.

## Atlas centerlines and candidate graph

The viewer extracts each vascular source mesh independently. A working copy welds duplicated OBJ vertices; a closed surface is voxelized, filled and reduced with Lee 3D thinning. Degree-two voxel chains become paths; junction voxel clusters become nodes. Curves, branches, disconnected components and cycles are retained. The original surface coordinates and faces are never edited. No PCA line or nearest-node bridge replaces a failed extraction.

Voxel pitch is adaptive (normally 0.12–0.8 assumed mm, coarsened to bound the grid). Radii come from the voxel distance transform; small branches, terminal placement, medial spurs and radius estimates remain resolution-dependent. Open source surfaces and empty skeletons are reported as UNRESOLVED. Source and algorithm fingerprints identify cached per-part results under ignored `reference-data/bodyparts3d/centerline-cache/`.

The atlas panel shows the selected vessel's paths and neighboring candidates in X/Z projection. Solid paths are mesh-derived or explicitly authored estimates. Dashed links are endpoint-to-path proximity candidates within the same circulation, using sampled radii and a two-source-unit gap allowance. They do not merge nodes, change meshes, assert a true ostium or define blood flow. Candidate attachments retain their target edge and sampled position. The estimated neck/sinus parts use their existing authored centerlines and are not presented as source-extracted anatomy.

`Atlas centerlines` overlays the paths on translucent source surfaces. Selection is shared by the neighborhood graph, structure list and 3D centerlines. The graph can be downloaded from `/api/atlas-centerlines`, and is included in the atlas workspace export. Existing schematic editing remains separate.

## Detailed vascular map correction — 2026-10-14

The official IS-A vessel groups alone omitted named arterial segments, vascular trunks and anastomoses. Explicit official categories now recover these original elements without transformations: 518 arterial, 248 systemic venous, 39 portal and 23 context meshes (828 distinct source elements). This includes descending thoracic aorta, proximal MCA/PCA subdivisions and both portal trunks. A selected atlas vessel is highlighted and focused; name/ID search and approximate regional filters browse the detailed source map from femoral to cerebral. Existing schematic graph/shape editing stays separately available.

The source has no identified cerebral venous sinus geometry. An explicitly estimated overlay now supplies bilateral IJV extensions, sigmoid/transverse paths, superior sagittal and straight sinus paths (11 named segments in one fused display surface). Only the lower IJV attachment sections are source-derived. Upper positions are authored from head vascular bounds, not recovered anatomy or registration. The original missing-source flags remain, with estimated display resolution recorded. This does not fill every cerebral tributary or establish whole-body lumen connectivity, source-to-estimate Boolean fusion or clinical validity. Original source meshes are unchanged; the estimates can be hidden independently.

Topology reference: [Piffer 1979, sigmoid sinus–jugular bulb–internal jugular transition](https://pubmed.ncbi.nlm.nih.gov/532542/). This supports the named connection, not the generated positions, radii or patient anatomy.

### Estimated carotid–jugular collision correction

The initial estimated IJVs intersected both estimated carotid connectors. The corrected IJV centerlines use bounded anterolateral squared-sine bows with fixed endpoints, zero endpoint displacement derivatives and unchanged radius profiles. The amplitude is solved for at least 1 original source unit of conservative capsule clearance across non-junction estimated segment pairs; a failed bound suppresses the venous estimate and reports the failed fit. Current source data require approximately 15.115 units on the right and 12.945 on the left. The correction remains authored geometry, not anatomical registration.

Independent triangle broad-phase and finite edge/triangle checks reproduce the old bilateral carotid crossings and find no intersecting surface candidates between any of the four estimated arterial surfaces and the corrected fused venous surface. This scope does not certify collision freedom against all original atlas vessels, organs, or all nonlocal self-contacts.

The earlier 752-element selection was incomplete and is superseded by the 828-element selection above. Original OBJ coordinates remain unchanged. A common display conversion assumes millimeter source units; the assumption is disclosed because OBJ does not encode units.

The separate authored schematic remains editable. Its former continuous inferior-cava–atrium–superior-cava tube has been removed: the cavae end at separate illustrative ostia, with a nonrendered chamber relation in the exported graph. Routing does not cross that relation. Other schematic positions remain unvalidated and must not be interpreted as an atlas fit.

Source: https://dbarchive.biosciencedbc.jp/en/bodyparts3d/desc.html

Current distributor license: https://dbarchive.biosciencedbc.jp/en/bodyparts3d/lic.html

Local source data remain ignored under `reference-data/`. Acquire explicitly with `scripts/acquire_atlas.py`; the viewer only reads local files. Original surfaces are shown read-only, with red arteries, blue systemic veins, light-blue portal veins and optional translucent heart context.

## Estimated neck connections

The original 4.0 selection contains neck-to-head gaps even when common/internal carotid, vertebral and internal jugular elements are included. The user explicitly authorized separately marked estimated connections. The viewer can add endpoint-derived carotid and vertebral display connectors; these are amber, can be hidden independently, and are exported with endpoint IDs and fitting metadata. Original source vertices remain unchanged.

These connectors are not recovered source anatomy, a validated carotid bifurcation, or a Boolean lumen union. Missing original upper venous targets are now supplemented by the explicitly estimated venous network described above. Use Head & neck focus to inspect source gaps with the estimate toggle off and the reconstructed display with it on.
# Selected atlas vessel modification

The modification panel offers side and cerebral-segment filters. Source sphenoidal MCA parts map to M1, insular MCA parts to M2, and precommunicating PCA parts to P1. These are source-name mappings, not independently validated annotations. M3, A1–A3 and P2–P3 show explicitly unsegmented candidate parts pending anatomical boundary annotation. Selecting one of these candidates still edits the whole atlas part, not an isolated segment. No equal-length segmentation is performed. M1/M2/P1 search aliases and left/right filters are supported.

Voxel-derived centerlines are resampled by arc length and smoothed with an anchored Gaussian filter. Junction/end positions stay fixed; displacement is bounded by 1.5 extraction voxels and 35% of the estimated local radius. Original extraction caches and atlas surfaces remain unchanged. Radii are interpolated original estimates; surface containment of the smoothed curve is not certified. The displayed graph and modification baseline share the smoothed paths.

The primary workspace now opens directly in Atlas. Vessel search, the selected vessel's relationship graph, and modification controls share one panel. Separate legacy schematic navigation is removed from the visible interface. Relationship edges represent source-derived proximity candidates, not verified parent/child anatomy or flow direction; selecting a neighboring node changes the active vessel and 3D focus. Detailed extraction and provenance information is available in collapsed sections.

The Atlas panel provides radius multiplier (0.5–2), tortuosity adjustment (-1–1), and torsion adjustment (-180–180 degrees). Select a structure with a centerline, adjust the controls, then Apply. Restore selected original removes that vessel's override. Each application starts from the source geometry, so edits do not accumulate numerical drift. The current workspace export includes parameter overrides and modified surfaces; source atlas files remain unchanged.

Radius changes taper toward fixed endpoint/junction collars, so the requested multiplier is not a uniform scale at every cross-section. Tortuosity changes transverse deviation from each edge's endpoint chord; positive adjustment also adds a bend. Torsion twists this deviation around that chord. A straight edge has no deviation to twist until bent; closed edges and short edges protected by collars may retain their shape. This is a shape parameter, not a prescribed differential-geometric torsion measurement.

The original surface topology is retained and displaced using a blended centerline field. Graph edges and proximity candidates update with the display. This is approximate deformation: surface containment of the centerline, inter-part junction continuity, self-intersections, and collisions with other vessels are not guaranteed. It is not anatomical or clinical validation. Estimated vessels retain their source labels.

