# Anatomy scope and provenance

The editable whole-body mode uses authored synthetic geometry. Segment names identify schematic vascular territories, not a patient atlas or a complete cortical arterial tree. Cerebral subdivisions are explicitly marked estimated, not source-annotated anatomical landmarks.

A separate read-only VMR reference mode preserves the original surface and five independent modeling paths from case 0011_H_AO_H. It does not register the case into the synthetic whole body or invent path junctions. Units are inferred from source evidence; anatomical axes, branch angles and arch classification remain UNKNOWN. See [reference pipeline](REFERENCE_PIPELINE.md).

## Requested coverage

- Bilateral femoral and iliac access, abdominal/thoracic aorta and rounded aortic arch.
- Celiac trunk with splenic (SA), common hepatic and left gastric branches; superior mesenteric, bilateral renal and inferior mesenteric branches.
- Supra-aortic carotid/subclavian/vertebral and basilar routes.
- Bilateral ACA A1–A3, MCA M1–M3 and PCA P1–P3; ACom and bilateral PCom.

One schematic M2/M3 continuation per side is not the full superior/inferior MCA division tree. Similarly, distal ACA/PCA labels do not imply every cortical branch is represented.

## Connectivity requirements

ACom links left/right ACA at the A1-to-A2 transition. Each PCom links the ipsilateral ICA region to the PCA P1-to-P2 region. PCA P1 links the basilar tip to that junction. ACom and PCom are cross-connections, not disconnected decorative tubes. Removing a supported communicating artery changes both exported adjacency and the rendered surface.

Standard arch branching has distinct brachiocephalic, left common carotid and left subclavian origins. A shared brachiocephalic/left-carotid origin and a left carotid arising from the brachiocephalic trunk are different supported variants. A left vertebral origin directly from the arch is another distinct variant.

## Arch height versus branching pattern

The height-based Type I/II/III convention uses the vertical distance from the brachiocephalic origin to the arch summit relative to the left common carotid diameter: less than one, one to two, or more than two diameters. It must not be confused with classifications based on which arteries share an origin.

The controls in this synthetic toolbox are construction presets. Requested construction ratios, measured model ratios and clinical classifications must not be conflated. The renderer does not perform clinical CTA plane selection or lumen-based landmark measurement.

## References

- [Aortic arch morphometry in living humans](https://pmc.ncbi.nlm.nih.gov/articles/PMC3035863/): height classification and arch geometry.
- [Circle of Willis anatomical study](https://pmc.ncbi.nlm.nih.gov/articles/PMC2909942/): anterior and posterior communicating connectivity.
- [Circle of Willis anatomy and variants](https://pmc.ncbi.nlm.nih.gov/articles/PMC11122484/): segment connection diagram.
- [Celiac branching CTA study](https://pmc.ncbi.nlm.nih.gov/articles/PMC4606222/): celiac trifurcation and variants.

These references guide naming and topology. They do not validate the synthetic coordinates, radii, shape variation ranges or any clinical application. No patient images or source model assets are included.
