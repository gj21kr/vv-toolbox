"""Create a synthetic browser fixture with five neighbors at each endpoint."""
from pathlib import Path
from vv_toolbox.case_io import save_case, load_case, case_digest

case=dict(schema='vv-toolbox.case/1',case_id='relationship-fixture',base_model_id='fixture',
    model_kind='synthetic',split='unassigned',
    generation=dict(seed=0,generator_version='relationship-fixture/1',config={}),
    frame=dict(id='fixture',units='mm',axes='LPS',origin='synthetic fixture'),
    sources=[dict(id='fixture',sha256='a'*64,license_ref='synthetic test fixture')],
    nodes={},edges=[])


def node(ident,point):
    case['nodes'][ident]=dict(kind='unresolved',evidence_status='unresolved',position_mm=point)


def edge(ident,start,end):
    case['edges'].append(dict(id=ident,start=start,end=end,source_ids=['fixture'],
        geometry_kind='estimated',evidence_status='synthetic_estimate',
        anatomy=dict(side='unknown',artery='fixture',segment='unresolved',branch_id=ident),
        centerline_mm=[case['nodes'][start]['position_mm'],case['nodes'][end]['position_mm']],
        radii_mm=[1,1]))


node('first',[0,0,0]);node('last',[10,0,0]);edge('selected','first','last')
for end,x in [('first',-5),('last',15)]:
    for index in range(5):
        ident=f'{end}-{index}'
        node(ident,[x,index*2-4,2])
        edge(ident,end,ident)
# Coincident position does not imply shared identity.
node('coincident',[0,0,0]);node('separate',[0,5,0])
edge('not-a-neighbor','coincident','separate')
path=Path('exports/label-workbench/relationships.snapshot.json')
if path.exists():
    assert load_case(path)[1]==case_digest(case),'Existing fixture differs'
else:
    save_case(path,case)
print(f'Fixture: {len(case["edges"])} edges')
