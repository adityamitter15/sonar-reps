# Phone UI handover

For the Claude Code session building the iPhone screen. Read this whole file first. It replaces the numbered steps in `CLAUDE.md`, which are for Addy's Mac and are not your job.

## The job

Sonar Reps counts push-ups with sonar: the iPhone lies face-up on the floor, plays three tones near 19 kHz and tracks the echo off the chest. There is already a live demo screen for the laptop, `display.html`. **Build the same screen as a native SwiftUI screen for the iPhone**, same look, same behaviour, laid out for a phone in portrait.

Everything under the screen is done and is not yours to change: the sonar, the network link and the rep counting. You get one object, `SonarSession`, with the live numbers on it. In the simulator it plays a scripted set, so you need no iPhone, no Mac receiver and no sound to build and check the whole UI.

**Deadline, London time, Sat 10 Oct 2026:** a first working version back by 12:50, final by 13:15. Features freeze at 13:30. If time runs short, work in the priority order given under "What to build".

## See the target first

Open the web version in demo mode. It needs no server:

```sh
open "display.html?demo"
```

Watch one full 18 second loop: five counted reps, one NO REP, and the phone-moved warning. That is the look and the behaviour to match. Then read `display.html` itself (300 lines); every colour, size ratio and timing below comes from it.

## Files

| Path | Whose | Notes |
|---|---|---|
| `ios/UI/` | **Yours** | Every screen and view. Add as many files as you like; `xcodegen` picks them up. |
| `ios/UI/SonarView.swift` | **Yours, replace it** | A plain placeholder that uses every part of `SonarSession`. The root view must stay `struct SonarView: View` with no init arguments. |
| `ios/SonarSession.swift` | Ours, read only | The data contract. Read its header comment. |
| `ios/SonarEngine.swift`, `ios/SonarRepsApp.swift`, `ios/project.yml` | Ours, do not edit | Audio, network, app entry, build spec. |
| All Python, `display.html`, `takes/`, `README.md`, `RESULTS.md` | Ours, do not edit | `display.html` is your reference. |

Touch nothing outside `ios/UI/`. We are changing the other files at the same time, and this split is what lets your work drop in with no merge conflict. If the UI needs something `SonarSession` does not offer, do not work around it and do not edit it: say so in your hand-back note and use a constant for now.

## The data contract

```swift
@StateObject private var session = SonarSession()   // demo in the simulator, live on a phone
```

| Property | Type | Meaning | On the web page |
|---|---|---|---|
| `running` | `Bool` | Start was pressed and Stop was not | |
| `live` | `Bool` | Numbers arrived within the last 1.5 s | LIVE or WAITING pill |
| `depthCm` | `Double` | How far down the chest is now, 0 at the top. About 30 updates a second | the chest bar, `12.3 CM DOWN` |
| `count` | `Int` | Counted reps this set | the big number |
| `noReps` | `Int` | Movements refused this set | NO REPS |
| `phoneMoving` | `Bool` | The phone itself is moving, so nothing counts | the hazard banner |
| `repLineCm` | `Double` | Depth a movement must reach to count | the dashed amber line |
| `lostPackets` | `Int` | Network packets lost | LOST |
| `reps` | `[RepEvent]` | Every finished movement this set, oldest first. It grows by one when a movement finishes and empties on reset | chips, LAST DEPTH, the thump and the NO REP flash |
| `status` | `String` | One line of plain status text | |
| `lastFileURL` | `URL?` | The saved recording of the last set | |
| `error` | `String?` | Set when Start fails, for example no microphone permission | |

`RepEvent` has `id` (1, 2, 3 in order), `valid` (true: counted, false: NO REP), `depthCm` and `reason` (empty for a counted rep, otherwise why not).

Actions: `session.start(macHost:)`, `session.stop()`, `session.reset()` (count from zero without stopping).

React to a finished movement with `.onChange(of: session.reps.count)` and look at `session.reps.last`.

Three things will change under you later today, so build for them now:

