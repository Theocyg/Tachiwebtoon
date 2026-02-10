// Library view - grid of manga in the user's collection

import SwiftUI

struct LibraryView: View {
    @EnvironmentObject var appState: AppState
    @State private var columns = [GridItem(.adaptive(minimum: 120), spacing: 12)]

    var body: some View {
        NavigationStack {
            Group {
                if appState.library.isEmpty {
                    VStack(spacing: 16) {
                        Image(systemName: "books.vertical")
                            .font(.system(size: 60))
                            .foregroundColor(.gray)
                        Text("Your library is empty")
                            .font(.title2)
                            .foregroundColor(.gray)
                        Text("Search for manga and add them\nto your library")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                            .multilineTextAlignment(.center)
                    }
                    .padding()
                } else {
                    ScrollView {
                        LazyVGrid(columns: columns, spacing: 12) {
                            ForEach(appState.library) { manga in
                                NavigationLink(value: manga) {
                                    MangaCoverCard(manga: manga)
                                }
                            }
                        }
                        .padding()
                    }
                }
            }
            .navigationTitle("Library")
            .navigationDestination(for: Manga.self) { manga in
                MangaDetailView(manga: manga)
            }
            .refreshable {
                await appState.loadLibrary()
            }
        }
    }
}

struct MangaCoverCard: View {
    let manga: Manga

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            // Cover image
            AsyncImage(url: URL(string: manga.coverUrl)) { phase in
                switch phase {
                case .success(let image):
                    image
                        .resizable()
                        .aspectRatio(contentMode: .fill)
                case .failure:
                    Rectangle()
                        .fill(Color.gray.opacity(0.3))
                        .overlay {
                            Image(systemName: "photo")
                                .foregroundColor(.gray)
                        }
                default:
                    Rectangle()
                        .fill(Color.gray.opacity(0.2))
                        .overlay { ProgressView() }
                }
            }
            .frame(width: 120, height: 170)
            .clipShape(RoundedRectangle(cornerRadius: 8))

            // Title
            Text(manga.title)
                .font(.caption)
                .fontWeight(.medium)
                .foregroundColor(.primary)
                .lineLimit(2)
                .frame(width: 120, alignment: .leading)
        }
    }
}
