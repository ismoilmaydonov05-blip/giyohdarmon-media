#!/usr/bin/env python3
"""Synthesizes ORIGINAL upbeat, cheerful background tracks (marimba plucks, bass, ukulele-like strums, soft drums).
Everything is generated from scratch with numpy (no samples, no third-party music), so there is no copyright/licence issue.

Usage: python3 make_music_upbeat.py <out_dir>
  -> upbeat_sunrise.mp3 (gentlest, 100 BPM), upbeat_walk.mp3 (108), upbeat_market.mp3 (114), upbeat_garden.mp3 (104), upbeat_bloom.mp3 (106)
The calm tracks (calm_*.mp3) come from make_music.py.
"""
import sys, os, subprocess
import numpy as np
from scipy.signal import butter, sosfilt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from make_music import SR, DUR, hz, midi, reverb          # same sample rate / length / helpers as the calm tracks

_rng = np.random.default_rng(11)
_NOISE = _rng.standard_normal(SR * 3)
HAT_N = sosfilt(butter(4, 7000, 'high', fs=SR, output='sos'), _NOISE)
CLAP_N = sosfilt(butter(3, [1100, 3800], 'band', fs=SR, output='sos'), _NOISE)
SHK_N = sosfilt(butter(3, [4500, 11000], 'band', fs=SR, output='sos'), _NOISE)


def _norm(s):
    return s / (np.abs(s).max() + 1e-9)


def _env(n, rate, attack=0.002):
    t = np.arange(n) / SR
    e = np.exp(-t * rate)
    na = max(1, int(attack * SR))
    e[:na] *= np.linspace(0, 1, na)
    return e


def kick():
    n = int(0.28 * SR); t = np.arange(n) / SR
    f = 48 + 95 * np.exp(-t * 34)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, 13, 0.001)
    s += np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 220) * 0.15
    return _norm(s)


def clap(off):
    n = int(0.22 * SR); t = np.arange(n) / SR
    burst = np.zeros(n)
    for d, g in ((0.0, 1.0), (0.011, 0.8), (0.022, 0.7)):
        a = int(d * SR); burst[a:] += g * np.exp(-t[:n - a] * 160)
    e = burst * 0.6 + np.exp(-t * 20) * 0.7
    return _norm(CLAP_N[off:off + n] * e)


def hat(off, open_=False):
    n = int((0.22 if open_ else 0.07) * SR)
    return _norm(HAT_N[off:off + n] * _env(n, 16 if open_ else 75, 0.001))


def shaker(off):
    n = int(0.09 * SR)
    t = np.arange(n) / SR
    e = np.minimum(1, t / 0.012) * np.exp(-t * 45)
    return _norm(SHK_N[off:off + n] * e)


def bass(m, dur):
    n = int((dur + 0.05) * SR); t = np.arange(n) / SR; f = hz(m)
    s = (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(4 * np.pi * f * t) * np.exp(-t * 9)
         + 0.25 * np.sin(6 * np.pi * f * t) * np.exp(-t * 14))
    e = np.exp(-t * 3.2)
    na = int(0.004 * SR); e[:na] *= np.linspace(0, 1, na)
    nr = min(n, int(0.04 * SR)); e[-nr:] *= np.linspace(1, 0, nr)
    return _norm(s * e)


def marimba(m, dur=0.9):
    n = int(dur * SR); t = np.arange(n) / SR; f = hz(m)
    s = (np.sin(2 * np.pi * f * t) * np.exp(-t * 6.5) + 0.45 * np.sin(2 * np.pi * 4 * f * t + 0.3) * np.exp(-t * 26)
         + 0.18 * np.sin(2 * np.pi * 10 * f * t) * np.exp(-t * 60))
    na = int(0.0015 * SR); s[:na] *= np.linspace(0, 1, na)
    return _norm(s)


def strum(notes, dur, down):
    n = int((dur + 0.5) * SR); out = np.zeros(n)
    order = notes if down else notes[::-1]
    for k, m in enumerate(order):
        a = int(k * 0.011 * SR); L = n - a; t = np.arange(L) / SR; f = hz(m)
        s = sum(np.sin(2 * np.pi * f * h * t + 0.7 * h) / h ** 1.2 for h in range(1, 7)) * np.exp(-t * (9 + 2 * k))
        na = int(0.002 * SR); s[:na] *= np.linspace(0, 1, na)
        rel = int(dur * SR)
        if rel < L: s[rel:] *= np.exp(-np.arange(L - rel) / SR * 40)
        out[a:] += s
    return _norm(out)


