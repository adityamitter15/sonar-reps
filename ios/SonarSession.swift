// SonarSession.swift
//
// The one object the screens talk to. It hides where the numbers come from,
// so the UI is the same whether a set is scripted or real.
//
//   .demo  plays a scripted set and touches no audio and no network. It runs
//          in the simulator and in SwiftUI previews. Use it to build the UI.
//   .live  starts the sonar (SonarEngine), streams the microphone to the Mac,
//          and shows the verdict the Mac sends back about 30 times a second
//          (see phone_receiver.py for the message).
//
// Usage from a view:
//
//   @StateObject private var session = SonarSession()   // demo in the simulator, live on a phone
//   ...
//   Text("\(session.count)")
//   .onChange(of: session.reps.count) { if session.reps.last?.valid == false { flashNoRep() } }
//   Button("Start") { session.start(macHost: "172.20.10.11") }
//
// Everything below "Read these" is published on the main thread.

import Foundation

/// One finished movement: a counted rep or a NO REP.
struct RepEvent: Identifiable, Equatable {
    let id: Int  // 1, 2, 3 in the order they finished, counted or not
    let valid: Bool  // true: counted. false: NO REP
    let depthCm: Double  // how far down the chest went
    let reason: String  // "" for a counted rep, otherwise why not, for example "too shallow"
}

final class SonarSession: ObservableObject {
    enum Source { case demo, live }
    let source: Source

    // Read these.
    @Published private(set) var running = false  // Start was pressed and Stop was not
    @Published private(set) var live = false  // numbers arrived within the last 1.5 s
    @Published private(set) var depthCm = 0.0  // how far down the chest is right now, 0 at the top
    @Published private(set) var count = 0  // counted reps this set
    @Published private(set) var noReps = 0  // movements refused this set
    @Published private(set) var phoneMoving = false  // the phone itself is moving, so nothing counts
    @Published private(set) var toneTooQuiet = false  // the tones reach the microphone too weakly to count: volume up
    @Published private(set) var repLineCm = 15.0  // depth a movement must reach to count
    @Published private(set) var lostPackets = 0
    @Published private(set) var reps: [RepEvent] = []  // every finished movement this set, oldest first
    @Published private(set) var status = "Idle"
    @Published private(set) var lastFileURL: URL?  // the saved take, for a share button
    @Published var error: String?

    private let engine = SonarEngine()
    private var setNumber = -1
    private var leavingSet: Int?  // the Mac's set we asked it to drop with reset(), until it has
    private var resetAsked = Date.distantPast
    private var lastMessage = Date.distantPast
    private var ticker: Timer?
    private var demoStart = Date()
    private var demoDone = Set<Int>()

    /// With no argument: demo in the simulator, live on a real phone.
    init(source: Source? = nil) {
        #if targetEnvironment(simulator)
        self.source = source ?? .demo
        #else
        self.source = source ?? .live
        #endif
    }

    /// Start a set. `macHost` is the Mac's address, ignored in demo.
    func start(macHost: String) {
        guard !running else { return }
        error = nil
        clear()
        leavingSet = nil
        switch source {
        case .demo:
            demoStart = Date()
            demoDone = []
            status = "Demo set"
        case .live:
            engine.onReply = { [weak self] data in
                DispatchQueue.main.async { self?.take(data) }
            }
            do {
                try engine.start(macHost: macHost)
            } catch {
                self.error = error.localizedDescription
                return
            }
            status = engine.status
            lastFileURL = engine.lastFileURL
        }
        running = true
        ticker = Timer.scheduledTimer(withTimeInterval: 1.0 / 30.0, repeats: true) { [weak self] _ in
            self?.tick()
        }
    }

    func stop() {
        guard running else { return }
        ticker?.invalidate()
        ticker = nil
        if source == .live {
            engine.stop()
            lastFileURL = engine.lastFileURL
        }
        running = false
        live = false
        depthCm = 0
        phoneMoving = false
        toneTooQuiet = false
        status = "Stopped"
    }

    /// Count from zero again without stopping the sonar.
    func reset() {
        clear()
        switch source {
        case .demo:
            demoStart = Date()
            demoDone = []
        case .live:
            // Until the Mac has started its new set, its messages still carry
            // the old count and last rep. take() ignores those.
            leavingSet = setNumber
            resetAsked = Date()
            engine.sendReset()
        }
    }

    private func clear() {
        depthCm = 0
        count = 0
        noReps = 0
        reps = []
    }

    private func tick() {
        switch source {
        case .demo: demoTick()
        case .live: live = Date().timeIntervalSince(lastMessage) < 1.5
        }
    }

    // MARK: Live: the verdict from the Mac

    private struct Message: Decodable {
        struct Rep: Decodable {
            let n: Int
            let valid: Bool
            let depth: Double
            let reason: String
        }
        let set: Int
        let depth: Double
        let count: Int
        let shallow: Int
        let moving: Bool
        let lost: Int
        let min_depth: Double
        let quiet: Bool?  // absent from older receivers
        let rep: Rep?
    }

    private func take(_ data: Data) {
        guard running, let m = try? JSONDecoder().decode(Message.self, from: data) else { return }
        lastMessage = Date()
        live = true
        if toneTooQuiet != (m.quiet ?? false) { toneTooQuiet = m.quiet ?? false }
        if let old = leavingSet {
            if m.set == old {
                // The reset has not reached the Mac yet. Ask again in case it was lost.
                if Date().timeIntervalSince(resetAsked) > 0.3 {
                    resetAsked = Date()
                    engine.sendReset()
                }
                phoneMoving = m.moving
                return
            }
            leavingSet = nil
        }
        if m.set != setNumber {
            // The Mac started a new set: forget the old reps.
            setNumber = m.set
            reps = []
        }
        depthCm = m.depth
        phoneMoving = m.moving
        if lostPackets != m.lost { lostPackets = m.lost }
        if repLineCm != m.min_depth { repLineCm = m.min_depth }
        if let r = m.rep, r.n > (reps.last?.id ?? 0) {
            reps.append(RepEvent(id: r.n, valid: r.valid, depthCm: r.depth, reason: r.reason))
        }
        if count != m.count { count = m.count }
        if noReps != m.shallow { noReps = m.shallow }
    }

    // MARK: Demo: the same scripted set as display.html?demo

    // (start second, depth in cm). The fourth is too shallow, and the phone
    // "moves" from 12 s to 14.2 s. The whole script repeats every 18 s.
    private static let script: [(start: Double, depth: Double)] =
        [(1, 26), (3.2, 24), (5.4, 27), (7.6, 9), (9.8, 25), (15, 23)]

    private func demoTick() {
        var t = Date().timeIntervalSince(demoStart)
        if t >= 18 {
            demoStart = Date()
            demoDone = []
            clear()
            t = 0
        }
        var depth = 0.0
        for (i, rep) in Self.script.enumerated() {
            if t >= rep.start && t < rep.start + 1.8 {
                depth = rep.depth * 0.5 * (1 - cos(2 * .pi * (t - rep.start) / 1.8))
            }
            if t >= rep.start + 1.5 && !demoDone.contains(i) {
                demoDone.insert(i)
                let valid = rep.depth >= repLineCm
                reps.append(RepEvent(id: reps.count + 1, valid: valid, depthCm: rep.depth,
                                     reason: valid ? "" : "too shallow"))
                if valid { count += 1 } else { noReps += 1 }
            }
        }
        phoneMoving = t > 12 && t < 14.2
        depthCm = phoneMoving ? 0 : depth
        live = true
    }
}
