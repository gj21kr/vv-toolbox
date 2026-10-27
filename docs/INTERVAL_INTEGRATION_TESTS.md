# 구간 편집 통합 회귀 검사

현재 작업 트리 전체 pytest 실행 결과: **966 passed, 0 failed, 0 skipped**, 112.11초. 경고 355개는 scikit-image marching cubes의 NumPy shape 대입 폐기 예정 경고다.

실행:
`docker exec -e PYTHONPATH=src -w /workspace vv-annotation-ui python -m pytest -q --junitxml=docs/evidence/interval-integration-full-tests.xml`

[전체 결과 XML](evidence/interval-integration-full-tests.xml)

## 실행 식별

- 기반 HEAD: `e42b0ef70460a06465007c1c74401701b00a6705`
- 미커밋 변경을 포함한 작업 트리를 검사했다. HEAD만으로 검사 코드를 재현할 수 없다.
- 컨테이너 이미지: `sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1`
- src/tests의 `.py`, `.js`, `.cjs`, `.html`, `.json` 파일 204개 내용 fingerprint:
  `ceb5007740580d50950fc022c26636e9065a7958262321a6c75f061a83530441`
- fingerprint 계산: Windows FullName 정렬, 저장소 상대 경로의 구분자를 `/`로 변환하고 `경로:소문자 SHA256` 행을 LF로 연결(마지막 LF 없음)한 UTF-8 bytes의 SHA256.
- Atlas 편집 저장본 SHA256:
  `082a9178daee4d52c79aaa709cba91fbdc56cfb5767fef4801fd4b9bb22d1964`

## 해석

비원형 단면/구간 편집, 실제 목표 단면 검사, 보호 표면 후보 생성, 이웃 접촉·완전 포함 검사와 기존 모듈 간 회귀 실패를 검출하지 않았다.

이 실행은 브라우저 검사를 새로 수행한 결과가 아니다. 실제 앱의 비원형 구간 편집·저장/재로드, 실제 전체 장면 충돌 검사, 모든 해부 구간과 개발계획 M1–M7 완료를 증명하지 않는다. 앱에는 기존 편집 복원 처리가 있지만 새 구간 후보 함수의 연결은 아직 남아 있다.
