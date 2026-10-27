# 기준 모델·합성 사례 데이터 계약

버전 1 · 대상 VV-REQ-001/002/003/011/013/014 · [개발계획서](DEVELOPMENT_PLAN.md)

## 사례와 원본

`vv-toolbox.case/1`은 Atlas 원본 대응과 합성 사례를 기술하는 교환 문서다. 화면의 근접 후보 그래프와 별도로 관리한다. `case_id`는 산출 사례, `base_model_id`는 파생물 전체가 공유하는 기준 해부 모델의 ID다. train/validation/test 배정은 `base_model_id` 단위이며 독립 기준 모델 하나의 파생물을 서로 다른 세트에 넣지 않는다.

- `model_kind`: `source` 또는 `synthetic`.
- `sources`: id, SHA-256, 라이선스 참조. 공개 접근 가능성과 파생 배포 허가는 별도 판단한다.
- `frame`: id, units=`mm`, axes=`LPS`, origin 설명. 단위 미확인 원본은 물리 좌표 계약으로 가져오지 않고 원본 검사 자료에 보관한다.
- `generation`: source 사례는 null. synthetic 사례는 정수 seed, generator_version, 설정 dictionary를 보존한다. 시드만으로 다른 버전의 결과 일치를 보장하지 않는다.
- `split`: unassigned/train/validation/test. 여러 사례를 묶을 때 같은 base_model_id의 서로 다른 split 배정은 거부한다.

## 혈관 구간과 연결

`nodes`는 ID에서 접합점/범위 경계로의 사전이다. 각각 `position_mm`(미확인 시 null), `kind`, `evidence_status`를 가진다. `kind`는 junction/segment_boundary/scope_boundary/anatomical_terminal/unresolved다. 근접 후보는 junction으로 확정하지 않는다.

`edges`는 id, start, end, anatomy, geometry_kind, evidence_status, source_ids, centerline_mm, radii_mm를 가진다. anatomy는 artery, side(L/R/midline), segment, branch_id를 담는다. 동일 구간·좌우 클래스가 여러 edge에 대응할 수 있으며 각 edge ID는 유일하다. 연결은 start/end incidence로 양방향 유도하고 혈류 방향과 분리한다. 분기 부착점이 edge 내부에 있으면 edge를 나누고 구간·출처를 유지한다.

`geometry_kind`는 source/estimated다. source 사례에는 estimated 형상을 넣을 수 없다. 합성 사례에는 원본 및 estimated가 함께 존재할 수 있다. `evidence_status`는 source_annotation/landmark_reviewed/synthetic_estimate/unresolved이며 estimated는 synthetic_estimate로 표시한다. 좌표 없는 요소는 unresolved다. 중심선과 반경은 함께 존재하거나 함께 null이며, 존재 시 점마다 양의 유한 반경(mm)이 필요하다.

유효한 JSON 구조가 해부학적 연결 확인을 의미하지 않는다. 소스상의 접촉·교차, 경계 위치 근거, 실제 내강 연결은 별도 검토 기록을 참조한다.

고리 형태의 추출 edge는 동일 start/end node를 가질 수 있다. 이 경우 최소 3개 서로 다른 위치를 가진 닫힌 중심선이 필요하다. incidence에는 고리의 두 끝이 각각 반영된다. 접근 경로의 단순 경로 검사는 고리를 돌아 필수 혈관을 방문하는 우회를 허용하지 않는다.

`atlas_case.build_atlas_case`는 명시적으로 대응한 동맥 부품의 medial preview를 가져온다. source part ID, 추출 edge ID, 원본 및 preview 해시, 파생 방법을 유지한다. `branch_id`가 추출 edge ID인 경우 실제 해부 분지 판정이 아니라는 상태를 함께 기록한다. 추출 terminal을 해부학적 종말점으로 승격하지 않으며 구간은 unresolved로 남긴다. 근접 links는 inspection 목록에만 저장하고 통과 edge로 추가하지 않는다. 입력 preview의 과거 단위 가정 문구를 보존하며 별도로 확인된 좌표 계약을 요구한다.

## 접근 경로 검사

