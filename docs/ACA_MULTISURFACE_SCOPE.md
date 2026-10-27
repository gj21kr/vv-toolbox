# ACA 분기부의 표면 범위 검사

기준 사례 `sample:FJ1654:e0:77`의 분기 입력은 ACA 두 구간과 `declared-link:21`이다. 추정 연결의 anchors는 `FJ1654:e0`의 77번 표본과 `FJ1655:e0`의 0번 표본이다. 현재 사례의 edge 및 surface part 목록에는 FJ1690이 없다. source ID 목록의 `bp3d`는 archive 출처이며 개별 혈관 대응을 뜻하지 않는다.

기존 `build_source_sac_union`은 명시한 원본 ACA 하나와 dome을 결합한다. 단일 닫힌 체적 검사만으로 ACom 및 주변 분지와의 연결 내강이 생성됐다고 해석할 수 없다. FJ1690 접촉을 허용된 분기 접합으로 자동 재분류하지 않는다.

## 명시적 세 표면 결합 실험

`scripts/inspect_aca_multisurface_union.py`는 FJ1654·FJ1655·FJ1690을 명시적으로 선택해 원본 세 표면의 합집합과 ACA 동맥류 후보를 포함한 합집합을 비교한다. 입력 archive·후보 해시를 확인하고 원본의 좌표 보존 인덱스 정규화 후 닫힌 방향성 표면 조건을 검사한다. Manifold 3.5.4를 사용하며 좌표를 국소 원점으로 옮겨 계산 후 복원한다.

[실행 기록](evidence/aca-multisurface-union.json):

- 결과: 닫힌 체적, 연결 성분 1개.
- 원본 세 표면 합집합: 240.327829 mm³.
- 동맥류 포함 합집합: 276.564262 mm³.
- Boolean 차집합으로 측정한 제거 체적: 8.26596e-8 mm³.
- 추가 체적: 36.236434 mm³.

제거량은 0이 아니며 사전 허용 기준을 정하지 않았으므로 체적 보존 PASS로 표시하지 않는다. 이 실험은 표면 결합 가능성 확인이며 해부학적 결합 근거, 분지 통로, 자기 접촉, 주변 간섭 검사는 미완료다. Boolean은 면을 다시 나누므로 원본 face의 정확한 좌표·면 ID 보존 방식과 구분한다. 원본 Atlas와 앱은 변경하지 않았고 생성 수용은 false다.

다음 단계는 명시적 혈관별 대응과 연결 근거 확인, 합집합의 분지 통로·단면 보존 및 주변 혈관 검증이다. 근거 없이 모델에 이웃 혈관을 추가해 충돌을 제거한 것으로 처리하지 않는다.

## 문헌 관계와 Atlas 명칭 대조

현재 Atlas 명칭은 FJ1654 `right anterior cerebral artery`, FJ1655 `anterior communicating artery`, FJ1690 `right medial frontobasal artery`다.

