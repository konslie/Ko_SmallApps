import AppKit
import SwiftUI

/// Route backward-delete by its physical key code, independently of menu
/// key-equivalent handling. Keep text editing and remapped shortcuts intact.
struct TrashShortcutHandler: NSViewRepresentable {
    let binding: ShortcutBinding
    let moveToTrash: () -> Void

    func makeNSView(context: Context) -> TrashShortcutView {
        let view = TrashShortcutView()
        updateNSView(view, context: context)
        return view
    }

    func updateNSView(_ view: TrashShortcutView, context: Context) {
        view.binding = binding
        view.moveToTrash = moveToTrash
    }

    static func dismantleNSView(_ view: TrashShortcutView, coordinator: ()) {
        view.removeMonitor()
    }
}

final class TrashShortcutView: NSView {
    var binding = ShortcutAction.moveToTrash.defaultBinding
    var moveToTrash: (() -> Void)?
    private var monitor: Any?

    override func hitTest(_ point: NSPoint) -> NSView? { nil }

    override func viewDidMoveToWindow() {
        super.viewDidMoveToWindow()
        removeMonitor()
        guard window != nil else { return }
        monitor = NSEvent.addLocalMonitorForEvents(matching: .keyDown) { [weak self] event in
            guard let self else { return event }
            return self.route(event, keyWindow: NSApp.keyWindow, modalWindow: NSApp.modalWindow) ? nil : event
        }
    }

    /// Returning true consumes the event, preventing a second menu dispatch.
    func route(_ event: NSEvent, keyWindow: NSWindow?, modalWindow: NSWindow?) -> Bool {
        guard event.type == .keyDown, event.keyCode == 51, binding.key == .delete,
              let window, window === keyWindow, event.window === window,
              window.attachedSheet == nil, modalWindow == nil,
              !isHiddenOrHasHiddenAncestor else { return false }
        if let editor = window.firstResponder as? NSTextView,
           editor.isFieldEditor || editor.isEditable { return false }

        let flags = event.modifierFlags.intersection([.command, .option, .control, .shift])
        var expected: NSEvent.ModifierFlags = []
        if binding.modifiers.contains(.command) { expected.insert(.command) }
        if binding.modifiers.contains(.option) { expected.insert(.option) }
        if binding.modifiers.contains(.control) { expected.insert(.control) }
        if binding.modifiers.contains(.shift) { expected.insert(.shift) }
        guard flags == expected, let moveToTrash else { return false }
        // A held key must not trash subsequent selections after a reload.
        if !event.isARepeat { moveToTrash() }
        return true
    }

    func removeMonitor() {
        if let monitor { NSEvent.removeMonitor(monitor) }
        monitor = nil
    }
}
