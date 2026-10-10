"""Rep judge: a small trained model that says what each movement was.

  python judge.py                  Train on the labelled takes, test each take on a
                                   model that never saw it, and write judge.json.
  python judge.py show take.wav    List the movements in a recording with their
                                   numbers and, if judge.json exists, the verdicts.

The sonar gives a trace of chest movement. A fixed depth line cannot judge it:
full push-ups read anywhere from 9 to 25 cm from one set to the next. So every
down and up is found with a low bar, described by a few numbers, and judged by
a model trained on our own recordings:

    full   a full rep, the only verdict that counts
    half   a push-up that did not go deep enough
    none   not a push-up: a hand, someone walking past, the phone being handled

The model is softmax regression on standardised features, fitted with plain
numpy, so the whole judge is a few dozen numbers in judge.json and ports to
the phone as they are.

Labels come from takes/labels.json. A take is used when it has either
    "label": "full" | "half" | "none"     every push-up in it is of that kind
    "sequence": "FHFHF..."                 its push-ups in order, F full, H half
The true_reps deepest movements of a take are its push-ups; anything else in
it (getting into position, standing up) is labelled none.
"""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

from sonar_core import Rep, RepCounter, RepCounterConfig, SonarConfig, SonarTracker

MODEL = Path(__file__).parent / "judge.json"
CLASSES = ("full", "half", "none")
REASONS = {"full": "", "half": "half rep", "none": "not a push-up"}
FEATURES = ("depth_cm", "down_s", "rise_s", "peak_down_cm_s", "peak_up_cm_s", "echo_db", "steadiness")
FLOOR_CM = 4.0  # anything that travels less than this is not even looked at
HISTORY_S = 12.0


class MovementFinder:
    """Finds every down and up in the chest trace and describes each one.

    Feed it the tracker's output block by block. It works the same on a live
    stream and on a file.
    """

    def __init__(self, rate_hz: float):
        self.rate = rate_hz
        self.counter = RepCounter(rate_hz, RepCounterConfig(min_depth_cm=FLOOR_CM))
        n = int(HISTORY_S * rate_hz)
        self.pos = deque(maxlen=n)  # cm
        self.power = deque(maxlen=n)
        self.steady = deque(maxlen=n)
        self.t = 0.0  # time of the newest sample

    def process(self, pos_m: np.ndarray, power: np.ndarray, steadiness: np.ndarray) -> List[Tuple[Rep, dict]]:
        self.pos.extend(pos_m * 100.0)
        self.power.extend(power)
        self.steady.extend(steadiness)
        self.t += len(pos_m) / self.rate
        return [(r, self.describe(r)) for r in self.counter.process(pos_m)]

    def describe(self, r: Rep) -> dict:
        pos = np.asarray(self.pos)
        power = np.asarray(self.power)
        steady = np.asarray(self.steady)
        t0 = self.t - len(pos) / self.rate  # time of the oldest sample kept

        def at(t):
            return int(np.clip(round((t - t0) * self.rate), 0, len(pos) - 1))

        a, b, c = at(r.t_start - 0.3), at(r.t_bottom), at(r.t_end)
        b = max(b, a + 2)
        c = max(c, b + 2)
        k = max(1, int(0.05 * self.rate))  # 50 ms smoothing before taking speeds
        # Padded with its own end values: the newest sample is the edge of the buffer.
        smooth = np.convolve(np.pad(pos, k, mode="edge"), np.ones(k) / k, mode="same")[k:-k]
        v = np.gradient(smooth) * self.rate
        heard = power[power > 0]  # a file can open with digital silence
        rest = np.percentile(heard if len(heard) else power, 5) + 1e-30  # the quietest moments kept
        return {
            "depth_cm": float(r.depth_cm),
            "down_s": float(r.t_bottom - r.t_start),
            "rise_s": float(r.t_end - r.t_bottom),
            "peak_down_cm_s": float(v[a:b].max()),
            "peak_up_cm_s": float(-v[b:c].min()),
            "echo_db": float(10.0 * np.log10(power[a:c].mean() / rest)),
            "steadiness": float(steady[a:c].mean()),
        }


