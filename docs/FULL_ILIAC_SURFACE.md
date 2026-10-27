# 전체 외장골·고환동맥 후보 표면과 상호 분리 검사

## 생성 범위

원본 프로파일 보정 snapshot
`b6417e63a06dd58c4df6bd127d54ad84190499a09746c7509b2715a86357ac20`의
`R-EIA-retained`와 `FJ3617:e0` **전체 경로**를 0.15 mm 격자로 생성했다.
기존 0.6 mm 격자 결과로 대체하거나 ROI만 잘라 검사하지 않았다.

생성기의 최소 명시 격자 간격을 0.2→0.1 mm로 확장했다. 기본 격자 선택과
`최소 반경의 75% 이하` 조건은 유지했다. 비접합 간격 규칙도 `2 × 격자 간격`
그대로이며 이번 계산에서는 0.3 mm다. 기존 1.2 mm 정책에 통과한 것으로
소급 해석하지 않는다. 정밀 격자를 사용한 별도 후보 검사다.

전체 bounding grid 상한 661,743,360 voxel, 명시 작업 예산 1,000,000,000 voxel.
실제 생성기는 slab 및 국소 XY 범위를 사용한다. 이 상한을 동시에 할당한 메모리나
실측 peak memory로 표시하지 않는다.

## 표면 결과

- 전체 322,565 vertex / 645,122 triangle.
- 외장골 component: 176,315 vertex / 352,626 triangle.
- 고환동맥 component: 146,250 vertex / 292,496 triangle.
- 두 component 각각 닫힘, 일관된 방향, 양의 체적 PASS; Euler characteristic 2.
- 선택된 경로 간격·비국소 자기 간격 검사 PASS. 국소 접힘 검사는 포함하지 않는다.

## 저장된 삼각형 표면 상호 검사

각 삼각형을 중심점과 최대 꼭짓점 거리의 구로 감쌌다. 첫 표면의 각 삼각형에서
상대 표면의 가장 가까운 삼각형 중심까지 거리로부터 자기 구 반경과 상대 구
최대 반경을 뺀 보수적 전역 하한은 **+0.095657 mm**였다.

이 양수 하한은 103,141,694,496개 가능한 두 표면 간 삼각형 쌍 전체의 교차를
배제한다. 그 수만큼 직접 pair 연산을 실행한 것이 아니라 KD-tree와 보수적
상한을 이용한 증명이다. 두 component 각각에서 상대 bounding box 밖의 실제
꼭짓점도 확인하여 한쪽 component 전체가 다른 쪽에 포함된 경우를 배제했다.

따라서 **저장된 두 표면 사이의 교차·전체 포함은 배제됨(PASS)**이다. 각 표면
자체의 삼각형 자기 교차, 다른 Atlas 혈관과의 최종 표면 충돌, 해부학적 수용은
검증하지 않았다. 이것을 전체 동맥계 충돌 PASS로 확대하지 않는다.

실제 mesh의 Z 850/855/860/875/880/885 mm 단면을 직접 확인했다. 각 위치에서
두 component의 윤곽이 분리돼 있다. 앱 기본 모델은 변경하지 않았다.

## 산출물과 테스트

- `scripts/inspect_full_iliac_surface.py`, [생성 검사](evidence/full-iliac-surface.json).
- `scripts/verify_full_iliac_mesh.py`, [삼각형 분리 근거](evidence/full-iliac-mesh-separation.json).
- `exports/full-iliac-surface/surface.npz`, `mesh-sections.png`.
- mesh SHA-256: `fe6c783befdf3b0d9e57ef934e0df3fc7ffce47dee627809a3efc4989f7476fc`.
- 정밀 격자/기존 사례 표면 검사 11 passed; 분리·중첩·전체 포함 certificate 검사
  2 passed. 전체 회귀 검사 결과는 아니다.
- 원본 snapshot 및 저장 mesh 불변 확인 PASS. 임상적 검증 NOT RUN.
