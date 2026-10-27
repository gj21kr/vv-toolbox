# MCA 지형 경계 검토

검사일: 2026-10-20. 좌표: `bodyparts3d_native_LPS`, mm. 원본 형상 보존.

## 검사 범위와 결과

좌우 M1/M2, M2/M3, M3/M4 **6개 경계군**에 대해 60개 원본 OBJ를 검사했다. MCA zone/branch와 MCA 명칭으로 연결된 46개 혈관 요소, 좌우 각각 7개 insula·피질 배경 요소다. inferior terminal trunk FJ1718/M도 포함한다. 이 요소는 단순 `branch of middle cerebral artery` 상위 개념 검색만으로는 누락되므로 MCA 이름 대응을 함께 사용했다.

46개 혈관 요소 모두 로컬 preview 중심선에 대응하며 총 120개 edge가 있다. 이 수는 해부학적 분지 수가 아니다. 예를 들어 FJ1662 한 요소에 14개 추출 edge가 있어, skeleton edge를 곧바로 독립 M2/M3 분지로 간주할 수 없다. JSON은 각 원본 요소별 edge ID, 양 끝 좌표, insula 정점 거리 범위를 기록한다. 이 중심선은 원배포 주석이 아닌 파생 preview이며 해부학적 경계 판정에 대한 독립 근거가 아니다.

이번 검사에서 **주변 opercular 피질 형상은 실제로 존재함**을 확인했다. 별도 `operculum` 이름이 없다는 이유만으로 배경 자료가 없다고 판단하면 안 된다. 다만 혈관과 배경 피질의 3개 직교 투영만으로 각 혈관의 circular sulcus 통과와 Sylvian 출구를 유일하게 지정하지 못했다. 승인 경계 좌표는 0개이며, 각 군의 `position=null`을 유지한다.

## 실제 확인한 배경 형상

| 지형 | 우측 | 좌측 |
|---|---|---|
| Insula | FJ1749 | FJ1748 |
| Inferior frontal gyrus | FJ1745 | FJ1744 |
| Precentral gyrus | FJ1801 | FJ1800 |
| Postcentral gyrus | FJ1798 | FJ1797 |
| Supramarginal gyrus | FJ1842 | FJ1841 |
| Anterior superior temporal gyrus | FJ1838 | FJ1837 |
| Posterior superior temporal gyrus | FJ1840 | FJ1839 |

원본 정점·면 검사와 SHA-256 기록 PASS. 위 표는 독립 operculum 주석이 아니라 해당 영역을 덮는 gyrus 형상 목록이다. 투영에서 inferior frontal과 superior temporal 사이를 지나는 여러 혈관, insula 위의 후방 주행 및 상방 피질 분지를 관찰했다. 여러 깊이의 gyri가 겹쳐 보이고 혈관이 요소 내부에서 여러 구간을 지나므로, 하나의 요소 끝이나 한 평면을 모든 분지에 적용할 수 없다.

## 경계군별 판정

| 경계군 | 검사한 경로와 추가 근거 | 현재 판정·정확한 잔여 작업 |
|---|---|---|
| B.R.MCA.M1_M2 | FJ1692 → FJ1660/FJ1694 및 FJ1718, FJ1749·FJ1745·FJ1838 배경 | 원자료 요소 접촉 탐색점 2개. 두 named insular 요소 입구가 한 점으로 일치하지 않는다. 각 실제 daughter 경로의 genu를 절단·회전 3D에서 판독해야 한다. |
| B.L.MCA.M1_M2 | 대응 M 요소와 FJ1748·FJ1744·FJ1837 | 동일하게 2개 탐색점. 좌우 형상이 유사하다는 이유로 우측 판정을 복사하지 않는다. |
| B.R.MCA.M2_M3 | 23개 우측 혈관 요소, insula와 frontal/parietal/temporal gyri | 분지별 insular 주행·opercular 전환 존재를 탐색할 배경은 확보. 각 분지의 sulcus 통과점과 실제 연결 경로 미판정. |
| B.L.MCA.M2_M3 | 23개 좌측 요소와 동일 종류의 좌측 배경 | 위와 같음. 단일 insula bounding box 이탈점을 anatomical boundary로 사용하지 않는다. |
| B.R.MCA.M3_M4 | 우측 cortical branch를 주변 6개 gyrus와 대조 | 표면 가까운 말초 주행은 관찰되나 opercular 주행 종료와 피질 출구를 개별적으로 지정하지 못함. 전체 gyrus의 최근접 표면은 출구 판정이 아님. |
| B.L.MCA.M3_M4 | 좌측 cortical branch와 주변 6개 gyrus | 위와 같음. 조기 temporal branch가 모든 M2/M3 구간을 반드시 지나는 것으로 강제하지 않는다. |

