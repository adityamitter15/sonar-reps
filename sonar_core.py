"""Sonar core: turn a phone's own speaker and microphone into a short-range sonar.

The speaker plays a few continuous near-ultrasonic tones (18 to 20 kHz). The
microphone hears the direct sound plus echoes. A chest moving towards or away
from the phone changes the length of the echo path, which rotates the phase of
the echo: one full turn for every half wavelength, about 0.9 cm.

Pipeline:
    mic samples
    -> per tone: mix down to 0 Hz (I/Q), low-pass, null the other tones,
       decimate to ~1 kHz
    -> per tone: remove the static part (direct sound, floor, walls) with a
       2 Hz high-pass, which also takes out slow drift of the speaker
    -> all tones together: phase step per sample from the lag-1 products
       (the pulse-pair estimate used in Doppler radar and ultrasound)
    -> path change -> displacement

Summing the lag-1 products over tones and over a few milliseconds weights
each tone by its echo strength, so a tone fading in a multipath null drops
out by itself, and noise pulls the estimate towards "not moving" instead of
sending it wandering. Everything is block based, so the same code runs on a
live stream or on a recorded file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence

import numpy as np
from scipy.signal import butter, lfilter, sosfilt, sosfilt_zi

SPEED_OF_SOUND = 343.0  # m/s at about 20 C


@dataclass
class SonarConfig:
    fs: int = 48_000
    tones_hz: Sequence[float] = (18_500.0, 19_100.0, 19_700.0)
    lowpass_hz: float = 150.0  # keeps Doppler up to about 1.3 m/s
    decim: int = 48  # 48 kHz -> 1 kHz baseband
    static_hz: float = 2.0  # anything slower than this is static (about 2 cm/s)
    average_ms: int = 32  # lag-1 products are averaged over this long


class ToneTracker:
    """Baseband echo of one carrier tone with the static part removed, streaming."""

    def __init__(self, cfg: SonarConfig, f_hz: float):
        self.cfg = cfg
        self.f = f_hz
        self.sos = butter(4, cfg.lowpass_hz, fs=cfg.fs, output="sos")
        zi = sosfilt_zi(self.sos)
        self.zi_i = zi * 0.0
        self.zi_q = zi * 0.0
        # Moving average over one beat of the tone spacing: its nulls sit
        # exactly on the other tones. On a phone the direct sound of each
        # tone is about 200 times stronger than the echo, so what the
        # low-pass lets through of a neighbour would swamp the echo.
        gaps = [abs(f - f_hz) for f in cfg.tones_hz if f != f_hz]
        n_avg = int(round(cfg.fs / min(gaps))) if gaps else 1
        self.avg = np.ones(n_avg) / n_avg
        self.za_i = np.zeros(n_avg - 1)
        self.za_q = np.zeros(n_avg - 1)
        self.n = 0  # global sample index
        self.level = 0.0  # tone amplitude at the microphone in the last block (direct sound)
        # Static removal. Second order, so a steady drift of the direct
        # sound (a phone speaker warming up) is removed as well as its level.
        self.hp = butter(2, cfg.static_hz, btype="highpass", fs=cfg.fs / cfg.decim, output="sos")
        self.zs: Optional[np.ndarray] = None

    def process(self, x: np.ndarray) -> np.ndarray:
        """Return the moving part of the echo (complex) at the decimated rate."""
        cfg = self.cfg
        idx = self.n + np.arange(len(x))
        w = 2.0 * np.pi * self.f / cfg.fs
        i = x * np.cos(w * idx)
        q = -x * np.sin(w * idx)
        i, self.zi_i = sosfilt(self.sos, i, zi=self.zi_i)
        q, self.zi_q = sosfilt(self.sos, q, zi=self.zi_q)
        i, self.za_i = lfilter(self.avg, 1.0, i, zi=self.za_i)
        q, self.za_q = lfilter(self.avg, 1.0, q, zi=self.za_q)
        keep = (idx % cfg.decim) == 0
        self.n += len(x)
        z = (i[keep] + 1j * q[keep]) * 2.0
        if len(z) == 0:
            return z
        self.level = float(np.abs(z.mean()))
        if self.zs is None:
            self.zs = sosfilt_zi(self.hp) * z[0]  # as if the signal had always been here
        d, self.zs = sosfilt(self.hp, z, zi=self.zs)
        return d


class SonarTracker:
    """Combines the tones into one displacement stream."""

    def __init__(self, cfg: SonarConfig = SonarConfig()):
        self.cfg = cfg
        self.trackers = [ToneTracker(cfg, f) for f in cfg.tones_hz]
        self.position_m = 0.0
        self.prev = np.zeros(len(cfg.tones_hz), dtype=complex)
        n_avg = max(1, int(round(cfg.average_ms * 1e-3 * self.rate_hz)))
        self.avg = np.ones(n_avg) / n_avg
        self.za = np.zeros(n_avg - 1, dtype=complex)
        self.zp = np.zeros(n_avg - 1)
        # Side information for the last block, one value per returned sample:
        # power of the moving part of the echo, and how steadily its phase
        # turns (near 1 for one clean reflector, near 0 for noise).
        self.power = np.zeros(0)
        self.steadiness = np.zeros(0)
        # Weakest tone at the microphone, smoothed over about a second. If
        # the phone volume is turned down this falls and the echo is lost.
        self.level = 0.0
        self.heard_s = 0.0
        # Phase to reflector movement. The tones are within 3 % of each other,
        # so one wavelength serves for the sum.
        self.scale = SPEED_OF_SOUND / float(np.mean(cfg.tones_hz)) / (4.0 * np.pi)

    @property
    def rate_hz(self) -> float:
        return self.cfg.fs / self.cfg.decim

    def process(self, x: np.ndarray) -> np.ndarray:
        """Feed raw mic samples, get cumulative displacement in metres
        (positive = closer to the phone) at about 1 kHz."""
        d = np.vstack([t.process(x) for t in self.trackers])
        if d.shape[1] == 0:
            return np.zeros(0)
        weakest = min(t.level for t in self.trackers)
        block_s = len(x) / self.cfg.fs
        self.level = weakest if self.heard_s == 0.0 else self.level + min(1.0, block_s) * (weakest - self.level)
        self.heard_s += block_s
        # Lag-1 products: each one turns by the phase the echo gained in one
        # sample. Phase rises as the echo path shortens, and the path changes
        # by twice the reflector's movement.
        before = np.column_stack([self.prev, d[:, :-1]])
        self.prev = d[:, -1].copy()
        p = (d * np.conj(before)).sum(axis=0)
        p, self.za = lfilter(self.avg, 1.0, p, zi=self.za)
        self.power, self.zp = lfilter(self.avg, 1.0, (np.abs(d) ** 2).sum(axis=0), zi=self.zp)
        self.steadiness = np.abs(p) / np.maximum(self.power, 1e-30)
        pos = self.position_m + np.cumsum(np.angle(p) * self.scale)
        self.position_m = pos[-1]
        return pos


@dataclass
class Rep:
    t_start: float
    t_bottom: float
    t_end: float
    depth_cm: float
    valid: bool
    reason: str = ""


@dataclass
class RepCounterConfig:
    min_depth_cm: float = 15.0  # a rep must travel at least this far
    start_down_cm: float = 3.0  # movement that opens a rep
    # A rep closes once it is back within this share of its depth from the
    # top. 0.7 since the deep set of 13:26: after a pause at the bottom the
    # way up reads short, and at 0.6 two of five deep reps never closed.
    return_frac: float = 0.7
    smooth_hz: float = 4.0
    rest_reset_s: float = 0.8  # re-anchor the top after this long still


@dataclass
class RepCounter:
    """Hysteresis state machine on chest position (closer = larger)."""

    rate_hz: float
    cfg: RepCounterConfig = field(default_factory=RepCounterConfig)
    reps: List[Rep] = field(default_factory=list)

    def __post_init__(self):
        self.alpha = 1.0 - np.exp(-2.0 * np.pi * self.cfg.smooth_hz / self.rate_hz)
        self.y: Optional[float] = None
        self.state = "up"
        self.top = 0.0
        self.bottom = 0.0
        self.t = 0.0
        self.t_start = 0.0
        self.t_bottom = 0.0
        self.still_since = 0.0
        self.last_y = 0.0

    @property
    def count(self) -> int:
        return sum(r.valid for r in self.reps)

    def process(self, pos_m: np.ndarray) -> List[Rep]:
        new: List[Rep] = []
        dt = 1.0 / self.rate_hz
        for p in pos_m * 100.0:  # to cm
            self.t += dt
            if self.y is None:
                self.y = p
                self.top = p
            self.y += self.alpha * (p - self.y)
            y = self.y
            moving = abs(y - self.last_y) > 0.02  # cm per sample (about 20 cm/s)
            self.last_y = y
            if moving:
                self.still_since = self.t
            if self.state == "up":
                if y < self.top:
                    self.top = y
                if (self.t - self.still_since) > self.cfg.rest_reset_s:
                    self.top = y  # absorb drift while resting at the top
                if y - self.top > self.cfg.start_down_cm:
                    self.state = "down"
                    self.t_start = self.t
                    self.bottom = y
                    self.t_bottom = self.t
            else:
                if y > self.bottom:
                    self.bottom = y
                    self.t_bottom = self.t
                depth = self.bottom - self.top
                back = self.bottom - y
                if depth > 0 and back > (1.0 - self.cfg.return_frac) * depth and back > self.cfg.start_down_cm:
                    valid = depth >= self.cfg.min_depth_cm
                    rep = Rep(
                        t_start=self.t_start,
                        t_bottom=self.t_bottom,
                        t_end=self.t,
                        depth_cm=round(depth, 1),
                        valid=valid,
                        reason="" if valid else "too shallow",
                    )
                    self.reps.append(rep)
                    new.append(rep)
                    self.state = "up"
                    self.top = y
        return new


def tone_block(cfg: SonarConfig, n0: int, n: int, amp: float = 0.25) -> np.ndarray:
    """Transmit signal for samples [n0, n0+n). Double precision phase avoids
    the audible artefacts single precision causes."""
    idx = (n0 + np.arange(n)).astype(np.float64)
    out = np.zeros(n)
    for f in cfg.tones_hz:
        out += np.sin(2.0 * np.pi * f * idx / cfg.fs)
    return (amp / len(cfg.tones_hz)) * out
