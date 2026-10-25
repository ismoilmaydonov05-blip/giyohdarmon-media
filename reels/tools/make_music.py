#!/usr/bin/env python3
"""Synthesizes ORIGINAL quiet ambient background tracks (no samples, no third-party music).
Every track is generated from scratch with additive synthesis, so there is no copyright/licence issue.
Usage: python3 make_music.py <out_dir>        -> writes calm_dawn.mp3, calm_meadow.mp3, calm_evening.mp3, calm_water.mp3
"""
import sys, os, subprocess, numpy as np
from scipy.signal import fftconvolve, butter, sosfilt

SR = 44100
DUR = 96.0

def hz(m):  # midi note -> Hz
    return 440.0 * 2 ** ((m - 69) / 12.0)

NOTE = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}

def midi(name):  # e.g. 'A3', 'Bb3', 'F#4'
    n = NOTE[name[0]]; i = 1
    while name[i] in '#b':
        n += 1 if name[i] == '#' else -1; i += 1
    return 12 * (int(name[i:]) + 1) + n

def tone(f, t, harm=6, detune=(0.0, 0.0035)):
    out = np.zeros_like(t)
    for dt in detune:
        ff = f * (1 + dt)
        for h in range(1, harm + 1):
            out += np.sin(2 * np.pi * ff * h * t + h) / (h ** 1.7)
    return out

def adsr(n, a, r):
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    na = min(na, n // 2); nr = min(nr, n // 2)
    e[:na] = np.linspace(0, 1, na) ** 1.5
    e[n - nr:] = np.linspace(1, 0, nr) ** 1.5
    return e

def pad_chord(notes, dur, tail=3.0):
    n = int((dur + tail) * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for k, m in enumerate(notes):
        trem = 1 + 0.12 * np.sin(2 * np.pi * (0.11 + 0.03 * k) * t + k)
        sig += tone(hz(m), t) * trem * (1.0 if k < 3 else 0.7)
    sig *= adsr(n, 2.6, tail + 1.0)
    return sig / max(1, len(notes))

def pluck(m, dur=2.4):
    n = int(dur * SR); t = np.arange(n) / SR
    f = hz(m)
    s = (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) + 0.12 * np.sin(2 * np.pi * 3 * f * t))
    s *= np.exp(-t * 2.6) * np.minimum(1, t * 120)
    return s

def reverb(x, rt=2.8, mix=0.38):
    n = int(rt * SR)
    rng = np.random.default_rng(7)
    ir = rng.standard_normal((2, n)) * np.exp(-np.arange(n) / SR * (6.9 / rt))
    ir[:, :int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))
    out = np.stack([fftconvolve(x[0], ir[0])[:x.shape[1]], fftconvolve(x[1], ir[1])[:x.shape[1]]])
    out /= (np.abs(out).max() + 1e-9) / (np.abs(x).max() + 1e-9)
    return x * (1 - mix) + out * mix

def make_track(chords, bpm, arp_pattern, seed, brightness=1.0):
    n = int(DUR * SR)
    L = np.zeros(n); R = np.zeros(n)
    bar = 4 * 60.0 / bpm * 2          # two bars per chord
    ci = 0; pos = 0.0
    while pos < DUR:
        root, notes, arp = chords[ci % len(chords)]
        seg = pad_chord([midi(x) for x in notes], bar)
        i0 = int(pos * SR); i1 = min(n, i0 + len(seg))
        L[i0:i1] += seg[:i1 - i0]; R[i0:i1] += seg[:i1 - i0] * 0.97
        # soft bass
        b = pad_chord([midi(root) - 12], bar, tail=2.0) * 0.9
        j1 = min(n, i0 + len(b)); L[i0:j1] += b[:j1 - i0] * 0.8; R[i0:j1] += b[:j1 - i0] * 0.8
        # arpeggio plucks
        step = 60.0 / bpm / 2
        k = 0; tt = pos + 1.2
        while tt < pos + bar - 0.4:
            m = midi(arp[arp_pattern[k % len(arp_pattern)] % len(arp)])
            p = pluck(m) * 0.34 * brightness
            a = int(tt * SR)
            if a >= n: break
            e = min(n, a + len(p))
            pan = 0.5 + 0.35 * np.sin(k * 1.7 + seed)
            L[a:e] += p[:e - a] * (1 - pan); R[a:e] += p[:e - a] * pan
            k += 1; tt += step
        pos += bar; ci += 1
    x = np.stack([L, R])
    # gentle low-pass (soft/warm) and high-pass (remove rumble)
    sos = butter(2, 3800 * brightness, 'low', fs=SR, output='sos'); x = sosfilt(sos, x, axis=1)
    sos = butter(2, 55, 'high', fs=SR, output='sos'); x = sosfilt(sos, x, axis=1)
    x = reverb(x)
    # fade in/out, normalise like the voice-over background level used in the videos (rms ~0.03)
    fade = int(2.5 * SR)
    x[:, :fade] *= np.linspace(0, 1, fade); x[:, -fade:] *= np.linspace(1, 0, fade)
    x *= 0.030 / (np.sqrt((x ** 2).mean()) + 1e-9)
    peak = np.abs(x).max()
    if peak > 0.3: x *= 0.3 / peak
    return x

