# Validation — 2026-10-14

Scope: synthetic arterial toolbox and venous viewer integration, current local working copy. No patient anatomy, CFD, FEM or catheter-contact acceptance is claimed.

## Venous integration — 2026-10-14

### Arterial arch ostial correction

User subsequently rejected the still-sharp arterial tube interfaces, especially upward arch branches. The complete aortic trunk is now one implicit envelope before localized branch blending, including the brachiocephalic branch junction. A continuous, non-overshooting PCHIP radius profile replaces repeated independent trunk tapers.

- PASS: 95 model/editing/venous/backend tests plus 12 surface tests (107 total).
- PASS: controlled arterial ostium normal-jump 95th percentile 18.37 degrees versus 27.99 with a hard union; maximum 21.06 versus 40.91. The opposite trunk radius remains 4 mm within 0.18 mm in this synthetic fixture. These numbers describe the fixture, not a clinical vessel measurement.
- PASS: adding a short 2 mm trunk segment changes the test surface by less than 0.005 mm; monotone radius profiles remain continuous without overshoot.
- PASS: minimum/default/maximum arterial surface regression retains closed connected surfaces and thin branches; venous surface regressions remain passing.
- Follow-up visual inspection found a remaining oversized brachiocephalic outlet. Its parent radius now smoothly approaches the root-sum-square of actual outgoing daughter radii (7 to 5.315 mm by default), with the arch inlet untouched. Seven targeted arterial junction tests PASS after this correction, including extra left-carotid branching and local-radius overrides. The entire 107-test set was not repeated after this localized correction.
- Live final arch close-up inspected with prior parameters restored; branch roots and brachiocephalic outlet are visibly rounded compared with the saved before image. No browser console errors. Arterial-only arch focus remains open for user inspection; visual user acceptance is not inferred from automated checks.

### Junction smoothness correction

The user rejected the visible tube interfaces after integration. Closed/manifold surfaces alone did not establish smoothness. Venous rendering now tapers geometrically continuing branches to a shared radius, treats Y confluences symmetrically, and uses caliber-scaled local smooth unions once per vessel rather than once per sampled capsule. IVC/SVC share a continuous spline across the abstract atrial node; drainage orientation is retained.

- PASS: 43 arterial regression tests, 56 venous/backend/control tests and 5 new venous surface tests (104 total).
- PASS: mismatched trunk junction meets at the common radius, distal narrow branch keeps its radius, equal-radius fillet differs from a hard union, and fixed-geometry 16/128-point sampling differs by less than 0.005 mm (relative volume difference below 1e-5).
- PASS: default systemic mesh 766,211 vertices / 1,532,438 faces; portal 96,095 vertices / 192,186 faces. Each has one component and zero boundary/nonmanifold edges or orphan vertices. Terminal surface-distance/radius ratios are 0.949–0.995 and 0.972–0.995 respectively.
- PASS: caval tangent regression at tortuosity 0, 0.3 and 1; the prior approximately 27-degree centerline kink was removed.
- PASS: live systemic and portal surfaces inspected after restarting the existing 8093/8094 service; previous shape/variation parameters restored. Before/after screenshots retained outside the source repository. Systemic-only view remains selected for junction inspection.
- These are synthetic display-surface checks, not anatomical or flow validation.

