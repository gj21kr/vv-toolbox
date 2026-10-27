# 외장골–대퇴 합성 후보의 주변·표면 검사

대상 revision: `69cca3347e668d85ce9bd28af8ecb3d2eea95ff7812c6ad7a01cd14914c3444f`.
기준은 절단 전 대동맥궁–경동맥 합성 사례다. 입력 snapshot은 변경하지 않았다.

## 주변 검사

현재 사례에 포함된 모든 중심선 형상을 주변 장애물로 사용하고, 수정한 네 혈관 구간과 생성 연결 두 개가 관여하는 쌍을 검사했다. 절단 child는 원본 edge ID로 정규화하되, 새 연결은 독립 ID로 유지했다. 수정 대상끼리의 접촉은 주변 증감에서 제외하고 전체 raw screen에는 남겼다. 검사 여유는 1.2 mm다.

| 항목 | 결과 |
|---|---:|
| 기준 주변 접촉 후보 | 13쌍 |
| 수정 후 주변 접촉 후보 | 11쌍 |
| 유지 | 10쌍 |
| 더 이상 검출되지 않음 | 3쌍 |
| 신규 | 1쌍 |

신규 쌍은 `FJ3604:e0`(원본 명칭: right inferior epigastric artery)과 `estimated_R_iliofemoral`이다. 최초 witness의 clearance 하한은 +1.189934 mm였지만, **전체 45,649 interval 쌍을 검사한 최솟값은 −0.950679 mm**였다. 최초 witness는 최솟값이 아니다.

이 수치는 중심선 interval의 최대 끝점 반경 capsule을 이용한 보수적 하한이다. 실제 표면 관통 깊이를 뜻하지 않으며, 실제 내강 접합도 증명하지 않는다. 해당 근위 분지와 생성 구간의 위치·연결 관계를 함께 검사해야 한다. 원래 1.2 mm gate는 그대로 유지한다. 충돌 판정을 통과시키려고 margin을 줄이지 않았다.

## 표면 검사

양쪽 각각 유지 구간 2개와 생성 연결 1개를 spacing 0.6 mm로 표면화했다. 기본 비접합 간격·접합 collar 밖 간격·비국소 자기접촉 검사를 통과했고, 각각 단일 graph component의 닫힌 방향성 표면과 양의 체적을 확인했다.

| 측 | 정점 | 삼각형 |
|---|---:|---:|
| 좌측 | 65,107 | 130,210 |
| 우측 | 64,580 | 129,156 |

`exports/iliofemoral-candidate-inspection/sections.png`의 실제 표면 축상 단면 6개를 열람했다. 이는 생성된 표면의 단면이며 원본 해부 경계나 전체 주변 충돌 승인 자료가 아니다. 선택 표면에는 하복벽동맥이 포함되지 않으므로, 선택 표면 생성 PASS가 주변 간격 UNKNOWN을 해소하지 않는다.

## 재현 및 상태

- `scripts/inspect_iliofemoral_candidate.py`: [전체 검사 기록](evidence/iliofemoral-candidate-inspection.json).
- `scripts/inspect_iliofemoral_surface_sections.py`: [단면·신규 접촉 상세](evidence/iliofemoral-surface-sections.json).
- 모든 형상 계산은 Docker에서 실행했다. 결과는 입력 revision과 표면·그림 SHA-256에 결합한다.
- 국소 표면 생성: **PASS**.
- 주변 간격: **UNKNOWN**, 신규 1쌍과 기존 10쌍 검토 필요.
- 최종 mesh 간 충돌·내강 연결: **NOT RUN / UNKNOWN**.
- 앱 기본 적용: **NOT ACCEPTED**. 원본에 존재하지만 import 이전 누락된 형상은 이번 주변 검사 범위에 포함되지 않는다.
