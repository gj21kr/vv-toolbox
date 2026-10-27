# 접근 모델의 굴곡·비틀림 후보

## 등록 사례의 벽·그래프 동시 변경

접촉 상세 표를 8093 데모에 배포했다. [실제 HTTP 대조 검사](evidence/context-review-live-ui.json)는 저장된 전체 788개 결과의 접촉·미확인 91행을 모두 대조해 PASS이며 사례 revision을 보존했다.

작업창의 접촉 상세 표는 저장된 현재 형상 검사에서 접촉·미확인 항목 전체를 표시하고 변경 전후 상태, 추가·제거된 삼각형 접촉 쌍을 구분한다. [저장 결과 UI 대조](evidence/context-review-ui.json)는 91개 표시 행 전체가 원기록과 일치하고 사례 revision이 유지됨을 확인했다. 추가 접촉 쌍이 있는 5개 이웃은 모두 기존에도 접촉하던 혈관이므로 새로 접촉한 혈관 5개라는 뜻이 아니다. 최신 HTML과 실제 API를 사용한 별도 화면 검사이며, 상세 표의 데모 배포는 아직 남아 있다.

8093 데모 서버에 공동 편집 기능을 반영했다. [실제 HTTP 브라우저 검사](evidence/source-chain-live-ui.json)는 합성 분할 사례의 두 구간 편집·노드 보존·undo/redo·다운로드 일치에 PASS이며 화면 캡처도 확인했다. 서버 재시작 뒤 기존 전체 검사 작업은 COMPLETE 788/788, 형상 판정 FAIL과 동일 출력 revision으로 복구됐다. 최초 재시작의 컨테이너 내부 bind 설정으로 호스트 접속이 되지 않았으나 `VV_BIND_HOST=0.0.0.0`으로 수정했다. Docker의 호스트 포트는 계속 127.0.0.1:8093/8094에만 공개된다. 마스크 계산 프로세스는 유지했다.

[실제 전체 비동기 브라우저 검사](evidence/full-context-job-ui.json)는 788/788 완료 후 PASS다. 요청은 한 번만 접수됐고 새로고침 후 같은 작업을 이어 보았으며, 저장 결과는 CLI 사례와 정확히 일치했다. UI는 주변 검사 FAIL·생성 미승인을 표시하고 Atlas는 변경하지 않았다. 완료 화면을 직접 확인했다. [저장 작업 복구 검사](evidence/full-context-recovery.json)도 PASS: 새 작업 관리 인스턴스에서 완료 결과를 읽었고 자동 계산을 시작하지 않았다. 복구 검증의 PASS는 혈관 형상 수용을 뜻하지 않는다.

[실제 접근 모델의 공동 편집](evidence/access-source-chain.json)은 272.975초에 PASS로 종료됐다. FJ2074를 공학적으로 두 구간으로 나눈 뒤 bend 0.25 mm·twist 0°를 적용했고, 결합 표면에 등록된 전체 66개 경로가 벽 내부 포함 검사를 통과했다. 노드·라벨·반경·비선택 경로를 보존했다. [별도 재조회](evidence/access-source-chain-reload.json)에서도 출력 revision, 표면 연결 구조·면 출처와 모든 검사 경로의 ID가 일치했다. 새 형상의 주변 검사는 NOT RUN이며 생성 승인 false다. [선택 순서 검사 13개 PASS](evidence/source-chain-selection-tests.xml)는 역방향 구간, 어느 구간을 선택하는지와 edge 배열 순서에 무관한 동일 변형을 확인한다.

[통합 회귀 검사 40개 PASS](evidence/source-chain-context-integration-tests.xml): 공동 편집, 작업창, 검사 이력 및 비동기 작업 저장 계층을 함께 실행했다. 실제 접근 모델의 FJ2074 중심선을 기존 station 714에서 나눈 공학 검증 사례도 별도로 실행한다. 분할 전 표면 해시와 구간을 다시 합친 중심선이 원본과 정확히 일치함을 먼저 확인했다. 이 분할점은 해부학적 경계 주석이 아니며, 해부학적 경계 12개를 확인한 것으로 세지 않는다. 최종 공동 변형과 전체 경로 검사는 [별도 기록](evidence/access-source-chain.json)에 남긴다.

