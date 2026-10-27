# 비평면 목에서 주머니로 이어지는 표면

`build_surface_neck_loft`는 원본 revision에 연결된 목 윤곽을 다시 계산한 뒤 열린 주머니 표면을 만든다. 64개 목 정점을 정확히 공유하고, 높이 방향 96개 ring과 단일 apex를 사용한다. 타원 단면 반경은 기존 dome 축 프로파일을 따른다. 목의 normal 변위는 `(1-z/h)^2`로 줄여 끝점에서 0이 된다.

`h > 2*max(positive neck offset)` 조건으로 각 대응 ray의 높이 증가를 유지한다. 이 조건은 전체 삼각형 자기 교차의 증명이 아니다. 생성된 패치의 연결 성분·winding·퇴화 면·비다양체 edge와 목 이외 추가 열린 경계 유무를 검사한다.

## 실제 MCA 적용

양측 MCA 모두 **6,145개 정점·12,224개 삼각형**, 목 경계 64점의 단일 연결 패치를 생성했다. 비평면 목 좌표는 원래 후보와 정확히 일치한다. 목을 제외한 정점 중 부모 프로파일 내부에 들어간 점은 양측 모두 0개였다. 정점 검사는 삼각형 내부 전체의 분리나 주변 다른 혈관과의 충돌 검사로 확대하지 않는다.

실제 생성 그림 `exports/surface-neck-loft/patches.png`를 열람했다. [검사 JSON](evidence/surface-neck-loft-inspection.json)에 attachment 전체·snapshot revision·표면 해시·검사 범위를 저장했다. 표면 NPZ는 로컬 exports에 두고 원본 snapshot·앱은 변경하지 않았다.

목은 열린 경계다. 부모 벽을 제거하고 주머니와 연결한 닫힌 내강은 아직 생성하지 않았다. 원래 평면 높이 기준 apex를 유지하지만 비평면 목 전체에서 동일한 높이를 뜻하지 않는다. 접합 C1 연속성, 전체 삼각형 충돌, 병변 마스크·기존 case 통합 및 임상 검증은 NOT RUN이다.

## 검증·재현

표면 경계 일치, 단일 apex, 열린 disk topology, 투영 dome 폭·깊이, 입력 불변과 잘못된 ring 수 거부를 포함한 관련 검사 **35 passed, 1.19초**.

Docker: `PYTHONPATH=src python scripts/inspect_surface_neck_loft.py`.
