import AppKit
import Foundation
import UniformTypeIdentifiers

// Drag/drop pasteboard plumbing for mq-dir.
//
// External drags (mq-dir → Finder/Terminal/etc.) carry a single primary URL
// via the standard `public.file-url` type. Internal drags carry an extra
// `com.mqdir.selection.urls` representation containing the *full* selection,
// so that pane-to-pane drops can move every selected item even though
// SwiftUI's `.draggable` only ships one item at a time.

@MainActor
enum DragDropSupport {
    nonisolated static let mqdirSelectionTypeIdentifier = "com.mqdir.selection.urls"

    // Drag-source construction lives in `AppKitFileDrag.swift` — we drive
    // NSDraggingSession directly with an NSPasteboardItem because
    // SwiftUI's `.onDrag` layers a promise on top of any NSItemProvider
    // we hand it, so receivers that read via `loadFileRepresentation`
    // (WebKit / cmux / browsers) end up with a cache copy instead of
    // the original path.

    static func resolveURLs(from providers: [NSItemProvider]) async -> [URL] {
        await beginResolvingURLs(from: providers).value
    }

    /// Start each provider load before the drop callback returns. Keep the
    /// drag order even when providers finish out of order.
    static func beginResolvingURLs(from providers: [NSItemProvider]) -> Task<[URL], Never> {
        let loads = providers.map { provider in
            let files = AsyncStream<URL>.makeStream()
            if provider.hasItemConformingToTypeIdentifier(UTType.fileURL.identifier) {
                provider.loadObject(ofClass: NSURL.self) { object, _ in
                    if let url = object as? URL, url.isFileURL {
                        files.continuation.yield(url)
                    }
                    files.continuation.finish()
                }
            } else {
                files.continuation.finish()
            }

            let selection = AsyncStream<[URL]>.makeStream()
            if provider.hasItemConformingToTypeIdentifier(mqdirSelectionTypeIdentifier) {
                provider.loadDataRepresentation(forTypeIdentifier: mqdirSelectionTypeIdentifier) { data, _ in
                    if let data, let strings = try? JSONDecoder().decode([String].self, from: data) {
                        let urls = strings.compactMap { URL(string: $0) }.filter(\.isFileURL)
                        if !urls.isEmpty { selection.continuation.yield(urls) }
                    }
                    selection.continuation.finish()
                }
            } else {
                selection.continuation.finish()
            }
            return (selection.stream, files.stream)
        }

        return Task {
            var urls: [URL] = []
            for (selection, files) in loads {
                var iterator = selection.makeAsyncIterator()
                if let batch = await iterator.next() {
                    urls.append(contentsOf: batch)
                } else {
                    for await url in files { urls.append(url) }
                }
            }
            var seen: Set<String> = []
            return urls.filter { seen.insert($0.standardizedFileURL.path).inserted }
        }
    }

    /// Type identifiers a drop destination should accept.
    nonisolated static let acceptedDropTypes: [String] = [
        mqdirSelectionTypeIdentifier,
        UTType.fileURL.identifier,
    ]
}