작업창은 서버가 확인한 원본 연결 조건에 따라 편집 가능 여부와 함께 바뀌는 구간 ID를 표시한다. [분할 구간 브라우저 검사](evidence/source-chain-ui.json)는 역방향 구간을 포함한 합성 사례에서 공동 변형·노드 보존·undo/redo·다운로드 일치를 확인했다. 최신 HTML과 Docker의 실제 요청 처리기를 사용한 별도 통신 경로 검사이며, 8093 서버에 배포한 검사는 아니다. 화면 캡처에서 두 구간 표시와 입력·버튼 가독성을 직접 확인했다. 전체 검사 실행이 끝난 뒤 실제 서버 반영이 필요하다.

계산 계층은 같은 원본 혈관에 속한 여러 구간이 하나의 열린 연결 경로를 이룰 때 공동 편집을 지원한다. 명시적인 그래프 연결로 구간을 정렬하고 하나의 변형장을 벽과 전체 중심선에 적용한다. 각 구간의 방향·라벨·반경 배열과 그래프 연결점은 보존하며, 모든 변경 구간의 벽 내부 포함 여부를 다시 검사한다. 분기·순환·분리된 원본은 아직 지원하지 않는다. [합성 검사 18개 PASS](evidence/source-chain-shape-tests.xml): 역방향 구간, 접합점 보존, 누락된 접합 좌표와 잘못된 연결 거부, 기존 단일 구간 동작 및 검사 이력을 포함한다. 실제 Atlas의 분할 구간 및 앱 선택 조건 확장은 아직 검증하지 않았다. 실행 중인 전체 검사 보존을 위해 서버는 재시작하지 않았다.

전체 새 CLI 검사는 788/788개를 완료했다. [측정 결과](evidence/registered-context-fresh.json)는 FAIL이며 변경·확장 접촉 5개, 잔존 접촉 80개, 미확인 11개를 기록한다. [독립 재조회 검사](evidence/registered-context-result-verification.json)는 PASS: 이전 전체 측정의 788행과 일치하고 저장 사례의 벽·그래프가 검사 전과 동일하다. 이는 형상 수용 PASS를 의미하지 않는다. 실제 브라우저의 별도 전체 작업은 실행 중이며 최종 UI 판정은 아직 없다.

새 검사 반영 시 이전 context와 그 출처 binding은 함께 context_history로 이동한다. 현재 측정에 이전 출처가 붙지 않으며 원래 사례·벽·그래프는 보존한다. [회귀 검사 7개 PASS](evidence/registered-context-history-tests.xml).

작업창의 `새 주변 검사 실행 / 이어 보기`는 비동기 검사 API를 호출하고 준비 상태·완료 수·최종 판정을 표시한다. 계산 중 사례 교체와 편집을 잠그며 완료 결과의 입력 revision을 확인한 뒤 사례에 반영한다. 같은 탭의 작업 ID를 보관해 동일 입력 사례를 다시 열었을 때 조회를 이어 갈 수 있다. 네트워크 오류는 자동 재실행하지 않고, ERROR/INTERRUPTED 또는 만료된 작업은 명시적 재요청이 필요하다. 결과 반영도 undo/redo·다운로드 대상이며 생성 승인 false를 유지한다.

[관련 검사 21개 PASS](evidence/context-job-ui-support-tests.xml). [제어된 브라우저 검사 PASS](evidence/context-job-ui.json): 실제 수치 검사로 만든 작은 합성 사례를 사용하되 작업 통신은 제어된 응답으로 대체했다. 진행 표시·입력 잠금·완료 반영·중복 접수 없는 이어 보기·다른 revision 거부를 확인하고 진행/완료 캡처를 직접 확인했다. 이는 전체 Atlas의 비동기 검사를 실제 서버에서 끝낸 검증은 아니다. 788개 전체 CLI 실행은 별도 진행 중이며 그 결과를 UI 테스트의 성공으로 대체하지 않는다.

새 주변 검사의 비동기 서버 관리 계층을 추가했다. `POST /api/case-context-jobs`는 사례 snapshot을 받아 작업 ID를 반환하고, `GET /api/case-context-jobs/<id>`와 `/result`로 상태·완료 사례를 조회한다. 같은 사례의 실행 중 요청은 하나로 합치고 다른 사례의 동시 요청은 409로 거부한다. 오류 작업의 결과는 반환하지 않으며 완료 검사도 생성 승인으로 바꾸지 않는다. [관련 검사 15개 PASS](evidence/context-jobs-tests.xml).

