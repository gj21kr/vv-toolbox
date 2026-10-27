# Disease geometry and preset specification

Date: 2026-10-20. Requirements: VV-REQ-007, 008, 009, 011, 013. Status: specification; generator acceptance is NOT RUN here.

## 1. Evidence and execution modes

Every target artery from femoral to bilateral ACA/MCA supports the same **synthetic geometry interface**, with region-specific measurement and eligibility rules below. This is not evidence that every lesion type, parameter combination or frequency is clinically representative at every site.

- `manual_synthetic`: user supplies explicit geometry parameters; save them as simulator design choices, not literature-derived values. No population sampling.
- `literature_fixed`: a named publication supports each fixed parameter. Unspecified required parameters must be supplied and marked `operator_defined`; such a result is `literature_conditioned_synthetic`, not a reproduction of that publication.
- `literature_distribution`: disabled until the regional joint distribution, cohort, measurement protocol and sampling implementation are independently specified. A mean and SD or a parameter sweep is insufficient.

Source geometry remains immutable. Lesions operate only on a synthetic derivative with base ID, source hashes, generator version and operation history. Lack of a patient ground truth does not prevent manual synthetic generation or geometry tests.

## 2. Stenosis measurements and controls

Save `measurement_method`, reference edge/station/plane, `reference_diameter_mm`, minimum residual diameter, length, shape and affected branches. Never store an unqualified `percent_stenosis`.

| Method | Definition and eligible use | Evidence/limitation |
|---|---|---|
| `NASCET_diameter` | `100 * (1 - D_min / D_distal_normal_ICA)`; reference beyond the bulb in normal cervical ICA | Original NASCET measurement study [S1]. Do not substitute CCA or reconstructed bulb diameter. A diseased/collapsed or unavailable distal reference makes this measure UNKNOWN. |
| `WASID_diameter` | `100 * (1 - D_min / D_reference)`; normal proximal artery, then distal artery, then feeding artery according to protocol | Original study covered major intracranial carotid, MCA, vertebral and basilar arteries [S2]. Intracranial ICA needs its protocol-specific reference selection; require an explicit reviewed reference rather than a generic nearest point. ACA and distal M2/M3 use must be labeled a geometric extension, not original validation. |
| `local_baseline_diameter` | `100 * (1 - D_min / D_baseline_at_lesion)` in the unmodified synthetic baseline | Engineering definition for femoral/iliac/aorta/CCA and other unsupported regional measurement protocols. Do not call it NASCET/WASID. |
| `local_baseline_area` | `100 * (1 - A_min / A_baseline_at_lesion)` | Use actual cross-sectional lumen areas. For concentric circular sections only, area fraction lost = `1 - (1 - diameter_fraction_lost)^2`. |

Radius scaling against a **local** baseline is not automatically the NASCET or WASID percentage: the reference may have a different diameter. When a reference-based severity is requested, solve for `D_min = D_reference * (1 - severity/100)` and verify the resulting surface section. Reject a requested narrowing that would instead enlarge the local baseline.

Proposed smooth engineering kernel (not a tissue model): on normalized longitudinal coordinate `u = 2*(s-s_center)/length`, `w=(1-u*u)^3` for `abs(u)<1`, otherwise zero. Circular concentric narrowing uses `r(s)=r0(s)*(1-alpha*w)`. This has zero first and second derivative at its support boundaries. `0 <= alpha < 1`, positive finite length and positive resolved residual lumen are mathematical constraints, **not clinical ranges**. An eccentric lesion requires separate cross-section axes/offset and measured area/minimum width; moving the centerline alone is not eccentric plaque.

## 3. Aneurysm representation

Keep `saccular` and `fusiform` separate. A saccular lesion needs an attachment curve/neck plane, sac axis, height perpendicular to that plane, maximum width, depth, orientation and blending extent. A fusiform lesion needs axial support, baseline-relative diameter profile and affected branch ostia; it has no cerebral-style sac neck.

