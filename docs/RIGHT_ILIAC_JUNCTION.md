# 우측 총장골–외장골 합성 연결

우측 총장골 `FJ3565:e0.start`의 Z=908.8 mm와 외장골 원래 근위 끝점의 Z=909.6 mm는 연속 진행 방향에서 겹친다. 두 끝점을 직접 잇는 대신 별도 합성 사례에서 말단을 절단했다.

## 구성

- 부모는 좌측 장골 smoothing까지 포함한 revision `23b547d31386462dbae203c4f60f67c0c363962878db538af88fe657570f5621`이다.
- 총장골은 고정 Z=915 mm, 외장골은 Z=903 mm에서 절단했다. 각 평면이 원본 중심선 내부 구간을 유일하게 가로지르는 것을 확인했다. 이는 합성 구성 규칙이며 실제 분기 경계가 아니다.
- 두 새 끝점 사이에 chord 길이와 같은 handle을 가진 192점 Hermite 연결을 만들었다. 역방향 진행 검사도 적용된다.
- 새 부착부 두 곳의 위치·반경 차이는 0이며 표본 접선각 차이는 각각 약 0.31도/0.18도다. 기존 선언 bridge 전체의 연속성 검사도 PASS다.
- 바뀐 두 edge 외에는 중심선과 반경 배열이 동일하다. 기존 합성 bridge가 참조하던 외장골 끝점은 유지 child로 갱신됐다.

## 경로 상태

좌우 대퇴→외장골→총장골 연결이 그래프에서 존재한다. 최신 역할 추적 검사에서 공통 leg 17종 중 7종 연결, 10종 미연결이다. 네 접근 조합 × ACA/MCA 근위 목표의 8개 선언 경로는 아직 모두 미완성이다.

우측 내부장골 분지는 이번 continuation 연산으로 붙이지 않았다. 원본 총장골 추출의 작은 추가 edge도 그대로 보존했다. 따라서 이 결과를 완성된 해부학적 장골 분기로 표시하지 않는다.

## 산출물

- `scripts/build_synthetic_right_iliac_junction.py`.
- [연결 생성·연속성 기록](evidence/synthetic-right-iliac-junction.json).
- [최신 역할별 경로 결손](evidence/access-route-gaps-right-iliac.json).
- `exports/synthetic-right-iliac-case/case.snapshot.json`.
- revision `ac6663b2ad015ed1031d35ff61ba84bcb35be5838656397e59d79107d2cdf8f5`.

현재 새 revision의 표면·주변 검사는 NOT RUN이며 해부학적 수용은 UNKNOWN이다. 원본과 앱 기본 사례는 변경하지 않았다.
