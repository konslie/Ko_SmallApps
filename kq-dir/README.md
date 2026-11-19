# kq-dir

오픈소스 macOS 파일 관리자 [mq-dir](https://github.com/h5nam/mq-dir)(제작: h5nam)를 가져와 몇 가지 기능을 추가하고 일부를 덜어낸 **개인용 비상업 버전**입니다. 업스트림 커밋 `399999d`에서 시작했습니다.

## 추가·변경한 점

- **탭에 파일 드롭:** 목록에서 선택한 파일·폴더를 다른 탭으로 드래그하면 그 탭의 폴더로 보냅니다. 같은 볼륨이면 이동, 다른 볼륨이거나 `Option`을 누르면 복사합니다. `⌘Z`로 직전 전송을 되돌릴 수 있습니다.
- **잘라내기·붙여넣기:** 항목을 선택하고 `⌘X`, 대상 폴더에서 `⌘V`를 누르면 이동합니다. 실패하거나 건너뛴 항목은 클립보드에 남습니다.
- **휴지통 단축키:** `⌘⌫`로 선택 항목을 휴지통으로 보냅니다.
- **파일 작업 현황:** 복사·이동·압축 등의 진행 상황과 실패 내역을 툴바의 **File operations** 버튼에서 봅니다.
- **제거한 기능:** 업스트림의 자동 업데이트와 피드백 전송.
- **개인용 안내서:** [한글 기능 가이드](docs/personal-guide.html)

## 기본 기능

- 최대 4개 창(pane), 창마다 폴더와 탭을 따로 가집니다.
- 탭 열기·복제·닫기, 폴더 새 탭으로 열기(가운데 클릭, `⌘`+더블클릭, `⌘`+`Enter`)
- 복사, 이름 변경, 복제, 압축·해제
- 하위 폴더 포함 검색, PDF·이미지·Markdown·ZIP 등 미리보기
- 사이드바 즐겨찾기, 프로젝트별 창·탭 배치 저장
- `⌘,`에서 설정과 단축키 변경

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
