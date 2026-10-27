# 합성 모델의 말단 절단과 외장골–대퇴 연결 후보

원본의 겹친 말단을 그대로 연결하면 역방향 곡선이 생길 수 있다. `trim_synthetic_terminal`은 지정한 원본 중심선 주소에서 자유 말단을 잘라 별도 합성 사례를 만든다. 원본 파일은 변경하지 않는다.

## 계약

- schema: `vv-toolbox.synthetic-terminal-trim/1`.
- 기존 `synthetic-junction` 선언의 사례·자료 해시, edge, 내부 sample 또는 interval/fraction, 새 node 및 두 child ID, 근거와 사유를 사용한다.
- `remove_endpoint`는 `start` 또는 `end`다. 제거할 끝점은 다른 edge나 bridge가 연결되지 않은 자유 말단이어야 한다.
- 제거한 tail과 node, 원본 전체 edge, 구간 주소와 근거를 이력에 보존한다. 유지한 끝점의 기존 bridge 참조는 유지 child로 갱신한다.
- 병변을 가진 edge와 기존 bridge 절단은 거부한다. 파생 사례의 형상·경로 검사 상태를 무효화한다. 새 끝점은 해부학적 terminal이나 확정 분기점이 아닌 `unresolved`다.
- CLI: `python -m vv_toolbox.case_cli trim-terminal INPUT SPEC OUTPUT --case-id ID`. 원본이나 선언 파일 덮어쓰기는 거부한다.

## 실제 자료 적용

`scripts/build_synthetic_iliofemoral_case.py`는 기존 대동맥궁–경동맥 후보에서 좌우 외장골–대퇴 네 말단을 절단한 뒤 두 Hermite 연결을 추가한다.

절단면은 두 원본 끝점의 Z 범위에서 위·아래 각각 10 mm 여유를 둔다. 이 값은 **합성 형상 구성 규칙**이며 서혜인대나 임상적 경계를 뜻하지 않는다. 각 절단면이 중심선과 한 번만 교차해야 하며, 정확한 보간 주소를 기록한다. 유지한 source 중심선은 아직 계단형 굴곡이 남아 있다.

- 출력: `exports/synthetic-iliofemoral-case/case.snapshot.json`.
- 후보 revision: `69cca3347e668d85ce9bd28af8ecb3d2eea95ff7812c6ad7a01cd14914c3444f`.
- 그림: `exports/synthetic-iliofemoral-case/centerline-comparison.png`. 원본과 유지 중심선, 생성 연결을 함께 표시한다. 표면 검사가 아니다.
- 근거: [JSON](evidence/synthetic-iliofemoral-case.json).

Docker에서 재생성 및 snapshot 일치, 원본·무관 edge 보존을 확인했다. 네 새 부착부의 위치·반경 연속성과 표본 접선각 3도 이내 검사 PASS. 말단 절단·CLI·junction·route 관련 33 tests PASS. 최초 CLI 실패 경로 테스트는 실제 `SystemExit(2)` 계약에 맞춰 수정했다.

주변 충돌·최종 표면·내강 연결은 NOT RUN이며, 해부학적 수용은 UNKNOWN이다. 앱 기본 사례에는 적용하지 않았다. 네 전체 접근 경로가 완성된 것은 아니다.
