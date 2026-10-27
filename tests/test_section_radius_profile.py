import math
import pytest
from vv_toolbox.section_radius_profile import section_radius_profile


def fixture():
    return dict(schema='vv-toolbox.source-sections/1',profiles=[dict(index=1,status='MEASURED',
        area_mm2=math.pi*4,area_equivalent_radius_mm=2.,center_boundary_distance_mm=.5),
        dict(index=2,status='UNKNOWN',reason='ambiguous')])


def test_distinct_radii_and_unknowns_are_preserved_without_filling_endpoints():
    result=section_radius_profile(fixture(),4)
    assert result['measured_count']==1 and result['radius_selection']=='UNSELECTED'
    assert result['stations'][1]['area_equivalent_radius_mm']==2
    assert result['stations'][1]['center_boundary_distance_mm']==.5
    assert result['stations'][0]['area_equivalent_radius_mm'] is None
    assert result['stations'][2]['status']=='UNKNOWN'
    assert result['stations'][3]['status']=='NOT MEASURED'


def test_inconsistent_area_is_rejected():
    sections=fixture();sections['profiles'][0]['area_mm2']=1
    with pytest.raises(ValueError,match='disagree'):section_radius_profile(sections,4)


def test_duplicate_station_is_rejected():
    sections=fixture();sections['profiles'].append(sections['profiles'][0])
    with pytest.raises(ValueError,match='Unique'):section_radius_profile(sections,4)
