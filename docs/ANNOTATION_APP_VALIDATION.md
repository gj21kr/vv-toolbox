# 경계 초안 앱 적용 및 검증

검사일: 2026-10-20 · 관련: [좌표 판정](CEREBRAL_BOUNDARY_ADJUDICATION.md), [구간 명세](CEREBRAL_SEGMENT_SPEC.md)

## 적용 기능

Atlas 작업 패널의 **4 · Cerebral boundary drafts**에서 좌우 ACA/MCA 경계를 선택하고, 미확인 사유·검토 메모·출처·후보 XYZ를 저장하거나 다시 불러올 수 있다. 원좌표의 뇌량·좌우 insula를 별도 표시하고, 저장된 후보점으로 3D 카메라를 이동한다.

좌표는 `bodyparts3d_native_LPS`, mm이다. [공식 좌표 정의](https://dbarchive.biosciencedbc.jp/data/bodyparts3d/20130619/coordinate_system.png)와 그림 해시는 좌표 판정 문서에 보관한다. 좌표계 확인은 경계의 해부학적 승인이 아니다.

좌우 ACom의 원본 표면 탐색 후보 2개를 원요소 해시·검사 보고서 참조와 함께 로컬 초안에 등록했다. `candidate_positions`에만 저장하며, 12개 `boundaries[].position`은 모두 null이다. 자동 혈관 분할·구간별 변형이나 경계 승인 기능은 이번 적용에 포함하지 않는다.

## 저장 및 표시 계약

- 저장 위치는 서버에서 고정한 Git 제외 경로 `reference-data/bodyparts3d/cerebral-boundary-drafts.json`이다. 웹에서 임의 파일 경로를 받지 않는다.
- 입력·원자료 fingerprint를 검증하고, 이전 revision의 저장을 409로 거부한다. 정상 문서는 임시 파일을 거쳐 교체한다.
- 좌표가 비유한 수이거나 미확인 경계를 승인 상태로 바꾸는 요청은 허용하지 않는다.
- 기존 저장 자료의 좌표계·단위를 자동 변경하지 않는다. canonical frame/mm 및 확인 상태가 없는 후보는 3D 표시를 거부한다.
- 저장·재로드 시 이전 후보 표시를 제거한다. Atlas에서 다른 source로 전환하면 후보와 landmark 표시를 제거하고 토글을 초기화한다.
- 서버 기본 바인딩은 127.0.0.1이다. Docker 검증에는 `VV_BIND_HOST=0.0.0.0`과 호스트의 127.0.0.1 포트 공개를 함께 사용했다.

## 실행 검증

| 검사 | 결과 및 범위 |
|---|---|
| 주석 저장/표시 회귀 테스트 | Docker 52 PASS: annotation API/service, 주석 문서, app controls |
| 최종 전체 테스트 | Docker 244 PASS, 3 SKIPPED, 289 dependency deprecation warnings; Node 미설치로 기존 UI 로직 테스트 3개 건너뜀 |
| 실제 브라우저 저장·재로드 | PASS: 좌 ACA A1/A2 후보 값 보존 및 authoritative position=null 확인 |
| 뇌량·insula 표시 | PASS: 원좌표 반투명 구조를 실제 3D 화면에서 확인 |
| 저장 후보 3D 이동 | PASS: ACom 탐색 후보 표시와 카메라 이동 확인 |
| 브라우저 검증 데이터 정리 | PASS: 검사 메모를 제거하고 출처가 있는 후보만 보존 |
| 해부학적 경계 승인 | UNKNOWN: 0개 승인, 12개 미확인 유지 |

브라우저 재현 스크립트는 `scripts/verify_annotation_browser.cjs`이다. 이미 열린 로컬 CDP 브라우저를 사용하고 검증 전 초안을 복구한다. Node Playwright는 브라우저 조작용으로만 사용했으며 Python 패키지 테스트·형상 계산은 Docker에서 실행했다.

Shiplight headless Chromium은 SwiftShader의 소프트웨어 3D 렌더링에서 DOM 검사 시간 초과가 발생했다. 일반 Chromium의 NVIDIA RTX 4090 렌더링에서는 저장·재로드·표시가 통과했다. `verify` 절차와 Playwright를 병행했다. 성공한 상호작용 구간에서 pageerror는 0개였다. 전체 세션 로그에는 서버 재시작 중 연결 오류, 초기 404, THREE 경고 및 검사 도구의 cross-origin iframe 접근 경고가 있으므로 console-clean으로 표시하지 않는다.

화면 증거는 로컬 `exports/annotation-ui/boundary-inspection-final.png`에 보관한다. 원본 형상·브라우저 영상·trace는 Git 제외 또는 로컬 도구 증거 경로에 두며, 이 보고서와 좌표 판정 JSON은 Git 추적한다.

브라우저 보고서: 로컬 `exports/annotation-ui/report.html`. 서버는 127.0.0.1:8093, 3D는 127.0.0.1:8094에서 확인했다.

## 남은 범위

세부 landmark에 근거한 실제 구간 경계 승인, 분지별 경계 추가 UI, 표면·중심선·마스크의 구간 분할 및 구간별 변형은 후속 작업이다. 현재 초안을 확정 분할 정답으로 출력하지 않는다.
