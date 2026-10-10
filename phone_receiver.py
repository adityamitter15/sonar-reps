"""Receive the iPhone's sonar stream on the Mac and count reps live.

  python phone_receiver.py [--port 5005] [--min-depth 12] [--record take.wav] [--display] [--judge]

--display also serves the live demo screen on http://localhost:8765.
--judge lets the trained rep judge (judge.json, from judge.py) decide what
counts, in place of the fixed depth line.

The verdict goes back to the phone as well, so the app can show it: about 30
times a second one JSON datagram is sent to the address the audio comes from.

    {"v": 1, "set": 3, "depth": 12.3, "count": 7, "shallow": 1,
     "moving": false, "quiet": false, "lost": 0, "min_depth": 12.0,
     "rep": {"n": 8, "valid": true, "depth": 21.4, "reason": ""}}

"rep" is the last finished movement of this set (null before the first) and
"n" its running number, so a lost datagram never loses a rep. "set" goes up
by one each time the count starts again from zero. An 8 byte packet with
flag bit 1 set and no samples is the phone asking for that reset. "quiet"
means the tones reach the microphone too weakly to count (phone volume
turned down), so nothing counts until they come back.

Network tip: university Wi-Fi often blocks device-to-device traffic. Turn on
Personal Hotspot on the iPhone and join it from the Mac; the Mac's address
is then usually 172.20.10.2 (check with: ipconfig getifaddr en0).
"""

import argparse
import json
import socket
import struct
import sys
import time

import numpy as np

from judge import REASONS, Judge, MovementFinder
from live_display import Display
from sonar_core import RepCounter, RepCounterConfig, SonarConfig, SonarTracker

