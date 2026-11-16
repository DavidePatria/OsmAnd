import Foundation

@main
struct ProtocolTests {
    static func main() throws {
        var assertions = 0
        func check(_ value: @autoclosure () -> Bool) {
            precondition(value(), "Protocol regression assertion failed")
            assertions += 1
        }
        func rejects(_ action: () throws -> Void) {
            do { try action(); preconditionFailure("Invalid protocol input was accepted") }
            catch { assertions += 1 }
        }
        let idle: [String: Any] = ["version": 1, "session": "native-session", "generation": 1, "seq": 2,
            "state": "idle", "geometryMode": "unavailable", "reason": "idle", "roadName": "", "maneuver": "",
            "radiusDm": 800, "distanceM": 0, "sourceAgeMs": 10, "fixAgeMs": 20,
            "progressAgeMs": 30, "speedDmps": 100, "anchors": [], "paths": []]
        func wrapper(_ scene: [String: Any]? = nil, captured: Int64 = 1000) throws -> Data {
            try JSONSerialization.data(withJSONObject: ["version": 1, "capturedUptimeMs": captured, "scene": scene ?? idle])
        }
        let aged = try SourceSnapshot.decode(wrapper(), nowMs: 1500)
        check(aged.sourceAgeMs == 510)
        check(aged.fixAgeMs == 520)
        check(aged.progressAgeMs == 530)
        check(aged.speedDmps == 100 && aged.distanceM == 0)
        rejects { _ = try SourceSnapshot.decode(wrapper(captured: 1501), nowMs: 1500) }
        rejects { _ = try SourceSnapshot.decode(wrapper(), nowMs: 3001) }
        for (key, value) in [("distanceM", -1 as Any), ("seq", true as Any), ("generation", 1.5 as Any)] {
            var invalid = idle; invalid[key] = value
            rejects { _ = try SourceSnapshot.decode(wrapper(invalid), nowMs: 1500) }
        }
        var invalidArrival = idle; invalidArrival["state"] = "arrived"; invalidArrival["distanceM"] = 1
        rejects { _ = try SourceSnapshot.decode(wrapper(invalidArrival), nowMs: 1500) }
        let gate = DeliveryGate()
        func request(_ epoch: String, _ id: Int) -> [AnyHashable: Any] {
            ["kind": "junction_request", "version": 1, "epoch": epoch, "requestId": id]
        }
        let first = gate.begin(request("a", 1), now: 1)!
        check(gate.begin(request("a", 2), now: 1.1) == nil)
        check(gate.response(first, scene: idle, now: 3.999) != nil)
        check(gate.response(first, scene: idle, now: 4) == nil)
        gate.finish(first)
        check(gate.begin(request("a", 1), now: 5) == nil)
        let second = gate.begin(request("b", 1), now: 5)!
        gate.finish(first)
        check(gate.current(second, now: 5.1))
        gate.finish(second)
        check(gate.begin(request("a", 2), now: 6) == nil)
        var malformed = request("c", 1); malformed["displayedSeq"] = 3
        check(gate.begin(malformed, now: 6) == nil)
        malformed = request("c", 1); malformed["displayedSeq"] = NSNull()
        check(gate.begin(malformed, now: 6) == nil)
        let pending = gate.begin(request("c", 1), now: 6)!
        gate.connectionChanged()
        check(!gate.current(pending, now: 6.1))
        let vectors = try JSONSerialization.jsonObject(with: Data(contentsOf: URL(fileURLWithPath: "integrations/garmin/fixtures/wire/compact.json"))) as! [[String: Any]]
        for vector in vectors {
            let packet = try CompactWire.encode(vector["reply"] as! [String: Any])
            check(packet.hasPrefix("JC2:") && packet.utf8.count <= 10928)
            let bytes = Data(base64Encoded: String(packet.dropFirst(4)))!
            check(bytes.map { String(format: "%02x", $0) }.joined() == vector["hex"] as! String)
        }
        print("Junction iOS protocol assertions passed: \(assertions)")
    }
}