- `reason` is "too shallow" today. A trained rep judge is coming and will send other reasons, such as "half rep" or "not a push-up". Show the text you are given; do not hard-code it.
- `repLineCm` is 15 in demo and 12 on the phone. Draw the line from the value. If it is 0, hide the line and its label.
- Full push-ups read anywhere from 9 to 25 cm at present. Keep the gauge scale at 0 to 40 cm as on the web page.

## Rules that come from the sonar

These are not style choices. Breaking them breaks the counting.

- **No sound.** The speaker is the sonar. No sound effects, no speech, no `AVAudioSession` changes, no audio or video playback of any kind.
- **No haptics.** A vibration moves the phone, the motion sensor sees it, and counting is blocked.
- **No touch needed during a set.** The phone lies on the floor under the chest and touching it counts as moving it. Start, then hands off. Everything during a set is read-only and readable at a glance from 30 to 60 cm, by someone mid push-up: the count must be huge.
- **Portrait only**, screen kept awake. Keep `UIApplication.shared.isIdleTimerDisabled = true` from the placeholder.
- Always dark. Do not follow the system light mode.

## What to build

In priority order. Finish each level before starting the next.

**1. The set screen, the part that must work for the video**

- The count, as large as the screen allows, in the display face, phosphor green with a glow.
- The depth gauge (the "water column"): scale 0 at the top to 40 cm at the bottom, tick every 5 cm, numbers every 10. A glowing bar is the chest and moves down with `depthCm`. Ease it as the page does: each frame, `shown += (depth - shown) * 0.3`. Readout `12.3 CM DOWN` at the top of the column.
- The rep line: dashed amber line at `repLineCm`, labelled `REP LINE 8 CM`. When the bar is at or below the line, the bar turns amber.
- Counted rep: the count thumps (scale 1.22 back to 1 over 0.5 s with a little overshoot, white for an instant) and the column flashes green for 0.5 s.
- NO REP: a full-screen red flash for 1.15 s. A white-bordered box tilted 5 degrees anticlockwise with `NO REP` in huge display type and a line under it, for example `too shallow: 9.0 cm of 15`. Build that line from `reason`, the rep's depth and `repLineCm`.
- Phone moved: an amber and black hazard-striped banner slides down from the top in 0.18 s reading `PHONE MOVED, NOT COUNTING`, and everything else goes grey and dim (greyscale, brightness 0.55) for as long as `phoneMoving` is true.
- Start and Stop. Before a set: one clear Start button. During a set: Stop and Reset small and out of the way.
- The Mac address: a text field kept with `@AppStorage("sonarMacHost")`, default `172.20.10.11`, numbers and punctuation keyboard, no autocorrect. Put it in a small settings sheet or on the pre-start screen. Hide it in demo (`session.source == .demo`).

**2. The rest of the page**

- `LIVE` pill with a blinking dot when `session.live`, `WAITING` when not. While running and not live, the column shows `WAITING FOR THE SONAR STREAM`, blinking.
- Under the count: `NO REPS` with its number in red, and `LAST DEPTH 24.0 CM`.
- Chips: the last 9 movements as small outlined tags, `24 cm`. A NO REP chip is red with a line through it. New chips rise in.
- Peak mark: a thin pale line held at the deepest point of the current movement. Clear it when depth falls under 1.5 cm; show it once it passes 3 cm.
- The trace: the last 12 s of depth as a glowing green line with a soft fill under it, the dashed amber rep line across it, and a small `REP` or `NO REP` mark at each finished movement. Use `Canvas` inside a `TimelineView`.
- Sonar pings: three arcs spreading up from a small phone outline at the bottom of the column, one every 0.7 s, each lasting 2.1 s, only while live.
- Header: `SONAR REPS`, wide letter spacing, and the line `No camera. Three tones near 19 kHz, echoing off your chest.`
- Background: the dark sea. A radial gradient from `#0a3a43` through `#05232b` to `#020b0e`, centred low and to the right (72% across, 82% down), faint concentric rings from the same centre, faint horizontal scan lines.

**3. Only if there is time**

