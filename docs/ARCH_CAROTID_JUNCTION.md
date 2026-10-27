# 대동맥궁–좌 총경동맥 접합 후보

`scripts/inspect_arch_carotid_junction.py`는 원본 FJ3411 대동맥궁과 FJ3483 좌 CCA의 삼각형, 열린 경계와 단면을 검사한다. 원본 graph·mesh를 수정하지 않는다. [검사 JSON](evidence/arch-carotid-junction.json)에 source archive·OBJ·preview hash, 중심선 case revision, 모든 경계·단면 좌표와 명시적 합성 anchor를 보관한다.

## 실제 원본 검사

두 원본 모두 watertight가 아니다. CCA에는 7개의 경계 경로가 있으며, 실제 단면 형태의 구멍 외에 면적 0에 가까운 되돌아오는 경로와 비평면 side hole이 포함된다. 따라서 중심선 시작점에 가장 가까운 경계 하나를 자동 기시점으로 채택할 수 없다.

가장 가까운 경계 2는 시작점에서 1.784 mm이지만 평면 이탈 최대 3.990 mm로 횡단 terminal opening에 적합하지 않다. 경계 3은 12개 정점, 중심 **[16.029958, -99.457684, 1307.692515] mm**, 투영 면적 38.744 mm², 등가 반경 3.512 mm, 최대 평면 이탈 0.463 mm이다. CCA 초기 5 mm chord 방향과 경계 법선의 내적 절댓값은 0.967이며 시작점보다 proximal 방향으로 3.616 mm에 있다.

이 관찰에 따라 **면적 >1 mm², 평면 이탈 <등가 반경의 25%, 법선 정렬 >0.8, 시작점보다 proximal**인 경계를 후보로 정했다. 이는 이번 원본의 side hole을 구분하는 공학적 선택 규칙이며 임상 기준이나 사전 등록된 수용 기준이 아니다. 해당 조건을 만족하는 경계가 정확히 하나일 때만 후보를 출력한다.

선택한 경계 법선 방향으로 -3, -1, 0, +1, +3, +5 mm에서 실제 source mesh를 절단했다. -3/-1 mm에는 CCA 단면이 없고, 0/+1/+3/+5 mm에서는 각각 **19/19, 23/23, 20/20, 20/20개 CCA 단면 정점이 대동맥궁의 닫힌 2D 단면 내부**에 있었다. 표본 정점 포함 검사이며 전체 삼각형 또는 내강 연결을 증명하지 않는다.

CCA opening 정점과 궁 삼각형의 거리는 최소 7.05, 최대 8.97, 평균 7.98 mm이다. 이것을 두 혈관 사이의 빈 공간이라고 해석하면 안 된다. 단면 검사와 함께 보면 CCA 근위 부분이 궁의 모델 내부에 들어간 배치이다. 별도 표면이 공통 내강으로 접합되었다는 뜻은 아니다.

![원본 표면과 합성 anchor 후보](../exports/arch-carotid-junction/source-opening-candidate.png)

![원본 단면: 빨강 궁, 주황 CCA](../exports/arch-carotid-junction/source-sections.png)

## 합성 연결 실험용 명시적 anchor

선택한 source opening 중심을 궁의 source 파생 중심선에 투영했다. 이 투영은 위의 실제 경계·단면 근거를 바탕으로 별도 합성 모델을 구성하기 위한 선택이며, 해부학적 기시점 복원이 아니다. 이전 capsule 검사에서 처음 만난 **arc 21.30 mm**와 구분한다.

| 항목 | 값 |
|---|---|
| 부모 edge | FJ3411:e0 |
| 분할 interval / fraction | 32 / 0.3576715787251739 |
| LPS mm anchor | [17.08613726298014, -100.51386273701988, 1305.6000000000001] |
| 부모 보간 반경 | 11.604863281413817 mm |
| 부모 시작부터 arc | 36.477290922205384 mm |
| 자식 endpoint | FJ3483:e0 start |
| 자식 LPS mm / 반경 | [16.8, -100.0, 1311.2] / 4.0 mm |
| 부모 anchor→자식 endpoint 거리 | 5.630801847495817 mm |
| source opening 중심→부모 anchor 거리 | 2.570923598845922 mm |
| 상태 | synthetic_estimate_candidate; anatomical approval UNKNOWN |

다음 연결 실험은 이 주석과 source revision을 고정하고 별도 합성 궁을 분할해 수행할 수 있다. split 위치에서 부모 반경을 유지한다. 짧은 daughter connector와 3-way surface blending은 별도 생성·검사 대상이며, 11.6 mm 부모 반경을 daughter tube 전체에 그대로 적용하지 않는다. anchor와 CCA 시작점이 궁의 source 모델 내부에 있으므로 단순 tube를 겹쳐 놓은 표면을 완료 결과로 사용하지 않는다. 합성 surface union, 분기부 단면, 반경 변화, 주변 혈관 충돌, graph incidence를 확인해야 한다.

실제 source 내강 접합 **UNKNOWN**, source graph 승격 **없음**, 환자별·임상 검증 **NOT RUN**이다.
