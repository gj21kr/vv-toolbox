# 혈관 간격과 접합부 밖 재교차 검사

`geometry_quality.screen_nonincident_clearance`는 연결 node를 공유하지 않는 서로 다른 edge의 polyline 구간 사이 최소 거리를 계산한다. 끝점 간 거리만 사용하지 않으므로 긴 구간의 중간 교차도 검사한다. 각 구간의 최대 끝점 반경으로 capsule 외곽을 감싸며, 중심선 최소 거리에서 두 반경을 뺀 값을 clearance lower bound로 사용한다.

명시한 mm margin보다 작거나 같은 값은 실제 삼각형 표면 충돌 확정이 아니라 potential contact, UNKNOWN이다. 범위가 보수적이므로 taper가 큰 구간은 실제 표면이 떨어져 있어도 검토 대상으로 남을 수 있다. 전체 AABB 간격으로 안전하게 제외한 쌍도 개수를 기록한다. 검사 횟수 상한에 도달하면 UNKNOWN이며 부분 검사로 PASS 처리하지 않는다.

## 표면 생성과 연결

합성 표면 생성 전 선택 edge에 이 검사를 적용한다. 수치 margin은 격자 간격의 두 배로 기록한다. UNKNOWN이면 표면 union 생성을 중단한다. 이 margin은 임상 간격이나 생성 표면 오차의 증명된 상한이 아닌 공학적 예방 설정이다.

PASS의 범위는 검사한 capsule 외곽뿐이다. 다음 항목은 아직 검사하지 않았다.

- 접합부 안의 겹침과 fillet 형상: 아래 명시적 collar 안은 허용 영역으로 남는다.
- 한 edge 안의 국소 접힘 및 최종 표면 자기 교차. 아래 비국소 재접촉 검사는 별도로 수행한다.
- 생성된 삼각형 표면 자체의 교차와 분기 fillet으로 확장된 영역.

검사 결과에 건너뛴 shared-node 쌍을 저장하고 최종 표면 충돌·자기 교차를 NOT RUN으로 유지한다. 현재 검사를 전체 혈관 충돌 없음으로 확대하지 않는다.

## 공유 분기점의 원위 재교차

`screen_junction_clearance`가 같은 node에 연결된 서로 다른 edge를 추가 검사한다. 호출자가 node별 mm collar를 명시하며, 각 edge의 해당 끝에서 **호길이**로 측정한다. 두 검사 구간이 동일한 공유 node의 collar 안에 모두 들어갈 때만 해당 쌍을 제외한다. collar 경계에서 원래 polyline 구간을 나누고 반경을 보간하므로, 표본점이 드문 긴 구간 전체를 접합부로 잘못 제외하지 않는다. 한쪽만 collar 안인 구간 쌍도 검사한다.

표면 생성기는 합성 정책으로 `3 × 참여 edge의 최대 끝점 반경 + 2 × 격자 간격`을 collar 길이로 사용하며 metadata에 기록한다. 임상적 접합 범위나 원본 주석이 아니다. collar가 edge 전체를 소비하면 UNKNOWN으로 중단한다. 누락된 collar는 입력 오류이며, 허용 쌍을 포함한 검사 예산 소진은 UNKNOWN이다. 정상 분기까지 보수적으로 차단할 수 있으므로 현재 수용 범위를 전체 해부 모델로 확대하지 않는다.

비접합 검사·공유 접합 검사·아래 자기 재접촉 검사 모두 PASS일 때만 표면을 생성한다. 공유 접합 검사 결과의 PASS는 collar **밖**의 검사된 capsule 간격만 의미한다. collar 안과 최종 삼각형 표면 교차는 미검증이다.

## 동일 혈관의 비국소 재접촉

`screen_self_clearance`는 동일 edge의 서로 다른 polyline 구간들을 검사한다. 호출자가 명시한 호길이 window보다 가까운 점 쌍은 정상적인 이웃 내강의 겹침을 허용하는 국소 범위로 제외한다. 표면 생성기의 정책은 `4 × 해당 edge 최대 반경 + 2 × 격자 간격`이며, 해부학적 수치가 아닌 합성 검사 정책으로 metadata에 기록한다.

단순히 이웃 interval을 통째로 제외하지 않는다. 두 interval의 연속 매개변수 영역을 호길이 차이 조건으로 자른 뒤, 그 안의 최소 공간 거리를 계산한다. 따라서 성긴 중심선의 서로 이웃한 긴 interval이 되꺾이는 경우도 검사한다. 각 interval의 최대 반경 capsule을 사용하므로 접촉 가능성은 UNKNOWN이며 실제 삼각형 교차 확정이 아니다. 검사 예산 소진도 UNKNOWN으로 표면 생성을 차단한다.

검증은 긴 구간 내부 자기 교차, 인접 긴 구간의 역주행, 평행 몸통 재접근, 촘촘한 직선 경로, 방향 반전·표본 추가, 3D 분리 및 예산/입력 오류를 포함한다. 높이를 올린 초기 fixture는 두 구간의 급한 접힘 때문에 clearance lower bound **-0.4467589904 mm**였으므로 UNKNOWN을 유지했다. 별도 충분히 분리된 3D fixture는 PASS다. 검사 조건을 완화해 초기 fixture를 통과시키지 않았다.

Docker 간격·표면·배치 검사 **29 passed, 56 warnings, 3.78 s**. [실행 근거](evidence/self-clearance-validation.json). 비국소 capsule 검사 통과를 국소 접힘 없음, 최종 표면 자기 교차 없음 또는 해부학적 타당성으로 확대하지 않는다. 전체 실제 해부 모델 적용은 NOT RUN이다.

추가 합성 검사: 정상 접합 허용, 먼 위치의 재교차와 표면 생성 차단, edge 방향/표본 밀도 변화, edge 전체를 덮는 collar 거부, 누락 collar/예산 소진, 정상 접합의 실제 닫힌 표면 생성과 정책 기록. Docker 간격·표면·batch 통합 회귀 **23 passed, 56 warnings, 3.44 s**. [실행 기록](evidence/junction-clearance-validation.json).

Docker 검사 8개: 구간 내부 교차·평행·끝점 최소 거리·입력 순서 대칭성, 끝점 간 거리로 놓칠 교차의 표면 생성 차단, margin 적용, 공유 node 검사 제외 명시, 검사 예산 소진 UNKNOWN. 표면 생성 회귀 4개와 함께 검사한다.

## 변경 혈관과 전체 주변 혈관의 검사

`screen_nonincident_clearance(..., focus_edge_ids=[...])`는 선택한 모든 주변 edge를 유지하면서 적어도 하나의 focus edge를 포함한 쌍을 검사한다. 새 연결부와 원본 전체의 간격 검사에 사용한다. focus를 생략하면 기존처럼 선택한 모든 edge 쌍을 검사한다. 보고서의 `coverage`는 전체 선택 ID와 focus ID, 쌍 선택 정책을 보존하며 예산 소진 시에도 포함된다.

이 검사에서 기존 혈관끼리의 충돌은 검사 범위 밖이다. 중심선이 없는 edge를 입력하면 오류를 반환하며, 실제 검사 스크립트가 이를 별도로 기록할 경우 전체 범위의 상태는 UNKNOWN으로 유지해야 한다. 공유 접합과 자기 교차는 별도 검사한다.

Docker 간격·표면·연속성 검사 **40 passed, 51 dependency deprecation warnings**. 주변 충돌을 빠뜨리지 않는지, 무관한 기존 혈관 쌍과 검사 범위를 혼동하지 않는지, 잘못된 focus 입력을 거부하는지 확인했다.
