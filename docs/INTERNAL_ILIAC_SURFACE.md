# 우측 장골 합성 분기부 표면 검사

## 입력과 변경 이력

검사 대상은 `synthetic-common-iliac-trunk` snapshot이며 revision은
`3028bfcbbed7082d18b01610e596a4b27fd4458cf69fa769a0e236d854c9d722`다.
원본 FJ3565:e1의 1.385641 mm 추출 가지는 별도 합성 모델에서 명시적으로 제외했다.
원본 edge와 제외 근거는 snapshot 이력에 보존한다. 원본 Atlas의 해부학적 분지가
없다고 확정한 것은 아니다. 두 총장골 경로의 원래 표본을 이어 붙였으며 기존
bridge의 끝점 참조를 갱신했다. 전체 20개 bridge 부착 연속성 검사는 PASS다.

## 국소 표면 결과

총장골·외장골·내장골의 외부 arm 3개와 내부 합성 connector 3개를 선택했다.
접합 영역 길이는 기존 정책 `3 × 최대 부착 반경 + 2 × 격자 간격`으로 정했고,
검사 결과를 본 뒤 범위를 넓히지 않았다. 격자 간격은 0.6 mm다.

- 영역 밖 서로 다른 edge의 선분 쌍 116,918개 검사 PASS. 영역 내부 62,959쌍은 제외했다.
- 비국소 자기 간격 검사 PASS. 국소 접힘과 최종 mesh 충돌은 검사하지 않았다.
- 표면 25,871 vertex / 51,738 triangle. 닫힘·일관된 방향·양의 체적 PASS.
- 저장된 mesh 독립 확인: component 1개, Euler characteristic 2, watertight true.
- 주변 capsule 검사의 raw 접촉 후보는 15쌍이다. 선택된 6개 edge끼리의 쌍도 포함되므로
  이를 주변 혈관 충돌 15개로 해석하지 않는다. 실제 표면 충돌 여부는 미확정이다.

두 시야의 생성 그림을 확인했다. 주 줄기의 반경/중심선 요철이 여전히 보이며,
시점에 따른 분지 중첩만으로 관통 여부를 판정하지 않는다. 매끄러움 수용과
접합 영역 내부 충돌 검사는 미완료다. 앱 기본 모델에는 적용하지 않았다.

## 재현과 근거

- `scripts/inspect_internal_iliac_surface.py`: 입력 hash, 국소 및 주변 간격, 표면 생성 검사.
- `scripts/render_internal_iliac_surface.py`: 저장된 실제 mesh의 두 방향 그림.
- [검사 JSON](evidence/internal-iliac-surface-inspection.json).
- [원본 추출 가지 검사](COMMON_ILIAC_SPUR_INSPECTION.md).
- [합성 trunk 변경 근거](evidence/common-iliac-trunk-simplification.json).
- Docker에서 trunk simplification, route roles, junction regions 관련 테스트 **32 passed**.

표면·그림은 `exports/internal-iliac-surface/`에 보존한다. 그림은 형상 검토 자료이며
해부학 정확성 검증이 아니다. 원본 입력 불변 검사 PASS. 해부학적 수용 UNKNOWN.
