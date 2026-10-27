# 합성 협착 프로파일

`lesions.concentric_stenosis`는 원본 사례를 보존하고 별도 synthetic 사례에 단일 동심성 협착을 생성한다. 대상 edge, 병변 ID, 새 사례 ID, 부위, 중심 arc-length·길이·협착률·측정 방식·표본 간격·seed를 명시한다. 같은 입력은 같은 결과를 낸다.

지원 측정은 `local_baseline_diameter`와 `local_baseline_area`다. 후자는 원형 단면 가정이며 면적 감소율에서 반경 비율을 제곱근으로 변환한다. NASCET/WASID는 적격 기준 단면 입력과 검증 전까지 거부한다. 부위별 임상 범위·모집단 확률 분포를 추정하지 않는다.

반경 변화는 명세의 compact polynomial kernel을 사용한다. 원래 중심선 점을 보존하고 병변 중심과 support 끝 및 설정 간격의 표본을 보간 삽입한다. support 끝의 반경과 edge의 공유 양 끝 좌표를 보존한다. 병변 중심에서 요청한 감소율과 계산한 프로파일 감소율을 기록한다. 가변 기저 반경에서는 이 값이 전체 병변의 최소 직경 위치를 뜻하지 않는다.

출력은 원본 base_model_id·출처·split을 유지하며, 변경 edge를 estimated/synthetic_estimate로 표시한다. 기존 연결 node의 미확인 상태는 그대로다. region은 사용자가 명시한 설계 설정이며 Atlas의 해부 부위 판정을 대체하지 않는다.

## 실행

```text
python -m vv_toolbox.case_cli stenosis SOURCE_SNAPSHOT.json PARAMETERS.json DERIVED_SNAPSHOT.json
```

PARAMETERS 필드: `edge_id`, `lesion_id`, `case_id`, `region`, `center_mm`, `length_mm`, `severity_percent`, `measurement_method`, `sample_spacing_mm`, `seed`, `min_spacing_mm`(기본 0, 접촉·겹침은 여전히 거부).

## 현재 제한과 검사

- support는 edge 양 끝 안쪽에 있어야 한다. 분기부 병변은 별도 구현 대상이다.
- 각 병변은 변경 전 반경으로 감싼 3D capsule 영향 영역을 저장한다. 이후 병변은 기존 모든 병변과 구간 간 최소 거리를 계산하여 겹침·접촉과 최소 간격 위반을 거부한다. 서로 다른 edge도 동일하게 검사한다. 두 병변의 설정 중 더 큰 최소 간격을 적용하며, 이전 조건을 낮춰 실패를 통과시키지 않는다.
- 과거 버전처럼 3D 영향 영역 기록이 없는 병변에는 추가 병변을 적용하지 않는다. 검사 쌍 예산을 넘으면 오류로 종료한다. 이 영향 영역은 보수적인 설계 범위이며 환자 병변의 실측 외곽이나 최종 삼각형 표면 교차 검사가 아니다.
- 중심선 반경 프로파일만 변경한다. 원본 삼각형 표면을 수정하지 않으며 표면 생성·측정, 충돌, 마스크 병변 라벨은 NOT RUN이다.
- 0%와 완전 폐색 100%는 이번 협착 연산 범위 밖이다. 양의 길이·잔여 내강·표본 간격은 수치 조건이며 임상 허용 범위가 아니다.
- Docker 병변 검사 16개 및 표면 회귀 4개 PASS: 면적/직경 구분, 원본 불변, 양 끝 보존, 동일 설정 재현, 잘못된 설정 거부, 겹침 병변 차단, 떨어진 다중 병변·기존 반경 보존, 다른 edge의 3D 충돌, 이전 최소 간격 유지, CLI 생성·snapshot 재로드.

문헌 정의와 부위별 확장 계획은 [질환 명세](DISEASE_PRESET_SPEC.md)를 따른다.
