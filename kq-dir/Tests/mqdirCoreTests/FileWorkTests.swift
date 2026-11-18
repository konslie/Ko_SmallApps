import XCTest
@testable import mqdirCore

final class FileWorkTests: XCTestCase {
    func testDropMovesByDefaultAndOptionCopiesWithUndo() throws {
        let root = try fixture()
        defer { try? FileManager.default.removeItem(at: root) }
        let folder = root.appendingPathComponent("destination")
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: false)
        let source = root.appendingPathComponent("file.txt")
        try Data("test".utf8).write(to: source)

        for forceCopy in [false, true] {
            let outcome = FileOperationService.perform(
                FileWorkRequest(kind: .drop, sources: [source], destination: folder, forceCopy: forceCopy),
                sources: [source], cancellation: .init())
            XCTAssertEqual(outcome.status, .succeeded)
            let destination = try XCTUnwrap(outcome.destination)
            XCTAssertTrue(FileManager.default.fileExists(atPath: destination.path))
            XCTAssertEqual(FileManager.default.fileExists(atPath: source.path), forceCopy)
            try XCTUnwrap(outcome.undoReceipt).apply(cancellation: .init())
            XCTAssertTrue(FileManager.default.fileExists(atPath: source.path))
            XCTAssertFalse(FileManager.default.fileExists(atPath: destination.path))
        }
    }

    func testMoveToSameFolderThroughAliasSkipsWithoutRenamingSource() throws {
        let root = try fixture()
        defer { try? FileManager.default.removeItem(at: root) }
        let folder = root.appendingPathComponent("files")
        let alias = root.appendingPathComponent("alias")
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: false)
        try FileManager.default.createSymbolicLink(at: alias, withDestinationURL: folder)
        let source = folder.appendingPathComponent("file.txt")
        try Data().write(to: source)

        for kind: FileWorkKind in [.move, .drop] {
            let result = FileOperationService.perform(
                FileWorkRequest(kind: kind, sources: [source], destination: alias),
                sources: [source], cancellation: .init())
            XCTAssertEqual(result.status, .skipped("Already in this folder"))
            XCTAssertEqual(try FileManager.default.contentsOfDirectory(atPath: folder.path), ["file.txt"])
        }
    }

    func testMoveToUnwritableFolderKeepsSource() throws {
        let root = try fixture()
        let destination = root.appendingPathComponent("read-only")
        defer {
            try? FileManager.default.setAttributes([.posixPermissions: 0o700], ofItemAtPath: destination.path)
            try? FileManager.default.removeItem(at: root)
        }
        try FileManager.default.createDirectory(at: destination, withIntermediateDirectories: false)
        try FileManager.default.setAttributes([.posixPermissions: 0o500], ofItemAtPath: destination.path)
        try XCTSkipIf(FileManager.default.isWritableFile(atPath: destination.path),
                      "Current user can write to the read-only fixture")
        let source = root.appendingPathComponent("file.txt")
        try Data("source".utf8).write(to: source)

        let outcome = FileOperationService.perform(
            FileWorkRequest(kind: .move, sources: [source], destination: destination),
            sources: [source], cancellation: .init())
        guard case .failed = outcome.status else { return XCTFail("Expected permission failure") }
        XCTAssertEqual(try Data(contentsOf: source), Data("source".utf8))
        XCTAssertTrue(try FileManager.default.contentsOfDirectory(atPath: destination.path).isEmpty)
    }

    func testCopyInPlaceReportsActualRenamedDestination() throws {
        let root = try fixture()
        defer { try? FileManager.default.removeItem(at: root) }
        let source = root.appendingPathComponent("file.txt")
        try Data("original".utf8).write(to: source)
        let result = FileOperationService.perform(FileWorkRequest(kind: .copy, sources: [source], destination: root),
            sources: [source], cancellation: .init())
        XCTAssertEqual(result.status, .succeeded)
        XCTAssertEqual(result.destination?.lastPathComponent, "file 2.txt")
        XCTAssertEqual(try Data(contentsOf: XCTUnwrap(result.destination)), Data("original".utf8))
        XCTAssertTrue(FileManager.default.fileExists(atPath: source.path))
    }

    func testSkippedAndFailedAreNotReportedAsSuccessful() throws {
        let root = try fixture()
        defer { try? FileManager.default.removeItem(at: root) }
        let folder = root.appendingPathComponent("folder")
        let child = folder.appendingPathComponent("child")
        try FileManager.default.createDirectory(at: child, withIntermediateDirectories: true)
        let skipped = FileOperationService.transferOutcome(folder, into: child, move: true)
        guard case .skipped = skipped.status else { return XCTFail("Expected explicit skipped result") }
        let missing = root.appendingPathComponent("missing")
        let failed = FileOperationService.transferOutcome(missing, into: folder, move: false)
        XCTAssertTrue(failed.needsRetry)
        XCTAssertNotEqual(failed.status, .succeeded)
    }

    func testChangeScopeExcludesUnrelatedFolders() {
        let root = URL(fileURLWithPath: "/fixture/project")
        XCTAssertFalse(FileChangeScope.affects(root: root, changedFolders: [URL(fileURLWithPath: "/fixture/other")], recursive: true))
        XCTAssertFalse(FileChangeScope.affects(root: root, changedFolders: [URL(fileURLWithPath: "/fixture/project/deep/nested")], recursive: false))
        XCTAssertTrue(FileChangeScope.affects(root: root, changedFolders: [URL(fileURLWithPath: "/fixture/project/deep/nested")], recursive: true))
        XCTAssertTrue(FileChangeScope.affects(root: root, changedFolders: nil, recursive: false))
    }

    private func fixture() throws -> URL {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        return root
    }
}
