# 접근 후보의 표면·그래프 사례 저장

## 굴곡 후보 다운로드

등록 표면이 있는 사례의 중심선 평활화를 지원한다. 표면 정점·면을 고정한 채 수정 경로 전체의 내강 포함이 PASS인 경우에만 경로 연결 해시를 갱신한다. 검사 미확정/실패 시 원본 사례를 유지한다. 기존 검사 기록은 부모 이력으로 보존하며 새 중심선 검사에 생성 승인 false를 기록한다. 반경–표면 일치와 해부학적 수용은 별도다.

[관련 검사 31개 PASS](evidence/registered-centerline-edit-tests.xml). [실제 고정 조건 실행](evidence/saved-bend-smoothing.json): FJ2074:e0, 평활 폭 0.5 mm, 이동 한도 0.3 mm에서 최대 이동 0.068767 mm, 길이 361.591454→360.604316 mm였다. 표면·노드·다른 64개 경로·부모 접촉 FAIL 기록을 보존하고 저장/재로드했다. [브라우저 검사 PASS](evidence/saved-bend-smoothing-ui.json): 수정, undo/redo, 변경 사례 다운로드 및 Atlas 불변을 확인했다. 브라우저 다운로드와 독립 실행 결과를 Docker에서 다시 읽어 사례 및 revision이 정확히 같은 것을 확인했다. 중심선 중첩 캡처를 직접 확인했으며 혈관 벽 굴곡·반경 편집의 완료를 뜻하지 않는다.

저장 사례 작업창의 등록 표면 표시를 추가했다. 원본 삼각형 좌표를 WebGL 깊이 버퍼로 그리며, 중심선과 같은 회전·확대·초점 좌표를 사용한다. 표면/중심선을 각각 켜고 끌 수 있고 중심선은 표면 위에 겹쳐 표시한다. 가려진 중심선이 앞에 보일 수 있음을 안내한다. 등록 표면이 없으면 중심선만 표시하고 WebGL 실패 시 표면 표시 불가를 명시한다. 다시 불러올 때 이전 그래픽 자원을 해제한다.

[관련 검사 15개 PASS](evidence/registered-surface-preview-tests.xml)는 투영·선택, 표면을 포함한 화면 범위, WebGL 부재 표시 및 숨긴 중심선의 선택 방지를 포함한다. [실제 저장 굴곡 사례 UI 검사](evidence/saved-bend-surface-ui.json)는 50,188개 삼각형, 비어 있지 않은 렌더링, 회전, 두 표시 토글, 문서 왕복 및 Atlas 불변을 확인했다. 대퇴 표면·회전·중심선 중첩 캡처를 직접 확인했다. 화면은 저장 형상의 표시이며 접촉 FAIL이나 미확인 해부학 상태를 해소하지 않는다. software WebGL 검사로 GPU 성능을 주장하지 않는다.

`/case-labels` 저장 사례 작업창에서 굴곡 다운로드 파일을 다시 불러와 중심선 65개와 양 끝 관계를 확인할 수 있다. 저장 당시 주변 검사 FAIL과 생성 미승인을 표시하고, 현재 편집에 대한 재검사 결과와 구분한다. 변경하지 않은 사례도 다운로드할 수 있도록 했다. 등록 표면은 파일 안에 보존되며 이 작업창 화면은 중심선만 그린다.

[관련 검사 20개 PASS](evidence/saved-candidate-workbench-tests.xml), [실제 굴곡 파일 왕복 PASS](evidence/saved-bend-workbench-ui.json): FJ2074 검색, 검사 상태 표시, 변경 없는 다운로드의 문서 전체 일치 및 Atlas generation 보존을 확인했다. Docker에서 두 다운로드 파일을 독립적으로 로드하여 사례 내용과 revision 일치도 확인했다. 직렬화 공백 차이 때문에 파일 바이트 해시는 다르다. 데스크톱 중심선 및 390px 화면의 안내 캡처를 직접 확인했다. 이 실행은 라벨 변경·형상 편집이나 표면 3D 재표시의 완료 증거가 아니다.

읽기 전용 굴곡 후보에서도 `현재 형상·그래프 저장 (검사용)`을 사용할 수 있다. 저장 영역은 반경 편집 가능 여부와 독립적으로 표시한다. 서버는 굴곡 후보의 변경 그래프를 로드하고 표시 중 revision·edge 및 형상 해시와 일치하는지 검사한다. 주변 검사 788개 전체 기록과 FAIL, 반경–표면 일치 NOT RUN, 생성 승인 false를 보존한다.

