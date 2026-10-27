# 수동 합성 방추형 확장

2026-10-20 · VV-REQ-007/008/011/013의 일부 구현. 연구용 형상 연산이며 임상 진단이나 문헌 프리셋이 아니다.

## 생성 계약

`lesions.fusiform_dilation`은 선택 edge 내부에서 중심선은 유지하고 반경을 대칭적으로 확장한다. `diameter_ratio > 1`은 병변 중심의 국소 기준 직경에 대한 배수다. 지원 인자는 edge/lesion/case ID, region, center_mm, length_mm, diameter_ratio, sample_spacing_mm, seed, min_spacing_mm이다. 다른 edge나 원본 좌표를 이동하지 않는다.

반경은 `baseline_radius × (1 + (diameter_ratio − 1) × (1 − u²)³)`이며 `|u| < 1`, `u = 2 × (station − center)/length`인 범위에만 적용한다. 바깥은 원본 프로파일을 보존한다. 시작·끝이 edge 내부에 있어야 하므로 분기부 병변은 이 연산의 범위가 아니다. 병변 중심과 support 끝점은 반드시 표본에 포함한다.

출력은 `model_kind=synthetic`, `type=fusiform_dilation`, `mode=manual_synthetic`, 생성기 `fusiform-profile-1`로 기록한다. 기준 모델·split·source와 이전 병변 이력을 유지한다. 기준 직경, 요청 배수, 실제 중심 프로파일 배수/직경을 기록하며 협착률 필드를 사용하지 않는다.

병변 간격 검사의 capsule은 **기준 반경과 확장된 최종 반경의 최대값**을 사용한다. 기존 협착과 혼합할 때도 같은 비겹침·최소 간격 조건을 적용한다. 인접 혈관의 최종 형상 검사는 선택 표면 생성 단계에서 수행하는 보수적 capsule 검사이며, 최종 mesh 충돌 검증과 다르다.

## 실행과 출력

`vv-case dilation source.snapshot.json parameters.json derived.snapshot.json`으로 생성하고, 기존 `surface` 및 볼륨 출력 흐름으로 전달한다. CLI는 실패 시 정상 snapshot을 게시하지 않는다.

배치 함수 `generate_lesion_batch`의 후보 항목에 `type: fusiform_dilation`을 지정한다. `concentric_stenosis`와 혼합할 수 있다. type 생략은 기존 협착 동작을 유지하며 알 수 없는 type은 실패 기록으로 격리한다. 기존 함수명 `generate_stenosis_batch`도 호환 alias로 유지한다. 후보·seed·표면 출력·마스크 요구 조건은 기존 배치 계약을 따른다.

## 검증

합성 직선 fixture에서 기준 직경 4 mm를 중심 직경 8 mm로 설정하고, 격자 0.2 mm에서 실제 표면 단면의 두 축 직경이 8 mm ±0.3 mm 이내인지 검사했다. 이 값들은 검사 전에 정한 수치 fixture 조건이며 부위별 임상 허용 범위가 아니다. 원래 반경 밖에 새로 생성된 내강 voxel도 병변 라벨에 포함됨을 확인했다.

- 원본 불변·프로파일 support 보존·결정적 재생성 PASS.
- 확장 반경을 반영한 다른 혈관 병변과의 겹침 거부 PASS.
- CLI snapshot 재로드·닫힌 표면·실제 단면·병변 내강 마스크 PASS.
- 협착/확장 혼합 batch, 지원하지 않는 type 격리, 두 병변 이력 보존 PASS.
- Docker 관련 회귀 **39 passed, 57 warnings, 4.66 s**. [실행 기록](evidence/fusiform-dilation-validation.json).

부위별 문헌 파라미터 범위·확률 분포, 낭상 동맥류, 분기부 동맥류, 임상적 타당성은 아직 구현 또는 검증하지 않았다. 현재 수동 연산을 동맥류 요구사항 전체 완료로 표시하지 않는다. 앱 조절 UI 연결도 남아 있다.
