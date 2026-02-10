// Extension repository parser

import Foundation

class RepoParser {
    private let network: NetworkService

    init(network: NetworkService = .shared) {
        self.network = network
    }

    /// Fetch and parse a Tachiyomi-compatible extension repository index
    func fetchRepo(url: String) async -> ExtensionRepo? {
        do {
            let data = try await network.get(url: url)

            let json = try JSONSerialization.jsonObject(with: data)
            var extensionInfos: [ExtensionInfo] = []

            // Try as array first (index.min.json format)
            if let array = json as? [[String: Any]] {
                extensionInfos = parseExtensionList(array, baseUrl: url)
            }
            // Try as dict with extensions key
            else if let dict = json as? [String: Any],
                    let array = (dict["extensions"] ?? dict["data"]) as? [[String: Any]] {
                extensionInfos = parseExtensionList(array, baseUrl: url)
            }

            let repoName = extractRepoName(from: url)

            return ExtensionRepo(
                url: url,
                name: repoName,
                extensions: extensionInfos
            )
        } catch {
            print("Failed to fetch repo \(url): \(error)")
            return nil
        }
    }

    private func parseExtensionList(_ items: [[String: Any]], baseUrl: String) -> [ExtensionInfo] {
        let decoder = JSONDecoder()

        return items.compactMap { item in
            guard let jsonData = try? JSONSerialization.data(withJSONObject: item) else {
                return nil
            }
            return try? decoder.decode(ExtensionInfo.self, from: jsonData)
        }
    }

    private func extractRepoName(from url: String) -> String {
        // Extract GitHub username/repo from URL
        let components = url.replacingOccurrences(of: "https://", with: "")
            .replacingOccurrences(of: "http://", with: "")
            .split(separator: "/")
        if components.count >= 2 {
            return String(components[1])
        }
        return url
    }
}
