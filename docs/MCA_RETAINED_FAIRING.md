# MCA 표면 보정 후보 검사

접합부와 인접 면의 정점을 고정하고 나머지 표면에 제한적 보정을 적용했다.
원본 및 데모에 등록된 후보는 보존하며, 새 후보는 별도 파일로 저장한다.

## 형상

- 후보 SHA256: `ed7178832bf4abc0847d7c0b315c4743d0a79726b6d951a51d0e5019d9e0d347`
- 원본: `cd83cdceb58b76019d61993107c069ff270f7927c65b084ce567de6a9031634a`
- 최대 정점 변위 0.0447203 mm, 체적 변화 0.00358843%.
- 접합부 주변 1,117개 정점과 neck 설계 곡선 보존.
- 보정 대상 영역의 인접 면 각도 p95: 14.0322° → 7.09224°.
- 접합부 각도는 그대로이며 매끄러움의 최종 판정은 UNKNOWN.

## 새 후보에 대한 검사

| 검사 | 결과 | 범위 |
|---|---|---|
| 자기교차 | NO_CONTACT_DETECTED | 전체 후보 표면의 서로 다른 삼각형 쌍; 보수적 공간 후보 추출 후 비인접 4,694쌍, 인접 328,832쌍 정밀 검사 |
| 주변 중심선·반경 프로파일 | REVIEW_REQUIRED | 1,080개 중 1,075개 분리 확인; 5개 내부 점 증거 |
| 새 접합부만 | SEPARATED_PROFILES | 주변 1,080개 프로파일 |
| 보존 sac 영역 | SEPARATED_PROFILES | 주변 1,080개 프로파일 |
| 원본 Atlas 표면 충돌 | NOT RUN | 프로파일 검사로 대체할 수 없음 |
| 해부학적 연결 승인 | UNKNOWN | 내부 점 증거를 정상 분기로 해석하지 않음 |
| 앱 미리보기 | PASS | 별도 읽기 전용 후보로 표시; 기존 후보도 유지 |

내부 점 증거가 남은 혈관 ID는 FJ1654:e0, FJ1660:e0, FJ1682:e0,
FJ1694:e0, FJ1718:e0이다. 이전과 ID 집합이 같지만 교차 위치나 범위가
같다는 뜻은 아니다. FJ1662:e12는 추가 세분화로 분리 확인했으며
거리 하한은 0.000253576 mm이다. 이는 모델에 대한 계산 하한으로,
해부학적으로 충분한 이격 거리를 의미하지 않는다.

자기교차 검사는 유한 정밀도이며 정확 술어 인증은 아니다.
수치 허용 오차는 1e-8 mm이며 인접 쌍 검사는 공유 위상 밖의 겹침을 확인한다.

## 재현

프로젝트 Docker 환경에서:

```text
PYTHONPATH=src python scripts/inspect_mca_retained_fairing.py
PYTHONPATH=src python scripts/inspect_transition_contacts.py --adjacent --whole-surface --retained-fairing
PYTHONPATH=src python scripts/inspect_uniform_transition_context.py --retained-fairing
PYTHONPATH=src python -m pytest tests/test_adjacent_contact.py tests/test_triangle_contact.py tests/test_surface_context.py -q
```

관련 검사 테스트 25개 통과. 기계 판독 기록:
[형상 보정](evidence/mca-retained-fairing.json),
[자기교차](evidence/mca-retained-fairing-uniform-full-surface-contacts.json),
[주변 프로파일](evidence/mca-retained-fairing-context.json).

## 앱 미리보기

`right-mca-retained-fairing`을 별도 등록했다. 선택 항목은
“우측 MCA 표면 보정 · 검토 필요”이며 전용 형상·주변 프로파일·자기교차
근거의 파일 해시와 사례 revision을 확인한다. 접합부 보존 실패나 전용
검사 파일 누락 시 로딩을 거부한다. 관련 로더·작업공간 테스트 21개 통과.

localhost:8093에서 API로 후보를 선택하고 1500×1000 브라우저 화면의
빨간 표면, 읽기 전용 표시, 1075/1080 및 UNKNOWN 표시를 확인했다.
화면은 `exports/junction-preview-browser/fairing.png`에 저장했다.
이 실행에서는 드롭다운 클릭을 통한 선택은 검사하지 않았다.
시각적으로 잔물결은 줄었으나 완전히 사라지지 않았으므로 매끄러움은
계속 UNKNOWN이다. 생성 당시 증거의 `app_applied: false`는 보존하며,
후속 미리보기 적용 사실은 본 절에 별도로 기록한다.
