# 실제 Atlas 구간 후보 HTTP 실행

실제 실행 중인 Atlas에서 FJ1692:e0의 후보를 생성했다. 합성 응답 주입 없이 **HTTP 200 CANDIDATE**를 받았다. 요청 전에 고정한 조건을 결과에 맞춰 변경하지 않았다.

| 조건 | 값 |
|---|---|
| 구간 | 첫 내부 단면 기준 8.328488–24.985464 mm |
| 중앙 배율 | 0.9 |
| 최대 정점 이동 | 0.3 mm |
| 단면 배율 절대 허용오차 | 0.02 |
| 처리 시간 | 255.473초 |

229개 단면의 최대 배율 오차는 **0.0158052**로 요청 조건 이내였다. 닫힌 topology와 자기 접촉 검출 0을 확인했다. 현재 장면 이웃 809개 중 795개는 전후 경계상자로 분리됐고, 전체 이웃 표면 접촉 보존 검사 PASS였다.

이는 한 혈관·한 조건의 후보 결과다. 이미 교차하는 표면의 겹침 체적, 해부학적 타당성 및 전체 대상 혈관 지원을 완료한 것으로 표시하지 않는다. 실제 적용은 하지 않았으며 generation·활성 수정 목록·저장본 SHA256을 보존했다.

- [전체 HTTP 결과와 검사](evidence/live-interval-preview.json)
- 별도 후보: `exports/live-interval-preview/candidate.json`
- 실행: `node scripts/inspect_live_interval_preview.cjs`

## 요청 처리 개선

긴 계산 중 장면 조회를 막던 공통 lock 점유를 수정했다. 장면 복사본을 lock 안에서 확보한 뒤 계산은 lock 밖에서 수행한다. 하나의 미리보기만 동시에 허용하며, 계산 중 generation이 바뀌면 결과를 409로 폐기한다. 실패·예외 때도 실행 중 표시를 해제한다.

[동시 요청 검사](evidence/interval-http-concurrency-tests.xml): 관련 6개 PASS. 실제 HTTP 서버에 통제된 대기 작업을 연결하여 계산 중 상태 조회 응답, 중복 요청 409, generation 변경 결과 폐기와 실행 표시 해제를 확인했다. [장면 복사·이웃 검사](evidence/interval-snapshot-tests.xml) 10개 PASS, [경계상자 검사](evidence/neighbor-bounds-tests.xml) 10개 PASS.

실제 255초 결과는 이 lock 개선 전 실행이다. 개선 후 실제 처리 시간 단축을 측정한 것은 아니며 계산량 자체는 여전히 줄여야 한다. 최신 요청 구조를 데모 서버에 반영했다.

## 실제 후보 화면 재생

저장된 실제 HTTP 200 응답의 402정점·800삼각형을 구간 미리보기 화면에 재생했다. 요청 조건과 기록의 일치 및 후보 검사 데이터의 동일성을 확인했다. 원본/후보 전환을 실행하고 두 캡처를 직접 확인했다.

[렌더링 기록](evidence/live-interval-render.json)은 실제 후보 파일의 SHA256을 포함한다. 합성 형상을 만든 검사가 아니라 실제 결과 재생이지만, 이 단계에서 서버 계산을 다시 수행한 것은 아니다. 전체 Viser 장면은 이번 캔버스 검사에서 제외했다.

캡처: `exports/live-interval-preview-render/candidate.png`, `reference.png`.

## 요청 안의 중복 검사 제거

동일 형상의 닫힘·자기 접촉 검사를 한 요청 안에서만 재사용하도록 구현했다. 정점·face 배열의 shape와 bytes를 SHA256으로 묶으며 좌표·연결 변경 시 다시 검사한다. 최대 32개 형상만 보관하고 영구 캐시는 만들지 않는다. 내부 포함 및 두 표면 접촉 검사는 매번 수행한다.

[재사용 검사](evidence/containment-reuse-tests.xml): 관련 15개 PASS. 재사용 전후 판정 동일성, 좌표 이동·face 제거 시 재검사를 확인했다. 실제 255초 조건의 속도 개선 재측정은 NOT RUN이며 이 최적화는 실행 중인 서버에 아직 재시작 반영하지 않았다.