- PASS: full suite 84 tests (45.47 seconds), followed by 32 backend/control tests after adding generation-conflict protection (12 new cases). Isolated venous suite accounts for 21 of the full-suite tests.
- PASS: JavaScript syntax and isolated wheel/source distribution build. A no-isolation build lacked local setuptools; the normal isolated build succeeded.
- PASS: default systemic mesh 767,785 vertices / 1,535,586 faces and portal mesh 97,284 vertices / 194,564 faces; each one component, zero boundary and nonmanifold edges. These checks cover the defaults, not every combined edit.
- PASS: live existing 8093/8094 viewer renders three independent surfaces; checkbox visibility changes preserve generation and selected graph layer.
- PASS: live IMV drainage changed from splenic to superior mesenteric with matching graph endpoint `ven_smv_junction` and visible 3D attachment change. Left transverse dominance applied in the same generation.
- PASS: direct graph selection of IMV and radius multiplier 1.05 yielded radius 2.625 mm in the generated/exported model. Existing arterial left-PCom absence was preserved.
- PASS: cerebral systemic graph and blue 3D surface inspected with arterial overlay; no browser console errors in the inspected final view.
- PASS: combined live JSON export reproduced both arterial and venous models exactly, retains non-rendered hepatic exchange metadata; a stale generation request returned HTTP 409 without replacing current state.
- NOT RUN: combined arterial-venous spatial registration, collision validation, clinical anatomy and hemodynamics.

The venous extension is now included in the local viewer acceptance above. Historical arterial-only results below retain their original scope. Changes remain local, without staging, commits or pushes.

## Research-guided reference pipeline — 2026-10-14

- PASS: 143 automated tests; isolated source distribution and wheel build. After fixing Windows copyright decoding to explicit UTF-8, six reference/workspace tests and the distribution build passed again, and the real local source loaded successfully.
- PASS: existing 8093/8094 browser displays original VMR 0011_H_AO_H surface, five independent modeling paths, source digest/license, inferred units, length/radius measurements and UNKNOWN classification status.
- PASS: reference-to-schematic switch preserves left-PCom absence, superior-mesenteric IMV drainage, left transverse dominance and authored parameters. Reference controls are read-only.
- PASS: raw reference data remains ignored and absent from source distribution/wheel.
- NOT RUN: anatomical axes/landmark validation, whole-body atlas registration, source-based cerebral segmentation, clinical acceptance.

## Cross-circuit overlap correction — 2026-10-14