TRACKS = {
    'calm_dawn':    dict(bpm=66, seed=1, bright=1.0, pat=[0, 2, 1, 3, 2, 1],
        chords=[('A2', ['A3', 'E4', 'B4', 'C5'], ['A4', 'C5', 'E5', 'B4']),
                ('F2', ['F3', 'C4', 'G4', 'A4'], ['F4', 'A4', 'C5', 'G4']),
                ('C3', ['C4', 'G4', 'B4', 'E5'], ['E4', 'G4', 'B4', 'C5']),
                ('G2', ['G3', 'D4', 'E4', 'B4'], ['G4', 'B4', 'D5', 'E5'])]),
    'calm_meadow':  dict(bpm=72, seed=2, bright=1.15, pat=[0, 1, 2, 1, 3, 2],
        chords=[('C3', ['C4', 'G4', 'B4', 'E5'], ['E4', 'G4', 'C5', 'D5']),
                ('A2', ['A3', 'E4', 'G4', 'C5'], ['A4', 'C5', 'E5', 'G4']),
                ('F2', ['F3', 'C4', 'A4', 'E5'], ['F4', 'A4', 'C5', 'E5']),
                ('G2', ['G3', 'D4', 'B4', 'F4'], ['G4', 'B4', 'D5', 'F5'])]),
    'calm_evening': dict(bpm=60, seed=3, bright=0.9, pat=[0, 1, 3, 2, 1, 2],
        chords=[('D2', ['D3', 'A3', 'C4', 'F4'], ['D4', 'F4', 'A4', 'C5']),
                ('Bb1', ['Bb2', 'F3', 'A3', 'D4'], ['Bb3', 'D4', 'F4', 'A4']),
                ('F2', ['F3', 'C4', 'A4', 'E4'], ['F4', 'A4', 'C5', 'E5']),
                ('C3', ['C4', 'G4', 'E4', 'B4'], ['C5', 'E5', 'G4', 'B4'])]),
    'calm_water':   dict(bpm=68, seed=4, bright=1.05, pat=[0, 2, 3, 1, 2, 0],
        chords=[('E2', ['E3', 'B3', 'D4', 'G4'], ['E4', 'G4', 'B4', 'D5']),
                ('C3', ['C4', 'G4', 'B4', 'E5'], ['E4', 'G4', 'B4', 'C5']),
                ('G2', ['G3', 'D4', 'B4', 'A4'], ['G4', 'B4', 'D5', 'A4']),
                ('D3', ['D4', 'A4', 'C5', 'F#4'], ['F#4', 'A4', 'C5', 'D5'])]),
}

def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for name, c in TRACKS.items():
        x = make_track(c['chords'], c['bpm'], c['pat'], c['seed'], c['bright'])
        pcm = (np.clip(x.T, -1, 1) * 32767).astype('<i2')
        raw = os.path.join(out_dir, name + '.raw')
        pcm.tofile(raw)
        out = os.path.join(out_dir, name + '.mp3')
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 's16le', '-ar', str(SR), '-ac', '2', '-i', raw,
                        '-c:a', 'libmp3lame', '-b:a', '160k', out], check=True)
        os.remove(raw)
        print(name, 'ok', os.path.getsize(out) // 1024, 'KB')

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'music')