Use explicit metric names: `height_perpendicular_mm`, `neck_average_diameter_mm`, `neck_max_width_mm`, `dome_max_width_mm`, `aspect_ratio_height_over_neck`, and the exact parent-vessel sampling convention for any `size_ratio`. Dhar et al. define aspect ratio using maximum perpendicular height and average neck diameter [S3]. Thus a spherical model's quoted “size” cannot silently become height or width. Do not transfer rupture cutoffs to generation limits.

Saccular generation must form one open lumen through the neck and remove any internal wall at the union. A sphere visually intersecting a tube is not sufficient. Fusiform expansion must preserve continuous upstream/downstream lumen and all declared ostia. Numerical mesh/voxel resolution and minimum resolvable neck/lumen are separate, explicitly configured acceptance limits.

## 4. Regional support matrix

| Region | Stenosis mode | Aneurysm modes | Fixed empirical support currently available |
|---|---|---|---|
| CFA/SFA/profunda | local baseline; branch-aware ostial option | fusiform/saccular manual synthetic | CFA concentric area-stenosis phantom condition [S4]; no regional aneurysm preset established here |
| Common/external iliac | local baseline | fusiform/saccular manual synthetic | No complete regional lesion preset established here |
| Abdominal aorta | local baseline | fusiform; saccular manual synthetic | Idealized AAA lumen dimensions [S6]; incomplete axial geometry |
| Thoracic aorta/arch and supra-aortic origins | local baseline | fusiform/saccular manual synthetic | No validated regional dimension ranges established here |
| CCA and carotid bifurcation | local baseline; NASCET only for the ICA lesion with valid distal reference | fusiform/saccular manual synthetic | Measurement method [S1], not a population shape distribution |
| Cervical ICA | NASCET with explicit eligible reference | fusiform/saccular manual synthetic | Measurement method [S1] |
| Intracranial ICA/MCA | WASID where eligible; otherwise explicit local baseline | saccular, bifurcation, fusiform manual synthetic | Idealized MCA bifurcation example [S5]; morphology definitions [S3] |
| ACA A1–A3 and distal MCA M2–M3 | local baseline; protocol extension must be labeled | saccular, bifurcation, fusiform manual synthetic | No segment-specific population ranges or complete fixed shapes established here |

The matrix is an implementation coverage contract. Unsupported **literature presets** do not disable the region's explicitly synthetic manual controls. Automatic generation must not replace missing literature values with hidden defaults.

## 5. Fixed literature conditions

These are deterministic conditions, not prevalence estimates or continuous allowed intervals. Source parameter names and units are preserved in the JSON companion.

| ID | Supported fixed condition | Missing information / transfer rule |
|---|---|---|
| `femoral_concentric_area75` | CFA 8.9 mm, SFA 6.2 mm, DFA 6.1 mm; CFA concentric **75% area** stenosis [S4] | Circular throat diameter is 4.45 mm (derived). Lesion length/profile and branch placement must be transcribed from full methods/figure or explicitly operator-defined. Do not turn this into 75% diameter loss. |
| `mca_bifurcation_sphere42_neck40` | Idealized MCA bifurcation; spherical size 4.2 mm, neck width 4 mm; 30-degree dome orientation reported [S5] | Reproduce the publication's angle axes and attachment construction before claiming exact reproduction. Daughter diameter ratios 1, 1.3, 2 are study settings, not a uniform distribution. Absolute daughter dimensions and all reconstruction details must be supplied/verified. |
| `aaa_lumen50_neck24_iliac12` | Idealized AAA: lumen sac diameter 50 mm, proximal neck 24 mm, iliac diameters 12 mm; 60-degree bifurcation [S6] | Axial dimensions/profile are not established by this extraction. These are lumen dimensions; do not treat outer-wall diameter as lumen or silently add thrombus. |

All three conditions have `complete_geometry_preset=false` until their missing geometry is resolved. A partial literature condition plus visible operator-defined parameters is executable in manual mode; it must retain both provenances.

## 6. Branches, multiple lesions and acceptance

These are project engineering requirements, not claims drawn from the studies:

