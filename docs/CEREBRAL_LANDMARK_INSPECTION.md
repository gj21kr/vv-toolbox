# 뇌혈관 구간 판정용 구조 검사

검사일: 2026-10-20 · 대상: BodyParts3D 4.0 · 관련: [구간 명세](CEREBRAL_SEGMENT_SPEC.md)

## 검사 결과

고정 acquisition manifest의 ZIP 및 개념표 4개 파일 SHA-256이 일치함을 확인했다. ZIP 내 정확한 요소 파일명과 IS-A 개념을 대응시키고 OBJ의 정점·면 수를 읽었다. 형상 변경, 단위 추정, 경계 좌표 생성은 수행하지 않았다.

| 구조 | FMA | 요소 | 정점 / 면 | 판정 |
|---|---|---|---|---|
| 뇌량 | FMA86464 | FJ1742 | 16,716 / 30,232 | 원본 형상 존재 PASS |
| 좌 insula | FMA72978 | FJ1748 | 1,250 / 2,448 | 원본 형상 존재 PASS |
| 우 insula | FMA72977 | FJ1749 | 1,261 / 2,448 | 원본 형상 존재 PASS |
| ACom | FMA50169 | FJ1655 | 63 / 80 | 원본 형상 존재 PASS |

IS-A/PART-OF 이름 목록에서 단어 경계로 genu, rostrum, limen, circular sulcus, limiting sulcus, operculum, opercular, lateral sulcus를 검색했으며 일치 항목은 없었다. 이것은 해당 지형이 형상에 없다는 뜻이 아니라 **별도 명칭·구간 경계 주석을 이번 목록에서 찾지 못했다**는 뜻이다. ACom 파일 존재도 좌우 A1/A2와의 실제 내강 연결 확인을 뜻하지 않는다.

## 구간 주석에 미치는 영향

- A2/A3·A3/A4: 뇌량 전체 표면을 참고할 수 있다. rostrum–genu 이행과 상면으로의 주행 전환은 표본별 검토가 필요하다.
- M1/M2·M2/M3: 좌우 insula 표면을 참고할 수 있다. limen과 circular sulcus의 위치 및 각 혈관의 경계 통과는 아직 미확인이다.
- M3/M4: operculum 및 Sylvian fissure 출구의 개별 주석을 확보하지 못했다. 혈관 모양이나 길이 비율로 경계를 자동 확정하지 않는다.
- A1/A2: ACom 원본 요소는 확보했다. 좌우 부착점은 별도 확인해야 한다.

현재 앱의 context 그룹은 심장 계열 FMA7088에 기반한다. 위 뇌량·insula를 주석용 화면에 표시하는 연결 작업은 별도로 필요하다. 이번 검사에서 앱 화면을 변경하거나 브라우저 검증을 수행하지 않았다.

## 산출물과 검증 범위

- 재현 스크립트: `scripts/inspect_cerebral_landmarks.py`.
- Git 추적용 측정 결과: [cerebral-landmark-inventory.json](evidence/cerebral-landmark-inventory.json). 입력·OBJ 해시, 개수와 원좌표 bounding box를 보관한다. bounding box는 landmark 좌표가 아니다.
- 실행: Docker `python:3.12-slim`, 표준 라이브러리만 사용.
- 무결성 및 4개 요소 판독: PASS.
- 단위·방향의 독립 확인, 실제 경계 좌표, 표면과 혈관의 시각적 대조: NOT RUN.

## 앱 연결을 위한 주석 저장 구조

`atlas_annotations.py`는 구간 경계 주석을 JSON으로 저장·불러오는 독립 모듈이다. 초기 경계는 null 좌표와 unresolved 사유를 유지한다. 검토된 경계는 좌표계·단위 확인과 근거 참조가 필요하며, 합성 경계는 합성 모델 문서에만 기록한다. 이 모듈은 아직 앱 API나 편집 화면에 연결되지 않았다.

Docker에서 `tests/test_atlas_annotations.py`의 **22개 테스트 PASS**를 확인했다. 저장·재로드, 비유한 좌표 거부, 근거 없는 검토 상태 거부, 합성/원본 분리, 손상 파일 처리 및 저장 실패 시 기존 파일 보존을 검사했다. 이는 저장 계약 검사이며 해부학적 좌표 정확도나 브라우저 검증이 아니다.

다음 구현은 뇌량·insula를 원좌표의 별도 표시 레이어로 추가하고, 경계 후보 선택 → 근거 기록 → 저장 → 재로드 흐름을 연결하는 것이다. 그 뒤 확인된 경계에 한해 중심선·표면 구간 라벨을 적용한다. 임의 분할 결과를 해부학적 확정으로 표시하지 않는다.

후속 결과: [실제 형상·좌표 판정](CEREBRAL_BOUNDARY_ADJUDICATION.md)에서 원좌표 단위·방향을 확인했으며, [앱 적용 검사](ANNOTATION_APP_VALIDATION.md)에 초안 저장 및 3D 표시 결과를 기록한다. 위 NOT RUN 항목은 이 문서의 최초 파일 검사 범위를 나타낸다.
