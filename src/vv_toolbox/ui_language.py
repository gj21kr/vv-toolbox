"""Local UI language controls. Model data and stored evidence are never translated."""
import json

# Each pair is English, Korean. Exact UI copy only: no vessel-name guessing.
COPY = [
('Loaded source-bound drafts. No reviewed boundary positions.','원본에 연결된 초안을 불러왔습니다. 검토 완료된 경계 위치는 없습니다.'),
('Source & reconstruction details','출처 및 재구성 상세'),('Title','제목'),('License','라이선스'),('Coordinates','좌표'),('Units','단위'),('Original atlas source','원본 Atlas 출처'),
('BodyParts3D 4.0 · shared-coordinate vascular atlas','BodyParts3D 4.0 · 공통 좌표 혈관 Atlas'),
('CC BY 4.0 per current official distribution license (2025-02-27)','공식 배포 라이선스에 따른 CC BY 4.0 (2025-02-27)'),
('One original BodyParts3D coordinate frame; no individual translation, rotation, scaling, registration or vessel fusion','단일 원본 BodyParts3D 좌표계이며 개별 이동·회전·크기 조절·정합·혈관 융합을 적용하지 않았습니다'),
('mm assumed from atlas convention; OBJ units not encoded','Atlas 관례에 따라 mm로 가정하며 OBJ에 단위는 기록되어 있지 않습니다'),
('Select an atlas vessel to adjust its radius, tortuosity and torsion. Changes are local derived geometry; original atlas parts remain recoverable.','Atlas 혈관을 선택해 반경·굴곡·비틀림을 조절하세요. 변경은 로컬 파생 형상이며 원본 Atlas 부위는 복원할 수 있습니다.'),
('Standalone reference arch · read-only','독립 대동맥궁 참조 · 읽기 전용'),
('BodyParts3D source atlas with separately marked estimated missing vessels. Organ context and estimated additions can be hidden independently.','누락 혈관의 추정 보충을 별도로 표시한 BodyParts3D 원본 Atlas입니다. 장기 참조와 추정 보충 형상은 각각 숨길 수 있습니다.'),
('Red arteries · blue veins. Heart context is a separate translucent structure. Visibility changes do not move atlas parts.','빨강 동맥 · 파랑 정맥. 심장 참조는 별도의 반투명 구조물입니다. 표시 변경은 Atlas 부위를 이동시키지 않습니다.'),
('Atlas workspace is not active. Reload to load the Atlas.','Atlas 작업 공간이 활성화되지 않았습니다. 다시 불러와 Atlas를 여세요.'),
('Literature reference · junctions','문헌 참조 · 접합부'),('Spatial candidates · unverified','공간적 후보 · 미검증'),('Centerline extraction details','중심선 추출 상세'),
('M1/M2/P1 have source-name mappings. Other segments require anatomical boundary annotation.','M1/M2/P1은 원본 명칭 대응이 있습니다. 다른 구간은 해부학적 경계 주석이 필요합니다.'),
('Save vessel edits','혈관 편집 저장'),('Reload saved edits','저장된 편집 불러오기'),
('Save all vessel adjustments locally. Reload replaces current adjustments and restores their 3D shapes and centerlines. Original Atlas files are preserved.','모든 혈관 조절값을 로컬에 저장합니다. 다시 불러오면 현재 조절값을 교체하고 3D 형상과 중심선을 복원합니다. 원본 Atlas 파일은 보존됩니다.'),
('Display options','표시 옵션'),('Camera focus','카메라 초점'),('Left MCA','좌측 MCA'),('Right MCA','우측 MCA'),('Left ACA','좌측 ACA'),('Right ACA','우측 ACA'),('Left PCA','좌측 PCA'),('Right PCA','우측 PCA'),
('User-authorized estimates, not recovered original anatomy. Estimated venous display does not resolve missing original upper-source coverage. Subclavian insertion is a fitted superior section, not a source-annotated vertebral ostium.','사용자가 허용한 추정이며 복구된 원본 해부 구조가 아닙니다. 추정 정맥 표시는 상부 원자료의 결손을 해결하지 않습니다. 쇄골하동맥 연결은 맞춘 상부 단면이며 원본에 주석된 척추동맥 기시부가 아닙니다.'),
('Original atlas geometry is retained. Selected-vessel modifications update the derived display and centerline graph; restore removes the selected override. Estimated missing vessels retain their provenance.','원본 Atlas 형상은 유지됩니다. 선택 혈관의 편집은 파생 표시와 중심선 그래프를 갱신하며 복원은 해당 변경을 제거합니다. 추정 보충 혈관의 출처 표시는 유지됩니다.'),
('Source-bound coordinates. Drafts do not split vessels or certify anatomical boundaries.','원본에 연결된 좌표입니다. 초안은 혈관을 분할하거나 해부학적 경계를 확정하지 않습니다.'),
('Side · artery · transition','좌우 · 동맥 · 경계'),('Unresolved reason','미확인 사유'),('Review notes','검토 메모'),('Evidence references · one per line','근거 참조 · 줄마다 하나'),
('Candidate XYZ · native source coordinates','후보 XYZ · 원본 좌표'),
('Leave all XYZ fields empty for no candidate. Coordinates remain an unreviewed draft; the authoritative boundary stays unresolved.','후보가 없으면 모든 XYZ 입력을 비워 두세요. 좌표는 미검토 초안이며 기준 경계는 미확인 상태로 유지됩니다.'),
('Show source corpus callosum and insula','원본 뇌량과 섬엽 표시'),('ACom remains in the artery layer.','ACom은 동맥 계통에 유지됩니다.'),
('Source coordinate definition','원본 좌표 정의'),(': mm; +X left, +Y posterior, +Z superior. Native origin, not a DICOM registration.',': mm; +X 좌측, +Y 후방, +Z 상방. 원본 기준점이며 DICOM 정합 좌표가 아닙니다.'),
('Show saved candidate in 3D','저장된 후보를 3D에 표시'),('Save draft','초안 저장'),('Reload saved drafts','저장된 초안 불러오기'),('Load saved drafts to begin.','저장된 초안을 불러와 시작하세요.'),
('5 · Source case data','5 · 원본 사례 데이터'),('Label a saved case →','저장 사례에 라벨 지정 →'),
('No case data loaded. The displayed Atlas is separate.','불러온 사례 데이터가 없습니다. 표시된 Atlas는 별개입니다.'),
('Prepare source case','원본 사례 준비'),('Reload saved data','저장된 데이터 불러오기'),('Save case data','사례 데이터 저장'),('Download case JSON','사례 JSON 다운로드'),('Refresh case status','사례 상태 갱신'),
('Right external iliac / testicular artery','우측 외장골·고환동맥'),
('Right MCA aneurysm · review required','우측 MCA 동맥류 · 검토 필요'),('Right MCA junction refinement · review required','우측 MCA 접합부 개선 · 검토 필요'),('Right MCA surface correction · review required','우측 MCA 표면 보정 · 검토 필요'),
('Return to Atlas','Atlas로 돌아가기'),('Show centerlines','중심선 보기'),('Show the original of the same vessel','같은 혈관의 원본 보기'),
('Candidate version and display scope','후보 버전과 표시 범위'),('Femoral–carotid access route inspection','대퇴–경동맥 접근 경로 검사'),
('Selected vessel radius','선택 혈관 반경'),('Junction transition distance (mm)','접합 전이 거리 (mm)'),('Preview radius','반경 미리보기'),
('Apply candidate','후보 적용'),('Cancel preview','미리보기 취소'),('Undo application','적용 되돌리기'),
('Select a vessel part, then calculate a radius candidate.','혈관 부분을 선택한 뒤 반경 후보를 계산하세요.'),
('Experimental synthetic editing that preserves the source. Junction boundaries are fixed. Neighbor collisions and centerline containment require reinspection. Edit files record source identity and edit order, and are recalculated from the same source when loaded.','원본을 보존하는 실험적 합성 편집입니다. 접합 경계는 고정합니다. 주변 충돌과 중심선 포함은 재검사가 필요합니다. 편집 파일에는 원본 식별 정보와 편집 순서를 기록하며, 불러올 때 같은 원본에서 재계산합니다.'),
('Save edit file','편집 파일 저장'),('Load edit file','편집 파일 불러오기'),('Save current geometry and graph (for inspection)','현재 형상·그래프 저장 (검사용)'),
('Failed and unknown inspection states are saved as well. This is not approved generation data.','검사 실패·미확인 상태도 함께 저장합니다. 승인된 생성 데이터가 아닙니다.'),
('Interval size preview','구간 크기 미리보기'),
('Select a vessel with a single centerline segment. Multi-branch editing is not yet supported.','단일 중심선 구간을 가진 혈관을 선택하세요. 다중 분기 편집은 아직 지원하지 않습니다.'),
('Distances in mm are measured from the first interior cross-section. Inspect the candidate before applying it to the current scene. Original files are preserved.','첫 내부 단면부터의 거리(mm)입니다. 후보를 검사한 뒤 현재 장면에 적용할 수 있습니다. 원본 파일은 유지됩니다.'),
('Start distance (mm)','시작 거리 (mm)'),('End distance (mm)','끝 거리 (mm)'),('Central scale factor','중앙 크기 배율'),
('Maximum vertex displacement (mm)','최대 정점 이동 (mm)'),('Cross-section scale tolerance','단면 배율 허용오차'),
('Scale and inspection conditions are user-defined, not regional disease presets.','배율과 검사 조건은 사용자가 지정합니다. 부위별 질환 프리셋이 아닙니다.'),
('Inspect and preview','검사하고 미리보기'),('Undo last interval edit','마지막 구간 편집 되돌리기'),
('Download interval edit session','구간 편집 세션 다운로드'),('Load interval edit session','구간 편집 세션 불러오기'),
('Session files store multiple interval edits in order. Undo all current interval edits and load using the same baseline vessel parameters. Whole-case generation is not yet connected.','세션 파일은 여러 구간 편집을 순서대로 저장합니다. 현재 구간 편집을 모두 되돌린 후 같은 기준 혈관 파라미터에서 불러오세요. 전체 사례 생성은 아직 연결되지 않았습니다.'),
('Reopen saved candidate','저장된 후보 다시 열기'),('Show original','원본 보기'),('Download candidate','후보 다운로드'),
('Reinspect current scene','현재 장면 재검사'),('Apply to scene after reinspection','재검사 후 장면에 적용'),
('Drag or use arrow keys to rotate. Neighbor vessels are not shown in this small preview. Full collision inspection and anatomical acceptance are separate.','드래그 또는 방향키로 회전 · 주변 혈관은 이 작은 미리보기에 표시하지 않습니다. 전체 충돌·해부학적 승인은 별도입니다.'),
('Prepare source paths only, or include current arterial surfaces and edit history. Structures without matching paths are listed as missing. Loading a case does not change the 3D scene.','원본 경로만 준비하거나, 현재 동맥 표면과 편집 기록을 함께 담을 수 있습니다. 대응 경로가 없는 구조는 누락 목록에 기록됩니다. 사례를 불러와도 3D 장면은 바뀌지 않습니다.'),
('Prepare case from current arterial surfaces and edits','현재 동맥 표면·편집으로 사례 준비'),
('Femoral–anterior circulation union · review candidate','대퇴–전방순환 통합 · 검토 후보'),
('Femoral bend 0.25 mm · inspection candidate','대퇴 굴곡 0.25 mm · 검사 후보'),
('Right MCA surface correction candidate','우측 MCA 표면 보정 후보'),('Right MCA junction inspection candidate','우측 MCA 접합부 검사 후보'),('Right MCA aneurysm synthetic candidate','우측 MCA 동맥류 합성 후보'),
('Right external iliac / testicular artery synthetic candidate','우측 외장골·고환동맥 합성 후보'),
('Left carotid · lumen union candidate','좌측 경동맥 · 내강 결합 후보'),('Right carotid · lumen union candidate','우측 경동맥 · 내강 결합 후보'),
('Eight cerebral vessels · source comparison','뇌혈관 8개 · 원본 비교'),('Eight cerebral vessels · endpoint-preserving correction candidate','뇌혈관 8개 · 끝단 보존 보정 후보'),
('Femoral–anterior circulation · neck mesh refinement candidate','대퇴–전방순환 · 목 메시 개선 후보'),
('Synthetic surface separate from source · distal ACA/MCA branches and segment labels are incomplete','원본과 분리된 합성 표면 · 전체 ACA/MCA 원위 분지와 구간 라벨은 미완성'),
('Bend inspection candidate · cannot apply · radius preservation and anatomical acceptance unknown','굴곡 검사 후보 · 적용 불가 · 반경 보존과 해부학적 수용 미확인'),
('Single MCA lesion candidate generated separately from the original Atlas','원래 Atlas와 별도로 생성한 단일 MCA 병변 후보'),
('Synthetic candidate showing only the complete paths of the two selected vessels','선택한 두 혈관의 전체 경로만 표시하는 합성 후보'),
('Synthetic surface joining two source carotid parts and an estimated neck connection','원본 경동맥 두 부분과 추정 목 연결부를 결합한 합성 표면'),
('The same eight original surfaces','동일한 8개 원본 표면'),('Eight synthetic surfaces with original endpoints and contact faces fixed','원본 끝단과 접촉면을 고정한 8개 합성 표면'),
('Source branches protected · estimated right neck interior mesh rebuilt · anatomical acceptance and context inspection are separate','원본 분지 보호 · 추정 우측 목 내부 메시 재구성 · 해부학적 수용 및 주변 검사 별도'),
('Read-only · original Atlas preserved','읽기 전용 · 원본 Atlas 보존'),('Read-only · original files preserved','읽기 전용 · 원본 파일 보존'),('Read-only · red arteries · original Atlas preserved','읽기 전용 · 빨간 동맥 · 원본 Atlas 보존'),
('Deformed coordinates have synthetic provenance. Junction smoothness and anatomical acceptance: unknown.','변형 좌표는 합성 출처입니다. 접합 매끄러움·해부학적 수용: 미확인.'),
('Four access-route graphs, anatomical segments and junction smoothness: unknown.','네 접근 경로 그래프·해부 구간·접합 매끄러움: 미확인.'),
('Centerline containment and junction smoothness require reinspection. Anatomical connectivity: unknown.','중심선 포함·접합 매끄러움: 재검사 필요. 해부학적 연결: 미확인.'),
('Junction smoothness and anatomical connectivity: unknown.','접합 매끄러움과 해부학적 연결: 미확인.'),
('Centerline/radius consistency and anatomical acceptance: unknown.','중심선·반경 일치와 해부학적 수용: 미확인.'),
('Original-surface collision and clinical validation: NOT RUN.','원본 표면 충돌·임상 검증: NOT RUN.'),
('Whole-Atlas collision and self-intersection: NOT RUN. Anatomical validation: UNKNOWN.','전체 Atlas 충돌·자기 교차: NOT RUN. 해부학 검증: UNKNOWN.'),
('Single closed surface · edited surface provenance comparison NOT RUN.','단일 폐곡면 · 변경 표면의 출처 대조 미실행.'),
('Vessel selection','혈관 선택'),('Select the vessel to modify','편집할 혈관을 선택하세요'),('Search vessels to modify','편집할 혈관 검색'),
('Name, ID or abbreviation · e.g. left ACom','혈관명, ID 또는 약어 · 예: left ACom'),('Both sides','양쪽'),('Left','좌측'),('Right','우측'),('Cerebral side','뇌혈관 좌우'),('Cerebral segment','뇌혈관 구간'),('All vessel segments','전체 혈관 구간'),
('Saved-edit status unavailable.','저장된 편집 상태를 확인할 수 없습니다.'),('Restoring saved vessel shapes…','저장된 혈관 형상 복원 중…'),('Saving vessel adjustments…','혈관 조절값 저장 중…'),
('Could not update saved edits','저장된 편집을 갱신하지 못했습니다'),('Vessel adjustments saved locally.','혈관 조절값을 로컬에 저장했습니다.'),('Saved adjustments restored in 3D and centerlines.','저장된 조절값을 3D와 중심선에 복원했습니다.'),
('Model information','모델 정보'),('Interactive 3D vessel model','대화형 3D 혈관 모델'),
('BodyParts3D · shared-coordinate atlas','BodyParts3D · 공통 좌표 Atlas'),
('Red arteries · blue veins · translucent organ context.','빨강 동맥 · 파랑 정맥 · 반투명 장기 참조.'),
('Shape edits are illustrative; junction continuity and collisions are not validated.','형상 편집은 설명용입니다. 접합 연속성과 충돌은 검증되지 않았습니다.'),
('Building initial anatomy…','초기 해부 모델 생성 중…'),
('Original image-derived reference surface and source paths.','원본 영상 기반 참조 표면과 원본 경로입니다.'),
('Standalone reference; not merged with the synthetic body.','독립 참조이며 합성 전신 모델과 병합되지 않았습니다.'),
('Clinical validation: NOT RUN.','임상 검증: NOT RUN.'),('SYNTHETIC / ILLUSTRATIVE','합성 / 설명용'),
('Three separate circulation layers. Undirected arterial route; not blood flow. All tabs share this workspace.','서로 분리된 세 순환 계통입니다. 무방향 동맥 경로이며 혈류가 아닙니다. 모든 탭이 이 작업 공간을 공유합니다.'),
('Choose a label…','라벨을 선택하세요…'),('Replace this case? Current changes have not been downloaded.','이 사례를 교체할까요? 현재 변경 사항을 아직 다운로드하지 않았습니다.'),
('Current case and edit history kept.','현재 사례와 편집 이력을 유지했습니다.'),('Current case kept.','현재 사례를 유지했습니다.'),
('Enter at least one full-edge evidence reference.','구간 전체를 뒷받침하는 근거를 하나 이상 입력하세요.'),
('Label applied to the copy. Download to keep it. Anatomical acceptance remains UNKNOWN.','복사본에 라벨을 적용했습니다. 보관하려면 다운로드하세요. 해부학적 수용은 UNKNOWN입니다.'),
('Checking original surface…','원본 표면 검사 중…'),('Inspection identity mismatch','검사 대상 식별자가 일치하지 않습니다'),
('Editing the wall and centerline and checking connected paths… The current case is preserved until the result is verified.','벽·중심선 변경과 연결 경로 검사 중… 현재 사례는 결과가 확인될 때까지 유지됩니다.'),
('Comparing stored context inspection records linked to this case…','사례와 연결된 기존 주변 검사 기록 대조 중…'),
('Checking surrounding geometry and inspection inputs…','주변 형상과 검사 입력 확인 중…'),
('Inspection request failed','검사 요청 실패'),('The inspection case has changed.','검사 대상 사례가 달라졌습니다.'),
('Inspection interrupted. It will not restart automatically.','검사가 중단되었습니다. 자동 재실행하지 않습니다.'),
('Could not load the completed result. Press resume again.','완료 결과를 불러오지 못했습니다. 다시 이어 보기를 누르세요.'),
('The result does not match the inspection case.','검사 결과의 사례가 일치하지 않습니다.'),
('The case changed, so the result was not applied.','사례가 변경되어 결과를 적용하지 않았습니다.'),
('Shape change exceeds displacement bound','형상 변경이 이동 허용값을 초과합니다'),
('Invalid shape parameters','형상 파라미터가 유효하지 않습니다'),
('Finite numeric shape parameters required','유한한 숫자 형상 파라미터가 필요합니다'),
('Bend direction must have a component perpendicular to chord','굴곡 방향은 양 끝을 잇는 축에 수직인 성분을 포함해야 합니다'),
('Shape self-contact not cleared','변경 형상의 자기 접촉 검사를 통과하지 못했습니다'),
('Shape change degenerates or reverses triangles','형상 변경으로 삼각형이 퇴화하거나 방향이 뒤집힙니다'),
('Shape change loses closed positive volume','형상 변경 후 닫힌 양의 체적을 유지하지 못합니다'),
('Deformed centerline containment not cleared','변형된 중심선의 내강 포함 검사를 통과하지 못했습니다'),
('Branched or cyclic source needs a branch-aware field','분기하거나 순환하는 원본은 분기를 고려한 변형이 필요합니다'),
('Source has disconnected components','원본에 서로 분리된 구간이 있습니다'),
('Source requires an open connected chain','원본은 열린 연결 경로여야 합니다'),
('Source chain endpoints must coincide exactly','원본 구간의 연결 끝점이 정확히 일치해야 합니다'),
('Snapshot revision mismatch','사례 snapshot의 revision이 일치하지 않습니다'),
('No original vessel mapping is available.','원본 혈관 대응 정보가 없습니다.'),
('All jointly edited segments need centerlines.','공동 편집할 모든 구간의 중심선이 필요합니다.'),
('All segments must belong to one registered surface with face ownership.','모든 구간이 면 소유권이 있는 동일한 등록 표면에 속해야 합니다.'),
('Joint shape editing is not supported on surfaces with lesions.','병변이 있는 표면의 공동 형상 편집은 지원하지 않습니다.'),
('Select a vessel to check editing availability.','혈관을 선택해 편집 가능 여부를 확인하세요.'),
('Vessel display','혈관 표시'),('Veins','정맥'),('Both','둘 다'),
('1 · Select a vessel','1 · 혈관 선택'),('2 · Vessel relationships','2 · 혈관 연결 관계'),('3 · Modify selected vessel','3 · 선택 혈관 편집'),
('Browse matching vessels','검색된 혈관 목록'),('Source atlas structures','원본 Atlas 구조물'),('No structure selected','선택한 구조물이 없습니다'),
('Selected vessel · both ends','선택 혈관 · 양 끝'),('Apply modification','편집 적용'),('Restore original','원본 복원'),
('Shared anatomical coordinates','공통 해부 좌표'),('ATLAS REFERENCE','ATLAS 참조'),('Atlas structures','Atlas 구조물'),
('Source atlas parts in their original shared coordinates. This is a structure list, not an inferred vessel-connectivity graph.','원본 공통 좌표에 있는 Atlas 구조물입니다. 이 목록은 추정된 혈관 연결 그래프가 아닌 구조물 목록입니다.'),
('Select a vessel…','혈관을 선택하세요…'),('Vessel name or atlas ID','혈관명 또는 Atlas ID'),
('Select a vessel from the atlas list or graph.','Atlas 목록이나 그래프에서 혈관을 선택하세요.'),
('Waiting for the current centerline graph.','현재 중심선 그래프를 기다리고 있습니다.'),
('This structure has no extracted centerline and cannot be modified.','추출된 중심선이 없어 이 구조물을 편집할 수 없습니다.'),
('Local modification applied to this vessel.','이 혈관에 로컬 편집을 적용했습니다.'),
('Original geometry · adjustments are relative to this baseline.','원본 형상 · 이 기준에 상대적으로 조절합니다.'),
('Select a vessel above to view neighboring vessel candidates.','위에서 혈관을 선택하면 이웃 혈관 후보를 볼 수 있습니다.'),
('Inspect a synthetic candidate and its inspection state separately from the original Atlas.','원본 Atlas와 분리된 합성 후보와 검사 상태를 확인합니다.'),
('View synthetic candidate','합성 후보 보기'),('Switch while preserving Atlas selection and edits.','Atlas의 선택과 수정 내용을 유지한 채 전환합니다.'),
('Femoral → cerebral','대퇴 → 뇌혈관'),('Connecting…','연결 중…'),
('Graph & vessel modification','그래프 및 혈관 편집'),('Atlas reference','Atlas 참조'),
('Branch graph','분지 그래프'),('Select a layer and vessel to edit its shape or connections.','혈관 계통과 혈관을 선택해 형상이나 연결을 편집하세요.'),
('Anatomy source','해부 모델 출처'),('Authored schematic · editable','작성된 개략 모델 · 편집 가능'),
('Standalone reference arch · unavailable','독립 대동맥궁 참조 · 사용 불가'),
('BodyParts3D · shared-coordinate atlas','BodyParts3D · 공통 좌표 Atlas'),('Atlas provenance','Atlas 출처'),
('Structures retain their shared atlas coordinates. One anatomical atlas is not a population model or a verified vascular lumen.','구조물은 공통 Atlas 좌표를 유지합니다. 단일 Atlas는 인구집단 모델이나 검증된 혈관 내강 모델이 아닙니다.'),
('Reference provenance & measurements','참조 출처 및 측정'),('No reference has been registered.','등록된 참조가 없습니다.'),
('Vessel layer','혈관 계통'),('Arteries','동맥'),('Systemic veins','체정맥'),('Hepatic portal veins','간문맥'),('Portal veins','문맥'),
('Heart / organ context','심장 / 장기 참조'),('Estimated missing vessels','추정 보충 혈관'),
('Missing neck connections and cerebral veins are estimated additions; not validated anatomy.','누락된 목 연결과 뇌정맥은 추정 보충 형상이며 검증된 해부 구조가 아닙니다.'),
('All arteries are red and veins are blue, including estimated additions. Estimated vessels retain their labels. Uncheck to inspect the original atlas alone.','추정 보충 혈관을 포함해 동맥은 빨강, 정맥은 파랑입니다. 추정 혈관은 표시를 유지합니다. 선택을 해제하면 원본 Atlas만 볼 수 있습니다.'),
('Reconstruction limits','재구성 한계'),('Named estimated venous segments (authored topology, not recovered source vessels):','추정 정맥 구간 (작성된 연결이며 원본에서 복구한 혈관이 아님):'),
('Inter-circuit clearance: awaiting screening.','계통 간 간격: 검사 대기.'),('Centerline/radius estimate · not surface or anatomical validation.','중심선/반경 추정 · 표면 또는 해부학적 검증 아님.'),
('Clearance screening details','간격 검사 상세'),
('Centerline/radius screening only. This is not an exact surface-intersection test or anatomical validation. Negative clearance indicates a potential overlap.','중심선/반경 기반 검사입니다. 정확한 표면 교차 검사나 해부학적 검증이 아닙니다. 음수 간격은 겹침 가능성을 뜻합니다.'),
('Red arteries · blue systemic veins · light blue portal veins. Portal and systemic veins remain separate across the unmodeled liver exchange.','빨강 동맥 · 파랑 체정맥 · 연파랑 문맥. 모델링하지 않은 간 교환 영역에서 문맥과 체정맥은 분리됩니다.'),
('All regions','전체 부위'),('Cerebral','뇌혈관'),('Aortic arch','대동맥궁'),('Abdominal','복부'),('Femoral','대퇴'),
('A1–A3, M1–M3 and P1–P3 are estimated schematic subdivisions. Landmark-based annotation has not been validated.','A1–A3, M1–M3, P1–P3는 추정된 개략 구간입니다. 해부 기준점 기반 주석은 검증되지 않았습니다.'),
('Atlas region','Atlas 부위'),('Whole body','전신'),('Head & neck','머리 및 목'),('Thorax','흉부'),('Abdomen','복부'),('Pelvis & femoral','골반 및 대퇴'),
('Find a structure','구조물 검색'),('Approximate spatial filter using source bounds. Select a structure to highlight and focus it in 3D.','원본 경계를 이용한 근사 공간 필터입니다. 구조물을 선택하면 3D에서 강조하고 확대합니다.'),
('Atlas centerlines','Atlas 중심선'),('Centerline extraction not available.','중심선 추출을 사용할 수 없습니다.'),
('Solid: within-part centerlines derived from meshes (or explicitly estimated vessels). Dashed: unverified proximity candidates between parts. These are not confirmed anatomical connections.','실선: 메시에서 얻은 부위 내 중심선 또는 명시적 추정 혈관. 점선: 부위 사이의 미검증 근접 후보이며 확인된 해부학적 연결이 아닙니다.'),
('Download centerline graph JSON','중심선 그래프 JSON 다운로드'),('Atlas vessel modification','Atlas 혈관 편집'),('Select an atlas vessel','Atlas 혈관 선택'),
('Radius multiplier','반경 배율'),('Tortuosity adjustment','굴곡 조절'),('Torsion adjustment (degrees)','비틀림 조절 (도)'),
('Apply atlas modification','Atlas 편집 적용'),('Restore selected original','선택한 원본 복원'),
('Edits create a local derived shape; restore returns this vessel to its original geometry. Endpoint and junction preservation is approximate. Collisions and anatomical validity are not validated.','편집은 로컬 파생 형상을 만들며 복원은 원래 형상으로 되돌립니다. 끝점과 접합부 보존은 근사적입니다. 충돌과 해부학적 타당성은 검증되지 않았습니다.'),
('Selected vessel','선택한 혈관'),('Choose a vessel','혈관을 선택하세요'),('Tortuosity','굴곡'),('Apply vessel shape','혈관 형상 적용'),('Reset vessel','혈관 초기화'),
('Standalone reference geometry is read-only. It is not joined to the authored whole-body network.','독립 참조 형상은 읽기 전용이며 작성된 전신 혈관망에 연결되지 않습니다.'),
('Arterial branch variations','동맥 분지 변이'),('Arch connections','대동맥궁 연결'),('Standard arch','표준 대동맥궁'),
('Shared brachiocephalic / left carotid origin','팔머리동맥 / 좌측 경동맥 공통 기시'),('Left carotid from brachiocephalic','팔머리동맥에서 분지하는 좌측 경동맥'),('Left vertebral from arch','대동맥궁에서 분지하는 좌측 척추동맥'),
('Arch shape preset','대동맥궁 형상 프리셋'),('Type I illustration','Type I 예시'),('Type II illustration','Type II 예시'),('Type III illustration','Type III 예시'),
('Custom degree','직접 조절'),('Requested arch depth','대동맥궁 깊이 설정'),
('Continuous synthetic construction ratio; presets illustrate types and do not classify clinical anatomy.','연속적인 합성 형상 비율입니다. 프리셋은 유형 예시이며 임상 해부 구조를 분류하지 않습니다.'),
('Left PCom','좌측 PCom'),('Right PCom','우측 PCom'),('Apply branch variation','분지 변이 적용'),('Venous variations','정맥 변이'),
('Inferior mesenteric vein drainage','하장간막정맥 배출 경로'),('Splenic vein','비장정맥'),('Superior mesenteric vein','상장간막정맥'),('Portal confluence','문맥 합류부'),
('Transverse sinus dominance','가로정맥굴 우세측'),('Balanced','균형'),('Left dominant','좌측 우세'),('Right dominant','우측 우세'),
('IMV changes portal connections. Dominance adjusts the synthetic cerebral sinus caliber.','IMV는 문맥 연결을 바꿉니다. 우세측 설정은 합성 뇌정맥굴의 굵기를 조절합니다.'),('Apply venous variation','정맥 변이 적용'),
('View & arterial route','보기 및 동맥 경로'),('Femoral access','대퇴 접근'),('Right femoral','우측 대퇴'),('Left femoral','좌측 대퇴'),('Cerebral destination','뇌혈관 도착점'),
('Focus','초점'),('Whole network','전체 혈관망'),('Femoral bifurcation','대퇴 분기부'),('Geometry','형상'),('Surface','표면'),('Centerlines','중심선'),('Update view','보기 갱신'),
('Workspace','작업 공간'),('All browser tabs share this model. Graph and surface update together after a rebuild.','모든 브라우저 탭이 이 모델을 공유합니다. 다시 생성하면 그래프와 표면이 함께 갱신됩니다.'),
('Reset anatomy','해부 모델 초기화'),('Download graph JSON','그래프 JSON 다운로드'),('About this anatomy','해부 모델 정보'),('Building anatomy…','해부 모델 생성 중…'),
('Authored illustrative arteries, systemic veins and hepatic portal veins. The liver exchange between portal and systemic compartments is not a connecting vessel. Not patient anatomy, validated flow, catheter contact or clinical planning. Coral lines show the arterial undirected shortest route. Coordinates use mm.','작성된 설명용 동맥·체정맥·간문맥 모델입니다. 문맥과 체정맥 사이의 간 교환은 연결 혈관이 아닙니다. 환자 해부 구조, 검증된 혈류, 카테터 접촉 또는 임상 계획용이 아닙니다. 산호색 선은 동맥의 무방향 최단 경로이며 좌표 단위는 mm입니다.'),
('VV Toolbox · Saved case labels','VV Toolbox · 저장 사례 라벨'),('Saved case labels','저장 사례 라벨'),
('Load a case snapshot, select an edge, and declare its whole-edge access-vessel label. Download creates a separate file. The Atlas scene and files on the server are unchanged.','사례 snapshot을 불러와 구간을 선택하고 구간 전체의 접근 혈관 라벨을 지정하세요. 다운로드는 별도 파일을 만듭니다. Atlas 장면과 서버 파일은 변경되지 않습니다.'),
('Labels are operator declarations. They do not confirm anatomical boundaries. An atlas fragment is not necessarily a complete vessel.','라벨은 사용자가 지정한 정보이며 해부학적 경계를 확정하지 않습니다. Atlas 조각이 반드시 전체 혈관을 나타내지는 않습니다.'),
('Saved inspections: load a case.','저장된 검사 기록: 사례를 불러오세요.'),('Neighbor contact inspection details','주변 혈관 접촉 검사 상세'),
('Added and removed counts describe triangle contact pairs, not penetration volume or newly contacting vessels. Anatomical junctions require separate review.','추가·제거 수는 삼각형 접촉 쌍의 변화입니다. 실제 관통 부피나 새로 접촉한 혈관 수가 아닙니다. 정상 분지 여부는 별도 확인이 필요합니다.'),
('Neighbor vessel ID','상대 혈관 ID'),('Before','변경 전'),('After','변경 후'),('Added pairs','추가 쌍'),('Removed pairs','제거 쌍'),
('1 · Case snapshot (.json, up to 16 MB)','1 · 사례 snapshot (.json, 최대 16 MB)'),('2 · Find an edge','2 · 혈관 구간 검색'),('Matching edges','검색된 구간'),('No case loaded.','불러온 사례가 없습니다.'),
('Saved surface and centerlines','저장된 표면과 중심선'),('Registered surface','등록 표면'),('Centerlines (overlaid on surface)','중심선 (표면 위에 표시)'),('Reset view','보기 초기화'),('Focus selected edge','선택 구간 확대'),
('Drag or use arrow keys to rotate · Scroll to zoom · Click a line to select. Registered triangles are shown without reconstruction. Centerlines overlay the surface and may be behind it in 3D. Overlapping projections can be ambiguous—rotate and check the selected ID.','드래그나 방향키로 회전 · 스크롤로 확대 · 선을 클릭해 선택. 등록된 삼각형을 재구성 없이 표시합니다. 중심선은 표면 위에 표시되지만 3D에서는 뒤에 있을 수 있습니다. 투영이 겹치면 회전하여 선택한 ID를 확인하세요.'),
('Recorded connections at both ends','양 끝의 기록된 연결'),('These are shared nodes in the saved graph, not inferred contacts. First/last follow centerline point order and do not indicate blood-flow direction.','저장된 그래프의 공유 노드이며 추정 접촉이 아닙니다. 처음/마지막은 중심선 점 순서로 혈류 방향을 뜻하지 않습니다.'),
('Modify selected centerline','선택한 중심선 편집'),('Creates a separate synthetic case. Endpoints, endpoint chords and radii stay fixed. This does not check vessel-surface collisions or anatomical validity.','별도 합성 사례를 만듭니다. 끝점, 끝 구간의 현과 반경은 고정됩니다. 혈관 표면 충돌이나 해부학적 타당성을 검사하지 않습니다.'),
('Smoothing width (mm, 0.05–5)','평활화 폭 (mm, 0.05–5)'),('Maximum allowed displacement (mm, up to 10)','최대 이동 허용값 (mm, 최대 10)'),('Smooth in synthetic copy','합성 복사본에서 평활화'),
('These are numerical controls, not clinical ranges. Requires an open path with at least five points and no existing lesion on it.','수치 조절값이며 임상 범위가 아닙니다. 점이 5개 이상인 열린 경로가 필요하며 해당 경로에 기존 병변이 없어야 합니다.'),
('Vessel wall and centerline bend / rotation','혈관 벽·중심선 굴곡 / 회전'),
('Creates a separate inspection candidate. Bend is displacement, not a tortuosity target. Rotation uses the endpoint chord, not differential torsion.','별도 검사 후보를 만듭니다. 굴곡은 변위이며 tortuosity 목표값이 아닙니다. 회전은 양 끝을 잇는 축 기준이며 미분 torsion이 아닙니다.'),
('Bend displacement (mm)','굴곡 변위 (mm)'),('Bend direction (LPS)','굴곡 방향 (LPS)'),('X · Left','X · 좌측'),('Y · Posterior','Y · 후방'),('Z · Superior','Z · 상방'),
('Rotation about axis (°)','축 주위 회전 (°)'),('Fixed junction collar (mm)','접합 고정 거리 (mm)'),('Transition distance (mm)','전이 거리 (mm)'),('Maximum allowed displacement (mm)','최대 이동 허용값 (mm)'),
('Create wall and centerline candidate','벽·중심선 변경 후보 만들기'),('Load matching context inspection','이 사례에 대응하는 주변 검사 불러오기'),('Run / resume context inspection','새 주변 검사 실행 / 이어 보기'),
('A new inspection takes time. The server continues when this window closes. Reopen the same case to resume viewing.','새 검사는 시간이 걸립니다. 창을 닫아도 서버 작업은 계속됩니다. 같은 사례를 다시 열어 이어 볼 수 있습니다.'),
('Numerical inputs are experimental conditions. Neighbor contacts and radius consistency require separate checks and do not grant generation approval. Inspection may take several minutes.','수치 입력은 실험 조건입니다. 주변 혈관과의 접촉 및 반경 일치는 별도 검사이며, 생성 승인으로 처리하지 않습니다. 검사에 수 분이 걸릴 수 있습니다.'),
('Check selected centerline','선택한 중심선 검사'),('Compare the entire centerline with its declared original Atlas surface. This does not check vessel walls, radii, other vessels or anatomical correctness.','전체 중심선을 지정된 원본 Atlas 표면과 비교합니다. 혈관 벽, 반경, 다른 혈관 또는 해부학적 정확성을 검사하지 않습니다.'),
('Check against original surface','원본 표면과 비교 검사'),('NOT RUN · Select an edge to check.','NOT RUN · 검사할 구간을 선택하세요.'),
('3 · Whole-edge label','3 · 구간 전체 라벨'),('Evidence covering the entire selected edge (one reference per line)','선택 구간 전체를 뒷받침하는 근거 (줄마다 하나)'),
('Apply label to copy','복사본에 라벨 적용'),('Download current case','현재 사례 다운로드'),('Undo change','변경 취소'),('Redo change','변경 다시 적용'),
('Up to 20 changes can be undone in this tab.','이 탭에서 최대 20개 변경을 되돌릴 수 있습니다.'),('Choose a saved case to begin.','저장된 사례를 선택해 시작하세요.'),
('Name, side, or edge ID','혈관명, 좌우 또는 구간 ID'),('Language','언어'),
]

