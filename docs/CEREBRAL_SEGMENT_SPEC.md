# 뇌혈관 구간 및 접합점 명세

버전: 0.1 · 작성일: 2026-10-20 · 대상: VV-REQ-002/003/004/006/011

상위 문서: [개발계획서](DEVELOPMENT_PLAN.md) · 입력 조사: [로컬 자료](LOCAL_SOURCE_INVENTORY.md), [TopCoW](TOPCOW_SOURCE_INSPECTION.md)

상태: 문헌 기반 주석·데이터 설계. 개별 표본의 경계 좌표 판정 및 앱 적용은 NOT RUN.

## 1. 분류 원칙

좌우 ACA A1–A3와 MCA M1–M3를 대상으로 **해부학적 지형 기준**을 사용한다. `segmentation_scheme`은 필수이며 ACA는 `aca_five_segment_topographic_v1`, MCA는 `mca_topographic_v1`로 기록한다. 구간, 실제 분기, 원자료 파일 경계는 별개 객체다. MCA의 주 분기점이 곧 M1/M2 경계라는 규칙을 사용하지 않는다. 혈관조영과 미세해부학의 M1 정의 차이는 원연구 [S2]가 지적한다. 다른 정의로 작성된 자료는 `source_scheme`을 보존하고 대응 상태를 기록한다.

목표는 12개 좌우 구간 클래스이며, 12개의 튜브나 12개 그래프 edge로 제한하지 않는다. 한 구간에 여러 분지·여러 edge가 존재할 수 있다. ACom은 좌우 ACA를 연결하는 별도 구조이며 `side=midline`이다. 좌우 부착점은 구별하지만 ACom 자체를 임의의 left/right 혈관 두 개로 복제하지 않는다.

## 2. 구간 경계

| 구간 | 근위 경계 | 원위 경계 | 주석 시 필요한 근거 |
|---|---|---|---|
| ACA A1 | ICA 말단의 ACA 기시 | 동측 ACom 접합 | ICA 분기와 ACom 부착 위치 |
| ACA A2 | 동측 ACom 접합 | 뇌량 rostrum–genu 이행부 수준 | 혈관과 뇌량의 공간 관계 |
| ACA A3 | A2 원위 경계 | genu를 돌아 뇌량 상면의 A4 주행으로 이행 | genu 주변 굴곡 및 뇌량 상면 |
| MCA M1 | ICA 말단의 MCA 기시 | limen insulae의 MCA genu | insula 지형과 혈관 주행 |
| MCA M2 | limen insulae의 genu | circular/limiting sulcus에서 operculum으로 이행 | 각 분지의 insular 주행과 경계 |
| MCA M3 | M2 원위 경계 | Sylvian fissure 밖 피질 표면의 M4 주행으로 이행 | 각 분지의 opercular 주행과 피질 출구 |

ACA 경계는 [S1], MCA 지형과 분기점 구분은 [S2–S4]를 근거로 한다. 이는 특정 평면 좌표나 고정 길이를 지정한 것이 아니다. 경계는 해당 표본에서 확인해야 한다. 특히 A3 원위 경계에는 사용한 뇌량 landmark와 판정 위치를 함께 보관한다. A3 원위의 운영 기준은 genu 위에서 후방 주행으로 전환하는 지점이며 [S5] 저자 원고에서도 확인된다. 최종 출판본의 해당 문구 대조는 미완료다.

다음은 금지한다.

- 중심선 길이를 3등분하여 A1–A3 또는 M1–M3로 표시하기.
- callosomarginal 기시를 모든 표본의 A2/A3 경계로 고정하기.
- pericallosal이라는 이름을 A3로 일괄 치환하기.
- TopCoW `3rd-A2`를 A3로 변환하기.
- 앞쪽 분기·좌우 위치만으로 superior/inferior division을 결정하기.
- 원자료의 잘린 끝을 해부학적 말단으로 표시하기.

MCA 분기가 genu보다 앞에 있으면 분기 이후에도 M1 구간이 존재할 수 있다. 각 daughter의 실제 genu에서 M2로 전환한다. 분기 위치와 구간 전환 위치가 일치할 때만 동일 위치를 공유한다. 지형 기준과 다른 분류를 요구하는 자료는 자동 변환하지 않는다.

## 3. 필수 연결과 범위 경계

아래 표는 기본형의 요구 관계다. 문헌 기반 변이에서는 별도 프리셋이 관계를 명시적으로 바꾼다. 표본의 ACom 결손·A1 결손 등을 기본형에 맞춰 강제로 연결하지 않는다.

