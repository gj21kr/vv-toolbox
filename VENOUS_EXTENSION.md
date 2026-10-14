# Venous extension

Independent module added in the existing worktree. No changes to the running viewer, server ports, arterial generator, shared UI, package initializer or strategy registry.

## API

```python
from vv_toolbox.veins import generate_veins

veins = generate_veins(
    vessel_parameters={"ven_left_femoral": {"radius_scale": 1.2, "tortuosity": 0.4}},
    imv_drainage="splenic",  # also superior_mesenteric or confluence
    transverse_dominance="balanced",  # also left or right
)
for layer, graph in veins.graphs.items():
    graph.validate()
    # Pass each graph separately to the existing graph/mesh renderer.
payload = veins.to_json()
restored = generate_veins(**veins.generation_kwargs())
```

`veins.systemic` and `veins.portal` provide the existing `VesselGraph` interface. All node and vessel IDs begin with `ven_`, avoiding arterial ID collisions. Local radius overrides are absolute baseline multipliers, matching arterial controls. Graph nodes carry exact shared endpoints; smooth chains and zero-endpoint-derivative perturbations avoid introducing a tangent jump at intermediate samples.

## Coverage

- Bilateral femoral, profunda femoris, external/internal/common iliac veins; IVC and SVC with an abstract right-atrial junction.
- Bilateral renal, adrenal, gonadal and left/middle/right hepatic veins; azygos and hemiazygos.
- Axillary/subclavian/brachiocephalic and internal jugular veins.
- Superior/inferior sagittal, straight, transverse, sigmoid, occipital, petrosal and intercavernous sinus connections; cavernous junctions; schematic cortical, internal cerebral, basal and great cerebral veins.
- Portal vein with right/left liver branches, splenic, superior/inferior mesenteric and left gastric veins.

Each listed cerebral vein represents a schematic drainage channel, not a complete cortical tree. Cavernous nodes are simplified junctions, not anatomical cavernous sinus volumes. Pulmonary/coronary circulation, detailed limb tributaries, hepatic sinusoids and the heart chambers are not modeled.

## Topology and variations

Portal blood enters liver microcirculation before hepatic venous outflow. Accordingly, portal and systemic graphs remain separate. Export includes non-rendered `unmodeled_exchange` metadata; do not draw a direct portal-to-hepatic-vein tube or weld the two meshes together. Arteries must likewise remain a separate layer.

IMV drainage changes its actual endpoint and geometry between splenic, superior mesenteric and confluence locations. Transverse dominance is an illustrative diameter asymmetry, not an absent-sinus or validated pathological model. Start/end orientation generally follows drainage; intercavernous and anastomotic connections must not be interpreted as a flow solution. `VesselGraph.route()` remains undirected.

## Integration boundary

The main viewer integrates this module through `app.py` and `web_ui.py` on the existing 8093/8094 server. It provides independent arterial/systemic/portal visibility, graph layer selection, per-vein overrides, IMV drainage and transverse dominance controls. Surfaces are extracted independently per circuit. Visibility changes reuse the existing meshes. Anatomy submissions carry an expected generation to reject stale edits from other tabs.

The bundled JSON is the authoritative full venous configuration. Use `VenousNetwork.generation_kwargs()` to reproduce both circuits, rather than the arterial-specific method on individual graphs.

All coordinates and radii are authored synthetic values. Spatial registration against the arterial model, artery-vein collision checks, whole-surface quality, valves, clinical anatomy and hemodynamics are not validated.

## References

- [NCBI: dural venous sinuses](https://www.ncbi.nlm.nih.gov/books/NBK482257/) — sinus and jugular connectivity.
- [NCBI: brain veins](https://www.ncbi.nlm.nih.gov/books/NBK546605/) — deep and superficial drainage.
- [NCBI: hepatic portal system](https://www.ncbi.nlm.nih.gov/books/NBK554589/) — portal versus systemic circulation.
- [Anatomical study of the splenic/mesenteric venous junction](https://journals.viamedica.pl/folia_morphologica/article/download/FM.2013.0010/24409) — portal tributary anatomy.

These sources inform topology, not the numerical dimensions. No source images, patient data or anatomical datasets were copied.

## Verification

2026-10-14: isolated extension suite **21 PASS**. Default systemic network has 61 nodes/64 segments; portal network has 10 nodes/9 segments. Integration test results and live browser evidence are recorded in `VALIDATION.md`. Default meshes each have one connected component and zero boundary/nonmanifold edges. Combined arterial-venous spatial validation remains **NOT RUN**.

Run only the isolated extension checks during concurrent development:

```powershell
.venv/Scripts/python -m pytest tests/test_veins.py -q
```
