# 구간 편집 세션 저장·복원

`interval_session`은 여러 구간 편집의 적용 순서, 기준 Atlas hash, 편집 전 전체 혈관 파라미터, 각 후보의 원본·파생 형상 및 검사 조건을 하나의 내용 해시가 있는 JSON 파일 형식으로 묶는다. 활성 표면과 마지막 편집 기록이 다르면 저장을 거부한다.

복원은 구간 편집이 없는 일치하는 기준 파라미터 장면에서 시작한다. 독립 복사본에서 모든 편집을 순서대로 재검사·적용한 후 현재 장면 generation을 다시 확인하여 한 번에 반영한다. 중간 실패 시 현재 장면에는 일부 결과도 반영하지 않는다. 복원된 편집은 개별 역순 undo가 가능하다.

적용 순번은 장면 generation과 별도로 기록한다. 여러 편집을 한 번에 복원한 뒤 새 편집을 추가해도 순서가 중복되지 않는다. 저장 파일의 PASS 기록은 기하 재검사를 대신하지 않는다.

[Docker 검사 기록](evidence/interval-session-tests.xml): 15개 PASS. 두 번의 실제 합성 형상 편집 저장·정확한 복원·개별 undo, 후속 검사 실패 시 전체 미반영, 손상 파일 거부, 해시를 다시 계산한 잘못된 순서 거부, 복원 후 새 편집 순서 보존 및 적용 HTTP 회귀를 포함한다.

## 앱 연결과 실행 기록

`/api/atlas-interval-session`의 export/restore와 **구간 편집 세션 다운로드**, **구간 편집 세션 불러오기**를 연결했다. 사용자 파일의 원문을 전달하며 현재 generation을 대조한다. 복원된 여러 혈관 표면 핸들은 같은 렌더 갱신에서 교체하고, 실패하면 이전 장면을 다시 그린다. 기존 활성 구간 편집은 먼저 되돌려야 한다.

[HTTP 회귀 검사](evidence/interval-session-http-tests.xml): 38개 PASS. 실제 합성 형상 적용→세션 export→undo→restore→undo와 오래된 generation 거부를 포함한다.

[브라우저 기록](evidence/interval-session-ui.json): 실제 FJ1692 후보 적용→세션 파일 다운로드→undo→파일 업로드·재생성·복원→undo PASS. 총 약 247초이며 원본 저장 hash와 기존 편집 검사 상태가 유지됐다. 실제 Atlas에서는 한 편집으로 확인했으며 여러 편집은 위 합성 형상 검사에서 확인했다. 전체 Viser 장면의 시각 검사는 NOT RUN이고 작업 패널은 캡처로 확인했다.

- 실행: `node scripts/verify_interval_application_ui.cjs --session`
- 파일: `exports/interval-application-ui/session.json`
- 화면: `exports/interval-application-ui/session-restored.png`

[전체 Docker 테스트](evidence/interval-session-full-tests.xml): 1,005개 PASS, 실패 0개, 건너뜀 0개, 139.72초. 외부 라이브러리의 NumPy 사용에 대한 deprecation warning 355개가 있다. 전체 개발계획의 해부학적 수용 완료를 증명하는 검사는 아니다.

전체 사례·라벨·마스크 출력 연결, 기준 전체 혈관 파라미터까지 자동 복원하는 통합 저장, 실제 Atlas 다중 편집 검증은 남아 있다.
