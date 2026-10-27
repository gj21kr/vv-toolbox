# 경동맥 합성 내강 결합

`solid_union.build_solid_union`은 이름이 지정된 원본 복사본과 추정 연결부를
별도 합성 형상으로 결합한다. 입력 표면은 이동하거나 덮어쓰지 않는다.

## 구현과 검사

- 선택 의존성: `pip install -e '.[solid]'`, `manifold3d==3.5.4`.
- Docker 개발 환경에만 패키지를 설치했다. 호스트 환경은 변경하지 않았다.
- 입력을 동일 좌표 정점 인덱스로 정규화하고, 양의 닫힌 체적 및 자기 접촉을 검사한다.
- 원점 이동 후 Manifold 결합을 수행하고 다시 원래 좌표계로 돌린다.
- 출력은 양의 닫힌 체적, 단일 경계 연결 성분 및 자기 접촉 검사를 통과해야 한다.
- 입력별 형상 해시, 체적, 패키지 버전 및 원점 이동량을 결과에 기록한다.

[Trimesh 공식 Boolean API](https://trimesh.org/trimesh.boolean.html)의
`union(..., engine='manifold', check_volume=True)`를 사용한다.
어댑터의 float32 변환이 있으므로 원본 삼각형의 정확한 보존을 출력 형상에
주장하지 않는다. 원본 입력 보존과 출력의 형상 충실도는 별도 항목이다.

합성 상자 두 개의 중첩 결합에서 예상 체적 12 mm³ 및 원본 배열 보존을
확인했다. 분리된 두 상자는 단일 형상으로 승인하지 않았다.
관련 검사 2개 PASS: `evidence/solid-union-tests.xml`.

## 실제 경동맥 적용

실행: `PYTHONPATH=src python scripts/build_carotid_solid_union.py`.
꼭짓점 보존 경동맥 후보를 닫고 양쪽 원본 혈관을 함께 결합한다.
결과는 `exports/carotid-solid-union/`, 검사 기록은
`docs/evidence/carotid-solid-union.json`에 생성한다.
실제 좌우 두 사례 모두 출력의 양의 닫힌 비퇴화 체적 검사에서 FAIL이었다.
입력 자기 접촉 검사를 통과한 뒤 결합 출력 검증에서 거부되었으며,
출력을 승인하거나 데모에 적용하지 않았다.
기록: [carotid-solid-union.json](evidence/carotid-solid-union.json).
다음 진단에서는 닫힘, 방향, 체적 및 퇴화 삼각형 수를 각각 분리하여
실패 원인을 확인해야 한다. 합성 상자 검사 통과를 실제 경동맥 통과로 확대하지 않는다.

연결 성분 검사는 해부학적 분기 정확성이나 접합 매끄러움의 증거가 아니다.
주변 혈관 재검사, 원본 대비 형상 오차, 출력 라벨 대응 및 앱 적용은 별도 작업이다.

## 실패 원인 분리 및 float64 경로

`--diagnostics` 재실행에서 좌우 모두 닫힘, 일관된 방향, 양의 체적은
통과했다. 실패 원인은 면적 0인 삼각형으로, 왼쪽 26개·오른쪽 74개였다.
기존 실패 기록은 보존하며 세부 결과는
[carotid-solid-union-diagnostic.json](evidence/carotid-solid-union-diagnostic.json)에 기록했다.
검사에서 거부된 표면도 `exports/carotid-solid-union-diagnostic/*-unaccepted.npz`로
별도 저장했다.

Trimesh 어댑터의 float32 입출력 대신 Manifold의 `Mesh64` / `to_mesh64`를
사용하는 경로를 추가했다. 라이브러리 함수 기본값은 float64이며,
실제 데이터 실행 도구는 `--diagnostics --float64`로 비교 경로를 명시한다.
Manifold 입력 및 결합 상태도 확인한다. 진단 콜백은 독립된 표면 복사본을
받아 실제 검사 형상을 변경할 수 없다.

float64 경로의 합성 결합·분리 거부·진단 복사본 검사 3개 PASS
(`evidence/solid-union-float64-tests.xml`).

## 실제 float64 결과

좌우 모두 닫힌 양의 체적, 단일 경계 연결 성분 및 자기 접촉 검사를 통과했다.
면적 0인 삼각형은 양쪽 모두 0개다.

| 후보 | 삼각형 수 | 체적(mm³) | 최소 삼각형 면적(mm²) |
|---|---:|---:|---:|
| 왼쪽 | 24,764 | 5,324.344072 | 0.0000996731 |
| 오른쪽 | 31,812 | 4,951.259513 | 0.0000124800 |

검사 기록:
[carotid-solid-union-diagnostic-float64.json](evidence/carotid-solid-union-diagnostic-float64.json).
결과 파일은 `exports/carotid-solid-union-diagnostic-float64/`의
`estimated_left_carotid_neck.npz`, `estimated_right_carotid_neck.npz`다.
`-unaccepted` 파일은 검증 전 콜백 복사본이므로 최종 후보와 구분한다.

`scripts/inspect_carotid_union_paths.py`에서 기존 선언된 Hermite 중심선을
변경하지 않고 검사했다. 양쪽 각 95개 선분 전체를 내부 거리 기반 분할
검사로 포함 확인했으며 바깥 표본 및 미확정 구간은 0개다.
검사 기록: [carotid-union-paths.json](evidence/carotid-union-paths.json).
이는 목 연결부의 중심선 포함 검사이며 대퇴–뇌혈관 전체 경로 검사,
접합부 매끄러움 또는 해부학적 연결 승인을 의미하지 않는다.
원본은 보존했고 데모 장면은 변경하지 않았다.

## 결합 표면의 원본 대응 거리

`scripts/inspect_carotid_union_fidelity.py`에서 출력의 모든 꼭짓점과 삼각형
중심을 원본 혈관 두 개 및 열린 연결부 측면까지의 최근접 거리로 검사했다.
임시 연결부 cap은 참조 표면에서 제외했다.

| 후보 | 표본 수 | 최대 거리(mm) | 1e-6 mm 초과 표본 |
|---|---:|---:|---:|
| 왼쪽 | 37,148 | 2.1725e-11 | 0 |
| 오른쪽 | 47,720 | 4.1289e-10 | 0 |

[carotid-union-fidelity.json](evidence/carotid-union-fidelity.json)에
입출력 파일 해시와 거리 통계를 보존했다.
이 결과는 출력 표본에서 입력 표면 방향의 거리 측정이다.
역방향 형상 누락, 삼각형 내부 전체에 대한 연속 거리 상한,
임시 cap의 노출 면적을 직접 검증한 결과는 아니다.

결합 전후 주변 혈관 비교는 `scripts/inspect_carotid_union_neighbors.py`로
실행을 완료했다. 양쪽 후보를 동시에 결합한 장면과 결합 전 구성 표면을 비교하며,
새로 접촉하는 혈관 및 미확정 검사를 기록한다.
같은 혈관에서 접촉 위치가 달라지는 경우까지 동등성을 주장하지 않는다.
양쪽 각 805개, 총 1,610개 비교에서 새로 접촉하는 혈관 및 미확정 결과는
0개였다. [검사 기록](evidence/carotid-union-neighbors.json)에 전체 비교를 보존했다.

## 결합 삼각형의 원본 대응

`manifold-solid-union/2`는 입력마다 Manifold original ID와 원본 face ID를
등록하여 출력 삼각형의 출처를 보존한다. `face_lineage`에는 원본 이름 목록,
출력 면별 원본 인덱스, 원본 면 번호가 들어간다.
동일 좌표 인덱스 정규화는 면 순서를 바꾸지 않으므로 원본 면 번호를 유지한다.
거리 기반 추측 라벨이 아니라 결합 연산의 출처 정보이며,
해부학적 구간 라벨은 아직 지정하지 않는다.

합성 도형에서 각 출력 삼각형의 꼭짓점이 지정된 원본 삼각형 위에 있는지
확인했다. 관련 검사 3개 PASS: `evidence/solid-union-lineage-tests.xml`.
실제 좌우 경동맥은 `--diagnostics --float64 --lineage`로 별도 재생성을 완료했고,
양쪽 모두 단일 닫힌 양의 체적과 자기 접촉 검사를 통과했다.
기록은 `evidence/carotid-solid-union-diagnostic-float64-lineage.json`이다.
출처 정보를 추가한 경로가 이전 출력과 동일하다고 가정하지 않으며,
기존 파일은 보존한다.

`union_lineage.verify_face_lineage`는 각 출력 삼각형의 세 꼭짓점과 지정된
원본 삼각형 간 거리를 계산하고 법선 방향을 확인한다. 원본 이름·면 번호의
범위와 완전성도 검사한다. 지정된 원본 삼각형은 볼록하므로 꼭짓점 거리
검사는 전체 출력 삼각형의 대응을 확인하는 데 사용할 수 있지만,
부동소수점 계산이며 해부학적 라벨 검증은 아니다.
정상 대응, 잘못된 면 번호, 범위를 벗어난 원본 번호 및 기존 결합 동작을
포함해 6개 검사 PASS (`evidence/union-lineage-validation-tests.xml`).
실제 검사 도구는 `scripts/inspect_carotid_union_lineage.py`이며,
입력 형상 해시를 확인한 뒤 결과를 기록한다.

실제 좌우 총 56,576개 출력 삼각형 모두에서 지정 원본 면 대응과 법선
방향 검사가 PASS였다. 최대 꼭짓점 거리는 약 1.24e-11 mm이며,
대응 실패·반대 방향 법선은 0개다.
[실제 대응 검사](evidence/carotid-union-lineage.json)에 원본별 면 수와 거리를 기록했다.
출력 NPZ SHA256은 출처 기록 추가 전의 중심선·형상 거리·주변 혈관 검사에
사용한 파일과 좌우 각각 동일하다. 따라서 동일 형상이라는 근거가 확인됐다.
이 출처 정보는 원본 혈관 이름과 추정 연결부의 구분이며,
ACA/MCA 구간 등의 해부학적 라벨을 새로 확정한 것은 아니다.

## 앱의 읽기 전용 후보 보기

합성 후보 선택 목록에 좌측·우측 경동맥 내강 결합 후보를 추가했다.
원본 Atlas 편집과 분리된 기존 후보 모드를 사용하며,
원본으로 돌아가는 동작을 유지한다.
입력 revision과 형상 SHA256이 중심선·면 출처·주변 혈관 검사와 일치해야 로딩된다.
합성 추정 범위, 검사된 항목, 접합 매끄러움 및 해부학적 연결 미확인을 표시한다.
이 모드에서 결합 모델의 혈관별 선택·편집 연결은 아직 구현하지 않았다.

후보 로딩·변조 거부·revision 불일치 및 기존 후보 회귀 검사 12개 PASS
(`evidence/carotid-preview-tests.xml`). 현재 데모 서버에 반영했다.
`scripts/verify_carotid_preview_ui.cjs`에서 좌우 후보 선택, 검사 문구,
Atlas 복귀를 확인했다. 첫 실행은 복귀 요청의 비동기 정상 응답 202를
200만 허용한 테스트 오류로 실패했다. 이를 수정한 후 제어부 검사는 PASS다.
([기록](evidence/carotid-preview-ui.json)).
제어부 screenshot을 직접 확인했고 표시 문구가 읽히는 것을 확인했다.
수정된 검사는 3D iframe 요청을 차단한 제어부 전용 검사이므로,
실제 3D 화면 검증은 NOT RUN으로 유지한다.

후속 실제 3D 캡처를 직접 확인했을 때 혈관이 표시되지 않았고
`Invalid controls` 오류가 보였다. 기존 일반 후보 설명에서
`pair_surface_separation`을 참조하던 코드가 경동맥 후보에 적용되어
카메라 이동 전에 예외가 발생했다. 경동맥 전용 설명을 추가했다.
실패 캡처 판정은 `evidence/carotid-preview-ui-render-before-fix.json`에
FAIL로 보존했다. 캔버스 존재만 확인한 자동 결과를 시각적 성공으로 인정하지 않았다.

설명 회귀 검사를 포함한 후보 테스트 13개가 통과했다.
브라우저 검사도 후보 전환 응답 상태와 `/candidate` 장면 수신을 확인하도록
강화했다. 수정 후 실제 3D 캡처 검사는 실행 중이다.

화면 갱신을 무제한 기다리던 테스트 코드를 제한 시간 대기로 수정했다.
또한 기본적으로 숨겨질 수 있는 장면 트리의 `/candidate` 항목 대신
3D 패널에 실제 표시되는 좌·우 후보 설명을 기다리도록 바꿨다.
왼쪽 수정 후 캡처에서는 빨간 경동맥 표면, 후보 설명 및 오류 표시 제거를
직접 확인했다. 양쪽 최종 자동 재검사는 아직 실행 중이다.

앱 설명 오류 수정까지 포함한 전체 Docker 회귀 검사:
**1,054 PASS**, 355개 기존 NumPy/scikit-image deprecation warning,
149.89초 (`evidence/carotid-integration-full-tests.xml`).
이 결과는 전체 개발계획 완료나 임상 검증을 의미하지 않는다.

최종 자동 재검사는 iframe 내 좌측 후보 설명을 찾는 단계에서 60초 시간
초과로 실패했다. 왼쪽 저장 캡처의 실제 혈관 표시는 확인했지만 양쪽 전체
자동 흐름은 검증되지 않았다. [재검사 기록](evidence/carotid-preview-render-retry.json)에
이를 구분해 남겼으며, 테스트 정리 단계에서 Atlas로 복귀했다.

## 원본 혈관별 선택 범위

`union_selection.select_union_source`는 원본 혈관 이름으로 출력 면을 선택하고,
해당 원본 면 번호, 선택 정점, 다른 원본과 공유하는 접합 정점,
선택 영역에만 속한 정점을 반환한다. 공유 정점은 독립 편집 범위에서
분리하여 경계를 함께 편집해야 함을 명시한다.

선택 범위·공유 경계·잘못된 원본 번호 검사 5개 PASS
(`evidence/union-selection-tests.xml`).
실제 좌우 56,576개 면을 세 원본별로 빠짐없이 한 번씩 분류했다.
추정 연결부의 공유 정점은 왼쪽 244개, 오른쪽 312개다.
[실제 선택 범위 검사](evidence/carotid-union-selections.json)에 원본별 개수를 기록했다.
형상은 변경하지 않았다. 앱의 상호작용 선택 및 선택 영역 변형은 아직 미완료다.

## 앱의 원본 혈관 부분 선택

후보 보기 아래에 원본 혈관 선택 목록을 연결했다.
내경동맥, 총경동맥, 추정 목 연결부를 선택하면 해당 원본에서 유래한 면만
표시하고, `전체 결합 표면`으로 복귀할 수 있다.
전체 정점과 전체 면 배열은 보존하며 표시 면만 변경한다.
부분 면 수와 접합 공유 정점 수를 표시하고, 부분 보기임을 명시한다.
선택은 편집이 아니며 반경·굴곡·비틀림 변경에는 아직 연결하지 않았다.

선택·복귀·잘못된 선택 거부 및 기존 후보 검사를 포함해 20개 PASS
(`evidence/carotid-source-selection-tests.xml`).
실제 브라우저에서 양쪽 각 3개 원본 선택과 전체 복귀를 확인했다
([기록](evidence/carotid-preview-ui-selection.json)).
부분 선택 UI 캡처를 직접 확인했다. 이 검사는 3D iframe을 차단한
제어부 검사이며 부분 표면의 실제 3D 렌더링 검사는 미완료다.
