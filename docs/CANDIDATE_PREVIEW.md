# 합성 후보 미리보기 연결

## 현재 구현

`src/vv_toolbox/candidate_preview.py`에 등록된 후보 ID 전용 읽기 로더를 추가했다.
현재 등록 ID는 `right-iliac-source-profile`이다. 클라이언트가 임의 파일 경로를
선택하는 방식은 지원하지 않는다.

snapshot의 검증된 revision, 표면 NPZ의 SHA-256, 표면 생성 및 표면 분리 검사
기록의 revision/hash, NPZ 내부 frame·edge 목록을 함께 대조한다. 좌표는 LPS/mm여야
하며 유한 vertex·정수 face index·배열 크기 및 범위를 검사한다. NPZ pickle은 금지한다.

전체 snapshot에 포함된 모든 혈관을 출력하지 않고 표면 생성 대상인 외장골·
고환동맥 두 edge만 돌려준다. 읽기 전용, 선택 범위, 해부학 UNKNOWN, 전체 Atlas
충돌/자기 교차 NOT RUN을 상태와 함께 전달한다. 두 표면 간 분리 PASS를 전체
모델 검증으로 바꾸지 않는다.

실제 저장 후보를 읽어 revision, 두 edge, 322,565 vertex 및 645,122 triangle을
확인했다. 앱의 별도 candidate source에 연결하여 붉은 표면과 선택된 두 중심선을
표시한다. 렌더링 좌표는 mm에서 m로 변환한다. 진입할 때마다 근거를 다시 검사하며,
검증 실패 시 기존 source와 generation을 유지한다.

왼쪽의 '합성 후보 보기'와 'Atlas로 돌아가기'로 전환한다. 후보 화면은 읽기 전용이며
Atlas 편집 패널을 숨긴다. 현재 후보는 장골 부위 두 혈관만 포함하며 전체 대상 동맥의
완성 모델이 아니다. Atlas 선택과 수정 표면은 전환 중 보존한다.

## 검사와 후속 연결

- 후보 범위·UNKNOWN 보존, 미등록 ID, 오래된 근거, 변조 mesh, 일치하는 hash를
  가진 잘못된 좌표/face/frame 거부 등 **9 tests passed**.
- 로더 추가 전 전체 Docker 회귀 검사: **569 passed, 3 skipped, 319 warnings**.
  건너뛴 3개는 컨테이너에 Node가 없어 실행되지 않은 UI JavaScript 검사다.
  브라우저 검증 PASS로 표시하지 않는다. 경고는 NumPy shape 변경 관련 폐기 예정 경고다.
- 연결 후 Docker 집중 검사 **26 passed**: 단위 변환, 두 경로만 표시, 가시성,
  읽기 전용 처리, Atlas 수정 표면 복원, 진입 실패 시 기존 상태 보존.
- 연결 후 전체 Docker 회귀 **581 passed, 3 skipped, 319 warnings** (51.75초).
  JUnit: `exports/regression-candidate-preview.xml`, SHA-256
  `b79a5cfc2d3176466e3842712c3d1c97e308bbb71d2a37d49d2a776e45dfc389`.
  3개 skip은 기존 Node 기반 관계 UI 검사이며 이번 브라우저 흐름 검사로 대체한 것은 아니다.
- Playwright Chromium에서 실제 후보 버튼 → 두 혈관 화면 → Atlas 복귀를 실행했다.
  데스크톱 1440×1000 및 모바일 크기 390×844 화면을 저장하고 열람했다.
  [실행 기록](evidence/candidate-preview-browser.json). 브라우저 플러그인이 없어
  Playwright를 사용했다. 소프트웨어 WebGL 경고가 있어 GPU 성능 검증은 NOT RUN이다.
- 브라우저 검사는 기존 선택·수정 사전의 전환 전후 일치를 검사한다. 새 형상 수정은
  수행하지 않았으며 수정된 표면의 보존은 위 집중 테스트에서 별도로 검사했다.
  현재 source-case 저장/재로드 기능은 합성 후보 렌더링과 분리해 유지한다.
