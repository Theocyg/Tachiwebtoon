// swift-tools-version: 5.9
// Swift Package Manager configuration for MangaReaderClone iOS

import PackageDescription

let package = Package(
    name: "MangaReaderClone",
    platforms: [
        .iOS(.v16),
        .macOS(.v13),
    ],
    dependencies: [
        // HTML parsing (equivalent to SwiftSoup via SPM)
        .package(url: "https://github.com/scinfu/SwiftSoup.git", from: "2.7.0"),
        // Image loading with caching
        .package(url: "https://github.com/onevcat/Kingfisher.git", from: "7.10.0"),
        // HTTP networking
        .package(url: "https://github.com/Alamofire/Alamofire.git", from: "5.9.0"),
    ],
    targets: [
        .executableTarget(
            name: "MangaReaderClone",
            dependencies: [
                "SwiftSoup",
                "Kingfisher",
                "Alamofire",
            ],
            path: "MangaReaderClone"
        ),
    ]
)
