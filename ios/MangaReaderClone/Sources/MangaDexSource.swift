// MangaDex source - uses the official MangaDex API v5

import Foundation

class MangaDexSource: MangaSource {
    let name = "MangaDex"
    let baseUrl = "https://mangadex.org"
    let lang = "en"

    private let apiBase = "https://api.mangadex.org"
    private let network: NetworkService

    init(network: NetworkService) {
        self.network = network
    }

    // MARK: - Popular

    func fetchPopularManga(page: Int) async throws -> [Manga] {
        let limit = 20
        let offset = (page - 1) * limit
        let url = "\(apiBase)/manga?limit=\(limit)&offset=\(offset)&order[followedCount]=desc&includes[]=cover_art&includes[]=author&includes[]=artist&availableTranslatedLanguage[]=en&hasAvailableChapters=true&contentRating[]=safe&contentRating[]=suggestive"

        guard let data = try await network.getJSON(url: url) else {
            return []
        }

        return parseMangaList(data)
    }

    // MARK: - Search

    func searchManga(query: String, page: Int) async throws -> [Manga] {
        let limit = 20
        let offset = (page - 1) * limit
        let encoded = query.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? query
        let url = "\(apiBase)/manga?title=\(encoded)&limit=\(limit)&offset=\(offset)&order[relevance]=desc&includes[]=cover_art&includes[]=author&includes[]=artist&availableTranslatedLanguage[]=en&contentRating[]=safe&contentRating[]=suggestive"

        guard let data = try await network.getJSON(url: url) else {
            return []
        }

        return parseMangaList(data)
    }

    // MARK: - Details

    func getMangaDetails(mangaId: String) async throws -> Manga {
        let url = "\(apiBase)/manga/\(mangaId)?includes[]=cover_art&includes[]=author&includes[]=artist"

        guard let data = try await network.getJSON(url: url),
              let mangaData = data["data"] as? [String: Any] else {
            throw URLError(.badServerResponse)
        }

        return parseManga(mangaData)
    }

    // MARK: - Chapters

    func getChapterList(mangaId: String) async throws -> [Chapter] {
        var chapters: [Chapter] = []
        var offset = 0
        let limit = 100

        while true {
            let url = "\(apiBase)/chapter?manga=\(mangaId)&translatedLanguage[]=en&limit=\(limit)&offset=\(offset)&order[chapter]=desc&includes[]=scanlation_group"

            guard let data = try await network.getJSON(url: url),
                  let items = data["data"] as? [[String: Any]] else {
                break
            }

            for item in items {
                let attrs = item["attributes"] as? [String: Any] ?? [:]
                let id = item["id"] as? String ?? ""
                let chNum = attrs["chapter"] as? String
                let chTitle = attrs["title"] as? String ?? ""
                let chapterNumber = Double(chNum ?? "0") ?? 0

                var name = "Chapter \(chNum ?? "?")"
                if !chTitle.isEmpty { name += " - \(chTitle)" }

                // Scanlator
                var scanlator = ""
                if let rels = item["relationships"] as? [[String: Any]] {
                    for rel in rels {
                        if rel["type"] as? String == "scanlation_group",
                           let relAttrs = rel["attributes"] as? [String: Any] {
                            scanlator = relAttrs["name"] as? String ?? ""
                            break
                        }
                    }
                }

                // Date
                var dateUpload: Date?
                if let dateStr = attrs["publishAt"] as? String {
                    let formatter = ISO8601DateFormatter()
                    formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
                    dateUpload = formatter.date(from: dateStr)
                }

                chapters.append(Chapter(
                    id: id,
                    mangaId: mangaId,
                    name: name,
                    url: "\(baseUrl)/chapter/\(id)",
                    chapterNumber: chapterNumber,
                    dateUpload: dateUpload,
                    scanlator: scanlator
                ))
            }

            let total = data["total"] as? Int ?? 0
            offset += limit
            if offset >= total { break }
        }

        return chapters
    }

    // MARK: - Pages

    func getPageList(chapterId: String) async throws -> [Page] {
        let url = "\(apiBase)/at-home/server/\(chapterId)"

        guard let data = try await network.getJSON(url: url) else {
            throw URLError(.badServerResponse)
        }

        let baseServer = data["baseUrl"] as? String ?? ""
        let chapter = data["chapter"] as? [String: Any] ?? [:]
        let hash = chapter["hash"] as? String ?? ""
        let pageFilenames = chapter["data"] as? [String] ?? []

        return pageFilenames.enumerated().map { index, filename in
            Page(
                index: index,
                imageUrl: "\(baseServer)/data/\(hash)/\(filename)",
                chapterId: chapterId
            )
        }
    }

    // MARK: - Parsing

    private func parseMangaList(_ data: [String: Any]) -> [Manga] {
        guard let items = data["data"] as? [[String: Any]] else { return [] }
        return items.compactMap { parseManga($0) }
    }

    private func parseManga(_ data: [String: Any]) -> Manga {
        let id = data["id"] as? String ?? ""
        let attrs = data["attributes"] as? [String: Any] ?? [:]
        let relationships = data["relationships"] as? [[String: Any]] ?? []

        // Title
        let titles = attrs["title"] as? [String: String] ?? [:]
        let title = titles["en"] ?? titles["ja-ro"] ?? titles.values.first ?? "Unknown"

        // Description
        let descriptions = attrs["description"] as? [String: String] ?? [:]
        let description = descriptions["en"] ?? descriptions.values.first ?? ""

        // Cover
        var coverUrl = ""
        for rel in relationships {
            if rel["type"] as? String == "cover_art",
               let relAttrs = rel["attributes"] as? [String: Any],
               let filename = relAttrs["fileName"] as? String {
                coverUrl = "https://uploads.mangadex.org/covers/\(id)/\(filename).256.jpg"
                break
            }
        }

        // Author/Artist
        var author = ""
        var artist = ""
        for rel in relationships {
            let relType = rel["type"] as? String ?? ""
            let relAttrs = rel["attributes"] as? [String: Any] ?? [:]
            let relName = relAttrs["name"] as? String ?? ""
            if relType == "author" && author.isEmpty { author = relName }
            if relType == "artist" && artist.isEmpty { artist = relName }
        }

        // Status
        let statusMap: [String: MangaStatus] = [
            "ongoing": .ongoing, "completed": .completed,
            "hiatus": .onHiatus, "cancelled": .cancelled,
        ]
        let status = statusMap[attrs["status"] as? String ?? ""] ?? .unknown

        // Tags
        var genres: [String] = []
        if let tags = attrs["tags"] as? [[String: Any]] {
            for tag in tags {
                if let tagAttrs = tag["attributes"] as? [String: Any],
                   let tagName = (tagAttrs["name"] as? [String: String])?["en"] {
                    genres.append(tagName)
                }
            }
        }

        return Manga(
            id: id, title: title, coverUrl: coverUrl,
            description: description, author: author,
            artist: artist.isEmpty ? author : artist,
            status: status, genres: genres,
            sourceId: "en/mangadex",
            url: "\(baseUrl)/title/\(id)"
        )
    }
}
