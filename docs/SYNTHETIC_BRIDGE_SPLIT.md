# 생성 연결의 분할 및 하복벽동맥 접합 후보

## 구현

`split_synthetic_bridge`와 CLI `split-bridge`는 이미 선언된 합성 bridge를 내부 주소에서 둘로 나눈다. 기존 일반 junction split의 우회가 아닌 별도 `vv-toolbox.synthetic-bridge-split/1` 선언을 사용한다. 입력 revision·자료 해시·주소·근거·새 ID 검사를 유지한다.

- 분할 전 전체 bridge와 외부 anchor는 이력에 보존한다.
- 두 child의 내부 anchor는 서로의 동일 접합점을 참조한다. 연속성 검사는 reciprocal sibling ID, parent bridge ID/revision, 내부 endpoint를 확인한다.
- side-branch의 출발 방향·반경 override는 첫 child의 외부 시작점에만 유지한다.
- bridge ID 목록을 두 child로 교체하고, 기존 외부 참조를 올바른 child로 갱신한다.
- 근거 상태는 synthetic_estimate이며 형상·경로 검사는 다시 필요하다. 기존 source_nodes_preserved=false를 후속 split이 true로 바꾸지 않도록 수정했다.
- 이미 분할된 child의 재분할은 아직 지원하지 않으며 명시적으로 거부한다. 병변이 있거나 선언되지 않은 bridge의 분할도 거부한다.

## 실제 합성 사례

`scripts/build_synthetic_epigastric_branch.py`는 [원본 접합 대조](EPIGASTRIC_SOURCE_JUNCTION.md)의 검토 위치를 **합성 구성 위치로 명시적으로 선택**했다. 위치가 실제 ostium으로 확정된 것은 아니다.

우측 외장골–대퇴 bridge를 두 구간으로 분할하고, 원본 `FJ3604:e0.start`까지 추정 side-branch를 추가했다. 새 node `synthetic_R_IEA_origin`의 degree는 3이다. source 형상과 그 외 edge는 동일하다.

- 사례: `exports/synthetic-epigastric-case/case.snapshot.json`.
- revision: `363551e43ad9b7d6a33e4853a9fa61e12ae76024f31d7c9b61cf34e14e8263df`.
- [검사 기록](evidence/synthetic-epigastric-branch.json): 전체 선언 bridge 부착부 14곳의 위치·반경 일치 및 표본 접선각 3도 이내 검사 PASS.
- Docker 관련 회귀 검사: **71 passed, 52 dependency deprecation warnings**. 분할·잘못된 계보 거부·side-branch override·CLI 저장/재로드·말단 절단·접합 영역·표면 회귀를 포함한다.

이전 후보의 주변/표면 검사는 새 revision에 자동 승계하지 않는다. 새 branch를 포함한 접합 영역, 표면, 주변 간격 검사는 **NOT RUN**이다. 원본 내강·정확한 ostium 및 해부학적 수용은 UNKNOWN이며 앱 기본 사례를 변경하지 않았다.
