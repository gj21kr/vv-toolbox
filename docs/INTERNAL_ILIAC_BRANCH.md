# 우측 내부장골 분지 원본 대조와 합성 후보

## 원본 대조

BodyParts3D의 우측 총장골 `FJ3565`, 외장골 `FJ3567`, 내부장골 `FJ3569`를 같은 좌표에서 절단했다. 실제 축상 단면 Z=903/906/909/912/915/924 mm를 열람했다.

- Z=903 mm: 내부장골–외장골 윤곽 교차 2개.
- Z=906 mm: 내부장골–총장골, 내부장골–외장골 각각 윤곽 교차 2개.
- Z=909 mm: 내부장골 단면이 다른 윤곽 내부에 보인다. 윤곽 교차 수 0은 표면이 서로 떨어졌다는 뜻이 아니다.
- 원본 표면 중첩과 명칭은 분지 구성의 근거지만, 공유 내강이나 정확한 ostium 좌표 확정은 아니다.

[단면·원본 해시·검토 위치](evidence/internal-iliac-junction-review.json). 그림은 `exports/internal-iliac-junction/source-sections.png`다.

## 합성 분지

기존 우측 총장골–외장골 연결의 interval 97, fraction 0.22494234172140176을 **합성 구성 위치로 명시적으로 선택**했다. 원본 내부장골 근위 끝점에서 생성 중심선으로 투영한 검토 위치이며, 최근접 규칙만으로 원본 해부 접합을 승인한 것이 아니다.

연결을 내부에서 분할하고 원본 `FJ3569:e0.end`까지 side-branch를 추가했다. 직선 끝점 거리는 1.744806 mm다. 새 node는 degree 3이고, 후보 전체의 선언 bridge 부착부 **20곳 수치 연속성 PASS**다. 입력 snapshot과 변경 대상 외 edge는 동일하다.

- 스크립트: `scripts/inspect_internal_iliac_junction.py`, `scripts/build_synthetic_internal_iliac_branch.py`.
- [생성·연속성 기록](evidence/synthetic-internal-iliac-branch.json).
- 사례: `exports/synthetic-internal-iliac-case/case.snapshot.json`.
- revision: `6b8beaf9bf255f543fa00b7f3c821bcb31a6be867eb3df2cd0d982299aa160c2`.

## 남은 검사

짧은 `R-CIA-retained`가 기본 collar에 모두 포함되는 이전 검사 문제는 이 분지 추가만으로 해소됐다고 판정하지 않는다. 원본 총장골의 `FJ3565:e1`은 짧은 추출 edge이며 임의 삭제하지 않았다. 원본 총장골 전체 경로와 해당 추가 edge의 실제 형상 대응을 확인해 검사 가능한 합성 접합을 구성해야 한다.

새 revision의 분지 포함 표면·주변 간격은 NOT RUN, 해부학적 수용은 UNKNOWN이다. 앱 기본 사례에는 적용하지 않았다.
