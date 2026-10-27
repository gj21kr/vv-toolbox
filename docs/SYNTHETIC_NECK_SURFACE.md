# 합성 목 표면의 저장 결과 검사

검사일: 2026-10-20. 입력은 `exports/synthetic-neck-case/neck-surface.npz`이다. 생성 대상은 좌우 CCA/ICA 원본 파생 중심선 4개와 합성 연결 2개다. 이 표면은 **source-derived 중심선·반경을 implicit union으로 재구성한 합성 표면**이며 원본 Atlas 삼각형 mesh를 합친 결과가 아니다.

생성은 `python -m vv_toolbox.case_cli surface exports/synthetic-neck-case/case.snapshot.json exports/synthetic-neck-case/neck-surface.npz --edges estimated_L_carotid_gap estimated_R_carotid_gap FJ3483:e0 FJ1682M:e0 FJ3564:e0 FJ1682:e0 --spacing-mm 0.6`으로 실행했다. 이후 Docker에서 `PYTHONPATH=src python scripts/inspect_synthetic_neck_surface.py`로 저장 NPZ를 다시 읽어 검사한다.

[검사 JSON](evidence/synthetic-neck-surface.json)은 case revision과 NPZ hash를 고정한다. 원본 snapshot 및 NPZ를 수정하지 않는다.

| 항목 | 측정 결과 |
|---|---:|
| 격자 간격 | 0.6 mm |
| vertices | 32,824 |
| triangles | 65,640 |
| graph component | 2 |
| 실제 mesh component | 2 |
| component별 watertight·일관된 winding·양의 volume | 모두 PASS |
| component별 Euler number | 각각 2 |

각 component의 volume은 5,388.106 및 6,657.816 mm³이다. 이는 생성 표면의 수치이며 원본 해부학 부피로 해석하지 않는다. 닫힌 출력의 양끝 cap 역시 모델 scope 경계이며 해부학적 terminal 판정이 아니다.

네 접합의 확대 그림은 `exports/synthetic-neck-case/neck-surface-attachments.png`다. 중심선 접합점을 통과하는 금색 선을 표시했다. 각 그림은 중심에서 ±15 mm 범위에 face centroid가 있는 삼각형만 보이는 표시용 crop이다. 그림의 위아래 잘린 테두리는 저장 mesh의 열린 경계가 아니다. Topology 검사는 잘리지 않은 전체 NPZ에서 수행했다.

생성 표면은 이어진 component로 확인되지만 원본 파생 반경의 국소 변화와 표면 요철이 보인다. 시각화나 watertight 결과를 매끄러움 검증으로 대체하지 않는다. 정량 surface smoothness와 최종 triangle collision·self-intersection은 NOT RUN이다. 원본 Atlas surface union, 전신 표면, 해부학적 경동맥 분기 완성도 이번 검사 범위 밖이다.
