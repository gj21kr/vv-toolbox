# 사례에 등록된 원본·파생 표면 출력

기존 사례 표면 생성은 중심선과 반경 프로파일에서 합성 튜브를 재구성한다. Atlas의 비원형 단면과 구간 편집 표면을 보존하기 위해 `surface_parts` 선택 필드를 추가했다.

각 표면은 part ID, 명시적 edge ID 목록, 좌표계, 출처 ID, source/estimated 구분, 정점·삼각형 및 형상 hash를 갖는다. 연결된 중심선·반경의 hash도 저장하여 경로 변경 후 이전 표면이 조용히 재사용되지 않도록 한다. 파생 표면은 source 사례로 표시할 수 없다.

`build_case_surface`는 등록 표면이 있는 사례에서 정점·삼각형을 그대로 출력한다. 여러 표면은 인덱스 오프셋만 조정해 결합하며, 용접·표면 합집합·분기점 보충을 수행하지 않는다. 등록된 다중 edge 표면의 일부 edge만 선택하면 명시적인 구간 표면 경계를 요구한다. 병변·접합부 변경은 별도의 표면 반영 없이 적용한 것으로 취급하지 않는다.

[Docker 검사](evidence/case-source-surfaces-tests.xml): 31개 PASS, 외부 라이브러리 deprecation warning 52개. 비원형 합성 fixture의 사례 저장/로드 후 좌표·삼각형 완전 일치, 형상/중심선/반경 변경 탐지, 부분 선택 거부, 출처 구분 및 기존 합성 표면 회귀를 확인했다.

## 등록 표면의 마스크

`build_case_masks`는 등록 표면이 있는 사례에서 실제 삼각형을 직접 voxelize한다. 전달된 출력 표면과 등록 표면의 정확한 일치, 좌표계, 전체 grid 범위를 확인한다. 반경으로 원형 튜브를 다시 만들지 않는다.

원본(source)·합성(estimated) 출처와 겹침 위치의 각 표면 membership을 보존한다. 인스턴스는 등록된 표면 part 단위다. 여러 edge가 한 part를 공유하면 이를 명시적으로 기록하며, 서로 다른 유효 구간 라벨을 가진 edge가 한 표면에 있으면 실제 분할을 요구한다. 근거가 없는 해부 구간은 0(unknown)이다.

병변이 선언되지 않은 경우 병변 마스크는 0이며 이는 질환 부재의 증거가 아니다. 등록 표면에 대한 병변/ROI 반영은 아직 지원하지 않는다. 빈 병변 라벨 배열의 메모리도 총 예산에서 예약한다.

[마스크 Docker 검사](evidence/case-source-masks-tests.xml): 31개 PASS, 외부 라이브러리 deprecation warning 51개. 비원형 표면 밖·원형 반경 안 위치의 배경 판정, 원본/합성 겹침 출처와 membership 보존, 다중 edge 단일 part, 서로 다른 구간 라벨의 분할 요구, 미등록 형상 거부 및 메모리 한도를 검사했다.

## 현재 Atlas 사례 캡처

`prepare_current`는 현재 중심선과 대응하는 동맥 표면을 사례에 등록한다. 화면의 **현재 동맥 표면·편집으로 사례 준비** 버튼을 연결했다. 장면 generation이 오래되었거나 구간 계산 중이면 캡처하지 않는다. 구간 편집 기록과 전체 혈관 파라미터 편집을 생성 조건에 보존하며 수정 표면은 estimated로 표시한다.

원본 경로와 파생 표면이 공존할 수 있다. 수정 부분의 반경 필드에는 현재 표면 실측치가 아니라는 상태를 남긴다. 대응 경로가 없는 동맥 및 캡처 범위 밖 편집은 명시적인 목록으로 기록한다. 사례 저장/재로드는 3D 장면을 바꾸지 않는다.

[캡처 회귀](evidence/atlas-case-surface-capture-tests.xml): 25개 PASS. 합성 fixture의 정확한 표면 보존, 구간 기록·출처 보존, 저장 후 동일한 사례 복원, 누락 part 기록, 실패 시 기존 사례 유지와 표면/마스크 회귀를 확인했다.

## 실제 Atlas 캡처 검증

데모 서버 반영 후 [브라우저 캡처·다운로드](evidence/atlas-case-capture-ui.json) PASS. 원본 동맥 표면 517개, 중심선 경로 1,081개를 현재 사례 파일로 내려받았다. 원본 Atlas 편집 저장 파일과 기존 사례 저장 파일의 hash, 장면 generation이 유지됐다. 검사 후 새 사례는 메모리에 남아 있으며 기존 디스크 사례 파일을 덮어쓰지 않았다.