JS = r'''(()=>{
'use strict';
const pairs=__COPY__,key='vv-ui-language';
const normalize=s=>s.trim().replace(/\s+/g,' '),lookup=new Map();
for(const pair of pairs)for(const value of pair)lookup.set(normalize(value),pair);
let language='en';try{language=localStorage.getItem(key)||((navigator.language||'').startsWith('ko')?'ko':'en');}catch{}
if(!['en','ko'].includes(language))language='en';
const style=document.createElement('style');style.textContent=`
#vv-language{position:fixed;right:12px;top:10px;z-index:1000;display:flex;gap:3px;padding:3px;background:#10191f;border:1px solid #607985;border-radius:8px}
#vv-language button{width:auto;min-width:54px;margin:0;padding:5px 9px;font:14px system-ui;border:0;border-radius:5px;background:transparent;color:#e8eff3;cursor:pointer}
#vv-language button[aria-pressed=true]{background:#23665f;color:white}#vv-language button:focus-visible{outline:2px solid #73d7ce;outline-offset:2px}
body>header{padding-right:160px}`;document.head.append(style);
const toolbar=document.createElement('nav');toolbar.id='vv-language';toolbar.setAttribute('aria-label','Language');
for(const [code,label]of [['en','EN'],['ko','한국어']]){const b=document.createElement('button');b.type='button';b.textContent=label;b.lang=code;b.dataset.language=code;b.onclick=()=>setLanguage(code);toolbar.append(b);}
document.body.append(toolbar);
const originals=new WeakMap();
function translated(text){
 const value=normalize(text),pair=lookup.get(value);if(pair)return pair[language==='ko'?1:0];
 if(language==='en'){
  let m;
  if((m=value.match(/^(.+) · (반경 변형 후보|합성 후보|합성 보정 후보|원본 비교)$/)))return translated(m[1])+' · '+({'반경 변형 후보':'radius-edit candidate','합성 후보':'synthetic candidate','합성 보정 후보':'synthetic correction candidate','원본 비교':'source comparison'}[m[2]]);
  if((m=value.match(/^원본 Atlas 보존 · 배율 (.+)$/)))return `Original Atlas preserved · scale ${m[1]}`;
  if((m=value.match(/^자기 접촉 검사: (.+)$/)))return `Self-contact inspection: ${m[1]}`;
  if((m=value.match(/^주변 혈관 검사: (.+)$/)))return `Neighbor vessel inspection: ${m[1]}`;
  if((m=value.match(/^중심선 검사: (.+) \((\d+)개 경로\) · 주변 검사: (.+)$/)))return `Centerline inspection: ${m[1]} (${m[2]} paths) · context inspection: ${m[3]}`;
  if((m=value.match(/^중심선 검사: (.+) · 주변 검사: (.+)\.$/)))return `Centerline inspection: ${m[1]} · context inspection: ${m[2]}.`;
  if((m=value.match(/^단일 폐곡면 · (\d+)개 면 출처 확인\.$/)))return `Single closed surface · provenance checked for ${m[1]} faces.`;
  if((m=value.match(/^중심선 (\d+)개 구간 포함 · (\d+)개 면 출처 확인\.$/)))return `${m[1]} centerline segments contained · provenance checked for ${m[2]} faces.`;
  if((m=value.match(/^후보 자기 접촉 검출 0 · 동시 대체 (\d+)조합의 접촉 쌍 보존\.$/)))return `Candidate self-contacts detected: 0 · contact pairs preserved for ${m[1]} simultaneous replacement combinations.`;
  if((m=value.match(/^주변 프로파일 검사: (.+) · 분리 (\d+)\/(\d+)$/)))return `Surrounding profile inspection: ${m[1]} · separated ${m[2]}/${m[3]}`;
  if((m=value.match(/^두 표면 간 분리: (.+)$/)))return `Separation between two surfaces: ${m[1]}`;
  if((m=value.match(/^벽·중심선 후보 생성\. 최대 이동 ([\d.]+) mm · 연결 경로 (\d+)개 내강 포함 PASS\. 주변 검사 NOT RUN · 생성 미승인\.$/)))return `Wall and centerline candidate created. Maximum displacement ${m[1]} mm · ${m[2]} connected paths inside lumen: PASS. Context inspection NOT RUN · not approved for generation.`;
  if((m=value.match(/^주변 검사 (.+) · (\d+)개 이웃\. 동일 형상에 연결된 기존 측정이며 새 검사 실행은 아닙니다\. 생성 미승인\.$/)))return `Context inspection ${m[1]} · ${m[2]} neighbors. Existing measurements linked to identical geometry; no new inspection was run. Not approved for generation.`;
  for(const [suffix,english]of [
   [' 현재 사례와 편집 이력을 유지했습니다.',' Current case and edit history kept.'],
   [' 현재 사례를 유지했습니다. 미등록 형상은 별도 주변 검사가 필요합니다.',' Current case kept. Unregistered geometry needs a separate context inspection.'],
   [' 현재 사례는 유지됩니다. 같은 사례에서 이어 보기를 다시 누를 수 있습니다.',' Current case kept. Resume viewing with the same case.']])
   if(value.endsWith(suffix))return translated(value.slice(0,-suffix.length))+english;
  if((m=value.match(/^함께 변경할 구간 (\d+)개: (.+)\. 연결점과 구간 라벨은 유지됩니다\. 상세 형상 검사는 실행 시 수행합니다\.$/)))return `Segments edited together (${m[1]}): ${m[2]}. Junctions and segment labels stay fixed. Detailed geometry checks run on submission.`;
  if((m=value.match(/^등록 표면 (\d+)개 보존\. 벽 변경 후보 · 주변 검사: (.+) · 생성 미승인\. 부모 검사 기록은 이력으로 보존됩니다\.$/)))return `${m[1]} registered surfaces preserved. Wall-edit candidate · context inspection: ${m[2]} · not approved for generation. Parent inspections are retained as history.`;
  if((m=value.match(/^저장된 검사 (\d+)\/(\d+)개 · (.+) · 잔존 접촉 (\d+)개 · 미확인 (\d+)개\. 접촉 또는 미확인 항목을 모두 표시합니다\.$/)))return `Saved inspection ${m[1]}/${m[2]} · ${m[3]} · ${m[4]} remaining contacts · ${m[5]} unknown. All contact and unknown entries are shown.`;
  if((m=value.match(/^주변 검사 (\d+)\/(\d+)개 완료 · 실행 중$/)))return `Context inspection ${m[1]}/${m[2]} complete · running`;
  if((m=value.match(/^검사 완료: (.+) · (\d+)\/(\d+)개\. 결과를 사례에 포함했습니다\. 생성 미승인\.$/)))return `Inspection complete: ${m[1]} · ${m[2]}/${m[3]}. Result included in the case. Not approved for generation.`;
  if((m=value.match(/^등록 삼각형 ([\d,]+)개 · 저장된 좌표 사용 · 형상 수용 검증과 별개$/)))return `${m[1]} registered triangles · saved coordinates · separate from geometry acceptance`;
  if((m=value.match(/^등록 표면 (\d+)개 보존\. 접근 후보 검사 기록 없음 · 수용 여부 미확인\.$/)))return `${m[1]} registered surfaces preserved. No access-candidate inspection · acceptance unknown.`;
 }
 if(language==='ko'){
  let m;
  if((m=value.match(/^(.+) · mm · source coordinate contract confirmed\. Drafts do not certify anatomical boundaries\.$/)))return `${m[1]} · mm · 원본 좌표 계약 확인. 초안은 해부학적 경계를 확정하지 않습니다.`;
  if((m=value.match(/^(Left|Right) · (ACA|MCA) · ([AM][1-4]) → ([AM][1-4])$/)))return `${m[1]==='Left'?'좌측':'우측'} · ${m[2]} · ${m[3]} → ${m[4]}`;
  if((m=value.match(/^unresolved · (.+)$/)))return `미확인 · ${m[1]}`;
  if((m=value.match(/^(.+): source absent; estimated display fill available$/)))return `${m[1]}: 원본 없음; 추정 표시 보충 가능`;
  if((m=value.match(/^Source triangle cross-section centroids and local axes; cubic Hermite centerlines with smoothstep radius taper · Estimated vessel spacing: ([\d.]+) source units minimum \(capsule proxy; original atlas surfaces are not certified clear\)\.$/)))return `원본 삼각형 단면 중심과 국소 축, cubic Hermite 중심선과 smoothstep 반경 전이를 사용합니다. 추정 혈관 간격: 원본 단위 최소 ${m[1]} (캡슐 근사이며 원본 Atlas 표면의 무충돌은 확인되지 않았습니다).`;
  if((m=value.match(/^(\d+) original-source gap reports: (\d+) represented by an estimated network; (\d+) without an estimated display fill\. Missing source anatomy remains missing\. Whole-network continuity is not validated\.$/)))return `원본 결손 기록 ${m[1]}개: 추정 혈관망으로 표시 ${m[2]}개, 추정 표시 보충 없음 ${m[3]}개. 원본 해부 구조의 결손은 유지됩니다. 전체 혈관망 연속성은 검증되지 않았습니다.`;
  if((m=value.match(/^(\d+) matching vessels$/)))return `검색된 혈관 ${m[1]}개`;
  if((m=value.match(/^Current measured centerline surrogate: ([\d.]+)\.$/)))return `현재 측정된 중심선 대리 지표: ${m[1]}.`;
  if((m=value.match(/^Measured surrogate: (.+) · requested preset: (.+)$/)))return `측정된 대리 지표: ${m[1]} · 요청한 프리셋: ${m[2]}`;
  if((m=value.match(/^Centerline graph available\. Neighbor links are unverified proximity candidates\. Source Parts: (\d+) · Extracted: (\d+) · Unresolved: (\d+) · Authored Parts: (\d+) · Nodes: (\d+) · Edges: (\d+) · Candidate Links: (\d+)$/)))return `중심선 그래프 준비 완료. 이웃 연결은 미검증 근접 후보입니다. 원본 부위: ${m[1]} · 추출: ${m[2]} · 미확인: ${m[3]} · 작성 부위: ${m[4]} · 노드: ${m[5]} · 구간: ${m[6]} · 후보 연결: ${m[7]}`;
  if((m=value.match(/^([MAP][123]) · (source named|boundary needed)$/)))return `${m[1]} · ${m[2]==='source named'?'원본 명칭':'경계 확인 필요'}`;
  if((m=value.match(/^(\d+) modified vessel\(s\); source files preserved\.$/)))return `편집한 혈관 ${m[1]}개 · 원본 파일 보존.`;
  if((m=value.match(/^Generation (\d+) · (\d+) arterial \/ (\d+) venous vessels$/)))return `생성 ${m[1]} · 동맥 ${m[2]}개 / 정맥 ${m[3]}개`;
  if((m=value.match(/^Arterial route ([\d,.]+) mm · (\d+) segments$/)))return `동맥 경로 ${m[1]} mm · ${m[2]}개 구간`;
  if((m=value.match(/^Loaded (\d+) edges\. Anatomical acceptance: UNKNOWN\.$/)))return `${m[1]}개 구간을 불러왔습니다. 해부학적 수용: UNKNOWN.`;
  if((m=value.match(/^Synthetic copy created\. Maximum displacement ([\d.]+) mm\. Surface collision checks: NOT RUN; anatomical acceptance: UNKNOWN\.$/)))return `합성 복사본을 만들었습니다. 최대 이동 ${m[1]} mm. 표면 충돌 검사: NOT RUN; 해부학적 수용: UNKNOWN.`;
  if((m=value.match(/^(Undo|Redo) restored the previous case revision\. Download to keep this version\.$/)))return `${m[1]==='Undo'?'변경 취소':'다시 적용'}로 사례 revision을 복원했습니다. 이 버전을 보관하려면 다운로드하세요.`;
  for(const [suffix,korean]of [[' Current case and edit history kept.',' 현재 사례와 편집 이력을 유지했습니다.'],[' Current case kept.',' 현재 사례를 유지했습니다.'],
   [' 현재 사례와 편집 이력을 유지했습니다.',' 현재 사례와 편집 이력을 유지했습니다.'],
   [' 현재 사례를 유지했습니다. 미등록 형상은 별도 주변 검사가 필요합니다.',' 현재 사례를 유지했습니다. 미등록 형상은 별도 주변 검사가 필요합니다.'],
   [' 현재 사례는 유지됩니다. 같은 사례에서 이어 보기를 다시 누를 수 있습니다.',' 현재 사례는 유지됩니다. 같은 사례에서 이어 보기를 다시 누를 수 있습니다.']])
   if(value.endsWith(suffix))return translated(value.slice(0,-suffix.length))+korean;
  if((m=value.match(/^Undo: (\d+)\/20 · Redo: (\d+)(.*)$/)))return `취소: ${m[1]}/20 · 다시 적용: ${m[2]}${m[3].includes('Changes not downloaded')?' · 변경 사항 미저장':''}`;
  if((m=value.match(/^(\d+) \/ (\d+) vessels$/)))return `혈관 ${m[1]} / ${m[2]}개`;
  if((m=value.match(/^Generation (\d+) · (\d+) atlas parts · (.+)$/)))return `생성 ${m[1]} · Atlas 부위 ${m[2]}개 · ${m[3]}`;
  if((m=value.match(/^Selected: (.+)$/)))return `선택: ${m[1]}`;
 }
 return text;
}
function walk(root){
 if(root.nodeType===3){const parent=root.parentElement;if(!parent||parent.closest('script,style,textarea,code,pre,#vv-language,[data-no-translate]'))return;
  const old=originals.get(root),source=old&&root.nodeValue===old.rendered?old.source:root.nodeValue;
  const rendered=translated(source);originals.set(root,{source,rendered});if(root.nodeValue!==rendered)root.nodeValue=rendered;return;}
 if(root.nodeType!==1&&root.nodeType!==9)return;
 if(root.nodeType===1){if(root.matches('script,style,textarea,code,pre,#vv-language,[data-no-translate]'))return;
  for(const attr of ['placeholder','title','aria-label'])if(root.hasAttribute(attr)){const current=root.getAttribute(attr),value=translated(current);if(current!==value)root.setAttribute(attr,value);}}
 for(const child of root.childNodes)walk(child);
}
const observer=new MutationObserver(records=>{observer.disconnect();for(const r of records){if(r.type==='childList')for(const node of r.addedNodes)walk(node);else walk(r.target);}observe();});
function observe(){observer.observe(document.documentElement,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['placeholder','title','aria-label']});}
function render(){observer.disconnect();document.documentElement.lang=language;walk(document.documentElement);toolbar.setAttribute('aria-label',language==='ko'?'언어':'Language');for(const b of toolbar.children)b.setAttribute('aria-pressed',String(b.dataset.language===language));observe();}
function setLanguage(code){if(!['en','ko'].includes(code))return;language=code;try{localStorage.setItem(key,code);}catch{}render();window.dispatchEvent(new CustomEvent('vv-language-change',{detail:{language}}));}
window.addEventListener('storage',event=>{if(event.key===key&&['en','ko'].includes(event.newValue)){language=event.newValue;render();}});
window.VVLanguage={get language(){return language;},setLanguage,translate:translated};render();
})();'''.replace('__COPY__',json.dumps(COPY,ensure_ascii=False))


def with_language(html):
    return html.replace('</html>','<script src="/ui-language.js"></script></html>')