[관련 검사 13개 PASS](evidence/bend-case-export-tests.xml). [실제 브라우저 다운로드 PASS](evidence/bend-case-download-ui.json): 버튼 표시, 오래된 generation의 HTTP 409 거부, 반경 편집 숨김, 변경 그래프 revision, 전체 검사 기록, Atlas 복원을 확인했다. 저장 영역 캡처에서 문구와 줄바꿈을 직접 확인했다. Browser plugin이 없어 로컬 Playwright를 사용했으며 모바일 레이아웃은 별도 검사하지 않았다.

[다운로드 파일 독립 재로드 PASS](evidence/bend-case-reload.json): 25,094정점·50,188면을 후보 NPZ와 정확히 대조하고, 65개 edge 및 노드를 변경 그래프와 대조했다. 주변 검사 기록도 전체 원본 JSON과 일치한다. 파일은 `exports/bend-case-download/case.snapshot.json`이다. 사례를 다시 앱에 불러와 편집하는 흐름이나 형상·해부학적 수용을 승인하는 결과는 아니다. 기존 접근 후보의 [다운로드 회귀 검사](evidence/candidate-case-download-ui.json)도 PASS이며 검사 후 Atlas로 복원했다.

목 내부 메시 개선 후보의 실제 표면과 접근 그래프를 하나의 사례 snapshot으로 저장한다. 기존 그래프 파일의 외부 표면 참조만으로 형상을 다시 생성하지 않는다. 원본 case와 그래프는 보존하며, 통합 표면은 estimated 출처의 synthetic 사례로 등록한다.

실행: Docker에서 `PYTHONPATH=src python scripts/export_access_candidate_case.py`.

[실행 기록](evidence/access-candidate-case.json): 저장→재로드→등록 표면 출력 PASS. 정점 25,094개, 면 50,188개, 노드 65개, edge 65개를 포함한다. 입력과 출력의 정점·면 배열이 정확히 일치하며 전체 그래프와 근거 상태, 면별 source 소유권을 보존했다. 기존 파일이 다른 revision이면 자동 덮어쓰기를 거부한다.

산출물은 `exports/access-candidate-case/case.snapshot.json`이며 실행 기록에 사례 revision, 원본 그래프 revision, 표면 artifact 해시를 기록한다. 기존의 사례 저장/로드와 등록 표면 출력 기능을 사용한다.

이 결과는 수정하지 않은 개선 후보의 저장·출력 검사다. 반경 확대 후 주변 검사에 실패한 형상을 승인한 결과가 아니다. 해부 구간과 접합 수용은 UNKNOWN, 반경·표면 일치와 구간별 마스크는 NOT RUN이며 `accepted_for_generation=false`다. source 소유권은 검토된 ACA/MCA 구간 라벨을 대신하지 않는다. 앱의 원본 후보·반경 수정 후보 다운로드 검증과 미승인 사례의 일괄 생성 거부 결과는 아래에 기록한다.

## 표시 후보의 검사 사례 다운로드

`candidate_case` 변환기는 현재 표시 표면과 원본 접근 그래프를 하나의 검사 사례로 구성한다. 반경 수정 표면은 실제 정점·면 해시를 검증하며 원본 중심선·반경을 유지한다. 원본 그래프 반경은 수정 표면에서 다시 측정한 값이 아님을 명시하고 반경–표면 일치는 NOT RUN으로 저장한다. 실패·미확인 summary와 context를 보존하며 `accepted_for_generation=false`를 유지한다.

앱에 `/api/candidate-case-snapshot`과 “현재 형상·그래프 저장 (검사용)” 버튼을 추가했다. 계산 중 요청과 오래된 generation을 거부한다. [관련 검사 13개 PASS](evidence/candidate-case-download-tests.xml), [실제 기본 후보의 저장/재로드/표면 출력 PASS](evidence/access-inspection-case.json). 실제 표면 50,188면과 그래프 65edge가 보존됐다. 기존 반경 편집 recipe 저장과 별개의 검사 사례 출력이다.

[실제 브라우저 다운로드 PASS](evidence/candidate-case-download-ui.json): 개선 후보 선택→버튼 다운로드→사례 재로드→표면·그래프 정확한 일치 확인→Atlas 복원. 오래된 generation은 HTTP 409이며 다운로드는 장면 generation을 변경하지 않는다. 검사 사례 비승인 안내와 버튼을 화면에서 직접 확인했다. 반경 변경 상태에서의 실제 다운로드는 아직 NOT RUN이며 변환기 단위 검사에서만 변경 표면 보존을 확인했다. UI 안내 수정 후 [관련 7개 검사 PASS](evidence/candidate-case-ui-tests.xml).

