// SonarView.swift
// Root screen, in three states. Home: personal best, recent sets, Start.
// During a set the phone lies
// under the chest and nothing needs a touch: the count, the depth column, the
// rep history and the trace all read from 30 to 60 cm away.
// After Stop: the result of the set, saved to the set log.
// No sound and no haptics anywhere: the speaker is the sonar, and a vibration
// would trip the motion check and block counting.

import SwiftUI

struct SonarView: View {
    @StateObject private var session = SonarSession()
    @StateObject private var history = MotionHistory()
    @StateObject private var log = SetLog()
    @AppStorage("sonarMacHost") private var macHost = "172.20.10.11"

    @State private var countScale: CGFloat = 1
    @State private var hit = false
    @State private var noRepDetail: String?
    @State private var noRepToken = 0
    @AppStorage("sonarSeenIntro") private var seenIntro = false
    @AppStorage("sonarDeveloperMode") private var developerMode = false
    @State private var showIntro = false
    @State private var showSettings = false
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var setStart = Date()
    @State private var result: SetRecord?
    @State private var resultIsBest = false

    var body: some View {
        ZStack(alignment: .top) {
            Theme.bg.ignoresSafeArea()

            VStack(spacing: 16) {
                header
                if session.running {
                    VStack(spacing: 16) {
                        readout
                        section("This set") { RepHistory(reps: session.reps, repLineCm: session.repLineCm) }
                            .frame(height: 78)
                        section("Your movement") { TraceView(history: history, repLineCm: session.repLineCm) }
                            .frame(height: 104)
                            .accessibilityElement()
                            .accessibilityLabel("Movement trace")
                            .accessibilityValue(String(format: "%.0f centimetres down", max(0, session.depthCm)))
                    }
                    .grayscale(notCounting ? 1 : 0)
                    .opacity(notCounting ? 0.4 : 1)
                    .animation(.easeOut(duration: 0.18), value: notCounting)
                } else if let result {
                    ResultPanel(record: result, isNewBest: resultIsBest, best: log.best,
                                reps: session.reps, repLineCm: session.repLineCm)
                } else {
                    HomePanel(best: log.best, recent: log.records)
                }
                controls
            }
            .padding(.horizontal, 20)
            .padding(.top, 8)
            .padding(.bottom, 12)

            if session.phoneMoving {
                PhoneMovedBanner()
                    .padding(.top, 4)
                    .transition(reduceMotion ? .opacity : .move(edge: .top).combined(with: .opacity))
            } else if session.toneTooQuiet {
                PhoneMovedBanner(text: "Too quiet. Turn the volume up.")
                    .padding(.top, 4)
                    .transition(reduceMotion ? .opacity : .move(edge: .top).combined(with: .opacity))
            }

            if let detail = noRepDetail {
                NoRepOverlay(detail: detail)
                    .transition(.opacity)
            }
        }
        .animation(.easeOut(duration: 0.18), value: notCounting)
        .sonarAppearance()
        .onAppear {
            UIApplication.shared.isIdleTimerDisabled = true
            if !seenIntro { showIntro = true }
            #if targetEnvironment(simulator)
            // For screenshots: `simctl launch ... -autostart` begins the demo set with no tap.
            let args = ProcessInfo.processInfo.arguments
            if args.contains("-autostart") { startSet() }
            if args.contains("-autostop") { DispatchQueue.main.asyncAfter(deadline: .now() + 17.3) { stopSet() } }
            #endif
        }
        .sheet(isPresented: $showIntro, onDismiss: { seenIntro = true }) { HowItWorks() }
        .sheet(isPresented: $showSettings) {
            SettingsView(session: session, log: log) { showIntro = true }
        }
        .onChange(of: session.depthCm) { history.add(depth: session.depthCm) }
        .onChange(of: session.reps.count) { old, new in
            if new == 0 { history.clear() }
            guard new > old, let rep = session.reps.last else { return }
            history.mark(valid: rep.valid)
            if rep.valid { celebrate() } else { refuse(rep) }
        }
    }

    // MARK: Header

