# 우측 장골 연결의 표면·주변 검사

대상 revision은 `ac6663b2ad015ed1031d35ff61ba84bcb35be5838656397e59d79107d2cdf8f5`다. 비교 기준과 대상 edge, 1.2 mm 여유·0.6 mm 격자·2,000,000 interval pair 상한을 [검사 선언](evidence/right-iliac-inspection-spec.json)에 고정했다.

## 결과

- 주변 후보: **4→5쌍**, 기존 4쌍 유지, 신규 1쌍.
- 신규: 우측 내부장골동맥 `FJ3569:e0`–`estimated_R_CIA_EIA_continuation`.
- 국소 표면 생성: **FAIL(검사 차단)**. 새 표면을 게시하지 않았다.
- 원인: `R-CIA-retained`와 새 continuation의 접합 collar가 짧은 edge 전체를 소비해 검사 가능한 외부 구간을 남기지 않는다. `collar_consumed_edge_pairs` 1쌍이며 실제 검사된 pair의 `potential_contacts`는 0개다. 따라서 이것을 확정된 표면 관통이나 국소 형상 충돌로 해석하지 않는다.
- 접합 gap 검사: 15,084쌍 확인·2,004쌍 collar 내부 면제, 상태 UNKNOWN.

collar 값은 기존 정책 `3×끝점 최대 반경+2×격자 간격`에서 13.952708/14.829075 mm다. 이 기준을 줄여 통과시키지 않았다. 내부장골 분지의 실제 원본 관계와 짧은 총장골 추출 구간을 함께 검토하여 접합 구조를 구성해야 한다.

## 재사용 가능한 검사 도구

`scripts/inspect_candidate_geometry.py SPEC REPORT ARTIFACT_DIRECTORY`는 다음을 수행한다.

1. baseline/candidate snapshot revision과 원본 source identity 확인.
2. 명시 focus와 전체 imported case 혈관 사이의 보수적 capsule 검사.
3. 실제 존재하는 edge 사이에 선언한 ID 정규화만 적용해 주변 쌍 비교.
4. 국소 표면 생성 및 실패 시 기본 shared-junction 진단 저장.
5. 입력 불변·검사 선언/표면 해시 기록.

원본/spec 덮어쓰기, 오래된 revision, 존재하지 않는 정규화 대상은 거부한다. Docker 거부 경로 테스트 **3 passed**. 실제 우측 장골 검사는 진단 확장 후 다시 실행했다. [전체 결과](evidence/right-iliac-geometry-inspection.json).

도구의 종료 성공은 보고서 작성 성공이며 geometry PASS를 뜻하지 않는다. 판단은 보고서 각 상태를 사용한다. 전체 원본 누락 형상, 최종 mesh 충돌, 접합 collar 내부 상세 품질은 이 검사로 승인하지 않는다. 앱 기본 적용은 NOT ACCEPTED다.
