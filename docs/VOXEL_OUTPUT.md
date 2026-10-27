# 표면 기반 3D 마스크 출력

대상: VV-REQ-011/012 · 구현: `src/vv_toolbox/voxel_output.py`

## 입력과 좌표

`voxelize(surfaces, grid)`는 명시적인 닫힌 삼각형 표면을 voxel 중심에서 표본화한다. 중심선으로 튜브를 만들거나 원본 표면을 추정하지 않는다. `Surface`에는 고유 양의 uint32 instance ID, 해부학 라벨(0=미확인), source/estimated 출처, vertices_mm, faces, frame_id, source_ref가 필요하다. 해부학 라벨과 출처 판정은 입력 제공자의 책임이며 함수가 검증된 해부 정답으로 승격하지 않는다.

`Grid(shape_zyx, spacing_xyz_mm, origin_xyz_mm, frame_id)`는 mm/LPS 좌표계의 축 정렬 격자다. origin은 첫 voxel의 **중심**이다. 배열 순서는 `[z,y,x]`, affine 입력은 `[x_index,y_index,z_index,1]`이다. 임의 회전 격자는 현재 지원하지 않는다. 입력 표면과 격자의 frame_id가 다르면 거부한다.

메시의 watertight, winding consistency, 양의 부피, 비퇴화 삼각형을 검사하며 자동 복구하지 않는다. **자기 교차 검사는 NOT RUN**이다. 이 검사는 표면의 임상적 타당성이나 원본 내강 연결을 입증하지 않는다. 여러 독립 instance 사이의 겹침은 입력을 거부하지 않고 별도 보존한다. 자기 교차가 의심되는 단일 표면은 사전 기하 검토가 필요하다.

## 출력과 겹침

`MaskVolume`은 다음 배열 및 `metadata()`를 제공한다.

| 배열 | dtype | 의미 |
|---|---|---|
| foreground | bool | 모든 표면 내부의 합집합 |
| anatomical | uint32 | 해부학 라벨, 미확인 또는 서로 다른 라벨 충돌은 0 |
| instance | uint32 | 겹침에서 가장 작은 ID를 갖는 대표 instance |
| provenance | uint8 | 0 배경, 1 원본, 2 추정, 3 혼합 |
| overlap_count | uint32 | voxel을 포함하는 instance 개수 |
| membership | bool | `[instance,z,y,x]`의 전체 소속, 겹침을 제거하지 않음 |

membership의 첫 축은 정렬된 `instances` 목록과 대응한다. representative instance 선택은 해부학적 분기 소속 판정이 아니라 고정된 출력 규칙이다. unknown 라벨의 혈관은 foreground로 배경과 구분된다. 병변 라벨/병변 마스크는 아직 이 모듈의 입력·출력에 포함하지 않는다.

## 파일 출력

`python -m vv_toolbox.volume_cli MANIFEST.json OUTPUT.npz` 또는 설치된 `vv-volume` 명령으로 출력한다. manifest schema는 `vv-toolbox.surface-mask-input/1`이며 `grid`는 Grid 필드, `surfaces`는 Surface 필드 목록이다. 정점과 삼각형 인덱스는 JSON 배열로 명시한다. `--crop Z0 Y0 X0 Z1 Y1 X1`은 상한 제외 정수 영역을 출력한다.

NPZ에는 위 여섯 배열과 JSON 문자열 `metadata`가 들어간다. `numpy.load(..., allow_pickle=False)`로 읽을 수 있다. 임시 파일 작성 후 같은 디렉터리의 hard link로 완성 파일을 게시하며 기존 파일은 덮어쓰지 않는다. 해당 파일 시스템에서 hard link가 지원되지 않으면 명시적 오류로 종료한다. exporter는 혈관 표면·주석을 자동 생성하지 않는다.

2026-10-20 CLI 검사: 합성 box 입력→voxelization→crop→NPZ 재로드에서 foreground/unknown anatomy/instance/provenance/affine 일치 PASS, 기존 출력 보존 PASS.

실제 원자료 추가 점검: 대동맥궁 FJ3411은 원본 그대로 381 vertices/670 triangles, watertight=False, winding_consistent=True, is_volume=False였다. 현재 마스크 입력 조건을 만족하지 않는다. 이 입력을 자동 봉합하거나 원본 마스크 출력 성공으로 표시하지 않는다. 닫힌 파생 표면 생성은 별도 합성/파생 처리 단계가 필요하다.

## 표본화와 자원 제한

닫힌 삼각형 표면의 generalized winding number를 사용한다. 기본 표면 허용오차는 1e-8 mm이며 metadata에 저장한다. 삼각형 면·변·꼭짓점 위 voxel 중심을 foreground에 포함한다. 이는 voxel과 표면의 교차율이나 anti-aliasing을 계산하는 방식이 아니므로 작은 혈관은 낮은 해상도에서 사라질 수 있다.

voxel 128개 × 삼각형 32개 단위로 계산하여 전체 voxel–triangle 행렬을 만들지 않는다. 계산량은 O(voxel 수 × 삼각형 수)로, 현재 구현은 제한된 ROI의 정확성 검사와 출력에 적합하다. 대규모 전신 고해상도 출력에는 공간 가속이 필요하다.

기본 max_bytes는 256 MiB다. 출력·임시 배열, 삼각형 복사와 메시 검사 배열의 보수적 추정치에 8 MiB 작업 공간을 더해 사전 거부한다. caller-owned 입력과 Python/라이브러리 자체 메모리는 제외하므로 프로세스 RSS 상한 보장은 아니다. 모든 membership을 보존하므로 instance가 많으면 상한에 빨리 도달할 수 있다. 이 경우 정보를 버리는 대신 명시적으로 실패한다.

## 전체 볼륨과 crop

`crop(volume, start_zyx, stop_zyx, max_bytes=...)`는 반열린 정수 범위의 동일 해상도 배열을 복사한다. crop origin은 원본 affine으로 start index를 변환하여 계산한다. 원본과 crop의 동일 voxel은 같은 물리 좌표를 가진다. 고해상도 ROI는 동일 frame_id에 더 작은 spacing을 설정한 Grid로 원래 표면을 다시 voxelize한다. 낮은 해상도 마스크를 확대해 고해상도 정답으로 표시하지 않는다.

이 모듈 자체는 파일 저장이나 앱 연결을 수행하지 않는다. 저장 계층은 배열 및 metadata를 함께 보관해야 한다.

## 검증

Docker `vv-annotation-ui`에서 `PYTHONPATH=src pytest -q -p no:cacheprovider tests/test_voxel_output.py` 실행. 11개 테스트 통과: 상자 경계 포함, 구·원통의 해석적 내부/외부와 비교, 겹침 소속 보존·입력 순서 독립성, unknown foreground, 비등방성 crop affine 및 고해상도 좌표 일치, open/inverted/degenerate/invalid-index/NaN 메시 거부, 메모리·좌표계·ID 검사.

검증은 합성 도형에 대한 수치/소프트웨어 검사다. 실제 Atlas 전체 마스크 출력, 자기 교차 판정, 분기 표면 분할 및 임상 검증은 포함하지 않는다.