반경 변경 상태의 후속 다운로드 검증은 `verify_access_radius_roundtrip.cjs --download-case`로 실행한다. [현재 실행](evidence/access-radius-case-download.json)은 원래 1.05/10/1 조건과 65개 중심선·788개 주변 검사 범위를 유지한다. 실제 서버의 계산 중 상태를 확인한 뒤 버전 헤더를 포함한 다운로드 요청이 HTTP 400으로 거부됨을 확인했다. 완료 후 표시 형상 해시·전체 radius audit와 다운로드 사례를 비교하고, 기존 적용 차단·취소·Atlas 복원도 수행한다. RUNNING은 아직 완료가 아니다.

첫 시도는 UI의 낙관적 대기 표시를 서버 계산 상태로 간주하고 버전 헤더 없이 요청해 HTTP 409를 받아 테스트가 실패했다. [실패 기록](evidence/access-radius-case-download-busy-status-mismatch.json)을 별도로 보존했다. 서버가 idle Atlas로 복원됐음을 확인한 후 실제 계산 상태를 기다리도록 테스트를 수정해 새 실행을 시작했다. 이 실패를 계산 중 요청 차단 PASS로 집계하지 않는다.

[실제 변경 형상의 독립 저장/재로드 PASS](evidence/edited-access-inspection.json): 이전에 계산·저장된 FJ2074 1.05배 후보를 완료된 브라우저 audit의 geometry hash와 대조하고 검사 사례로 저장했다. 다시 읽은 정점·면·그래프와 전체 radius audit가 정확히 일치했다. 주변 FAIL 및 `accepted_for_generation=false`를 보존했다. 이는 실행 중인 새 브라우저 다운로드 검증과 별개의 저장 파일 검사이며 실시간 다운로드 완료를 대신하지 않는다.

일괄 생성기는 `inspection` 안에 명시된 `accepted_for_generation`이 정확한 boolean true가 아니면 검사 사례를 입력 단계에서 거부한다. false·null·숫자·문자열을 승인으로 해석하지 않는다. true는 기존 형상·병변 검사를 우회하지 않는다. 이 필드가 없는 기존 사례에 해부학적 승인을 새로 부여하는 규칙도 아니다. [관련 25개 검사 PASS](evidence/inspection-batch-gate-tests.xml), [실제 실패 후보의 일괄 생성 거부 PASS](evidence/actual-inspection-batch-rejection.json): 결과 폴더를 만들기 전에 거부됐다.

반경 변경 상태의 [실제 다운로드 실행](evidence/access-radius-case-download.json)은 **PASS, 1,077.783초**로 종료됐다. 65개 중심선 및 788개 주변 검사 후 다운로드한 사례를 별도로 재로드하고 실제 표면 해시·원본 그래프·전체 radius audit의 정확한 일치를 확인했다. 주변 FAIL, 생성 미승인, 적용 차단을 보존하고 취소 후 Atlas로 복원했다. `exports/access-radius-case-download/controls.png`에서 적용 차단과 검사용 저장 버튼·비승인 안내를 직접 확인했다. 이 실행은 저장 기능 검증 PASS이며 실패 형상의 수용 승인이 아니다.

### ROI 생성 및 검증

등록 표면에 `coverage='roi'`를 지정하면 전체 폐곡면을 그대로 사용하면서 지정 격자 영역의 voxel만 계산한다. 기본 `whole`은 계속 전체 표면 범위를 덮는 격자를 요구한다. ROI 출력은 source bounds와 sampled bounds를 별도로 기록하고 전체 범위 충족을 NOT APPLICABLE로 표시한다. 미물질화 병변 및 서로 다른 구간 라벨의 임의 표면 분할은 허용하지 않는다.

[관련 검사 25개 PASS](evidence/registered-roi-mask-tests.xml): 동일 격자에 맞춘 전체 출력의 crop과 ROI의 foreground·해부·instance·출처·겹침·membership 배열 일치, affine 원점 보존 및 불완전 whole 격자 거부를 포함한다.

실제 후보의 FJ2074 중심선 중간 호길이에 33×33×33, 0.5 mm ROI를 고정했다. [실행 기록](evidence/access-roi-mask.json): **PASS**, 269.62초. 35,937개 voxel 중 혈관 내부는 11,691개이며, 직접 winding 판정과 별도 ray containment의 voxel별 차이는 0개다. 파일 저장/로드와 affine 중심 좌표 검사도 PASS다. 이는 전체 모델 마스크나 ACA/MCA 구간 마스크 완료를 뜻하지 않는다. 해부 구간은 미확인 라벨 0, 혈관 내부 출처는 estimated로 보존한다.