- [Avci 등, 2003, DOI 10.2176/nmc.43.329](https://www.jstage.jst.go.jp/article/nmc/43/7/43_7_329/_pdf): 원문 329–330쪽을 확인했다. 31개 사체 뇌, 62개 반구의 해부 연구에서 OFA는 A2에서 기시했으며 ACom에서의 거리는 2.61–8.22 mm, 평균 5.96 mm로 보고됐다. 이 표본 집단의 결과를 모든 사람의 고정 규칙이나 Atlas의 좌표로 사용하지 않는다.
- [The Microsurgical Anatomy of the Orbitofrontal Arteries, 2016](https://pubmed.ncbi.nlm.nih.gov/26875657/): 검색에서 제공된 초록과 [출판사 초록](https://www.sciencedirect.com/science/article/abs/pii/S1878875016002369)은 orbitofrontal/frontobasal 명칭 및 내측 분지가 ACA, 외측 분지가 MCA에서 나오는 관계를 설명한다. PubMed 직접 열기는 본문이 없는 응답이었으며 이 연구의 전문을 확인했다고 표시하지 않는다.

따라서 FJ1690–FJ1654는 문헌상 가능한 부모–분지 관계로 등록할 근거가 있다. 다만 이름 대응과 일반적인 관계는 이 표본의 ostium 위치, A2 경계, 실제 열린 통로를 증명하지 않는다.

`atlas_topology.reference_junctions`에 좌우 ACA–medial frontobasal 관계를 추가했다. `literature_reference`, `specimen_status=unverified`, `position=null`을 유지하며 공간 접촉 후보만 분류한다. 반대편 혈관으로 연결하거나 형상을 합치지 않는다. [관련 검사 10개 PASS](evidence/orbitofrontal-reference-tests.xml). 이는 관계 생성 코드의 검증이며 실행 중인 브라우저 반영 검증은 별도다.

## 기존 결합 검증 경로 적용

`scripts/inspect_aca_multisurface_checked.py`는 기존 `solid_union.build_solid_union`을 사용한다. 64비트 Manifold 입력과 원본 면 출처를 유지하며, 입력 세 표면과 결과의 자기 접촉, 양의 닫힌 체적, 단일 경계 성분을 검사한다. [실행 기록](evidence/aca-multisurface-checked.json)은 CANDIDATE이며 자기 접촉 검사에서 접촉은 검출되지 않았다. 앞선 직접 Boolean 실험과 구분되는 새 형상을 `exports/aca-multisurface-checked.npz`에 저장했다.

`scripts/inspect_aca_checked_context.py`는 저장 해시를 확인하고 출력 면이 선언한 입력 삼각형에 속하는지 기존 lineage 검사로 대조했다: **PASS**. 여기서 ACA 입력은 원본에 dome을 붙인 후보이며, 그 후보까지의 출처 추적과 원본 Atlas 면까지의 추적을 혼동하지 않는다.

[전체 동맥 문맥 검사](evidence/aca-checked-context.json)는 포함된 세 표면을 제외한 **515개**를 빠짐없이 비교했다. 표면 접촉이 없는 인접 조합에는 기존 disjoint containment 검사도 적용했다.

- 최종 문맥 판정: **UNKNOWN**.
- 접촉 7개: FJ1654M, FJ1662, FJ1676, FJ1682, FJ1692, FJ1695, FJ1699.
- 검사 미확정 1개: FJ1699M.

위 목록은 절대 문맥 검사이며 새 접촉 목록이 아니다. 원본의 합당한 접합인지 또는 문제가 되는 겹침인지 아직 승인하지 않았다. 분지 통로·단면 보존은 NOT RUN이며 앱 적용과 생성 수용은 false로 유지한다.

## 원본 중심선 단면의 결합 전후 비교

`scripts/inspect_aca_branch_sections.py`는 원본 전체 동맥 사례의 해시와 Atlas archive를 확인하고 세 part의 추출 중심선 5개를 사용한다. 각 경로의 양 끝점을 제외한 모든 위치에서 동일한 이전–다음 표본 방향의 평면으로 원본 개별 표면과 결합 후보를 비교한다. 일부 통과 지점만 선택하지 않는다.

[실행 기록](evidence/aca-branch-sections.json): 내부 표본 총 327개 중 320개에서 양쪽 모두 중심점을 감싸는 유일한 폐곡선을 측정했다. 나머지 7개는 FJ1690:e0에 있으며 원본과 결과 모두 UNKNOWN이다. ACA 46개·ACom 22개는 모두 측정됐고 FJ1690의 세 경로는 각각 40/47, 70/70, 142/142개가 측정됐다. 원본에서 측정되던 표본이 결과에서 UNKNOWN으로 바뀐 경우는 없다.

단면 면적 변화는 표본별 기록에 보존했다. 합집합과 dome 때문에 면적이 증가하는 단면도 있어 이를 원래 분지 단면과 동일하다고 볼 수 없다. 끝점, 표본 사이의 연속 통로, 7개 미확정 위치 및 단면 윤곽 보존은 미검증이다. 따라서 전 분지 개통 PASS나 생성 수용으로 승격하지 않는다.

## 전체 중심선 구간 포함 검사

`scripts/inspect_aca_branch_paths.py`는 같은 5개 추출 경로를 자르거나 이동하지 않고 기존 적응적 구간 포함 검사에 전달한다. 첫·마지막 구간을 포함하며, 내부점의 표면 거리와 구간 길이로 전체 구간을 덮거나 외부 지점을 기록한다. 고정 표본 검사보다 넓은 범위지만 부동소수점 계산과 유효한 폐곡면 가정에 의존한다.

[실행 기록](evidence/aca-branch-paths.json):

| 경로 | 원본 | 결합 후보 | 외부 증거점 수(원본/후보) |
|---|---|---|---:|
| FJ1654:e0 | PASS | PASS | 0 / 0 |
| FJ1655:e0 | PASS | PASS | 0 / 0 |
| FJ1690:e0 | FAIL | FAIL | 8 / 8 |
| FJ1690:e1 | PASS | PASS | 0 / 0 |
| FJ1690:e2 | PASS | PASS | 0 / 0 |

단면 UNKNOWN 7개가 있던 FJ1690:e0은 원본부터 외부 경로 구간이 있는 추출 중심선이다. 이 실패를 결합 후 새로 발생한 폐색으로 해석하지 않는다. 후속 수정은 원본 표면을 보존한 별도 중심선 후보에서 수행하고, 경로를 잘라 실패 구간을 제외하지 않는다. 반경을 가진 통로와 분지 접합을 통과하는 경로는 별도 검사 대상이다.
