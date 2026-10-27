# MCA 전체 경로와 6개 경계군 검사

`scripts/inspect_mca_boundary_paths.py`는 기존 대표 8개 요소를 넘어 MCA 이름으로 대응된 **46개 source 요소의 120개 추출 edge 전체**를 검사한다. 좌우 각각 23개 요소를 두 방향씩 표시해 총 92개 시야를 8개 sheet로 저장했다. source vessel mesh, insula, 주변 6개 gyrus와 M1 원본을 함께 표시한다. 원본 60개 OBJ와 archive·preview hash를 기존 보고서와 대조했다.

8개 sheet를 직접 열어 전체 경로 표시를 확인했다. 이는 개별 경계의 해부학적 판독 완료가 아니다. **좌우 M1/M2, M2/M3, M3/M4 여섯 경계군 모두 승인 0개**, `position=null`을 유지한다. 120개는 실제 daughter 수가 아니라 skeleton 추출 edge 수이다.

## 전체 경로를 확인하며 얻은 관찰

아래 각 행은 우측 ID와 좌측 `M` 대응 요소를 **각각 표시한 그림**을 확인한 결과다. 공통 형태를 정리했으며 좌측 좌표·edge 번호·경계를 우측에서 복사하지 않았다. 특히 추출 방향과 edge 분할은 좌우에서 다르다.

| 요소 쌍 | 양측 화면에서 확인한 경로 | 다음 판독 대상 |
|---|---|---|
| FJ1659 / M | 여러 갈래가 insula 아래쪽에서 더 외측·아래로 퍼짐 | 각각의 temporal 경로 기시와 주행을 먼저 연결; 동일한 M2/M3 통과 강제 금지 |
| FJ1660 / M | insula 전하방의 짧은 굴곡 | M1과 실제 접합 및 limen/genu를 함께 표시 |
| FJ1662 / M | 짧은 줄기에서 여러 가는 추출 경로가 위쪽으로 퍼짐 | source central-branch 명칭 확인; cortical segment 체계 적용 대상부터 구분 |
| FJ1663 / M | insula 아래의 짧은 선형·분기 경로 | central-branch 기시를 판독; M3/M4 출구 찾기로 대체하지 않음 |
| FJ1664 / M | 하단에서 굽은 뒤 길게 상방으로 진행 | circular sulcus 교차와 더 외측 출구를 서로 분리해 판독 |
| FJ1665 / M | 아래에서 고리처럼 돌아 상방으로 진행 | 굴곡과 실제 sulcus 통과를 구분 |
| FJ1666 / M | 하부 짧은 횡방향 구간에서 위쪽으로 방향 전환 | 전환점 주변 insula margin과 opercular 경로 확인 |
| FJ1667 / M | 대체로 길고 위쪽으로 뻗으며 끝에서 짧게 굽음 | 근위 경로가 어디에 이어지는지와 출구 위치 별도 추적 |
| FJ1668 / M | 하부 굴곡 뒤 높은 피질 쪽으로 진행 | 하부 굴곡이 sulcus인지 독립 표면 landmark 필요 |
| FJ1669 / M | insula 외측에서 짧게 굽어 위로 진행 | 짧은 요소 끝을 경계로 고정하지 않고 전후 part 연결 확인 |
| FJ1670 / M | insula보다 위쪽에 놓인 짧은 경로 | 근위 opercular 구간을 포함하지 않을 수 있으므로 이어지는 source part 확인 |
| FJ1673 / M | 높은 위치의 짧은 여러 추출 가지 | 원위 분할·기시 판독 후 경계 적용 여부 결정 |
| FJ1685 / M | insula 뒤쪽으로 길게 뻗다가 되돌아 굽음 | 후방 groove와 opercular 출구를 개별적으로 추적 |
| FJ1686 / M | 뒤쪽으로 길게 이어지는 비교적 단순한 경로 | 근위 연결과 뒤쪽 출구의 실제 surface landmark 확인 |
| FJ1692 / M | insula 아래에서 횡방향으로 진행하는 named M1 | 말단 분기점과 genu를 같은 점으로 가정하지 않음 |
| FJ1693 / M | insula 가까운 상단에서 아래로 긴 경로 및 말단 분할 | 시작/끝 추출순서를 혈류 방향으로 해석하지 않고 기시 확인 |
| FJ1694 / M | insula 하부를 따라 길게 굽은 named insular 경로 | 접촉 근처 bend 탐색점과 실제 genu 분리, distal sulcus도 따로 판독 |
| FJ1712 / M | 아래쪽에서 외측으로 굽는 짧은 경로 | 전후 part와 이어지는 opercular 구간 추적 |
| FJ1716 / M | 하부 굴곡에서 상방으로 진행한 뒤 가지가 나뉨 | 분할 전후 같은 daughter인지 확인하고 sulcus/출구 표시 |
| FJ1717 / M | 상단에서 아래로 길게 진행, 하부의 작은 분할 | temporal 방향의 실제 진행과 기시를 독립 확인 |
| FJ1718 / M | insula 하부에서 짧게 굽는 trunk 요소 | 현재 요소만으로 distal exit가 없으므로 연결 source part 필요 |
| FJ1724 / M | 하부의 큰 굴곡과 상방의 긴 여러 추출 경로 | 공통 하부 경로와 각 원위 가지의 출구를 따로 표시 |
| FJ1729 / M | insula 아래를 길게 따라간 뒤 외측·하방으로 여러 갈래 | 각 temporal 경로를 분리해 추적; 단일 공통 출구 평면 금지 |

