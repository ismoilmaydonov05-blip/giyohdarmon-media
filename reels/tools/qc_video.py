#!/usr/bin/env python3
"""Technical QC for a finished Reel + contact sheet.
  python3 qc_video.py VIDEO.mp4 [--sheet SHEET.jpg]
Checks: 1080x1920, h264+aac, 25..90 s, size < 90 MB, no black frames, audio level sane. Prints JSON; exit 1 on failure."""
import sys, os, json, re, subprocess, argparse
from PIL import Image, ImageDraw
ap = argparse.ArgumentParser(); ap.add_argument('video'); ap.add_argument('--sheet'); a = ap.parse_args()
def sh(c): return subprocess.run(c, capture_output=True, text=True)
pr = json.loads(sh(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', a.video]).stdout)
v = next(s for s in pr['streams'] if s['codec_type'] == 'video'); au = [s for s in pr['streams'] if s['codec_type'] == 'audio']
dur = float(pr['format']['duration']); size = int(pr['format']['size'])
res = dict(file=os.path.basename(a.video), width=v['width'], height=v['height'], vcodec=v['codec_name'], acodec=au[0]['codec_name'] if au else None, duration=round(dur, 2), size_mb=round(size / 1e6, 1), problems=[])
P = res['problems']
if (v['width'], v['height']) != (1080, 1920): P.append('resolution is not 1080x1920')
if v['codec_name'] != 'h264': P.append('video codec is not h264')
if not au or au[0]['codec_name'] != 'aac': P.append('no aac audio')
if not (25 <= dur <= 90): P.append(f'duration {dur:.1f}s outside 25..90')
if size > 90e6: P.append('file larger than 90 MB')
bd = sh(['ffmpeg', '-hide_banner', '-i', a.video, '-vf', 'blackdetect=d=0.4:pix_th=0.10', '-an', '-f', 'null', '-']).stderr
blk = re.findall(r'black_start:([\d.]+) black_end:([\d.]+)', bd)
if blk: P.append(f'black frames: {blk}')
vd = sh(['ffmpeg', '-hide_banner', '-i', a.video, '-af', 'volumedetect', '-vn', '-f', 'null', '-']).stderr
m = re.search(r'mean_volume: (-?[\d.]+) dB', vd); mx = re.search(r'max_volume: (-?[\d.]+) dB', vd)
if m: res['mean_volume_db'] = float(m.group(1)); res['max_volume_db'] = float(mx.group(1))
if m and not (-33 <= float(m.group(1)) <= -12): P.append(f'mean volume {m.group(1)} dB looks wrong')
if mx and float(mx.group(1)) > -0.5: P.append('audio peak too hot (clipping risk)')
if a.sheet:
    n = 12; frames = []
    for i in range(n):
        t = dur * (i + 0.5) / n
        out = f'/tmp/_qc_{os.getpid()}_{i}.jpg'
        sh(['ffmpeg', '-y', '-loglevel', 'error', '-ss', f'{t:.2f}', '-i', a.video, '-frames:v', '1', '-vf', 'scale=270:480', out])
        frames.append(out)
    S = Image.new('RGB', (270 * 6, 480 * 2), (20, 20, 20))
    for i, f in enumerate(frames):
        S.paste(Image.open(f), ((i % 6) * 270, (i // 6) * 480)); os.remove(f)
    S.save(a.sheet, quality=82); res['sheet'] = a.sheet
    bj = os.path.splitext(a.video)[0] + '.build.json'          # fast style: one frame per shot, to judge every framing
    if os.path.exists(bj):
        mids = json.load(open(bj)).get('shot_mid_times') or []
        if len(mids) > 1:
            mids = mids[:36]; tiles = []
            for i, t in enumerate(mids):
                out = f'/tmp/_qs_{os.getpid()}_{i}.jpg'
                sh(['ffmpeg', '-y', '-loglevel', 'error', '-ss', f'{min(t, dur - 0.1):.2f}', '-i', a.video, '-frames:v', '1', '-vf', 'scale=216:384', out]); tiles.append(out)
            cols = 8; rows_ = (len(tiles) + cols - 1) // cols
            S2 = Image.new('RGB', (216 * cols, 384 * rows_), (20, 20, 20))
            for i, f in enumerate(tiles):
                S2.paste(Image.open(f), ((i % cols) * 216, (i // cols) * 384)); os.remove(f)
            p2 = os.path.splitext(a.sheet)[0] + '.shots.jpg'; S2.save(p2, quality=80); res['shots_sheet'] = p2
print(json.dumps(res, ensure_ascii=False, indent=1))
sys.exit(1 if P else 0)
