# 동일 Atlas 요청의 검사 재사용 전후 비교

원래 요청과 같은 FJ1692:e0, 중앙 50% 구간, 배율 0.9, 이동 한도 0.3 mm, 단면 배율 허용오차 0.02로 재실행했다. 원래 결과 파일을 보존하고 최적화 결과를 별도 저장했다.

| 항목 | 이전 | 검사 재사용 후 |
|---|---:|---:|
| 실제 HTTP 요청 처리 시간 | 255.473초 | 119.591초 |
| 응답 | 200 CANDIDATE | 200 CANDIDATE |
| 원본 상태 보존 | 확인 | 확인 |

한 쌍의 실행에서 관측된 감소는 **53.19%**다. 반복 측정 평균이나 모든 혈관의 속도 향상으로 확대하지 않는다.

비교 결과:

- 요청 파라미터 정확 일치.
- 후보 정점과 face 배열 정확 일치.
- 단면별 목표 검사 결과 정확 일치.
- 이웃별 표면 접촉·포함 검사 결과 정확 일치.
- 유효성 검사 수행 10회, 동일 형상 검사 결과 재사용 22회.

실제 계산 중 `/api/state`가 `interval_preview_busy=true`와 함께 약 247 ms에 응답했다. 이 값은 한 번의 상태 조회 관측이며 지연 보장값은 아니다. 미리보기 작업이 끝나면 실행 표시를 해제한다.

## 근거

- [최적화 실행 결과](evidence/live-interval-preview-optimized.json)
- [이전 실행 결과](evidence/live-interval-preview.json)
- [관련 회귀 검사](evidence/optimized-preview-regression-tests.xml): 30개 PASS.
- 실행: `node scripts/inspect_live_interval_preview.cjs --optimized`
- 후보: `exports/live-interval-preview-optimized/candidate.json`

최적화와 상태 조회 필드를 데모 서버에 반영했다. 119.6초는 여전히 대화형 편집에 길며, 단계별 비용 분석과 추가 개선이 필요하다. 검사 조건·범위를 줄여 속도를 얻지 않았고, 실제 형상 적용·저장 또는 전체 모델 완료를 선언하지 않는다.
