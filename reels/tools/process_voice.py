#!/usr/bin/env python3
"""Post-processes raw TTS wavs (trim lead/tail silence, compress inner pauses, tempo 1.1, 24 kHz).
   python3 process_voice.py RAW_DIR OUT_DIR      (every RAW_DIR/*.wav -> OUT_DIR/<same name>.wav)"""
import sys, os, glob, subprocess
raw, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
AF = ("silenceremove=start_periods=1:start_threshold=-40dB:start_silence=0.05,areverse,"
      "silenceremove=start_periods=1:start_threshold=-40dB:start_silence=0.05,areverse,"
      "silenceremove=stop_periods=-1:stop_duration=0.2:stop_silence=0.11:stop_threshold=-38dB,atempo=1.1")
for f in sorted(glob.glob(os.path.join(raw, '*.wav'))):
    o = os.path.join(out, os.path.basename(f))
    r = subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', f, '-af', AF, '-ar', '24000', o], capture_output=True, text=True)
    if r.returncode: print('FAILED', f, r.stderr[-300:]); sys.exit(1)
    d = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', o], capture_output=True, text=True).stdout.strip()
    print(os.path.basename(o), d)