## Winding 계산 묶음 검증

공통 `volume_io.load_volume`은 NPZ 재로드 시 좌표계·affine·배열 크기/자료형을 검사하고, 전체 membership에서 소유 instance·해부 라벨 충돌·출처·겹침 수·foreground를 재계산해 저장값과 대조한다. 병변 배열의 정렬과 혈관 밖 라벨도 검사한다. 원본 형상이나 병변 생성 규칙의 재검증은 아니다. 압축 해제 payload 한도를 적용하며 이 한도는 프로세스 RSS 한도가 아니다. [관련 검사 11개 PASS](evidence/volume-archive-reader-tests.xml), [실제 대퇴 ROI 재로드 PASS](evidence/access-roi-archive-reader.json).

일괄 생성 사례 묶음은 `python -m vv_toolbox.case_artifacts <case-folder> --expected-sha256 <batch-report-digest> --validate-masks`로 검사한다. 외부 기록의 manifest 해시와 모든 파일 바이트를 확인한 뒤, 전체 마스크 및 병변 ROI를 읽어 좌표·라벨 일관성과 사례 revision을 확인한다. 기본 명령의 파일 무결성 검사와 구분된다. [재로드·배치 검사 25개 PASS](evidence/bundle-mask-reload-tests.xml): 합성 병변 사례의 전체 마스크와 고해상도 ROI 재로드를 포함한다. 71개 경고는 skimage/NumPy deprecation이며 실제 해부학 검증은 검사 범위 밖이다.

사례 연결 보강 후 [30개 PASS](evidence/bundle-mask-case-binding-tests.xml): case frame과 mask frame, 병변 metadata의 grid, 병변 ID→edge 대응, 중복/미등록 라벨 및 병변별 voxel 수를 대조한다. 다른 frame, 어긋난 병변 grid, 미등록 라벨, 잘못된 voxel 수, 다른 edge를 넣고 파일 manifest를 다시 생성한 5개 fixture는 파일 무결성 검사에는 통과하지만 의미적 마스크 검사에서 모두 거부됐다. 이 결과는 해시 일치와 사례 일치가 별개임을 검증한다. 76개 경고는 skimage/NumPy deprecation이다.

저장된 NPZ에서 세 방향 중심 단면을 생성했다: `exports/access-candidate-roi/orthogonal-slices.png`. [출력 검사 기록](evidence/access-roi-mask-visual.json)은 원본 해시, LPS affine, 미확인 해부 라벨, estimated 출처, instance 및 membership 일치를 확인한다. 병변 라벨 0은 이 사례에 병변이 선언되지 않았음을 뜻한다. 그림은 보간하지 않은 voxel 표시이며 해부학적 승인 자료가 아니다.

삼각형 처리 묶음을 32개에서 128개로 늘리되, 각 32개 단위의 합산 순서를 유지한다. [관련 검사 31개 PASS](evidence/winding-batching-tests.xml)는 경계·내부·외부의 판정 일치와 기존 8 MiB 임시 계산 메모리 한도를 포함한다.

[실제 후보 비교](evidence/winding-batching-benchmark.json)는 전체 50,188개 면을 유지하고 위 ROI의 매 4번째 voxel 중심 729개를 고정해 수행했다. 두 방식 모두 완료된 ROI와 판정 차이 0개다. 32개 묶음 5.361초, 128개 묶음 4.534초였다. 동시 작업이 있는 환경의 단일 비교이며 전체 마스크의 속도 향상이나 전체 voxel의 두 구현 동등성을 입증하지 않는다. 이미 실행 중인 전체 Atlas 마스크 작업은 재시작하지 않는다.

후속 [전체 ROI 비교](evidence/winding-batching-full-roi.json)는 같은 50,188개 면과 ROI 전체 35,937개 voxel 중심을 사용했다. 32개/128개 묶음 모두 저장된 기준 ROI와 판정 차이 **0개, PASS**다. 실행 시간은 각각 252.270초/229.645초였다. 이 결과의 동등성 범위는 지정된 ROI 전체이며 다른 부위나 전신 전체에 대한 증명은 아니다. 동시 작업 중 단일 측정이므로 일반적인 성능 향상 수치로 사용하지 않는다.
