# ACA 경계의 표본별 지형 검토

검토일: 2026-10-20. BodyParts3D 4.0 native LPS, mm. 대상은 좌우 A1/A2, A2/A3, A3/A4 6개 경계다.

## 결과와 적용 범위

**4개 경계의 지형 전환 영역을 수동 검토했고, ACom 부착 2개는 중심선 탐색 후보로 남긴다. 정확한 절단 평면이나 단일 좌표를 승인한 경계는 0개다.** `landmark_reviewed`는 아래 `localization_scope=region_only`와 함께 읽어야 한다. 앱의 확정 구간 분할이나 데이터셋 정답 라벨로 자동 승격하지 않는다.

원배포의 독립 경계 주석이 없다는 사실만으로 미확정 처리하지 않았다. 뇌량의 실제 sagittal 단면과 양측 혈관의 3D 주행을 보고 rostrum–genu 및 superior genu–body 전환을 식별했다. 다만 매끈한 표면에는 선 하나로 유일하게 정해지는 seam이 없으므로 넓이를 가진 검토 영역으로 기록한다.

| 경계 | 판정 | 원본 좌표 범위 또는 후보 [X,Y,Z] mm | 남은 사항 |
|---|---|---|---|
| R A1/A2 | candidate | 중심선 탐색점 [-4.086,-112.770,1537.924] | 독립 ACom/ACA 표면의 겹침에 해당하는 공유 ostial plane 결정 |
| L A1/A2 | candidate | 중심선 탐색점 [3.269,-113.606,1538.178] | 동일; 두 중심선의 최근접점이 접합 중심이라는 보장은 없음 |
| R A2/A3 | landmark_reviewed, region_only | [-3.337,-126.818,1553.243]–[-2.503,-123.481,1556.302] | inferior genu/rostrum 전환 영역 안의 운영 절단 평면 정의 |
| L A2/A3 | landmark_reviewed, region_only | [2.503,-126.807,1553.113]–[3.615,-123.470,1556.172] | 동일 |
| R A3/A4 | landmark_reviewed, region_only | [-3.894,-119.865,1576.604]–[-3.337,-110.131,1580.498] | superior genu에서 후방 주행으로 바뀌는 완만한 영역의 운영 평면 정의 |
| L A3/A4 | landmark_reviewed, region_only | [3.337,-119.855,1576.751]–[4.171,-110.122,1580.644] | 동일 |

범위는 검토자가 선택한 지형 전환 window에 들어오는 파생 중심선 표본들의 axis-aligned bounds다. 통계적 신뢰구간, 측정 오차 한계, 문헌에서 정한 mm 허용오차가 아니다. 좌우 유사성은 같은 Atlas의 관찰이며 독립 표본 재현성의 증거가 아니다.

## 실제 관찰

- FJ1742 뇌량을 X=0,-3,+3 mm 평면으로 절단한 단면에서 앞쪽으로 둥글게 돌아가는 genu, 아래쪽 rostrum, 위쪽 body 주행을 구별했다. 혈관은 단면으로 절단한 것이 아니라 같은 native 좌표에서 투영한 중심선이므로 그림 제목에 이를 명시했다.
- FJ1654/M 근위 ACA는 ACom 부근에서 끝나며, FJ1699/M pericallosal 경로가 inferior genu를 지나 뇌량 상면으로 계속된다. 따라서 A2/A3/A4 판정에는 FJ1699/M이 필수다. FJ1676/M callosomarginal 기시를 경계로 대신하지 않았다.
- 앞쪽 genu의 하부 굴곡과 rostrum 이행은 대략 Z 1553–1557 mm의 범위에서 관찰된다. 상부 genu는 Y -120–-110 mm 부근에서 후방으로 향하는 supracallosal course로 완만히 바뀐다. 고정 길이 분할이나 최대 곡률 자동 판정을 사용하지 않았다.
- ACom의 Z=1537.5 및 1538 mm 실제 수평 단면에서 ACom과 양측 ACA의 **서로 다른 폐곡선이 교차**한다. Z=1538.5에서는 ACom 단면이 보이지 않는다. 이는 단순 투영 중첩보다 강한 공간 위치 근거지만 별개 표면의 교차는 열려 있는 내강 접합을 증명하지 않는다.
- 파생 중심선 최근접 거리는 R 1.535 mm, L 1.926 mm다. 원자료의 접합부 중심선 주석이 아니며 이 수치가 연결 오류나 해부학적 허용오차를 뜻하지 않는다.

## 문헌 기준

- [2021 해부 연구](https://pmc.ncbi.nlm.nih.gov/articles/PMC8073207/): A2 끝은 뇌량 rostrum–genu 이행, A3는 genu 주변 주행이라는 지형 기준. 오래된 해부 정의 자료이며 2026년의 새 표본 검증 자료가 아니다.
- [1978 distal ACA 미세해부 원연구](https://pubmed.ncbi.nlm.nih.gov/671075/): ACA 구간과 cortical branch 기시를 구별한다. 분지 기시를 모든 표본의 구간 경계로 고정하는 근거로 사용하지 않는다.
- [2019 DACA 수술 원연구](https://www.sciencedirect.com/science/article/pii/S1878875019310332): A2의 rostrum–genu 경계, A3의 genu를 지나 위쪽 후방에 이르는 지형을 명시한다. 본 Atlas에 적용한 window 좌표는 문헌값이 아니라 위 형상에 대한 검토 판단이다.

## 재현과 근거

- [스크립트](../scripts/review_aca_boundaries.py), [근거 JSON](evidence/aca-boundary-review.json).
- 원본 ZIP은 acquisition manifest SHA-256과 대조한다. JSON에는 ZIP, 8개 OBJ, 파생 centerline JSON, 3개 그림의 SHA-256을 저장한다. 경계 영역에 들어가는 edge ID와 point index 및 모든 표본 좌표를 저장한다.
- Docker `python:3.12-slim` + numpy, scipy, trimesh, matplotlib, networkx에서 실행했다. 3개 실제 뇌량 단면, 2개 oblique 3D 방향, 3개 ACom axial 단면을 그림으로 열람했다. `exports/aca-boundary-review/`에 로컬 그림을 보관한다.
- 현재 검토는 source-specific 연구용 주석이다. 독립 검토자 재현성, 환자 영상 대조, 임상 승인, lumen 연결 검증은 NOT RUN 또는 NOT PROVEN이다.

다음 단계는 4개 검토 영역에 대해 해부학적 landmark를 유지하는 운영 절단면을 지정하고 해당 표면/중심선 분할의 민감도를 검사하는 것이다. ACom은 독립 표면 교차 영역을 명시적인 접합 구조로 모델링할지 결정하고 원본 변경 없이 별도 주석으로 남긴다.
