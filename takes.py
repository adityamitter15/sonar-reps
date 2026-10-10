"""Labelled real recordings: the regression set and the evaluation table.

  python takes.py
      Replay every stored take and print counted reps against true reps.

  python takes.py add recordings/book.wav book_10 --kind "book over laptop" --true 10
      Store a new take with its label. The counts it gives today become the
      expected counts, so later changes to the pipeline cannot move them
      unnoticed.

Takes live in takes/ as FLAC with everything below 17.5 kHz filtered out, so
they hold the sonar band only and no speech from the room.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfiltfilt

from sonar_core import RepCounter, RepCounterConfig, SonarConfig, SonarTracker

TAKES = Path(__file__).parent / "takes"
LABELS = TAKES / "labels.json"
KEEP_ABOVE_HZ = 17_500.0


def load_labels():
    return json.loads(LABELS.read_text()) if LABELS.exists() else []


def count(x, fs, tones_hz, min_depth_cm):
    cfg = SonarConfig(fs=fs, tones_hz=tuple(tones_hz))
    tr = SonarTracker(cfg)
    rc = RepCounter(tr.rate_hz, RepCounterConfig(min_depth_cm=min_depth_cm))
    for i in range(0, len(x), 1024):
        rc.process(tr.process(x[i:i + 1024]))
    return rc


def run_take(label):
    x, fs = sf.read(TAKES / label["file"], dtype="float64", always_2d=True)
    return count(x[:, 0], fs, label["tones_hz"], label["min_depth_cm"])


def run_all():
    """Replay every take. True when all counts match what was stored."""
    all_ok = True
    for label in load_labels():
        rc = run_take(label)
        valid, shallow = rc.count, sum(not r.valid for r in rc.reps)
        ok = valid == label["expect_valid"] and shallow == label["expect_shallow"]
        all_ok &= ok
        print(f"{'PASS' if ok else 'FAIL'}  take {label['name']} ({label['kind']}): "
              f"true {label['true_reps']}, valid {valid}/{label['expect_valid']}, "
              f"shallow {shallow}/{label['expect_shallow']}, "
              f"depths cm {[float(r.depth_cm) for r in rc.reps]}")
    return all_ok


def add(a):
    x, fs = sf.read(a.wav, dtype="float64", always_2d=True)
    sos = butter(8, KEEP_ABOVE_HZ, btype="highpass", fs=fs, output="sos")
    x = sosfiltfilt(sos, x[:, 0])
    TAKES.mkdir(exist_ok=True)
    name = f"{a.name}.flac"
    sf.write(TAKES / name, x, fs, subtype="PCM_16")
    label = {
        "name": a.name,
        "file": name,
        "kind": a.kind,
        "true_reps": a.true,
        "min_depth_cm": a.min_depth,
        "tones_hz": [float(f) for f in a.tones.split(",")],
        "note": a.note,
    }
    # What the push-ups in it were, for the rep judge (see judge.py).
    if a.label:
        label["label"] = a.label
    if a.sequence:
        label["sequence"] = a.sequence
    if a.moves:
        label["moves"] = a.moves
    rc = run_take(label)
    label["expect_valid"] = int(rc.count)
    label["expect_shallow"] = int(sum(not r.valid for r in rc.reps))
    labels = [l for l in load_labels() if l["name"] != a.name] + [label]
    LABELS.write_text(json.dumps(labels, indent=2) + "\n")
    print(f"stored takes/{name} ({(TAKES / name).stat().st_size / 1e6:.1f} MB): true {a.true}, "
          f"valid {label['expect_valid']}, shallow {label['expect_shallow']}, "
          f"depths cm {[float(r.depth_cm) for r in rc.reps]}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("add")
    p.add_argument("wav")
    p.add_argument("name")
    p.add_argument("--kind", required=True, help="what was done, for the table")
    p.add_argument("--true", type=int, required=True, help="reps really done")
    p.add_argument("--min-depth", type=float, default=RepCounterConfig().min_depth_cm)
    p.add_argument("--tones", default="18500,19100,19700")
    p.add_argument("--note", default="")
    p.add_argument("--label", choices=["full", "half", "none"], default="",
                   help="what every push-up in the take was, for the rep judge")
    p.add_argument("--sequence", default="", help="mixed set, in order: F full, H half, for example FHFHF")
    p.add_argument("--moves", type=int, default=0,
                   help="push-up movements done, when not all should count (10 half reps: --true 0 --moves 10)")
    a = ap.parse_args()
    if a.cmd == "add":
        add(a)
    else:
        print("ALL PASS" if run_all() else "SOME FAILED")
