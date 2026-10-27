# 좌측 장골 접합 smoothing의 표면·주변 비교

수정 전 revision `ba73dd6b5eae4f2dd96e58ce5af1ae457af9b66b814a2a10e8561ba3a8174524`, 수정 후 `23b547d31386462dbae203c4f60f67c0c363962878db538af88fe657570f5621`를 비교했다. 대상 edge는 `FJ3464:e0`, `FJ3466:e0-trim-first`다.

## 결과

| 항목 | 전 | 후 |
|---|---:|---:|
| 0.6 mm 격자 표면 생성 | PASS | PASS |
| 정점 | 22,467 | 22,444 |
| 삼각형 | 44,930 | 44,884 |
| 주변 검사 interval 쌍 | 196,163 | 196,163 |
| 주변 접촉 후보 쌍 | 8 | 8 |

주변 신규/제거 쌍은 각각 0개다. 여유 1.2 mm를 유지했고 모든 imported case 중심선을 주변 장애물로 사용했다. 동일 공유 node의 접촉은 이 주변 검사에서 제외되며, 선택 표면의 접합 collar·비국소 자기접촉 검사는 표면 생성 과정에서 별도로 수행한다.

기존 8쌍은 총장골–FJ1932:e0/FJ3427:e0/FJ3468:e0/FJ3565:e2/FJ3632:e1/FJ3636:e2, 외장골–FJ3468:e0/FJ3532:e0다. 이 결과는 현재 국소 수정이 새로운 capsule 접촉 쌍을 만들지 않았다는 뜻이며 기존 8쌍의 해부학적 연결을 승인하지 않는다.

기존 접합점의 Z=907.2 mm를 기준으로 동일한 고정 축상 평면 6개에서 실제 mesh 윤곽을 겹쳐 열람했다. 중심선 이동·반경 smoothing에 따른 국소 표면 변화가 보이며, 전후 모두 닫힌 단면이다. 그림만으로 정량적 표면 거칠기 개선이나 최종 mesh 자기교차 부재를 주장하지 않는다.

## 재현 및 상태

- 스크립트: `scripts/inspect_left_iliac_smoothing.py`.
- [검사 JSON](evidence/left-iliac-smoothing-inspection.json).
- 표면과 그림: `exports/left-iliac-smoothing-inspection/`의 `before-surface.npz`, `after-surface.npz`, `sections.png`.
- 원본 snapshot 불변, 결과 표면·그림 해시 기록.
- 선택 표면 생성 PASS, 주변 간격 UNKNOWN(기존 8쌍), 최종 mesh 충돌 NOT RUN, 해부학적 수용 UNKNOWN.

연속적인 파생 변환에서 기존 node 수정 이력이 사라지는 표시 오류도 수정했다. 중심선·반경 smoothing은 이전 `source_nodes_preserved=false`를 유지하며 true로 바꾸지 않는다. 관련 Docker 회귀 검사 **27 passed**. 앱 기본 적용은 하지 않았다.
