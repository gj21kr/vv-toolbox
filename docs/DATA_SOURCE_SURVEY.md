# 혈관 기준 자료 조사

조사일: 2026-10-20 · 단계: 1차 공개 자료 조사 · 대상 계획: [개발계획서](DEVELOPMENT_PLAN.md)

후속 파일 검사: [BodyParts3D·VMR 원자료](LOCAL_SOURCE_INVENTORY.md), [TopCoW 마스크·연결 주석](TOPCOW_SOURCE_INSPECTION.md). 아래 1차 조사와 후속 파일 확보·검사 범위를 구분한다.

## 1. 조사 목적과 판정 기준

대퇴–대동맥–경동맥–좌우 ACA A1–A3/MCA M1–M3의 기준 형상, 연결 근거, 구간 라벨 및 협착·동맥류 생성 규칙에 사용할 자료를 선정한다.

다음 다섯 항목을 분리해 조사한다.

1. **제공 범위:** 필요한 혈관이 실제 파일에 들어 있는가.
2. **주석:** 혈관 마스크, 구간 경계, 중심선, 접합점 또는 연결 관계가 있는가.
3. **독립성:** 기준 모델과 다른 출처로 관계를 대조할 수 있는가.
4. **이용조건:** 코드, 영상, 마스크, 모델과 파생 데이터의 조건이 무엇인가.
5. **획득 가능성:** 공식 배포 위치, 접근 제한, 버전 및 파일 확인 가능 여부.

상태는 `문서 확인`, `로컬 자료 확인`, `미확인`, `후속 파일 검사 필요`로 기록한다. 자료의 공개 소개나 논문 존재를 실제 파일의 확보·검수 완료로 간주하지 않는다. 원본 환자 영상과 대용량 데이터는 이번 조사에서 새로 취득하지 않았다.

## 2. 전신·대동맥 자료 비교

| 후보 | 확인된 제공 내용 | 활용 후보 | 한계 및 필요한 확인 |
|---|---|---|---|
| BodyParts3D 4.0 | 공통 좌표의 OBJ, IS-A/PART-OF 및 개념–요소 대응표 | 전신 배치·명칭의 기준 틀 | 분류/포함 관계는 혈관 연결 그래프가 아님. 연결과 세부 구간 주석 별도 필요 |
| Vascular Model Repository (VMR) | 영상 기반 구역별 모델과 사례별 자료; 로컬 0011의 표면·경로·단면 파일 확인 | 대동맥궁과 개별 혈관 형상·단면 대조 | 전신 한 표본으로 간주 불가. 사례별 coverage·단위·영상 및 경로 제공 여부 검사 필요 |
| TotalSegmentator v2 공개 CT 자료 | 1,228 CT, 117 구조 분할의 배포 기록 및 v2 클래스 설명 | 대동맥·궁 분지·총경동맥 등의 독립적 마스크 대조 | 임상 CT의 촬영 범위는 사례별로 다름. 대퇴–뇌혈관 전 경로 또는 A1–A3/M1–M3 주석 자료로 사용 불가 |

### 2.1 BodyParts3D