작업별 입력 snapshot·상태·완료 결과를 `exports/context-jobs/<id>/`에 저장한다. 메모리와 재시작 복구는 최신 네 작업을 제공하며 이전 파일은 삭제하지 않는다. 완료 결과 복구 시 입력·출력 revision과 검사 연결을 확인한다. 실행 중 기록은 재시작 시 INTERRUPTED로 표시하고 자동 재실행하지 않는다. 손상된 결과는 ERROR로 거부하며 원본 파일을 보존한다. 앱 진행률 UI와 중단 계산 자체의 재개는 아직 연결하지 않았다. CLI로 실행 중인 검사와 이 작업 관리자는 별도이며 기존 CLI 작업을 자동 인수하거나 재시작하지 않는다.

[영속 저장 관련 검사 13개 PASS](evidence/context-job-persistence-tests.xml): 완료 결과 복구, 중단 작업의 자동 재실행 방지, 손상된 출력 거부, 입력 보존과 기존 단일 실행 규칙을 확인했다. 실제 HTTP 오류 작업에서도 입력 snapshot과 ERROR 상태가 디스크에 저장되는 것을 [API 기록](evidence/context-job-api.json)에 확인했다. 실제 서버 재시작 후 전체 788개 성공 작업 복구의 검증은 아직 아니다.

[실제 HTTP 검사 PASS](evidence/context-job-api.json): 잘못된 snapshot 400, 작업 접수 202, 미지원 부모의 ERROR, 실패 결과 조회 409, 없는 작업 404와 Atlas 불변을 확인했다. 전체 성공 작업을 API로 완료한 검증은 아직 아니며, 기존 788개 CLI 검사를 중복 실행하지 않았다.

새 측정은 `scripts/inspect_registered_context.py --case <snapshot> --report <새 결과 JSON> --output <새 사례 JSON>`으로 Docker에서 실행한다. 현재 실행기는 등록된 접근 부모 사례에서 직접 파생한 단일 결합 표면을 지원한다. 임의의 다른 기준 모델이나 연속 편집의 부모 선택은 아직 연결하지 않았다. 전체 이웃 ID와 형상 해시가 고정 context와 일치해야 시작하고, 진행 결과를 10개마다 원자적으로 기록한다. 완료 시 판정을 포함한 별도 사례를 저장하며 기존 결과·사례를 덮어쓰지 않는다.

[관련 검사 13개 PASS](evidence/registered-context-execution-tests.xml): 사례·부모·주변 입력 연결, 전체 검사 콜백, 다른 입력의 검사 전 거부, 다른 사례 또는 모순된 PASS 기록의 적용 거부를 확인했다. 실제 전체 CLI 측정은 완료됐고 앱 비동기 실행도 연결했다. 전체 브라우저 실행의 완료·재조회 검증은 진행 중이다.

`이 사례에 대응하는 주변 검사 불러오기` 버튼은 로컬에 측정 근거가 등록된 정확한 사례 revision에서만 작동한다. 검사 파일 해시, 전체 이웃 ID·개수 및 context 해시를 대조한 뒤 기존 측정 기록을 사례에 포함한다. 변경 형상이나 다른 revision에는 별도 검사가 필요하다. 이 동작은 새 주변 검사 실행이 아니며 생성 승인 false를 유지한다.

[관련 검사 19개 PASS](evidence/registered-context-workbench-tests.xml), [실제 브라우저 PASS](evidence/registered-context-ui.json): 788개 주변 검사 FAIL 표시, undo/redo, 기록 포함 다운로드 및 Atlas 불변을 확인했다. 내려받은 파일을 Docker에서 독립 재로드하여 직접 기록 연결 결과와 일치하고 표면·그래프가 그대로임을 확인했다. 상태 안내 캡처를 직접 확인했다. 이 사례는 이제 별도 저장 파일에도 주변 FAIL을 포함할 수 있으며, 등록되지 않은 후보의 주변 검사는 여전히 NOT RUN이다.

저장 사례 작업창 `/case-labels`에 굴곡 변위·LPS 방향·끝점 축 회전각·고정 거리·전이 거리·이동 한도 조절을 연결했다. 명시적 단일 edge–source 대응과 면 소유권이 있는 표면에서 별도 후보를 만들고 undo/redo 및 다운로드를 지원한다. 계산 중 파일 교체·입력을 잠그며 실패 시 현재 사례와 이력을 유지한다. 굴곡 변위를 tortuosity 목표값으로, 축 회전을 미분 torsion으로 표시하지 않는다.