class Judge:
    """Softmax regression over the movement features."""

    def __init__(self, classes, mean, std, w, b):
        self.classes = list(classes)
        self.mean = np.asarray(mean, dtype=float)
        self.std = np.asarray(std, dtype=float)
        self.w = np.asarray(w, dtype=float)
        self.b = np.asarray(b, dtype=float)

    @staticmethod
    def matrix(feats: List[dict]) -> np.ndarray:
        return np.array([[f[k] for k in FEATURES] for f in feats], dtype=float)

    @classmethod
    def fit(cls, feats: List[dict], labels: List[str], l2: float = 0.05, steps: int = 3000) -> "Judge":
        classes = [c for c in CLASSES if c in set(labels)]
        x = cls.matrix(feats)
        mean, std = x.mean(axis=0), x.std(axis=0) + 1e-9
        z = (x - mean) / std
        y = np.eye(len(classes))[[classes.index(l) for l in labels]]
        # Each class pulls its weight however many examples it has.
        weight = (y / y.sum(axis=0)).sum(axis=1)
        weight /= weight.mean()
        w = np.zeros((z.shape[1], len(classes)))
        b = np.zeros(len(classes))
        for _ in range(steps):
            s = z @ w + b
            p = np.exp(s - s.max(axis=1, keepdims=True))
            p /= p.sum(axis=1, keepdims=True)
            g = (p - y) * weight[:, None] / len(z)
            w -= 0.5 * (z.T @ g + l2 * w)
            b -= 0.5 * g.sum(axis=0)
        return cls(classes, mean, std, w, b)

    def verdict(self, feat: dict) -> str:
        s = ((self.matrix([feat]) - self.mean) / self.std) @ self.w + self.b
        return self.classes[int(np.argmax(s))]

    def save(self, path: Path = MODEL, **extra):
        path.write_text(json.dumps({
            "features": list(FEATURES), "classes": self.classes, "mean": self.mean.tolist(),
            "std": self.std.tolist(), "w": self.w.tolist(), "b": self.b.tolist(), **extra}, indent=1) + "\n")

    @classmethod
    def load(cls, path: Path = MODEL) -> Optional["Judge"]:
        if not path.exists():
            return None
        m = json.loads(path.read_text())
        if tuple(m["features"]) != FEATURES:
            raise SystemExit(f"{path} was trained on other features; run python judge.py again")
        return cls(m["classes"], m["mean"], m["std"], m["w"], m["b"])


def movements(x: np.ndarray, fs: int, tones_hz) -> List[Tuple[Rep, dict]]:
    """Every movement in a recording, with its features."""
    tr = SonarTracker(SonarConfig(fs=fs, tones_hz=tuple(tones_hz)))
    finder = MovementFinder(tr.rate_hz)
    out = []
    for i in range(0, len(x), 1024):
        pos = tr.process(x[i:i + 1024])
        out += finder.process(pos, tr.power, tr.steadiness)
    return out


def labelled(take: dict, moves: List[Tuple[Rep, dict]]) -> Tuple[List[str], str]:
    """The true label of each movement in a take, and a note if the take does not add up."""
    seq = take.get("sequence")
    # "moves" is how many push-up movements were done when that differs from
    # the reps that should count (a set of half reps: 10 moves, 0 true reps).
    n = len(seq) if seq else int(take.get("moves", take["true_reps"]))
    kinds = [{"F": "full", "H": "half"}[ch] for ch in seq.upper()] if seq else [take["label"]] * n
    if take.get("label") == "none":
        return ["none"] * len(moves), ""
    order = np.argsort([-f["depth_cm"] for _, f in moves])[:n]
    labels = ["none"] * len(moves)
    for kind, i in zip(kinds, sorted(order)):  # push-ups in the order they were done
        labels[i] = kind
    note = "" if len(moves) >= n else f"only {len(moves)} of {n} push-ups were found"
    return labels, note


