# kq-dir

A personal macOS file manager for working with multiple folders in one window. Each pane has its own folder and tabs, and projects preserve separate workspace layouts.

[한국어](README.ko.md) · [Korean feature guide](docs/personal-guide.html)

## Features

- **Up to four panes:** choose a single pane, side-by-side or stacked two-pane layout, three panes, or four panes. Each pane maintains its own folders and tabs.
- **Tabs:** use `⌘T` or `+` for an empty tab. Double-click a tab to duplicate it to the right, or middle-click to close it. Closing the last tab leaves an empty `Untitled` tab.
- **Open folders in tabs:** middle-click or `⌘`-double-click a folder in list or tree view; `⌘`+`Enter` opens the selected folder in a new tab.
- **Keep the current tab:** opening, duplicating, or reopening a tab leaves the current tab selected. Click the new tab to switch to it.
- **Drop files onto tabs:** drop selected files and folders from the list onto another tab to send them to that tab’s folder. Items move on the same volume and copy across volumes or when you hold `Option`. The target is highlighted and the active tab stays selected. Use `⌘Z` to undo a recent transfer.
- **Cut and paste:** use `⌘X` on selected items, then `⌘V` in the destination folder to move them. Failed or skipped items stay on the clipboard so you can paste them into another folder.
- **File operations:** copy, cut, paste, rename, duplicate, move to Trash, compress, and extract. Failures are reported separately; the toolbar's **File operations** button shows progress and results.
- **Search and preview:** search folders and their descendants and preview PDFs, images, Markdown, ZIP contents, and other formats supported by macOS Quick Look.
- **Projects and favorites:** keep frequently used folders in the sidebar and save pane and tab layouts by project.
- **Settings:** use `⌘,` to choose system, light, or dark appearance and customize shortcuts. Custom color themes are not yet available.

See the [Korean feature guide](docs/personal-guide.html) for a visual overview and shortcuts.

## Move selected files and folders to Trash

Version `0.3.2` handles `⌘+Backspace` directly in the app window, independently of menu shortcut dispatch. Install the [updated DMG](https://github.com/konslie/Ko_SmallApps/releases/tag/kq-dir-v0.3.2). Text editing and customized shortcut bindings remain supported.

Select one or more files or folders in list or tree view, then press **`⌘` + `Backspace` (`⌘⌫`)**. The selection in the active pane moves to the macOS Trash. On a Mac keyboard, use the backward-delete key labeled `delete` or `⌫`.

The same action is available through **Edit → Move to Trash**. While editing a filename or search text, the shortcut applies to the text being edited. If you have customized shortcuts, check **`⌘,` → Shortcuts → Move to Trash** for the current binding.

## Requirements

- Running the app: macOS 14 or later; Xcode is not required.
- Building from source: Xcode + [XcodeGen](https://github.com/yonaskolb/XcodeGen), or compatible standalone Command Line Tools with Swift 5.10 or later.

## Install: DMG or Command Line Tools

The [kq-dir v0.3.2 release](https://github.com/konslie/Ko_SmallApps/releases/tag/kq-dir-v0.3.2) provides two options:

- **DMG:** open `kq-dir-v0.3.2.dmg` and drag the app into Applications. The binary includes Apple silicon and Intel architectures.
- **Build with CLT:** extract `kq-dir-v0.3.2-clt-source.zip` and run the commands below. You can also clone the GitHub repository and run the same commands from `kq-dir/`.

```bash
cd kq-dir
bash Scripts/build-clt.sh --version 0.3.2 --build-number 10
open /tmp/kq-dir-build/clt/kq-dir.app
```

Both paths use ad-hoc signing without Apple notarization. Neither overrides company execution policies. See the [installation guide (Korean)](docs/install.md) for CLT setup, SDK compatibility, first launch, and validation limits.

## Local Debug build

After cloning this repository, run from the `kq-dir` directory:

```bash
cd kq-dir
Scripts/generate-project.sh
xcodebuild -scheme mq-dir -configuration Debug -derivedDataPath DerivedData build
open DerivedData/Build/Products/Debug/kq-dir.app
```

The generated project and scheme retain the `mq-dir` build names; the app is named `kq-dir`. Install XcodeGen with `brew install xcodegen` if needed.

## Tests

```bash
swift test
xcodebuild -scheme mq-dir -configuration Debug -derivedDataPath DerivedData test -only-testing:mq-dir-service-tests
```

`swift test` covers the core library; `mq-dir-service-tests` covers app services. Run these tests with Xcode selected, because standalone CLT installations may not include XCTest. XCTest is not needed to build the app.

## Storage and external connections

Projects, tabs, favorites, and settings are stored in `~/Library/Application Support/com.konslie.mqdir/state.json`. The upstream automatic updater and feedback submission features have been removed. Remote images in Markdown previews are blocked by default; selecting **Load external images** sends requests to the relevant image servers.

## Attribution and license

kq-dir is a personal, non-commercial version based on the open-source [mq-dir](https://github.com/h5nam/mq-dir) by **h5nam**, starting from upstream commit `399999d`.

The original copyright notice and MIT license are preserved in [LICENSE](LICENSE). Copyright © 2026 mq-dir contributors.
