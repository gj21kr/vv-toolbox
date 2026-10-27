# 낭상 동맥류 설계 입력

`saccular_spec()`은 원본 사례의 revision에 연결된 수동 합성 설계 입력을 만든다.
**주머니 표면·열린 내강·마스크를 생성하는 연산은 아직 아니다.**
원본 사례나 `lesions` 목록을 수정하지 않으며 `geometry_status=NOT GENERATED`를 반환한다.

## 입력과 저장

- 대상 edge와 내부 호길이 station, 명시적 부위.
- 목 평면의 중심, 바깥쪽 단위 법선, 평면 위 단위 폭 방향.
- 타원 목의 폭·깊이, 평면에 수직인 높이, dome의 폭·깊이, blending extent.
- 모서리 방향이나 부착 위치를 최근접 혈관만으로 추론하지 않는다.

목 윤곽은 타원 위 순서 있는 64개 점으로 저장한다. 마지막 점은 첫 점으로 연결하며,
목 평면·직교 축·중심선 보간 주소를 함께 보관한다. 평균 목 직경은 선언한 타원 두 축
직경의 산술평균이라는 **설계 규칙**이다. 높이/평균 직경 비율은 요청값에서 계산한 값이며
생성 표면의 실측값이나 문헌 측정법의 재현으로 표시하지 않는다.

`validate_saccular_spec()`은 현재 사례로 계약을 재구성하여 revision 변경, 윤곽 좌표
변조, 생성/검사 상태의 임의 승격을 거부한다. 숫자 유효성, 단위 축, 평면 직교성 및
내부 station을 검사한다. 목이 실제 부모 혈관 표면에 붙는지까지 증명하지 않는다.
현재 endpoint/분기점 부착은 별도 다분지 계약이 필요하므로 받지 않는다.

## 명령행

```text
python -m vv_toolbox.case_cli saccular-spec source.snapshot.json parameters.json
```

결과는 표준 출력 JSON이며 원본 파일을 쓰지 않는다. 파라미터 예시는 다음과 같다.
이 수치는 합성 시험 입력이며 부위별 임상 허용 범위가 아니다.

```json
{
  "lesion_id": "sac-1",
  "edge_id": "e",
  "region": "aca",
  "station_mm": 10,
  "neck_center_mm": [10, 2, 0],
  "outward_normal": [0, 1, 0],
  "width_direction": [1, 0, 0],
  "neck_width_mm": 2,
  "neck_depth_mm": 1,
  "height_perpendicular_mm": 5,
  "dome_width_mm": 4,
  "dome_depth_mm": 3,
  "blending_extent_mm": 0.5
}
```

## 출력 보호와 검증

반경 프로파일 표면 생성 및 병변 라벨 함수는 `concentric_stenosis`와
`fusiform_dilation`만 받는다. `saccular`, 미지원 또는 type 없는 병변을 넣으면
명시적으로 실패한다. 주머니를 빠뜨린 정상 튜브/라벨을 성공 결과로 출력하지 않는다.

- 전체 Docker 회귀: 600 passed / 3 skipped (CLI 추가 직전).
- CLI 포함 최종 집중 검사: 40 passed.
- 원본 불변, 반복 생성 일치, 타원 평면/치수, 잘못된 입력, stale revision,
  좌표/상태 변조, 미지원 병변의 표면·라벨 출력 거부를 검사했다.
- 근거: [검사 기록](evidence/saccular-spec-validation.json).

별도 [표면 후보 생성기](SACCULAR_SURFACE_CANDIDATE.md)에서 단일 부모의 implicit union을
구현했다. 합성 fixture의 중앙 내강과 목 치수 보존을 검사했지만 전체 사례 수용 전 단계다.
다음 구현은 실제 부모 표면과 목의 교차 확인, 목 치수 제약을 만족하는 implicit union,
목·dome의 생성 후 치수 측정, 주변 혈관/병변과의 간격 검사, 표면·마스크·라벨 연결이다.
분기점 병변·부위별 문헌 프리셋·앱 편집 UI도 남아 있다. M5 완료로 판정하지 않는다.
