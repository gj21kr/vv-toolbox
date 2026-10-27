# 하부 MCA 줄기 연결 판정 — 2026-10-20

대상: FJ1718 (trunk of inferior terminal branch of right middle cerebral artery)의 기존 8개 후보. 전신 혈관이나 반대쪽 MCA까지 검사한 결과가 아니다.

## 결론

**해부학적 관계의 일반적 근거와 Atlas 모델의 실제 체적 접촉을 분리해서 확인했다.** 기존 거리 기반 검사보다 강한 근거를 확보했지만, 특정 Atlas 표본의 진짜 분기 관계를 확정할 독립 주석은 확보하지 못했다.

- 원본 삼각형이 둘러싼 체적의 양의 겹침: **6/8**.
- 양의 겹침 없음: **2/8** — FJ1660, FJ1664. 이는 접선 접촉 또는 실제 혈관의 존재 자체를 배제하지 않는다.
- 문헌과 형상 증거가 함께 지지하는 주요 후보: **FJ1692 (M1), FJ1659 (anterior temporal)**.
- 형상 접촉이 있어도 해부학적 판정이 필요한 후보: **FJ1669, FJ1694, FJ1712, FJ1729**.
- 독립적인 Atlas 분기 주석에 의해 확정한 specimen-specific 연결: **0**. 이 결과를 confirmed anatomical connectivity로 승격하지 않는다.

## 방법 및 통제

고정 원본 해시 검증 후 각 OBJ의 동일 좌표 정점을 용접했다. hole filling, dilation, 위치 이동, 접합 생성은 하지 않았다. 선택 혈관과 8개 상대 혈관은 모두 watertight 및 valid volume이었다. Manifold boolean intersection으로 쌍별 교차 체적을 계산하고, 기존 중심선 샘플이 상대 체적 내부에 있는지도 조사했다.

단위 상자 겹침(예상 체적 0.5), 접선 접촉(0), 분리(0) 통제 검사 **PASS**. 접촉 계산은 컨테이너에서 실행했다. 0체적 통제 사례에서 trimesh의 center-of-mass 연산 경고가 발생했지만 체적 단언은 통과했다. 샘플 내부 개수는 중심선 해상도에 의존하며 0이라고 연결이 없다는 뜻은 아니다.

검사한 혈관은 폐곡면의 solid 표현이다. 교차 체적은 **모델상 겹침**을 증명하며, 실제 혈관 내강, 혈류 방향 또는 부모·자식 관계를 증명하지 않는다. 의도한 접합과 잘못된 관통은 모두 양의 체적을 만들 수 있다.

## 후보별 판정

체적 단위: 원본 좌표 단위³ (mm³ 가정). 위치 비율은 선택 중심선 n0→n1 기준, 혈류 방향 아님. 내부 샘플은 `상대 중심선이 선택 체적 내부 / 선택 중심선이 상대 체적 내부` 순서다.

| 후보 | 교차 체적 | 내부 샘플 | 접촉 중심의 선택 경로 위치 | 판정 |
|---|---:|---:|---:|---|
| FJ1692, sphenoid MCA (M1) | 6.055492 | 13 / 20 | 98.8% | **가장 강한 연결 후보**. M1에서 주요 줄기로 분기하는 일반적 관계와 모델 접촉이 부합. 표본의 정확한 분기점·변이는 미확인. |
| FJ1659, anterior temporal | 3.745691 | 5 / 0 | 0.0% | **해부학적으로 타당한 연결 후보**. 대표 inferior-trunk 분포와 접촉이 부합. early branch 변이도 있어 이름만으로 확정하지 않음. |
| FJ1729, temporo-occipital | 4.381312 | 0 / 23 | 56.8% | **중간부 모델 접촉 확인**. inferior/middle trunk 배치 변이를 고려해야 하며 개별 origin은 미확인. 끝점 접합으로 표시하면 안 됨. |
| FJ1712, polar temporal | 1.000933 | 0 / 0 | 74.8% | **중간부 모델 접촉 확인, origin 미확인**. 조기 temporal branch 가능성 때문에 반드시 inferior daughter라고 볼 수 없음. |
| FJ1694, insular MCA | 0.986157 | 0 / 0 | 93.2% | **모델 접촉 확인, 역할 미확인**. M2는 지형적 segment 명칭이므로 별도 daughter인지 인접 줄기인지 이름만으로 판단 불가. |
| FJ1669, precentral | 1.147561 | 0 / 0 | 0.0% | **문헌 대표 분포와 불일치하여 보류**. 접촉은 있으나 precentral은 주로 superior trunk 계열. 잘못된 관통·라벨·실제 변이 중 어느 것인지 확정 불가. |
| FJ1660, 다른 insular MCA 요소 | 0 | 0 / 0 | 해당 없음 | **직접 연결 지지 근거 부족**. 거리 후보만으로 연결하면 안 됨. |
| FJ1664, central sulcus | 0 | 0 / 0 | 해당 없음 | **직접 연결 지지 근거 부족, 우선 제외 검토**. 대표적으로 superior trunk 계열이며 양의 체적 접촉도 없음. 원본 라벨에 side가 없으므로 right로 확정하지 않음. |

