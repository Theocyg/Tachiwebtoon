// Settings view

import SwiftUI

struct SettingsView: View {
    @AppStorage("readingMode") private var readingMode = 0
    @AppStorage("nightModeDefault") private var nightModeDefault = false

    var body: some View {
        NavigationStack {
            Form {
                Section("Reader") {
                    Picker("Default Reading Mode", selection: $readingMode) {
                        Text("Vertical Scroll").tag(0)
                        Text("Horizontal (Page)").tag(1)
                    }
                    Toggle("Night Mode by Default", isOn: $nightModeDefault)
                }

                Section("Storage") {
                    Button("Clear All Downloads", role: .destructive) {
                        clearDownloads()
                    }
                }

                Section("About") {
                    LabeledContent("Version", value: "1.0.0")
                    LabeledContent("App", value: "MangaReaderClone")
                    Text("A cross-platform manga reader inspired by Tachiyomi. For educational purposes only.")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
            .navigationTitle("Settings")
        }
    }

    private func clearDownloads() {
        let downloadDir = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("downloads")
        try? FileManager.default.removeItem(at: downloadDir)
        try? FileManager.default.createDirectory(at: downloadDir, withIntermediateDirectories: true)
    }
}
