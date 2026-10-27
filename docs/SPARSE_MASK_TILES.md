# 공간 블록 단위 마스크 출력

`iter_mask_tiles`는 grid를 고정 크기 블록으로 나누고 각 블록의 voxel 중심 범위와 만나는 표면만 계산한다. 비어 있지 않은 블록만 반환한다. 각 블록은 foreground, 해부 라벨, 대표 instance, 출처, 겹침 수, 모든 해당 표면의 membership을 보존한다. 블록마다 instance 목록이 있으므로 서로 다른 블록의 membership 행 번호를 동일한 혈관 ID로 가정하지 않는다.

모든 입력 표면을 첫 출력 전에 검사한다. grid 밖에 있는 열린 표면도 조용히 무시하지 않는다. 명시적으로 선택한 exact-index normalization은 삼각형 좌표를 보존하며 열린 표면을 막거나 방향을 수정하지 않는다. 원본·전처리 배열 예산을 예약하고 남은 예산으로 각 블록을 계산한다. 호출자가 반환된 모든 블록을 메모리에 보관하는 사용 방식은 예산 범위 밖이다.

`write_mask_tiles`는 NPZ 블록과 hash가 있는 manifest를 임시 디렉터리에 작성한 뒤 전부 성공했을 때 새 출력 디렉터리로 게시한다. 기존 결과는 덮어쓰지 않는다. 실패한 실행의 임시 결과와 자체 lock을 정리한다. 완료 manifest에서 누락된 블록은 배경이다. 저장 데이터의 무결성을 대조하려면 반환한 manifest hash를 별도로 보관해야 한다.

[Docker 검사](evidence/voxel-tiles-tests.xml): 26개 PASS. 세 가지 블록 크기에서 기존 dense 출력과 foreground·해부 라벨·instance·출처·겹침 수·전체 membership 배열 일치, 좌표 보존 인덱스 정리, 외부 열린 표면 거부, 메모리 제한, 파일 hash·재구성 일치 및 실패 시 미게시를 확인했다.

## 사례·CLI 및 읽기 연결

`case_tiles.export_case_tiles`는 등록된 사례 표면을 희소 출력에 연결한다. 선택한 part, 제외한 part, 사례 revision, 형상 hash, part-instance 매핑과 해부 라벨 registry를 manifest에 기록한다. 기본값은 모든 등록 표면이며, 일부를 선택하면 제외 목록을 남긴다. 열린 표면이나 미반영 병변을 조용히 생략하지 않는다.

CLI: `python -m vv_toolbox.case_tiles CASE_JSON OUTPUT_DIR --spacing-mm 1 --tile-size 32 --max-mib 256`. 해상도는 호출자가 명시하며 새 디렉터리에만 출력한다.

`iter_saved_tiles`는 외부에 보관한 manifest hash와 모든 블록 파일 hash를 확인한 후 블록을 읽는다. 반복 좌표/파일, grid 배치, 배열 shape·dtype를 검사하고 압축 해제 메모리를 제한한다. 뒤쪽 블록이 손상돼도 앞쪽 블록을 먼저 전달하지 않는다.

[사례·읽기 회귀](evidence/case-tiles-tests.xml): 18개 PASS. 사례/형상 식별값 보존, source 출처 유지, 마지막 블록 변조 선행 거부, 잘못된 선택 미게시 및 압축 해제 예산을 확인했다.

## 실제 원본 Atlas 실행

`scripts/run_atlas_sparse_masks.py`로 고정된 원본 표면 517개 전체를 1 mm, 32³ 블록, 알고리즘 예산 256 MiB로 실행 완료했다. 범위는 이전 브라우저에서 내려받은 원본 사례이며 추정 경부 연결은 제외된다. 전체 성공 후 출력 디렉터리를 게시했다.

- 결과 기록: `docs/evidence/atlas-sparse-mask-run.json`
- 출력: `exports/atlas-source-masks-1mm/`
- 실행 시간과 프로세스 최대 RSS를 별도 기록한다. 프로세스 RSS는 사례 JSON·라이브러리·호출자 입력을 포함하여 알고리즘 예산과 같지 않다.
- 생성·파일 무결성 판정: PASS. 1,025개 블록, 전경 453,552복셀, 실행 33,788.286초, 최대 RSS 576,905,216바이트다. 해부학적 수용은 NOT RUN이다.

