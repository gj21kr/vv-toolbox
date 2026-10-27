# 낭상 동맥류 후보의 마스크와 병변 라벨

`build_saccular_masks()`는 현재 사례와 설계 명세로 표면을 다시 생성한 후, 실제
닫힌 삼각형 표면을 복셀화한다. 관련 없는 표면 파일을 사례의 결과로 연결하지 않는다.
출력은 **CANDIDATE**이며 기존 일반 사례 생성기의 수용 결과와 분리한다.

## 출력 계약

- 전체 선택 부모+주머니 표면 또는 주머니 주변 ROI를 명시적으로 선택한다.
  여기서 whole은 **이 후보의 단일 부모 표면 전체**이며 전체 대상 동맥을 뜻하지 않는다.
- 혈관 foreground, instance, provenance, membership과 별도 uint32 병변 ID 배열을 저장한다.
- 해부학 구간은 추론하지 않으며 anatomical 배열의 0은 미확정을 뜻한다.
- LPS/mm 좌표, zyx 배열 순서, voxel-to-world affine, 사례 revision, 설계 SHA-256,
  생성 표면의 검사 기록, 병변 ID/부모 edge 대응을 같이 저장한다.
- 원본 snapshot과 기존 출력 파일을 덮어쓰지 않는다.

병변 라벨 1의 정의는 다음 두 영역의 합이다. 둘 다 실제 표면 foreground 안에서만
허용한다.

1. 선언한 목 평면 위의 sac field 내부 내강.
2. 목 평면 아래/위치상 동일 평면에서, 선언한 sac/blend 지지 범위 안에 있으며
   원래 부모의 원형 반경 프로파일 밖으로 추가된 내강.

부모의 원래 내강, 벽/플라크/조직, 다른 해부 구간은 이 병변 라벨로 치환하지 않는다.
이 정의는 합성 시뮬레이터의 영역 규칙이며 임상 정답이나 실제 ostium의 전문가 주석이 아니다.

## 명령행

```text
python -m vv_toolbox.case_cli saccular-masks source.snapshot.json spec.json grid.json masks.npz --surface-spacing-mm 0.15 --coverage whole
```

`--coverage sac_roi`는 전체 부모가 아니라 sac와 blending의 보수적 범위를 덮어야 한다.
grid JSON에는 shape_zyx, spacing_xyz_mm, origin_xyz_mm, frame_id를 명시한다.
마스크 메모리 예산과 표면 생성 격자 예산은 별도다.

표면/ROI 범위가 잘리거나 frame이 다르거나 명세가 오래된 경우 거부한다. 표면 복셀화 후
foreground가 비어 있거나 face 연결 기준으로 여러 성분이면 거부한다. sac voxel이
하나도 없을 때에도 성공 결과를 발행하지 않는다. 이러한 샘플링 검사가 목 직경을
연속 공간에서 보장하는 것은 아니다.

## 합성 fixture 확인

기존 직선 부모·낭상 후보에서 다음 산출물을 만들었다.

| 범위 | 격자 간격 | 혈관 voxel | 병변 voxel |
|---|---|---:|---:|
| 선택 부모+주머니 전체 | 1.0 mm | 261 | 32 |
| sac 주변 ROI | 0.5 mm | 489 | 237 |

ROI 병변 237개는 평면 위 sac 235개와 추가 neck 내강 2개다. 격자 간격과 범위가
다르므로 두 표의 voxel 수를 직접적인 부피 일치 또는 해상도 수렴 증거로 해석하지 않는다.
별도 테스트에서는 **동일한 1 mm 격자**로 만든 ROI와 전체 결과의 해당 crop이
foreground와 병변 배열 모두 정확히 일치함을 확인했다.

산출물은 `exports/saccular-mask-final/whole.npz`, `roi.npz`, `masks.png`이다.
[실행 근거](evidence/saccular-mask-inspection.json)에 두 archive의 해시와 전체 metadata를
보관한다. 검사 스크립트는 `scripts/inspect_saccular_masks.py`이며 `--output`에
exports 내부의 새 폴더를 지정해 재실행할 수 있다.

코드 검사: 전체 회귀 620 passed / 3 skipped (최종 라벨 지지 범위 제한 전),
최종 집중 검사 40 passed. [검사 기록](evidence/saccular-mask-validation.json).
앱 편집 UI, 분기점/다중 병변, 실제 Atlas, 전체 대퇴–뇌혈관 출력은 아직 연결하지 않았다.
