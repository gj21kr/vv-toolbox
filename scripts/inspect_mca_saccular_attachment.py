"""Separate baseline parent and sac fields on the unchanged failed neck plane."""
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import label
from vv_toolbox.case_io import load_case
from vv_toolbox.saccular_surface import _parent_field, _sac_field, build_saccular_candidate

ROOT=Path(__file__).resolve().parents[1]


def main():
    source=ROOT/'exports/atlas-case-inspection/all-arterial.snapshot.json'
    before=source.read_bytes()
    case,revision=load_case(source)
    prior=json.loads((ROOT/'docs/evidence/mca-saccular-grid-recheck-3000000.json').read_text())
    if revision!=prior['case_revision']:
        raise ValueError('source revision mismatch')
    spec=prior['specification']
    edge=next(e for e in case['edges'] if e['id']==spec['parameters']['edge_id'])
    neck=spec['neck']
    points,radii=np.asarray(edge['centerline_mm']),np.asarray(edge['radii_mm'])
    center=np.asarray(neck['center_mm'])
    basis=np.column_stack([neck[k] for k in ('width_axis','depth_axis','normal')])
    # Fixed diagnostic window; not a replacement neck measurement or tolerance.
    coords=np.arange(-12.,12.0001,.05)
    x,y=np.meshgrid(coords,coords)
    world=np.column_stack([x.ravel(),y.ravel(),np.zeros(x.size)])@basis.T+center
    parent=_parent_field(world,points,radii).reshape(x.shape)
    sac=_sac_field(world,spec).reshape(x.shape)
    union=np.minimum(parent,sac)  # local blend is exactly zero at this plane
    occupied=union<0
    components,n=label(occupied)
    middle=len(coords)//2
    chosen=components[middle,middle]
    selected=components==chosen if chosen else np.zeros_like(occupied)
    spans=[float(np.ptp(x[selected])),float(np.ptp(y[selected]))] if selected.any() else None
    rim=np.asarray(neck['curve_mm'])
    rim_field=_parent_field(rim,points,radii)
    # A negative baseline value at a declared boundary point means that point
    # is inside the union, so it cannot remain its external contour.
    intrusion=rim_field < -1e-6
    try:
        build_saccular_candidate(case,spec,spacing_mm=.15,max_grid_voxels=10)
    except ValueError as error:
        preflight_reason=str(error)
        if 'neck rim intersects baseline parent' not in preflight_reason:
            raise
    else:
        raise RuntimeError('known invalid attachment was not rejected')
    out=ROOT/'exports/mca-saccular-attachment'
    out.mkdir(exist_ok=True)
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    for ax in axes:
        ax.contour(x,y,parent,levels=[0],colors=['#2869af'],linewidths=1.4)
        ax.contour(x,y,sac,levels=[0],colors=['#d1495b'],linewidths=1.6)
        ax.contour(x,y,union,levels=[0],colors=['#222222'],linestyles='dotted')
        ax.set_aspect('equal')
        ax.set(xlabel='Neck width axis (mm)',ylabel='Neck depth axis (mm)')
    axes[0].set(title='Same plane: parent blue, sac red, union dotted')
    axes[1].set(xlim=(-2,2),ylim=(-1.5,1.5),title='Declared neck and baseline parent intrusion')
    local=(rim-center)@basis
    axes[1].scatter(local[intrusion,0],local[intrusion,1],s=12,color='#f08c00')
    fig.suptitle('Atlas-derived profile diagnosis; not original anatomical lumen validation')
    fig.tight_layout()
    figure=out/'neck-plane.png'
    fig.savefig(figure,dpi=150)
    plt.close(fig)
    report=dict(case_revision=revision,edge_id=edge['id'],input_unchanged=source.read_bytes()==before,
        diagnostic_spacing_mm=.05,diagnostic_window_mm=[-12,12],
        declared_rim_samples=len(rim),rim_samples_inside_baseline_parent=int(intrusion.sum()),
        generator_version='saccular-sidewall-6',early_attachment_rejection='PASS',
        rejection_reason=preflight_reason,
        rim_parent_field_range_mm=[float(rim_field.min()),float(rim_field.max())],
        plane_union_component_count=int(n),neck_center_component_id=int(chosen),
        neck_center_component_span_mm=spans,
        diagnostic_component_clipped=bool(selected[0,:].any() or selected[-1,:].any()
                                          or selected[:,0].any() or selected[:,-1].any()),
        limitation='Sampled profile-field diagnosis, not source mesh ostium proof. Window and sample counts are not acceptance tolerances.',
        figure_sha256=hashlib.sha256(figure.read_bytes()).hexdigest(),
        original_requested_neck_mm=[2,1],anatomy='UNKNOWN',app_applied=False)
    if not report['input_unchanged']:
        raise ValueError('source changed')
    (ROOT/'docs/evidence/mca-saccular-attachment.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':
    main()