def pad(notes, dur):
    n = int((dur + 0.6) * SR); t = np.arange(n) / SR; s = np.zeros(n)
    for k, m in enumerate(notes):
        for dt in (0.0, 0.004):
            f = hz(m) * (1 + dt)
            s += (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)) / (1 + 0.15 * k)
    e = np.ones(n); na = int(0.18 * SR); nr = int(0.6 * SR)
    e[:na] = np.linspace(0, 1, na); e[-nr:] = np.linspace(1, 0, nr)
    return _norm(s * e)


def put(L, R, a, sig, gain, pan=0.5):
    if a < 0 or a >= len(L): return
    e = min(len(L), a + len(sig)); seg = sig[:e - a] * gain
    L[a:e] += seg * (1 - pan) * 1.4142; R[a:e] += seg * pan * 1.4142


def build(cfg):
    bpm = cfg['bpm']; step = 60.0 / bpm / 4; bar = step * 16
    rng = np.random.default_rng(cfg['seed'])
    n = int(DUR * SR); L = np.zeros(n); R = np.zeros(n)
    K = kick(); chords = cfg['chords']; pats = cfg['arp_patterns']
    nbars = int(DUR / bar) + 1
    for b in range(nbars):
        sec = (b // 8) % 4; pos = b % 8
        root, triad, arp = chords[b % len(chords)]
        t0 = b * bar
        # pad (soft sustained chord)
        put(L, R, int(t0 * SR), pad([midi(x) for x in triad], bar), cfg['pad'][sec], 0.5)
        for s_ in range(16):
            t = t0 + s_ * step
            if s_ % 4 == 2: t += cfg.get('swing', 0.0) * step          # swing the off-8ths
            t += rng.uniform(-0.003, 0.003)                            # tiny human timing
            a = int(t * SR); v = rng.uniform(0.9, 1.05)
            # drums
            if cfg['kick'][sec] and s_ in cfg['kick_steps'](b):
                if not (sec == 2 and pos < 2): put(L, R, a, K, cfg['kick'][sec] * v, 0.5)
            if cfg['clap'][sec] and s_ in (4, 12):
                put(L, R, a, clap(int(rng.integers(0, SR))), cfg['clap'][sec] * v, 0.5)
            if cfg['hat'] and s_ % 2 == 0:
                acc = 1.0 if s_ % 4 == 2 else 0.6
                put(L, R, a, hat(int(rng.integers(0, SR)), open_=(s_ == 14 and pos % 2 == 1)), cfg['hat'] * acc * v, 0.62)
            if cfg['shaker'] and sec in (1, 3) and s_ % 2 == 1:
                put(L, R, a, shaker(int(rng.integers(0, SR))), cfg['shaker'] * v, 0.35)
            # bass
            if s_ in cfg['bass_steps']:
                idx = cfg['bass_steps'].index(s_)
                m = midi(root) + (12 if idx % 5 == 4 else 0) + (7 if idx % 4 == 2 else 0)
                put(L, R, a, bass(m, step * 2.6), cfg['bass'] * v, 0.5)
            # ukulele-like strums on the off-beats
            if cfg['strum'][sec] and s_ in cfg['strum_steps']:
                put(L, R, a, strum([midi(x) for x in triad[1:]] + [midi(triad[0]) + 12], step * 1.6, (s_ // 2) % 2 == 0),
                    cfg['strum'][sec] * v, 0.5)
            # marimba arpeggio (8th notes) with section-dependent pattern
            if s_ % 2 == 0:
                pat = pats[sec]; i = (s_ // 2) % len(pat)
                if pat[i] is not None:
                    m = midi(arp[pat[i] % len(arp)]) + (12 if (sec in (1, 3) and b % 2 == 1 and i in (3, 7)) else 0)
                    put(L, R, a, marimba(m), cfg['marimba'][sec] * v, 0.5 + 0.28 * np.sin(b * 1.3 + i))
    x = np.stack([L, R])
    x = sosfilt(butter(2, 10000, 'low', fs=SR, output='sos'), x, axis=1)
    x = sosfilt(butter(2, 50, 'high', fs=SR, output='sos'), x, axis=1)
    x = reverb(x, rt=1.5, mix=0.14)
    x = np.tanh(x * 1.6) / 1.6                                          # gentle glue / soft clip
    fade = int(0.35 * SR); x[:, :fade] *= np.linspace(0, 1, fade)
    fo = int(2.5 * SR); x[:, -fo:] *= np.linspace(1, 0, fo)
    x *= cfg.get('rms', 0.055) / (np.sqrt((x ** 2).mean()) + 1e-9)
    pk = np.abs(x).max()
    if pk > 0.5: x *= 0.5 / pk
    return x


def kick_steps_basic(b):  return (0, 8) if b % 2 == 0 else (0, 8, 10)
def kick_steps_four(b):   return (0, 4, 8, 12)
def kick_steps_bounce(b): return (0, 6, 8, 14) if b % 2 == 0 else (0, 8, 11)

TRACKS = {
    # gentlest of the set (used for sensitive health topics): C major, I-V-vi-IV
    'upbeat_sunrise': dict(bpm=100, seed=21, swing=0.0, rms=0.050,
        chords=[('C3', ['C4', 'E4', 'G4'], ['C5', 'E5', 'G5', 'D5', 'A4', 'E4']),
                ('G2', ['B3', 'D4', 'G4'], ['B4', 'D5', 'G5', 'A4', 'E5', 'G4']),
                ('A2', ['A3', 'C4', 'E4'], ['A4', 'C5', 'E5', 'B4', 'G4', 'C5']),
                ('F2', ['A3', 'C4', 'F4'], ['A4', 'C5', 'F5', 'G4', 'E5', 'C5'])],
        arp_patterns=[[0, 2, 1, 2, 0, 3, 1, 2], [0, 1, 2, 3, 2, 1, 4, 2], [0, 2, 4, 2, 1, 3, 5, 3], [0, 1, 2, 3, 2, 1, 0, 2]],
        pad=[0.30, 0.22, 0.26, 0.22], kick=[0.55, 0.75, 0.60, 0.75], kick_steps=kick_steps_basic, clap=[0.0, 0.30, 0.15, 0.30],
        hat=0.10, shaker=0.0, bass=0.55, bass_steps=[0, 6, 8, 14], strum=[0.0, 0.20, 0.12, 0.20], strum_steps=(2, 10), marimba=[0.45, 0.42, 0.50, 0.42]),
    # G major, I-vi-IV-V: friendly "walking" feel
    'upbeat_walk': dict(bpm=108, seed=22, swing=0.0, rms=0.055,
        chords=[('G2', ['G3', 'B3', 'D4'], ['G4', 'B4', 'D5', 'E5', 'A4', 'G5']),
                ('E2', ['G3', 'B3', 'E4'], ['E4', 'G4', 'B4', 'D5', 'A4', 'E5']),
                ('C3', ['G3', 'C4', 'E4'], ['C5', 'E5', 'G5', 'D5', 'B4', 'G4']),
                ('D3', ['A3', 'D4', 'F#4'], ['D5', 'F#5', 'A5', 'E5', 'C5', 'A4'])],
        arp_patterns=[[0, 1, 2, 1, 3, 2, 1, 2], [0, 2, 1, 3, 2, 4, 3, 2], [0, 1, 2, 4, 3, 2, 1, 0], [0, 2, 3, 2, 4, 3, 5, 3]],
        pad=[0.28, 0.20, 0.22, 0.20], kick=[0.70, 0.85, 0.75, 0.85], kick_steps=kick_steps_basic, clap=[0.0, 0.40, 0.25, 0.40],
        hat=0.13, shaker=0.06, bass=0.58, bass_steps=[0, 3, 6, 8, 11, 14], strum=[0.0, 0.24, 0.15, 0.24], strum_steps=(2, 6, 10, 14), marimba=[0.42, 0.40, 0.46, 0.40]),
    # D major, I-IV-vi-V: busier, bouncy
    'upbeat_market': dict(bpm=114, seed=23, swing=0.18, rms=0.058,
        chords=[('D3', ['D4', 'F#4', 'A4'], ['D5', 'F#5', 'A5', 'E5', 'B4', 'A4']),
                ('G2', ['G3', 'B3', 'D4'], ['G4', 'B4', 'D5', 'E5', 'A4', 'G5']),
                ('B2', ['B3', 'D4', 'F#4'], ['B4', 'D5', 'F#5', 'E5', 'A4', 'D5']),
                ('A2', ['A3', 'C#4', 'E4'], ['A4', 'C#5', 'E5', 'B4', 'F#4', 'A5'])],
        arp_patterns=[[0, 2, 1, 3, 2, 1, 3, 2], [0, 1, 3, 2, 4, 3, 1, 2], [0, 2, 4, 3, 5, 4, 2, 3], [0, 1, 2, 3, 4, 3, 2, 1]],
        pad=[0.26, 0.18, 0.20, 0.18], kick=[0.75, 0.90, 0.80, 0.90], kick_steps=kick_steps_bounce, clap=[0.0, 0.45, 0.30, 0.45],
        hat=0.15, shaker=0.08, bass=0.60, bass_steps=[0, 3, 7, 8, 10, 14], strum=[0.0, 0.26, 0.16, 0.26], strum_steps=(2, 6, 10, 14), marimba=[0.40, 0.40, 0.44, 0.40]),
    # F major, I-V-vi-IV with a kalimba-like melody
    'upbeat_garden': dict(bpm=104, seed=24, swing=0.08, rms=0.054,
        chords=[('F2', ['F3', 'A3', 'C4'], ['F4', 'A4', 'C5', 'G4', 'D5', 'F5']),
                ('C3', ['G3', 'C4', 'E4'], ['C5', 'E5', 'G5', 'D5', 'A4', 'G4']),
                ('D3', ['A3', 'D4', 'F4'], ['D5', 'F5', 'A5', 'E5', 'C5', 'A4']),
                ('Bb2', ['Bb3', 'D4', 'F4'], ['Bb4', 'D5', 'F5', 'G5', 'C5', 'A4'])],
        arp_patterns=[[0, 1, 2, 3, 2, 1, 4, 2], [0, 2, 1, 3, 4, 2, 5, 3], [0, 1, 3, 2, 4, 3, 5, 4], [0, 2, 1, 2, 3, 1, 2, 0]],
        pad=[0.28, 0.20, 0.24, 0.20], kick=[0.65, 0.80, 0.70, 0.80], kick_steps=kick_steps_basic, clap=[0.0, 0.35, 0.20, 0.35],
        hat=0.12, shaker=0.05, bass=0.56, bass_steps=[0, 6, 8, 11, 14], strum=[0.0, 0.22, 0.14, 0.22], strum_steps=(2, 10, 14), marimba=[0.44, 0.42, 0.48, 0.42]),
    # E major, I-V-vi-IV: bright and light (5th track so that the five videos of a day can all differ)
    'upbeat_bloom': dict(bpm=106, seed=25, swing=0.12, rms=0.054,
        chords=[('E3', ['E4', 'G#4', 'B4'], ['E5', 'G#5', 'B5', 'F#5', 'C#5', 'B4']),
                ('B2', ['B3', 'D#4', 'F#4'], ['B4', 'D#5', 'F#5', 'G#5', 'C#5', 'F#4']),
                ('C#3', ['C#4', 'E4', 'G#4'], ['C#5', 'E5', 'G#5', 'D#5', 'B4', 'G#4']),
                ('A2', ['A3', 'C#4', 'E4'], ['A4', 'C#5', 'E5', 'B4', 'F#4', 'A5'])],
        arp_patterns=[[0, 2, 1, 3, 2, 4, 3, 2], [0, 1, 2, 4, 3, 2, 5, 3], [0, 2, 3, 1, 4, 3, 2, 1], [0, 1, 3, 2, 4, 5, 3, 2]],
        pad=[0.27, 0.19, 0.23, 0.19], kick=[0.68, 0.84, 0.72, 0.84], kick_steps=kick_steps_bounce, clap=[0.0, 0.38, 0.22, 0.38],
        hat=0.13, shaker=0.07, bass=0.58, bass_steps=[0, 3, 8, 11, 14], strum=[0.0, 0.24, 0.15, 0.24], strum_steps=(2, 6, 10, 14), marimba=[0.43, 0.41, 0.47, 0.41]),
}


def main(out_dir, only=None):
    os.makedirs(out_dir, exist_ok=True)
    for name, cfg in TRACKS.items():
        if only and name not in only: continue
        x = build(cfg)
        raw = os.path.join(out_dir, name + '.raw')
        (np.clip(x.T, -1, 1) * 32767).astype('<i2').tofile(raw)
        out = os.path.join(out_dir, name + '.mp3')
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 's16le', '-ar', str(SR), '-ac', '2', '-i', raw,
                        '-c:a', 'libmp3lame', '-b:a', '160k', out], check=True)
        os.remove(raw)
        print(name, 'ok', os.path.getsize(out) // 1024, 'KB', flush=True)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'music', sys.argv[2:] or None)
