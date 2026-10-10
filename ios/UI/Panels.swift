// Panels.swift
// The two screens around a set. Home: the personal best and recent sets.
// Result: what the set just was, in cards, with a badge for a new best.
// Plus the cards and buttons both use.

import SwiftUI

// MARK: Home

struct HomePanel: View {
    let best: SetRecord?
    let recent: [SetRecord]

    var body: some View {
        VStack(spacing: 12) {
            Card {
                HStack {
                    Caption("Personal best", size: 13)
                    Spacer()
                    if let best { Caption(best.date.setStamp, size: 13) }
                }
                if let best {
                    BigCount(reps: best.reps)
                    HStack(spacing: 0) {
                        MiniStat(label: "Deepest", value: depthText(best.deepest), unit: "cm")
                        MiniStat(label: "Average", value: depthText(best.average), unit: "cm")
                        MiniStat(label: "Time", value: clockText(best.duration))
                    }
                } else {
                    Text("No sets yet")
                        .font(.title2.bold())
                        .foregroundStyle(Theme.text)
                        .padding(.top, 4)
                    Text("Your best set will show here, with when you did it and how deep you went.")
                        .font(.subheadline)
                        .foregroundStyle(Theme.muted)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }

            Card {
                Caption("Recent sets", size: 13)
                if recent.isEmpty {
                    Text("Finished sets are listed here.")
                        .font(.subheadline)
                        .foregroundStyle(Theme.muted)
                } else {
                    VStack(spacing: 0) {
                        ForEach(Array(recent.prefix(4).enumerated()), id: \.element.id) { i, r in
                            if i > 0 { Rectangle().fill(Theme.hairline).frame(height: 1) }
                            RecentRow(record: r)
                        }
                    }
                }
            }

            Spacer(minLength: 0)
        }
    }
}

private struct RecentRow: View {
    let record: SetRecord

    var body: some View {
        HStack(alignment: .center) {
            VStack(alignment: .leading, spacing: 2) {
                Text(record.date.setStamp)
                    .font(.body)
                    .foregroundStyle(Theme.text)
                Text(detail)
                    .font(.footnote)
                    .foregroundStyle(Theme.muted)
            }
            Spacer()
            HStack(alignment: .firstTextBaseline, spacing: 4) {
                Text("\(record.reps)")
                    .font(Theme.display(30))
                    .monospacedDigit()
                    .foregroundStyle(Theme.text)
                Caption("reps", size: 13)
            }
        }
        .padding(.vertical, 10)
        .accessibilityElement(children: .combine)
    }

    private var detail: String {
        var parts: [String] = []
        if let avg = record.average { parts.append(String(format: "Average %.1f cm", avg)) }
        parts.append(clockText(record.duration))
        if record.noReps > 0 { parts.append("\(record.noReps) no rep\(record.noReps == 1 ? "" : "s")") }
        return parts.joined(separator: ", ")
    }
}

// MARK: Result

struct ResultPanel: View {
    let record: SetRecord
    let isNewBest: Bool
    let best: SetRecord?
    let reps: [RepEvent]
    let repLineCm: Double

