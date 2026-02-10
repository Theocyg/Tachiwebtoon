// Search view - search manga across installed sources

import SwiftUI

struct SearchView: View {
    @EnvironmentObject var appState: AppState
    @State private var query = ""
    @State private var results: [Manga] = []
    @State private var isSearching = false
    @State private var selectedSourceIndex = 0

    private var columns: [GridItem] {
        [GridItem(.adaptive(minimum: 120), spacing: 12)]
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // Source picker
                if !appState.sources.isEmpty {
                    Picker("Source", selection: $selectedSourceIndex) {
                        ForEach(appState.sources.indices, id: \.self) { i in
                            Text(appState.sources[i].name).tag(i)
                        }
                    }
                    .pickerStyle(.segmented)
                    .padding(.horizontal)
                    .padding(.top, 8)
                }

                // Results
                if isSearching {
                    Spacer()
                    ProgressView("Searching...")
                    Spacer()
                } else if results.isEmpty && !query.isEmpty {
                    Spacer()
                    Text("No results found")
                        .foregroundColor(.secondary)
                    Spacer()
                } else {
                    ScrollView {
                        LazyVGrid(columns: columns, spacing: 12) {
                            ForEach(results) { manga in
                                NavigationLink(value: manga) {
                                    MangaCoverCard(manga: manga)
                                }
                            }
                        }
                        .padding()
                    }
                }
            }
            .navigationTitle("Search")
            .navigationDestination(for: Manga.self) { manga in
                MangaDetailView(manga: manga)
            }
            .searchable(text: $query, prompt: "Search manga...")
            .onSubmit(of: .search) {
                Task { await search() }
            }
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button("Popular") {
                        Task { await browsePopular() }
                    }
                }
            }
        }
    }

    private func search() async {
        guard !query.isEmpty, selectedSourceIndex < appState.sources.count else { return }
        isSearching = true
        do {
            let source = appState.sources[selectedSourceIndex]
            results = try await source.searchManga(query: query, page: 1)
        } catch {
            print("Search error: \(error)")
        }
        isSearching = false
    }

    private func browsePopular() async {
        guard selectedSourceIndex < appState.sources.count else { return }
        isSearching = true
        do {
            let source = appState.sources[selectedSourceIndex]
            results = try await source.fetchPopularManga(page: 1)
        } catch {
            print("Browse error: \(error)")
        }
        isSearching = false
    }
}