    private var header: some View {
        HStack(alignment: .center, spacing: 10) {
            LogoMark().frame(width: 26, height: 26)
                .accessibilityHidden(true)
            Text("SONAR REPS")
                .font(Theme.display(24))
                .tracking(3)
                .foregroundStyle(Theme.text)
            Spacer()
            if session.running {
                TimelineView(.periodic(from: setStart, by: 1)) { tl in
                    Text(clockText(tl.date.timeIntervalSince(setStart)))
                        .font(.system(size: 15, weight: .semibold).monospacedDigit())
                        .foregroundStyle(Theme.muted)
                }
                StatusPill(state: pillState)
            } else {
                HeaderIcon(symbol: "gearshape", label: "Settings") { showSettings = true }
            }
        }
        .frame(height: 36)
    }

    /// The phone is moving or its tones are too quiet: nothing counts, and the screen says why.
    private var notCounting: Bool { session.phoneMoving || session.toneTooQuiet }

    private var pillState: StatusPill.State {
        session.live ? .live : .waiting
    }

    // MARK: Count and depth

    private var readout: some View {
        GeometryReader { geo in
            let gaugeWidth = min(150, geo.size.width * 0.36)
            let countWidth = geo.size.width - gaugeWidth - 16
            HStack(alignment: .top, spacing: 16) {
                VStack(alignment: .leading, spacing: 0) {
                    Caption("Reps")
                    Spacer(minLength: 0)
                    Text("\(session.count)")
                        .font(Theme.display(min(countWidth * 1.45, geo.size.height * 0.72)))
                        .monospacedDigit()
                        .foregroundStyle(Theme.text)
                        .lineLimit(1)
                        .minimumScaleFactor(0.3)
                        .scaleEffect(countScale, anchor: .bottomLeading)
                        .accessibilityLabel("\(session.count) \(session.count == 1 ? "rep" : "reps")")
                    Spacer(minLength: 0)
                    HStack(alignment: .top, spacing: 22) {
                        Stat(label: "No reps", value: "\(session.noReps)",
                             color: session.noReps > 0 ? Theme.noRep : Theme.text)
                        Stat(label: "Last depth", value: lastDepth, unit: "cm")
                    }
                }
                .frame(width: countWidth, alignment: .leading)

                VStack(spacing: 8) {
                    HStack(alignment: .firstTextBaseline, spacing: 4) {
                        Text(String(format: "%.1f", max(0, session.depthCm)))
                            .font(Theme.display(28))
                            .monospacedDigit()
                            .foregroundStyle(Theme.text)
                        Caption("cm", size: 12)
                    }
                    DepthGauge(depthCm: session.depthCm, repLineCm: session.repLineCm,
                               peakCm: history.peakCm, live: session.running && session.live,
                               waiting: session.running && !session.live, hit: hit)
                }
                .frame(width: gaugeWidth)
            }
        }
    }

    private var lastDepth: String {
        guard let last = session.reps.last else { return "0.0" }
        return String(format: "%.1f", last.depthCm)
    }

    // MARK: Controls

