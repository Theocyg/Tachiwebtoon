// Extensions view - manage extension repos

import SwiftUI

struct ExtensionsView: View {
    @EnvironmentObject var appState: AppState
    @State private var repoUrl = ""
    @State private var repos: [String] = []
    @State private var extensions: [ExtensionInfo] = []
    @State private var isLoading = false
    @State private var filterText = ""

    private var filteredExtensions: [ExtensionInfo] {
        if filterText.isEmpty { return extensions }
        return extensions.filter {
            $0.name.localizedCaseInsensitiveContains(filterText) ||
            $0.pkg.localizedCaseInsensitiveContains(filterText)
        }
    }

    var body: some View {
        NavigationStack {
            List {
                // Add repo section
                Section("Add Repository") {
                    HStack {
                        TextField("Repo URL", text: $repoUrl)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                        Button("Add") {
                            Task { await addRepo() }
                        }
                        .disabled(repoUrl.isEmpty)
                    }
                }

                // Repos section
                Section("Repositories (\(repos.count))") {
                    ForEach(repos, id: \.self) { url in
                        Text(url)
                            .font(.caption)
                            .lineLimit(2)
                    }
                    .onDelete { indexSet in
                        Task {
                            for index in indexSet {
                                await appState.databaseService.removeRepo(repos[index])
                            }
                            await loadRepos()
                        }
                    }
                }

                // Extensions section
                Section("Available Extensions (\(filteredExtensions.count))") {
                    if isLoading {
                        ProgressView()
                    } else {
                        ForEach(filteredExtensions) { ext in
                            HStack {
                                VStack(alignment: .leading) {
                                    HStack {
                                        Text(ext.name)
                                            .fontWeight(.medium)
                                        if ext.nsfw != 0 {
                                            Text("NSFW")
                                                .font(.caption2)
                                                .padding(.horizontal, 4)
                                                .padding(.vertical, 2)
                                                .background(.red.opacity(0.2))
                                                .clipShape(Capsule())
                                        }
                                    }
                                    Text("\(ext.lang) | v\(ext.version)")
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                }
                                Spacer()
                            }
                        }
                    }
                }
            }
            .navigationTitle("Extensions")
            .searchable(text: $filterText, prompt: "Filter extensions...")
            .refreshable { await refreshAll() }
            .task { await loadRepos() }
        }
    }

    private func addRepo() async {
        guard !repoUrl.isEmpty else { return }
        await appState.databaseService.addRepo(repoUrl)
        repoUrl = ""
        await loadRepos()
        await refreshAll()
    }

    private func loadRepos() async {
        repos = await appState.databaseService.getRepos()
    }

    private func refreshAll() async {
        isLoading = true
        extensions = []

        for url in repos {
            if let repo = await appState.repoParser.fetchRepo(url: url) {
                extensions.append(contentsOf: repo.extensions)
            }
        }

        extensions.sort { $0.name < $1.name }
        isLoading = false
    }
}
