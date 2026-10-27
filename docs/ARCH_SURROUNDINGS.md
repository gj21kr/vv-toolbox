# 합성 궁–경동맥 주변 혈관 검사

기존 목 연결 사례 1,083개 edge와 궁–경동맥 합성 사례 1,085개 edge를 각각 주변 장애물 집합으로 검사했다. 변경·선택 경로가 포함된 쌍만 검사하며, 나머지 장애물끼리의 충돌을 검사한 것은 아니다.

## 비교 결과

| 항목 | 기준 사례 | 합성 사례 |
|---|---:|---:|
| 검사한 polyline interval 쌍 | 447,024 | 506,685 |
| 선택 경로 밖 혈관과의 접촉 후보 쌍 | 19 | 19 |
| 새로 검출된 주변 접촉 쌍 | — | 0 |
| 새 합성 bridge의 주변 접촉 후보 | — | 0 |

분할된 궁의 두 child ID만 원래 `FJ3411:e0`로 대응시켜 비교했다. 원래 서로 다른 혈관을 동일시하지 않았다. 선택 경로 내부의 접촉은 비교 표에서 제외하되 전체 검사 결과에 보존했고, [별도 접합 영역 검사](ARCH_JUNCTION_SURFACE.md)로 다룬다. 공통 node가 있는 쌍은 이번 주변 검사에서 제외되며 그 사실도 기록한다.

두 실행 모두 margin 1.2 mm, interval 쌍 예산 2,000,000을 고정했다. 현재 사례의 누락 geometry 여부와 원본 입력 불변을 확인했다. 각 interval은 양끝 반경의 최댓값을 사용한 capsule로 보수적으로 둘러싼다. 접촉 후보는 실제 표면 관통 확정이 아니다.

19쌍이 남아 있으므로 주변 분리 상태는 **UNKNOWN**이다. 원래 누락되어 사례로 가져오지 못한 원본 요소, 최종 메시 충돌, 접합 영역 내부의 상세 품질은 이 검사로 확인되지 않는다. 후보의 기본 적용은 **NOT ACCEPTED**를 유지한다.

## 재현과 출력

Docker: `PYTHONPATH=src python scripts/inspect_arch_surroundings.py`.

[검사 JSON](evidence/arch-surroundings.json)에 전체 검사 범위, witness interval, 전후 사례 revision, 접합 검사 파일 해시, 유지·신규·미검출 쌍을 저장했다.

표면 생성 명령에도 `--junction-regions regions.json`을 추가했다. 이 옵션은 사례 해시에 결합한 명시적 접합 영역을 읽고 같은 검사를 실행한다. 누락 시 기존 정책을 유지한다. `test_case_surface.py`와 `test_junction_regions.py` Docker 검사 **28 passed**: CLI 생성·선언 보존과 오래된 사례 해시의 거부를 포함한다.