[공식 다운로드](https://dbarchive.biosciencedbc.jp/en/bodyparts3d/download.html)는 OBJ와 개념 대응표를 제공하며, 배포 OBJ를 polygon reduction rate 99%로 설명한다. 정밀한 작은 혈관의 접합·반경 검증에는 이 표현 수준을 고려해야 한다. [공식 4.0 릴리스 노트](https://dbarchive.biosciencedbc.jp/data/bodyparts3d/20130619/release_4.0_e.html)는 모델 오류 가능성을 명시한다.

[공식 라이선스](https://dbarchive.biosciencedbc.jp/en/bodyparts3d/lic.html)는 2025-02-27 갱신된 CC BY 4.0과 출처 표기를 안내한다. 배포 시 원본 버전·해시, 요구된 출처 표기와 변경 사실을 함께 관리한다. 원본 파일의 과거 라이선스 헤더도 보존한다.

**선정 의견:** 전신 기준 배치의 우선 후보. 연결·구간 라벨의 완성된 정답으로는 선정하지 않는다. 최초 기준 모델의 실제 접합 검수와 합성 보충 목록이 필요하다.

### 2.2 VMR

[공식 갤러리 안내](https://www.vascularmodel.org/gallerytutorial.html)는 사례별 설명·프로젝트 파일·일부 시뮬레이션 결과의 접근 방법을 제공한다. [0044_H_ABAO_AAA 설명서](https://vascularmodel.com/vmr-pdfs/0044_H_ABAO_AAA.pdf)는 복부대동맥류 및 CT 기반 사례임을 확인한다. 설명서의 일반 해부 설명은 그 사례 파일이 대퇴까지 포함한다는 증거가 아니다.

로컬 `0011_H_AO_H` 자료에는 표면, Paths, Segmentations 및 README-COPYRIGHT가 있다. 현재 프로젝트의 [참조 파이프라인](../REFERENCE_PIPELINE.md)은 독립 경로 5개와 단위 추정의 한계를 기록한다. 이는 인구 정상 분포를 대표하는 자료가 아니다. [Stanford 영구 주소](https://purl.stanford.edu/kd053sz6270)는 이번 웹 도구에서 접근하지 못했으므로 온라인 원본 재취득 상태는 미확인이다.

[공식 저장소 LICENSE](https://github.com/SimVascular/vascularmodel/blob/main/LICENSE)는 연구·개발 사용과 사본의 저작권 고지 보존 조건을 명시한다. 무제한 상업용 파생 데이터 배포 허가로 확대하지 않는다. 실제로 선택할 사례의 README-COPYRIGHT와 이용 목적을 대조한 뒤 파생 데이터 공개 여부를 정한다.

**선정 의견:** 구역별 형상·접합 검증 후보. 전신 기준 모델의 다른 표본을 그대로 이어 붙이는 방식은 채택하지 않는다.

### 2.3 TotalSegmentator

[공식 CT v2.0.1 배포 기록](https://zenodo.org/records/10047292)은 1,228 CT와 117개 구조, 약 23.6 GB의 파일을 설명한다. 페이지에 새 버전 링크가 있으므로 취득 단계에서 사용할 버전을 별도로 고정한다. 이번에 전체 파일을 다운로드하지 않았다.

[공식 v2 변경 설명](https://raw.githubusercontent.com/wasserth/TotalSegmentator/master/resources/improvements_in_v2.md)에는 brachiocephalic trunk, 좌우 common carotid 및 subclavian artery의 추가가 기재돼 있다. 추가 task의 학습 라벨과 비공개 추가 학습 사례는 공개 117-class 자료에 포함되지 않는다고 명시한다. 모델이 추론할 수 있는 구조와 공개 데이터의 수동 주석을 혼동하지 않는다.

소프트웨어의 [공식 README](https://github.com/wasserth/TotalSegmentator)는 기본 task와 일부 추가 task의 라이선스를 구분한다. Zenodo 자료의 Rights 영역은 이번 텍스트 조회에서 라이선스 값이 표시되지 않았다. **데이터 라이선스와 합성 파생물 배포 조건은 취득 전 재확인**하며 소프트웨어의 Apache-2.0을 영상 자료에 자동 적용하지 않는다.

**선정 의견:** 궁–총경동맥 영역의 독립 영상·마스크 대조 후보. 환자별 FOV, 조영 상태, 라벨 품질을 확인할 사례 선정표가 필요하다.

## 3. 뇌혈관·동맥류 자료 비교

| 후보 | 제공 내용 | 활용 후보 | 한계 |
|---|---|---|---|
| TopCoW | CTA/MRA, CoW 성분 마스크·ROI, 사례별 CoW edge 존재 여부 | 근위 뇌혈관의 표본별 연결 대조 | 전체 원위 분지 그래프나 A1–A3/M1–M3 구간 GT는 아님 |
| BraVa | TOF-MRA에서 추적한 동맥 tree, 직경·형태 정보 | 분지 구조·형태 통계 | 원영상·마스크 및 세부 구간 라벨 배포 미확인 |
| TubeTK/Bullitt | 공개 MRA와 혈관 추적 자료 후보 | 중심선·반경 표현 대조 | 원배포 접근·manifest·데이터 라이선스 재확인 필요 |
| Lausanne ds003949 | TOF-MRA/T1w 및 동맥류 관련 라벨 | 병변 형상·영상 대조 | weak label과 정밀 mask를 구분해야 함; 혈관 구간 GT가 아님 |

### 3.1 TopCoW

[공식 2025 배포](https://zenodo.org/records/15692630)는 영상, CoW segmentation, ROI 외에 `antpos_edges_labelsTr`의 edge 유무 YAML을 명시한다. 영상과 ROI는 LPS+로 설명된다. 따라서 일반적인 해부 연결표가 아닌 **사례별 CoW 연결 주석**을 대조할 수 있는 우선 후보이다. [원논문](https://pmc.ncbi.nlm.nih.gov/articles/PMC10793481.2/)의 성분 클래스와 A1–A3/M1–M3 세부 구간을 동일시하지 않는다. 중심선의 기본 제공은 확인하지 못했다.

본체 자료는 출처 표시와 상업 이용 시 소유자 허가를 요구한다. 외부 세트는 원자료 조건이 다르다: Lausanne CC0, IXI CC BY-SA 3.0, ISLES 비상업 조건. LargeIA 원영상은 원배포에서 별도로 받아야 한다. 단일 라이선스로 묶지 않으며 파생 주석·합성물의 조건은 ZIP README/License에서 추가 확인한다.

**우선 검사:** 본체 또는 외부 세트 1개를 선택해 edge YAML과 실제 마스크의 대응, ROI 절단, ACA/MCA 범위를 검사한다. Lausanne 외부 세트 20개는 대조군이므로 동맥류 학습 자료로 간주하지 않는다.

### 3.2 BraVa

[원논문](https://pmc.ncbi.nlm.nih.gov/articles/PMC3971907/)은 건강인 61명의 TOF-MRA에서 추적한 동맥 arbor와 형태·직경 정보를 설명한다. 표본별 추적 tree는 분지 및 형태 통계 후보지만 그 자체가 독립 검증을 거친 모든 연결의 정답은 아니다. A1–A3/M1–M3 명시적 경계, voxel mask와 원영상 배포는 확인되지 않았다.

[공식 사이트](https://cng.gmu.edu/brava/) 접근이 실패해 현재 파일 획득 및 명시적 재배포·합성 파생 라이선스는 **미확인**이다. 다운로드 가능이라는 논문 설명을 재배포 허가로 해석하지 않는다. 파일과 이용조건 확인 전에는 통계·구조 조사 후보로 보류한다.

### 3.3 TubeTK/Bullitt

[Kitware 문서](https://github.com/KitwareMedical/TubeTK-pypbm)와 [공식 데이터 주소](https://public.kitware.com/Wiki/TubeTK/Data)는 MRA 및 혈관 표현 자료를 조사할 출발점이다. [관련 원연구](https://doi.org/10.1371/journal.pone.0311439)에서 공개 혈관 자료 활용을 확인했다.

이번에는 원사이트의 실제 파일 목록·주석 수·세부 해부학적 라벨·이용조건을 확인하지 못했다. TubeTK 소프트웨어 라이선스를 데이터에 적용하지 않는다. 자료 취득과 주석 규격을 확인할 때까지 기준 모델 후보로 채택하지 않는다.

### 3.4 Lausanne ds003949

[공식 설명](https://github.com/OpenNeuroDatasets/ds003949)과 [원논문](https://doi.org/10.1007/s12021-022-09597-0)은 TOF-MRA/T1w, 동맥류 라벨 및 정합 관련 자료를 설명한다. [공식 metadata](https://github.com/OpenNeuroDatasets/ds003949/blob/master/dataset_description.json)는 CC0를 명시한다.

정밀 동맥류 mask와 병변을 크게 둘러싼 weak label을 구분해야 한다. 모든 라벨을 동맥류 표면·목 경계의 정답으로 사용하지 않는다. 개인 영상으로 변환한 확률 혈관 Atlas도 개인별 실제 연결 주석은 아니다. **병변 대조 자료의 우선 후보**로 두되, 정밀 라벨이 있는 사례부터 검토한다.

## 4. 혈관별 자료 확보 과제

| 대상 | 기준 틀 후보 | 독립 대조 후보 | 현재 미해결 항목 |
|---|---|---|---|
| 좌우 대퇴·장골 | BodyParts3D | 하지를 포함한 공개 CTA 조사 | 대퇴 접근 위치, 분지 주석, 공개 사례와 이용조건 |
| 복부·흉부 대동맥 | BodyParts3D | VMR, TotalSegmentator | 사례별 연속 범위·단위·기준점 |
| 대동맥궁·주요 기시부 | BodyParts3D | VMR 0011, TotalSegmentator v2 | 기시 위치, 프리셋 분류와 표본 변이 |
| 총경동맥–내경동맥 | BodyParts3D | 공개 CT/CTA 및 구역별 모델 | 목의 연속 coverage와 bifurcation 주석 |
| ACA·MCA 근위 연결 | 기준 모델의 뇌혈관 구조 | TopCoW 영상·마스크·edge 주석 | CoW 연결 주석 범위와 전신 모델의 표본 독립성 |
| A1–A3/M1–M3 경계 | 해부학적 정의와 원영상 | 원위부를 포함한 뇌혈관 자료 | 모든 구간의 명시적 GT를 제공하는 자료 미확보 |
| 협착·동맥류 | 부위별 병변 자료 | VMR 병변 사례, Lausanne | 부위별 정의·허용 범위·분포·상관관계; weak label 구분 |

이번 검색에서 하지 CTA 연구는 발견했으나 대퇴 분할과 연결 주석의 실제 공개 파일·배포 조건을 확보하지 못했다. 이를 공개 자료가 없다는 결론으로 해석하지 않는다.

## 5. 우선순위와 자료 선정 절차

**1차 제안:** BodyParts3D는 전신 배치, VMR/TotalSegmentator는 체간·경부 형상 대조, TopCoW는 근위 연결 대조, Lausanne는 병변 대조에 사용한다. BraVa는 통계 후보로 남긴다. 각 역할의 자료를 한 표본의 실측 모델처럼 결합하지 않는다.

**남은 핵심 공백:** 단일 표본의 대퇴–뇌혈관 연속 자료, 좌우 A1–A3/M1–M3의 완전한 경계 주석, 부위별 협착·동맥류의 공동 분포는 이번 조사에서 확보되지 않았다. 이 공백은 별도 자료 조사 및 주석 과제로 관리한다.

1. 자료별 공식 릴리스·라이선스와 표본 식별 체계를 고정한다.
2. 소수 사례의 manifest와 라벨 목록을 확인해 필수 혈관 coverage를 작성한다.
3. 영상·마스크·중심선·그래프를 직접 열어 좌표, 단위, 절단 범위, 구간 정의를 대조한다.
4. 기준 모델과 독립 대조 자료의 관계 및 같은 원본 파생 여부를 확인한다.
5. 필수 연결마다 근거, 표본 위치 확인 상태, 합성 보충 필요 여부를 기록한다.
6. 라벨 없는 A1–A3/M1–M3에 대해 주석 프로토콜을 작성한다. 임의 길이 분할로 대체하지 않는다.

최초 기준 모델 선정은 파일 단위 검사가 완료된 후 확정한다. 이 보고서는 후보를 선별하는 단계이며 데이터 확보나 해부 검증 완료 보고서가 아니다.
