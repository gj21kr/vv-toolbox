# 낭상 동맥류 표면 후보

`build_saccular_candidate()`와 `saccular-surface` CLI는 단일 부모 혈관의 내부 sidewall
위치에서 주머니와 혈관을 하나의 implicit field로 합친다. 결과는 **CANDIDATE**이며,
정상 사례 출력·병변 라벨·일괄 생성의 수용 경로에는 연결하지 않는다.

## 주머니 치수와 재현 정보

`saccular-sidewall-3`은 목뿐 아니라 주머니의 폭·깊이·수직 높이를 생성된 삼각형에서
측정한다. 선언한 목 평면 위로 삼각형을 잘라 축별 범위를 구하며, 평면을 통과하는
삼각형의 교차점도 포함한다. 부모가 평면에 접하기만 하는 면적 없는 부분은 제외한다.
평면을 옮기거나 요청 치수를 바꾸지 않는다.

주머니 치수에도 기존과 같은 **2×spacing 절대 허용오차**를 적용한다. 차이가 크면
후보 표면과 후속 마스크를 출력하지 않는다. 기본 합성 fixture에서 요청 4×3×5 mm에
실측 **3.998616×2.999842×5.000000 mm**를 얻었다. 목 치수는 앞선 보정과 동일하다.
이 값들은 선언한 축에 대한 폭·깊이이며 임의 방향 최대 직경이나 임상 지표가 아니다.

기울어진 좌표계, 0.10/0.15 mm 격자, 다른 두 주머니 크기를 검사했다. 평면을 가로지르는
단순 다면체로 교차점 포함을 따로 검증했고, 목을 유지한 채 sac field의 폭을 두 배로
왜곡한 결함 주입에서도 출력이 거부됐다. [검사 기록](evidence/saccular-dome-validation.json):
최종 집중 검사 **43 passed**. 이 변경 후 전체 회귀는 재실행하지 않았다.

표면 metadata에는 생성기 버전·무작위 샘플링 없음·설계 입력 전체·사례/기준 모델 ID·
출처와 해시를 기록한다. 이를 포함한 [현재 fixture 기록](evidence/saccular-neck-preservation.json)을
생성했다. 이전 버전의 mask archive는 그 당시의 metadata를 그대로 유지한다.
현재 마스크 생성기는 새 표면 metadata를 자동으로 함께 저장한다.

## 목 치수 보정 결과

동일한 2×1 mm 목표와 동일한 목 평면을 유지한 채 접합 연산을 보정했다.
기존 [실패 기록](evidence/saccular-surface-fixture.json)은 그대로 보존한다.
최신 결과는 [목 치수 보정 기록](evidence/saccular-neck-preservation.json)이다.

- smooth minimum의 영향을 목 아래에 한정하고, 목 평면까지 C1 가중치로 줄였다.
- 목의 폭·깊이·법선에 맞춰 격자를 배치하여 선언 평면 자체가 격자층이 되도록 했다.
  출력 좌표는 원래 LPS/mm로 되돌리고 격자의 방향 행렬도 저장한다.
- 부모 혈관만 목 평면에 접하는 체적 없는 선은 부동소수점 오차로 긴 단면 윤곽을
  만들 수 있었다. 해당 zero tie를 spacing/1000의 양의 field 값으로 취급한다.
  주머니 field나 측정 평면을 옮기지 않는다. 이 수치 규칙을 metadata에 기록한다.
- 추출 시 퇴화 삼각형을 제외하고 양의 체적·면적·단일 표면을 다시 검사한다.
- 생성된 삼각형과 기존 평면의 교차 윤곽을 측정하여 축별 오차가 **2×spacing**
  이내인지 검사한다. 이 기준은 첫 보정 실행 전에 0.15 mm 격자에서 0.30 mm로
  고정했다. 초기 보정의 폭 2.397 mm는 이 기준에 실패했으며 허용오차를 늘리지 않았다.

0.15 mm 격자의 최종 목 폭·깊이는 **2.099103×1.008647 mm**, tip Y는 **7.0 mm**다.
출력은 20,436 vertices / 40,868 triangles이며 실제 단면 폐곡선 1개와 독립 표면
복셀화 중앙 통로가 유지됐다. 0.10 mm 격자는 해당 0.20 mm 허용오차로 검사했고,
회전·이동 및 기울어진 목 프레임도 검사했다.

