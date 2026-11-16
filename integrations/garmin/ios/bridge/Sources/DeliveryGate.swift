import Foundation

/** At most one request; callbacks from old connections cannot clear a newer request. */
final class DeliveryGate {
    final class Ticket {
        let epoch: String
        let id: Int
        let startedAt: TimeInterval
        let connection: Int
        init(epoch: String, id: Int, now: TimeInterval, connection: Int) {
            self.epoch = epoch; self.id = id; self.startedAt = now; self.connection = connection
        }
    }
    private var connection = 0
    private var slot: Ticket?
    private var lastEpoch = ""
    private var lastID = 0
    private var retired: [String] = []
    struct Request: Decodable {
        let kind: String; let version: Int; let epoch: String; let requestId: Int
        let displayedSession: String?; let displayedGeneration: Int?; let displayedSeq: Int?; let displayedState: String?
    }
    func connectionChanged() {
        connection += 1; slot = nil; lastEpoch = ""; lastID = 0; retired.removeAll()
    }
    func begin(_ dictionary: [AnyHashable: Any], now: TimeInterval) -> Ticket? {
        guard slot == nil, now.isFinite, now >= 0,
              let data = try? JSONSerialization.data(withJSONObject: dictionary), data.count <= 4096,
              let request = try? JSONDecoder().decode(Request.self, from: data),
              request.kind == "junction_request", request.version == 1,
              (1...64).contains(request.epoch.utf16.count), (1...1_000_000).contains(request.requestId),
              !retired.contains(request.epoch) else { return nil }
        let acknowledgement = [request.displayedSession != nil, request.displayedGeneration != nil,
            request.displayedSeq != nil, request.displayedState != nil]
        if acknowledgement.contains(true) || ["displayedSession", "displayedGeneration", "displayedSeq", "displayedState"].contains(where: { dictionary[$0] != nil }) {
            guard acknowledgement.allSatisfy({ $0 }),
                  (1...64).contains(request.displayedSession!.utf16.count),
                  (0...1_000_000).contains(request.displayedGeneration!), (0...1_000_000).contains(request.displayedSeq!),
                  ["active", "idle", "recalculating", "unavailable", "arrived", "stale_source", "stale_transport"].contains(request.displayedState!) else { return nil }
        }
        if request.epoch == lastEpoch && request.requestId <= lastID { return nil }
        if request.epoch != lastEpoch {
            if !lastEpoch.isEmpty { retired.append(lastEpoch); if retired.count > 4 { retired.removeFirst() } }
            lastEpoch = request.epoch; lastID = 0
        }
        lastID = request.requestId
        let ticket = Ticket(epoch: request.epoch, id: request.requestId, now: now, connection: connection)
        slot = ticket
        return ticket
    }
    func current(_ ticket: Ticket, now: TimeInterval) -> Bool {
        slot === ticket && ticket.connection == connection && now >= ticket.startedAt && now - ticket.startedAt < 3
    }
    func response(_ ticket: Ticket, scene: [String: Any]?, now: TimeInterval) -> [String: Any]? {
        guard current(ticket, now: now) else { return nil }
        var response: [String: Any] = ["version": 1, "epoch": ticket.epoch, "requestId": ticket.id]
        if let scene { response["kind"] = "junction_snapshot"; response["scene"] = scene }
        else { response["kind"] = "junction_unavailable"; response["reason"] = "source_unavailable" }
        return response
    }
    func finish(_ ticket: Ticket) { if slot === ticket { slot = nil } }
}