def load_takes():
    import soundfile as sf
    from takes import LABELS, TAKES
    out = []
    for take in json.loads(LABELS.read_text()):
        if "label" not in take and "sequence" not in take:
            continue
        x, fs = sf.read(TAKES / take["file"], dtype="float64", always_2d=True)
        moves = movements(x[:, 0], fs, take["tones_hz"])
        labels, note = labelled(take, moves)
        out.append((take, [f for _, f in moves], labels, note))
    return out


def best_line(feats, labels) -> float:
    """The fixed depth line that best separates full reps from everything else."""
    depth = np.array([f["depth_cm"] for f in feats])
    full = np.array([l == "full" for l in labels])
    lines = np.arange(FLOOR_CM, 40.0, 0.5)
    return float(lines[int(np.argmax([np.mean((depth >= ln) == full) for ln in lines]))])


def train():
    data = load_takes()
    if not data:
        raise SystemExit("no take in takes/labels.json has a label yet")
    print("Movements per take:")
    for take, feats, labels, note in data:
        counts = {c: labels.count(c) for c in CLASSES if c in labels}
        print(f"  {take['name']:22s} {counts}" + (f"   NOTE: {note}" if note else ""))
    every_f = [f for _, feats, _, _ in data for f in feats]
    every_l = [l for _, _, labels, _ in data for l in labels]
    if len(set(every_l)) < 2:
        raise SystemExit("only one kind of movement is labelled so far; nothing to learn yet")

    # Each take is judged by a model, and a fixed line, that never saw it.
    print("\nEach take judged without having been trained on:")
    print("| Take | Kind | True full reps | Model counted | Fixed line counted | Model verdicts right |")
    print("|---|---|---|---|---|---|")
    hit = total = 0
    confusion = {a: {b: 0 for b in CLASSES} for a in CLASSES}
    for k, (take, feats, labels, _) in enumerate(data):
        tf = [f for j, d in enumerate(data) if j != k for f in d[1]]
        tl = [l for j, d in enumerate(data) if j != k for l in d[2]]
        if len(set(tl)) < 2 or not feats:
            continue
        judge, line = Judge.fit(tf, tl), best_line(tf, tl)
        said = [judge.verdict(f) for f in feats]
        for a, b in zip(labels, said):
            confusion[a][b if b in CLASSES else "none"] += 1
        right = sum(a == b for a, b in zip(labels, said))
        hit += right
        total += len(labels)
        print(f"| {take['name']} | {take['kind']} | {labels.count('full')} | {said.count('full')} | "
              f"{sum(f['depth_cm'] >= line for f in feats)} (line {line:.1f} cm) | {right} of {len(labels)} |")
    if total:
        print(f"\nModel verdicts right on unseen takes: {hit} of {total}")
        print("\n| True \\\\ Model said | " + " | ".join(CLASSES) + " |\n|---|" + "---|" * len(CLASSES))
        for a in CLASSES:
            if sum(confusion[a].values()):
                print(f"| {a} | " + " | ".join(str(confusion[a][b]) for b in CLASSES) + " |")

    judge = Judge.fit(every_f, every_l)
    judge.save(trained_on={c: every_l.count(c) for c in CLASSES}, takes=[d[0]["name"] for d in data])
    print(f"\nWrote {MODEL.name}, trained on {len(every_l)} movements from {len(data)} takes: "
          + ", ".join(f"{every_l.count(c)} {c}" for c in CLASSES))


def show(wav: str, tones: str):
    import soundfile as sf
    x, fs = sf.read(wav, dtype="float64", always_2d=True)
    judge = Judge.load()
    for k, (r, f) in enumerate(movements(x[:, 0], fs, [float(t) for t in tones.split(",")]), 1):
        said = judge.verdict(f) if judge else "?"
        print(f"{k:3d}. {r.t_start:6.2f}s  {said:5s} " + "  ".join(f"{name} {f[name]:6.2f}" for name in FEATURES))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("show")
    p.add_argument("wav")
    p.add_argument("--tones", default="18500,19100,19700")
    a = ap.parse_args()
    show(a.wav, a.tones) if a.cmd == "show" else train()
