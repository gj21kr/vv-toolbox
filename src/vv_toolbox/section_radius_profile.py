"""Explicit radius measurements from source sections; no endpoint inference."""
import math


def section_radius_profile(sections,station_count):
    if type(station_count) is not int or station_count<3 or sections.get('schema')!='vv-toolbox.source-sections/1':
        raise ValueError('Source sections and valid station count required')
    result=[dict(index=i,status='NOT MEASURED',reason='endpoint section not measured' if i in (0,station_count-1) else 'section absent',
                 area_equivalent_radius_mm=None,center_boundary_distance_mm=None) for i in range(station_count)]
    seen=set()
    for section in sections['profiles']:
        index=section['index']
        endpoint_enabled=sections.get('endpoint_sections')=='ATTEMPTED'
        if (type(index) is not int or not 0<=index<station_count or index in seen
                or (index in (0,station_count-1) and not endpoint_enabled)):
            raise ValueError('Unique interior station indices required')
        seen.add(index)
        if section['status']!='MEASURED':
            result[index].update(status='UNKNOWN',reason=section.get('reason','section unresolved'));continue
        area=section['area_mm2'];radius=section['area_equivalent_radius_mm'];distance=section['center_boundary_distance_mm']
        if any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in (area,radius,distance)):
            raise ValueError('Positive finite section measurements required')
        if not math.isclose(radius,math.sqrt(area/math.pi),rel_tol=1e-8,abs_tol=1e-10):
            raise ValueError('Area and equivalent radius disagree')
        result[index]=dict(index=index,status='MEASURED',area_mm2=area,
            area_equivalent_radius_mm=radius,center_boundary_distance_mm=distance)
    return dict(schema='vv-toolbox.section-radius-profile/1',stations=result,
        measured_count=sum(s['status']=='MEASURED' for s in result),
        endpoint_policy='not inferred',radius_selection='UNSELECTED',
        limitation='Equivalent-area radius does not preserve a noncircular wall. Center-to-wall distance is a planar inscribed radius, not a 3D clearance bound.',
        accepted_for_generation=False)
