# Atlas 구간 편집 미리보기 API

`POST /api/atlas-interval-preview`를 앱 라우터에 연결했다. 현재 장면 세대와 일치하는 `X-Expected-Generation` 헤더가 필요하다.

요청 필드:
`part_id`, `edge_id`, `start_mm`, `end_mm`, `factor`, `max_displacement_mm`, `absolute_scale_tolerance`.

현재 Atlas 표면과 중심선을 사용한다. 장면에 존재하는 모든 비-context 혈관을 이웃 목록으로 만들며 현재 수정된 이웃 표면도 반영한다. 기존 접촉 삼각형의 정점을 자동 보호 목록에 포함한다.

단면 추출·구간 편집·닫힌 후보 생성·목표 크기·자기 접촉·이웃 접촉/완전 포함 검사를 거쳐 별도 정점·면·검사 결과를 반환한다. 기존 422 편집 검사 실패 응답과 409 장면 세대 충돌 응답을 사용한다. 이 API는 활성 형상, generation, 편집 저장본을 변경하지 않는다.

## 현재 제한

- 한 part에 중심선 edge가 하나인 경우만 지원한다. 여러 분기를 가진 part를 잘못 변형하지 않도록 명시적으로 거부하며, 공동 분기 편집은 개발 범위에 남는다.
- 거리는 첫 추출 내부 단면부터 측정한다.
- 실제 부위별 허용 범위를 제공하는 API가 아니다. 배율과 오차·이동 한도는 명시적 입력이다.
- 표면이 이미 교차하는 이웃의 겹침 체적 변화는 미검증이다. 결과는 `CANDIDATE`, `read_only=true`, `applied=false`다.
- 화면 조절기·후보 렌더링·실제 적용·저장은 아직 연결하지 않았다.

[검사 기록](evidence/atlas-interval-preview-tests.xml): 관련 31개 테스트 PASS. 합성 Atlas 미리보기 생성, 현재 이웃 목록 검사, 실패 시 장면 불변, 다중 edge 거부 및 기존 저장/복원 회귀 검사 포함. 이 기록은 실제 HTTP/브라우저 실행 검증이 아니며 실행 중인 데모 서버는 이번 단계에서 재시작하지 않았다.

## 실제 서버 HTTP 검증

이후 저장하지 않은 Atlas 수정이 없고 사례 workspace가 비어 있음을 확인한 뒤, 명령행으로 신원을 확인한 데모 프로세스만 재시작하여 최신 코드를 반영했다. 포트는 기존 `127.0.0.1:8093`을 유지했다.

[HTTP 실행 기록](evidence/interval-preview-http.json):

- 장면 generation 누락: 409.
- 잘못된 요청: 400.
- 다른 Origin 요청: 403.
- 실제 FJ1692:e0에 0.9배, 1–2 mm 구간, 이동 한도 1e-12 mm의 의도적 실패 조건: 422 `Projection exceeds declared displacement bound`.
- 요청 전후 generation, 활성 수정 목록 및 저장 Atlas SHA256 불변.

실행: `node scripts/verify_interval_preview_http.cjs`.

이는 거부 경로와 원본 유지 검증이다. 실제 Atlas 성공 후보 HTTP 반환과 브라우저 렌더링은 NOT RUN이며 화면 조절기를 추가한 것으로 표시하지 않는다.
