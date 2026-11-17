# kq-dir 설치: 두 가지 방법

앱 이름은 `kq-dir`, 번들 ID는 `com.konslie.mqdir`입니다. macOS 14 이상을 사용합니다. 두 방법 모두 Apple Developer 계정 없이 ad-hoc 서명하며 공증하지 않습니다. 회사의 보안 정책이 실행을 제한하면 IT의 허용이 필요합니다. 로컬 빌드가 실행 제한을 해제하지는 않습니다.

## A. 완성된 DMG 설치

1. [릴리스 페이지](https://github.com/konslie/Ko_SmallApps/releases/tag/kq-dir-v0.3.2)에서 `kq-dir-v0.3.2.dmg`와 `.dmg.sha256`을 내려받습니다.
2. 두 파일이 있는 폴더에서 `shasum -a 256 -c kq-dir-v0.3.2.dmg.sha256`으로 다운로드 무결성을 확인합니다.
3. DMG를 열고 `kq-dir.app`을 `Applications` 바로가기로 드래그합니다.
4. Applications의 앱을 실행합니다. 이 Mac에는 Xcode, CLT, Homebrew가 필요하지 않습니다.

GitHub CLI가 이미 있다면 다음과 같이 받을 수도 있습니다. CLI는 필수가 아닙니다.

```bash
gh release download kq-dir-v0.3.2 -R konslie/Ko_SmallApps -p '*.dmg' -p '*.dmg.sha256'
```

미공증 앱 경고가 나타나면 출처와 체크섬을 확인한 뒤, 장치 정책이 허용하는 경우 **시스템 설정 → 개인정보 보호 및 보안 → 확인 없이 열기**를 사용합니다. 회사 관리 정책이 이를 막으면 IT에 앱 허용을 요청합니다. 격리 속성 제거 또는 Gatekeeper 해제를 필수 설치 단계로 사용하지 않습니다.

DMG는 Xcode의 Release 구성으로 만든 `0.3.2`(빌드 `10`) 유니버설 바이너리(`arm64`, `x86_64`)입니다. `codesign --verify` 통과는 서명 무결성 확인이며 Apple 공증이나 회사 정책의 승인을 뜻하지 않습니다.

## B. Xcode 없이 CLT로 직접 빌드

이 방법은 회사에서 로컬 개발 도구와 소스 빌드를 허용하는 경우에 사용합니다. Xcode 앱, XcodeGen, Homebrew, 유료 개발자 계정은 필요하지 않습니다. Swift 컴파일러와 호환 macOS SDK가 포함된 **Command Line Tools(CLT)**는 필요합니다.

1. CLT가 없다면 터미널에서 `xcode-select --install`을 실행하고 설치를 완료합니다.
2. 같은 릴리스의 **`kq-dir-v0.3.2-clt-source.zip`**과 `.zip.sha256`을 내려받습니다. GitHub의 자동 `Source code (zip)`과는 다른 파일입니다.
3. `shasum -a 256 -c kq-dir-v0.3.2-clt-source.zip.sha256`으로 확인한 뒤 압축을 풉니다.
4. 압축을 푼 `kq-dir` 폴더에서 실행합니다.

```bash
bash Scripts/build-clt.sh --version 0.3.2 --build-number 10
open /tmp/kq-dir-build/clt/kq-dir.app
```

생성된 앱을 Finder로 Applications에 복사해 사용할 수 있습니다. 기존 kq-dir을 종료하고 교체하면 됩니다. 기존 설정은 `~/Library/Application Support/com.konslie.mqdir/state.json`을 그대로 사용합니다.

첫 빌드에는 `Config/Package.resolved`에 고정된 MarkdownUI, NetworkImage, swift-cmark를 받기 위한 GitHub 접근이 필요합니다. 빌드 스크립트는 앱의 외부 통신 기능을 추가하지 않습니다.

### 빌드 동작과 호환성

- CLT의 컴파일러·SDK만 명시적으로 선택합니다. 시스템 전체의 `xcode-select` 설정은 바꾸지 않습니다.
- 현재 Mac의 아키텍처용 앱을 만듭니다. DMG의 유니버설 바이너리와 달리 이 결과를 다른 아키텍처의 Mac에 복사하는 용도는 아닙니다.
- 산출물, 임시 SwiftPM 패키지와 로그는 `/tmp/kq-dir-build/clt`에 둡니다. 임시 폴더는 macOS가 정리할 수 있으므로 완성된 앱은 Applications로 옮깁니다.
- 기존 앱 소스를 사용하며 개발용 `#Preview`만 SwiftPM 빌드에서 제외합니다. 아이콘은 기존 PNG에서 `.icns`로 만듭니다.
- 설치된 CLT SDK마다 `@State`를 포함한 SwiftUI 코드를 먼저 검사하고, 통과한 최신 SDK를 선택합니다. 최신 SDK가 SwiftUI 매크로 도구를 요구하지만 해당 CLT에 도구가 없다면 함께 설치된 이전 호환 SDK를 사용합니다.
- 호환 SDK가 하나도 없으면 빌드를 중단하고 진단 로그를 남깁니다. 호환되는 CLT 버전 설치가 필요합니다.
- CLT 업데이트 잔재로 SwiftPM의 오래된 private interface가 새 라이브러리와 충돌하면 임시 복사본에서만 잔재를 제외합니다. 시스템 CLT 파일은 수정하지 않습니다.
- SwiftPM의 native 빌드 방식을 사용합니다. 향후 Swift에서 이 방식이 제거되면 스크립트 재검증이 필요합니다.

특정 CLT SDK를 지정할 때는 다음과 같이 실행합니다. 지정한 SDK는 실제로 설치되어 있어야 합니다.

```bash
bash Scripts/build-clt.sh --version 0.3.2 --build-number 10 \
  --sdk /Library/Developer/CommandLineTools/SDKs/MacOSX26.5.sdk
```

### 배포 소스와 테스트

DMG와 CLT 소스는 `konslie/Ko_SmallApps`의 `kq-dir-v0.3.2` 태그에 있는 `kq-dir/`를 기준으로 합니다. 버전은 `0.3.2`, 빌드 번호는 `10`입니다. CLT 빌드 스크립트와 설치 안내도 저장소에 포함됩니다. GitHub 저장소를 클론하거나 릴리스의 `kq-dir-v0.3.2-clt-source.zip`을 사용할 수 있습니다.

`⌘+Backspace`는 앱 창의 실제 뒤로 지우기 키 입력으로도 처리합니다. 파일 행 클릭 시 리스트·트리에 키보드 포커스를 돌려주며, 이름·검색 텍스트 편집 중에는 파일 삭제를 실행하지 않습니다. 단축키 사용자 지정은 유지합니다. 회사 Mac에서 발생한 무반응의 정확한 원인은 해당 기기에서 추가 확인해야 합니다.

코어 197개와 앱 서비스 39개 테스트는 XCTest가 포함된 Xcode 환경에서 통과했습니다. CLT에는 XCTest가 없을 수 있으므로 이 자동 테스트를 실행하는 것과 앱을 빌드하는 것은 구분합니다. 회사 Mac의 실제 설치 정책과 Intel Mac에서의 실행은 해당 기기에서 확인해야 합니다.

CLT 경로는 Apple silicon Mac에서 **CLT Swift 6.4.2 + CLT macOS 26.5 SDK**로 Release 빌드·ad-hoc 서명 검증을 통과했습니다. 독립된 임시 작업 공간에서 앱 실행과 리스트·트리 선택 항목 휴지통 이동도 확인했습니다. 이전 `0.3.1`에서도 새 탭·가운데 버튼 닫기·설정 화면을 확인했습니다. 이 환경의 macOS 27.2 SDK는 CLT에 없는 `SwiftUIMacros`가 필요해 사전 검사에서 제외됐습니다. Xcode로 만든 DMG도 마운트 후 서명 검증과 앱 실행·버전 표시·단축키 휴지통 이동을 확인했습니다. 검증 중 기존 작업 공간의 보호 폴더 접근에서 첫 실행이 대기하는 경우가 있어, 해당 검증은 보호 폴더가 없는 임시 작업 공간으로 수행하고 기존 설정을 복원했습니다. 회사 Mac에서의 폴더 접근 권한도 별도 확인이 필요합니다.

## 회사 Mac에서 업데이트 확인

1. 기존 kq-dir을 종료하고 `0.3.2` 앱으로 교체합니다.
2. 앱 메뉴의 **About kq-dir**에서 **0.3.2 (10)**인지 확인합니다. 다른 위치에 남은 이전 앱을 실행하지 않도록 Applications의 앱을 엽니다.
3. 삭제해도 되는 테스트 파일을 선택한 뒤 `⌘+Backspace`를 누릅니다. 리스트·트리와 다중 선택을 지원합니다.
4. 단축키를 사용자 지정했다면 **Settings → Shortcuts → Move to Trash**가 `⌘⌫`인지 확인합니다.
5. 파일 권한·볼륨 정책 때문에 작업이 실패하면 오류 알림과 **File operations**의 실패 내용을 확인합니다. 회사 기기 자체에서의 검증 전에는 해결을 보장하지 않습니다.

## 원작과 라이선스

kq-dir은 **h5nam의 [mq-dir](https://github.com/h5nam/mq-dir)**, 원본 커밋 `399999d`를 기반으로 합니다. [MIT 라이선스](../LICENSE)와 원저작권 고지를 유지합니다. 배포 앱의 `Contents/Resources/Licenses`에는 원작과 포함 라이브러리의 라이선스도 들어 있습니다.
