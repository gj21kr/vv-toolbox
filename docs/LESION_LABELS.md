# 병변 내강 라벨

`lesion_labels.label_lesion_lumen`은 합성 사례의 병변을 독립 uint32 배열로 출력한다. 정의는 **생성된 병변 영향 구간 안의 혈관 내강**이다. 협착으로 제거된 조직·plaque·혈관벽 또는 임상 정답 분할을 의미하지 않는다.

입력은 MaskVolume, 같은 frame의 synthetic case, 명시적인 edge→surface instance ID 목록이다. 원래 volume의 membership으로 혈관 소속을 제한한 뒤, 해당 edge 중심선에 투영한 nearest station이 병변 support 내부에 있는 voxel만 라벨링한다. 같은 surface instance를 여러 edge에 대응시키는 모호한 union 매핑은 거부한다. 이 매핑은 호출자가 제공한 대응이며 공간적 근접으로 자동 판정하지 않는다.

병변 ID 정렬 순서로 stable label 번호를 부여하고 registry를 함께 저장한다. 해부학·혈관 instance·출처 배열은 바꾸지 않는다. 병변 라벨 겹침은 오류이며, 병변이 0 voxel로 표본화되면 UNKNOWN이다. 격자를 바꾸거나 ROI를 조정해야 하며 자동으로 작은 병변을 누락시키지 않는다. nearest station 규칙의 곡률·교차 부근 모호성은 생성 규칙의 제한이며 해부학적 경계 승인으로 해석하지 않는다.

## 파일 출력

`vv-volume` 또는 `python -m vv_toolbox.volume_cli`에 `--case-snapshot CASE.json --edge-instances MAPPING.json`을 함께 전달한다. 나머지 표면 manifest/grid 입력은 [마스크 출력](VOXEL_OUTPUT.md)과 동일하다. crop을 요청하면 crop의 물리좌표에서 라벨을 계산한다.

NPZ에 `lesion_instance`와 JSON 문자열 `lesion_metadata`를 추가한다. 병변 표본화 UNKNOWN이면 CLI는 출력 성공으로 처리하지 않는다. 기존 출력 파일은 덮어쓰지 않는다.

## 검사

Docker 5개 검사 PASS: 지정 혈관 내강만 라벨링·인접 혈관 누출 방지·기존 anatomy 보존, crop과 전체 배열 라벨 일치, 작은 병변 미표본화 UNKNOWN, 겹침/누락 매핑 거부, NPZ에서 독립 라벨과 registry 재로드.

현재 배치 출력과 앱의 병변 조작 연결은 별도 작업이며 전체 동맥의 표면 instance 분할을 대체하지 않는다.
