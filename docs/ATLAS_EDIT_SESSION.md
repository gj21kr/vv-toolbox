# Atlas 형상 편집 저장과 재로드

2026-10-20 · VV-REQ-001, 005, 013 · M4의 일부 구현.

## 사용자 흐름

`3 · Modify selected vessel`에서 혈관을 선택하고 반경·굴곡·비틀림을 적용한다. 아래 `Save vessel edits`는 모든 혈관의 현재 편집값을 로컬에 저장한다. `Reload saved edits`는 현재 편집값을 저장본으로 교체하고 표면·중심선을 함께 재생성한다. 선택 혈관, 카메라, 가시성 설정은 현재 상태를 유지한다.

원본 Atlas는 변경하지 않는다. `5 · Source case data`의 원본 중심선 사례 저장과 별개이며, 이 기능은 혈관 구간 경계·병변·마스크·연결 승인 저장을 포함하지 않는다. 화면은 형상 타당성과 충돌 검증이 미완료임을 계속 표시한다.

## 저장 계약

- 고정 로컬 파일 `reference-data/bodyparts3d/atlas-edits.snapshot.json`. Git 제외 영역이다.
- schema `vv-toolbox.atlas-edit-session/1`; source archive, 원본 중심선 및 원본/추정 부품 geometry의 SHA-256을 기록한다.
- 생성기 `anchor-preserving-centerline-field-v1`과 완전한 반경·굴곡·비틀림 파라미터만 저장한다. 원본 surface를 파일에 복제하지 않는다.
- payload hash로 손상을 검출한다. 해시는 서명이나 진위 인증이 아니다.
- 저장은 임시 파일 flush/fsync 후 원자적 교체하며 revision 비교와 배타적 writer lock을 적용한다. 외부 변경·기존 파일 삭제·남은 lock을 자동으로 덮거나 제거하지 않는다.
- 재시작 후 기존 파일을 덮기 전에는 재로드가 필요하다. 상태 조회만으로 덮어쓰기 기준 revision을 갱신하지 않는다.
- 재로드는 source/version/파라미터를 검증하고 전체 형상을 재생성한 뒤 live geometry를 갱신한다. scene setter 실패 시 기존 배열 복원을 시도하고 사례 데이터는 게시하지 않는다. 복원 자체가 실패하는 경우도 성공으로 표시하지 않는다.

API: GET `/api/atlas-edit-session`; POST `{action:"save"|"reload", expected_generation:int}`. 오래된 generation과 저장 revision 충돌은 409다.

## 실행 증거

Docker 전체 검사: **371 passed, 3 skipped, 296 warnings, 45.55 s**. 새 저장·재로드 14개 및 기존 변형 14개 검사도 별도로 통과했다. 건너뛴 Node 의존 검사 3개는 전체 PASS로 포함하지 않는다. NumPy/scikit-image deprecation 경고가 남아 있다.

실제 브라우저에서 FJ1692를 검색·선택하고 반경 1.30을 적용했다. 저장 → 원본 복원 → 재로드 후 다음 결과를 확인했다.

| 항목 | 결과 |
|---|---|
| UI 편집값 복원 | PASS: 1.30 |
| 수정 표면 해시 일치 | PASS: e29bf0a1b2dae89ed2b04b66ff5be4552ed50b93aaaba1f64155623b132ab6a8 |
| 수정 중심선 해시 일치 | PASS: 8d503147a6e70b5afd9382016aa141dde1ef63caaa3aab4ac86d60a55dd809a6 |
| 이전 generation 재로드 요청 | PASS: 409, 표면 보존 |
| 검사 종료 상태 | 원본 geometry 및 빈 편집 저장본으로 복원 |
| 상호작용 중 JavaScript pageerror | 0 |

리소스 404 한 건, THREE.Clock/WebGL 경고 및 검사 도구의 다른 origin iframe 접근 경고는 남았다. 콘솔 전체 무오류로 판정하지 않는다. 초기 검증 스크립트의 선택 API 응답 기대값을 200 단독에서 기존 앱의 202도 허용하도록 수정한 뒤 위 흐름이 통과했다.

재현: `scripts/verify_atlas_edit_session.cjs`. 기존 편집이나 저장 파일이 있으면 검증 스크립트는 중단해 보존한다. 로컬 근거: `exports/atlas-edit-session-verification/result.json`, `restored-vessel-edits.png`, `report.html`. 브라우저 세션 `2026-10-20-02-37-15-d3e4`의 영상·trace는 로컬 `.shiplight/inspect/`에 있다.

해부학적 연결, 경계 판독, junction 매끄러움 및 충돌 없는 변형의 M4 수용 조건은 여전히 미완료다.
