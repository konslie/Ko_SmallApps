# kq-dir

A personal macOS file manager for working with multiple folders in one window. Each pane has its own folder and tabs, and projects preserve separate workspace layouts.

[한국어](README.ko.md) · [Korean feature guide](docs/personal-guide.html)

## Features

- **Up to four panes:** choose a single pane, side-by-side or stacked two-pane layout, three panes, or four panes. Each pane maintains its own folders and tabs.
- **Tabs:** use `⌘T` or `+` for an empty tab. Double-click a tab to duplicate it to the right, or middle-click to close it. Closing the last tab leaves an empty `Untitled` tab.
- **Open folders in tabs:** middle-click or `⌘`-double-click a folder in list or tree view; `⌘`+`Enter` opens the selected folder in a new tab.
- **Keep the current tab:** opening, duplicating, or reopening a tab leaves the current tab selected. Click the new tab to switch to it.
- **File operations:** copy, cut, paste, rename, duplicate, move to Trash, compress, and extract. Failures are reported separately; the toolbar's **File operations** button shows progress and results.
- **Search and preview:** search folders and their descendants and preview PDFs, images, Markdown, ZIP contents, and other formats supported by macOS Quick Look.
- **Projects and favorites:** keep frequently used folders in the sidebar and save pane and tab layouts by project.
- **Settings:** use `⌘,` to choose system, light, or dark appearance and customize shortcuts. Custom color themes are not yet available.

See the [Korean feature guide](docs/personal-guide.html) for a visual overview and shortcuts.

## Requirements

- macOS 14 or later
- Xcode and Xcode Command Line Tools
- [XcodeGen](https://github.com/yonaskolb/XcodeGen)

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

`swift test` covers the core library; `mq-dir-service-tests` covers app services.

## Storage and external connections

Projects, tabs, favorites, and settings are stored in `~/Library/Application Support/com.konslie.mqdir/state.json`. The upstream automatic updater and feedback submission features have been removed. Remote images in Markdown previews are blocked by default; selecting **Load external images** sends requests to the relevant image servers.

## Attribution and license

kq-dir is a personal, non-commercial version based on the open-source [mq-dir](https://github.com/h5nam/mq-dir) by **h5nam**, starting from upstream commit `399999d`.

The original copyright notice and MIT license are preserved in [LICENSE](LICENSE). Copyright © 2026 mq-dir contributors.
