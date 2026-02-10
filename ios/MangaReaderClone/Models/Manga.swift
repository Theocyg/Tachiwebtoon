// Data models for manga, chapters, and pages

import Foundation

enum MangaStatus: Int, Codable {
    case unknown = 0
    case ongoing = 1
    case completed = 2
    case licensed = 3
    case publishingFinished = 4
    case cancelled = 5
    case onHiatus = 6
}

struct Manga: Identifiable, Codable, Hashable {
    let id: String
    var title: String
    var coverUrl: String
    var description: String
    var author: String
    var artist: String
    var status: MangaStatus
    var genres: [String]
    var sourceId: String
    var url: String
    var inLibrary: Bool
    var lastUpdated: Date?

    init(
        id: String,
        title: String,
        coverUrl: String = "",
        description: String = "",
        author: String = "",
        artist: String = "",
        status: MangaStatus = .unknown,
        genres: [String] = [],
        sourceId: String = "",
        url: String = "",
        inLibrary: Bool = false,
        lastUpdated: Date? = nil
    ) {
        self.id = id
        self.title = title
        self.coverUrl = coverUrl
        self.description = description
        self.author = author
        self.artist = artist
        self.status = status
        self.genres = genres
        self.sourceId = sourceId
        self.url = url
        self.inLibrary = inLibrary
        self.lastUpdated = lastUpdated
    }

    func hash(into hasher: inout Hasher) {
        hasher.combine(id)
    }

    static func == (lhs: Manga, rhs: Manga) -> Bool {
        lhs.id == rhs.id
    }
}

struct Chapter: Identifiable, Codable {
    let id: String
    let mangaId: String
    var name: String
    var url: String
    var chapterNumber: Double
    var dateUpload: Date?
    var scanlator: String
    var language: String
    var downloaded: Bool

    init(
        id: String,
        mangaId: String,
        name: String,
        url: String = "",
        chapterNumber: Double = 0,
        dateUpload: Date? = nil,
        scanlator: String = "",
        language: String = "en",
        downloaded: Bool = false
    ) {
        self.id = id
        self.mangaId = mangaId
        self.name = name
        self.url = url
        self.chapterNumber = chapterNumber
        self.dateUpload = dateUpload
        self.scanlator = scanlator
        self.language = language
        self.downloaded = downloaded
    }
}

struct Page: Identifiable {
    let id: Int  // index
    let imageUrl: String
    let chapterId: String
    var localPath: String?

    var isDownloaded: Bool { localPath != nil }

    init(index: Int, imageUrl: String, chapterId: String = "", localPath: String? = nil) {
        self.id = index
        self.imageUrl = imageUrl
        self.chapterId = chapterId
        self.localPath = localPath
    }
}

struct ExtensionInfo: Identifiable, Codable {
    var id: String { pkg }
    let pkg: String
    let name: String
    let apk: String
    let lang: String
    let code: Int
    let version: String
    let nsfw: Int
    let sources: [[String: AnyCodable]]?
    let iconUrl: String?

    enum CodingKeys: String, CodingKey {
        case pkg, name, apk, lang, code, version, nsfw, sources
        case iconUrl = "icon"
    }
}

/// Type-erased Codable wrapper for JSON values
struct AnyCodable: Codable {
    let value: Any

    init(_ value: Any) { self.value = value }

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let int = try? container.decode(Int.self) { value = int }
        else if let double = try? container.decode(Double.self) { value = double }
        else if let string = try? container.decode(String.self) { value = string }
        else if let bool = try? container.decode(Bool.self) { value = bool }
        else { value = "" }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        if let int = value as? Int { try container.encode(int) }
        else if let double = value as? Double { try container.encode(double) }
        else if let string = value as? String { try container.encode(string) }
        else if let bool = value as? Bool { try container.encode(bool) }
    }
}

struct ExtensionRepo {
    let url: String
    var name: String
    var extensions: [ExtensionInfo]
}
