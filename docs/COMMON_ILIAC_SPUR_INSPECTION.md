# 우측 총장골의 짧은 추출 가지 검사

원본 `FJ3565` 표면과 추출 edge `FJ3565:e1`을 직접 대조했다. 사례 revision `6b8beaf9bf255f543fa00b7f3c821bcb31a6be867eb3df2cd0d982299aa160c2`에 결합한 검사다.

## 측정

- edge 길이: **1.385641 mm**, 표본 2점.
- 21개 균일 보간점에서 원본 삼각형까지의 unsigned 최단 거리: **3.486462–4.035076 mm**.
- Z=922/924.2/924.4/924.6/924.8/926 mm의 실제 source 단면 6개 모두 윤곽 1개.
- 짧은 edge가 통과하는 4개 표본 단면에서 점은 모두 원본 윤곽 내부에 위치한다.
- 실제 단면 그림을 열람했다. 이것은 전체 3D inside 판정이나 독립 branch 부재의 완전한 증명은 아니다.

## 판단과 다음 구성

이 짧은 추출 경로를 별도 해부학적 daughter로 간주할 근거는 이번 원본 검사에서 확인되지 않았다. 현재 그래프에서는 이 경로가 node degree를 3으로 만들어 총장골 주 경로의 단순 합치기를 방해한다. 또한 아래쪽의 짧은 retained 구간은 접합 collar 검사에서 전체 소비된다.

다음 합성 구성은 이 edge의 원본 대응·제외 사유·위치를 보존한 명시적 omission과, 남은 주 경로 두 edge의 병합을 함께 다룬다. 원본 Atlas나 원본 추출 결과를 삭제하지 않는다. 제외된 원본 edge를 역할 추적이 조용히 누락하지 않도록 omission 기록을 검사에 포함해야 한다. 이는 임의의 짧은 분지를 일괄 삭제하는 정책이 아니다.

이번 검사에서는 geometry/graph를 변경하지 않았다. 해부학적 branch 판정은 UNKNOWN이며 실제 합성 제외·주 경로 병합 구현은 남아 있다.

- 스크립트: `scripts/inspect_common_iliac_spur.py`.
- [수치·원본 삼각형 대응·단면 기록](evidence/common-iliac-spur-inspection.json).
- 그림: `exports/common-iliac-spur-inspection/source-sections.png`.

Docker에서 실행했고 source archive와 그림 SHA-256을 기록했다.
