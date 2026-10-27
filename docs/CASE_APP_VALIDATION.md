# 원본 사례 데이터 앱 검증

검사일: 2026-10-20. 로컬 Docker 앱 8093/8094 및 headed Chromium.

## 구현 범위

왼쪽 `5 · Source case data`에서 원본 동맥 중심선의 사례 준비, 로컬 저장, 재로드, JSON 다운로드를 제공한다. 이 기능은 화면의 혈관 변형·목 추정 형상·표면·마스크를 저장하지 않으며 재로드가 3D 장면을 바꾸지 않는다는 범위를 명시한다. 원래 전체 작업 공간 export는 별도로 유지한다.

준비는 서버의 원본 중심선과 Atlas 메타데이터를 사용한다. 클라이언트가 원본 해시나 저장 경로를 정하지 않는다. 저장은 revision 검사, 재로드는 원본 해시와 좌표계 검사를 거치며 실패 시 현재 사례를 보존한다. `GET/POST /api/case-workspace`, `GET /api/case-download`를 사용한다.

## 실제 브라우저 결과

- 원본 사례 준비: PASS, 1,081 paths / 1,653 nodes.
- 저장→재로드→다운로드 digest 일치: PASS.
- 오래된 workspace version으로 저장: HTTP 409 PASS.
- 준비/저장/재로드 전후 scene generation 유지: PASS.
- 1,081개 미확인 경로 상태 유지: PASS.
- 검사 중 pageerror: 0. 콘솔에는 resource 404 및 기존 THREE/WebGL 경고가 있으므로 전체 콘솔 무오류로 표시하지 않는다.
- UI 화면 직접 열람 PASS. 저장 범위 설명과 버튼이 패널 폭 안에서 표시된다.

재현 스크립트: `scripts/verify_case_workspace.cjs`. 기존 저장본이 있으면 덮어쓰지 않고 검사를 중단한다. 이 검사는 새 snapshot 파일을 남기며 사용자 기존 파일을 삭제하지 않는다.

로컬 증거: `exports/case-app-verification/browser-result.json`, `source-case-workspace.png`, `report.html`. 재시작 전 기존 작업 공간 export는 같은 폴더의 `prior-workspace.json`에 보존했다. 원본 자료·화면·영상은 Git에 추가하지 않는다.

## 통합 검사

최종 Docker 전체 suite: **319 passed, 3 skipped, 289 dependency deprecation warnings**, 42.24초. 건너뛴 3개는 Docker Node 부재로 실행되지 않은 기존 JS 보조 검사다. 새 앱 흐름은 위 headed browser 검증으로 별도 확인했다.

질환 생성·해부 구간 확정·표면/마스크 앱 연결·전체 기준 경로 완료는 이 검사 범위 밖이며 개발 완료로 판정하지 않는다.