[전체 캡처 표면 대조](evidence/atlas-case-capture-geometry.json) PASS. 내려받은 517개 표면의 정점 433,267개와 삼각형 774,984개를 원본 Atlas와 전수 비교하여 정확한 배열 일치를 확인했다. 원본 동맥 518개 중 `FJ3553`은 경로 대응이 없어 제외됐으며 누락 목록에 기록됐다. 별도 추정 경부 연결 4개도 현재 캡처에 포함되지 않는다.

- 브라우저 실행: `node scripts/verify_atlas_case_capture_ui.cjs`
- 원본 대조(Docker): `python scripts/inspect_atlas_case_capture.py`
- 파일: `exports/atlas-case-capture-ui/case.snapshot.json`
- 화면: `exports/atlas-case-capture-ui/captured.png`

위 브라우저 캡처는 미수정 Atlas로 확인했다. 수정된 실제 Atlas 캡처, 전체 Atlas 마스크 실행, 다중 edge 표면의 구간별 마스크 분할과 전체 라벨 연결은 미완료다. 추정 연결 포함은 아래 후속 기록을 따른다. 전체 Viser 장면의 시각 검사는 NOT RUN이며 작업 패널은 확인했다. 폐곡면·충돌·해부학적 검증을 등록/hash 검사로 대체하지 않는다.

## 추정 경부 연결의 사례 포함

현재 표면 캡처는 `AUTHORED_ESTIMATE`로 등록된 동맥 중심선도 명시적인 출처 기록이 있으면 포함한다. 원본 경로 전용 `prepare` 동작은 그대로 유지한다. 추정 중심선·노드·표면은 합성 출처이며, 기존 endpoint ID를 그대로 유지해 근접한 원본 endpoint와 자동으로 연결하지 않는다. 원본 좌표계와 출처 metadata, 열린 표시용 표면 및 내강 합집합 미검증 한계를 사례에 보존한다.

[회귀 검사](evidence/atlas-case-estimate-tests.xml): 27개 PASS. 추정 형상 포함, 별도 노드 보존, 출처와 한계 기록, 저장/재로드를 확인했다.

[실제 자료 서비스 실행](evidence/atlas-case-estimate-capture.json): 현재 그래프와 고정된 Atlas 원본에서 캡처하여 표면 521개·경로 1,085개를 확인했다. 좌우 carotid/vertebral 경부 연결 4개가 estimated로 포함되고 모든 원본·추정 표면 배열이 보존됐다. 남은 원본 표면 누락은 `FJ3553`이다. 실제 화면의 작업 상태·저장 파일은 변경하지 않았다.

- 실행(Docker): `python scripts/inspect_atlas_case_estimates.py`
- 추정 연결을 포함한 최신 서버 재시작·브라우저 검증: [PASS](evidence/atlas-case-estimates-ui.json). 원본 517개와 추정 4개를 구분하여 521개 표면을 내려받았으며 원본 저장 파일과 장면 generation을 보존했다. 화면에 추정 형상 포함·해부 연결 미검증을 표시한다.
- 추정 연결의 내강 합집합·해부학적 연결 수용: NOT RUN

이 캡처는 Atlas의 전체 동맥 자료를 보존하므로 v1 접근 경로 밖 vertebral 표시용 연결도 포함한다. 개발계획의 v1 경로 범위가 확장됐음을 뜻하지 않는다.

## 전체 마스크 사전 점검

[521개 표면 전수 점검](evidence/atlas-mask-readiness.json): 현재 voxelizer의 폐곡면·방향·양의 체적·비퇴화 조건을 원래 인덱스 그대로 만족하는 표면은 61개다. 좌표가 정확히 같은 정점의 인덱스만 통합하면 원본 517개가 조건을 만족한다. 이 작업은 삼각형 좌표를 이동하거나 면을 추가·제거하지 않는다. 추정 경부 연결 4개는 여전히 열린 표시용 표면이므로 그대로 체적 마스크로 승인할 수 없다. 자기 교차 검사는 이 사전 점검에 포함하지 않았다.

고정된 1 mm 공학적 grid probe(권장 임상 해상도 아님)는 652×242×1,704이다. 현재 모든 part membership을 조밀 배열로 유지하는 구현의 메모리 상한 추정은 148,337,832,032 bytes로 기본 256 MiB를 초과한다. 이 제한을 완화해 강행하지 않았으며 전체 마스크 실행은 NOT RUN이다. 전체 출력에는 좌표 보존 인덱스 정규화, 추정 연결의 별도 체적 구성, 공간별 분할 처리·희소 membership 저장이 필요하다.

- 브라우저 재현: `node scripts/verify_atlas_case_capture_ui.cjs --estimates`
- 캡처 파일: `exports/atlas-case-estimates-ui/case.snapshot.json`
- 표면·메모리 사전 점검(Docker): `python scripts/inspect_atlas_mask_readiness.py`
