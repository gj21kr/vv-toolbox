# ACA 여섯 경계의 원자료 추가 판독

실제 ACA/ACom 교차 영역으로 좌우 A1/A2 운영 후보를 구체화하고, 실제 뇌량 단면과 함께 나머지 네 전환 영역을 재검사했다. **검사 6개 완료, 정확한 해부학 경계 승인 0개**다. 모든 경계의 승인 좌표 `position`은 null이며 후보 좌표는 별도로 기록했다. 원본과 앱 라벨은 변경하지 않았다.

## A1/A2: 표면 교차에서 유도한 운영 후보

기존 최근접 중심선 vertex 선택을 대신하여, Z 1536.5–1539.0 mm에서 실제 ACA/ACom 표면의 축상 윤곽 교차 좌표를 계산했다. 0.05 mm와 0.025 mm 두 간격을 검사하고, 교차점들의 평균 좌표를 ACA **연속 polyline 구간**에 투영했다. 이는 표면 교차에 근거한 운영 규칙이며 shared ostium이나 내강 접합의 확정은 아니다.

| 경계 | 최종 후보 [X,Y,Z] mm | 원본 edge 주소 | 교차점 투영 station 범위 |
|---|---|---|---|
| R A1/A2 | [-3.994907,-112.861133,1538.014513] | FJ1654:e0 interval 21, fraction 0.222643 | 10.267753–11.818017 mm |
| L A1/A2 | [3.269241,-113.606129,1538.177952] | FJ1654M:e0 interval 22, fraction 1.0 (=sample 23) | 12.622773–13.385398 mm |

Station은 저장된 edge 시작점부터의 호길이이며 혈류 방향을 뜻하지 않는다. 양 후보 모두 extraction edge의 내부에 있다. 왼쪽 결과가 기존 sample과 같아도 새 선택 방법은 표면 교차 centroid의 연속 구간 투영이다.

0.025 mm sweep에서 오른쪽 교차점 98개·왼쪽 62개를 기록했다. 표본 교차 Z 범위는 각각 1537.075–1538.275 mm, 1537.500–1538.250 mm다. 0.05→0.025 mm 간격 변경에 따른 후보 위치 이동은 오른쪽 0.001917 mm·왼쪽 0 mm다. 이는 수치 sampling 민감도이며 해부학 오차나 confidence interval이 아니다.

교차점 centroid와 ACA 중심선 후보의 3D 거리는 오른쪽 1.126679 mm·왼쪽 1.136170 mm다. centroid는 별도 표면이 만나는 벽 영역에 있으므로 중심선과 같을 필요가 없다. 여전히 원본 표면 사이 실제 열린 내강·공유 ostial plane·분기 topology는 미확정이다. 사용한 평균은 Z-slice 가중 평균이며 면적/길이 가중 ostium 중심을 측정한 것이 아니다.

## A2/A3, A3/A4: 실제 뇌량의 완만한 전환

FJ1742 원본 뇌량을 X=-3,0,+3 mm에서 절단했다. 해당 sagittal contour와 원래 혈관 중심선의 Y/Z 투영을 확대해 기존 window의 시작·중간·끝을 표시하고 직접 확인했다. 여기서 혈관선은 단면이 아닌 투영이다.

| 경계 | 유지한 원본 edge | 운영 중간 후보 interval/fraction | 검토 영역 호길이 |
|---|---|---|---:|
| R A2/A3 | FJ1699:e1 | 24 / 약 1.0 | 4.896467 mm |
| L A2/A3 | FJ1699M:e0 | 232 / 0.288675 | 5.174144 mm |
| R A3/A4 | FJ1699:e1 | 127 / 0.683503 | 12.187764 mm |
| L A3/A4 | FJ1699M:e0 | 127 / 0.869989 | 12.363517 mm |

실제 contour에서 rostrum–genu와 superior genu–body 전환은 연속적인 곡선이다. 기존 지형 정의를 유지할 때 단일 seam이나 주석 vertex가 없어 네 영역을 유일하게 더 좁히지 못했다. 최대 곡률이나 임의 기울기 임계값을 새 해부학 기준으로 도입하지 않았다. 운영 중간 plane과 양 끝 candidate, 원래 범위 및 실제 뇌량 contour 전부를 JSON에 보존했다. 영역 크기는 검토자가 정한 범위이고 통계적 불확실성이 아니다.

## 재현과 한계

Docker에서 `PYTHONPATH=src python scripts/inspect_aca_boundary_resolution.py` 실행. [검사 JSON](evidence/aca-boundary-resolution.json)은 원본 ZIP·8개 OBJ·중심선·이전 두 보고서·그림 hash를 포함한다. 입력 불변 검사도 수행했다.

그림: `exports/aca-boundary-resolution/acom-intersection-anchors.png`, `callosal-transition-regions.png`. 실제 생성 그림을 열람해 교차점 cloud·polyline 후보와 뇌량 지형의 관계를 확인했다.

새 운영 후보는 구간 라벨 정답이나 임상적 경계 승인으로 적용하지 않았다. 독립 검토자 일치도·환자 대조·내강 접합 검증은 NOT RUN이다. 새로운 문헌 기준은 도입하지 않고 [기존 검토의 지형 정의](ACA_BOUNDARY_REVIEW.md)를 유지했다.
