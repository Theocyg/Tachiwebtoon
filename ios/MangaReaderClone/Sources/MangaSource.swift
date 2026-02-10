// MangaSource protocol - interface all manga sources must implement

import Foundation

/// Protocol that all manga sources must conform to.
/// Equivalent to Tachiyomi's HttpSource interface.
protocol MangaSource {
    var name: String { get }
    var baseUrl: String { get }
    var lang: String { get }
    var sourceId: String { get }

    func fetchPopularManga(page: Int) async throws -> [Manga]
    func searchManga(query: String, page: Int) async throws -> [Manga]
    func getMangaDetails(mangaId: String) async throws -> Manga
    func getChapterList(mangaId: String) async throws -> [Chapter]
    func getPageList(chapterId: String) async throws -> [Page]
}

extension MangaSource {
    var sourceId: String {
        "\(lang)/\(name.lowercased().replacingOccurrences(of: " ", with: "_"))"
    }
}
