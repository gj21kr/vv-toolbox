# 하복벽동맥 포함 합성 접합 검사

대상 revision: `363551e43ad9b7d6a33e4853a9fa61e12ae76024f31d7c9b61cf34e14e8263df`.

## 접합 영역과 표면

외장골 유지 구간, 외장골–대퇴 bridge의 두 child, 하복벽 연결, 원본 하복벽 및 대퇴 유지 구간의 6개 edge를 검사했다. 짧은 bridge child 전체를 접합 영역 내부 연결로 포함할 때 reciprocal split 계보와 동일 내부 node를 확인하도록 검사기를 확장했다. 외부 arm 개수·연결성·영역 중복·영역 밖 접촉 제한은 그대로 유지한다.

기존 수치 정책 `3 × 끝점 최대 반경 + 2 × 격자 간격`을 사용했다. 짧은 내부 연결 두 개를 통과하는 복합 영역과 대퇴 부착 영역을 선언했다. 이는 실제 해부학적 ostium 크기가 아니다.

- 영역 밖 interval 쌍 **458,488개 검사 PASS**, 영역 안 **27,275쌍 면제**. 면제 영역의 상세 품질은 검증 완료가 아니다.
- spacing **0.6 mm**, **72,061정점 / 144,118삼각형**의 닫힌 표면 생성 PASS.
- 실제 표면 단면 Z=826/829/832/835/838/841 mm 6개를 열람했다. 앞의 세 단면은 윤곽 1개, 뒤의 세 단면은 2개다. 생성 분기에서 주혈관과 daughter가 갈라지는 모습이며 원본 내강 검증을 뜻하지 않는다.
- 관련 Docker 회귀 **35 passed / 52 dependency deprecation warnings**. 잘못된 reciprocal 계보 거부와 기존 영역 밖 접촉 검사도 포함한다.

## 주변 비교

검사 사례에 포함된 전체 중심선을 장애물로 사용했다. 신규 분지를 포함하는 동일한 역할 범위를 비교하기 위해 기준 focus에도 하복벽동맥을 포함했다. 생성 bridge의 두 child만 기존 bridge ID로 정규화한다.

주변 후보 **5쌍 유지, 신규 0쌍, 제거 0쌍**이다. 기존 쌍은 대퇴 유지 구간–FJ2137:e1/FJ2170:e0 및 외장골 유지 구간–FJ3565:e0/FJ3569:e0/FJ3617:e0다. 모두 이번 수정 밖의 연결·접촉 검토 대상으로 남는다.

이전 검사에서 주변 접촉이던 하복벽–생성 연결은 이번에 명시적 분지 접합으로 구성되어 **국소 영역 검사 대상**이 됐다. 단순히 주변 접촉 수가 줄었다고 충돌이 해소됐다고 판정하지 않는다. 영역 내부 상세 품질·최종 mesh 충돌·해부학적 수용은 미확인이다.

## 산출물

- `scripts/inspect_epigastric_candidate.py`, [검사 JSON](evidence/epigastric-candidate-inspection.json).
- `scripts/plot_epigastric_surface.py`, [단면 JSON](evidence/epigastric-surface-sections.json).
- `exports/epigastric-candidate-inspection/surface.npz`, `sections.png`.

입력 snapshot 불변 및 결과 해시를 기록했다. 앱 기본 적용은 NOT ACCEPTED다. 전체 대퇴–뇌혈관 경로 완료 판정은 아니다.
