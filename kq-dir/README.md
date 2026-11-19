# kq-dir

오픈소스 macOS 파일 관리자 [mq-dir](https://github.com/h5nam/mq-dir)(제작: h5nam)를 가져와 몇 가지 기능을 추가하고 일부를 덜어낸 **개인용 비상업 버전**입니다. 업스트림 커밋 `399999d`에서 시작했습니다.

## 추가·변경한 점

**탭 조작**
- **휠클릭으로 폴더를 새 탭에 열기:** 목록·트리에서 폴더를 휠클릭(마우스 가운데 버튼)하면 새 탭으로 엽니다. `⌘`+더블클릭, 선택 후 `⌘`+`Enter`도 같은 동작입니다.
- **탭 휠클릭으로 닫기:** 활성·비활성 탭 모두 바로 닫힙니다. 마지막 탭을 닫으면 빈 `Untitled` 탭이 남습니다.
- **탭 더블클릭으로 복제:** 클릭한 탭 바로 오른쪽에 복제하며 폴더·정렬·보기 방식을 이어받습니다.
- **현재 탭 유지:** 새 탭 만들기, 폴더 새 탭 열기, 복제, 닫은 탭 복원을 해도 보던 탭에 머뭅니다. 새 탭을 클릭하면 그때 전환합니다.

**파일 작업**
- **탭에 파일 드롭:** 선택한 파일·폴더를 다른 탭으로 드래그하면 그 탭의 폴더로 보냅니다. 같은 볼륨은 이동, 다른 볼륨이거나 `Option`을 누르면 복사합니다. 대상 탭은 강조되고 `⌘Z`로 되돌릴 수 있습니다.
- **잘라내기·붙여넣기 보완:** `⌘X` 후 `⌘V`로 이동하며, 실패하거나 건너뛴 항목은 클립보드에 남아 다른 폴더에 다시 붙여넣을 수 있습니다.
- **`⌘⌫` 휴지통 이동:** 메뉴 단축키 전달에 의존하지 않고 앱 창에서 직접 처리합니다. 이름·검색창 편집 중에는 텍스트 편집이 우선입니다.

**개인용 구성**
- 자동 업데이트와 피드백 전송 기능을 제거했습니다.
- 한글 안내서: [기능 가이드](docs/personal-guide.html)

## 설치

macOS 14 이상에서 실행됩니다. 앱을 쓰는 데 Xcode는 필요 없습니다.

- **DMG:** [v0.3.2 릴리스](https://github.com/konslie/Ko_SmallApps/releases/tag/kq-dir-v0.3.2)에서 `kq-dir-v0.3.2.dmg`를 받아 앱을 Applications로 옮깁니다.
- **소스 빌드(Command Line Tools):**

```bash
cd kq-dir
bash Scripts/build-clt.sh --version 0.3.2 --build-number 10
open /tmp/kq-dir-build/clt/kq-dir.app
```

임시 서명(ad-hoc)만 되어 있고 Apple 공증은 받지 않았습니다. 회사 실행 정책은 우회하지 않습니다. 자세한 절차는 [설치 안내](docs/install.md)를 참고하세요.

## 저장 위치와 외부 통신

프로젝트, 탭, 즐겨찾기, 설정은 `~/Library/Application Support/com.konslie.mqdir/state.json`에 저장됩니다. Markdown 미리보기의 원격 이미지는 기본으로 차단되며, **Load external images**를 선택할 때만 해당 서버에 요청합니다.

## 라이선스

원본 mq-dir의 MIT 라이선스와 저작권 표기를 그대로 유지합니다. [LICENSE](LICENSE) 참고. Copyright © 2026 mq-dir contributors.
