# 합성 사례 반경 평활화

`radius_regularization.smooth_synthetic_radii`는 선택한 혈관의 반경만 별도 합성 사례에서 평활화한다. 원본 사례를 직접 입력하면 거부한다. 좌표·중심선·node·양 끝 반경·선택하지 않은 혈관은 유지한다. 기존 병변이 있는 edge는 병변 형상 손상을 막기 위해 거부한다.

물리 호길이에서 균일 재표본화하고 Gaussian 필터를 적용한다. 끝점에서 3 sigma까지 smoothstep으로 영향도를 줄여 양 끝 반경을 정확하게 보존한다. sigma와 표본 간격은 mm 단위다. 표본 간격은 sigma/2 이하여야 한다. 최대 반경 변화량이 사용자가 정한 `max_change_mm`를 넘으면 전체 연산을 실패시키며 한계값으로 잘라서 통과시키지 않는다.

선택 edge는 estimated/synthetic_estimate로 기록하고 부모 사례 revision·기존 생성 조건·필터 설정·실제 최대 변화량을 보존한다. 이전 geometry 검사 상태는 새 형상의 PASS로 승계하지 않는다. 중심선 변화·표면 충돌·해부학적 보정의 정확성은 이 연산의 검증 범위가 아니다.

```text
python -m vv_toolbox.case_cli smooth-radii INPUT.snapshot.json PARAMETERS.json OUTPUT.snapshot.json
```

파라미터 JSON에는 `edge_ids`, `sigma_mm`, `sample_spacing_mm`, `max_change_mm`, 새 `case_id`를 명시한다. CLI는 입력 파일·파라미터 파일 덮어쓰기를 거부한다. 기존 출력 갱신에는 `--expected-revision`이 필요하다.

Docker 관련 검사 **21 passed, 0.91 s**. 합성 반경의 고주파 변화 감소, 끝점·중심선·비선택 혈관 보존, 재현성, 최대 변화량 초과 거부, 원본 입력·기존 병변 평활화 거부 및 CLI 저장을 확인했다. 실제 Atlas 표면의 요철 변화는 별도 단면 측정으로 판단한다.

실제 목 사례에서 sigma 2 mm, 표본 간격 0.25 mm, 최대 반경 변화 1 mm를 고정한 비교를 실행했다. 실제 최대 반경 변화는 약 0.422 mm였으며 입력 반경의 변동은 줄었다. 그러나 동일 단면에서 측정한 표면 반경 변동은 네 곳 중 두 곳에서 증가했다. 따라서 이 설정은 전체 표면 요철을 해결한 기본값으로 채택하지 않는다. 파생 사례를 별도로 보관하고 중심선·단면 방향·표면 생성의 영향을 추가로 검사한다.
