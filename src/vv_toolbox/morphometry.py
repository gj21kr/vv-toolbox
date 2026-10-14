"""Numerical 3D centerline measurements; no empirical normality/clinical thresholds.

Inputs must use a shared Cartesian frame and millimeters. Derivatives are estimated
with an unsmoothed cubic interpolant parameterized by cumulative polyline length.
Curvature/torsion formulas are parameter-invariant; noisy inputs remain noisy.
"""
import math
import numpy as np
from scipy.interpolate import CubicSpline


def _curve(points):
    points=np.asarray(points,dtype=float)
    if points.ndim!=2 or points.shape[1]!=3 or len(points)<2 or not np.isfinite(points).all():
        raise ValueError('Centerline must contain at least two finite 3D points')
    distances=np.linalg.norm(np.diff(points,axis=0),axis=1)
    if np.any(distances<=0):
        raise ValueError('Consecutive centerline points must be distinct')
    return points,np.r_[0,np.cumsum(distances)]


def _vector(vector,name):
    vector=np.asarray(vector,dtype=float)
    if vector.shape!=(3,) or not np.isfinite(vector).all():
        raise ValueError(name+' must be a finite 3D vector')
    return vector.copy()


def _summary(values,unit,reason):
    values=np.asarray(values,dtype=float)
    values=values[np.isfinite(values)]
    if not len(values):
        return dict(status='UNKNOWN',unit=unit,valid_count=0,reason=reason)
    return dict(status='PASS',unit=unit,valid_count=len(values),minimum=float(values.min()),
                maximum=float(values.max()),mean=float(values.mean()),median=float(np.median(values)),
                p95=float(np.quantile(values,.95)))


def centerline_metrics(points_mm,*,evaluation_points=256):
    """Measure sampled length and spline curvature/torsion in 3D.

    Summaries use equal parameter spacing, excluding the first/last spline interval
    for open curves. Undefined torsion on zero-curvature samples is not reported as0.
    """
    points,s=_curve(points_mm)
    if isinstance(evaluation_points,bool) or not isinstance(evaluation_points,int) or evaluation_points<8:
        raise ValueError('evaluation_points must be an integer >=8')
    result=dict(status='PASS',length_mm=float(s[-1]),endpoint_distance_mm=float(np.linalg.norm(points[-1]-points[0])),
                input_points=len(points),parameter='cumulative polyline arc length (mm)',
                estimator='unsmoothed cubic interpolation; parameter-invariant derivative formulas',
                anatomy_validation='NOT RUN')
    if len(points)<4:
        result.update(curvature=_summary([], '1/mm','At least four samples required for cubic derivatives'),
                      torsion=_summary([], '1/mm','At least four samples required for cubic derivatives'))
        return result
    scale=max(1.,float(np.max(np.abs(points))))
    roundoff=64*np.finfo(float).eps*scale
    closed=np.linalg.norm(points[-1]-points[0])<=roundoff
    if closed:
        points=points.copy()
        points[-1]=points[0]
    spline=CubicSpline(s,points,axis=0,bc_type='periodic' if closed else 'not-a-knot')
    q=np.linspace(0,s[-1],evaluation_points,endpoint=False) if closed else np.linspace(s[1],s[-2],evaluation_points)
    first,second,third=(spline(q,order) for order in (1,2,3))
    speed=np.linalg.norm(first,axis=1)
    cross=np.cross(first,second)
    cross_norm=np.linalg.norm(cross,axis=1)
    eps=np.finfo(float).eps
    speed_valid=speed>64*eps*max(1.,float(speed.max()))
    # This is floating-point degeneracy detection, not an anatomical cutoff.
    cross_floor=256*eps*np.maximum(1.,np.linalg.norm(first,axis=1)*np.linalg.norm(second,axis=1))
    curvature=np.full(len(q),np.nan)
    curvature[speed_valid]=cross_norm[speed_valid]/speed[speed_valid]**3
    curvature[speed_valid & (cross_norm<=cross_floor)]=0
    torsion=np.full(len(q),np.nan)
    valid=speed_valid & (cross_norm>cross_floor)
    torsion[valid]=np.einsum('ij,ij->i',cross[valid],third[valid])/cross_norm[valid]**2
    result.update(closed=bool(closed),evaluation_points=len(q),
                  evaluated_arc_length_interval_mm=[float(q[0]),float(q[-1])],
                  curvature=_summary(curvature,'1/mm','Zero speed prevents curvature measurement'),
                  torsion=_summary(torsion,'1/mm','Torsion undefined where curvature or speed is numerically zero'),
                  torsion_undefined_samples=int((~valid).sum()))
    return result


