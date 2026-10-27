# 로컬 원자료 파일 검사

검사일: 2026-10-20 · 대상: BodyParts3D 4.0 및 VMR 0011_H_AO_H · 상위 문서: [자료조사](DATA_SOURCE_SURVEY.md)

## 1. 검사 범위와 판정

PowerShell의 TSV/XML 판독, SHA-256, .NET ZIP 중앙 디렉터리 검사를 수행했다. 원본 형상 수정, 재구성, 영상 렌더링, 체적 겹침 검사와 임상 검증은 수행하지 않았다. 아래 `파일 확인`은 파일·주석의 존재를 뜻하며 해부학적 연결 확인을 뜻하지 않는다.

| 검사 | 결과 |
|---|---|
| BodyParts3D acquisition.json에 고정된 7개 파일 해시 | PASS: 7개 일치 |
| BodyParts3D ZIP | 2,234개 항목, 모두 OBJ, 고유 경로 2,234개 |
| 아래 표에 등장하는 25개 고유 OBJ 요소 | PASS: 각 파일명에 정확히 1개 ZIP 항목 |
| VMR acquisition.json에 등록된 로컬 15개 파일 해시 | PASS: 15개 일치 |
| VMR 경로–단면 대응 | 5개 path ID와 5개 contourgroup path_id 대응 확인 |
| 표본별 혈관 접속 그래프 | 이번 검사 파일에서 제공 확인되지 않음 |
| A1–A3/M1–M3의 완전한 구간 경계 | 제공 확인되지 않음 |

원자료 위치는 저장소 상대 경로 `reference-data/bodyparts3d/`, `reference-data/vmr-0011/`이다. 캐시 중심선이나 애플리케이션의 후보 링크를 원자료 주석으로 집계하지 않았다. 공개 원자료는 Git 문서와 별도로 관리한다.

## 2. BodyParts3D 대상 혈관 대응

`isa_element_parts.txt`의 **정확한 이름과 concept id**로 추출했다. 요소 개수는 동일 개념의 고유 element file id 수다. 표의 한 개 요소가 온전한 한 혈관이나 단일 연결 성분이라는 뜻은 아니다.

| 원자료 개념명 | Concept ID | OBJ element ID | 개수 |
|---|---|---|---:|
| right femoral artery | FMA70249 | FJ2143 | 1 |
| left femoral artery | FMA70250 | FJ2074 | 1 |
| right external iliac artery | FMA18806 | FJ3567 | 1 |
| left external iliac artery | FMA18807 | FJ3466 | 1 |
| right common iliac artery | FMA14765 | FJ3565 | 1 |
| left common iliac artery | FMA14766 | FJ3464 | 1 |
| right internal iliac artery | FMA18809 | FJ3569 | 1 |
| left internal iliac artery | FMA18810 | FJ3468 | 1 |
| ascending aorta | FMA3736 | FJ3413 | 1 |
| arch of aorta | FMA3768 | FJ3411 | 1 |
| descending thoracic aorta | FMA87217 | FJ1931 | 1 |
| abdominal aorta | FMA3789 | FJ1932 | 1 |
| descending aorta | FMA3784 | FJ3427 | 1 |
| right common carotid artery | FMA3941 | FJ3564 | 1 |
| left common carotid artery | FMA4058 | FJ3483 | 1 |
| right internal carotid artery | FMA3949 | FJ1682 | 1 |
| left internal carotid artery | FMA4062 | FJ1682M | 1 |
| right anterior cerebral artery | FMA50029 | FJ1654 | 1 |
| left anterior cerebral artery | FMA50030 | FJ1654M | 1 |
| sphenoid part of right middle cerebral artery | FMA50366 | FJ1692 | 1 |
| sphenoid part of left middle cerebral artery | FMA50367 | FJ1692M | 1 |
| insular part of right middle cerebral artery | FMA50369 | FJ1660, FJ1694 | 2 |
| insular part of left middle cerebral artery | FMA50370 | FJ1660M, FJ1694M | 2 |

