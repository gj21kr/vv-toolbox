# 목 중심선·반경 결합 처리의 실제 비교

검사일: 2026-10-20. `scripts/inspect_joint_regularized_neck.py`를 Docker에서 실행했다. 원래 합성 목 사례, 중심선 단독, 반경 단독, 중심선→반경 결합 처리의 네 가지 표면을 비교했다. 원본 snapshot과 이전 산출물은 보존했다.

## 고정 조건

- 네 source-derived CCA/ICA edge만 변경하며 합성 bridge 2개는 유지한다.
- 중심선: sigma 2.0 mm, arc sample spacing 0.25 mm, 최대 변위 1.0 mm.
- 이후 반경: sigma 2.0 mm, arc sample spacing 0.25 mm, 최대 변화 1.0 mm.
- 원본 node·각 edge의 첫 두 점/마지막 두 점·끝점 반경은 유지한다.
- 동일 6개 edge의 합성 표면을 0.6 mm 격자로 생성한다.
- 원래 중심선에서 ±2 mm chord normal로 만든 124개 plane을 네 모델에 동일하게 적용한다. 각 변형 중심선 자체의 plane 결과도 별도로 기록한다.

수치 조건을 완화하거나 결과를 보고 조정하지 않았다. 결합 처리의 실제 최대 중심선 변위는 **0.822302 mm**, 최대 반경 변화는 **0.427141 mm**였다. 변경된 edge는 estimated/synthetic_estimate로 보존하며 해부학적 교정으로 승인하지 않는다.

결합 사례 revision은 `7583ab45163a08c803e6e76b25be63bd303c3c42e8a8beac519bbc97bdbebb8f`이다. `exports/synthetic-neck-case/joint-case.snapshot.json` 및 `joint-neck-surface.npz`에 저장했다.

## 동일 원래 plane 비교

TV는 각 접합 source-side -15…0 mm에서 1 mm 간격으로 측정한 면적 등가 반경의 절대 변화량 합이다. 이 지표가 전체 표면의 매끄러움이나 해부학 정확성을 의미하지 않는다.

| 구간 | 원래 TV mm | 중심선만 | 반경만 | 결합 |
|---|---:|---:|---:|---:|
| 왼쪽 CCA | 0.476950 | 0.503703 | 0.715883 | **0.287303** |
| 왼쪽 ICA | 0.391390 | 0.546079 | 0.347457 | **0.139332** |
| 오른쪽 CCA | 0.887534 | 1.002710 | 0.710958 | **0.640563** |
| 오른쪽 ICA | 0.301301 | 0.463814 | 0.355291 | **0.101178** |

결합 처리에서는 네 국소 구간의 측정 TV가 모두 감소했다. 변형 중심선 자체의 plane에서도 결합 결과는 각각 0.300916, 0.148983, 0.647320, 0.108666 mm로 원래 측정값보다 작았다. 단독 처리만으로는 네 구간 모두에서 개선되지 않았다.

비교 그림은 `exports/synthetic-neck-case/joint-four-way-comparison.png`이다. [전체 JSON](evidence/joint-regularized-neck.json)에 각 모델 snapshot/surface hash, 고정 plane·자체 plane별 124개 측정, parameter, 실제 변화량을 기록했다.

실제 저장 표면의 접합 확대 그림은 `exports/synthetic-neck-case/joint-attachments.png`이다. [표면 재검사 JSON](evidence/joint-neck-surface.json)에서 31,364 vertices·62,720 triangles, graph/mesh component 각각 2개, 각 component의 watertight·winding·positive volume을 확인했다. 표시용 ±15 mm crop은 저장 mesh의 열린 경계가 아니다. 원래 표면은 `neck-surface-attachments.png`에 보존되어 있다. 시각적 요철 변화는 후보 검토 자료이며 정량 전체 매끄러움 승인으로 사용하지 않는다.

## 연결과 충돌 후보

네 bridge 부착점의 위치차·반경차는 0이며 sampled tangent 각도는 최대 약 0.503°로 명시한 5°/1e-6 mm 기준 PASS다. 선택한 6개 edge 표면의 topology 검사도 PASS다.

두 bridge와 변경된 네 edge를 focus로 전체 사례 geometry와 nonincident capsule 검사를 수행했다. 이전과 동일 범위의 원래 검사 근거를 parent revision·검사 선택/focus 목록으로 확인하고 파일 hash를 기록해 재사용했다.

원래 17개 의심 접촉 쌍 중 16개가 계속 검출되었고 신규 후보는 0개였다. `FJ1663:e1–FJ1682:e0` 한 쌍은 이번 형상에서 더 이상 검출되지 않았다. 이것은 capsule witness 차이이며 실제 해부학적 접합이나 mesh collision 해소 판정이 아니다. 16개 후보가 남아 전체 간격 수용 상태는 UNKNOWN이다.

## 판정

이번 결과는 **고정 조건에서 네 국소 구간의 반경 요동 지표 개선을 확인한 실험**이다. 자동 기본값으로 채택하지 않았다(`default_adoption: NOT ACCEPTED`). 전체 표면의 정량 매끄러움·삼각형 교차·해부학적 수용은 미확정이며, 원본 atlas를 교정했다는 의미도 아니다. 향후 적용에는 남은 접촉 후보의 근거 검토와 전체 표면 검증이 필요하다.
