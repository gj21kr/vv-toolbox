# 우측 하복벽동맥 접합 후보의 원본 대조

## 실제 표면 대조

`FJ3567` 원본 우측 외장골동맥, `FJ3604` 원본 우측 하복벽동맥, 새 우측 외장골–대퇴 표면을 같은 native LPS 좌표에서 비교했다. Z=826/829/832/835/838/841 mm의 실제 mesh 단면을 생성해 열람했다.

Z=832 mm에서 원본 외장골–하복벽 윤곽 교차 2개, 합성 표면–하복벽 윤곽 교차 2개를 확인했다. 원본 하복벽 윤곽의 정점 중 각각 74개와 63개가 해당 parent 단면 내부에 있다. 이 수는 면적 비율이나 내강 연결률이 아니다. 다른 다섯 표본 평면에는 교차가 검출되지 않았다. 평면 사이 전체 3D 구간을 검사한 것은 아니다.

따라서 이전 capsule 검사에서 발견한 후보는 **실제 표면 단면 교차로도 확인되며, 원본에도 같은 높이의 접촉이 있다.** 새로운 무관 혈관의 충돌로만 분류해 parent를 이동시키기보다, 하복벽동맥 접합을 포함한 합성 topology를 구성해야 한다. 원본 공유 내강 및 정확한 ostium은 UNKNOWN이다.

## 문헌 대조

- [Jakubowicz & Czerniawska-Grzesińska, Variability in origin and topography of the inferior epigastric and obturator arteries, PMID 8908792](https://pubmed.ncbi.nlm.nih.gov/8908792/): 검색 가능한 초록은 하복벽동맥의 외장골동맥 기시와 다른 기시 변이를 보고한다. 일반 관계의 근거이며 BodyParts3D 표본의 위치 근거는 아니다.
- [Mustafa & Alasmari, Anatomical Study and Clinical Importance of the Inferior Epigastric Artery, 2021](https://www.scielo.cl/pdf/ijmorphol/v39n3/0717-9502-ijmorphol-39-03-688.pdf): 검색 색인에서 원위 외장골동맥 기시를 확인했다. 이번 실행에서 HTML 본문은 403으로 열리지 않았으므로, 전체 논문 방법·수치를 검증한 것으로 기록하지 않는다.

## 후속 구현 입력

[기계 판독 기록](evidence/epigastric-source-junction.json)에 원본 근위 끝점을 생성 중심선에 연속 투영한 interval/fraction/XYZ를 저장했다. 이는 `REVIEW_LOCATOR_ONLY`이며 실제 ostium이나 자동 연결 승인이 아니다. 가장 가까운 위치만으로 해부학을 확정하지 않는다.

생성 bridge를 내부에서 분할할 때 외부 두 부착점과 연속성 검사의 계보를 유지하는 기능이 필요하다. 현재 일반 split은 declared bridge 분할을 거부하므로 이를 우회해 metadata를 삭제하지 않는다. 접합을 추가한 뒤 하복벽동맥을 포함한 표면·접합 영역·주변 검사를 다시 실행해야 한다.

스크립트: `scripts/inspect_epigastric_source_junction.py`. 그림: `exports/epigastric-source-junction/source-candidate-sections.png`. 원본 archive, 사례 revision, 후보 표면, 검사 기록 및 그림 해시를 기록했다. 원본이나 앱은 변경하지 않았다.
