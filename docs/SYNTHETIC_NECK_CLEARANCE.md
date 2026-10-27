# 실제 합성 목 연결의 간격 검사

검사일: 2026-10-20. 재현: Docker에서 `PYTHONPATH=src python scripts/inspect_synthetic_neck_clearance.py`. [검사 JSON](evidence/synthetic-neck-clearance.json)을 Git 추적한다.

검사 대상은 [합성 목 사례](SYNTHETIC_NECK_CASE.md)의 좌우 두 연결이다. source case canonical hash, snapshot revision/file hash, seed 0 및 검사 parameter를 결과에 기록했다. 무작위 표본 추출 없이 해당 범위의 선분을 검사했으며 snapshot bytes를 변경하지 않았다.

## 범위별 결과

| 검사 | 범위 | 결과 |
|---|---|---|
| 비공유 node 간격 | 두 bridge 각각과 모든 원본 1,081 edge 및 두 bridge 상호 | PASS |
| 접합 주변 | 원본 CCA/ICA와 공유하는 네 접합의 collar 바깥 | 4/4 PASS |
| bridge 내부 | 명시한 arc 거리 이상 떨어진 같은 bridge 선분 | 2/2 PASS |

입력 1,083개 edge 모두 중심선 geometry가 있다. 비공유 검사에서는 2,153개 edge 쌍을 bounding box로 분리하고 35,910개 선분 쌍을 실제 계산했다. 공유 네 쌍은 별도 접합 검사에서 47,274개 선분 쌍을 계산했고 collar 안 822쌍을 제외했다. 두 bridge의 self 검사에서 8,930개 조합 중 국소 3,296쌍을 제외하고 5,634쌍을 검사했다. 검사 budget 소진은 없었다.

의심 접촉 witness는 0개였다. 향후 발견되면 정확한 edge/part·선분 index 또는 arc interval·좌표·반경·원자료 근거를 JSON에 함께 기록한다. 이 스크립트는 접촉을 자동 수정하지 않는다.

## 명시적 수치 조건

간격 margin은 0 mm이다. 각 선분의 최대 끝점 반경을 사용한 보수적 capsule envelope 사이 거리를 검사한다. 이 결과는 실제 원본 삼각형 표면 충돌 판정이 아니다.

접합 collar는 기존 수치 정책 `3 × 최대 incident 끝점 반경 + 2 × spacing`을 사용한다. spacing 0.6 mm를 기록했고 실제 표면을 생성한 것은 아니다.

| 원본 node | collar mm |
|---|---:|
| FJ1682M:n1 | 7.961516 |
| FJ3483:n1 | 13.2 |
| FJ1682:n0 | 7.961690 |
| FJ3564:n0 | 10.8 |

Self 검사의 arc 거리 창은 `4 × 최대 bridge 반경 + 2 × spacing`이다. 왼쪽 17.2 mm, 오른쪽 14.0 mm보다 가까운 국소 접힘은 수용 검사 범위에서 제외한다. 각 screen의 최대 선분 조합 budget은 2,000,000이다. 모두 수치 모델 검사 정책이며 임상 허용 기준이 아니다.

## 해석과 미검증 범위

PASS는 **두 합성 연결과 제공된 동맥 추출 중심선의 지정 범위**에 한한다. 원본 source-source 충돌 전체를 검사한 결과가 아니다. 원본에서 중심선을 얻지 못한 FJ3553, 격리된 퇴화 추출 고리 3개, 정맥 및 다른 표시 레이어는 포함되지 않는다. 전체 Atlas coverage와 해부학적 수용은 UNKNOWN이다.

공유 접합 collar 안·bridge의 국소 접힘은 NOT CHECKED이며, 최종 surface collision과 표면 매끄러움은 NOT RUN이다. 따라서 이번 결과로 원본 표면과 부드럽게 합쳐졌거나 해부학적 경동맥 분기가 완성되었다고 판정하지 않는다.

이 문서의 검사는 중심선 capsule 범위다. 별도 [생성 표면 검사](SYNTHETIC_NECK_SURFACE.md)는 선택한 6개 edge에서 생성한 합성 표면의 닫힘·component 수를 검사한다. 원본 Atlas mesh를 합친 결과가 아니며, 그 검사도 최종 표면 충돌·매끄러움을 승인하지 않는다.
