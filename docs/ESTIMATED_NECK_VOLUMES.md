# 추정 경부 연결의 마스크용 체적 후보

`cap_estimated_neck`은 원본 Atlas가 아닌 `estimated-neck-connector`로 명시된 표시용 튜브에만 적용한다. 정확히 두 개의 단순 경계 루프, 일관된 면 방향, 평면·볼록 단면을 요구한다. 단면 중심에 fan 삼각형을 추가하며 원래 삼각형 좌표를 보존한다. 원본 혈관의 cap을 제거하거나 원본과 Boolean 합집합을 만들지 않는다.

최종 후보는 닫힘·방향·양의 체적·비퇴화 조건과 자기 접촉 검사를 통과해야 반환한다. 원래 표시 형상과 활성 장면은 변경하지 않는다. 결과는 독립된 추정 체적이며 해부학적 연결 수용이 아니다.

[실제 네 연결 검사](evidence/estimated-neck-volumes.json): 고정된 planarity 허용오차 0.001 mm에서 좌우 carotid/vertebral 경부 연결 4개 모두 PASS. 후보 파일은 `exports/estimated-neck-volumes/`에 보관했다. 주변 원본과의 접촉·내강 합집합 검증은 NOT RUN이다.

[관련 Docker 검사](evidence/neck-volume-and-tile-rollback-tests.xml): 12개 PASS. 원래 삼각형 보존, 원본 Atlas cap 금지, 비평면 경계 거부, 블록 출력 중 두 번째 파일 쓰기 실패 시 첫 블록까지 정리하는 검사를 포함한다.

실행: `python scripts/inspect_estimated_neck_volumes.py` (Docker).

## 파생 사례 등록

`derive_neck_volumes`는 캡처 사례를 복사하여 추정 경부 표면만 닫힌 후보로 교체한다. 부모 사례 revision, 부모 생성 조건과 단면 cap의 계산·검사 기록을 저장한다. 원본 표면과 중심선·연결 노드는 바꾸지 않는다. 한 후보라도 실패하면 입력 사례를 수정하지 않는다.

[파생 사례 회귀](evidence/neck-volume-case-tests.xml): 11개 PASS. 원본 표면·그래프·부모 사례 보존, 저장/재로드, 후속 후보 실패 시 입력 보존을 확인했다.

[실제 521개 표면 사례](evidence/atlas-neck-volume-case.json): 새 사례 저장·재로드 후 521개 모두가 좌표 보존 인덱스 정규화 기준의 닫힘·방향·양의 체적·비퇴화 조건을 만족했다. 원본 표면 517개 및 그래프가 정확히 보존됐다. 원본 전체의 자기 접촉 검사는 수행하지 않았으므로 topology 통과를 전체 기하 검증으로 확대하지 않는다.

- 실행(Docker): `python scripts/build_neck_volume_case.py`
- 파생 파일: `exports/atlas-neck-volume-case/f8714bac82de86e2ba4223f57ae33a3a975c5fddf76f2002b47e9c21a5f8119d.snapshot.json`

파생 사례의 전체 희소 마스크 실행, 원본과의 겹침 접합 검증 및 v1 경동맥 경로 연결 판정은 미완료다. 진행 중인 원본 517개 마스크 작업은 그대로 유지했다. Vertebral 후보는 기존 전체 Atlas 자료의 체적 준비이며 v1 접근 경로 범위 확장이 아니다.

## 원본 혈관과의 끝단 대조

[8개 끝단 샘플 검사](evidence/neck-volume-attachments.json)는 폐곡면 검사와 별도다. 각 cap의 정점·모서리 중점·면 중심 총 97점을 선언된 원본 혈관에 대조했다. 2/8만 모든 cap 샘플이 원본 내부/표면에 있었고, 나머지 6개에서는 17–20점이 원본 밖이었다.

끝단 중심에서 반대쪽 끝단 중심 방향으로 0.25 mm 이동한 확인점은 7/8에서 두 체적 내부였다. 우측 carotid–`FJ3564`에서는 이 확인점의 겹침을 확인하지 못했다. 이 한 점의 실패는 체적 전체가 분리됐다는 증명이 아니며, 전체 겹침 체적·연속 연결 검증은 NOT RUN이다. 끝단 중심과 선언된 원본 단면 중심 차이는 최대 약 0.000013 mm였다.

기존 경부 생성기는 원본 단면의 convex hull 면적을 등가 원형 반경으로 바꾼다. 중심 일치만으로 비원형 단면의 전체 포함을 보장할 수 없으므로 다음 보정은 실제 원본 단면 윤곽과 연결부 전이 형상을 대상으로 해야 한다. 현 후보의 **닫힌 체적 PASS**는 유지하지만 **원본 내강 접합 완료**로 표시하지 않는다. 원본이나 후보를 이 검사에서 변경하지 않았다.

실행(Docker): `python scripts/inspect_neck_volume_attachments.py`.
