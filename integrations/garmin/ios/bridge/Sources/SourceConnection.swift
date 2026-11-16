import Foundation
import Network
import Security

enum SourceCredential {
    private static let service = "net.osmand.junction.bridge.source"
    static func read() -> String? {
        var item: CFTypeRef?
        let query: [String: Any] = [kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service, kSecAttrAccount as String: "osmand",
            kSecReturnData as String: true]
        guard SecItemCopyMatching(query as CFDictionary, &item) == errSecSuccess,
              let data = item as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }
    static func save(_ token: String) -> Bool {
        let query: [String: Any] = [kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service, kSecAttrAccount as String: "osmand"]
        let attributes: [String: Any] = [kSecValueData as String: Data(token.utf8),
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly]
        let status = SecItemUpdate(query as CFDictionary, attributes as CFDictionary)
        if status == errSecSuccess { return true }
        guard status == errSecItemNotFound else { return false }
        return SecItemAdd(query.merging(attributes) { _, new in new } as CFDictionary, nil) == errSecSuccess
    }
}

/** One bounded read from the authenticated source on this iPhone. */
final class SourceConnection {
    private let queue = DispatchQueue(label: "net.osmand.junction.source")
    private var connection: NWConnection?
    private var completion: ((Result<Data, Error>) -> Void)?
    private var buffer = Data()
    enum Failure: Error { case unavailable, timeout, oversized, malformed }

    func read(token: String, completion: @escaping (Result<Data, Error>) -> Void) {
        queue.async {
            guard self.connection == nil else {
                DispatchQueue.main.async { completion(.failure(Failure.unavailable)) }; return
            }
            self.completion = completion
            self.buffer.removeAll(keepingCapacity: true)
            let connection = NWConnection(host: "127.0.0.1", port: 38765, using: .tcp)
            self.connection = connection
            connection.stateUpdateHandler = { [weak self, weak connection] state in
                guard let self, let connection, self.connection === connection else { return }
                switch state {
                case .ready:
                    connection.send(content: Data("GET \(token)\n".utf8), completion: .contentProcessed { error in
                        guard self.connection === connection else { return }
                        if let error { self.finish(.failure(error)); return }
                        self.receive(connection)
                    })
                case .failed(let error): self.finish(.failure(error))
                case .cancelled: self.finish(.failure(Failure.unavailable))
                default: break
                }
            }
            connection.start(queue: self.queue)
            self.queue.asyncAfter(deadline: .now() + 1.5) { [weak self, weak connection] in
                guard let self, let connection, self.connection === connection else { return }
                self.finish(.failure(Failure.timeout))
            }
        }
    }

    func cancel() { queue.async { self.finish(.failure(Failure.unavailable)) } }

    private func receive(_ connection: NWConnection) {
        connection.receive(minimumIncompleteLength: 1, maximumLength: 8192) { [weak self] data, _, ended, error in
            guard let self, self.connection === connection else { return }
            if let data { self.buffer.append(data) }
            guard self.buffer.count <= 65537 else { self.finish(.failure(Failure.oversized)); return }
            if let newline = self.buffer.firstIndex(of: 10) {
                guard newline == self.buffer.count - 1 else { self.finish(.failure(Failure.malformed)); return }
                self.finish(.success(self.buffer.prefix(upTo: newline))); return
            }
            if let error { self.finish(.failure(error)) }
            else if ended { self.finish(.failure(Failure.malformed)) }
            else { self.receive(connection) }
        }
    }

    private func finish(_ result: Result<Data, Error>) {
        let completion = completion
        self.completion = nil
        let connection = connection
        self.connection = nil
        connection?.stateUpdateHandler = nil
        connection?.cancel()
        DispatchQueue.main.async { completion?(result) }
    }
}
