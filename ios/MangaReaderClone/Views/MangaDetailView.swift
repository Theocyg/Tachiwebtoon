// Manga detail view - shows info and chapter list

import SwiftUI

struct MangaDetailView: View {
    @EnvironmentObject var appState: AppState
    let manga: Manga
    @State private var chapters: [Chapter] = []
    @State private var isLoading = true
    @State private var isInLibrary = false
    @State private var detailedManga: Manga?

    private var displayManga: Manga { detailedManga ?? manga }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                // Header with cover and info
                HStack(alignment: .top, spacing: 16) {
                    // Cover
                    AsyncImage(url: URL(string: displayManga.coverUrl)) { phase in
                        switch phase {
                        case .success(let image):
                            image.resizable().aspectRatio(contentMode: .fit)
                        default:
                            Rectangle().fill(Color.gray.opacity(0.3))
                                .overlay { ProgressView() }
                        }
                    }
                    .frame(width: 130, height: 190)
                    .clipShape(RoundedRectangle(cornerRadius: 8))

                    // Info
                    VStack(alignment: .leading, spacing: 6) {
                        Text(displayManga.title)
                            .font(.title2)
                            .fontWeight(.bold)

                        if !displayManga.author.isEmpty {
                            Label(displayManga.author, systemImage: "person")
                                .font(.subheadline)
                                .foregroundColor(.secondary)
                        }

                        Text(displayManga.status.displayName)
                            .font(.caption)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                            .background(.pink.opacity(0.2))
                            .clipShape(Capsule())

                        // Genres
                        FlowLayout(spacing: 4) {
                            ForEach(displayManga.genres, id: \.self) { genre in
                                Text(genre)
                                    .font(.caption2)
                                    .padding(.horizontal, 6)
                                    .padding(.vertical, 2)
                                    .background(Color.purple.opacity(0.2))
                                    .clipShape(Capsule())
                            }
                        }
                    }
                }
                .padding()

                // Library button
                Button {
                    Task { await toggleLibrary() }
                } label: {
                    Label(
                        isInLibrary ? "In Library" : "Add to Library",
                        systemImage: isInLibrary ? "heart.fill" : "heart"
                    )
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 12)
                }
                .buttonStyle(.borderedProminent)
                .tint(isInLibrary ? .pink : .purple)
                .padding(.horizontal)

                // Description
                if !displayManga.description.isEmpty {
                    Text(displayManga.description)
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                        .padding()
                        .lineLimit(6)
                }

                Divider().padding(.horizontal)

                // Chapters
                HStack {
                    Text("Chapters (\(chapters.count))")
                        .font(.headline)
                    Spacer()
                }
                .padding()

                if isLoading {
                    ProgressView()
                        .frame(maxWidth: .infinity)
                        .padding()
                } else {
                    LazyVStack(spacing: 0) {
                        ForEach(chapters) { chapter in
                            NavigationLink {
                                ReaderView(
                                    mangaTitle: displayManga.title,
                                    chapter: chapter,
                                    chapters: chapters
                                )
                            } label: {
                                ChapterRow(chapter: chapter)
                            }
                            Divider()
                        }
                    }
                }
            }
        }
        .navigationTitle(displayManga.title)
        .navigationBarTitleDisplayMode(.inline)
        .task { await loadData() }
    }

    private func loadData() async {
        isInLibrary = await appState.databaseService.isInLibrary(mangaId: manga.id)

        guard let source = appState.getSource(for: manga) else {
            isLoading = false
            return
        }

        // Load details
        do {
            detailedManga = try await source.getMangaDetails(mangaId: manga.id)
        } catch {
            print("Failed to load details: \(error)")
        }

        // Load chapters
        do {
            chapters = try await source.getChapterList(mangaId: manga.id)
        } catch {
            print("Failed to load chapters: \(error)")
        }

        isLoading = false
    }

    private func toggleLibrary() async {
        if isInLibrary {
            await appState.databaseService.removeFromLibrary(mangaId: manga.id)
        } else {
            await appState.databaseService.addToLibrary(displayManga)
        }
        isInLibrary.toggle()
        await appState.loadLibrary()
    }
}

struct ChapterRow: View {
    let chapter: Chapter

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text(chapter.name)
                    .font(.subheadline)
                    .foregroundColor(.primary)

                HStack(spacing: 8) {
                    if !chapter.scanlator.isEmpty {
                        Text(chapter.scanlator)
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    if let date = chapter.dateUpload {
                        Text(date, style: .date)
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }
            }
            Spacer()
            Image(systemName: "chevron.right")
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .padding(.horizontal)
        .padding(.vertical, 10)
        .contentShape(Rectangle())
    }
}

/// Simple flow layout for genre tags
struct FlowLayout: Layout {
    var spacing: CGFloat = 4

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let result = layout(proposal: proposal, subviews: subviews)
        return result.size
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        let result = layout(proposal: proposal, subviews: subviews)
        for (index, origin) in result.origins.enumerated() {
            subviews[index].place(at: CGPoint(x: bounds.minX + origin.x, y: bounds.minY + origin.y), proposal: .unspecified)
        }
    }

    private func layout(proposal: ProposedViewSize, subviews: Subviews) -> (size: CGSize, origins: [CGPoint]) {
        let maxWidth = proposal.width ?? .infinity
        var origins: [CGPoint] = []
        var x: CGFloat = 0
        var y: CGFloat = 0
        var maxHeight: CGFloat = 0
        var rowHeight: CGFloat = 0

        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified)
            if x + size.width > maxWidth && x > 0 {
                x = 0
                y += rowHeight + spacing
                rowHeight = 0
            }
            origins.append(CGPoint(x: x, y: y))
            rowHeight = max(rowHeight, size.height)
            x += size.width + spacing
            maxHeight = max(maxHeight, y + rowHeight)
        }

        return (CGSize(width: maxWidth, height: maxHeight), origins)
    }
}

extension MangaStatus {
    var displayName: String {
        switch self {
        case .unknown: return "Unknown"
        case .ongoing: return "Ongoing"
        case .completed: return "Completed"
        case .licensed: return "Licensed"
        case .publishingFinished: return "Finished"
        case .cancelled: return "Cancelled"
        case .onHiatus: return "On Hiatus"
        }
    }
}
