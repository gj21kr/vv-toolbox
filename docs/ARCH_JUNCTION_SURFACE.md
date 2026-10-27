# 대동맥궁–좌측 경동맥 합성 접합 표면

기존 합성 사례를 변경하지 않고 명시적 접합 영역으로 선택 6개 edge의 표면을 생성했다. 이전 검사의 두 접촉 후보를 전체적으로 무시하지 않고, 선언한 접합 구간 내부의 합류만 허용한다. 영역 밖과 무관 혈관 간 검사는 유지한다.

## 선언과 범위

- 입력 revision: `2b77c5e97f7d7b6c51625b82bb5c8ef7165fb12eb3979a64c2a15646d9c264ae`.
- 궁 양쪽 arm과 CCA 시작의 허용 호길이: 각각 **36.014590 mm**. 기존 수치 정책 `3 × 부모 반경 + 2 × grid spacing`을 적용했다. 해부학적 ostium 크기 측정값이 아니다.
- 내부 합성 연결 길이 **5.739700 mm**는 전체를 같은 접합 영역에 포함한다. 원본 혈관 전체를 내부 연결로 취급하지 않는다.
- 목 연결 양끝에는 기존 degree-2 수치 영역을 각각 적용했다.
- 모든 선언은 사례 해시, 정확한 edge와 endpoint, 근거 및 이유에 결합한다. 영역 경계에서 polyline interval을 나누고 두 interval이 같은 영역 안에 있을 때만 검사를 제외한다.

## 실제 실행 결과

| 항목 | 결과 |
|---|---|
| 선택 edge 사이 영역 밖 capsule 검사 | PASS: 98,742개 interval 쌍 검사, 접촉 후보 0개 |
| 동일 영역 내부 제외 | 14,593개 interval 쌍; 내부 형상 품질을 확인한 수가 아님 |
| 표면 생성 | PASS: 정점 43,728개, 삼각형 87,452개 |
| 닫힘·방향·양의 체적 | PASS |
| 원본 합성 snapshot 불변 | PASS |
| 실제 생성 메시 단면 | 서로 다른 Z의 6개 단면 생성 및 열람 |
| 전체 Atlas 주변 충돌 | NOT RUN |
| 접합부 내부 상세 형상·최종 메시 자기교차 | NOT RUN |
| 해부학적 승인·기본 적용 | UNKNOWN / NOT ACCEPTED |

단면에서 대동맥궁에 해당하는 긴 윤곽이 위쪽으로 올라가며 CCA의 작은 윤곽으로 전환하는 것을 확인했다. 이것은 생성 표면의 관찰이며 원본 내강 복원이나 임상 정확성 검증이 아니다. 기존 원본 중심선의 계단형 변화도 유지한다.

## 재현과 검사

Docker에서 `PYTHONPATH=src python scripts/inspect_arch_junction_surface.py`를 실행한다. 결과는 [검사 JSON](evidence/arch-junction-surface.json), 로컬 `exports/arch-junction-surface/surface.npz`, `regions.json`, `junction-sections.png`에 보관한다. 원본·기존 실패 기록은 보존했다.

`build_case_surface(..., junction_regions=...)`는 명시된 영역 검사를 선택적으로 사용한다. 미지정 경로는 기존 정책을 유지한다. 잘못된 해시·끊어진 영역·영역끼리의 중첩·임의 원본 edge 전체 면제·영역 밖 재교차는 거부하거나 UNKNOWN으로 차단한다. 내부 허용 영역이 안전하다는 자동 승인은 없다.

Docker 회귀: `test_junction_regions.py`, `test_case_surface.py`, `test_geometry_quality.py` **53 passed**. 생성 가능한 합성 분기 fixture와 영역 밖 재교차 시 표면 거부를 함께 확인했다. 첫 새 fixture는 지원 범위보다 작은 grid spacing으로 실패했고, 지원되는 반경 0.4 mm/spacing 0.2 mm로 fixture를 수정했다. 실제 사례의 0.6 mm spacing과 검사 허용 범위는 변경하지 않았다.
