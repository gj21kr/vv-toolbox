# 보정 표면과 중심선 일치 검사

고정된 8개 뇌혈관 후보의 실제 저장 PLY를 재로드하여 원본 및 평활화 중심선의 모든 선분을 검사했다. 각 중심선 집합 533개 구간, 총 1,066개 구간에서 내부 포함 판정 **PASS**다.

| 대상 | 혈관 수 | 구간 수 | 최소 내부 구간 커버 여유 |
|---|---:|---:|---:|
| 원본 중심선 → 보정 표면 | 8 | 533 | 0.509660 mm |
| 평활화 중심선 → 보정 표면 | 8 | 533 | 0.532531 mm |

여유는 구간 내부를 보장하는 공의 수치적 커버 여유이며 혈관 반경이나 전역 최소 벽 거리와 같지 않다. 닫힌 유효 표면 가정 아래 허용오차 1e-6 mm, 최대 분할 깊이 16, 최대 셀 수 100,000으로 검사했다.

앱 로더의 원본 해시·보호 정점·동시 장면 접촉 범위 검증을 먼저 실행했다. 기존 중심선 검사 기록과 원본 snapshot, 개별 평활화 사례 revision, 후보 PLY 해시를 연결했다. 입력 파일과 Atlas 저장본은 변경하지 않았다.

- 실행: `docker exec -e PYTHONPATH=src -w /workspace vv-annotation-ui python scripts/inspect_protected_centerlines.py`
- 결과: [protected-centerlines.json](evidence/protected-centerlines.json)
- 검사기: [inspect_protected_centerlines.py](../scripts/inspect_protected_centerlines.py)

반경과 비원형 표면의 대응, 해부학적 구간 경계, 전체 대퇴–뇌혈관 모델 수용은 이 검사에 포함하지 않는다. 앱은 현재 표면 비교를 제공하며 중심선 동시 표시·편집은 별도 구현 대상이다.
