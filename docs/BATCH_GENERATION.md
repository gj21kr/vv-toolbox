# 명시적 후보 목록의 병변 일괄 생성

## 기본 출력 범위

기본값은 **기준 사례의 모든 edge**다. 병변 없는 혈관도 표면과 요청된 마스크에 포함하고 간격 검사 대상으로 유지한다. 출력 부분집합은 Python `surface_edge_ids` 또는 CLI `--surface-edges`를 명시한 경우에만 허용한다. report와 surface metadata에 `complete_case`/`explicit_subset`, 선택/제외 edge ID, 원본 edge 수를 기록한다. 모든 기존·새 병변 edge는 반드시 출력 범위에 포함되어야 한다.

`complete_case`는 입력 사례의 edge를 빠짐없이 포함했다는 뜻이다. 입력 자료 자체의 해부학적 완전성, 네 접근 경로 연결 또는 임상 검증을 뜻하지 않는다. 원본에서 분리된 graph component는 각각 생성해 함께 출력하며 임의의 연결을 추가하지 않는다. geometry가 없거나 필요한 검사를 통과하지 못한 edge를 조용히 제외하지 않는다.

합성 두 혈관 fixture에서 수정하지 않은 두 번째 혈관의 표면·내강 voxel을 포함하고 해당 voxel의 병변 라벨은 0임을 확인했다. 수정하지 않은 혈관과 교차하면 기본 배치는 실패하고 report만 남긴다. 명시적 부분 출력은 제외 ID를 기록하며, 병변 edge를 제외하려는 요청은 실패한다. Docker 관련 검사 **41 passed, 63 warnings, 7.30 s**. [검증 근거](evidence/complete-case-output-validation.json).

`generate_lesion_batch`는 항목별 `type`으로 `concentric_stenosis`와 `fusiform_dilation`을 지원한다. 생략 시 협착이며, 기존 `generate_stenosis_batch` 이름도 호환된다. 수동 방추형 확장과 협착의 혼합 사례도 동일한 간격·출력 검사에 따른다. [방추형 확장 계약](FUSIFORM_DILATION.md). 지원하지 않는 유형은 실패 기록으로 격리한다.

`batch.generate_stenosis_batch`는 동일 기준 사례에 후보 설정을 순서대로 적용한다. 목표는 시도 수가 아니라 검사에 통과한 사례 수다. 목표 도달·최대 시도 수·후보 소진 중 먼저 발생한 조건에서 종료한다. 부족한 수는 FAIL과 remaining_count로 보고하며 기준을 낮추지 않는다.

```text
python -m vv_toolbox.case_cli batch SOURCE.snapshot.json CANDIDATES.json OUTPUT_DIR --target-count 10 --max-attempts 30 --seed 7 --spacing-mm 0.3
```

후보 JSON은 병변 연산 목록들의 배열이다. 각 연산은 협착 CLI의 파라미터에서 batch가 관리하는 case_id와 seed를 제외한다. 여러 연산을 넣으면 한 사례 안에 다중 병변을 생성하며 3D 영향 영역 간격 검사를 적용한다. 예제 수치는 명령 문법 예시이며 해부학적·임상적 허용 범위가 아니다.

기준 모델·출처·split은 파생 사례에 유지한다. 시도별 seed는 batch seed와 시도 index의 SHA-256에서 결정한다. 실패 이후에도 다른 시도의 seed가 바뀌지 않는다. 현재 후보는 operator_defined이며 확률분포나 모집단 대표성을 주장하지 않는다.

## 저장과 판정

- 새 output 디렉터리만 허용하며 기존 실행을 덮어쓰지 않는다.
- 통과한 사례는 `case-00000/` 등의 폴더에 `case.snapshot.json`과 `surface.npz`를 저장한다. 임시 폴더에서 모두 작성한 뒤 게시한다.
- `report.json`은 원본 revision·후보 설정 해시·모든 시도 설정·seed·실패 사유·통과 병변 측정값·부족 수를 기록한다. 결과 분포 검토에 필요한 입력/탈락/통과 목록을 보존하며 아직 통계적 분포 비교 그래프는 제공하지 않는다.
- 입력 검증·형상 생성 실패는 해당 후보만 FAIL로 기록한다. 파일 시스템 오류는 실행을 중단하고 이미 저장된 정상 사례를 보존한다. 프로세스 중단 후 자동 resume은 아직 지원하지 않는다.
- 현재 acceptance_scope는 **반경 프로파일 및 선택 edge 합성 표면의 위상·비접합 간격 검사**다. 전체 동맥의 경로·해부 정확성, 최종 표면 자기 교차, 마스크·라벨 출력 검증은 NOT RUN이다.
- CLI 종료 코드는 목표 도달 0, 사례 수 부족 1, 입력/저장 오류 2다.

## 검사

## 마스크 동반 출력

### 고해상도 병변 영역

