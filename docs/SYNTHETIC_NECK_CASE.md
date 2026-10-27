# 원본 사례에 연결된 합성 경동맥 구간

검사일: 2026-10-20. 실제 원본 동맥 사례의 1,081개 edge와 모든 node를 보존한 별도 합성 사례에 좌우 목 연결 2개를 추가했다. 저장 사례는 1,083개 edge이며 `exports/synthetic-neck-case/case.snapshot.json`에 있다. 앱 표시 사례를 변경한 작업은 아니다.

재현: Docker에서 `PYTHONPATH=src python scripts/build_synthetic_neck_case.py`. 기존 출력이 같은 revision이면 재사용하여 검사하고, 다르면 덮어쓰지 않고 실패한다.

## 명시적 연결 선택

[기존 neck 연결 코드](../src/vv_toolbox/atlas_neck.py)의 좌우 CCA/ICA part 대응과 superior CCA→inferior ICA 방향을 따른다. [끝점 검사](ACCESS_ROUTE_ENDPOINTS.md)에서 좌표를 확인하고 아래 앵커를 코드에 명시했다. 최근접 후보를 자동 채택하지 않았다.

| 구간 | CCA 끝점 | ICA 끝점 | 각 tangent handle 길이 mm |
|---|---|---|---:|
| 왼쪽 | FJ3483:e0 end | FJ1682M:e0 end | 69.996975 |
| 오른쪽 | FJ3564:e0 start | FJ1682:e0 start | 70.053092 |

명세는 원본 사례 canonical SHA256 `ac39f2d88883cf9f2389618a7ad6f0770dd3b5efef17278fbcefa02bf677aa24`에 결합되어 있다. [실행 명세](evidence/synthetic-neck-specification.json)는 Git 추적하며, shape는 원본 끝점 방향을 사용하는 96점 Hermite 곡선과 smoothstep 반경이다. Handle 길이를 endpoint chord 길이로 정하는 기존 표시 정책을 사용했다. 해부학적으로 측정된 경동맥 경로·분기점이나 임상 parameter가 아니다.

기존 표시 연결은 원본 mesh 단면 중심에 붙고, 새 사례 연결은 추출 중심선의 정확한 node에 붙는다. 서로 동일한 앵커가 아니다. 실제 차이는 CCA에서 좌/우 3.417/2.288 mm, ICA에서 0.795/0.831 mm이며 [검사 JSON](evidence/synthetic-neck-case.json)에 두 좌표와 단면 반경을 모두 기록했다. 원본 중심선을 mesh 단면으로 이동시키지 않았다.

## 실제 생성 및 수치 검사

- 원본 파일 bytes, 모든 source edge/node, 미확인 근거 상태 보존: PASS.
- 별도 snapshot 저장/재로드와 전체 사례 일치: PASS.
- 네 부착점의 좌표차·반경차: 모두 0 mm.
- sampled tangent 각도: 왼쪽 양끝 0.424119°, 오른쪽 양끝 약 0.502955°. 명시된 수치 기준 5°/반경차 1e-6 mm 이내: PASS. 이 기준은 임상 허용 범위가 아니다.
- 좌우 합성 연결 사이 모든 95×95 선분 조합 최소 중심선 거리: 36.146864 mm. 각 선분 최대 끝점 반경을 뺀 보수적 capsule 간격 하한: 28.946864 mm.
- 합성 연결 2개와 원본 CCA/ICA 4개에 대한 nonincident capsule 검사: PASS. 11쌍은 bounding box로 분리되며, 공유 부착점 4쌍은 이 검사에서 제외된다.

합성 사례 revision: `165cebe813b506cf1a12bd299de0b05c96890def6214e4233d85d33e3eea55b3`.

검토 그림: `exports/synthetic-neck-case/carotid-gaps.png`. 빨강은 원본 중심선, 주황은 합성 연결이다. 정면 X/Z와 측면 Y/Z를 같은 물리 좌표로 표시한다. 측면에서 좌우가 포개져 보이는 것은 2D 투영이며 위 간격은 3D 선분 계산이다.

## 남은 범위

경동맥 bifurcation과 ECA 연결은 생략되어 있다. 새 연결은 전부 `estimated / synthetic_estimate`이며 원본의 unresolved 상태를 해부학 승인으로 바꾸지 않는다. 원본 source part 사이의 실제 lumen 연결을 복구했다는 주장이 아니다.

전체 Atlas의 다른 모든 혈관과의 충돌, 공유 접합 collar 안의 표면, 최종 surface smoothness·self-intersection, 네 대퇴 접근 경로는 NOT RUN이다. 이번 PASS는 실제 원본을 보존한 별도 합성 사례 생성과 명시된 중심선 수치 검사 범위에 한한다.