## 문헌으로 확인한 사실

1. [Gibo et al., 1981, Microsurgical anatomy of the middle cerebral artery](https://pubmed.ncbi.nlm.nih.gov/7452329/): M1–M4 지형적 구분과 bifurcation/trifurcation/multiple-trunk 변이가 보고됐다. 표준 2분기 그래프를 모든 표본에 강제할 수 없다.
2. [Rakshith et al., MCA cadaveric study](https://pmc.ncbi.nlm.nih.gov/articles/PMC11588606/): 대표 type 1에서 precentral/central은 superior, temporal 계열은 inferior에서 나온다. 이를 FJ1669/FJ1664 검토 근거로 사용하며 표본 특이적 절대 규칙으로 사용하지 않는다.
3. [Microsurgical anatomy of the central lobe](https://pubmed.ncbi.nlm.nih.gov/25555079/): central/precentral/anterior parietal의 주된 superior-trunk origin을 별도 해부 연구에서 보고한다.
4. [Early MCA branches](https://pubmed.ncbi.nlm.nih.gov/12816276/): 조기 temporal/frontal 분기 다양성이 있어 temporal label만으로 origin을 결정할 수 없다.
5. [Middle cerebral artery revascularization: anatomical studies](https://www.scielo.br/j/anp/a/rRFzmFfb8t3RBS7Pr4zdxJD/?lang=en): trifurcation에서 temporo-occipital이 middle trunk에 속하는 패턴도 기술되어, 해당 이름을 inferior 전용으로 고정할 수 없다.

위 문헌은 일반적 해부와 변이의 근거다. 이 특정 BodyParts3D 형상의 실제 접합을 직접 관찰한 연구가 아니다.

## 왜 아직 해부학적 확정은 아닌가

[BodyParts3D 4.0 공식 릴리스 노트](https://dbarchive.biosciencedbc.jp/data/bodyparts3d/20130619/release_4.0_e.html)는 모델에 오류가 남아 있을 수 있다고 명시한다. IS-A/PART-OF와 mesh-concept 표는 제공하지만, 우리가 읽은 자료에서 이 8쌍의 검수된 branch-from 관계나 접합면 주석은 확보되지 않았다. 이를 데이터셋 전체에 그런 자료가 존재하지 않는다는 주장으로 확대하지 않는다.

확정하려면 이 모델의 원본 분지 주석 또는 해당 접합부를 식별할 독립 영상/해부 근거가 필요하다. 현재는 **문헌 지지 후보 / 모델 접촉만 확인 / 직접 연결 근거 부족**으로 저장하는 것이 타당하다. 미확인 후보를 confirmed로 표시하거나 자동 연결 형상을 만들지 않았다.

## 산출물과 재현

- `scripts/verify_mca_contacts.py`: 원본 hash 검증, 부피 교차, 중심선 포함 및 통제 검사.
- `exports/connection-audit/mca-volume-contacts.json`: 후보별 수치, 9개 원본 파일 hash, 패키지 버전, 선택 혈관의 원본 concept 목록. Git 제외 로컬 결과.
- 이전 `ATLAS_CONNECTION_VALIDATION.md`: 거리·endpoint 분류 검증. 이번 보고서는 더 강한 체적 접촉 증거를 추가한다.

이전 UI의 2개/6개 그룹이 실제 해부학적 2개/6개 연결을 의미한다는 해석은 기각한다. 형상이나 UI는 이번 확인 과정에서 변경하지 않았다.
