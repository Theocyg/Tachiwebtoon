// Database service using UserDefaults + FileManager for simplicity
// (In production, use Core Data or SwiftData)

import Foundation

actor DatabaseService {
    private let libraryKey = "manga_library"
    private let reposKey = "extension_repos"
    private let defaults = UserDefaults.standard
    private let encoder = JSONEncoder()
    private let decoder = JSONDecoder()

    func initialize() {
        // Ensure storage directories exist
        let downloadDir = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("downloads")
        try? FileManager.default.createDirectory(at: downloadDir, withIntermediateDirectories: true)
    }

    // MARK: - Library

    func getLibrary() -> [Manga] {
        guard let data = defaults.data(forKey: libraryKey),
              let manga = try? decoder.decode([Manga].self, from: data) else {
            return []
        }
        return manga.sorted { $0.title < $1.title }
    }

    func addToLibrary(_ manga: Manga) {
        var library = getLibrary()
        if !library.contains(where: { $0.id == manga.id }) {
            var m = manga
            m.inLibrary = true
            library.append(m)
            saveLibrary(library)
        }
    }

    func removeFromLibrary(mangaId: String) {
        var library = getLibrary()
        library.removeAll { $0.id == mangaId }
        saveLibrary(library)
    }

    func isInLibrary(mangaId: String) -> Bool {
        getLibrary().contains { $0.id == mangaId }
    }

    private func saveLibrary(_ library: [Manga]) {
        if let data = try? encoder.encode(library) {
            defaults.set(data, forKey: libraryKey)
        }
    }

    // MARK: - Repos

    func getRepos() -> [String] {
        defaults.stringArray(forKey: reposKey) ?? []
    }

    func addRepo(_ url: String) {
        var repos = getRepos()
        if !repos.contains(url) {
            repos.append(url)
            defaults.set(repos, forKey: reposKey)
        }
    }

    func removeRepo(_ url: String) {
        var repos = getRepos()
        repos.removeAll { $0 == url }
        defaults.set(repos, forKey: reposKey)
    }
}