배경은 반투명 전체 gyrus 표면이며 sulcus 자체의 주석이 아니다. 전체 보기에서 피질 경계가 중첩되는 부분은 이 그림만으로 정확한 출구를 판정할 수 없다. JSON의 edge별 이유·후속 작업은 범주별 검사 지침이며 120개 edge의 독립 전문 판독 결과를 의미하지 않는다.

## 재현 가능한 탐색점

모든 길이 >4 mm 경로에 대해 ±2 mm chord의 방향 변화량을 0.25 mm arc 간격으로 계산해 큰 굴곡을 `operational_path_probe`로 기록했다. 짧거나 퇴화한 경로에는 null과 이유를 기록한다. 이 점들은 **경계 후보가 아닌 경로 재탐색 좌표**이며 voxel skeleton의 요동일 수도 있다.

기존 M1–named insular source 접촉 탐색점 4개 주변에서는 접촉점의 중심선 투영 arc ±8 mm 안에서 같은 방식으로 굴곡 탐색점을 추가했다. source edge interval/fraction, XYZ, 반경, ±2 mm 탐색 범위를 기록하여 같은 위치를 다시 볼 수 있다. ±2 mm는 통계적 신뢰구간이 아닌 chord 계산 창이다.

| 탐색 edge | interval / fraction | arc mm | XYZ mm | chord turn |
|---|---|---:|---|---:|
| FJ1660:e0 | 13 / 0.6615000029 | 7.00 | [-40.486592,-108.744845,1550.301094] | 24.58° |
| FJ1694:e0 | 117 / 0.8673419538 | 62.75 | [-45.462681,-99.887524,1551.270036] | 22.37° |
| FJ1660M:e0 | 14 / 0.0744018663 | 7.00 | [40.514175,-108.638330,1550.145444] | 19.21° |
| FJ1694M:e0 | 13 / 0.1180616350 | 7.75 | [45.855236,-98.718851,1552.415283] | 14.37° |

**이 네 점을 genu로 자동 채택하지 않는다.** 화면의 파란 점은 `operational_bend_locator`이며 `anatomical_boundary_approved=false`이다. 원래 source contact point도 독립 anatomical landmark가 아니므로 두 종류의 계산이 일치해도 승인 근거가 되지 않는다. M2/M3·M3/M4에 대해서는 이번 자료에서 landmark로 뒷받침되는 좌표를 확보하지 못했다.

## 산출물과 검증 범위

- [mca-boundary-path-audit.json](evidence/mca-boundary-path-audit.json): 46개 source part, 120개 edge, 각 edge의 세 경계군 평가·후속 판독 지침, 4개 contact-window 탐색점, source/figure SHA-256.
- `exports/mca-boundary-path-audit/R-1.png`…`R-4.png`, `L-1.png`…`L-4.png`: 각 요소 두 시야. source 관련 그림은 Git에 추가하지 않는다.
- 원본 archive·60개 OBJ·preview fingerprint, 기존 route 목록과 edge 집합, 46/120/6 coverage를 Docker 실행에서 검사했다.
- 원본 source·앱 annotation·graph에 쓰기 없음. 임상/독립 영상 검증 NOT RUN. 해부학적 승인 0/6 유지.
