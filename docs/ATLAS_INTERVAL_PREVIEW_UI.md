# Atlas 구간 미리보기 화면

왼쪽 `3 · Modify selected vessel` 패널 아래에 **구간 크기 미리보기**를 추가했다. 단일 중심선 혈관을 선택하면 내부 호길이와 시작·끝 거리 입력이 활성화된다. 중앙 배율, 최대 정점 이동, 단면 배율 허용오차는 사용자가 입력한다.

실제 미리보기 API를 호출하며 실패 메시지를 표시한다. 성공 응답은 별도 캔버스에 표시하고 원본/후보 전환, 드래그·방향키 회전을 제공한다. 동맥은 빨강, 그 외 혈관 레이어는 파랑이다. 선택 혈관 또는 장면 generation이 바뀌면 이전 후보를 제거한다. 활성 Atlas 장면과 저장 상태는 변경하지 않는다.

미리보기는 mm 단위의 실제 정점과 삼각형을 투영한 비교 화면이다. 주변 혈관은 작은 캔버스에 표시하지 않으며 전체 충돌 승인을 의미하지 않는다. 다중 분기 part는 미지원 상태를 표시한다. 이 제한은 개발계획의 다중 분기 요구사항을 제거하지 않는다.

## 검증

- [백엔드 검사](evidence/interval-ui-backend-tests.xml): 4개 PASS.
- [브라우저 검사](evidence/interval-preview-ui.json): PASS.
- 실제 서버에서 FJ1692 이동 한도 초과 오류를 화면에 표시하고 후보를 숨김.
- 성공 표시·원본/후보 전환·방향키 회전은 **합성 응답을 주입한 UI 검사**다. 실제 Atlas 성공 후보 생성 검증과 구분한다.
- 390 px 화면에서 가로 넘침 없음, 선택 변경 시 이전 결과 폐기, 활성 수정과 generation 불변.
- Playwright 사용 이유: Browser plugin not available. 최종 검사는 새 패널과 자체 캔버스에 한정하여 Viser iframe을 로드하지 않았다.
- `exports/interval-preview-ui/candidate.png`, `mobile.png`를 직접 시각 확인했다.

실행: `node scripts/verify_interval_preview_ui.cjs`.

데모 서버에 최신 코드를 반영했다. 실제 Atlas 성공 후보·전체 3D 장면 표시·적용/저장/복원은 별도 미완료다.
