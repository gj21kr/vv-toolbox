# 목 연결 표면 요철 진단과 고정 반경 실험

검사일: 2026-10-20. 원본 Atlas와 이전 합성 사례·표면은 보존했다. `surface.py`는 변경하지 않았다.

## 원인 분리

실제 neck 사례의 접합은 모두 arterial degree 2이다. `_arterial_junctions`는 degree 3 이상에만 fillet을 부여하며, 이 사례의 모든 edge는 explicit radius profile이므로 접합 반경 평균 보정도 실행되지 않는다. 따라서 현재 목 요철을 degree-2 fillet artifact로 보고 수정할 근거는 없다.

`tests/test_synthetic_neck_smoothing.py`는 같은 constant/variable radius 경로를 하나의 edge와 두 개의 edge로 표현한 출력 vertices/faces가 정확히 같음을 검사한다. 일정 반경 접합에서 추가 팽창이 없고 입력 반경·좌표가 불변임을 확인했다. Docker 검사 **2 passed / 60 warnings**. 이는 실제 전체 모델 매끄러움 판정이 아니다.

## 실제 표면 단면 측정

`scripts/inspect_neck_surface_bulge.py`는 네 접합에서 arc offset -15…15 mm를 1 mm마다 측정한다. 음수는 원본 파생 구간, 양수는 합성 연결이다. 중심선 위치와 ±0.3 mm chord 방향으로 plane을 만들고, 가장 가까운 닫힌 mesh 단면의 면적 등가 반경을 계산한다. 총 124개 단면을 측정했다.

[원래 측정 JSON](evidence/neck-surface-bulge.json) 및 `exports/synthetic-neck-case/neck-surface-radius-profiles.png`에 입력 profile과 표면 반경을 함께 보관했다. 원본 파생 centerline과 반경 모두 voxel 추출 영향을 받는다. 국소 plane normal 자체의 변화도 단면 반경의 요동에 기여할 수 있으므로 이 수치를 순수 표면 roughness로 해석하지 않는다.

## 별도 합성 반경 regularization

`scripts/inspect_regularized_neck_surface.py`에서 네 원본 파생 CCA/ICA edge만 별도 합성 사례로 변환했다. sigma **2.0 mm**, sample spacing **0.25 mm**, 최대 반경 변화 **1.0 mm**를 실행 전에 고정했다. 허용값 완화 없이 생성에 성공했고 실제 최대 변화는 **0.421582 mm**였다. 모든 중심선 좌표와 끝점 반경을 보존했다. 변경된 반경의 provenance는 estimated/synthetic_estimate이며 해부학 교정으로 승인하지 않는다.

출력은 `exports/synthetic-neck-case/regularized-case.snapshot.json`, `regularized-neck-surface.npz`이다. 표면 격자는 전과 동일한 0.6 mm이고 같은 6개 edge를 사용했다. 원래 124개 plane의 위치·normal이 새 측정과 정확히 같음을 확인했다.

아래 TV는 source-side -15…0 mm의 1 mm station 간 절대 반경차 합이다. 물리적 surface smoothness 표준이 아닌 동일 조건 비교 지표다.

| 원본 파생 구간 | 입력 profile TV 전→후 mm | 표면 등가 반경 TV 전→후 mm |
|---|---:|---:|
| 왼쪽 CCA FJ3483:e0 | 0.832352 → 0.289967 | 2.238454 → 2.265579 |
| 왼쪽 ICA FJ1682M:e0 | 1.320009 → 0.146603 | 0.768316 → 0.700704 |
| 오른쪽 CCA FJ3564:e0 | 1.960533 → 1.409849 | 2.130622 → 2.040138 |
| 오른쪽 ICA FJ1682:e0 | 1.084133 → 0.106650 | 0.668010 → 0.753187 |

입력 반경의 변화량은 네 구간에서 줄었지만 표면 측정값은 두 구간에서 증가했다. **반경 smoothing만으로 실제 surface 요철이 해결되었다고 판정할 수 없다.** 국소 중심선 방향과 단면 측정 방향, envelope 형상이 함께 작용하는지 다음 검사가 필요하다. 불리한 결과도 [전후 비교 JSON](evidence/regularized-neck-surface.json)에 그대로 기록했다.

전후 그림: `exports/synthetic-neck-case/regularized-radius-comparison.png`. 원본 snapshot 불변과 수치변환 실행은 PASS, 표면 매끄러움 수용은 UNKNOWN이다. 변경 후 전체 Atlas 간격 검사, 최종 표면 collision과 해부학적 수용은 이번 실험에서 수행하지 않았다.

## 단면 방향 민감도 추가 검사

기존 ±0.3 mm normal 결과를 보존한 채 `--normal-half-window-mm 2.0`으로 동일 네 접합·124개 station을 다시 검사했다. 원래/regularized geometry는 전혀 바꾸지 않고 측정 plane의 normal만 더 긴 chord로 계산했다. 각 실험 안에서 before/after plane은 정확히 같다. [별도 JSON](evidence/regularized-neck-surface-normal2.json)과 `exports/synthetic-neck-case/regularized-radius-comparison-normal2.png`를 생성했다.

| 구간 | ±2 mm normal의 surface TV 전→후 mm |
|---|---:|
| 왼쪽 CCA | 0.476950 → 0.715883 |
| 왼쪽 ICA | 0.391390 → 0.347457 |
| 오른쪽 CCA | 0.887534 → 0.710958 |
| 오른쪽 ICA | 0.301301 → 0.355291 |

동일 표면인데 normal window만 바꾸어도 측정 TV가 크게 달라졌다. 이는 앞 측정값에 단면 방향 민감도가 포함됨을 보여준다. 더 긴 normal에서도 두 구간은 개선·두 구간은 악화되어 반경 regularization만으로 전반적인 surface smoothness 향상을 주장할 근거는 없다. normal window 변경을 geometry 개선으로 표시하지 않으며 매끄러움 수용은 UNKNOWN으로 유지한다.
