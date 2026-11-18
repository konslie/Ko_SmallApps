import AppKit

/// Completes only the clipboard transaction that started this move.
@MainActor
enum CutPasteboard {
    static let markerType = NSPasteboard.PasteboardType("com.mqdir.cut.urls")

    static func write(_ urls: [URL], cutting: Bool, to pasteboard: NSPasteboard) {
        pasteboard.clearContents()
        guard !urls.isEmpty, pasteboard.writeObjects(urls.map { $0 as NSURL }) else { return }
        if cutting { pasteboard.setData(Data(), forType: markerType) }
    }

    static func complete(_ pasteboard: NSPasteboard, changeCount: Int, remainingURLs: [URL]) {
        guard pasteboard.changeCount == changeCount else { return }
        write(remainingURLs, cutting: true, to: pasteboard)
    }
}
