# 파생 혈관의 역할 추적과 좌측 장골 접합

## 역할 추적

`resolve_source_roles`는 명시된 원본 edge ID에서 현재 활성 split/trim descendant를 찾는다. 여러 세대의 `derived_interval`과 보존된 parent edge 이력을 사용한다. 제거된 tail은 경로에 포함하지 않는다. 혈관명이나 거리로 대체하지 않으며, 누락·순환·모호한 계보를 거부한다.

`scripts/inspect_access_route_gaps.py`는 `--snapshot`과 `--output`을 지원한다. 원본 역할 목록과 해시 검사를 유지하며 특정 arch child 이름을 코드에 고정하지 않는다.

| 사례 | 연결된 leg 종류 | 미연결 leg 종류 |
|---|---:|---:|
| 대동맥궁–경동맥 후보 | 3 | 14 |
| 하복벽 포함 외장골–대퇴 후보 | 5 | 12 |
| 좌측 총장골–외장골 node 통합 후보 | 6 | 11 |

17은 네 접근 조합을 ACA/MCA 근위 원본 요소까지 검사할 때의 공통 leg 종류 수다. 8개 선언 경로 모두 아직 미완성이다. pairwise 연결 개수는 전체 순서 경로, 해부 구간 커버리지, 내강 연속성의 통과 수가 아니다.

## 동일 좌표의 명시적 node 통합

`coalesce_synthetic_nodes`는 원본을 보존하고 별도 합성 사례에서 정확히 일치하는 좌표의 node만 통합한다. 허용 거리 기반 snapping은 하지 않는다. 명시된 사례·자료 해시, node ID, 근거와 사유가 필요하다. 원본 node 및 변경 edge를 이력에 보존하고, 형상·경로 결과를 무효화한다. 끝점을 통합하면 self-loop가 되는 edge와 고립 node는 거부한다.

좌측 `FJ3464:e0.end`와 `FJ3466:e0-trim-first.start`는 `[31.2, -96.8, 907.2]` mm에서 정확히 일치한다. 두 점을 별도 합성 node로 통합했다. **모든 중심선과 반경 배열은 그대로다.** 계약상 수정 edge는 estimated로 표시하고 좌표·반경 불변을 별도로 기록한다.

단, 원본 끝점 반경 차이 **0.335881 mm**, 마지막/첫 표본 chord 각도 차이 **60도**가 있다. 따라서 그래프 연결만 확보했으며 매끄러운 접합 형상으로 승인하지 않는다. 내부장골 등 다른 분지의 관계도 이번 통합으로 해결된 것은 아니다.

- 사례: `exports/synthetic-left-iliac-case/case.snapshot.json`.
- revision: `ba73dd6b5eae4f2dd96e58ce5af1ae457af9b66b814a2a10e8561ba3a8174524`.
- [접합 기록](evidence/synthetic-left-iliac-junction.json), [현재 경로 결손](evidence/access-route-gaps-left-iliac.json), [직전 경로 결손](evidence/access-route-gaps-epigastric.json).
- 재현 스크립트: `scripts/build_synthetic_left_iliac_junction.py`.
- Docker 역할/경로/trim/bridge 관련 29 tests PASS, 추가 node 통합 및 역할 검사 9 tests PASS. 두 수에는 역할 검사 3개가 중복되므로 합산하지 않는다. node 통합 최초 테스트에서 계약의 estimated 상태 결합 제약을 확인하고 수정했다.

표면·접합 연속성의 최종 수용과 앱 기본 적용은 보류한다.
