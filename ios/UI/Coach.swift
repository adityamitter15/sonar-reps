// Coach.swift
// One line of advice after a set, worked out from what the rep judge said
// about each movement and how deep it read. It appears on the result screen
// only: nothing is said during a set, and nothing is asked of the user.
// The verdicts come from the trained model; this line is plain rules on top.

import Foundation

enum Coach {
    static func note(reps: [RepEvent], duration: TimeInterval) -> String? {
        guard !reps.isEmpty else { return nil }
        let counted = reps.filter(\.valid)
        let refused = reps.count - counted.count
        let depths = counted.map(\.depthCm)

        if counted.isEmpty {
            let deepest = reps.map(\.depthCm).max() ?? 0
            return String(format: "Nothing counted. Your deepest was %.0f cm. Go lower, until your chest is close to the phone.", deepest)
        }

        // Refused movements bunched at the end point to tiredness, not technique.
        if refused >= 2 {
            let tail = reps.suffix(max(2, reps.count / 3))
            let late = tail.filter { !$0.valid }.count
            if late * 2 > refused {
                return "\(refused) movements did not go deep enough, most of them at the end. Stop a rep or two earlier and keep every one full."
            }
            return "\(refused) of \(reps.count) movements did not go deep enough. Go lower on every rep before adding more."
        }

        if depths.count >= 6 {
            let first = depths.prefix(3).reduce(0, +) / 3
            let last = depths.suffix(3).reduce(0, +) / 3
            if last < first * 0.8 {
                return String(format: "Your depth faded from %.0f cm to %.0f cm over the set. Slow down, or stop one rep earlier.", first, last)
            }
        }

        if reps.count >= 5, duration / Double(reps.count) < 1.3 {
            return String(format: "Quick set, about %.1f s a rep. Try the same number slower, two seconds on the way down.",
                          duration / Double(reps.count))
        }

        if refused == 1 {
            return "One movement did not go deep enough. The other \(counted.count) were full."
        }

        if depths.count >= 5, let deepest = depths.max(), let shallowest = depths.min(), deepest - shallowest <= 5 {
            return "Even depth on every rep. Add one or two next set."
        }
        return "\(counted.count) full \(counted.count == 1 ? "rep" : "reps"). Add one next set."
    }
}