1. Identify affected edge intervals and every incident junction before deformation. For an ostial lesion, distinguish main-vessel lumen, selected daughter ostium and unaffected daughters.
2. Bifurcation aneurysm attachment may span several incident surfaces; retain each branch ID and patent path to every pre-existing outlet. A sac is a lesion object, not a new anatomical daughter artery.
3. Compare baseline and output graph incidence; unintended branch loss, extra connections and self-intersection are FAIL. Meshing union must not erase branch labels.
4. Define lesion support as the **entire modified volume**, including blend and transition zones. Reject overlap between these supports, even when centerline intervals lie on different branches. Additionally enforce an explicit configured minimum 3D distance; graph-path interval spacing alone is insufficient.
5. No literature-derived universal minimum lesion spacing is established. `min_spacing_mm` is a recorded engineering setting. Set it before generation; never shrink it to accept a failed result.
6. Record measured versus requested severity, neck/height/width, preserved outlet count and connectivity, surface validity, label assignment and mask sampling adequacy. Tolerances belong to the versioned numerical configuration, not a clinical reference range.
7. Reference sections must lie outside all lesion supports and remain valid after edits. A later lesion invalidating a reference requires remeasurement or UNKNOWN, not reuse of stale severity.

## 7. Minimal operation record

`lesion_id`, `model_kind=synthetic`, `base_model_id`, `region`, `type`, `edge_intervals`, `junction_ids`, `support_definition`, `measurement_method`, `reference_section`, `requested_parameters`, `measured_parameters`, `parameter_provenance` (per key), `preset_id/version`, `source_ids`, `generator_version`, `seed`, `min_spacing_mm`, `quality_configuration`, `quality_results`.

Numeric constraints must reject NaN/infinity, negative lengths, zero neck/lumen and inconsistent units. An operation must either succeed atomically or return a reason while retaining the previous case. Export vascular segment and lesion-instance labels as independent arrays so a lesion does not erase anatomy.

## Sources

- **S1 (1994, dated):** Eliasziw et al., *Further comments on the measurement of carotid stenosis from angiograms*. Original measurement comparison, 112 angiograms. [PubMed](https://pubmed.ncbi.nlm.nih.gov/7974588/), [DOI](https://doi.org/10.1161/01.STR.25.12.2445).
- **S2 (2000, dated):** Samuels et al., *A standardized method for measuring intracranial arterial stenosis*. Original measurement/reproducibility study. [Full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC7976653/), [PubMed](https://pubmed.ncbi.nlm.nih.gov/10782772/).
- **S3 (2008, dated):** Dhar et al., *Morphology parameters for intracranial aneurysm rupture risk assessment*. Original morphometric study. [PubMed](https://pubmed.ncbi.nlm.nih.gov/18797347/), [DOI](https://doi.org/10.1227/01.NEU.0000316847.64140.81). Definitions only; rupture prediction is outside this specification.
- **S4 (2024):** *Validation of ultrasound velocimetry and computational fluid dynamics for flow assessment in femoral artery stenotic disease*. Original phantom/CFD study. [Article](https://pmc.ncbi.nlm.nih.gov/articles/PMC11097197/).
- **S5 (2013, dated):** *Effect of Bifurcation Angle Configuration and Ratio of Daughter Diameters on Hemodynamics of Bifurcation Aneurysms*. Original idealized-model study. [Article](https://pmc.ncbi.nlm.nih.gov/articles/PMC7965116/).
- **S6 (2014, dated):** Cloonan et al., *3D-Printed Tissue-Mimicking Phantoms for Medical Imaging and Computational Validation Applications*. Original phantom study. [Article](https://pmc.ncbi.nlm.nih.gov/articles/PMC4981152/), [DOI](https://doi.org/10.1089/3dp.2013.0010).

Retrieval limitation: several PMC direct opens returned a browser challenge. Indexed original-article text and PubMed were readable; exact full CAD reconstruction, code availability and supplementary asset licensing were not verified. No article's mesh/code is assumed reusable solely because its text is accessible. The extracted fixed conditions above are deliberately incomplete rather than silently filled with guessed parameters.
