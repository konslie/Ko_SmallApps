import AppKit
import SwiftUI

/// Observes the middle button without taking hit-testing away from row gestures.
struct MiddleClickAware: NSViewRepresentable {
    let onMiddleClick: () -> Void

    func makeNSView(context: Context) -> MiddleClickView {
        let view = MiddleClickView()
        view.onMiddleClick = onMiddleClick
        return view
    }

    func updateNSView(_ nsView: MiddleClickView, context: Context) {
        nsView.onMiddleClick = onMiddleClick
    }

    static func dismantleNSView(_ nsView: MiddleClickView, coordinator: ()) {
        nsView.removeMonitor()
    }
}

final class MiddleClickView: NSView {
    var onMiddleClick: (() -> Void)?
    private var monitor: Any?
    private var pressLocation: NSPoint?

    override func hitTest(_ point: NSPoint) -> NSView? { nil }

    override func viewDidMoveToWindow() {
        super.viewDidMoveToWindow()
        removeMonitor()
        guard window != nil else { return }
        monitor = NSEvent.addLocalMonitorForEvents(matching: [.otherMouseDown, .otherMouseUp]) { [weak self] event in
            guard let self, event.buttonNumber == 2 else { return event }
            guard let window = self.window, event.window === window,
                  !self.isHiddenOrHasHiddenAncestor else {
                self.pressLocation = nil
                return event
            }
            let point = self.convert(event.locationInWindow, from: nil)
            if event.type == .otherMouseDown {
                self.pressLocation = self.bounds.intersection(self.visibleRect).contains(point) ? event.locationInWindow : nil
                return event
            }
            defer { self.pressLocation = nil }
            guard let start = self.pressLocation,
                  self.bounds.intersection(self.visibleRect).contains(point),
                  hypot(event.locationInWindow.x - start.x, event.locationInWindow.y - start.y) < 5
            else { return event }
            self.onMiddleClick?()
            return nil
        }
    }

    func removeMonitor() {
        if let monitor { NSEvent.removeMonitor(monitor) }
        monitor = nil
        pressLocation = nil
    }
}