[관련 검사 21개 PASS](evidence/shape-workbench-tests.xml). 브라우저와 독립 실행의 정수/실수 입력 차이로 사례 ID가 달라지는 문제를 발견해 수치 입력을 정규화했다. [최초 실패 기록](evidence/registered-shape-ui-numeric-identity-failure.json)을 보존했으며 같은 값의 정수/실수 요청이 동일한 revision을 만드는 검사를 추가했다. [브라우저 실행 기록](evidence/registered-shape-ui.json)의 최종 상태와 범위를 따르며 RUNNING은 통과가 아니다.

정규화 후 브라우저 실행 **PASS**: 실제 접근 사례를 불러와 FJ2074를 선택하고 과도한 변형 거부·원본 보존, 입력 잠금, 0.25 mm 굴곡 후보 생성, undo/redo, 다운로드를 확인했다. 다운로드 전체 문서는 독립 실행 결과와 일치했고 Docker의 독립 재로드에서도 내용과 revision 일치 PASS다. 조절 패널과 변경 표면 캡처를 직접 확인했다. 화면은 Atlas의 서버 상태를 바꾸지 않았다. 이 실행의 twist는 0°이며 실제 모델의 비영 회전 성공 검증으로 확대하지 않는다. 모바일 조절 패널은 별도 검사하지 않았다.

[고정 주변 검사 연결](evidence/registered-shape-context-binding.json): 새 사례와 부모 사례의 정점·삼각형을 기존 굴곡 검사 입력 두 개와 정확히 대조했다. 입력 파일 해시·788개 고유 이웃 ID 집합·context 해시도 일치했다. 기존 접촉 판정 **FAIL**을 해당 사례 revision에 연결하며, 이는 기존 측정의 재사용이고 새로운 788개 검사 실행이 아니다. 사례 파일은 변경하지 않았으므로 앱 일반 후보에는 주변 검사 NOT RUN이 남는다. 이 별도 기록을 생성 승인으로 해석하지 않는다.

`registered_shape_edit.deform_registered_source`는 명시적인 단일 edge–source 대응과 면 소유권이 있는 사례에서 벽과 중심선에 같은 변형을 적용한다. 그래프 노드를 보호점으로 전달하고 다른 edge 좌표를 보존한다. 변경 표면에 연결된 모든 중심선의 내강 포함이 PASS인 경우만 별도 사례로 반환한다. 다중 edge로 분할된 source의 독립 회전 및 기존 병변이 있는 표면은 지원하지 않는다.

부모 형상의 검사·품질·표면 참조는 이력으로 분리하고 새 형상에는 주변 혈관 검사 NOT RUN, 반경–표면 일치 NOT RUN 및 생성 승인 false를 기록한다. 이는 편집 후보 생성 기능이며 전체 모델의 수용이나 대화형 앱 편집 완료가 아니다.

[관련 검사 17개 PASS](evidence/registered-shape-edit-tests.xml): 벽/그래프 동시 변경, 노드·원본 보존, 결정적 사례 해시, 잘못된 대응·과도한 변형 거부, 다른 연결 경로의 미확정 판정 시 거부를 포함한다. [실제 접근 사례 실행](evidence/registered-shape-case.json)은 FJ2074:e0, bend 0.25 mm, twist 0°, collar 1 mm, 전이 10 mm, 최대 이동 1 mm를 고정해 실행한다. RUNNING 기록은 완료나 수용의 증거가 아니다.

실제 실행은 **183.42초에 PASS**로 종료됐다. 변경 표면에 연결된 **65개 경로 모두 내강 포함 PASS**, 노드 및 다른 edge 보존, 별도 사례 저장·재로드 일치를 확인했다. 결과는 `exports/registered-shape-case/case.snapshot.json`, revision `e09458dedd417a1fad89eb9fbc5521a7f7074219ce31ccff88ee797c7ed65c8c`다. 이 새 사례의 주변 혈관 검사는 NOT RUN이며 생성 승인 false다. 기존 별도 굴곡 후보의 접촉 결과를 형상 해시 대조 없이 이 사례의 결과로 재사용하지 않는다.

