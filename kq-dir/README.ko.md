# kq-dir

macOS에서 여러 폴더를 한 창에 나란히 놓고 사용하는 개인용 파일 관리자입니다. 각 패널에서 독립된 폴더와 탭을 사용하고, 프로젝트별 작업 공간을 저장할 수 있습니다.

[English](README.md) · [한국어 기능 안내](docs/personal-guide.html)

## 주요 기능

- **최대 4개 패널**: 1개, 좌우·상하 2개, 3개 또는 4개 패널로 작업합니다. 패널별 폴더와 탭을 따로 관리합니다.
- **탭**: `⌘T` 또는 `+`로 빈 탭을 만듭니다. 탭을 더블클릭하면 오른쪽에 복제하고, 휠클릭하면 닫습니다. 마지막 탭을 닫으면 빈 `Untitled` 탭이 남습니다.
- **폴더 새 탭 열기**: 리스트·트리에서 폴더를 휠클릭하거나 `⌘`+더블클릭합니다. 선택한 폴더는 `⌘`+`Enter`로도 열 수 있습니다.
- **현재 탭 유지**: 새 탭을 만들거나 폴더를 새 탭으로 열거나 탭을 복제·복원해도 현재 탭에 머무릅니다. 새 탭을 클릭해 전환합니다.
- **파일 작업**: 복사·잘라내기·붙여넣기, 이름 변경, 복제, 휴지통 이동, 압축·해제 등을 지원합니다. 작업이 실패하면 오류를 알리고, 도구 막대의 **File operations** 버튼에서 진행 상황과 결과를 확인할 수 있습니다.
- **검색과 미리보기**: 폴더와 하위 폴더 검색, PDF·이미지·Markdown·ZIP 등의 미리보기를 지원합니다. 다른 형식의 표시는 macOS Quick Look 지원 여부에 따릅니다.
- **프로젝트와 즐겨찾기**: 자주 쓰는 폴더를 사이드바에 추가하고, 프로젝트별 패널과 탭을 저장합니다.
- **설정**: `⌘,`에서 시스템·라이트·다크 외관과 단축키를 설정합니다. 사용자 지정 색상 테마는 아직 제공하지 않습니다.

자세한 사용법과 단축키는 [한국어 기능 안내](docs/personal-guide.html)를 브라우저에서 열어 확인하세요.

## 요구사항

- macOS 14 이상
- Xcode 및 Xcode Command Line Tools
- [XcodeGen](https://github.com/yonaskolb/XcodeGen)

## 로컬 Debug 빌드

이 저장소를 클론한 뒤 `kq-dir` 폴더에서 실행합니다.

```bash
cd kq-dir
Scripts/generate-project.sh
xcodebuild -scheme mq-dir -configuration Debug -derivedDataPath DerivedData build
open DerivedData/Build/Products/Debug/kq-dir.app
```

`mq-dir.xcodeproj`와 `mq-dir` 스킴은 기존 프로젝트 생성·빌드 이름이며, 앱 이름은 `kq-dir`입니다. XcodeGen이 없다면 `brew install xcodegen`으로 설치할 수 있습니다.

## 테스트

```bash
swift test
xcodebuild -scheme mq-dir -configuration Debug -derivedDataPath DerivedData test -only-testing:mq-dir-service-tests
```

`swift test`는 코어 라이브러리를, `mq-dir-service-tests`는 앱 서비스 코드를 검증합니다.

## 저장과 외부 연결

프로젝트·탭·즐겨찾기·설정은 `~/Library/Application Support/com.konslie.mqdir/state.json`에 저장됩니다. 원작자의 자동 업데이트와 피드백 전송 기능은 제거했습니다. Markdown 미리보기의 외부 이미지는 기본 차단되며, **Load external images**를 직접 선택하면 해당 이미지 서버로 요청이 전송됩니다.

## 원작과 라이선스

kq-dir은 **h5nam의 오픈소스 [mq-dir](https://github.com/h5nam/mq-dir)** 소스를 기반으로 한 개인·비상업 사용 버전입니다. 원본 기준 커밋은 `399999d`입니다.

원본의 저작권 고지와 MIT 라이선스는 [LICENSE](LICENSE)에 그대로 유지합니다. Copyright © 2026 mq-dir contributors.
