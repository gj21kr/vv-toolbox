# 팔머리동맥–우 CCA–우 쇄골하동맥 접합 검사

`scripts/inspect_brachiocephalic_junction.py`가 FJ3417, FJ3564, FJ3579의 실제 source mesh·열린 경계·중심선·5개 축상 단면을 대조했다. [검사 JSON](evidence/brachiocephalic-junction.json)은 원본 archive·OBJ·preview hash와 case revision, 경계 정점, 단면, 끝점의 좌표·반경·방향을 포함한다. 원본 graph와 앱 주석은 변경하지 않는다.

## 원본에서 확인한 구조

세 원본은 모두 watertight가 아니다. 각각 7/4/8개의 boundary 경로를 추출했으나 대부분 면적 0의 되돌이 경로·작은 crack이다. 특히 CCA의 네 boundary는 모두 면적 0으로, 접합 근처의 독립된 원형 opening으로 승인할 수 없다. 정상 내강 또는 cap 존재를 boundary 개수만으로 판단하지 않는다.

실제 원본의 Z 범위는 BCT **1304.320–1342.280 mm**, RCCA **1329.420–1373.380 mm**, 쇄골하동맥 **1330.940–1353.030 mm**이다. BCT가 높은 쪽에서 끝나고 RCCA가 더 높은 목 방향으로 이어지며, 쇄골하동맥은 음의 X 방향으로 길게 뻗는다. 이는 source 좌표상의 관찰이며 독립적인 해부학 검증이 아니다. 각 source는 유한하게 잘린 요소이고, 열린 경계와 별도 겹친 표면으로 표현되어 있다.

축상 단면의 결과:

| Z mm | 실제 source 단면 관찰 |
|---|---|
| 1327.2 | BCT만 나타남 |
| 1331.2 | RCCA 46/46, 쇄골하 13/13 단면 정점이 BCT 단면 내부. 엄격한 선분 교차 0개 |
| 1335.2 | RCCA 50/50 정점이 BCT 내부. 가까운 쇄골하 loop는 29/33 정점 내부·2개 교차. 원위 쇄골하 재절단 loop는 별개 |
| 1339.2 | RCCA 27/52, 가까운 쇄골하 8/28 정점이 BCT 내부. 각 2개 교차 |
| 1343.2 | BCT 단면은 없고 두 daughter의 단면이 남음 |

이는 **원본의 별도 표면끼리 내부 중첩 후 갈라지는 배치**를 보여준다. 정점 포함·선분 교차는 해당 2D 단면 검사이며, 3D 공통 내강의 완전한 연결을 증명하지 않는다. 원위 쇄골하 재절단 결과도 JSON에서 보존하며 그림만 동일 국소 범위로 crop했다.

![원본 접합 3방향](../exports/brachiocephalic-junction/source-junction.png)

![원본 5개 축상 단면](../exports/brachiocephalic-junction/source-sections.png)

## 합성 접합 검토용 끝점

기존 capsule first witness가 가리킨 RCCA 내부 위치(끝까지 13.17 mm)는 기시점으로 채택하지 않았다. source의 위/아래 extent와 실제 세 표면을 대조해 **BCT start, RCCA end, 쇄골하 end**를 명시적 국소 접합 검토 위치로 기록했다.

| 역할 | edge / endpoint | interval / fraction | XYZ mm | 반경 mm |
|---|---|---|---|---:|
| BCT | FJ3417:e0 start | 0 / 0 | [-13.6,-109.6,1335.2] | 5.306600 |
| RCCA | FJ3564:e0 end | 44 / 1 | [-12.8,-108.8,1333.6] | 3.919184 |
| 쇄골하 | FJ3579:e0 end | 78 / 1 | [-15.2,-106.4,1336.8] | 4.000000 |

BCT–RCCA 거리 **1.959592 mm**, BCT–쇄골하 **3.919184 mm**이다. 좌표가 가깝다고 직결 tube를 승인하지 않는다.

끝점에서 원본 내부 5 mm chord의 반대 방향을 outward tangent로 계산했다. BCT→RCCA 연결 chord와 BCT outward의 cosine은 **−0.774996**, RCCA→BCT chord와 RCCA outward는 **−0.979340**이다. 짧은 직결이 두 원본의 자연스러운 연장 방향을 거스른다. 특히 BCT 1335.2→RCCA 1333.6 mm로 먼저 내려갔다가 목으로 올라가므로, 단순 Hermite 연결은 작은 되돌이 고리를 만들 수 있다.

BCT–쇄골하는 각각 **0.706262 / 0.942809**로 대체로 같은 방향이지만 삼자 junction 표면 검증 전 별도 bridge를 승인하지 않는다. JSON의 모든 연결은 `straight_bridge_accepted=false`, `anatomical_approval=UNKNOWN`이다.

## 구현에 전달하는 조건

이 끝점 묶음은 **중첩 지역을 재구성하기 위한 후보**이며 즉시 실행 가능한 두 개의 Hermite bridge 승인안이 아니다. 부모 내부 split은 현재 후보 자체에는 필요 없지만, 실제 생성기는 별도 합성 모델에서 terminal tail trim, 공통 junction으로의 endpoint coalescence, 또는 국소 junction remesh를 검토해야 한다. 이때 원본 그대로인 형상과 합성 변경 영역을 분리해 추적한다.

후속 선택에서는 세 branch의 진행 방향·반경과 공통 내강, 최종 표면의 단면 연결 및 비인접 충돌을 함께 검사한다. RCCA와 쇄골하를 직접 parent–daughter로 연결하거나 가까운 점을 강제로 합쳐 해부학적 연결로 표시하지 않는다. 해부학적 parent 관계는 [기존 문헌 대조](NECK_CONTACT_RELATIONS.md)의 일반 reference를 유지하며, 본 Atlas의 실제 내강 승인은 **UNKNOWN**이다.

Docker 실행으로 입력 revision·archive 검증을 통과했고 실제 두 그림을 열어 확인했다. 원본·graph·앱 변경 없음. source 입력과 출력 재현성 검사는 별도 SHA 비교로 수행한다.