## 탐색 좌표

아래 좌표는 named source-part 표면 최근접 정점쌍의 한쪽 위치다. **genu, 중심선 접합점 또는 승인된 구간 경계가 아니다.** `inspection_locators`에만 저장한다.

| 경계군 | 분지 후보 | [X,Y,Z] mm | 정점 간 거리 mm |
|---|---|---|---|
| 우 M1/M2 | FJ1660 | [-38.6689,-108.554,1544.52] | 0.129852 |
| 우 M1/M2 | FJ1694 | [-44.0721,-104.794,1547.8] | 0.021757 |
| 좌 M1/M2 | FJ1660M | [38.6689,-108.554,1544.52] | 0.129852 |
| 좌 M1/M2 | FJ1694M | [44.0721,-104.794,1547.8] | 0.021757 |

23쌍 혈관의 우측 정점을 X 반사한 뒤 좌측 정점에 비교했다. 모든 쌍에서 방향성 최대 최근접 정점 거리가 0.348 mm 이내였다. 이는 매우 유사한 좌우 형상이라는 관찰이며 독립적인 좌우 표본 검증이나 제작 과정의 증명은 아니다. 좌우 일치만으로 경계 신뢰도를 높이지 않는다.

## 재현 및 다음 판정 조건

- 스크립트: `scripts/review_mca_boundaries.py`.
- 추적 근거: [mca-boundary-review.json](evidence/mca-boundary-review.json). 60개 OBJ 해시·범위, 46개 요소별 120개 파생 edge, 4개 탐색점, 6개 군별 미확인 상태 포함.
- 그림: `exports/mca-boundary-review/R-context.png`, `L-context.png`. XY/XZ/YZ 투영이며 정점·면에서 직접 렌더링. 로컬 산출물; 원본 데이터·그림은 Git에 추가하지 않는다.
- 실행: Docker `python:3.12-slim`, NumPy/SciPy/Matplotlib. 원본 archive fingerprint 일치 및 정점·면 범위 검사 PASS. 임상·독립 영상 검증 NOT RUN.
- 다음 판정은 선택 분지를 주변 피질과 함께 회전/절단하고 근위→원위로 추적하여, genu·sulcus·피질 출구 각각에 landmark 영역과 혈관 위 위치를 함께 저장해야 한다. 단지 기존 annotation이 없다는 이유로 수동 판독을 금지하지 않지만, 이번 투영 검사만으로 승인할 근거는 부족하다.

## 문헌 정의 확인

[Rakshith et al., 2024 원연구](https://pmc.ncbi.nlm.nih.gov/articles/PMC11588606/) Methods 및 Observations에서 M1 origin–genu, limen에서 circular sulcus까지 M2를 기술하며, cortical branch가 opercular cleft를 돌아 convexity로 진행하는 관계를 제시한다. 해당 일반 정의를 BP3D 요소 끝점과 동일시하지 않는다. 문헌의 수치는 본 표본의 경계 오차 허용치로 사용하지 않았다.
