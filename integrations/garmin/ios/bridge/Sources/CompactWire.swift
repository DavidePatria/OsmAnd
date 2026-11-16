import Foundation

/** The iOS SDK supports NSString, but does not document NSData/ByteArray transport.
 * Wrap the existing lossless JC2 packet in Base64 rather than expand nested arrays.
 */
enum CompactWire {
    static let words = ["active", "idle", "recalculating", "unavailable", "map_context", "layer_context",
        "routing_branches", "route_only", "selected", "branch", "context",
        "motorcycle road context; intersections do not imply connectivity", "motorcycle road context with level ordering"] +
        (0...3).map { "j\($0)" } + (1...40).map { "c\($0)" } + ["arrived"]
    enum Invalid: Error { case packet }
    private struct Writer {
        var data = Data()
        mutating func u(_ input: Int) throws {
            guard (0...2_000_000).contains(input) else { throw Invalid.packet }
            var n = input
            while n >= 128 { data.append(UInt8((n & 127) | 128)); n >>= 7 }
            data.append(UInt8(n))
        }
        mutating func s(_ input: Int) throws { try u(input < 0 ? -2 * input - 1 : 2 * input) }
        mutating func text(_ value: String) throws {
            if let token = CompactWire.words.firstIndex(of: value) { try u(token + 1) }
            else {
                let bytes = Data(value.utf8)
                guard bytes.count <= 320 else { throw Invalid.packet }
                try u(0); try u(bytes.count); data.append(bytes)
            }
        }
        mutating func point(_ value: [Int]) throws {
            guard value.count == 2 else { throw Invalid.packet }
            try s(value[0]); try s(value[1])
        }
    }
    static func encode(_ reply: [String: Any]) throws -> String {
        guard reply["version"] as? Int == 1, let epoch = reply["epoch"] as? String,
              let id = reply["requestId"] as? Int, (1...1_000_000).contains(id),
              (1...64).contains(epoch.utf16.count), let kind = reply["kind"] as? String,
              ["junction_snapshot", "junction_unavailable"].contains(kind) else { throw Invalid.packet }
        let unavailable = kind == "junction_unavailable"
        var w = Writer()
        try w.u(74); try w.u(67); try w.u(2); try w.u(unavailable ? 1 : 0)
        try w.text(epoch); try w.u(id)
        if unavailable {
            guard let reason = reply["reason"] as? String, reason.utf16.count <= 80 else { throw Invalid.packet }
            try w.text(reason)
        } else {
            guard let raw = reply["scene"] as? [String: Any] else { throw Invalid.packet }
            let scene = try JSONDecoder().decode(JunctionScene.self, from: JSONSerialization.data(withJSONObject: raw))
            try scene.validate()
            try w.text(scene.session); try w.u(scene.generation); try w.u(scene.seq)
            for value in [scene.state, scene.geometryMode, scene.reason, scene.roadName, scene.maneuver] { try w.text(value) }
            for value in [scene.distanceM, scene.sourceAgeMs, scene.fixAgeMs, scene.radiusDm] { try w.u(value) }
            try w.u(scene.progressAgeMs == nil ? 0 : 1)
            if let age = scene.progressAgeMs, let speed = scene.speedDmps { try w.u(age); try w.u(speed) }
            try w.u(scene.anchors.count)
            for anchor in scene.anchors { try w.text(anchor.id); try w.u(anchor.routeIndex); try w.point(anchor.point) }
            try w.u(scene.paths.count)
            for path in scene.paths {
                try w.text(path.id); try w.text(path.role); try w.u(path.points.count)
                var x = 0, y = 0
                for point in path.points { try w.s(point[0] - x); try w.s(point[1] - y); x = point[0]; y = point[1] }
                try w.u(path.anchorRefs.count)
                for reference in path.anchorRefs {
                    guard case .text(let name) = reference[0], case .index(let index) = reference[1],
                          let anchor = scene.anchors.firstIndex(where: { $0.id == name }) else { throw Invalid.packet }
                    try w.u(anchor); try w.u(index)
                }
                if scene.geometryMode == "layer_context" {
                    guard let layer = path.layer else { throw Invalid.packet }
                    try w.s(layer)
                    if path.role == "selected" { for layer in path.segmentLayers ?? [] { try w.s(layer) } }
                }
            }
            try w.u(scene.destination == nil ? 0 : 1)
            if let destination = scene.destination { try w.point(destination) }
        }
        guard w.data.count <= 8192 else { throw Invalid.packet }
        return "JC2:" + w.data.base64EncodedString()
    }
}