이는 합성 fixture의 목 치수 보존 PASS다. 주머니 축별 치수는 위 후속 검사로 확인했다. 실제 ostium 정의,
접합 표면의 곡률·법선 연속성, 원위 부모 자체 충돌, 분기점·실제 Atlas·다중 병변
검증은 남아 있다. blending 가중치의 C1 성질을 최종 표면 전체의 매끄러움으로
확대하지 않는다. 결과 상태는 계속 CANDIDATE다.

최신 그림: `exports/saccular-neck-preservation/inspection.png`를 생성하고 열람했다.
최종 전체 Docker 회귀는 **613 passed / 3 skipped / 323 warnings**이며
[검사 기록](evidence/saccular-neck-validation.json)에 범위와 JUnit 해시를 저장했다.
건너뛴 3개는 컨테이너에서 Node를 사용할 수 없는 기존 UI 검사다.
아래 내용은 보정 전 후보의 구현·실패 근거다.

## 구현 범위

- 선언한 목 평면은 원형 반경 프로파일의 국소 벽 위에 있고 법선은 중심선에 수직이어야 한다.
- 높이 방향에서 폭·깊이별 타원체 프로파일을 구성한다. 목 아래 연장부는 목에서
  반경과 미분값이 이어지도록 구성하고, 아래 윤곽은 부모 내강 내부에 묻히는지 검사한다.
- compact polynomial smooth minimum으로 부모와 주머니를 합친 후 한 번의 등위면을 추출한다.
  별도의 닫힌 주머니를 원본 튜브에 겹쳐 그리는 방식이 아니다.
- 그리드 예산·해상도·경계 clipping·닫힌 양의 체적·단일 표면과 복셀 내강 연결을 검사한다.
- 다른 혈관과는 주머니의 보수적 지지 영역을 대조한다. 검사를 통과하지 못하거나
  다른 혈관의 형상이 미확인이면 거부한다. 같은 부모의 멀리 떨어진 구간과의 충돌은 미검사다.
- 기존 병변 및 분기부 부착은 아직 받지 않는다. 원본 사례를 변경하지 않는다.

```text
python -m vv_toolbox.case_cli saccular-surface source.snapshot.json spec.json candidate.npz --spacing-mm 0.15
```

NPZ에는 vertices_mm, faces, metadata가 있고 사례 revision과 명세 SHA-256을 기록한다.
기존 출력 파일은 덮어쓰지 않는다.

## 합성 fixture에서 확인한 결과

20 mm 길이·반경 2 mm의 직선 부모 혈관과 수동 주머니를 사용했다. 실제 Atlas나 환자
해부학의 재현이 아니다. `scripts/inspect_saccular_candidate.py`로 재현한다.

| 검사 | 결과 |
|---|---|
| 생성 표면 | 20,314 vertices / 40,624 triangles |
| 닫힌 단일 양의 체적 표면 | PASS |
| 실제 삼각형 단면의 폐곡선 | 1개 |
| 별도 표면 복셀화의 부모–목–주머니 중앙 통로 | PASS |
| 요청 tip Y / 생성 tip Y | 7.0 / 6.9625 mm |
| 요청 목 폭·깊이 / 해당 평면 실측 | [2.0, 1.0] / 약 [4.0792, 1.3657] mm |
| 요청 목 치수의 보존 | 미달: 지정 폭과 실측이 크게 다름 |
| 연속 내강 전체의 엄밀한 증명·self-intersection | NOT RUN |
| 실제 Atlas·분기점·다중 병변·임상적 타당성 | NOT RUN |

목 치수 실측은 생성 삼각형과 선언 평면의 교차 윤곽의 축별 범위다. 부모 벽에 접하는
평면에서 부모 형상·격자 및 smooth blending의 영향이 섞인다. 이 수치를 독립적으로
확정된 ostium 치수로 부르지 않는다. 현재 후보는 요청 목 치수를 충족한 동맥류로
수용할 수 없다. 다음 단계는 목 윤곽 제약과 실제 접합부 측정 정의를 보정하는 것이다.

그림 `exports/saccular-candidate/inspection.png`에서 생성 표면과 실제 단면을 열람했다.
[fixture 기록](evidence/saccular-surface-fixture.json)에 표면·그림 해시와 실측을 보관한다.

## 코드 검사

- 전체 Docker 회귀: 609 passed / 3 skipped / 321 warnings (목 아래 미분 연결 보정 전).
- 최종 집중 검사: 45 passed / 56 warnings. 미분 연결, 묻힌 윤곽, 분리 부착 거부,
  격자 예산, 주변 혈관 충돌 거부, 회전·이동된 좌표계, CLI 저장도 포함한다.
- [검사 기록](evidence/saccular-surface-validation.json). 테스트 PASS는 치수 수용 PASS가 아니다.
