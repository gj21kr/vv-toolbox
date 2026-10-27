# 사례 모음의 데이터 분리 검사

`vv-case collection first.json second.json ...`은 저장 snapshot의 무결성을 확인한 뒤 기준 모델 ID와 형상 참조 원본 SHA-256의 세트 배정을 검사한다. 동일 원본 해시를 공유하는 사례는 모델 ID나 source ID를 바꾸어도 다른 세트로 배정할 수 없다. 해시 문자열 대소문자는 동일하게 처리한다. 오류는 종료 코드 2이며 입력 파일은 변경하지 않는다.

성공 출력은 사례 수·기준 모델 ID 수·입력 revision을 포함한다. `independent_anatomy=UNKNOWN`을 유지한다. 같은 원본 묶음의 해시를 공유하면 보수적으로 한 세트에 묶이며, 서로 다른 해시는 독립 표본이라는 증거가 아니다. 원본 묶음 안에서 실제로 독립된 표본을 나누려면 표본별 원본 등록과 근거가 필요하다.

여기서 검사하는 해시는 snapshot에 선언된 값이다. 외부 원본 파일을 다시 읽어 실제 내용을 검증하는 기능은 아니다. 모든 edge의 `source_ids`를 검사하고, 어느 edge에서도 참조하지 않는 부가 source 항목은 묶음 기준에서 제외한다. `unassigned` 역시 하나의 명시적 상태이므로 같은 원본의 일부만 train/test로 배정한 모음은 거부한다.

## 검증

Docker에서 `tests/test_case_contract.py tests/test_case_io.py` 실행: **26 passed, 0.84초**. 처음 CLI 테스트는 오류 반환 방식이 기존 `SystemExit(2)`인 점을 반영하지 않아 실패했다. 기존 CLI 계약에 맞게 테스트를 수정한 뒤 재실행했다.

검사 범위는 ID 변경 우회 거부, 해시 대소문자 처리, 미참조 metadata 구분, 독립 해시 허용, snapshot CLI와 입력 불변이다. 실제 다중 독립 해부 원본 등록·임상 검증·전체 프로젝트 회귀는 이번 변경 후 NOT RUN이다.
