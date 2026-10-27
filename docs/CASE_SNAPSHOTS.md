# 사례 저장·재로드

`vv-toolbox.case-snapshot/1`은 검증된 사례 JSON과 canonical JSON SHA-256 revision을 함께 저장한다. 원본·파생 출처, 중심선·반경, 연결 근거, 구간 분할 기록과 설정을 보존한다. 형상 생성기 재실행이나 표면·마스크 출력 기능은 포함하지 않는다.

## 사용

Docker의 프로젝트 환경에서 다음 모듈을 실행한다. 패키지 설치 시 `vv-case` 명령도 제공한다.

```text
python -m vv_toolbox.case_cli save INPUT_CASE.json OUTPUT_SNAPSHOT.json
python -m vv_toolbox.case_cli inspect OUTPUT_SNAPSHOT.json
python -m vv_toolbox.case_cli route SNAPSHOT.json --start NODE_ID --end NODE_ID --via EDGE_ID EDGE_ID
python -m vv_toolbox.case_cli split SNAPSHOT.json ANNOTATIONS.json ASSIGNMENTS.json DERIVED_SNAPSHOT.json --tolerance-mm 0.01
```

기존 파일 변경은 `--expected-revision CURRENT_SHA256`이 일치할 때만 허용한다. raw 입력 파일과 같은 출력 경로는 거부한다. 파이썬 `load_case(..., expected_sources=...)`는 원본 ID/해시 집합을 별도로 확인할 수 있다.

`route`는 PASS=0, FAIL=1, UNKNOWN=3 종료 코드를 반환한다. 미확인 경로를 자동화에서 성공으로 오인하지 않는다. `split`은 명시적 경계 대응과 전체 구간 범위 검토를 적용하고 검증된 결과를 snapshot으로 저장한다. 예제의 0.01 mm는 명령 문법 예시이며 해부학적 허용오차 권장값이 아니다. 실제 실행자는 대응 자료에 맞는 수치 허용오차를 명시해야 한다.

검증 후 같은 디렉터리의 임시 파일에 쓰고 flush/fsync 후 교체한다. 협력하는 writer는 독점 lock으로 직렬화한다. 남아 있는 lock은 자동 삭제하지 않으며 오류로 보고한다. 파일 손상이나 검증 실패 시 기본값으로 대체하거나 기존 저장본을 덮어쓰지 않는다. 프로세스 강제 종료·전원 차단에 대한 내구성 검증은 별도이며 현재 검사는 정상 실행 및 주입한 파일 교체 실패 범위다.

내용 해시는 손상 탐지 수단이며 신뢰 가능한 전자서명이 아니다. `PASS`는 데이터 구조·저장 무결성 범위이며 해부학적 연결·임상 유효성 승인이 아니다.

## 실행 결과: 2026-10-20

- Docker 관련 검사 51개 PASS. 새 저장 관련 5개는 roundtrip/revision 충돌, 손상·잘못된 사례의 덮어쓰기 방지, lock·원본 불일치, 파일 교체 실패 복구, CLI 실제 파일 흐름을 검사한다.
- 전체 동맥 사례 1,653 nodes / 1,081 edges 저장·재로드 PASS.
- 저장 전후 revision: `ac39f2d88883cf9f2389618a7ad6f0770dd3b5efef17278fbcefa02bf677aa24`.
- 1,081개 edge의 unresolved 상태 유지. 원본 사례와 snapshot은 로컬 `exports/atlas-case-inspection/`에 보관한다.
- 웹 앱 저장/재로드 연결과 표면·마스크 동반 저장은 아직 미구현이다.