def branch_angle(parent_points_mm,daughter_points_mm,*,window_mm,parent_end='end',daughter_end='start',reference_direction=None):
    """Incoming-parent to outgoing-daughter deflection over a fixed arc window.

    Zero degrees denotes a straight continuation. Optional azimuth uses the given
    reference direction projected perpendicular to the incoming parent direction.
    The method is a windowed chord estimator, not a 2D screen angle.
    """
    parent,_=_curve(parent_points_mm)
    daughter,_=_curve(daughter_points_mm)
    if parent_end not in ('start','end') or daughter_end not in ('start','end'):
        raise ValueError('Endpoint must be start or end')
    if isinstance(window_mm,bool) or not isinstance(window_mm,(int,float)) or not math.isfinite(window_mm) or window_mm<=0:
        raise ValueError('window_mm must be finite and positive')
    if parent_end=='start': parent=parent[::-1]
    if daughter_end=='end': daughter=daughter[::-1]
    parent,ps=_curve(parent)
    daughter,ds=_curve(daughter)
    result=dict(status='UNKNOWN',window_mm=float(window_mm),angle_deg=None,azimuth_deg=None,
                method='3D incoming-parent/outgoing-daughter chords over fixed polyline arc-length windows',anatomy_validation='NOT RUN')
    tolerance=64*np.finfo(float).eps*max(1.,float(np.abs(parent).max()),float(np.abs(daughter).max()))
    if np.linalg.norm(parent[-1]-daughter[0])>tolerance:
        return {**result,'reason':'Parent and daughter do not share the specified junction'}
    if window_mm>ps[-1] or window_mm>ds[-1]:
        return {**result,'reason':'Requested measurement window exceeds available centerline length'}
    p=np.array([np.interp(ps[-1]-window_mm,ps,parent[:,axis]) for axis in range(3)])
    d=np.array([np.interp(window_mm,ds,daughter[:,axis]) for axis in range(3)])
    incoming,outgoing=parent[-1]-p,d-daughter[0]
    if min(np.linalg.norm(incoming),np.linalg.norm(outgoing))<=tolerance:
        return {**result,'reason':'Measurement window has a degenerate chord'}
    incoming/=np.linalg.norm(incoming)
    outgoing/=np.linalg.norm(outgoing)
    result.update(status='PASS',angle_deg=float(np.degrees(np.arccos(np.clip(np.dot(incoming,outgoing),-1,1)))))
    if reference_direction is None:
        result['azimuth_reason']='No circumferential reference direction supplied'
    else:
        reference=_vector(reference_direction,'reference_direction')
        normal=reference-np.dot(reference,incoming)*incoming
        transverse=outgoing-np.dot(outgoing,incoming)*incoming
        if min(np.linalg.norm(normal),np.linalg.norm(transverse))<=64*np.finfo(float).eps:
            result['azimuth_reason']='Reference or daughter has no resolvable transverse direction'
        else:
            normal/=np.linalg.norm(normal)
            result['azimuth_deg']=float(np.degrees(np.arctan2(np.dot(transverse,np.cross(incoming,normal)),np.dot(transverse,normal))))
    return result


def arch_type_for_ratio(ratio):
    """Named numerical ranges only; callers must state their landmark definition."""
    if isinstance(ratio,bool) or not isinstance(ratio,(int,float)) or not math.isfinite(ratio) or ratio<0:
        raise ValueError('ratio must be finite and nonnegative')
    return 'Type I' if ratio<1 else ('Type II' if ratio<=2 else 'Type III')


def arch_height_ratio(arch_points_mm,innominate_origin_mm,left_cca_diameter_mm,*,superior_axis=(0,0,1)):
    """Classify a centerline-landmark surrogate using I<1, II[1,2], III>2.

    Supplied landmarks are centerline points, not verified luminal anatomical
    landmarks. The output is explicitly not a clinical arch classification.
    """
    points,_=_curve(arch_points_mm)
    origin=_vector(innominate_origin_mm,'innominate_origin_mm')
    superior=_vector(superior_axis,'superior_axis')
    if np.linalg.norm(superior)<=0:
        raise ValueError('superior_axis must be nonzero')
    if isinstance(left_cca_diameter_mm,bool) or not isinstance(left_cca_diameter_mm,(int,float)) or not math.isfinite(left_cca_diameter_mm) or left_cca_diameter_mm<=0:
        raise ValueError('left_cca_diameter_mm must be finite and positive')
    superior/=np.linalg.norm(superior)
    top=float(np.max(points@superior))
    origin_height=float(np.dot(origin,superior))
    distance=top-origin_height
    if distance<0:
        raise ValueError('Innominate origin lies above the supplied arch top')
    ratio=distance/left_cca_diameter_mm
    return dict(status='PASS',kind='centerline-landmark-surrogate',clinical_classification=False,
                height_mm=distance,left_cca_diameter_mm=float(left_cca_diameter_mm),ratio=float(ratio),
                surrogate_type=arch_type_for_ratio(float(ratio)),
                boundaries=dict(type_i='ratio < 1',type_ii='1 <= ratio <= 2',type_iii='ratio > 2'),
                superior_axis=superior.tolist(),arch_top_projected_mm=top,origin_projected_mm=origin_height)
