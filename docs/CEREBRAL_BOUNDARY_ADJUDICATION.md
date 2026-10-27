# 뇌혈관 경계 좌표 판정

검사일: 2026-10-20 · BodyParts3D 4.0 · research use only, not for clinical decision

## 결과

원본 16개 요소를 좌표 변환 없이 XY/XZ/YZ 투영으로 대조했다. **좌우 ACom 접합부 탐색용 표면 좌표 2개**를 확보했으며, **해부학적 경계 승인 좌표는 0개**다. 12개 경계는 `position=null`, `evidence_status=unresolved`를 유지한다. 표면의 가까운 정점은 중심선 접합점이나 혈관 내강의 연결을 증명하지 않는다.

이번 검사는 앞선 파일 존재 검사에서 실제 형상·공간 관계 검사로 범위를 확장했다. 원본 표면을 수정하지 않았으며, 합성 경계나 고정 비율 분할을 생성하지 않았다.

## 좌표·단위 계약

공식 20130619 배포 디렉터리의 [coordinate_system.png](https://dbarchive.biosciencedbc.jp/data/bodyparts3d/20130619/coordinate_system.png)를 내려받아 그림의 설명을 직접 확인했다.

- 길이 단위: **mm**.
- +X: 왼쪽, +Y: 뒤쪽, +Z: 위쪽.
- 원점을 유지하는 `bodyparts3d_native_LPS` 좌표계로 기록한다. DICOM 환자 좌표 affine이나 다른 자료와의 registration을 의미하지 않는다.
- 참조 그림 SHA-256: `338736275c11eac8c89531fdc14193c9a8adf5baab674033d9d89259f152a5f6`.

이 확인으로 해당 원본 좌표와 단위의 이전 미확인 상태를 해소한다. 좌표 계약 확인과 경계 해부학적 승인은 별개다.

## 원본 형상 관찰

| 검사 | 실제 관찰 | 판정 영향 |
|---|---|---|
| ACA–뇌량 | FJ1654/M은 ACom 주변의 짧은 근위 형상이다. FJ1699/M pericallosal을 함께 표시하면 genu 주변과 뇌량 상면을 따르는 주행이 보인다. FJ1676/M callosomarginal은 별도 주행이다. | FJ1654/M 하나를 A1–A3로 나누면 원위 구간을 잘못 지정한다. FJ1699/M 전체를 A3로 지정하는 것도 불가하다. |
| ACom–좌우 ACA | ACom FJ1655는 두 ACA 사이에 위치하며 각 끝 부근에 가까운 ACA 표면이 있다. 세 투영에서 탐색 후보 위치를 확인했다. | 화면 이동·검토용 후보 2개를 제공한다. 접합 중심·접합 평면 판정은 미완료다. |
| MCA–insula | FJ1692/M과 FJ1660/M, FJ1694/M의 주행을 좌우 insula FJ1748/1749와 대조했다. 원본 요소 경계 부근의 주행 전환은 보이나 별도 limen/sulcus 주석은 없다. | 원본 이름이나 파일 경계만으로 topographic M1/M2 또는 M2/M3를 승인하지 않는다. |
| M3 원위 | 검사한 명칭표에 별도 operculum/Sylvian exit 경계 주석이 없다. | 경계 없는 것을 혈관의 해부학적 결손으로 해석하지 않는다. |

투영은 서로 다른 깊이의 표면을 겹쳐 보여준다. 투영에서 접해 보이는 것을 내강 연결 PASS로 표시하지 않는다. 독립 영상, 임상 검수 및 표본별 해부학적 ground truth 대조는 NOT RUN이다.

## 앱에서 사용할 탐색 후보

| 경계 ID | ACA 표면 후보 [X,Y,Z] mm | ACom–ACA 최근접 정점 거리 mm |
|---|---|---|
| `B.R.ACA.A1_A2` | `[-3.35964, -111.652, 1538.03]` | 0.240363 |
| `B.L.ACA.A1_A2` | `[2.06185, -113.234, 1538.05]` | 0.214363 |

이는 표면 정점 간 거리이며 표면 간 최소거리·내강 거리·오차 허용치가 아니다. 정점 해상도에 의존하므로 작은 수치가 정확한 해부학적 판정을 뜻하지 않는다. JSON의 `inspection_locators`는 승인된 `boundaries[].position`과 분리되어 있다. 후보를 앱에 표시할 때 원자료 요소 ID와 해시, 후보 표면 좌표, 방법, 미확인 사유를 함께 유지한다.

A2/A3, A3/A4는 뇌량의 세부 지형에 대한 표본별 landmark 주석이 필요하다. M1/M2는 각 daughter의 실제 genu, M2/M3 및 M3/M4는 각 분지의 insular–opercular 및 피질 출구 판정이 필요하다. 이 위치를 최근접점이나 곡률 극값으로 자동 승인하지 않는다.

## 재현 및 검증

- 스크립트: `scripts/adjudicate_cerebral_landmarks.py`.
- Git 추적용 근거: [cerebral-boundary-adjudication.json](evidence/cerebral-boundary-adjudication.json). 원본 ZIP/OBJ/참조 그림 해시, 16개 형상 개수·범위, 후보의 정점 인덱스·좌표, 12개 미확인 사유를 보관한다.
- 로컬 그림: `exports/cerebral-boundary-inspection/aca-callosum.png`, `mca-insula.png`, `acom-closeup.png`. 각 그림은 3개 직교 투영을 포함하며 JSON에 해시가 있다. Git에는 원자료나 렌더링 이미지를 추가하지 않는다.
- Docker `python:3.12-slim`에서 NumPy/SciPy/Matplotlib을 사용했다. 원본 ZIP 해시 일치, 요소 파일 유일성, 유한 좌표, 삼각형 정점 인덱스 범위 검사 PASS.
- 실제 3개 투영 그림 열람 PASS. 해부학적 경계 승인 및 임상 검증 NOT RUN. 앱 UI 검증은 별도 작업이다.

공식 [BodyParts3D 설명](https://lifesciencedb.jp/bp3d/info_en/index.html)은 수작업 제작·변형된 구조와 세분화에 따른 개념 대응 오류 가능성을 설명한다. 따라서 파일명 대응과 공간적 근접만으로 표본별 해부학적 확정을 대신하지 않는다.
