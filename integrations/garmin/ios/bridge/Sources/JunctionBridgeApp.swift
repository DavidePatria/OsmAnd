import SwiftUI

struct WatchChoice: Identifiable {
    let id: String
    let name: String
}

final class BridgeModel: ObservableObject {
    @Published var devices: [WatchChoice] = []
    @Published var selectedDeviceID = UserDefaults.standard.string(forKey: "selectedDeviceID") ?? ""
    @Published var dataField = UserDefaults.standard.bool(forKey: "dataField")
    @Published var resumeAtLaunch = UserDefaults.standard.bool(forKey: "resumeAtLaunch")
    @Published var status = "bridge_stopped"
    @Published var running = false
    @Published var ready = false
    @Published var pendingToken: String?
    @Published var acknowledgement = ""
    private let link = GarminLink()
    private let source = SourceConnection()
    private let gate = DeliveryGate()

    init() {
        link.onDevices = { [weak self] raw in
            guard let self else { return }
            self.devices = raw.compactMap { item in
                guard let id = item["id"] as? String, let name = item["name"] as? String else { return nil }
                return WatchChoice(id: id, name: name)
            }
            if self.devices.count == 1 && self.selectedDeviceID.isEmpty { self.selectedDeviceID = self.devices[0].id }
        }
        link.onState = { [weak self] state, ready in
            guard let self else { return }
            self.ready = ready && self.running
            if self.running || state == "garmin_install" { self.status = state }
            if !ready { self.gate.connectionChanged(); self.source.cancel() }
        }
        link.onMessage = { [weak self] message in self?.receive(message) }
        link.initializeSDK()
        if resumeAtLaunch { start() }
    }

    func chooseWatch() { link.chooseDevices() }
    func openWatch() { link.openWatchApp() }
    func configurationChanged() {
        if running { stop() }
        UserDefaults.standard.set(selectedDeviceID, forKey: "selectedDeviceID")
        UserDefaults.standard.set(dataField, forKey: "dataField")
    }
    func saveStartupChoice() { UserDefaults.standard.set(resumeAtLaunch, forKey: "resumeAtLaunch") }

    func handle(_ url: URL) {
        guard url.scheme?.lowercased() == "junctionbridge" else { return }
        if url.host == "source" {
            guard let components = URLComponents(url: url, resolvingAgainstBaseURL: false),
                  components.queryItems?.count == 1,
                  let token = components.queryItems?.first(where: { $0.name == "token" })?.value,
                  token.count == 64, token.allSatisfy({ "0123456789abcdef".contains($0) }) else { return }
            // A URL alone never enables sharing or replaces the stored credential.
            pendingToken = token
        } else if link.handle(url: url) {
            running = false; ready = false; gate.connectionChanged(); source.cancel()
            status = "watch_selected"
        }
    }

    func acceptSource() {
        guard let token = pendingToken else { return }
        stop()
        status = SourceCredential.save(token) ? "source_configured" : "source_setup_required"
        pendingToken = nil
    }

    func start() {
        guard SourceCredential.read() != nil else { status = "source_setup_required"; return }
        guard devices.contains(where: { $0.id == selectedDeviceID }) else { status = "choose_watch"; return }
        gate.connectionChanged()
        running = true; ready = false; acknowledgement = ""
        link.start(deviceID: selectedDeviceID, dataField: dataField)
    }
    func stop() {
        running = false; ready = false
        gate.connectionChanged(); source.cancel(); link.stop()
        status = "bridge_stopped"
    }

    private func receive(_ request: [AnyHashable: Any]) {
        guard running && ready, let token = SourceCredential.read(),
              let ticket = gate.begin(request, now: ProcessInfo.processInfo.systemUptime) else { return }
        acknowledgement = request["displayedState"] as? String ?? ""
        source.read(token: token) { [weak self] result in
            guard let self, self.gate.current(ticket, now: ProcessInfo.processInfo.systemUptime) else { return }
            var scene: [String: Any]?
            if case .success(let data) = result,
               let snapshot = try? SourceSnapshot.decode(data, nowMs: Int64(ProcessInfo.processInfo.systemUptime * 1000)),
               let normalized = try? snapshot.dictionary() { scene = normalized }
            guard let response = self.gate.response(ticket, scene: scene, now: ProcessInfo.processInfo.systemUptime),
                  let packet = try? CompactWire.encode(response) else { self.gate.finish(ticket); return }
            self.link.send(packet) { [weak self] success in
                guard let self else { return }
                if self.gate.current(ticket, now: ProcessInfo.processInfo.systemUptime) {
                    self.status = success ? (scene == nil ? "source_unavailable" : "sdk_send_complete") : "delivery_failed"
                }
                self.gate.finish(ticket)
            }
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 3) { [weak self] in
            guard let self else { return }
            // Releasing an expired slot does not accept a late response or advance navigation.
            self.gate.finish(ticket)
        }
    }
}

@main
struct JunctionBridgeApp: App {
    @StateObject private var model = BridgeModel()
    var body: some Scene {
        WindowGroup {
            NavigationView {
                Form {
                    Section(header: Text("setup_heading")) {
                        Text("source_setup_help")
                        Button("choose_garmin", action: model.chooseWatch)
                        Picker("watch_label", selection: $model.selectedDeviceID) {
                            Text("choose_watch").tag("")
                            ForEach(model.devices) { Text($0.name).tag($0.id) }
                        }
                        Toggle("data_field_label", isOn: $model.dataField)
                    }
                    Section(header: Text("connection_heading")) {
                        Text(LocalizedStringKey(model.status))
                        Button(LocalizedStringKey(model.running ? "stop_bridge" : "start_bridge")) { model.running ? model.stop() : model.start() }
                        Button("open_watch_app", action: model.openWatch).disabled(!model.ready || model.dataField)
                        Toggle("resume_at_launch", isOn: $model.resumeAtLaunch)
                        Text("startup_help").font(.footnote)
                    }
                    Section(header: Text("watch_ack_heading")) {
                        Text(LocalizedStringKey(model.acknowledgement.isEmpty ? "no_watch_ack" : model.acknowledgement))
                        Text("verification_help").font(.footnote)
                    }
                }
                .navigationTitle("bridge_title")
            }
            .navigationViewStyle(.stack)
            .onOpenURL(perform: model.handle)
            .onChange(of: model.selectedDeviceID) { _ in model.configurationChanged() }
            .onChange(of: model.dataField) { _ in model.configurationChanged() }
            .onChange(of: model.resumeAtLaunch) { _ in model.saveStartupChoice() }
            .alert("confirm_source", isPresented: Binding(get: { model.pendingToken != nil }, set: { if !$0 { model.pendingToken = nil } })) {
                Button("connect_source", action: model.acceptSource)
                Button("cancel", role: .cancel) { model.pendingToken = nil }
            } message: { Text("confirm_source_help") }
        }
    }
}