추정 경부 연결 체적 구성과 전체 해부 구간 라벨은 미완료다. 이 구현은 입력 표면의 자기 교차나 해부학적 연결을 검증하지 않는다.

추정 경부 연결은 [별도 체적 후보](ESTIMATED_NECK_VOLUMES.md) 4개를 만들었으며 원본 517개 실행에는 추가하지 않았다. 블록 저장 도중 실제 파일 쓰기 실패를 주입한 검사에서도 임시 결과와 lock이 정리되는 것을 확인했다([12개 관련 회귀 PASS](evidence/neck-volume-and-tile-rollback-tests.xml)).

## 전체 저장 결과 재읽기

[별도 재검사](evidence/atlas-mask-reload.json)는 모든 1,025개 블록을 다시 읽어 manifest/파일 해시, 원본 517개와 geometry hash·edge ID 대응, 타일 좌표 변환, 배열과 membership의 일관성을 확인했다. 전경 453,552복셀, 여러 표면에 속하는 복셀 82,066개다. 원본 표면 간 겹침을 삭제하지 않고 membership에 보존한다.

해부학적 라벨은 전경 전체 453,552복셀에서 0(미확인)이다. part instance는 보존됐지만 ACA/MCA 구간 라벨이 완성된 출력은 아니다. `FJ1707M`, `FJ1708M`, `FJ3420`은 전체 입력에 포함됐으나 1 mm 복셀 중심 샘플이 하나도 해당하지 않았다. 얇은 형상의 누락 여부·해상도 적절성은 별도 검사 대상이며 파일 무결성 PASS로 해소되지 않는다.

읽기 모듈은 각 블록의 foreground·겹침 수·최소 ID 소유자·해부 라벨 충돌·출처 비트가 membership과 일치하는지 확인한다. 해시가 일치해도 채널 의미가 서로 모순되면 거부한다. [관련 테스트 20개](evidence/tile-semantic-tests.xml)가 통과했다. 기하 정확도·해부 연결·전 구간 라벨은 아직 NOT RUN/미완료다.

## 복셀이 없는 세 원본의 해상도 검사

`scripts/inspect_zero_sampled_parts.py`는 동일 사례 revision·형상 hash를 확인하고, 기존 전체 격자의 원점을 유지한 국소 영역에서 1 / 0.5 / 0.25 mm 중심 샘플링을 수행한다. 작은 격자의 샘플 위치는 큰 격자의 위치를 포함한다. 인덱스 정규화만 수행하며 원본 삼각형 좌표를 바꾸지 않는다.

| 원본 part | 1 mm 복셀 | 0.5 mm 복셀 | 0.25 mm 복셀 |
|---|---:|---:|---:|
| FJ1707M | 0 | 9 | 78 |
| FJ1708M | 0 | 5 | 34 |
| FJ3420 | 0 | 11 | 86 |

[실행 기록](evidence/zero-sample-resolution.json): 세 원본 모두 1 mm 전체 출력의 0복셀을 재현했고, 더 촘촘한 격자에서는 검출됐다. 이 세 항목의 누락은 격자 중심 샘플링 해상도로 설명된다. 0.25 mm에서 체적이 수렴했거나 모든 얇은 분지가 보존된다는 증거는 아니다. 전체 결과를 교체하거나 앱의 기본 해상도를 변경하지 않았으며, 출력 정책에는 미검출 part 목록과 해상도 한계를 유지해야 한다.

신규 출력의 manifest와 CLI 반환에는 `sampling_summary`를 포함한다. 모든 입력 instance의 source reference와 membership 복셀 수, 0복셀 instance ID를 기록한다. 겹치는 혈관도 소유자 채널과 무관하게 각각 집계한다. `WRITTEN`은 저장 성공이며, `ZERO_SAMPLED_INSTANCES`가 함께 있으면 입력 중 표현되지 않은 항목이 있다는 뜻이다. `ALL_INSTANCES_SAMPLED`도 형상 정확도 판정은 아니다. 기존 저장 결과의 manifest와 해시는 변경하지 않는다.

[Docker 회귀 22개 PASS](evidence/tile-sampling-summary-tests.xml): 겹친 비소유 혈관의 집계, 얇은 형상의 0복셀 경고, 빈 출력의 전체 입력 추적, 세밀한 격자에서 검출 복구 및 기존 저장·읽기 검사를 포함한다.
