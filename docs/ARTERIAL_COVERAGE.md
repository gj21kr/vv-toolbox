# 동맥 원자료 대응 검사

검사일: 2026-10-20. 재현: Docker에서 `PYTHONPATH=src python scripts/inspect_arterial_coverage.py`.

현재 Atlas 선택에 속한 동맥 부품 518개 전체를 검사했다. 인체의 모든 동맥 또는 개발계획의 해부 구간 전체가 완성됐다는 뜻은 아니다.

| 항목 | 결과 |
|---|---:|
| 원본 동맥 부품 | 518 |
| 가져온 파생 중심선 edge | 1,081 |
| 가져온 node | 1,653 |
| 중심선 없는 부품 | 1: FJ3553 |
| 이름만으로 좌우를 정하지 않은 부품 | 81 |
| 실제 연결과 분리한 근접 후보 | 1,522 |
| 유효 경로에서 제외한 퇴화 고리 | 3 |

전체 preview에서 서로 다른 위치가 두 개뿐인 왕복 고리 5개를 발견했다. 이 중 동맥에 속한 FJ1680:e3, FJ1680:e4, FJ1680M:e13 세 개를 이번 동맥 사례에서 격리했다. 원본 중심선은 수정하지 않으며 격리 목록에 원래 edge와 사유를 보존한다. 나머지 두 개는 이번 동맥 범위 밖이다. 적어도 세 위치를 가지는 실제 추출 고리는 유지한다.

명칭에 좌우가 없는 부품을 midline으로 추정하지 않고 unknown으로 기록한다. 이름 대응은 구조 identity 후보이며 구간 경계·접합의 확정이 아니다. 원본·추출 파일 해시와 개별 OBJ 해시, 모든 부품의 경로 목록은 [검사 JSON](evidence/arterial-coverage.json)에 저장했다. 대퇴·장골·대동맥·경동맥·근위 ACA/MCA의 18개 원자료 대응 항목도 별도로 기록했다.

전체 동맥 사례는 로컬 `exports/atlas-case-inspection/all-arterial-case.json`에 생성한다. 원본 bytes 불변 검사 PASS, 사례 계약 검사 PASS. 부품 사이 실제 연결과 해부 구간은 unresolved이므로 네 접근 조합의 해부학적 완료 판정은 UNKNOWN이다. 근접 후보를 자동 접합해 이 결과를 PASS로 바꾸지 않는다.

단위·좌표 확인 근거는 [landmark 검사](CEREBRAL_LANDMARK_INSPECTION.md)를 참조한다. 기존 preview의 'mm assumed' 문구는 원본 선언으로 보존하고 별도 확인된 native LPS/mm 계약을 적용한다.
