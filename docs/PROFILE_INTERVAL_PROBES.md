# 실제 단면 기반 구간 편집 검사

고정된 평활화 중심선·2 mm 방향 창에서 추출한 8개 뇌혈관 단면에 구간 편집을 적용했다. 첫 단면부터의 전체 호길이 중 25–75%를 편집 범위로 고정하고 중앙 목표 배율 0.8과 1.2를 각각 적용했다. 이 값은 기능 검사 조건이며 문헌 질환 프리셋이나 허용 범위가 아니다.

## 결과

총 16개 후보를 저장 후 재로드하여 검사했다.

| 검사 | 결과 |
|---|---|
| 전체 삼각형 쌍 범위 자기 접촉 검사 | 16/16 완료, 검출 0 |
| 배율 1인 단면 링 좌표 | 16/16 동일 직렬화 정밀도에서 정확 일치 |
| 원본 loft 대비 face index 연결 | 16/16 정확 일치 |
| Atlas 편집 저장본 | SHA256 변경 없음 |

단면 프로필·사례 revision·출력 PLY 해시와 각 검사를 [결과 JSON](evidence/profile-interval-edits.json)에 기록했다. 검사 대상은 열린 내부 loft이며 원본 끝단을 포함한 전체 혈관이 아니다. 보호 목록은 처음과 마지막 단면만 포함한다. 실제 해부학적 분기 보호, 주변 혈관 충돌, 닫힌 표면 수용과 앱 적용은 NOT RUN이다.

실행:
`docker exec -e PYTHONPATH=src -w /workspace vv-annotation-ui python scripts/inspect_profile_interval_edits.py`

후보는 `exports/profile-interval-edits/<sha256>/surface.ply`에 별도로 보관한다. 원본과 기존 후보를 덮어쓰지 않는다.
