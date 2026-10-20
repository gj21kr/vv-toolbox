# Atlas 연결 추가 검증 — 2026-10-20

## 판정

- 데이터 참조 무결성: **PASS** (아래 명시한 검사 범위).
- 양쪽 끝 표시를 실제 해부학적 연결도로 해석: **FAIL**. 중간부 부착 후보가 끝점 영역으로 묶이고, 후보 수 제한이 있다.
- 개별 후보의 실제 내강 연결: **UNKNOWN**. 가까운 중심선·표면 정점은 내강 연결의 증거가 아니다.
- 브라우저 재검증: **NOT RUN**. 이번 실행에서 8093 서버는 연결 거부 상태였다. 이전 화면 검증과 구분한다.

## 재현 범위

고정 해시를 검증하는 `load_atlas()`로 원본을 읽고, 현재 코드의 smoothing 및 proximity 계산을 다시 실행했다. 기존 추출 캐시는 현재 알고리즘과 형상 해시로 검증해 재사용했다. 원본 Atlas 805개만 포함하며, 추정 목 연결 5개와 사용자 변형은 제외했다. 따라서 이전 화면의 radius_scale=0.5인 FJ1692와 정확히 같은 장면은 아니다.

선택 혈관: **FJ1718**, trunk of inferior terminal branch of right middle cerebral artery.

805개 중 804개 추출, 1개 미해결. 중심선 edge 1,679개, 후보 link 2,316개. 그래프 JSON SHA256: `4c5bb8f0aa8aa688b2fb59abd526e1dded9c6d6d0634c6cc79b33697b00b05ee`.

검사한 edge 끝점 ID, 점/반지름 개수, link의 source-node 및 target-edge 존재와 소유 혈관 일치에서 오류 0건. 끝점/분기 영역에 배정되지 않은 link를 가진 part 0개. anchor가 없는 part 1개, 후보가 비어 있는 anchor 영역 1,038개. 이 수치는 해부학적 말단 개수가 아니다.

## 중요한 발견

### 1. 끝점 영역은 실제 부착 위치가 아니다

현재 `endpointNeighborhood()`는 자기 혈관 내부의 degree-1 또는 degree>2 노드까지의 경로 거리로 모든 후보를 배정한다. 외부 혈관이 자기 혈관 중간에 접근해도 새로운 분기 노드를 만들지 않는다.

FJ1718에서 다음 incoming 후보가 모두 End region 2에 묶였다. 비율은 선택 중심선 n0에서 n1까지의 길이 기준이며 혈류 방향이 아니다.

| 후보 | 선택 혈관에서 부착 후보 위치 | 가장 가까운 선택 끝점까지 경로 거리 |
|---|---:|---:|
| FJ1729 측두후두분지 | 54.8% | 10.538 |
| FJ1712 측두극동맥 | 74.4% | 5.965 |
| FJ1664 중심고랑동맥 | 76.5% | 5.483 |
| FJ1694 섬엽부 MCA | 92.8% | 1.685 |

FJ1729는 특히 끝점 자체의 관계로 표시하기 어렵다. 이를 고치려면 실제 부착 후보 위치를 따라 **끝점–중간부 후보–끝점**으로 보여주고, 아직 검증되지 않은 후보를 확정 분기 노드와 구분해야 한다.

### 2. 후보 생성 자체가 전체 이웃을 보장하지 않는다

`proximity_links()`는 같은 layer에서 반지름 기반 gap proxy가 2 이하인 후보를 찾은 뒤, 각 source 끝점에서 가까운 **최대 3개**만 남긴다. 반대 방향으로 생성된 link도 UI가 읽지만, 이 제한 때문에 전체 branch를 빠짐없이 복원했다고 주장할 수 없다. 임의로 모든 후보를 연결하면 오연결도 늘어나므로 후보 수 제한과 실제 연결 판정은 별도로 다뤄야 한다.

### 3. 근접성과 문헌 대응은 별도 증거다