# Weakest tone level at the phone's microphone that still gives a usable
# echo. Good sets measured 0.0017 to 0.0031; the set recorded with the volume
# turned down measured 0.0002 and read as noise (RESULTS.md, 13:04).
QUIET_LEVEL = 0.0008


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=5005)
    # 12 cm: fitted on the labelled full and half sets (README, Evaluation).
    ap.add_argument("--min-depth", type=float, default=12.0)
    ap.add_argument("--tones", default="18500,19100,19700")
    ap.add_argument("--record", default="")
    ap.add_argument("--display", type=int, nargs="?", const=8765, default=0, metavar="PORT",
                    help="serve the live demo screen (default port 8765)")
    ap.add_argument("--judge", action="store_true", help="count what the trained rep judge calls a full rep")
    a = ap.parse_args()

    cfg = SonarConfig(tones_hz=tuple(float(f) for f in a.tones.split(",")))
    tracker = SonarTracker(cfg)
    rep_cfg = RepCounterConfig(min_depth_cm=a.min_depth)
    judge = Judge.load() if a.judge else None
    if a.judge and judge is None:
        sys.exit("No judge.json yet. Run: python judge.py")
    line_cm = 0.0 if judge else a.min_depth  # no fixed line when the judge decides

    def fresh():
        """A count starting from zero, with the movement finder around it when the judge is on."""
        if judge:
            f = MovementFinder(tracker.rate_hz)
            return f, f.counter
        return None, RepCounter(tracker.rate_hz, rep_cfg)

    finder, counter = fresh()
    display = None
    if a.display:
        display = Display(line_cm, "iPhone", port=a.display)
        display.start()
    writer = None
    if a.record:
        import soundfile as sf
        writer = sf.SoundFile(a.record, "w", samplerate=cfg.fs, channels=1, subtype="FLOAT")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", a.port))
    print(f"Listening on UDP {a.port}. Start sonar on the phone.")
    expected = None
    lost = 0
    blocked = 0
    last_print = 0.0
    last_reply = 0.0
    set_no = 1
    was_quiet = False
    try:
        while True:
            pkt, phone = sock.recvfrom(65536)
            seq, flags = struct.unpack("<II", pkt[:8])
            if len(pkt) == 8:
                if flags & 2:
                    # The Reset button in the app: same set of tones, count from zero.
                    finder, counter = fresh()
                    set_no += 1
                    if display:
                        display.reset_requested = True
                        display.take_reset()
                continue
            x = np.frombuffer(pkt[8:], dtype="<f4").astype(np.float64)
            if expected is not None and seq != expected:
                gap = (seq - expected) & 0xFFFFFFFF
                if gap < 1000:
                    # Packets all carry the same number of samples, so step
                    # over the hole to keep the tone phase lined up.
                    lost += gap
                    skipped = gap * len(x)
                    for t in tracker.trackers:
                        t.n += skipped
                    if writer:
                        writer.write(np.zeros(skipped, dtype=np.float32))
                else:
                    # The phone restarted its stream: a new set, from zero.
                    tracker = SonarTracker(cfg)
                    finder, counter = fresh()
                    set_no += 1
                    if display:
                        display.reset_requested = True
            expected = (seq + 1) & 0xFFFFFFFF
            if writer:
                writer.write(x.astype(np.float32))
            pos = tracker.process(x)
            if display and display.take_reset():
                finder, counter = fresh()
                set_no += 1
            phone_moving = bool(flags & 1)
            quiet = tracker.heard_s > 1.0 and tracker.level < QUIET_LEVEL
            if quiet != was_quiet:
                was_quiet = quiet
                print(f"\n  TONE TOO QUIET (level {tracker.level:.4f}, need {QUIET_LEVEL}): turn the phone volume up"
                      if quiet else f"\n  tone level back to {tracker.level:.4f}, counting again")
            if phone_moving or quiet:
                # Anti-cheat: while the phone itself moves, nothing counts,
                # and the counter starts again from wherever the chest is.
                # The same holds while the tones are too quiet to trust.
                blocked += phone_moving
                counter.state = "up"
                counter.y = None
            else:
                if finder:
                    done = []
                    for r, feat in finder.process(pos, tracker.power, tracker.steadiness):
                        said = judge.verdict(feat)
                        r.valid, r.reason = said == "full", REASONS[said]
                        done.append(r)
                else:
                    done = counter.process(pos)
                for r in done:
                    mark = "REP" if r.valid else f"NO REP ({r.reason})"
                    print(f"\n  {mark}  depth {r.depth_cm:.1f} cm   total {counter.count}")
                    if display:
                        display.rep(r, counter.count)
            if display:
                display.state(counter, phone_moving, lost, quiet)
            now = time.time()
            if now - last_reply > 1 / 30:
                last_reply = now
                last = counter.reps[-1] if counter.reps else None
                depth = 0.0 if phone_moving or quiet or counter.y is None else max(0.0, counter.y - counter.top)
                reply = {
                    "v": 1, "set": set_no, "depth": round(float(depth), 2), "count": int(counter.count),
                    "shallow": int(sum(not r.valid for r in counter.reps)), "moving": phone_moving,
                    "quiet": bool(quiet), "lost": int(lost), "min_depth": float(line_cm),
                    "rep": None if last is None else {"n": len(counter.reps), "valid": bool(last.valid),
                                                      "depth": float(last.depth_cm), "reason": last.reason},
                }
                try:
                    sock.sendto(json.dumps(reply).encode(), phone)
                except OSError:
                    pass  # the phone left the network; the count carries on
            if now - last_print > 0.05 and len(pos):
                last_print = now
                depth = (counter.y - counter.top) if counter.y is not None else 0.0
                bar = int(np.clip(depth * 2, 0, 60))
                sys.stdout.write(f"\r  depth {depth:5.1f} cm |{'#'*bar:<60}| reps {counter.count}  lost {lost}  ")
                sys.stdout.flush()
    except KeyboardInterrupt:
        pass
    if writer:
        writer.close()
    print(f"\nFinal: {counter.count} valid, {sum(not r.valid for r in counter.reps)} refused, "
          f"{lost} packets lost, {blocked} blocks ignored while the phone moved")


if __name__ == "__main__":
    main()