주의: `descending aorta`와 `descending thoracic aorta`·`abdominal aorta`가 별개 요소로 존재한다. 의미가 겹쳐 보인다는 이유로 모두 합치거나 중복 제거하면 안 된다. 실제 표면 범위·겹침을 별도 확인해야 한다.

### 2.1 구간 라벨의 실제 수준

두 `*_parts_list_e.txt`에서 단어 경계 기준 `A1`, `A2`, `A3`, `M1`, `M2`, `M3` 문자열은 발견되지 않았다. 다만 **sphenoid part**, **insular part**라는 해부학적 구역 개념은 위와 같이 존재한다. 이를 앱에서 M1/M2로 대응시켜 쓰더라도 **원자료의 숫자 구간 라벨과 접합점 주석이 있는 것처럼 기록하지 않는다**.

- ACA는 좌우 이름 있는 요소를 제공하지만 A1/A2/A3 각각의 독립 요소·경계 좌표는 이번 표에서 확인되지 않았다.
- `branch of postcommunicating part of anterior cerebral artery`(FMA79615)는 존재한다. 이것은 postcommunicating ACA 자체의 경계 주석이 아니다.
- callosomarginal 및 pericallosal 개념은 존재하지만 A2/A3 경계와 동일한 라벨로 자동 치환하지 않는다.
- MCA의 insular part는 한쪽에 2개 요소다. 첫 항목만 고르는 매핑은 불완전하다.
- MCA M3의 명시적 구간 또는 opercular part/segment 주석은 검사한 이름 목록에서 확인되지 않았다. 말초 분지들의 존재를 M3 경계 정답으로 간주하지 않는다.

### 2.2 PART-OF와 접속 관계 구분

`partof_element_parts.txt`는 포함 관계다. 예를 들어 `right femoral artery`(FMA70249)에 FJ2137, FJ2143, FJ2158, FJ3614가 대응하고, `right common carotid artery`(FMA3941)에는 총경동맥 요소와 여러 두개내 요소가 함께 포함된다. 이 행들은 직접 parent/daughter 인접 목록이 아니다. `aorta`(FMA3734)의 PART-OF 요소는 FJ1931, FJ1932, FJ3411, FJ3413, FJ3427이다.

IS-A/PART-OF에서 연결 그래프를 생성하거나, 폴리곤의 접촉만으로 실제 내강 연결을 확정하는 것은 이 검사 범위를 넘는다.

## 3. VMR 0011 경로와 단면 주석

파일에 XML 선언 뒤 `<format/>`과 `<path/>` 또는 `<contourgroup/>`가 나란히 있어, 읽을 때만 임시 루트로 감싸 XML을 판독했다. 원본 파일은 변경하지 않았다. 점 개수는 XML 항목 수이며 균일 간격이나 해부학적 정확성을 뜻하지 않는다.

| Paths 파일 | path id | control_points/point | path_points/path_point | 대응 Segmentations 파일 | contour 수 | contour_points/point 합계 |
|---|---:|---:|---:|---|---:|---:|
| aorta.pth | 101 | 15 | 300 | aorta_final.ctgr | 20 | 2,196 |
| btrunk.pth | 200 | 10 | 200 | btrunk_final.ctgr | 10 | 483 |
| carotid.pth | 401 | 10 | 150 | carotid_final_short.ctgr | 10 | 381 |
| rt_carotid.pth | 301 | 6 | 100 | rt_carotid_final_short.ctgr | 7 | 249 |
| subclavian.pth | 601 | 10 | 200 | subclavian_final.ctgr | 15 | 607 |
| **합계** | — | **51** | **950** | — | **62** | **3,916** |

경로에는 위치·접선·회전 정보가 있고, 단면에는 path_id, path_point, closed 속성 및 lofting 설정이 있다. 경로 파일의 속성명은 calculation_number, id, method, spacing, version, x, y, z다. 경로 사이의 parent/child, junction, inlet/outlet 접속 좌표, 해부학적 구간 ID 또는 물리 단위를 명시하는 속성은 이 10개 XML에서 확인되지 않았다. `path_id`는 단면 묶음이 참조하는 경로 ID이며 혈관 사이 접속 관계가 아니다.