원자료 명칭만으로 좌우를 정할 수 없는 구조는 anatomy.side=`unknown`을 허용한다. 이를 midline으로 자동 변환하지 않는다. 원본 추출의 두 위치 왕복 고리는 `inspection.rejected_extraction_edges`에 원래 데이터와 사유를 보존하고 유효 edge 목록에서는 제외한다.

`access_routes.inspect_route`는 시작/종점 node ID와 순서가 정해진 필수 edge instance ID 목록을 받는다. 경동맥은 좌우 이름만으로 추정하지 않고 해당 instance를 필수 통과 구간으로 지정한다. 시작 혈관과 종점 혈관도 목록에 명시할 수 있다.

- incidence를 양방향 탐색하되 동일 node를 두 번 방문하지 않는다. 막힌 분지를 왕복하여 필수 구간을 방문한 것으로 처리하지 않는다.
- 확인 상태의 source 경로를 먼저 찾고, 없으면 synthetic 경로, 그다음 unresolved 연결을 포함하는 경로를 찾는다. 짧은 미확인 경로가 확인 경로보다 우선하지 않는다.
- `PASS/source_graph`와 `PASS/synthetic_graph`는 입력 그래프에 대한 구조 검사다. 연결 근거 자체의 진위, 표면 연속성, 카테터 통과 또는 임상 유효성 판정이 아니다.
- 미확인 edge 또는 node를 거치는 경로는 `UNKNOWN/unresolved_graph`로 반환한다. node의 미확인 상태도 인접 통과 edge에 반영한다.
- 순서대로 필수 구간을 통과하는 단순 경로가 없으면 `FAIL`. 탐색 상태 상한에 도달하면 `UNKNOWN/search_budget_exhausted`이며 단절로 판정하지 않는다.

반환값은 통과 node/edge ID, 미확인·추정 edge 목록과 검사 상태 수를 포함한다. 실제 Atlas adapter의 네 경로 지정 및 대상 구간별 통합 검사는 별도 구현 단계다.

## 라벨 및 출력 계약

`segment_materialization.materialize_segments`는 동일 원본 해시·좌표계의 source_annotation/landmark_reviewed 점 주석과 명시적 edge interval 주소를 소비한다. region_only, 미확인 위치, 다른 좌우·동맥·branch 대응은 거부한다. 원본 중심선 방향이 근위→원위라는 가정은 하지 않으며 labels의 전환을 주석과 대조한다.

분할에는 각 경계의 original interval index와 fraction, 전체 edge 범위의 구간 소속 검토 참조(`extent_review_refs`), 수치 대응 허용오차가 필요하다. 경계 하나만으로 원래 edge 전체의 구간 소속이 입증되지는 않는다. 경계 좌표와 지정한 중심선 위 위치 사이 잔차를 저장하며 중심선을 강제로 경계 좌표로 이동하지 않는다.

새 중심선은 기존 점과 선형 보간한 경계점·반경으로 구성한다. 공유 경계 node를 양쪽 구간이 사용하고 원본 edge ID·범위·주석 참조를 기록한다. 원본 입력은 불변이며 검증 실패 시 부분 결과를 반환하지 않는다. 구간 분할은 원래 연결 근거 상태를 승격하지 않는다. 현재 구현 범위는 중심선이며 표면·마스크 라벨 분할은 별도 단계다.

후속 출력에서는 혈관 foreground, 해부학 구간 클래스, edge/분지 instance, 병변 instance, 원본/추정 상태를 별도 배열로 관리한다. 하나의 정수에 해부학과 질환을 섞지 않는다. 불명확한 구간을 확정 구간 ID로 강제 배정하지 않는다.

전체 볼륨과 병변 crop은 voxel-to-world affine을 각각 기록한다. 배열 인덱스 순서·voxel 중심 convention·spacing·dtype·shape를 함께 저장하고, crop과 원본의 물리좌표 일치를 검사한다. 혈관 합집합 경계에서 단순 최근접 edge로 결정한 label은 생성 규칙 라벨임을 표시하며 독립 해부 정답으로 표시하지 않는다.

마스크 형식·해상도·junction voxel 소유 정책과 기하 허용오차는 exporter 명세에서 고정한다. 현재 `case_contract.py`는 사례·연결·출처·중심선 및 split 계약만 검증하며 마스크/질환/표면 생성 구현을 뜻하지 않는다.
