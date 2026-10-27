# 합성 사례 표면 생성

`case_surface.build_case_surface`는 명시적인 synthetic 사례의 선택 edge들을 반경 프로파일 기반 implicit union 표면으로 만든다. 원본 Atlas 표면의 복원이라고 표시하지 않는다. 모든 입력 edge ID, 사례 revision, 좌표계, 격자 간격과 출력 provenance=estimated를 보존한다.

```text
python -m vv_toolbox.case_cli surface CASE.snapshot.json SURFACE.npz --edges EDGE_ID --spacing-mm 0.2
```

NPZ에는 `vertices_mm`, `faces`, JSON 문자열 `metadata`가 들어간다. `allow_pickle=False`로 열 수 있다. 기존 출력 파일을 덮어쓰지 않는다. 간격 0.2는 문법 예시이며 모든 혈관에 적합한 해상도를 뜻하지 않는다. 생성기는 최소 반경 대비 해상도를 검사하며 사전에 전체 격자 규모 상한을 검사한다.

중심선 끝은 닫힌 cap으로 생성되며 실제 해부학적 종말점 판정이 아니다. 선택 부분집합만 출력한다. 가까운 비접합 경로가 implicit union으로 합쳐질 수 있으므로 watertight PASS만으로 연결·충돌 검사를 통과했다고 표시하지 않는다. 자기 교차, 해부학적 연결, 임상 검증은 각각 NOT RUN 또는 UNKNOWN으로 기록한다. 닫힘·일관된 winding을 검사하고 필요 시 생성 표면의 winding만 반전하여 양의 체적 방향을 맞춘다. 원본 자료를 수정하지 않는다.

## 검증

선택 그래프가 분리되어 있으면 연결 component별로 표면을 생성하고 각각 닫힘·방향·양의 체적을 검사한 뒤 하나의 배열로 출력한다. `graph_component_count`와 각 component의 edge 목록·방향 반전 여부를 기록한다. 다른 component를 연결하는 형상을 추정하지 않는다. 선택 범위 전체의 간격 검사는 component 분리 전에 실행한다.

Docker 합성 fixture에서 반경 2 mm 직선 혈관의 중심 직경 50% 협착을 생성했다. 표면의 중심 단면 직경은 목표 2 mm에서 사전에 고정한 0.3 mm 이내였다(격자 0.2 mm). 이 허용치는 해당 수치 fixture의 공학적 검사 조건이며 임상 허용치가 아니다.

- 생성 표면 closed/oriented/positive volume PASS.
- 표면 단면 치수 PASS.
- 같은 표면→작은 ROI 3D 마스크의 내강/외부 및 estimated 출처 보존 PASS.
- source 사례 입력 거부, 과대 격자·부적절한 해상도 거부 PASS.
- CLI NPZ 재로드와 출처 보존 PASS.

병변 및 해부 구간 face/voxel label, 전 혈관 경로의 비접합 관통, 분기부 병변은 아직 이 기능으로 완료되지 않는다.

표면 생성 전 [간격 검사](GEOMETRY_CLEARANCE.md)를 실행한다. 비접합 혈관, 공유 node의 명시적 접합 collar 밖 구간, 같은 edge의 명시적 국소 호길이 범위 밖 구간을 보수적인 capsule로 검사한다. potential contact·검사 예산 소진·edge 전체를 덮는 collar가 있으면 생성을 차단한다. collar 안·국소 접힘·최종 표면 교차는 별도 미완료다.
