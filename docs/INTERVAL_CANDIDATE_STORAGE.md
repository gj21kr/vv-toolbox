# 구간 편집 후보 저장 형식

`vv-toolbox.interval-candidate-snapshot/1`은 원본 Atlas 편집 저장본과 분리된 불변 후보 기록이다.

포함 정보:

- 후보·참조 표면의 대응 정점 및 삼각형.
- 중심선 좌표, part/edge ID, native LPS mm 좌표계.
- 원본 Atlas 및 참조 형상 SHA256.
- 후보 형상 SHA256과 해당 형상에 연결된 검사 기록.
- 구간 편집 조건, generation, CANDIDATE·미적용 상태.

`save_interval_snapshot`은 내용 해시를 파일명으로 사용한다. 같은 결과의 중복 저장은 동일 파일을 반환하고 다른 결과는 별도 파일로 저장한다. 임시 파일을 기록·동기화한 뒤 배타적으로 연결하여 기존 파일을 덮어쓰지 않는다.

`load_interval_snapshot`은 중복 JSON 키, envelope/내용 hash, 좌표·인덱스, 원본/후보 형상과 검사 fingerprint 연결을 확인한다. 필요하면 호출자가 지정한 Atlas hash와도 대조한다. 재로드 자체는 기하 검사를 다시 수행하지 않으며, 저장된 PASS 기록을 새 장면 적용 승인으로 사용해서는 안 된다.

원형 반경을 비원형 표면과 일치하는 값으로 새로 만들어 넣지 않는다. 기존 단면 검사와 표면을 보존하며, 전체 사례 라벨·마스크 출력 계약은 별도다.

[검사 기록](evidence/interval-snapshot-storage-tests.xml): 관련 14개 PASS. 저장·재로드 동일성, 중복 저장, 내용 변조·출처 불일치·잘못된 형상·중복 키 거부, 원본 불변을 확인했다.

후보 API 응답에 출처·중심선·좌표계·형상 fingerprint를 추가하고 데모 서버에 반영했다. 과거 응답에 없던 출처/중심선을 추정해 자동 보충하지 않는다.

## 화면 다운로드·재로드

구간 후보 캔버스의 **후보 다운로드**가 `/api/interval-snapshot`의 export 검사를 거쳐 snapshot 파일을 내려받는다. **저장된 후보 다시 열기**는 파일의 원문을 전달하여 JSON 실수 표기의 재직렬화 때문에 hash가 달라지는 문제를 피한다. 현재 Atlas 출처와 일치하는 파일만 허용하며, 선택한 혈관과 part ID가 다르면 표시하지 않는다.

불러온 결과는 별도 캔버스에만 표시한다. 파일 무결성 확인, 기하 재검증 NOT RUN, 현재 장면 미적용을 화면에서 구분한다. 손상 파일을 열더라도 직전 유효 미리보기를 유지한다. 파일 업로드는 15 MB, HTTP 요청은 20 MB로 제한한다.

## 실제 브라우저 실행

[파일 API 회귀](evidence/interval-file-ui-tests.xml): 관련 17개 PASS.

[실제 화면 기록](evidence/interval-snapshot-ui.json): 합성 응답 없이 FJ1692 후보를 생성하고 다운로드 → 재로드 → 변조 파일 거부까지 PASS. 원본 generation·활성 수정·저장본 해시가 유지됐다. 실패한 import 뒤 기존 캔버스 내용이 바뀌지 않음도 확인했다.

- 실행: `node scripts/verify_interval_snapshot_ui.cjs`
- 실제 다운로드: `exports/interval-snapshot-ui/candidate.json`
- 시각 확인 캡처: `exports/interval-snapshot-ui/reloaded.png`
- Playwright로 패널·자체 캔버스를 검사했으며 전체 Viser 장면은 로드하지 않았다.

활성 Atlas 형상에 적용·복원하는 경로와 전체 사례·라벨·마스크 내보내기는 여전히 별도 개발 대상이다.

## 현재 장면 재검사

`/api/atlas-interval-revalidate`는 저장 파일의 출처와 참조 표면·중심선을 현재 장면과 대조하고, 저장된 조건으로 후보를 다시 생성한다. 현재 이웃 혈관을 포함한 구현된 검사를 다시 실행한 뒤 저장 형상과 정확히 일치하는 경우에만 결과를 반환한다. 저장된 PASS 기록은 검사 실행을 대신하지 않는다.

계산은 잠금 안에서 복사한 장면으로 수행한다. 계산 중 다른 요청을 처리할 수 있으며, 장면 generation이 바뀌면 결과를 폐기한다. 재검사 결과는 미적용 후보이고 전체 해부학적 수용 판정이 아니다.

[Docker 검사 기록](evidence/interval-revalidation-tests.xml): 18개 PASS. 실제 재생성 일치·원본 보존, 변경된 참조 표면/중심선 거부, 저장 검사 기록 우회 방지, 새 이웃 포함, 파일 무결성 및 두 HTTP 계산 경로의 동시 요청·장면 변경 처리를 확인했다.

화면의 **현재 장면 재검사** 버튼과 API를 데모 서버에 반영했다.

[실제 브라우저 기록](evidence/interval-revalidation-ui.json): 저장된 FJ1692 후보 파일을 불러온 뒤 버튼으로 현재 장면의 809개 이웃을 포함한 검사를 실행했다. 약 120초 후 재생성 형상과 저장 형상의 정확한 일치, 원본 저장 해시·generation·활성 수정 상태 보존을 확인했다. 합성 응답 없이 실행했으며 전체 Viser 화면은 제외하고 작업 패널과 자체 후보 캔버스를 검사했다.

- 재현: `node scripts/verify_interval_revalidation_ui.cjs`
- 시각 확인: `exports/interval-revalidation-ui/revalidated.png`
- 현재 결과는 미적용 후보다. 활성 장면 적용·복원 및 전체 해부학적 검증 완료를 의미하지 않는다.
