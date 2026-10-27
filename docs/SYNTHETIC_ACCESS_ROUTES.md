# 원본 앵커 기반 합성 접근 경로

`synthetic_routes.build_synthetic_routes`는 명시적으로 지정한 원본 edge 끝점 사이에 별도 합성 연결을 추가한다. 원본 사례의 모든 node와 edge를 그대로 보존하며, 원본의 미확인 해부학 상태도 유지한다. 근접 후보에서 연결을 자동 선택하지 않는다.

## 입력과 산출물

명세 schema는 `vv-toolbox.synthetic-routes/1`이다. `source_case_sha256`은 `case_io.case_digest`로 계산한 원본 사례 전체 hash와 일치해야 한다. `bridges`의 각 항목은 다음 필드를 요구한다.

- `id`: 기존 edge와 충돌하지 않는 ID.
- `from`, `to`: 각각 `{edge_id, endpoint}`. endpoint는 `start` 또는 `end`이다.
- `handle_lengths_mm`: 양 끝의 양수 tangent handle 길이 두 개.
- `samples`: 3–10000 정수.
- `rationale`, `evidence_refs`: 연결 선택 사유와 검사 근거.

연결은 cubic Hermite 곡선이다. 원본 끝점의 바깥 방향 접선과 반경을 사용하고, 반경은 smoothstep으로 보간한다. 원본의 중간 지점을 접합점으로 쓰려면 먼저 명시적 분할을 해야 한다. 닫힌 고리에 끝점 방향을 임의로 부여하지 않는다. 모든 새 연결은 `estimated / synthetic_estimate`, 해부학 연결 판정은 UNKNOWN이다. 이산 곡선의 접선 근사, 충돌, 표면 접합은 별도 검사 대상이다.

`inspect_four_access_routes`는 L→L, L→R, R→L, R→R 네 조합을 빠짐없이 요구한다. 시작 대퇴 edge와 경유 경동맥 edge를 ID로 지정하고 좌우 및 순서를 검사한다. 검사 결과의 PASS는 그래프 도달성에 한하며, 미확인 원본 node/edge를 통과하면 UNKNOWN이 유지된다.

대퇴·경동맥 역할 자체는 호출자가 명세에 선언한다. 이 함수는 이름을 해석하거나 실제 artery 역할을 해부학적으로 검증하지 않는다. 원본 대응 검사는 별도 근거가 필요하다.

## 실제 Atlas 원자료 대응

다음 ID는 `docs/evidence/arterial-coverage.json`의 `route_slots`에서 확인했다. 명칭 대응은 접합·구간 경계의 확정이 아니다.

| 역할 | 왼쪽 | 오른쪽 |
|---|---|---|
| 대퇴 | FJ2074:e0 | FJ2143:e0 |
| 외장골 | FJ3466:e0 | FJ3567:e0 |
| 총장골 | FJ3464:e0 | FJ3565:e0,e1,e2 |
| 총경동맥 | FJ3483:e0 | FJ3564:e0 |
| 내경동맥 | FJ1682M:e0 | FJ1682:e0 |
| ACA 원자료 | FJ1654M:e0 | FJ1654:e0 |
| MCA sphenoid 원자료 | FJ1692M:e0 | FJ1692:e0 |

공통 몸통은 복부 대동맥 FJ1932:e0, 흉부 하행 대동맥 FJ1931:e0–e4, 대동맥궁 FJ3411:e0이다. 오른쪽 경동맥 경로의 brachiocephalic 원자료는 FJ3417:e0이다. 다중 추출 edge 중 통과할 edge 순서와 각 접합 endpoint는 아직 지정되지 않았다.

실제 Atlas에 대한 네 경로 구성은 **NOT RUN**이다. 18개 역할의 원자료 대응만으로 접합 위치를 정하거나 연결을 승인하지 않는다. 다음 실행에는 각 단절의 원본 부품·끝점 ID·접합 검사 근거·handle 길이를 담은 명시적 명세가 필요하다. 이를 적용한 뒤 전체 경로와 충돌·접합 표면을 검사한다.

## 저장 및 경로 검사 명령

연결부 검사는 저장된 합성 사례에서 실행한다. 허용각과 반경 차이를 명시적으로 입력한다. 아래 5도·0.01 mm는 사용법 예시이며 해부학적 허용 기준이 아니다.

```text
python -m vv_toolbox.case_cli bridge-continuity SYNTHETIC.snapshot.json --max-angle-deg 5 --max-radius-jump-mm 0.01
```

두 부착점 각각의 node 공유, 좌표 간격, 반경 차이, 원본 끝 선분과 연결 첫 선분의 방향 차이를 기록한다. 위치는 정확히 일치해야 한다. PASS 종료 코드는 0, 연속성 FAIL은 1이다. 실제 저장된 이산 중심선을 검사하므로 생성식의 해석적 접선 일치만으로 통과시키지 않는다. 이 검사는 표면 매끄러움·충돌·해부학적 접합의 승인이 아니다. 양 끝 결함 및 CLI를 포함한 관련 Docker 검사 **26 passed, 0.71 s**.

```text
python -m vv_toolbox.case_cli synthetic-routes SOURCE.snapshot.json CONNECTIONS.json SYNTHETIC.snapshot.json --case-id synthetic-access-001
python -m vv_toolbox.case_cli four-routes SYNTHETIC.snapshot.json FOUR_ROUTES.json
```

첫 명령은 source hash와 연결 명세를 검증한 뒤 별도 합성 snapshot을 저장한다. 원본 또는 명세 파일을 출력으로 지정할 수 없으며 hard link 별칭도 거부한다. 기존 합성 출력 갱신에는 `--expected-revision`이 필요하다. 저장 성공의 PASS 범위는 사례 구조·파일 무결성이다.

두 번째 명령은 네 경로 검사 결과와 사례 revision을 출력한다. 종료 코드는 그래프 PASS=0, FAIL=1, 입력 오류=2, UNKNOWN=3이다. 미확인 원본을 지나는 경로를 PASS로 바꾸지 않는다. 두 명령 모두 중복 JSON 키를 거부한다.

Docker CLI·경로·snapshot 검사 **36 passed (0.83 s)**: 원본 보존, 명세 보존, 저장·재로드, 기존 파일 갱신 충돌, hard link 원본 보호, UNKNOWN 반환을 확인했다.

Docker에서 `PYTHONPATH=src pytest -q -p no:cacheprovider tests/test_synthetic_routes.py tests/test_access_routes.py`를 실행한다. 합성 fixture의 원본 불변·끝점 접선/반경·재현성·잘못된 명세 거부·네 조합·미확인 상태 유지가 검사 범위다. 실제 전신 경로 또는 임상 유효성 검증이 아니다.
