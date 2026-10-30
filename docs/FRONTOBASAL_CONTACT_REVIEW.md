# Medial frontobasal 접합부 검토

## 범위와 판정 기준

FJ1690과 FJ1654·FJ1655·FJ1695 사이의 원본 표면 접촉을 검토한다. 일반적인 해부학적 관계, 이 Atlas 표본의 표면 접촉, 실제 열린 내강 연결을 구분한다. 표면 교차나 이름 대응만으로 접합부를 승인하거나 자동 Boolean 결합하지 않는다.

현재 작업 경로는 `vv-toolbox`이며 이전 `vv-toolbox-dev`의 코드와 검사 기록은 main에 병합되어 있다. 이전 로컬 exports는 현재 체크아웃에 없어 기존 반경 후보나 중심선의 좌표 검사를 실행했다고 표시하지 않는다. 공식 원본은 프로젝트 취득 스크립트의 고정 SHA256으로 확인한다.

## 문헌 근거

- [Avci et al., 2003, DOI 10.2176/nmc.43.329](https://www.jstage.jst.go.jp/article/nmc/43/7/43_7_329/_article/-char/en): 발행처 초록을 확인했다. 31개 사체 뇌 연구에서 OFA는 A2에서 기시했고, ACom과의 평균 거리는 5.96 mm였다. FPA 역시 주로 A2에서 나오는 별도 분지로 기술됐다. 이는 ACA–OFA 관계의 근거이며 이 Atlas의 접촉 지점이나 내강 개방성 검증은 아니다.
- [Najera et al., 2019, PMID 30649510](https://pubmed.ncbi.nlm.nih.gov/30649510/): PubMed 초록을 확인했다. 25개 두부 표본에서 FOA의 70%가 A2에서 기시했다. FOA와 FPA는 기시뿐 아니라 주행과 도달 영역을 이용해 구별한다. 2003년 표본의 A2 기시를 모든 개체의 고정 규칙으로 적용하지 않는다.
- [The Microsurgical Anatomy of the Orbitofrontal Arteries, 2016, PMID 26875657](https://pubmed.ncbi.nlm.nih.gov/26875657/): 검색 초록에서 medial orbitofrontal/frontobasal 명칭과 ACA 분지 관계를 확인했다. 이번 직접 PubMed 열기는 초록을 반환하지 않았고 출판사 열기는 403이었다. 전문 확인 근거로 사용하지 않는다.

## 재현 검사

FJ1695는 공식 element table에서 `right ophthalmic artery`에 대응한다. frontopolar artery로 취급하지 않는다. [Bertelli et al., 2016, PMID 27048359](https://pubmed.ncbi.nlm.nih.gov/27048359/)의 검색 초록에는 ACA A1에서 나오는 ophthalmic artery 변이가 보고되어 있지만, 이는 medial frontobasal artery와의 직접 연결을 입증하지 않는다. 직접 PubMed 열기는 429 응답으로 제한되었으므로 검색 초록 수준의 근거로 한정한다.

| 대상 접촉 | 문헌과 명칭으로 가능한 분류 | 현재 수용 판정 |
|---|---|---|
| FJ1690–FJ1654 (right ACA) | ACA의 medial frontobasal 분지 기시 후보 | 표본의 ostium·내강 미확인, UNVERIFIED |
| FJ1690–FJ1655 (ACom) | ACom 부근의 표면 접촉. 확인한 논문은 ACA 기시를 지지하며 이 직접 연결을 입증하지 않음 | UNVERIFIED; 직접 연결로 등록하거나 결합하지 않음 |
| FJ1690–FJ1695 (right ophthalmic) | 서로 다른 이름의 혈관 간 접촉. ACA–ophthalmic 변이 보고를 이 접촉의 근거로 전용할 수 없음 | UNVERIFIED; 겹침 또는 연결 여부 추가 검토 |

`scripts/inspect_frontobasal_source_contacts.py`는 원본 네 부분의 삼각형 좌표를 보존한 인덱스 정규화 사본으로 접촉 쌍을 구한다. 각 혈관에서 접촉 삼각형들이 이루는 면 인접 연결 성분, 전체 지지 면적, 면적 가중 중심과 경계 상자를 기록한다. 지지 면적은 교차 면적이나 열린 혈관 입구의 면적이 아니다. 원본 면 번호는 보존되지만 이전 FJ1690 분할 후보의 면 번호와 혼용하지 않는다.

실행: Docker 컨테이너에서 `PYTHONPATH=src python scripts/inspect_frontobasal_source_contacts.py`.

## 원본 표면 측정 결과 (2026-10-30)

[검사 기록](evidence/frontobasal-source-contacts.json)은 네 OBJ의 해시, 원본 면 ID, 전체 접촉 쌍과 각 지지 영역의 좌표를 포함한다. 세 비교 모두 삼각형 쌍 검사를 끝까지 수행했다(`complete=true`).

| 이웃 | 접촉 삼각형 쌍 | FJ1690 지지 면 수 | 지지 영역 수 | 지지 면적 합계(mm²) |
|---|---:|---:|---:|---:|
| FJ1654 / right ACA | 51 | 28 | 2 | 17.224156 |
| FJ1655 / ACom | 4 | 2 | 1 | 1.967614 |
| FJ1695 / right ophthalmic | 49 | 16 | 1 | 4.535933 |

FJ1690 위 ACA 주 지지 영역의 중심과 ophthalmic 지지 영역의 중심 사이 거리는 약 **43.764 mm**다. 따라서 후자를 ACA/ACom 부근의 같은 국소 접합부로 일괄 수용할 근거가 없다. 이는 지지 면 중심의 직선거리이며 중심선 거리나 실제 입구 간 거리가 아니다. ACom 지지 영역은 ACA 주 지지 영역 근처지만 두 표면이 닿는 사실은 개방된 내강의 증명이 아니다. 세 대상 모두 표본 수준 접합 승인은 UNVERIFIED를 유지한다.

공식 ZIP과 5개 표/설명 파일의 해시는 기존 고정값과 일치한다. `LICENSE.html`만 불일치하여 정상 `load_atlas()`는 FAIL이다. 별도 진단 스크립트는 이 불일치를 보고서에 명시하고 해시가 일치하는 형상/표만 읽는다. 앱 로더의 검사와 고정 해시는 변경하지 않았다. 동적으로 생성된 페이지에 CSRF token/nonce가 포함되어 있으나, 불일치가 그것만의 영향인지와 라이선스 본문 동등성은 아직 확인하지 않았다. 취득 전체 성공이나 앱 복구로 표시하지 않는다.

이전 로컬 exports가 없어 반경 후보·기시 중심선 비교는 NOT RUN이다. 원본 표면 접촉을 독립적으로 재현한 결과를 기존 후보의 전체 문맥 PASS로 승격하지 않는다.

## 후속 수용 조건

1. 접촉 지지 영역과 중심선 기시 후보를 같은 좌표계에서 대조한다.
2. 일반적 분기 관계와 맞더라도 표본의 ostium 및 열린 내강을 별도로 확인한다.
3. 직접 연결 근거가 없는 접촉은 미확정으로 보존한다. 문헌에 없다는 이유만으로 변이를 부정하거나 원본을 이동하지 않는다.
4. 접합 승인, 단면 반경 검증, 전체 문맥 재검사가 끝나기 전 생성 수용 및 앱 적용은 false다.

## 라이선스 검증 및 중심선 재생성

공식 [라이선스 페이지](https://dbarchive.biosciencedbc.jp/en/bodyparts3d/lic.html)의 현재 본문, 귀속 문구, 조건과 링크를 확인했다. 원본 페이지 전체의 예전 바이트를 확보하지 못했으므로 과거 페이지와 모든 차이가 요청 토큰뿐이었다고 단정하지 않는다. 현재 검토한 본문의 고정 해시를 별도로 추가했다.

`source_identity.validate_source_identity`는 기존 전체 파일 SHA256을 우선 확인한다. LICENSE.html에 한해 정확히 하나의 완결된 `tinymce-content` 영역을 HTMLParser로 추출하고 태그·속성·텍스트를 정규화한 SHA256 `9c0ffe8ac89dfe29946cc3f903b39124553f4fbceecd97d25d8ede3df79691fb`와 대조한다. 라이선스 영역 밖의 페이지 장식과 요청 토큰은 이 별도 검사의 범위가 아니다. 영역 안 문구·링크·속성이 바뀌거나 영역이 없거나 중복되면 거부한다. 형상·해부학 표·README의 고정 해시는 그대로다. 원본 HTML을 보존하고 실제 파일 해시와 본문 해시, 적용한 검증 방법을 취득 기록과 Atlas 메타데이터에 남긴다. [관련 단위 검사 10개 PASS](evidence/source-identity-tests.xml).

취득 스크립트의 전체 파일 검증과 `load_atlas()`가 성공했다. 이는 파일 로딩 복구이며 브라우저 데모 실행 검증은 아니다. 이전 원본 표면 진단 기록의 FAIL은 실행 당시 기록으로 보존한다.

[복구 관련 회귀 검사 32개 PASS](evidence/source-restoration-tests.xml): 라이선스 식별, Atlas 파서, 중심선 추출 및 해부학 참조 그래프를 검사했다. scikit-image 내부 NumPy API의 deprecation 경고 50건이 있었으며 실패는 없었다.

`scripts/restore_frontobasal_centerlines.py`로 대상 네 원본 부분에서 voxel-medial 중심선을 재생성했다. [재생성 기록](evidence/frontobasal-centerline-restoration.json)에 런타임 버전, 원본 식별자, 출력 해시와 접촉 지지 중심의 최근접 구간 투영을 기록했다. 네 부분 모두 추출됐고 노드 13개·구간 6개다. 별도 `exports/frontobasal-restored/centerlines.json`에 저장했으며 과거 전체 동맥 snapshot이나 보정 후보를 덮어쓰지 않았다.

| 접촉 지지 영역 | FJ1690 최근접 구간 | 지지 중심–중심선 거리(mm) | 구간 시작에서의 호길이(mm) |
|---|---|---:|---:|
| ACA 주 영역 | e2 | 0.176 | 4.459 |
| ACA 작은 영역 | e2 | 0.892 | 0.000 |
| ACom | e2 | 0.915 | 4.997 |
| Ophthalmic | e0 | 0.150 | 5.356 |

e2 길이는 45.916 mm, e0 길이는 17.238 mm다. 시작·끝 방향은 추출 그래프의 인덱스 방향이며 혈류 방향이 아니다. 지지 중심은 전체 접촉 삼각형의 면적 가중 중심이므로 ostium 위치로 확정하지 않는다. 중심선 근접성 역시 표면 관통과 실제 연결을 구별하지 못한다. 이전 전체 snapshot과의 동등성은 NOT VERIFIED이고, 세 접합부의 해부학적 승인과 생성 수용은 여전히 미완료다.