| 식별자 패턴 | 참여 구간 | 종류 및 조건 |
|---|---|---|
| `J.{side}.ICA_TERMINUS` | 동측 ICA, ACA A1, MCA M1 | 기본형 말단 분기; accessory/duplicated MCA는 별도 변이 |
| `J.{side}.ACOM_ATTACH` | 동측 A1, A2, ACom | 기본형 문합 접합; ACom은 두 접합점 사이의 edge |
| `B.{side}.ACA.A2_A3` | 동측 A2, A3 | 구간 전환; 분기 없는 경우 degree 2 |
| `B.{side}.ACA.A3_A4` | A3, 범위 밖 A4 | 출력 범위 경계; 실제 혈관 말단 아님 |
| `J.{side}.MCA.DIVISION.{id}` | MCA 주행 및 daughter들 | 표본별 분기; bifurcation만 강제하지 않음 |
| `B.{side}.MCA.M1_M2.{id}` | 같은 경로의 M1, M2 | 각 genu의 구간 전환 |
| `B.{side}.MCA.M2_M3.{id}` | 같은 경로의 M2, M3 | 각 insula–operculum 전환 |
| `B.{side}.MCA.M3_M4.{id}` | M3, 범위 밖 M4 | 각 피질 출구의 범위 경계 |

`side`는 L/R, `{id}`는 지속되는 분지 ID다. 분지 수는 표본에 따라 가변이다. A3와 M3의 모든 확인된 원위 출구를 기록한다. 범위 밖 A4/M4는 경계 메타데이터로 참조하며 전체 형상 생성 의무를 추가하지 않는다.

원자료에서 확인되는 recurrent artery of Heubner, lenticulostriate, callosomarginal, temporal/cortical branch 등의 부착점은 측분지로 보존한다. 이번 기본 연결 표는 이 작은 분지들의 완전한 목록이나 일률적인 기시 구간을 확정하지 않는다. 발견된 미대응 분지는 삭제하지 않고 `unmapped_branch`로 남긴다. 미세 분지 전체의 완성을 기본 경로 완료와 혼동하지 않는다.

그래프는 혈류 방향과 독립인 incidence 관계로 저장한다. 각 접합점은 참여 edge와 각 edge 위 부착 위치를 가진다. 내부 분기에서는 edge를 나누되 같은 해부학적 구간 라벨을 유지한다. ACom 때문에 생기는 순환을 허용한다. 표시에서는 선택 edge 양 끝과 중간 분기 모두 조회하며 이웃 개수를 제한해 원자료를 버리지 않는다.

## 4. 표본별 주석 계약

| 객체 | 필수 필드 |
|---|---|
| 구간 클래스 | `anatomy_key`, `artery`, `side`, `segment`, `scheme_version` |
| 구간 인스턴스 | `instance_id`, `anatomy_key`, `branch_id`, `edge_ids`, `source_refs` |
| 경계 주석 | `boundary_id`, `landmark_type`, `position`, `coordinate_frame_id`, `source_refs`, `evidence_status`, `review_note` |
| 접합점 | `junction_id`, `kind`, `incident_edge_ids`, 각 edge의 `attachment_parameter`, `evidence_refs` |
| 원자료 대응 | source ID/해시, 원본 이름·구간 체계, 대응 유형, 적용 범위, 미확인 사유 |
| 범위 경계 | `reason=out_of_scope`, 계속되는 혈관명, source의 실제 잘림 여부 |

좌표 미확인 시 `position=null`을 사용한다. 0,0,0이나 임의 중간점으로 채우지 않는다. `attachment_parameter`는 정해진 edge 방향의 호길이 비율 [0,1]이며, 이 방향은 혈류·접근 방향을 뜻하지 않는다. 단위 및 좌표 변환이 확인되지 않은 주석은 물리적 위치 확정으로 승인하지 않는다.

근거 상태는 다음처럼 분리한다.

- `name_candidate`: 이름으로 대응시킨 후보, 경계 좌표 미확인.
- `source_annotation`: 원배포 주석, 주석 범위를 그대로 유지.
- `landmark_reviewed`: 해당 표본의 지형·영상에 근거한 경계 주석.
- `cross_source_supported`: 독립 자료가 일반 관계를 뒷받침함. 해당 표본의 위치 확인과 별도 필드.
- `synthetic_estimate`: 합성 보충 위치·연결. 기준 모델 원본에는 적용하지 않음.
- `unresolved`: 필요한 근거 부족, 이유 기록.

원본에 경계가 없는 것과 혈관 자체가 없는 것은 다른 상태다. `not_visible`, `source_truncated`, `extraction_failed`, `anatomically_absent`, `unknown`을 구분하며 마지막 두 상태를 거리만으로 판정하지 않는다.

## 5. 확보 자료 대응

| 자료 | 대응 후보 | 사용 제한 |
|---|---|---|
| BP3D FJ1654 / FJ1654M | 우/좌 ACA A1–A3의 원구조 후보 | 한 요소를 세 구간으로 확정하지 않음. 필요한 landmark 미확보 |
| BP3D FJ1692 / FJ1692M | 우/좌 sphenoid part → M1 후보 | 이름 대응이며 원위 genu 좌표 검수 필요 |
| BP3D FJ1660+FJ1694 / mirror 요소 | 우/좌 insular part → M2 후보 | 각 두 요소를 모두 보존, 지형·연결 대조 필요 |
| BP3D 말초 MCA 요소 | M3 후보 탐색 | 이름만으로 M3 대응 불가 |
| TopCoW label 11/12 | 우/좌 ACA 성분 마스크 | A1–A3 세부 경계 아님 |
| TopCoW label 5/7 | 우/좌 MCA 성분 마스크 | M1–M3 세부 경계 아님 |
| TopCoW A1/ACom 존재 YAML | 사례별 근위 연결 주석 | 부착 좌표·전체 그래프 아님 |
| VMR 0011 | 대동맥궁 접근 구간의 별도 대조 자료 | 뇌혈관 경계의 근거로 사용하지 않음 |

