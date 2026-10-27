# TopCoW 파일·주석 검사

검사일: 2026-10-20 · 대상: TopCoW 공식 배포 v1의 CTA_LargeIA.zip · 상위 문서: [자료조사](DATA_SOURCE_SURVEY.md)

## 1. 확보 및 검사 범위

[공식 배포](https://zenodo.org/records/15692630)의 작은 외부 자료 묶음을 내려받아 ZIP 구성, 전체 40개 NIfTI 마스크의 헤더·라벨 값·라벨별 voxel 수, 20개 YAML, 40개 ROI 텍스트를 검사했다. 40개 마스크는 20사례의 두 표현이며 독립적인 40사례가 아니다. 원본 CTA는 이 ZIP에 없으며 이번에 취득하지 않았다. 영상과 분할의 일치, 혈관 내강 연결, 해부학적 정확도는 검사하지 않았다.

| 항목 | 결과 |
|---|---|
| ZIP 크기 | 802,732 bytes |
| 공식 MD5와 비교 | PASS: `83cf2f4df95738eb5f76c6eb6b78c3bf` |
| SHA-256 | `560a73c38370f3b8bf83c7e7a62295d653fab67d1fe38c03d080255a249d4c8c` |
| 전체 파일 | 100개 |
| 5개 파일 그룹의 사례 ID 대응 | PASS: 각 20개, 중복 없음, 동일 사례 집합 |
| YAML 구조 및 값 | PASS: 20개 모두 지정된 전방·후방 8개 항목, 0/1 값 |
| `cow_seg_labelsTr` | 가공 마스크 20개 |
| `raw/cow_seg_labels_for_raw_imgs` | 원영상 대응 마스크 20개 |
| `antpos_edges_labelsTr` | 연결 존재 여부 YAML 20개 |
| `roi_loc_labelsTr` | CoW ROI 텍스트 20개 |
| `raw/braincase_ROI_after_LPS_reorient` | braincase ROI 텍스트 20개 |
| 영상·중심선·표면·README·LICENSE 파일 | ZIP 내 없음 |

사례 ID는 0011, 0012, 0013, 0016, 0017, 0023, 0026, 0027, 0028, 0034, 0045, 0058, 0066, 0068, 0076, 0080, 0084, 0085, 0088, 0089이다.

검사 스크립트는 `scripts/inspect_topcow_source.py`, 상세 측정 결과는 로컬 `exports/source-audit/topcow-largeia.json`, 원자료는 `reference-data/topcow-largeia/CTA_LargeIA.zip`에 보관한다. 원자료와 상세 결과는 Git 제외 경로이다. Docker `python:3.12-slim`에서 nibabel, numpy, PyYAML로 실행했다. 패키지 버전 고정은 아직 하지 않았으며 입력 해시와 검사 스크립트를 보존한다.

## 2. 구간 라벨과 연결 주석

[공식 클래스 정의](https://github.com/CoWBenchmark/TopCoW_Eval_Metrics/blob/master/topcow24_eval/constants.py)에 따르면 1=BA, 2/3=우/좌 PCA, 4/6=우/좌 ICA, 5/7=우/좌 MCA, 8/9=우/좌 PCom, 10=ACom, 11/12=우/좌 ACA, 15=3rd-A2이다. 전체 파일에서 관측된 값은 배경 0과 이 13개 클래스에 한정된다. 모든 사례에 모든 클래스가 있다는 뜻은 아니다.

**3rd-A2는 변이 혈관 명칭이며 ACA의 A3 구간을 의미하지 않는다.** ACA와 MCA 마스크에는 A1–A3 또는 M1–M3를 나누는 클래스가 없다.

YAML은 `anterior`와 `posterior` 아래 명명된 0/1 값을 담는다. [공식 연결 정의](https://github.com/CoWBenchmark/TopCoW_Eval_Metrics/blob/master/topcow24_eval/metrics/seg_metrics/graph_classification/generate_edgelist.py)와 대응되는 항목은 다음과 같다.

| 항목 | 존재 주석이 1인 사례 수 / 20 |
|---|---:|
| L-A1 | 20 |
| R-A1 | 20 |
| ACom | 16 |
| 3rd-A2 | 2 |
| L-PCom | 8 |
| R-PCom | 11 |
| L-P1 | 16 |
| R-P1 | 17 |

이는 선택된 20사례의 주석 집계이며 일반 인구의 변이 발생률로 사용하지 않는다. 접합점 좌표, 전체 분지 edge list, 혈류 방향 또는 중심선 경로를 제공하는 자료로 해석하지 않는다. 별도 YAML과 마스크에서 추론한 연결이 일치하는지는 후속 검사 대상이다.

## 3. 좌표와 단위

40개 마스크 모두 affine에서 판독한 voxel 축 방향은 LPS였다. 원영상 대응 마스크 20개는 공간 단위 `mm`, 가공 마스크 20개는 `unknown`이었다. 공간 단위 공백을 자동으로 mm로 채우지 않는다.

예를 들어 Tr0011 가공 마스크는 287×381×370, spacing 약 0.455078×0.455078×0.400009, qform code 0, sform code 2이다. 대응 braincase ROI는 크기 287×381×370, 시작 index 96,72,19를 기록한다. 이 예의 크기 일치는 전체 사례의 좌표 정합 검증을 대체하지 않는다. 원영상·원영상 대응 마스크·가공 마스크의 affine, crop offset, voxel 값을 함께 대조해야 한다.

## 4. 사용 판정과 다음 작업

- **근위부 CoW 연결 대조 후보:** 사례별 A1/ACom/PCom/P1 존재 주석을 확보했다.
- **전체 목표 구간 정답 자료:** 보류. ACA A1–A3와 MCA M1–M3 경계 및 말초 분지 연결을 별도로 정의하고 주석해야 한다.
- **치수 기준 자료:** 보류. 원영상과 단위·좌표 계약을 확인해야 한다.
- **합성 파생자료의 공개 배포:** 보류. 이 ZIP에는 라이선스 파일이 없으므로 원 LargeIA 자료 조건 및 추가 주석의 조건을 확인해야 한다. 배포 페이지의 다른 자료 라이선스를 대신 적용하지 않는다.

다음 작업은 목표 구간별 해부학적 경계·필수 접합점 명세를 작성하고, 이 자료의 각 필드를 명세에 대응시키는 것이다. 이후 원영상 확보와 crop/affine 대조, 사례별 연결 주석 대조를 수행한다. 모델 학습이나 성능 평가는 범위에 포함하지 않는다.
