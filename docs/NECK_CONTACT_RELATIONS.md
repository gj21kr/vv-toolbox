# 목 연결 사례의 접촉 후보와 해부학적 관계

검사 입력은 `centerline-regularized-neck.json`의 보정 전후 동일한 **17개 edge 쌍**이다. `scripts/inspect_neck_contact_relations.py`가 snapshot revision, 기존 capsule witness의 거리·반경, 17쌍의 일치를 검증하고 [검사 JSON](evidence/neck-contact-relations.json)을 생성한다. 원본·합성 graph·앱은 수정하지 않는다.

**일반적 reference 관계 13쌍, 직접 관계 미확인 4쌍, 실제 Atlas 내강 접합 확정 0쌍**이다. 13쌍 중 한 쌍은 직접 부모–자식이 아니라 같은 부모에서 갈라지는 두 분지이다. 이 분류는 충돌 해소나 연결 승인 결과가 아니다.

## 근거와 한계

기존 `atlas_topology.py`의 ICA 말단 분기, PCom 기시, 대동맥궁–좌 CCA reference를 사용했다. source 이름과 reference member를 대조했으며 source graph의 연결로 승격하지 않았다.

추가로 확인한 일차 연구:

- Gibo, Lenkey, Rhoton, 1981, [Microsurgical anatomy of the supraclinoid portion of the internal carotid artery](https://pubmed.ncbi.nlm.nih.gov/7277004/), DOI 10.3171/jns.1981.55.4.0560. 50개 성인 사체 대뇌 반구의 미세해부 연구로 ICA에서 안동맥·PCom·전맥락동맥이 나오는 관계를 기술한다. 이 연구는 본 Atlas의 접합 좌표나 변이를 확정하지 않는다.
- [Morphometry of the Brachiocephalic Artery: A Cadaveric Anatomical Study](https://pmc.ncbi.nlm.nih.gov/articles/PMC7505533/), 2020. 사체 연구에서 팔머리동맥의 분기를 우 CCA·우 쇄골하동맥으로 추적한다. 따라서 두 딸분지 간 근접을 직접 CCA→쇄골하동맥 연결 근거로 사용하지 않는다.

FJ1662/FJ1663 및 좌측 대응 요소는 source 이름이 `anterolateral central branch of ... middle cerebral artery`이다. 이 네 edge의 ICA 접촉은 **source 명칭의 부모와 접촉 대상이 다르다는 검사 결과**이다. ICA 기시 변이가 불가능하다는 주장이 아니며, source mesh와 실제 MCA 기시를 확인할 때까지 직접 연결을 미확인으로 둔다.

## 전체 17쌍의 위치

`M`은 해당 원본 ID의 좌측 요소이다. 아래 수치는 **처음 검출된 capsule witness**에서 시작/끝까지의 중심선 arc 거리(mm)이다. 전체 edge 간 최단점, 최적 접합점, 혈류 방향이 아니다. endpoint는 거리 1e-7 mm 이내의 정확한 추출 끝점이며, 0.1 mm 떨어진 점도 internal로 기록한다. near-end를 임의 허용값으로 endpoint로 승격하지 않는다.

| Edge A / B | Reference 관계 | A 시작/끝 거리 | B 시작/끝 거리 |
|---|---|---:|---:|
| FJ1654:e0 / FJ1682:e0 | ACA–ICA 말단 | 0 / 24.93 | 127.45 / 4.11 |
| FJ1654M:e0 / FJ1682M:e0 | ACA–ICA 말단 | 22.36 / 4.52 | 3.75 / 127.81 |
| FJ1658:e0 / FJ1682:e0 | 전맥락동맥–ICA | 64.00 / 1.65 | 124.09 / 7.48 |
| FJ1658M:e0 / FJ1682M:e0 | 전맥락동맥–ICA | 0 / 64.09 | 5.70 / 125.86 |
| FJ1662:e12 / FJ1682:e0 | 직접 관계 미확인 | 1.36 / 3.72 | 128.25 / 3.31 |
| FJ1662M:e2 / FJ1682M:e0 | 직접 관계 미확인 | 0.64 / 3.32 | 2.95 / 128.60 |
| FJ1663:e1 / FJ1682:e0 | 직접 관계 미확인 | 10.64 / 0.29 | 126.66 / 4.91 |
| FJ1663M:e1 / FJ1682M:e0 | 직접 관계 미확인 | 0 / 11.19 | 3.75 / 127.81 |
| FJ1682:e0 / FJ1692:e0 | ICA–M1 말단 | 127.45 / 4.11 | 36.40 / 0 |
| FJ1682:e0 / FJ1695:e0 | ICA–안동맥 | 115.30 / 16.26 | 0.26 / 59.77 |
| FJ1682:e0 / FJ1713:e0 | ICA–PCom | 119.18 / 12.38 | 0.10 / 14.88 |
| FJ1682M:e0 / FJ1692M:e0 | ICA–M1 말단 | 0.36 / 131.20 | 0 / 36.92 |
| FJ1682M:e0 / FJ1695M:e0 | ICA–안동맥 | 10.99 / 120.56 | 61.60 / 0.90 |
| FJ1682M:e0 / FJ1713M:e0 | ICA–PCom | 6.27 / 125.29 | 14.40 / 0.55 |
| FJ3411:e0 / FJ3483:e0 | 궁–좌 CCA | 21.30 / 64.98 | 0 / 66.08 |
| FJ3417:e0 / FJ3564:e0 | 팔머리동맥–우 CCA | 0 / 43.21 | 29.31 / 13.17 |
| FJ3564:e0 / FJ3579:e0 | 같은 부모의 두 분지 | 32.62 / 9.85 | 81.97 / 1.39 |

각 행의 정확한 좌표, interval index/fraction, source part ID·이름·OBJ 식별근거, 보정 전후 witness를 JSON에 보관했다. 보정 후 witness가 다른 interval에 잡힐 수 있으므로 위 arc 거리는 **보정 전 source 파생 중심선**에만 적용한다.

## 합성 graph 후속 명세

1. **좌 대동맥궁–CCA:** FJ3483:e0의 start와 궁 FJ3411:e0의 내부를 먼저 단면으로 대조한다. 접합이 확인되면 별도 합성 궁 edge를 해당 주석 위치에서 둘로 나누고 공통 junction을 만든다. 현재 witness의 궁 station 21.30 mm를 승인 좌표로 사용하지 않는다.
2. **우 팔머리동맥 분기:** FJ3417:e0, FJ3564:e0, FJ3579:e0을 함께 검토한다. 우 CCA의 접촉점은 endpoint가 아니라 내부(끝까지 13.17 mm)이다. 단순 endpoint 병합이나 CCA–쇄골하동맥 직접 bridge를 만들지 않는다. 세 원본 표면의 공통 내강과 중심선 추출 tail을 먼저 판독한 뒤 각 합성 edge의 끝점 정합/내부 split 여부를 결정한다.
3. **양측 ICA 말단:** ACA와 M1의 서로 다른 witness를 각각 독립 접합으로 만들지 않는다. ICA–ACA–M1 세 표면을 공동 판독해 하나의 말단 분기인지 확인한다. 우측 ICA의 두 witness는 모두 끝에서 약 4.11 mm 떨어져 있고, 좌 ACA witness는 끝에서 4.52 mm 떨어져 있다. 추출 tail을 삭제하거나 접합을 이중 생성하기 전에 주석을 확정해야 한다.
4. **ICA 측분지:** 안동맥·PCom·전맥락동맥의 실제 기시를 확인하면 ICA를 기시 arc 순서대로 분할하는 후보이다. 분지 쪽 witness가 내부인 경우 추출 tail 처리까지 별도 명시해야 한다. JSON `proposed_internal_split_edge_ids`는 검토 대상 목록이며 자동 실행 명세가 아니다.
5. **MCA 이름의 네 edge:** ICA split 후보에서 제외했다. 해당 source part 전체와 M1/M2 측 기시를 추적하고, 단순 근접·분류 오류·표본 변이 중 어느 것인지 미확인으로 유지한다.

합성 split 구현 시 source hash·edge interval·주석 revision을 고정하고, 원본 보존, 양끝/접합 반경·방향, graph incidence, source/synthetic 라벨 및 다시 수행한 clearance를 함께 검증한다. 접촉 후보가 사라지더라도 내강 접합 승인으로 해석하지 않는다.

## 실행 확인

Docker `vv-annotation-ui`, `PYTHONPATH=src`에서 검사 스크립트가 17쌍 모두의 입력 revision과 capsule witness 수치를 확인했다. 같은 환경의 `tests/test_geometry_quality.py`는 **26 passed / 49 warnings**였다. 이는 거리 계산 회귀 검사이며 본 문서의 해부학적 분류를 자동 검증한 결과가 아니다. 스크립트는 snapshot·topology 파일을 읽기만 하며 출력은 이 검사 JSON 하나이다.