| 후보 ID | 원본 이름 | 최소 정점 간 거리 | 검토 판단 |
|---|---|---:|---|
| FJ1659 | right anterior temporal artery | 0.038 | 근접; 개별 연결 미확인 |
| FJ1669 | artery of right precentral sulcus | 0.109 | 대표적인 상부 줄기 분포와 달라 우선 검토 |
| FJ1692 | sphenoid part of right MCA | 0.140 | 등록된 문헌 관계 대응 후보; 위치/내강 미확인 |
| FJ1694 | insular part of right MCA | 0.107 | 근접; 개별 branch 역할 미확인 |
| FJ1712 | right polar temporal artery | 0.172 | 중간부 후보; 조기 분기 변이 고려 |
| FJ1729 | temporo-occipital branch of right MCA | 0.148 | 중간부 후보; 끝점 관계로 해석 불가 |
| FJ1660 | insular part of right MCA | 1.456 | 근접 증거가 상대적으로 약함; 검토 필요 |
| FJ1664 | artery of central sulcus | 2.314 | 대표 분포와 다르고 gap proxy도 양수; 우선 검토 |

단위는 원본 Atlas 단위(mm 가정)다. 최소 정점 거리는 표면 샘플링에 의존한다. 큰 값도 삼각형 표면의 분리 증명이 아니며, 작은 값도 접합이나 내강 연속성의 증명이 아니다. 삼각형 교차·내강 연속성·접합면은 이번에 검사하지 않았다. FJ1669는 표면 정점은 가깝지만 해부학적 관계가 자동으로 확정되지 않는 대표 사례다.

## 문헌 대조

[Rakshith et al., Microsurgical Anatomy of Middle Cerebral Artery in Northwest Indian Population](https://pmc.ncbi.nlm.nih.gov/articles/PMC11588606/)의 type 1 패턴은 precentral/central 동맥을 superior trunk에서, temporal 계열과 angular 동맥을 inferior trunk에서 기술한다. 이 대표 패턴을 기준으로 FJ1669/FJ1664를 **검토 우선순위**로 지정했다. 해당 Atlas 표본의 변이를 증명하거나 배제한 것이 아니다.

[Gibo et al., 1981](https://pubmed.ncbi.nlm.nih.gov/7452329/)의 M1–M4는 지형적 구분이다. M2라는 이름이 같다는 이유만으로 동일한 branch나 분기점을 확정할 수 없다.

[Tanriover et al., early MCA branches](https://pubmed.ncbi.nlm.nih.gov/12816276/)는 조기 temporal/frontal 분기의 다양성을 보고한다. 따라서 temporal 이름만으로 반드시 inferior trunk의 daughter라고 확정하지 않는다. 이번 문헌 확인은 공개 초록·검색 가능한 본문 범위이며 새로운 표본 주석 검증이 아니다.

## 실행 검증

Python 3.12 Docker 컨테이너에서 현재 전체 pytest: **200 passed, 3 skipped**, 289 deprecation warnings. NumPy 2.5와 scikit-image 사이의 shape 설정 경고가 포함됐다. skip 3개는 컨테이너에 Node가 없어 실행하지 못한 UI 검사이며 PASS로 집계하지 않았다. 호스트 Python 테스트는 실행하지 않았다.

현재 UI의 실제 `endpointNeighborhood()` 함수를 Node에서 원본 전체 그래프에 적용해 배정과 참조를 검사했다. 이는 브라우저 렌더링 테스트를 대신하지 않는다. `git diff --check` PASS.

재현 도구:

- `scripts/audit_atlas_geometry.py`: 의존성 컨테이너에서 원본 그래프 및 정점 거리 산출.
- `scripts/audit_endpoint_connections.cjs`: 실행 중 API 또는 저장 그래프를 읽는 무변경 검사.
- `exports/connection-audit/source-graph.json`, `geometry.json`, `endpoints.json`: 로컬 결과, Git 제외.

## 다음 수정의 검증 기준

1. 양 끝점과 중간 부착 후보를 구분하고 실제 중심선 위치 순서로 배치.
2. 후보 개수 제한으로 누락될 수 있음을 공개하고, 전체 후보와 검토된 관계를 별도 보관.
3. 표면 접합/교차, 접선 방향, 내강 연속성 및 출처 개념을 함께 평가. 문헌만으로 표본 연결을 확정하지 않음.
4. 수동 확인된 관계에만 confirmed 상태를 부여하고 수정 전후 원본 근거를 보존.

이번 작업은 검증과 재현 스크립트 추가이며, 미확인 관계를 삭제하거나 새로운 연결 형상을 생성하지 않았다.
