"""Generate real description templates without constructing or accepting geometry."""
import json
from pathlib import Path
from types import SimpleNamespace
from vv_toolbox.app import Workspace
from vv_toolbox.ui_language import JS

common=dict(title='좌측 경동맥 · 내강 결합 후보',scope='원본 경동맥 두 부분과 추정 목 연결부를 결합한 합성 표면')
summaries=[
    dict(common,access_union=dict(lineage_faces=50188,centerline_status='PASS',checked_paths=65,context_status='FAIL')),
    dict(common,access_union=dict(lineage_faces=None,centerline_status='PASS',checked_paths=65,context_status='FAIL')),
    dict(common,access_union=dict(centerline_status='PASS',checked_paths=65),radius_edit=dict(scale=1.05,self_contact=dict(status='NO_CONTACT_DETECTED'),neighbor_contact='FAIL')),
    dict(common,carotid_union=dict(path_segments=128,lineage_faces=2345)),
    dict(common,carotid_union=dict(self_contact='NO_CONTACT_DETECTED'),radius_edit=dict(scale=1.05,neighbor_contact='UNKNOWN')),
    dict(common,protected_comparison=dict(reference=True,affected_pairs=28)),
    dict(common,protected_comparison=dict(reference=False,affected_pairs=28)),
    dict(common,context_inspection=dict(status='UNKNOWN',separated_count=5,context_edge_count=8)),
    dict(common,pair_surface_separation='UNKNOWN'),
]
folder=Path('exports/candidate-language');folder.mkdir(parents=True,exist_ok=True)
descriptions=[Workspace.description(SimpleNamespace(source='candidate',candidate=dict(summary=summary)),None) for summary in summaries]
(folder/'descriptions.json').write_text(json.dumps(descriptions,ensure_ascii=False),encoding='utf-8')
(folder/'language.js').write_text(JS,encoding='utf-8')
