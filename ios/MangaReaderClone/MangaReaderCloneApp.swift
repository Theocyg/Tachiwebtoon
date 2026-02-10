// MangaReaderClone - iOS App Entry Point
// A manga reader inspired by Tachiyomi with modular extension system

import SwiftUI

@main
struct MangaReaderCloneApp: App {
    @StateObject private var appState = AppState()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(appState)
                .preferredColorScheme(.dark)
        }
    }
}

/// Central application state
@MainActor
class AppState: ObservableObject {
    @Published var sources: [any MangaSource] = []
    @Published var library: [Manga] = []
    @Published var isLoading = false

    let databaseService = DatabaseService()
    let networkService = NetworkService()
    let repoParser = RepoParser()

    init() {
        // Register built-in sources
        sources = [MangaDexSource(network: networkService)]

        Task {
            await databaseService.initialize()
            await loadLibrary()
        }
    }

    func loadLibrary() async {
        library = await databaseService.getLibrary()
    }

    func getSource(for manga: Manga) -> (any MangaSource)? {
        // For MangaDex UUIDs
        if manga.id.count == 36 && manga.id.contains("-") {
            return sources.first { $0.name == "MangaDex" }
        }
        return sources.first
    }
}