mask 설정의 `lesion_rois`는 `{grid_config, required_lesion_ids}` 객체 목록이다. 각 격자는 전체 격자보다 하나 이상의 축에서 더 촘촘하고 다른 축에서도 더 거칠지 않아야 한다. 물리적 voxel extent는 전체 격자 안에 있으며 대상 병변의 기록된 3D support를 모두 포함해야 한다.

`lesion-roi-000.npz`와 대응 quality JSON을 저장한다. 같은 표면을 새 격자에서 독립적으로 rasterization하며 저해상도 마스크를 보간하지 않는다. quality의 `roi_voxel_xyz_to_whole_voxel_xyz`는 두 voxel 중심 좌표계 사이 변환이며, 배열 순서는 여전히 zyx다. case revision과 병변 label registry는 전체 출력과 동일하게 유지한다.

ROI에 없는 다른 병변은 registry에 남기되 그 영역의 필수 표본화 대상에서는 제외한다. 지정 대상 병변의 누락은 실패다. ROI 실패 시 전체 사례가 게시되지 않으며 정상 사례 수에도 포함하지 않는다.

통합 검사: 1 mm 전체 격자와 0.5 mm 병변 격자 출력·변환 일치 PASS. 병변 support를 일부만 포함하는 ROI는 실패하고 report만 남기는 검사 PASS. 배치·병변 라벨 관련 검사 합계 10개 PASS. 이는 작은 합성 fixture 범위이며 전신 고해상도 성능 검증은 아니다.

`--mask-config MASK_CONFIG.json`을 전달하면 마스크 검사를 필수로 실행한다. 설정에는 `grid_config`(shape_zyx, spacing_xyz_mm, origin_xyz_mm, frame_id), 선택적 `anatomical_labels`(edge ID→정수 label), `max_bytes`가 들어간다. grid는 선택된 표면 bounds 전체를 포함해야 한다. 이는 전체 해부 모델의 범위를 자동으로 담는다는 뜻이 아니다.

통과 폴더에 `mask.npz`와 `mask-quality.json`이 추가된다. NPZ는 혈관 foreground/해부 구간/instance/출처/소속/겹침과 병변 라벨을 함께 보존한다. 해부 라벨을 명시하려면 구간 materialization 근거가 있어야 하며 미확정 구간은 0을 유지한다.

여러 edge의 경우 개별 표면에서 instance membership을 구하고 합성 union 표면의 foreground와 출력 격자에서 정확히 비교한다. 분기 fillet 등으로 두 값이 다르면 소속을 임의 배정하지 않고 후보를 실패시킨다. 이 검사는 voxel 중심에서의 일치이며 연속 공간의 표면 동등성 증명이 아니다. 병변이 0 voxel이면 실패한다. 모든 검사를 통과한 뒤 사례 폴더를 게시한다.

추가 통합 검사 PASS: 합성 협착 사례의 snapshot/표면/마스크/병변 NPZ 동반 저장, 병변이 foreground 내부인지 확인, 미확정 anatomy 0 유지, 너무 작은 grid 실패 시 정상 사례 폴더 미생성. 배치 검사 합계 4개 PASS. 고해상도 병변 crop 동반 출력과 전체 혈관 해부 라벨 완성은 남아 있다.

Docker 3개 검사 PASS: 실패 후보 격리와 실제 성공 수 기준 종료, 같은 설정의 사례 revision/기록 재현, 최대 시도·후보 소진 시 부족 수, 기존 폴더 보존, CLI 실패 종료 코드. 이 검사는 전체 계획의 일괄 생성 완료를 뜻하지 않는다. 통합 마스크·라벨 출력과 최종 품질 기준 연결이 남아 있다.

## 통과·탈락 전후 파라미터 분포

각 `report.json`의 `parameter_distribution`은 전체 후보, 실제 시도, 통과, 탈락, 미시도 후보를 구분한다. 목표 수 도달 이후 또는 최대 시도 제한으로 실행하지 않은 후보는 실패에 포함하지 않는다. 매 시도 종료 시 보고서를 갱신한다.

질환 유형·부위·측정 정의별로 수치 파라미터의 관측값과 빈도, 최솟값·최댓값·누락 수를 기록한다. 직경 감소율과 면적 감소율은 합산하지 않는다. 다중 병변 사례에서는 병변 작업별 빈도를 세며, 사례 전체가 실패하면 해당 사례의 모든 작업을 탈락 집합에 포함한다. 이는 요청한 설정의 경험적 분포이며 독립 환자 표본이나 임상 모집단 분포를 의미하지 않는다. 측정 결과는 기존 `measured_lesions`에서 별도로 확인한다.

Docker 회귀 검사: `tests/test_batch_distribution.py`, `tests/test_batch.py`, `tests/test_fusiform_dilation.py` — **19 passed**, 60 dependency deprecation warnings. 실제 생성·실패 격리·목표 도달·파일 저장과 분포 일치를 확인했다.
