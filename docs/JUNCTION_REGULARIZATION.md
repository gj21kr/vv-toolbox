# 양쪽 구간을 함께 다듬는 합성 연속 접합

`smooth_continuation_node`는 명시된 degree-2 node의 양쪽 edge를 하나의 arc-length 경로로 처리한다. 공유 위치와 반경을 동시에 갱신하고 원래 edge 방향으로 되돌려 저장한다. 원본은 보존한다.

## 범위와 제약

- synthetic 사례, degree-2 접합, 각 3점 이상의 열린 중심선만 처리한다.
- 명시된 sigma, 물리 격자 간격, 양쪽 support 길이, 최대 위치·반경 변화량을 요구한다.
- Gaussian smoothing은 균일 arc-length 격자에서 계산하며 접합으로부터 support 경계까지 smoothstep으로 가중치를 0으로 줄인다. 바깥 두 endpoint chord는 보존한다.
- 반경 불연속이 있는 접합의 초기 공통 반경은 두 값의 평균이다. 최종 변화량은 양쪽 원본 반경 각각과 비교한다.
- 한계를 넘으면 입력을 변경하지 않고 실패한다. 반경·위치가 가까워졌다는 이유로 해부학적 승인을 부여하지 않는다.
- 분기 node, 병변을 가진 edge, declared bridge는 이 연속 접합 연산에서 제외한다. 이는 해당 기능의 최종 지원 완료가 아니다.
- 기존 형상·경로 검사 결과를 무효화하고, 원본 두 edge와 node·파라미터·실측 변화량을 이력에 남긴다.

## 좌측 총장골–외장골 실제 사례

고정 설정: sigma 2 mm, support 양쪽 6 mm, 격자 0.25 mm, 최대 위치 변화 1 mm, 최대 반경 변화 1 mm. 실행 중 설정을 조정하지 않았다.

| 측정 | 전 | 후 |
|---|---:|---:|
| 접합에서 인접 표본 chord 각도 | 60.0000° | 2.1555° |
| 접합 반경 차이 | 0.335881 mm | 0 mm |
| 최대 중심선 이동 | — | 0.421308 mm |
| 최대 반경 변화 | — | 0.492668 mm |

각도는 표본 chord의 유한 차분이며 연속 곡선 미분값이나 모든 지점의 곡률 검사가 아니다. 공유 node는 두 edge와 동일하게 이동하며, 원본 사례와 다른 edge는 변하지 않았다.

- 스크립트: `scripts/smooth_left_iliac_junction.py`.
- [검사 기록](evidence/left-iliac-junction-smoothing.json).
- 사례: `exports/synthetic-left-iliac-smoothed/case.snapshot.json`.
- revision: `23b547d31386462dbae203c4f60f67c0c363962878db538af88fe657570f5621`.
- Docker 접합 smoothing·node 통합 검사 **10 passed**. 방향 반전 등가성, 외부 chord 보존, 공유 반경·위치, 초과 변화 거부, 분기점 거부를 포함한다.

표면·주변 간격 검사는 NOT RUN이며 해부학적 수용은 UNKNOWN이다. 앱 기본 모델을 변경하지 않았다.
