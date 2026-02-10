// Network service for HTTP requests

import Foundation

class NetworkService {
    static let shared = NetworkService()

    private let session: URLSession

    init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        config.httpAdditionalHeaders = [
            "User-Agent": "MangaReaderClone/1.0"
        ]
        session = URLSession(configuration: config)
    }

    func get(url: String, headers: [String: String]? = nil) async throws -> Data {
        guard let url = URL(string: url) else {
            throw URLError(.badURL)
        }

        var request = URLRequest(url: url)
        headers?.forEach { request.setValue($1, forHTTPHeaderField: $0) }

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw URLError(.badServerResponse)
        }

        if httpResponse.statusCode == 429 {
            // Rate limited - wait and retry
            let retryAfter = Int(httpResponse.value(forHTTPHeaderField: "Retry-After") ?? "2") ?? 2
            try await Task.sleep(nanoseconds: UInt64(retryAfter) * 1_000_000_000)
            return try await get(url: url.absoluteString, headers: headers)
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            throw URLError(.badServerResponse)
        }

        return data
    }

    func getJSON(url: String, headers: [String: String]? = nil) async throws -> [String: Any]? {
        let data = try await get(url: url, headers: headers)
        return try JSONSerialization.jsonObject(with: data) as? [String: Any]
    }

    func getText(url: String, headers: [String: String]? = nil) async throws -> String {
        let data = try await get(url: url, headers: headers)
        return String(data: data, encoding: .utf8) ?? ""
    }
}
