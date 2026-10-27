# 명시적 내부 위치의 합성 접합 준비

`synthetic_junctions.split_synthetic_junction(case, specification, case_id=...)`는 원본 또는 합성 사례의 한 open edge를 명시된 내부 위치에서 두 edge로 나눈 **별도 합성 사례**를 만든다. 입력 사례를 수정하지 않는다. 새 node는 추후 접합을 위한 degree-2 node이며, 실제 해부학적 분기점의 승인이나 자동 연결이 아니다.

## 명세

`schema: vv-toolbox.synthetic-junction/1`과 다음 값이 필요하다.

- `parent_case_sha256`: 입력 전체 사례의 `case_digest`.
- `source_hashes`: 입력 `sources`의 ID→SHA256 전체 목록과 정확히 일치하는 객체.
- `edge_id`: 분할할 기존 edge ID.
- `node_id`: 기존 node와 충돌하지 않는 새 ID.
- `child_edge_ids`: 두 개의 서로 다른 새 edge ID.
- `rationale`, `evidence_refs`: 선택 이유와 검사 근거.
- 위치는 `interval_index`와 `fraction` 또는 `sample_index` 중 한 방식만 쓴다.

Fraction은 엄격하게 0보다 크고 1보다 작아야 한다. 두 원본 sample 사이의 좌표와 반경을 같은 fraction으로 선형 보간한다. 기존 sample을 선택하려면 양 끝을 제외한 `sample_index`를 사용한다. 최근접 점 찾기, 임계거리 snap 또는 해부학 이름으로 위치를 추정하는 동작은 없다.

## 출처와 불변 조건

원래 edge는 출력의 활성 edge 목록에서 두 child로 대체되지만, 전체 parent edge를 `synthetic_junctions.history`에 보존한다. 각 child의 `derived_interval`은 parent case revision, parent edge ID, 원래 sample index+fraction 주소 구간을 기록한다. 원래 artery·side·segment·branch identity를 유지하며 새 해부학 구간 라벨을 만들지 않는다. 새 node와 child들은 synthetic_estimate/estimated로 표시한다.

원래 외곽 node와 좌표·끝점 반경은 그대로다. 선택하지 않은 edge는 보존하며, 기존 bridge가 교체되는 parent의 외곽 endpoint를 참조하면 start→첫 child의 start, end→둘째 child의 end로 앵커만 재연결한다. 이전 앵커는 history에 보존하고 bridge geometry는 바꾸지 않는다. 기존 bridge ID 목록과 원본 case hash도 유지하지만 연결/충돌 판정은 NOT RUN으로 초기화한다. 오래된 route 결과와 품질 기록은 현재 결과로 재사용하지 않고 archive한다.

선택 edge에 기존 병변이 있거나 닫힌 고리·geometry 누락이면 거부한다. 선언된 bridge 자체를 분할하는 작업은 별도의 bridge lineage 정의가 필요하므로 거부한다. 반복 분할은 각각의 전체 parent를 history에 추가한다.

## 이후 연결

분할만으로 다른 혈관에 붙지 않는다. 별도 `extend_synthetic_routes` 명세를 현재 분할 사례 hash에 결합하고, 원하는 child의 새 node endpoint와 상대 혈관 endpoint를 명시해야 한다. 기존 원본 전용 `build_synthetic_routes`의 입력 제한을 우회하지 않는다. 접합 후에도 원본의 미확인 연결 근거는 확정 상태로 바뀌지 않는다.

CLI는 `vv-case split-junction input.snapshot.json specification.json output.snapshot.json --case-id new-id`이다. 별도 출력의 source 보호와 revision 비교는 사례 CLI 계약을 따른다.

연결 추가 CLI는 `vv-case extend-routes split.snapshot.json extension.json connected.snapshot.json --case-id connected-id`이다. 명세의 schema는 `vv-toolbox.synthetic-route-extension/1`, `parent_case_sha256`은 분할 후 사례의 해시다. 기존 연결 ID와 원본 출처를 유지하면서 `bridges`에 선언한 연결만 추가한다.

### 측분지의 방향과 반경

측분지는 `attachment_mode: side_branch`와 `from_direction_xyz`, `from_radius_mm`를 명시한다. 시작 node에는 기존 edge가 두 개 이상 연결되어 있어야 한다. 명시한 반경은 양수이고 부모 endpoint 반경 이하여야 한다. 큰 부모 혈관의 반경·접선 방향을 그대로 딸혈관 입구에 적용하지 않는다. 방향은 정규화하며 0 벡터는 거부한다. 끝에서는 상대 혈관 endpoint의 반경과 진행 방향을 사용한다.

이 설정은 합성 연결 형상의 수치 조건이다. 표면이 부모 혈관 내부에서 합쳐지는 접합부의 실제 해부학적 형상이나 표면 품질을 증명하지 않는다. 연속성 검사는 측분지 시작에서 **선언한 분지 방향·반경**과 비교하고, 실제 부모 반경과의 차이도 따로 기록한다. 기존 직렬 연결의 부모 endpoint 비교는 유지한다.

## 검증

Docker의 `tests/test_synthetic_junctions.py`와 `tests/test_synthetic_routes.py` 검사에서 **28 passed**를 확인했다. Source 불변, 좌표·반경 연속, 기존 sample 분할, branch identity, 전체 parent archive, bridge 외곽 앵커 재연결, 중복 ID·hash 불일치·잘못된 위치·병변 거부와 반복 분할이 포함된다. 수치 구조 검증이며 실제 해부학 접합 또는 표면 매끄러움의 승인이 아니다.

추가 통합 검사: `test_synthetic_junctions.py`, `test_synthetic_route_extension.py`, `test_junction_continuity.py`, `test_synthetic_route_cli.py` **36 passed**. CLI로 내부 분할 → 측분지 추가 → snapshot 재읽기를 실행하고, degree-3 연결·기존 bridge 보존·입력 불변·출력 덮어쓰기 거부를 확인했다.
