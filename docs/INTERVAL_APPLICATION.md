# 구간 후보 적용 트랜잭션

`interval_application.apply_interval`은 저장 후보를 현재 장면의 복사본으로 재생성·검사한 뒤 generation이 유지된 경우 파생 표면을 교체한다. 원본 표면은 변경하지 않는다. 구간 후보 기록은 기존 반경·굴곡·비틀림 파라미터와 별도인 `atlas_interval_edits`에 둔다.

화면 갱신 콜백이 실패하면 직전 표면·기록·generation으로 되돌리고 화면을 다시 구성한다. 복원 화면 구성까지 실패하면 recovery 상태를 남긴다. 계산 중 다른 장면으로 변경되면 새 후보를 적용하지 않는다.

[Docker 검사](evidence/interval-application-tests.xml): 15개 PASS. 실제 합성 표면 재생성 후 적용, 원본 보존, 화면 오류 시 상태 복원, 복원 실패 상태, 시작 전/계산 중 generation 변경 거부 및 관련 재검사·HTTP 동시성 검사를 포함한다.

`undo_interval`은 연속 구간 편집을 역순으로 복원한다. 각 적용 직전의 파생 표면과 구간 기록을 독립 복사하여 보관한다. 되돌리기 성공 시 generation은 증가하며 이전 단계도 이어서 되돌릴 수 있다. 다른 장면 수정이 끼어들면 오래된 전체 표면 상태를 덮어쓰지 않도록 거부한다. 이후 새 구간 적용은 그 시점부터 새 undo 이력을 시작한다.

실제 두 번의 합성 표면 편집 후 역순 복원, 중간 장면 변경 거부, undo 렌더 실패 시 편집·이력 보존 후 재시도 성공을 검사했다. 디스크 저장본은 변경하지 않는다.

## 앱 연결과 실제 실행

`/api/atlas-interval-apply`와 `/api/atlas-interval-undo`를 작업 패널 버튼에 연결했다. 적용 시 현재 장면에서 재검사하고 기존 표면 핸들의 정점만 교체한다. 선택·색·카메라·중심선 경로를 재생성하지 않는다. 원본 중심선의 반경 값을 새 단면의 실제 반경으로 간주하지 않는다.

구간 기록은 workspace JSON 내보내기에 포함된다. 기존 파라미터 저장/재로드와 사례 생성은 구간 기록을 보존하지 못하므로 활성 구간 편집이 있으면 거부한다. 전체 혈관 파라미터 수정과 원본 모델 전환도 먼저 구간 undo를 요구한다. 이는 현재 통합 범위의 제한이며 최종 저장·조합 기능을 대체하지 않는다.

[HTTP·회귀 검사](evidence/interval-application-http-tests.xml): 40개 PASS. 실제 후보 생성/적용/undo HTTP 경로, generation 거부, 기존 편집 저장 회귀를 포함한다.

[실제 브라우저 검사](evidence/interval-application-ui.json): FJ1692 저장 후보를 열고 재검사 후 적용 → 버튼 undo까지 PASS. generation 두 단계 증가, 활성 검사 기록 복원, 원본 저장 파일 hash와 기존 수정 상태 보존을 확인했다. 응답을 합성하지 않았으며 실제 서버 렌더러가 실행됐다. 브라우저에서는 작업 패널을 확인했고 전체 Viser 장면의 시각 검사는 NOT RUN이다.

- 재현: `node scripts/verify_interval_application_ui.cjs`
- 화면 확인: `exports/interval-application-ui/applied.png`

구간 기록의 파일 저장/재로드는 [세션 저장·복원](INTERVAL_SESSION.md)에 연결했다. 기존 전체 혈관 수정과 자유로운 조합, 전체 사례 출력 연결은 미완료다. 현재 세션의 적용·undo 성공을 전체 해부학적 모델 수용으로 확대하지 않는다.