    var body: some View {
        VStack(spacing: 12) {
            Card {
                HStack {
                    Caption("Set complete", size: 13)
                    Spacer()
                    Caption(record.date.setStamp, size: 13)
                }
                HStack(alignment: .bottom) {
                    BigCount(reps: record.reps)
                    Spacer()
                    if isNewBest {
                        Label("New personal best", systemImage: "trophy.fill")
                            .font(.footnote.bold())
                            .foregroundStyle(Theme.onAccent)
                            .padding(.horizontal, 12)
                            .frame(height: 30)
                            .background(Capsule().fill(Theme.accent))
                            .padding(.bottom, 14)
                    }
                }
                if !isNewBest, let best {
                    Text("Personal best: \(best.reps) reps on \(best.date.setStamp)")
                        .font(.system(size: 14))
                        .foregroundStyle(Theme.muted)
                }
            }

            if let note = Coach.note(reps: reps, duration: record.duration) {
                Card {
                    Caption("Coach note", size: 13)
                    Text(note)
                        .font(.system(size: 16, weight: .medium))
                        .foregroundStyle(Theme.text)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }

            HStack(spacing: 12) {
                Tile(label: "No reps", value: "\(record.noReps)",
                     color: record.noReps > 0 ? Theme.noRep : Theme.text)
                Tile(label: "Time", value: clockText(record.duration))
            }
            HStack(spacing: 12) {
                Tile(label: "Deepest", value: depthText(record.deepest), unit: "cm")
                Tile(label: "Average", value: depthText(record.average), unit: "cm")
            }

            Card {
                Caption("Depth per movement", size: 13)
                RepHistory(reps: reps, repLineCm: repLineCm)
                    .frame(maxHeight: .infinity)
                    .frame(minHeight: 70)
            }
        }
    }
}

// MARK: Pieces

/// A rounded panel with a hairline border, the one container on these screens.
struct Card<Content: View>: View {
    @ViewBuilder let content: () -> Content

    var body: some View {
        VStack(alignment: .leading, spacing: 10, content: content)
            .padding(16)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(RoundedRectangle(cornerRadius: 18).fill(Theme.surface))
            .overlay(RoundedRectangle(cornerRadius: 18).strokeBorder(Theme.hairline, lineWidth: 1))
    }
}

private struct BigCount: View {
    let reps: Int
    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: 8) {
            Text("\(reps)")
                .font(Theme.display(84))
                .monospacedDigit()
                .foregroundStyle(Theme.text)
            Caption(reps == 1 ? "rep" : "reps", size: 18)
        }
    }
}

private struct MiniStat: View {
    let label: String
    let value: String
    var unit: String = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Caption(label, size: 12)
            HStack(alignment: .firstTextBaseline, spacing: 3) {
                Text(value)
                    .font(Theme.display(26))
                    .monospacedDigit()
                    .foregroundStyle(Theme.text)
                if !unit.isEmpty { Caption(unit, size: 12) }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

private struct Tile: View {
    let label: String
    let value: String
    var unit: String = ""
    var color: Color = Theme.text

    var body: some View {
        Card {
            Caption(label, size: 13)
            HStack(alignment: .firstTextBaseline, spacing: 4) {
                Text(value)
                    .font(Theme.display(40))
                    .monospacedDigit()
                    .foregroundStyle(color)
                if !unit.isEmpty { Caption(unit, size: 13) }
            }
        }
    }
}

/// Full-width filled button: Start set, Stop.
struct PrimaryButton: View {
    let title: String
    var systemImage: String?
    var fill: Color = Theme.accent
    var ink: Color = Theme.onAccent
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 8) {
                if let systemImage { Image(systemName: systemImage) }
                Text(title)
            }
            .font(.system(size: 18, weight: .semibold))
            .foregroundStyle(ink)
            .frame(maxWidth: .infinity)
            .frame(height: 60)
            .background(RoundedRectangle(cornerRadius: 16).fill(fill))
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
    }
}

/// Outlined button on the card colour: Reset, Done.
struct SecondaryButton: View {
    let title: String
    var systemImage: String?
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            SecondaryLabel(title: title, systemImage: systemImage)
        }
        .buttonStyle(.plain)
    }
}

struct SecondaryLabel: View {
    let title: String
    var systemImage: String?

    var body: some View {
        HStack(spacing: 8) {
            if let systemImage { Image(systemName: systemImage) }
            Text(title)
        }
        .font(.system(size: 17, weight: .semibold))
        .foregroundStyle(Theme.text)
        .frame(maxWidth: .infinity)
        .frame(height: 60)
        .background(RoundedRectangle(cornerRadius: 16).fill(Theme.surface))
        .overlay(RoundedRectangle(cornerRadius: 16).strokeBorder(Theme.hairline, lineWidth: 1))
        .contentShape(Rectangle())
    }
}
