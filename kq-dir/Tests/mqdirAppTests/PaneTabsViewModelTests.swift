import XCTest

final class PaneTabsViewModelTests: XCTestCase {
    @MainActor
    func testNewTabsKeepTheCurrentTabSelected() {
        let pane = PaneTabsViewModel(state: PaneState())
        let original = pane.activeTab
        let added = pane.newTab()
        XCTAssertEqual(pane.tabs.count, 2)
        XCTAssertTrue(pane.activeTab === original)
        XCTAssertTrue(pane.tabs.last === added)
        XCTAssertFalse(added === original)
    }

    @MainActor
    func testDuplicatingActiveTabKeepsOriginalSelected() {
        let pane = PaneTabsViewModel(state: PaneState())
        let original = pane.activeTab
        pane.duplicate(at: 0)
        XCTAssertEqual(pane.tabs.count, 2)
        XCTAssertTrue(pane.activeTab === original)
        XCTAssertFalse(pane.tabs[1] === original)
    }

    @MainActor
    func testDuplicatingEarlierTabPreservesActiveTabIdentity() {
        let pane = PaneTabsViewModel(state: PaneState())
        pane.newTab()
        let original = pane.newTab()
        pane.selectTab(at: 2)
        pane.duplicate(at: 0)
        XCTAssertEqual(pane.activeIndex, 3)
        XCTAssertTrue(pane.activeTab === original)
    }

    @MainActor
    func testReopeningClosedFolderKeepsCurrentTabSelected() throws {
        let root = try makeFolder()
        defer { try? FileManager.default.removeItem(at: root) }
        let pane = PaneTabsViewModel(state: PaneState())
        let original = pane.activeTab
        pane.newTab(folderURL: root)
        pane.closeTab(at: 1)
        pane.reopenClosed()
        XCTAssertEqual(pane.tabs.count, 2)
        XCTAssertTrue(pane.activeTab === original)
        XCTAssertEqual(pane.tabs[1].folderURL?.resolvingSymlinksInPath(), root.resolvingSymlinksInPath())
    }

    @MainActor
    func testExternalFolderOpensInReturnedTabWithoutNavigatingCurrentTab() throws {
        let root = try makeFolder()
        defer { try? FileManager.default.removeItem(at: root) }
        let pane = PaneTabsViewModel(state: PaneState())
        let original = pane.activeTab
        pane.newTab().openExternalURL(root)
        XCTAssertTrue(pane.activeTab === original)
        XCTAssertNil(original.folderURL)
        XCTAssertEqual(pane.tabs[1].folderURL?.resolvingSymlinksInPath(), root.resolvingSymlinksInPath())
    }

    private func makeFolder() throws -> URL {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        return root
    }
}