- After Stop: a short set summary (reps, NO REPs, deepest, shallowest) and a `ShareLink` for `lastFileURL`.
- `LOST n` in small type, and `session.error` shown in red when it is set.

### Design tokens, from `display.html`

| Token | Value | Used for |
|---|---|---|
| ink | `#020b0e` | background edge |
| deep | `#05232b` | background middle |
| phos | `#6fffd2` | count, chest bar, trace, live |
| phos dim | `#2f8f79` | labels, borders |
| line | `#6fffd2` at 13% | ticks, dividers |
| text | `#d5fff2` | secondary numbers |
| hot | `#ff4a36` | NO REP |
| amber | `#ffb627` | rep line, phone moved, deep bar |

Type: display face `DINCondensed-Bold` (ships with iOS; fall back to `DINAlternate-Bold`), used for the count, `SONAR REPS`, the readout and `NO REP`. Everything else is the system monospaced face, upper case, wide tracking, small. Glows are `shadow(color: phos.opacity(0.7), radius: 10)` plus a wider, fainter one.

The web page is landscape with two columns. In portrait, stack it: header, count with its stats and chips, the column taking most of the height, the trace as a strip at the bottom. Target iPhone 16 Pro Max first (440 by 956 points); it must also fit an iPhone 16. Size from the available space with `GeometryReader`, not fixed numbers.

## Build and check

You need Xcode and XcodeGen (`brew install xcodegen`). Deployment target is iOS 17, so guard anything newer with `if #available`. Do not change the signing team or the bundle id, and do not try to sign: build for the simulator only.

```sh
cd ios
xcodegen generate
xcodebuild -project SonarReps.xcodeproj -scheme SonarReps \
  -destination 'platform=iOS Simulator,name=iPhone 16 Pro Max' \
  -derivedDataPath build/sim CODE_SIGNING_ALLOWED=NO build
xcrun simctl boot "iPhone 16 Pro Max"; open -a Simulator
xcrun simctl install booted build/sim/Build/Products/Debug-iphonesimulator/SonarReps.app
xcrun simctl launch booted com.adityamitter.sonarreps
xcrun simctl io booted screenshot /tmp/sonar.png
```

Run `xcodegen generate` again whenever you add a file. In the simulator, press Start and the demo set runs and repeats every 18 s:

| Second | What happens | What the screen must do |
|---|---|---|
| 1.0, 3.2, 5.4 | three full reps, 26, 24 and 27 cm | count 1, 2, 3 with a thump each |
| 7.6 | a 9 cm movement | NO REP flash, NO REPS 1, red chip |
| 9.8 | full rep, 25 cm | count 4 |
| 12 to 14.2 | phone moved | hazard banner, screen dimmed |
| 15 | full rep, 23 cm | count 5 |
| 18 | loop | everything back to zero |

Take screenshots at each of those moments and look at them before you call it done.

## Done means

- [ ] Builds for the simulator with no errors after a fresh `xcodegen generate`.
- [ ] Nothing outside `ios/UI/` changed (`git status` shows only `ios/UI/`).
- [ ] The demo loop shows every row of the table above correctly.
- [ ] No sound and no haptics anywhere.
- [ ] The count is readable from a metre away.
- [ ] Start, Stop and Reset work; the Mac address survives an app restart.
- [ ] Fits iPhone 16 Pro Max and iPhone 16 in portrait with nothing clipped.

## Hand back

- If you have push access to `adityamitter15/sonar-reps`: work on a branch called `phone-ui`, commit small and often as yourself, push the branch, and tell Addy. Do not push to `main`.
- If you do not: zip the `ios/UI/` folder and send it to Addy (AirDrop). It drops straight in.

With either, send three lines: what works, what is missing, and anything you needed from `SonarSession` that was not there.

## House rules

- Never use em dashes, anywhere: code comments, commit messages, UI text.
- Do not copy code from any other project.
- UI text must claim nothing the README does not. In particular, no accuracy figures and no "AI" label on the screen unless Addy sends you the wording.
- Match the comment style of the existing Swift files: a short header comment per file, comments only where the reason is not obvious.