데모 서버에 `대퇴 굴곡 0.25 mm · 검사 후보` 읽기 전용 선택 항목을 반영했다. 실제 형상·변경 그래프·전체 경로 검사 및 고정 주변 집합의 해시를 대조하며, 다른 source/공유 경계 좌표 변경이나 불완전한 PASS 기록을 거부한다. 반경 편집 경로는 비활성화한다. [관련 검사 10개 PASS](evidence/bend-preview-tests.xml), [브라우저 검사 PASS](evidence/access-bend-ui.json): 후보 선택, 대퇴 source 선택, 읽기 전용 안내, 65개 경로 표시, 표면/중심선 전환 및 Atlas 복원. 캡처를 직접 확인했고 3D 설명에서 NOT RUN을 면 개수처럼 표시하던 문구를 수정했다. 수정 후 [관련 7개 검사 PASS](evidence/bend-preview-ui-tests.xml). 캡처는 software WebGL이며 GPU 성능 검증이 아니다. 주변 검사 상태는 후보 로드 시점의 기록이다.

`union_shape.deform_selected_shape`는 선택 source의 표면과 주어진 중심선에 같은 공간 변형을 적용한다. 다른 source 정점과 경로 끝점 주위에 고정 영역을 두고, 전이 영역에서 변위를 완만하게 증가시킨다. 선택 source의 공유 정점과 다른 source 표면은 정확히 고정한다.

`bend_mm`는 chord에 수직인 방향의 변위이고 `twist_deg`는 끝점 chord 주위 회전각이다. 측정된 tortuosity 또는 미분기하학적 torsion의 목표값이 아니다. 반경을 보존한다고 가정하지 않으며 반경–표면 일치는 NOT RUN이다. 공유 정점 보존 자체가 접합부 접선 연속성의 증명은 아니다.

후보 반환 전 최대 이동량, 삼각형 퇴화/반전, 양의 폐곡면, 자기 접촉, 변경 중심선 전체의 내강 포함을 검사한다. 선택 밖 그래프 경로와 주변 혈관의 검사는 별도로 필요하다. 현재 앱 편집 세션에는 연결하지 않았다.

[합성 검사 10개 PASS](evidence/union-shape-tests.xml): 굴곡·비틀림 조합, 원본/공유부/다른 source 보존, 중심선 끝점 보존과 내강 포함, 0 변형, 입력 및 과도한 이동 거부를 포함한다.

## 실제 대퇴 source의 고정 조건

[실행 결과](evidence/access-shape-edit.json): FJ2074, bend 0.25 mm, LPS X 방향, twist 5°, 고정 영역 1 mm, 전이 10 mm, 최대 이동 1 mm. **FAIL: 최대 이동량 한도 초과**다. 실제 후보를 저장하거나 앱에 반영하지 않았다. 검사 통과를 위해 한도를 늘리거나 파라미터를 자동 조정하지 않았다. 다음 검토는 chord 기준 회전의 실제 변위 분포와 국소 회전축 정의이며, 주변 검사와 통합 그래프 갱신은 아직 NOT RUN이다.

## 이동량 진단

`ShapeEditFailure.measurements`에 표면·중심선 최대 이동량, 최대 위치, 회전축 거리, 선택 정점의 이동량 분위수를 보존한다. [진단 관련 검사 8개 PASS](evidence/union-shape-diagnostics-tests.xml). [최초 실패 기록](evidence/access-shape-edit-initial.json)은 별도 보존했다.

동일 조건 재측정에서 표면 최대 2.821754 mm, 중심선 최대 2.340546 mm였다. 표면 최대 위치는 끝점 chord에서 35.027383 mm 떨어져 있으며 chord 길이는 348.562304 mm다. 이 수치는 긴 곡선 혈관을 전역 chord 주위로 돌릴 때 5°라도 1 mm보다 큰 이동을 만들 수 있음을 보여준다.

효과 분리를 위해 별도 입력으로 검사한다. [twist만 5°](evidence/access-shape-edit-twist.json)는 표면 최대 3.059278 mm, 중심선 최대 2.575592 mm로 같은 1 mm 제한에서 FAIL이다. [bend만 0.25 mm](evidence/access-shape-edit-bend.json)는 별도 실행 중이다. 두 실행은 결합 조건의 실패를 대체하지 않으며 제한을 자동 조정하지 않는다. 현재 twist는 chord 주위 회전이라는 명시적 의미를 유지하고, 국소 단면 회전이나 미분 torsion으로 이름만 바꾸지 않는다.