- Reauthored local caval/brachiocephalic, renal, azygos, cavernous and portal routes to address real inter-circuit penetrations. This is a schematic correction, not atlas registration. Whole circuits were not translated apart.
- PASS: 143 existing regressions, five new exact capsule-clearance tests, and 29 focused clearance/venous topology/tangent checks. Default and current user settings have minimum capsule clearance 3.121 mm.
- PASS: `scripts/check_circuit_surfaces.py` validates the actual user-configuration display meshes using a conservative boundary-distance lower bound (nearest vertex distance minus both meshes' maximum triangle diameters). Artery/systemic >=1.827 mm, artery/portal >=5.049 mm, systemic/portal >=17.562 mm. This establishes surface-boundary separation for this configuration; not anatomical validity or all parameter combinations.
- Runtime screening recomputes on shape changes and exports the result. It uses centerline capsules, excludes mesher fillets, and reports potential overlaps rather than certifying surface separation. Opaque surfaces prevent misleading transparent overdraw.
- NOT RUN: atlas-based relative placement, organ clearance, exhaustive combined edits and clinical acceptance.

## Shared-coordinate anatomy correction — 2026-10-14

- PASS: 153 regression tests after removal of the false caval tube; seven atlas-loader/workspace tests subsequently passed, including required structures in the acquired source.
- PASS: official BodyParts3D source contains 752 selected elements: 467 arterial, 222 systemic venous, 37 portal and 26 heart-context parts. Explicit central-vessel concepts include aortic segments, SVC, IVC and both brachiocephalic veins; generic artery/vein concept lists alone omit central trunks.
- Original coordinates and part hashes are retained. Default source becomes the atlas when acquired; synthetic geometry is not overlaid. The atlas part list does not infer lumen topology.
- PASS: live 8093/8094 atlas rendering, source switch, original part list and heart-context hide/show verified. Prior schematic left-PCom/IMV settings retained. Final atlas/control tests (15) and package build passed after integration.
- PASS: synthetic cavae now terminate separately. Physiological association through the unmodeled right atrium is metadata, not a vessel or traversable vessel route. Default systemic surface has two closed components.
- UNKNOWN: absolute source-unit calibration (OBJ contains no unit declaration), patient-specific validity and clinical acceptance. Source decimation is 99%; no promise of fine-vessel fidelity or collision-free atlas surfaces.

## Neck source-gap reconstruction — 2026-10-14

- All 2,234 source archive elements were checked; all 14 vascular elements intersecting the audited neck interval were already included. CCA/ICA source nearest-vertex gaps are 63.39 and 62.53 original coordinate units. Source-unit scale remains qualified.
- User explicitly authorized marked estimates. Four additional arterial display parts reconstruct bilateral carotid and vertebral gaps from terminal section positions, area-equivalent radii and local axes with Hermite curves. Source arrays remain unchanged.
- PASS: connector endpoint/tangent/radius/source-preservation regressions and atlas workspace visibility/export checks. Estimated connections remain separate from source geometry and use independent visibility and amber coloring.
- UNRESOLVED: bilateral jugular-to-intracranial venous continuity; no identified upper sinus target in this source. 4.3 metadata identifies additional cervical components but their geometry was not retrieved/validated; no unverified version mixing.
- These are display repairs, not a fused lumen or clinical anatomical validation.

## Automated checks

- PASS: 51 tests across `test_model.py`, `test_surface.py`, `test_editable_graph.py`, and `test_app_controls.py` (43.80 seconds).
- PASS: subsequent UI-only refinement checked by the 8 request/control tests and JavaScript syntax validation.
- PASS: wheel and source distribution build. A concurrently authored, independent venous extension may be present locally; it is not part of this arterial UI acceptance.
- Tested surfaces at the selected minimum/default/maximum settings have one connected component, no boundary or nonmanifold edges, and no orphan vertices. This does not establish those properties for every possible combined edit or clinical suitability.
- Synthetic topology baseline: 53 nodes, 56 segments. Supported arch variants, communicator absence and parameter export/reproduction have regression coverage.
- Main aortic and femoral/iliac chains preserve shared spline tangents. Sampled tangent jumps were below one degree at tested tortuosity values.

## Live browser checks

- PASS: left graph shows bilateral A1–A3, M1–M3, P1–P3, ACom and PCom. Direct click on Left MCA M2 selects its editing controls.
- PASS: abdominal filter includes celiac/splenic/hepatic/gastric/SMA/renal/IMA branches. Applying a splenic-only radius multiplier of 2 updates the model to a new generation.
- PASS: ACom absence, left-carotid-from-brachiocephalic variation and Type III illustration apply together. Both graph and viewer report 55 vessels and the same generation; the rendered arch changes. Requested depth 2.5 and measured centerline surrogate 2.41 remain distinct.
- PASS: rebuild state disables conflicting controls and covers the previous 3D model.
- PASS: rounded arch and femoral region inspected in close-up; cerebral focus and graph are visible in the final local view.
- PASS: no browser console errors in the final inspected view.

The live workspace is shared among local tabs. It is served on loopback port 8093, with the embedded 3D viewer on 8094. It is not remotely deployed.

## Delivery state

### Atlas centerlines and candidate graph — 2026-10-14

- PASS: 804/805 original vascular meshes yield voxel medial paths. Posterior cecal artery FJ3553 is UNRESOLVED because its welded source surface is not watertight; no substitute path is fabricated.
- Five existing authored estimate parts are included separately. Initial graph: 4,939 nodes, 1,694 within-part paths and 2,347 unverified proximity links. Candidate links are not confirmed vascular connections.
- PASS: 26 focused atlas/centerline/workspace/control tests, covering a curved tube, a Y branch, explicit open-surface failure, circulation separation, visibility and export. All 1,694 generated paths pass endpoint/radius/finite-coordinate checks. Isolated wheel build PASS.
- Source surfaces are unchanged. This is a voxel-resolution medial approximation, not a validated anatomical centerline, full circulation graph, automatic variation editor or clinical acceptance.
- Quality limits: 163 source parts are flagged COARSE by the pitch/radius criterion; 59 have multiple voxel-skeleton components. These remain visible in per-part export metadata rather than being silently fused or counted as verified continuous vessels.

### Detailed atlas and estimated cranial veins — 2026-10-14

Subsequent user-reported estimated carotid/IJV penetration: reproduced with 480 right and 477 left noncoplanar intersecting triangle pairs. Bounded anterolateral IJV bows correct it without changing source anchors or radii. Independent surface tests PASS (2): zero triangle AABB candidates between four estimated arteries and the corrected venous surface; all 828 source mesh hashes unchanged; anchor/junction continuity preserved. Existing neck/workspace/control tests PASS (16), JavaScript syntax and isolated wheel build PASS. These checks do not certify the entire original atlas collision-free.

- PASS: 24 focused tests across atlas selection, estimated neck/venous geometry, workspace selection and application controls; JavaScript syntax and isolated wheel build.
- PASS: official-source selection now renders 828 unique elements (805 vascular, 23 context), including previously omitted thoracic aorta, cerebral arterial subdivisions and portal trunks.
- PASS: estimated cerebral venous network has shared endpoints/tangents and one closed synthetic surface in regression fixtures; actual atlas generation succeeds. This is not a Boolean union with source IJV meshes or a full-network lumen check.
- PASS: browser Head & neck shows cyan estimated jugular/sinus network; estimate toggle removes/restores it. Femoral-vein search returns eight named structures; selecting left femoral vein highlights and focuses the original part.
- NOT RUN: whole-body lumen continuity and anatomical landmark validation. Source head venous sinuses remain absent; all upper venous positions/radii are authored estimates. Detailed atlas shape/topology editing remains unavailable; existing schematic editor is preserved separately.

The user explicitly chose to retain local changes without committing or pushing. The private `gj21kr/vv-toolbox` repository exists, but this implementation has not been uploaded. The originally independent venous extension is preserved and its newly authorized integration is covered by the venous section above.
# Atlas graph live browser verification (2026-10-14)

- PASS: selecting an atlas graph vessel focuses and highlights its 3D centerline.
- PASS: centerline visibility toggles restore opaque original surfaces when disabled.
- PASS: selection followed by Update view preserves all centerline colors. Initial and updated line colors use the same per-point array shape to avoid stale renderer color buffers.
- PASS: 26 focused tests after the rendering fix; browser console contains no errors.
- Screenshot: `vv-atlas-centerline-graph.png` in the local task visualization directory.

# Atlas vessel modification verification (2026-10-15)

- PASS: 33 focused tests covering deformation, workspace integration, control validation and centerline extraction.
- PASS: source arrays remain immutable, repeated apply uses an absolute source baseline, reset restores original edges, export includes overrides and derived surfaces.
- PASS: browser selected FJ1682, applied radius 1.10, tortuosity 0.05, torsion 5 degrees. Maximum centerline displacement 1.503243 source units, peak radius ratio 1.0999993; edge endpoints fixed and all other edges unchanged.
- PASS: browser Restore selected original cleared overrides and returned every edge exactly to the pre-edit data. Stale generation edit returned HTTP 409.
- NOT RUN: full anatomical continuity, surface self-intersection and inter-vessel collision validation after deformation.
- Test modification was reset; source assets and prior schematic parameters were preserved. No commit or push.

# Atlas-only panel verification (2026-10-15)

- PASS: 29 focused tests; JavaScript syntax check; Atlas is the default loaded workspace.
- PASS: browser shows one Atlas workspace with search, relationship nodes, and modification cards. Legacy editor navigation is absent from the visible/accessibility UI.
- PASS: relationship-node click FJ1673 -> FJ1716 -> FJ1673 updates selection, 3D focus, neighbor graph and modification controls.
- PASS: existing FJ1682 radius override 1.35 was restored after server restart; selected FJ1673 restored. Browser console has no errors.
- Relationship links remain proximity candidates, not confirmed anatomical parent/child or blood-flow connections. Nearest four neighbors are displayed when there are more, with an explicit count.

