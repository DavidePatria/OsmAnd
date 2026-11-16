import Foundation

/** Typed decoding rejects booleans/floats where the watch contract requires integers. */
struct JunctionScene: Codable {
    struct Anchor: Codable { let id: String; let routeIndex: Int; let point: [Int] }
    struct Path: Codable {
        let id: String
        let role: String
        let points: [[Int]]
        let anchorRefs: [[Reference]]
        let layer: Int?
        let segmentLayers: [Int]?
    }
    enum Reference: Codable {
        case text(String), index(Int)
        init(from decoder: Decoder) throws {
            let container = try decoder.singleValueContainer()
            if let text = try? container.decode(String.self) { self = .text(text) }
            else { self = .index(try container.decode(Int.self)) }
        }
        func encode(to encoder: Encoder) throws {
            var container = encoder.singleValueContainer()
            switch self { case .text(let text): try container.encode(text); case .index(let index): try container.encode(index) }
        }
    }
    let version: Int
    let session: String
    let generation: Int
    let seq: Int
    let state: String
    let geometryMode: String
    let reason: String
    let roadName: String
    let maneuver: String
    let radiusDm: Int
    let distanceM: Int
    var sourceAgeMs: Int
    var fixAgeMs: Int
    var progressAgeMs: Int?
    let speedDmps: Int?
    let anchors: [Anchor]
    let paths: [Path]
    let destination: [Int]?

    enum Invalid: Error { case snapshot }
    func validate() throws {
        func check(_ value: Bool) throws { if !value { throw Invalid.snapshot } }
        func text(_ value: String, _ minimum: Int = 0, _ maximum: Int = 80) -> Bool {
            (minimum...maximum).contains(value.utf16.count)
        }
        func point(_ value: [Int]) -> Bool {
            value.count == 2 && value.allSatisfy { (-radiusDm...radiusDm).contains($0) } &&
                value[0] * value[0] + value[1] * value[1] <= radiusDm * radiusDm
        }
        try check(version == 1 && text(session, 1, 64) && (0...1_000_000).contains(generation) && (0...1_000_000).contains(seq))
        try check(["active", "idle", "recalculating", "unavailable", "arrived"].contains(state))
        try check(["map_context", "layer_context", "routing_branches", "route_only", "unavailable"].contains(geometryMode))
        try check(text(reason) && text(roadName) && text(maneuver))
        try check((1...2000).contains(radiusDm) && (0...1_000_000).contains(distanceM))
        try check((0...60_000).contains(sourceAgeMs) && (0...60_000).contains(fixAgeMs))
        if progressAgeMs != nil || speedDmps != nil {
            try check(progressAgeMs.map { (0...60_000).contains($0) } == true && speedDmps.map { (0...700).contains($0) } == true)
        }
        let context = ["map_context", "layer_context"].contains(geometryMode)
        try check(anchors.count <= 4 && paths.count <= (context ? 40 : 8))
        var byID: [String: [Int]] = [:]
        for anchor in anchors {
            try check(text(anchor.id, 1, 32) && (0...1_000_000).contains(anchor.routeIndex) && point(anchor.point) && byID[anchor.id] == nil)
            byID[anchor.id] = anchor.point
        }
        var identifiers = Set<String>(), selected = 0, total = 0
        for path in paths {
            try check(text(path.id, 1, geometryMode == "layer_context" ? 24 : 32) && identifiers.insert(path.id).inserted)
            try check(["selected", "branch"].contains(path.role) || (context && path.role == "context"))
            if path.role == "selected" { selected += 1 }
            try check(geometryMode != "route_only" || path.role == "selected")
            try check((2...(context ? 48 : 24)).contains(path.points.count) && path.points.allSatisfy(point))
            total += path.points.count
            try check(total <= (context ? 512 : 96))
            if geometryMode == "layer_context" {
                try check(path.layer.map { (-10...10).contains($0) } == true)
                if path.role == "selected" {
                    try check(path.segmentLayers?.count == path.points.count - 1 && path.segmentLayers?.allSatisfy { (-10...10).contains($0) } == true)
                } else { try check(path.segmentLayers == nil) }
            } else { try check(path.layer == nil && path.segmentLayers == nil) }
            try check(path.anchorRefs.count <= 4 && (path.role == "context" ? path.anchorRefs.isEmpty : !path.anchorRefs.isEmpty))
            var linked = Set<String>()
            for reference in path.anchorRefs {
                try check(reference.count == 2)
                guard case .text(let id) = reference[0], case .index(let index) = reference[1] else { throw Invalid.snapshot }
                try check(path.points.indices.contains(index) && byID[id] != nil && linked.insert(id).inserted)
                try check(path.points[index] == byID[id])
            }
            if path.role == "selected" { try check(linked == Set(byID.keys)) }
        }
        if state == "active" && geometryMode != "unavailable" { try check(selected == 1 && !anchors.isEmpty) }
        else { try check(paths.isEmpty && anchors.isEmpty) }
        if state == "arrived" { try check(geometryMode == "unavailable" && distanceM == 0) }
        if let destination {
            try check(state == "active" && geometryMode != "unavailable" && point(destination))
            try check(paths.first { $0.role == "selected" }?.points.last == destination)
        }
    }

    mutating func addTransportAge(_ age: Int) {
        sourceAgeMs = min(60_000, sourceAgeMs + age)
        fixAgeMs = min(60_000, fixAgeMs + age)
        if let progressAgeMs { self.progressAgeMs = min(60_000, progressAgeMs + age) }
    }
    func dictionary() throws -> [String: Any] {
        try JSONSerialization.jsonObject(with: JSONEncoder().encode(self)) as? [String: Any] ?? [:]
    }
}

struct SourceSnapshot: Decodable {
    let version: Int
    let capturedUptimeMs: Int64
    var scene: JunctionScene

    static func decode(_ data: Data, nowMs: Int64) throws -> JunctionScene {
        guard data.count <= 65_536 else { throw JunctionScene.Invalid.snapshot }
        var wrapper = try JSONDecoder().decode(Self.self, from: data)
        guard wrapper.version == 1, wrapper.capturedUptimeMs >= 0, nowMs >= wrapper.capturedUptimeMs,
              nowMs - wrapper.capturedUptimeMs <= 2000 else { throw JunctionScene.Invalid.snapshot }
        try wrapper.scene.validate()
        wrapper.scene.addTransportAge(Int(nowMs - wrapper.capturedUptimeMs))
        return wrapper.scene
    }
}
