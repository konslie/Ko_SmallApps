import AppKit
import XCTest

final class TrashShortcutTests: XCTestCase {
    @MainActor
    func testBackwardDeleteRoutesOnceRegardlessOfCharacterEncoding() {
        let window = makeWindow()
        let view = TrashShortcutView()
        window.contentView = view
        var calls = 0
        view.moveToTrash = { calls += 1 }
        for character in ["\u{8}", "\u{7f}"] {
            XCTAssertTrue(view.route(event(window, characters: character), keyWindow: window, modalWindow: nil))
        }
        XCTAssertEqual(calls, 2)
        XCTAssertTrue(view.route(event(window, repeatKey: true), keyWindow: window, modalWindow: nil))
        XCTAssertEqual(calls, 2)
        view.removeMonitor()
    }

    @MainActor
    func testOtherKeysModifiersAndRemappedBindingsAreNotConsumed() {
        let window = makeWindow()
        let view = TrashShortcutView()
        window.contentView = view
        view.moveToTrash = { XCTFail("Unexpected trash operation") }
        for flags: NSEvent.ModifierFlags in [[], [.command, .option], [.command, .shift], [.control]] {
            XCTAssertFalse(view.route(event(window, flags: flags), keyWindow: window, modalWindow: nil))
        }
        XCTAssertFalse(view.route(event(window, code: 117), keyWindow: window, modalWindow: nil))
        view.binding = ShortcutBinding(key: .character("t"), modifiers: .command)
        XCTAssertFalse(view.route(event(window), keyWindow: window, modalWindow: nil))
        view.removeMonitor()
    }

    @MainActor
    func testTextEditingAndOtherWindowsAreNotConsumed() {
        let window = makeWindow()
        let other = makeWindow()
        let view = TrashShortcutView()
        window.contentView = view
        view.moveToTrash = { XCTFail("Unexpected trash operation") }
        XCTAssertFalse(view.route(event(window), keyWindow: other, modalWindow: nil))
        XCTAssertFalse(view.route(event(other), keyWindow: window, modalWindow: nil))
        XCTAssertFalse(view.route(event(window), keyWindow: window, modalWindow: other))
        let editor = NSTextView(frame: NSRect(x: 0, y: 0, width: 80, height: 30))
        view.addSubview(editor)
        XCTAssertTrue(window.makeFirstResponder(editor))
        XCTAssertFalse(view.route(event(window), keyWindow: window, modalWindow: nil))
        editor.isEditable = false
        editor.isFieldEditor = true
        XCTAssertFalse(view.route(event(window), keyWindow: window, modalWindow: nil))
        view.removeMonitor()
    }

    @MainActor
    private func makeWindow() -> NSWindow {
        _ = NSApplication.shared
        return NSWindow(contentRect: NSRect(x: 0, y: 0, width: 200, height: 100),
                        styleMask: [.titled], backing: .buffered, defer: false)
    }

    @MainActor
    private func event(_ window: NSWindow, flags: NSEvent.ModifierFlags = .command,
                       code: UInt16 = 51, characters: String = "\u{7f}", repeatKey: Bool = false) -> NSEvent {
        NSEvent.keyEvent(with: .keyDown, location: .zero, modifierFlags: flags,
                         timestamp: 0, windowNumber: window.windowNumber, context: nil,
                         characters: characters, charactersIgnoringModifiers: characters,
                         isARepeat: repeatKey, keyCode: code)!
    }
}
