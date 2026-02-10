// Chapter reader view - vertical/horizontal scroll with zoom and night mode

import SwiftUI

struct ReaderView: View {
    let mangaTitle: String
    let chapter: Chapter
    let chapters: [Chapter]

    @EnvironmentObject var appState: AppState
    @Environment(\.dismiss) private var dismiss
    @State private var pages: [Page] = []
    @State private var isLoading = true
    @State private var currentPage = 0
    @State private var isVerticalMode = true
    @State private var isNightMode = false
    @State private var showToolbar = true
    @State private var error: String?

    var body: some View {
        ZStack {
            // Background
            (isNightMode ? Color.black : Color(uiColor: .systemBackground))
                .ignoresSafeArea()

            if isLoading {
                ProgressView("Loading pages...")
            } else if let error {
                VStack {
                    Image(systemName: "exclamationmark.triangle")
                        .font(.largeTitle)
                    Text(error)
                        .foregroundColor(.secondary)
                }
            } else if isVerticalMode {
                verticalReader
            } else {
                horizontalReader
            }

            // Overlay toolbar
            if showToolbar {
                VStack {
                    toolbar
                    Spacer()
                    bottomBar
                }
            }
        }
        .navigationBarHidden(true)
        .statusBarHidden(!showToolbar)
        .onTapGesture { withAnimation { showToolbar.toggle() } }
        .task { await loadPages() }
    }

    // MARK: - Vertical Scroll Reader

    private var verticalReader: some View {
        ScrollView {
            LazyVStack(spacing: 0) {
                ForEach(pages) { page in
                    AsyncImage(url: URL(string: page.imageUrl)) { phase in
                        switch phase {
                        case .success(let image):
                            image
                                .resizable()
                                .aspectRatio(contentMode: .fit)
                                .if(isNightMode) { $0.colorInvert() }
                        case .failure:
                            VStack {
                                Image(systemName: "photo")
                                Text("Failed to load page \(page.id + 1)")
                            }
                            .frame(height: 400)
                            .frame(maxWidth: .infinity)
                            .foregroundColor(.gray)
                        default:
                            ProgressView()
                                .frame(height: 400)
                                .frame(maxWidth: .infinity)
                        }
                    }
                }
            }
        }
    }

    // MARK: - Horizontal Page Reader

    private var horizontalReader: some View {
        TabView(selection: $currentPage) {
            ForEach(pages) { page in
                AsyncImage(url: URL(string: page.imageUrl)) { phase in
                    switch phase {
                    case .success(let image):
                        image
                            .resizable()
                            .aspectRatio(contentMode: .fit)
                            .if(isNightMode) { $0.colorInvert() }
                    case .failure:
                        VStack {
                            Image(systemName: "photo")
                            Text("Failed to load")
                        }
                        .foregroundColor(.gray)
                    default:
                        ProgressView()
                    }
                }
                .tag(page.id)
            }
        }
        .tabViewStyle(.page(indexDisplayMode: .never))
    }

    // MARK: - Toolbar

    private var toolbar: some View {
        HStack {
            Button { dismiss() } label: {
                Image(systemName: "chevron.left")
                    .padding(8)
                    .background(.ultraThinMaterial)
                    .clipShape(Circle())
            }

            VStack(alignment: .leading) {
                Text(mangaTitle)
                    .font(.caption)
                    .lineLimit(1)
                Text(chapter.name)
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }

            Spacer()

            Button {
                isVerticalMode.toggle()
            } label: {
                Image(systemName: isVerticalMode ? "arrow.left.arrow.right" : "arrow.up.arrow.down")
                    .padding(8)
                    .background(.ultraThinMaterial)
                    .clipShape(Circle())
            }

            Button {
                isNightMode.toggle()
            } label: {
                Image(systemName: isNightMode ? "sun.max" : "moon")
                    .padding(8)
                    .background(.ultraThinMaterial)
                    .clipShape(Circle())
            }
        }
        .padding(.horizontal)
        .padding(.top, 8)
        .background(.ultraThinMaterial)
    }

    private var bottomBar: some View {
        HStack {
            Text("\(currentPage + 1) / \(pages.count)")
                .font(.caption)
                .monospacedDigit()
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
                .background(.ultraThinMaterial)
                .clipShape(Capsule())
        }
        .padding(.bottom, 16)
    }

    // MARK: - Data loading

    private func loadPages() async {
        guard let source = appState.getSource(for: Manga(id: chapter.mangaId, title: "")) else {
            error = "Source not available"
            isLoading = false
            return
        }

        do {
            pages = try await source.getPageList(chapterId: chapter.id)
            if pages.isEmpty {
                error = "No pages found"
            }
        } catch {
            self.error = error.localizedDescription
        }

        isLoading = false
    }
}

// Conditional modifier
extension View {
    @ViewBuilder
    func `if`<Transform: View>(_ condition: Bool, transform: (Self) -> Transform) -> some View {
        if condition {
            transform(self)
        } else {
            self
        }
    }
}