보조 확인한 `Models/0094_0001.mdl`에는 wall과 6개 cap 이름(inflow, btrunk, rt_carotid, carotid, subclavian, outflow)이 있다. 이 경계면 이름은 유용하지만 5개 경로 사이의 연결 그래프를 명시하지 않는다. `carotid`라는 파일명만으로 좌측/총경/내경 범위를 확정하지 않는다. femoral/iliac/ACA/MCA 이름의 경로는 이 로컬 Paths 5개 목록에 없다.

## 4. 입력 SHA-256

아래 값은 이번에 다시 계산했다. 원본 URL과 취득 크기는 각 `acquisition.json`에 있으며, BodyParts3D 공식 위치는 [배포 목록](https://dbarchive.biosciencedbc.jp/en/bodyparts3d/download.html), VMR 사례의 영구 주소는 [Stanford record](https://purl.stanford.edu/kd053sz6270)다. 이번 검사는 로컬 사본에 대한 것이며 원격 재다운로드 일치 검사는 아니다.

```text
BodyParts3D/
isa_BP3D_4.0_obj_99.zip 40665852c49f218326590e204db91064a1ecfc3c6f8cbd7bbbcaac62c7cd409e
isa_parts_list_e.txt ab7796deedd49205e77f3609a1cb8c53e2bbee14ecb5c9a6ca05227469780513
isa_element_parts.txt a3de74423f943b0d724ae8f59b3a817f87c423a544f8db98113b1980817cbeaf
partof_parts_list_e.txt 9224080557053e6f1322f1e13ab27f0ecde0db19bb3b505f0631afad230eeebd
partof_element_parts.txt 3f5f6df1028eb122b30de77c711597b6bb8e5541658e5985859fd228adbf88ea
VMR0011/Paths/
aorta.pth f9410d84504bf5ad6f8380fbe22fdbe997bbd7e72531274bef272721d3ceb616
btrunk.pth 81d598615b49d328b7b7c03078d36d6543ab991e68ce44b9f0b0f8e0cf60932d
carotid.pth 494d780e5dc7184d9457696dac980b74c46cf84dbb01d71a61beb42b23b77606
rt_carotid.pth 1ea4009d99773656dfae5ebc156b84e6ef5dd0b0c00621bcb2b43ff12a5ad7c7
subclavian.pth 173750d0d3c738d26a0607af995862b1c45bb81d1071b0fbc3d78798fafdc8e9
VMR0011/Segmentations/
aorta_final.ctgr 6e33a60ea503ff64902ebf806a399b21d831a60cba33f9cff2568027efefff75
btrunk_final.ctgr 494a856cd5707d30ded911f4c6a58620556b5530d0b991630ba6fe39df09eb29
carotid_final_short.ctgr b51808893c642a19a1749e18c9a226e1e14319da0a95f2112cc7c39981de3b3c
rt_carotid_final_short.ctgr 5c5f19a0fc293a0a0276a7d7bcba07f1561580e98a4eedfd65f140048b1bfccb
subclavian_final.ctgr acf1e955bf38f037e260a95304e7561384db2f796d54daec24d8337bcc3be5a0
```

## 5. 기준 모델 선정에 필요한 다음 검사

1. BodyParts3D의 25개 요소는 **명칭 대응 후보**로 등록한다. 대퇴 접근점, 경부 결손, 겹치는 대동맥 요소와 단일 표본의 연속성은 별도 형상 검사 대상으로 둔다.
2. VMR 0011은 **대동맥궁 주변의 경로·단면 대조 후보**다. 단위·좌표계, 촬영 범위와 절단 위치를 사례 설명 및 원영상으로 확인한다.
3. ACA A1–A3/MCA M1–M3의 경계·분기 좌표를 위한 주석 프로토콜이 필요하다. 이름 매핑만으로 구간별 마스크를 확정하지 않는다.
4. 원자료의 포함 관계, 앱이 추출한 공간 후보, 독립 자료로 대조한 연결, 합성 보충 연결은 서로 다른 데이터 필드로 관리한다.

**선정 상태:** 로컬 파일 존재·무결성·명칭 매핑 PASS. 해부학적 접속·세부 구간 경계·최종 기준 모델 채택은 NOT VERIFIED.