    @ViewBuilder
    private var controls: some View {
        if session.running {
            VStack(spacing: 8) {
                if developerMode && session.lostPackets > 0 {
                    Caption("Lost \(session.lostPackets) packets", color: Theme.faint, size: 12)
                        .frame(maxWidth: .infinity, alignment: .trailing)
                }
                HStack(spacing: 12) {
                    PrimaryButton(title: "Stop", systemImage: "stop.fill",
                                  fill: Theme.text, ink: Theme.bg) { stopSet() }
                    SecondaryButton(title: "Restart", systemImage: "arrow.counterclockwise") {
                        session.reset()
                        setStart = Date()
                    }
                    .frame(width: 130)
                }
            }
        } else {
            VStack(spacing: 12) {
                PrimaryButton(title: result == nil ? "Start set" : "Start next set") { startSet() }
                if result != nil {
                    SecondaryButton(title: "Done") { withAnimation(.easeOut(duration: 0.2)) { result = nil } }
                } else if session.error != nil {
                    Label("Sonar couldn't start. Check that Sonar Reps can use the microphone in Settings.",
                          systemImage: "exclamationmark.circle")
                        .font(.subheadline)
                        .foregroundStyle(Theme.noRep)
                        .frame(maxWidth: .infinity, alignment: .leading)
                } else {
                    Text("Put the phone face-up under your chest, press Start, then hands off.")
                        .font(.subheadline)
                        .foregroundStyle(Theme.muted)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
        }
    }

    private func startSet() {
        history.clear()
        result = nil
        setStart = Date()
        session.start(macHost: macHost)
    }

    private func stopSet() {
        let duration = Date().timeIntervalSince(setStart)
        session.stop()
        guard !session.reps.isEmpty else { return }
        let counted = session.reps.filter(\.valid)
        let record = SetRecord(date: setStart, reps: counted.count, noReps: session.reps.count - counted.count,
                               duration: duration, depths: counted.map(\.depthCm))
        resultIsBest = log.add(record)
        result = record
    }

    // MARK: Verdicts

    private func celebrate() {
        var instant = Transaction()
        instant.disablesAnimations = true
        withTransaction(instant) {
            if !reduceMotion { countScale = 1.14 }
            hit = true
        }
        DispatchQueue.main.async {
            withAnimation(.spring(response: 0.45, dampingFraction: 0.55)) { countScale = 1 }
            withAnimation(.easeOut(duration: 0.5)) { hit = false }
        }
    }

    private func refuse(_ rep: RepEvent) {
        let reason = rep.reason.isEmpty ? "Not counted" : rep.reason.prefix(1).uppercased() + rep.reason.dropFirst()
        var detail = String(format: "%@. You reached %.0f cm", reason, rep.depthCm)
        detail += session.repLineCm > 0 ? String(format: " of %.0f cm.", session.repLineCm) : "."
        noRepToken += 1
        let token = noRepToken
        withAnimation(.easeOut(duration: 0.08)) { noRepDetail = detail }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.85) {
            guard token == noRepToken else { return }
            withAnimation(.easeIn(duration: 0.3)) { noRepDetail = nil }
        }
    }

    // MARK: Pieces

    private func section<Content: View>(_ title: String, @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Caption(title, size: 12)
            content()
        }
        .padding(.top, 12)
        .overlay(alignment: .top) { Rectangle().fill(Theme.hairline).frame(height: 1) }
    }
}

private struct Stat: View {
    let label: String
    let value: String
    var unit: String = ""
    var color: Color = Theme.text

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Caption(label, size: 12)
            HStack(alignment: .firstTextBaseline, spacing: 3) {
                Text(value)
                    .font(Theme.display(34))
                    .monospacedDigit()
                    .foregroundStyle(color)
                if !unit.isEmpty { Caption(unit, size: 12) }
            }
        }
    }
}

private struct HeaderIcon: View {
    let symbol: String
    let label: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Image(systemName: symbol)
                .font(.system(size: 16, weight: .regular))
                .foregroundStyle(Theme.muted)
                .frame(width: 44, height: 44)
                .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityLabel(label)
    }
}

struct StatusPill: View {
    enum State { case ready, demo, live, waiting }
    let state: State
    @SwiftUI.State private var blink = false

    var body: some View {
        HStack(spacing: 6) {
            Circle().fill(color).frame(width: 7, height: 7)
                .opacity(state == .live && blink ? 0.25 : 1)
            Caption(title, color: color, size: 12)
        }
        .padding(.horizontal, 10)
        .frame(height: 24)
        .overlay(Capsule().strokeBorder(color.opacity(0.5), lineWidth: 1))
        .onAppear {
            withAnimation(.easeInOut(duration: 0.55).repeatForever()) { blink = true }
        }
    }

    private var title: String {
        switch state {
        case .ready: return "Ready"
        case .demo: return "Demo"
        case .live: return "Listening"
        case .waiting: return "Connecting"
        }
    }

    private var color: Color {
        switch state {
        case .live: return Theme.accent
        case .waiting: return Theme.warn
        case .ready, .demo: return Theme.muted
        }
    }
}

#Preview {
    SonarView()
}
