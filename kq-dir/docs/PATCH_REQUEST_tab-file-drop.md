# 패치 요청: 탭에 파일 드롭 이동 / 잘라내기 보완

> 상태: 검토 요청 (구현 전 설계 검토 → 승인 후 구현)
> 대상: `kq-dir/Sources/mq-dir`

## 요청 1. 파일/폴더를 다른 탭으로 드래그하여 이동

### 요구사항
- 리스트에서 선택한 파일·폴더(다중 선택 포함)를 상단의 다른 탭 위로 드래그한다.
- 드롭하면 해당 탭이 가리키는 폴더로 항목이 이동한다.
- 드롭 대상 탭에 하이라이트 등 시각적 피드백을 준다.
- 같은 볼륨은 이동, 다른 볼륨은 복사, Option 키를 누르면 복사로 바꾸는 Finder 규칙을 검토한다.
- 탭 위에 잠시 머물면 그 탭이 활성화되는 spring-loaded 동작을 넣을지 검토한다.
  - (a) hover 후 탭 활성화 → 하위 폴더에 드롭
  - (b) 탭에 직접 드롭 → 즉시 그 탭의 현재 폴더로 이동
  - 두 방식 중 권장안과 이유를 제시한다.

### 현재 코드 현황 (확인 사항)
- `BrowserPaneView.swift`의 탭 칩 `.onDrop`은 `UTType.plainText`만 받는 `TabReorderDropDelegate`(탭 순서 변경용)이다. 파일 URL 드롭은 받지 않는다.
- 파일 드롭 처리는 `DragDropSupport.acceptedDropTypes`(`BrowserPaneView.swift`의 `paneIsDropTargeted` 영역)와 `FileWorkCenter`의 `.move` 요청 경로를 참고한다.
- 탭 순서 변경 드롭과 파일 드롭이 같은 탭 칩 위에서 충돌하지 않아야 한다.
  - `TabDragCoordinator`의 `sourceTabID` 유무로 탭 드래그와 파일 드래그를 구분할 수 있는지 검토한다.

### 검토 항목
1. 드롭 대상 탭 판별과 `FileWorkRequest(kind: .move, destination:)` 연결 방법
2. 탭 순서 변경 드롭과 파일 드롭의 공존 방식
3. 엣지 케이스
   - 같은 폴더로 드롭
   - 폴더를 자기 하위로 이동
   - 이름 충돌
   - 권한 오류
   - 다른 볼륨
   - 클라우드 동기화 폴더의 이동 실패나 지연
4. Undo 지원 여부와 추가 난이도

## 요청 2. ⌘X / ⌘V 잘라내기 (보완 확인)

### 현재 코드 현황
- 이미 구현되어 있는 부분:
  - `MenuCommands.swift`: ⌘X가 Cut 명령으로 연결되어 있다.
  - `FolderBrowserViewModel.cutSelectionToPasteboard()`: 선택 URL과 private marker(`CutPasteboard.markerType`)를 pasteboard에 쓴다.
  - `pasteFromPasteboard()`: marker가 있으면 `.move`, 없으면 `.copy`로 처리한다.
  - `CutPasteboard.complete`: 이동에 성공한 항목만 pasteboard에서 정리한다.

### 확인/보완 요청
1. 설치된 앱(`/Applications/kq-dir.app`)이 이 코드를 포함한 빌드인지 확인한다. 포함하지 않았다면 재빌드와 배포만 필요할 수 있다.
2. 잘라내기 대기 중인 항목을 리스트에서 흐리게 표시하는 기능이 없는 것으로 보인다. 추가 여부와 방법을 검토한다.
   - 대기 상태는 pasteboard marker를 기준으로 한다.
   - pasteboard 변경(다른 복사, Esc 등) 시 해제되어야 한다.
3. ⌘C 후 ⌘X, ⌘X 후 ⌘C 순서에서 상태가 올바르게 전환되는지 확인한다.
4. 이동할 수 없는 대상(권한 없음, 같은 폴더)에 붙여넣을 때의 동작을 확인한다.
5. 요청 1의 드롭 이동과 요청 2의 붙여넣기 이동이 같은 `FileWorkCenter` 경로를 쓰는지 확인한다. 불필요한 추상화는 만들지 않는다.

## 출력 요청 (검토 단계)
- 코드는 수정하지 않고 아래 순서로 작성한다.
  1. 현재 구조 요약
  2. 기능별 권장 설계
  3. 엣지 케이스 표
  4. 구현 단계 (단계별 검증 방법 포함)
  5. 열린 질문
- 요청 범위를 넘는 리팩터링은 제안하지 않는다.
