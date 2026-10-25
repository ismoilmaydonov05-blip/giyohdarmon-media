#!/usr/bin/env python3
"""Collects Speko TTS results that the harness saved as tool-result files and writes them as raw wavs.

Each mcp__Speko__audio_synthesize result is too large for the conversation, so it is stored on disk as
.../tool-results/mcp-Speko-audio_synthesize-<epoch_ms>.txt (JSON with audio_base64, duration_seconds).
Call this script right after a batch of synthesize calls that were issued IN ONE MESSAGE IN ROW ORDER:

  python3 harvest_tts.py --out RAW_DIR --spec SPEC.json [--files path_row0,path_row1,...]      (preferred)
  python3 harvest_tts.py --out RAW_DIR --labels id_0,id_1,id_2 [--texts texts.json]

* files not yet consumed are taken oldest-first and matched to --labels in order (count must match exactly)
* consumed files are remembered in RAW_DIR/.consumed so the next batch starts clean
* --texts: JSON {label: text}; used for a speech-rate sanity check (chars per second must be 8..18)
"""
import argparse, base64, glob, json, os, re, sys

ap = argparse.ArgumentParser()
ap.add_argument('--out', required=True); ap.add_argument('--labels'); ap.add_argument('--texts'); ap.add_argument('--spec', help='SPEC.json: labels = <id>_<row index>, texts = the row texts (replaces --labels/--texts)')
ap.add_argument('--roots', default='/root/.claude/projects,' + os.path.expanduser('~/.claude/projects'))
ap.add_argument('--allow-extra', action='store_true', help='take the NEWEST len(labels) files if more are pending')
ap.add_argument('--files', help='comma-separated explicit result files IN LABEL ORDER (the paths printed in the "saved to ..." message of each synthesize call); skips the glob')
a = ap.parse_args()
spec_texts = {}
if a.spec:
    _sp = json.load(open(a.spec, encoding='utf-8'))
    labels = [f"{_sp['id']}_{i}" for i in range(len(_sp['rows']))]
    spec_texts = {l: r['text'] for l, r in zip(labels, _sp['rows'])}
elif a.labels:
    labels = [x for x in a.labels.split(',') if x]
else:
    ap.error('give --spec or --labels')
os.makedirs(a.out, exist_ok=True)
cons_path = os.path.join(a.out, '.consumed')
consumed = set(open(cons_path).read().split()) if os.path.exists(cons_path) else set()
files = []
for r in dict.fromkeys(a.roots.split(',')):
    files += glob.glob(os.path.join(r, '**', 'tool-results', 'mcp-*Speko*audio_synthesize-*.txt'), recursive=True)
def ts(f):
    m = re.search(r'-(\d+)\.txt$', f); return int(m.group(1)) if m else 0
files = sorted(set(files), key=ts)
pending = [f for f in files if f not in consumed]
if a.files:
    pending = [x for x in a.files.split(',') if x]
    missing = [x for x in pending if not os.path.exists(x)]
    if missing: print('MISSING files:', missing, file=sys.stderr); sys.exit(2)
if len(pending) != len(labels):
    if a.allow_extra and len(pending) > len(labels):
        pending = pending[-len(labels):]
    else:
        print(f'MISMATCH: {len(pending)} pending tts result files vs {len(labels)} labels', file=sys.stderr)
        for f in pending: print('  pending', f, file=sys.stderr)
        sys.exit(2)
texts = spec_texts or (json.load(open(a.texts, encoding='utf-8')) if a.texts else {})
bad = 0
for f, lab in zip(pending, labels):
    d = json.load(open(f))
    wav = base64.b64decode(d['audio_base64'])
    open(os.path.join(a.out, lab + '.wav'), 'wb').write(wav)
    dur = float(d.get('duration_seconds') or 0)
    note = ''
    if lab in texts and dur > 0:
        cps = len(texts[lab]) / dur
        note = f' chars/s={cps:.1f}'
        if not (8 <= cps <= 18): note += '  <-- SUSPICIOUS (clip may be cut or wrong order)'; bad += 1
    print(f'{lab}: {dur:.2f}s {len(wav)//1024}KB{note}')
    open(cons_path, 'a').write(f + '\n')
if bad: print(f'WARNING: {bad} suspicious clips - re-synthesize those rows individually', file=sys.stderr)
