import UniformTypeIdentifiers
import XCTest

final class DragDropSupportTests: XCTestCase {
    @MainActor
    func testDropLoadsAllFileURLProvidersInOrder() async {
        let paths = ["first.txt", "second.txt"].map { "/tmp/mqdir-drop/" + $0 }
        let urls = paths.map { URL(fileURLWithPath: $0) }
        let providers = urls.map { url in
            let provider = NSItemProvider()
            provider.registerDataRepresentation(forTypeIdentifier: UTType.fileURL.identifier,
                                                visibility: .all) { completion in
                completion(Data(url.absoluteString.utf8), nil)
                return nil
            }
            return provider
        }
        let result = await DragDropSupport.beginResolvingURLs(from: providers).value
        XCTAssertEqual(result, urls)
    }
}