원자료 파일 수준 근거와 해시는 연결된 검사 문서에 있다. 서로 다른 표본의 주석을 동일 모델 좌표에 바로 붙이지 않는다.

## 6. 주석 절차와 수용 기준

1. 표본, 원자료 해시, 좌표·단위 및 필요한 해부학적 배경 구조를 등록한다.
2. ICA 말단과 좌우 ACA/MCA 경로, ACom 주석 유무를 확인한다.
3. 뇌량·insula·operculum landmark로 각 경계를 주석한다. 없으면 unresolved로 남긴다.
4. 분기 위치를 경계와 독립적으로 기록하고 가변 개수의 edge로 구성한다.
5. 자료 잘림과 범위 경계를 구별하고 원본·합성·미확인 표시를 유지한다.
6. 양방향 incidence, 분지 누락, 구간 순서, 표면·중심선·마스크의 대응을 검사한다.

| 검사 | 수용 기준 |
|---|---|
| 기본형 클래스 범위 | 좌우 12개 클래스의 대응 또는 미확인 사유가 전부 있음; 일부 누락을 숨기지 않음 |
| 관계 무결성 | 모든 incident 참조의 역참조 일치, orphan 참조 없음 |
| 조기 MCA 분기 | 분기 후 M1을 표현할 수 있고 자동 M2 변환 없음 |
| 다분지 | M2/M3 복수 instance와 모든 연결 이웃 보존 |
| ACom | midline 구조 하나와 양쪽 접합점; 결손 사례는 결손 주석 보존 |
| 구간·병변 라벨 | 병변 ID와 해부학 구간 ID를 별도 저장 |
| 경계 불확실성 | 근거 없는 위치 null, 해당 세부 구간 출력은 미확인 또는 합성으로 표시 |
| 접근 경로 | 좌우 대퇴 × 좌우 경동맥 네 조합 각각에서 동측 ACA/MCA 목표까지 도달 검사; 반대편 ACom 우회를 지정 경동맥 통과로 대체하지 않음 |

현재는 명세 작성 단계이며 위 검사의 실행 결과는 모두 NOT RUN이다. 위치 오차·곡률·마스크 허용오차는 좌표 계약과 기준 주석 확보 후 별도 기하 명세에서 고정한다. 구현 전에 첫 기준 표본의 landmark 가용성, ACom 대응 요소, M3 후보 목록을 조사한다.

## 7. 문헌과 적용 범위

- **S1:** *Microsurgical Anatomy of the Anterior Circulation of the Brain Adjusted to the Neurosurgeon’s Daily Practice* (2021). [본문](https://pmc.ncbi.nlm.nih.gov/articles/PMC8073207/). ACA 지형 및 분지 기시의 가변성. 개별 Atlas의 경계 좌표를 제공하지 않음.
- **S2:** *The Angiographic Anatomy of the Sphenoidal Segment of the Middle Cerebral Artery and Its Relevance in Mechanical Thrombectomy* (2020). [원연구 및 비교표](https://pmc.ncbi.nlm.nih.gov/articles/PMC7253867/), [PubMed](https://pubmed.ncbi.nlm.nih.gov/32508905/). MCA 구간 분류의 불일치와 분기/genu 구분 근거.
- **S3:** Rakshith et al., 사체 MCA 해부 연구 (2024). [본문](https://pmc.ncbi.nlm.nih.gov/articles/PMC11588606/), [DOI](https://doi.org/10.1055/s-0042-1750188). 15개 뇌의 30개 MCA에서 origin–genu 및 limen–circular sulcus의 지형 정의를 사용.
- **S4:** Isolan et al., insula 혈관 미세해부 연구 (2022). [본문](https://pmc.ncbi.nlm.nih.gov/articles/PMC9388914/). 주 분기 기준의 M1/M2를 사용하므로 S3와 구분한다. M3의 opercular 주행과 M4로의 이행 확인 자료.
- **S5:** Georgountzos et al., ACA 사체 해부 연구 (2024 온라인/2025 권호). [최종 논문](https://doi.org/10.1007/s00276-024-03532-5), [확인한 저자 원고](https://assets-eu.researchsquare.com/files/rs-4903088/v1/90187d54-783f-4435-96a7-35d1f12b3b13.pdf?c=1734365181). ACA 경계 문구는 저자 원고에서 확인했으며 최종 본문과의 일치는 추가 확인 대상.

해부학적 정의는 문헌 근거이며, ID·필드·null 처리·수용 기준은 본 프로젝트의 설계 결정이다. 원문에서 확인하지 않은 치수나 변이 빈도를 생성 파라미터로 추가하지 않는다.