굴곡 단독 실행은 95.88초에 CANDIDATE로 종료됐다. 최대 이동 0.25 mm, 다른 source 정점 및 경로 끝점 보존, 자기 접촉 미검출과 선택 중심선 1,427개 선분 포함 PASS다. 전체 그래프·주변 혈관 검사와 반경–표면 일치 검사는 별개이며 이 결과로 앱 적용을 허용하지 않는다.

`protected_points_mm`로 그래프 중간 접합점에도 동일한 고정 공간 영역을 적용할 수 있다. [관련 15개 검사 PASS](evidence/union-shape-graph-anchors-tests.xml)는 내부 접합점 정확한 보존과 잘못된 보호 좌표 거부를 포함한다. 보호점 주변의 접선·곡률 연속성을 증명하지는 않는다.

[전체 그래프 검사](evidence/access-bend-graph.json)는 변경된 FJ2074 단일 경로와 원본 그래프의 정확한 대응·끝점 보존을 확인한 뒤 해당 edge만 estimated/synthetic_estimate로 표시하고 65개 전체 경로를 변경 표면에서 검사한다. 다른 edge와 노드 좌표는 보존한다. 원본 반경은 다시 측정하지 않았으므로 반경–표면 일치는 NOT RUN이다. RUNNING 기록은 전체 통과를 뜻하지 않는다.

전체 그래프 검사는 **65/65 PASS**로 종료됐다. [주변 접촉 비교](evidence/access-bend-context.json)는 고정된 788개 표면 전부를 887.09초에 검사했고 **FAIL**이다. 접촉 이웃 80개와 미확정 11개가 남았다. [접촉 위치 기록](evidence/access-bend-contact-locations.json)에서 FJ2069, FJ2086, FJ2099, FJ2102, FJ3484의 삼각형 접촉 쌍이 추가·제거됐다. 모두 변경 전부터 SURFACE_CONTACT였으므로 새로 접촉한 혈관 5개라는 뜻은 아니다. 정상 분지와 비접합 관통의 해부학적 분류는 미확인이다. 후보는 읽기 전용이며 적용·생성 승인을 부여하지 않는다.

미리보기의 주변 검사 연결은 해시·개수 외에 실제 이웃 ID 집합도 대조한다. 진행 중 결과는 기준 집합의 부분집합이어야 하고, 종료 결과는 전체 집합과 일치해야 한다. 같은 해시와 개수에 다른 혈관 행을 끼운 진행 중/종료 기록을 거부한다. [관련 검사 7개 PASS](evidence/bend-preview-neighbor-binding-tests.xml).

## 입력량과 측정량

[중심선 측정](evidence/access-bend-path-metrics.json): 원본 길이 361.624670 mm → 변경 361.591454 mm, 끝점 거리 348.562304 mm 유지, 길이/끝점 거리 비율 1.037474982 → 1.037379687이다. 양의 bend 변위가 이 사례에서 길이 기반 굴곡도를 증가시키지는 않았다. 따라서 bend_mm를 tortuosity 목표값으로 표시하지 않는다. 표본 정점의 최대 방향 전환은 22.642672° → 22.588153°이며 표본 밀도에 의존한다. 미분 곡률·torsion 또는 임상 범위 판정은 아니다. [측정 함수 검사 5개 PASS](evidence/path-metrics-tests.xml)는 알려진 경로, 강체 변환, 폐경로의 비율 미정의 및 잘못된 입력을 포함한다.

[단면 측정](evidence/access-bend-sections.json)은 원본 호길이를 기준으로 33개 대응 위치를 정하고, 양 끝을 제외한 31개에서 각각 변경 전후 중심선의 국소 수직 평면을 사용했다. 모두 MEASURED이며 면적 환산 반경 비율은 **0.997243768–1.000025798**이다. 미세한 단면 크기 변화가 있으므로 정확한 반경 보존이라고 표시하지 않는다. 표면/그래프 해시를 대조했고, 끝점과 단면 사이 연속 구간 전체의 보존 판정은 NOT RUN이다. `exports/access-shape-edit-bend/section-comparison.png`에서 두 곡선과 비율 축을 직접 확인했다. 이는 샘플 단면 측정 그림이며 합격 허용오차나 임상 범위를 나타내지 않는다.
