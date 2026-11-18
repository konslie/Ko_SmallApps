# kq-dir

macOS에서 여러 폴더를 한 창에 나란히 놓고 사용하는 개인용 파일 관리자입니다. 각 패널에서 독립된 폴더와 탭을 사용하고, 프로젝트별 작업 공간을 저장할 수 있습니다.

[English](README.md) · [한국어 기능 안내](docs/personal-guide.html)

## 주요 기능

- **최대 4개 패널**: 1개, 좌우·상하 2개, 3개 또는 4개 패널로 작업합니다. 패널별 폴더와 탭을 따로 관리합니다.
- **탭**: `⌘T` 또는 `+`로 빈 탭을 만듭니다. 탭을 더블클릭하면 오른쪽에 복제하고, 휠클릭하면 닫습니다. 마지막 탭을 닫으면 빈 `Untitled` 탭이 남습니다.
- **폴더 새 탭 열기**: 리스트·트리에서 폴더를 휠클릭하거나 `⌘`+더블클릭합니다. 선택한 폴더는 `⌘`+`Enter`로도 열 수 있습니다.
- **현재 탭 유지**: 새 탭을 만들거나 폴더를 새 탭으로 열거나 탭을 복제·복원해도 현재 탭에 머무릅니다. 새 탭을 클릭해 전환합니다.
- **탭으로 파일 보내기**: 리스트에서 선택한 파일·폴더를 다른 탭에 놓으면 그 탭의 폴더로 보냅니다. 같은 볼륨에서는 이동하고, 다른 볼륨이거나 `Option` 키를 누른 채 놓으면 복사합니다. 대상 탭은 강조 표시되고 현재 탭은 그대로 유지됩니다. 최근 작업은 `⌘Z`로 되돌릴 수 있습니다.
- **잘라내고 붙여넣기**: `⌘X`로 잘라낸 뒤 대상 폴더로 가서 `⌘V`로 이동합니다. 이동에 실패하거나 건너뛴 항목은 클립보드에 남아 다른 폴더에 다시 붙여넣을 수 있습니다.
- **파일 작업**: 복사·잘라내기·붙여넣기, 이름 변경, 복제, 휴지통 이동, 압축·해제 등을 지원합니다. 작업이 실패하면 오류를 알리고, 도구 막대의 **File operations** 버튼에서 진행 상황과 결과를 확인할 수 있습니다.
- **검색과 미리보기**: 폴더와 하위 폴더 검색, PDF·이미지·Markdown·ZIP 등의 미리보기를 지원합니다. 다른 형식의 표시는 macOS Quick Look 지원 여부에 따릅니다.
- **프로젝트와 즐겨찾기**: 자주 쓰는 폴더를 사이드바에 추가하고, 프로젝트별 패널과 탭을 저장합니다.
- **설정**: `⌘,`에서 시스템·라이트·다크 외관과 단축키를 설정합니다. 사용자 지정 색상 테마는 아직 제공하지 않습니다.

자세한 사용법과 단축키는 [한국어 기능 안내](docs/personal-guide.html)를 브라우저에서 열어 확인하세요.

## 선택한 파일·폴더를 휴지통으로 이동

`0.3.2`에서는 `⌘+Backspace` 입력을 앱 창에서 직접 처리해 메뉴 단축키 전달에만 의존하지 않도록 보완했습니다. [업데이트 DMG](https://github.com/konslie/Ko_SmallApps/releases/tag/kq-dir-v0.3.2)로 설치할 수 있습니다. 이름·검색 텍스트 편집과 사용자 지정 단축키는 유지합니다.

리스트 또는 트리에서 파일·폴더를 하나 이상 선택한 뒤 **`⌘` + `Backspace` (`⌘⌫`)**를 누릅니다. 현재 활성 패널의 선택 항목들이 macOS 휴지통으로 이동합니다. Mac 키보드에서 `delete` 또는 `⌫`로 표시된 뒤로 지우기 키를 사용하세요.

같은 작업은 메뉴의 **Edit → Move to Trash**에서도 실행할 수 있습니다. 이름 변경이나 검색창에서 텍스트를 편집하는 중에는 파일 대신 편집 중인 텍스트에 적용됩니다. 단축키를 변경했다면 **`⌘,` → Shortcuts → Move to Trash**에서 현재 설정을 확인하세요.

## 요구사항

- 실행: macOS 14 이상. 완성된 앱을 사용하는 Mac에는 Xcode가 필요 없습니다.
- 소스 빌드: Xcode + [XcodeGen](https://github.com/yonaskolb/XcodeGen), 또는 호환되는 Swift 5.10 이상 Command Line Tools.

## 설치: DMG 또는 CLT

[kq-dir v0.3.2 릴리스](https://github.com/konslie/Ko_SmallApps/releases/tag/kq-dir-v0.3.2)에서 두 방법을 제공합니다.

- **DMG 설치:** `kq-dir-v0.3.2.dmg`를 열고 앱을 `Applications`로 드래그합니다. Apple silicon과 Intel을 모두 지원합니다.
- **CLT로 직접 빌드:** `kq-dir-v0.3.2-clt-source.zip`을 풀고 아래 명령을 실행합니다. GitHub 소스를 클론한 뒤 `kq-dir/`에서도 같은 명령을 사용할 수 있습니다.

```bash
cd kq-dir
bash Scripts/build-clt.sh --version 0.3.2 --build-number 10
open /tmp/kq-dir-build/clt/kq-dir.app
```

두 방법 모두 ad-hoc 서명이며 Apple 공증은 하지 않습니다. 회사의 실행 제한을 해제하는 방법은 아닙니다. CLT 설치, 호환 SDK, 최초 실행과 검증 범위는 [설치 안내](docs/install.md)를 참고하세요.

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

`swift test`는 코어 라이브러리를, `mq-dir-service-tests`는 앱 서비스 코드를 검증합니다. 이 테스트들은 XCTest가 포함된 Xcode 환경에서 실행합니다. CLT 설치에는 XCTest가 없을 수 있지만 앱 빌드에는 필요하지 않습니다.

## 저장과 외부 연결

프로젝트·탭·즐겨찾기·설정은 `~/Library/Application Support/com.konslie.mqdir/state.json`에 저장됩니다. 원작자의 자동 업데이트와 피드백 전송 기능은 제거했습니다. Markdown 미리보기의 외부 이미지는 기본 차단되며, **Load external images**를 직접 선택하면 해당 이미지 서버로 요청이 전송됩니다.

## 원작과 라이선스

kq-dir은 **h5nam의 오픈소스 [mq-dir](https://github.com/h5nam/mq-dir)** 소스를 기반으로 한 개인·비상업 사용 버전입니다. 원본 기준 커밋은 `399999d`입니다.

원본의 저작권 고지와 MIT 라이선스는 [LICENSE](LICENSE)에 그대로 유지합니다. Copyright © 2026 mq-dir contributors.
