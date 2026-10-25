#!/usr/bin/env python3
"""Builds one vertical Instagram Reel (1080x1920) from a spec JSON + processed voice wavs.

  python3 build_reel.py SPEC.json --voices VOICE_DIR --out OUT.mp4 [--work WORKDIR] [--keep]

SPEC.json (see ../README.md): id, product_name, final_img, final_lines, delivery, disclaimer, music, rows[{text,kw,img,crop?}]
VOICE_DIR must contain <id>_<i>.wav for every row (processed, see process_voice.py).
The closing voice-over is the fixed pre-recorded clip assets/voice/final_delivery.wav or final_nodelivery.wav.
The WhatsApp number is hard-coded below on purpose: it must never be changed by a spec.
"""
import os, sys, json, math, textwrap, subprocess, argparse, shutil
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                  # .../reels
ASSETS = os.path.join(ROOT, 'assets')
W, H = 1080, 1920
GREEN = (20, 67, 46); CREAM = (246, 240, 227); GOLD = (226, 169, 59)
FB = os.path.join(ASSETS, 'fonts', 'Inter-Bold.otf')
FX = os.path.join(ASSETS, 'fonts', 'Inter-ExtraBold.otf')
WHATSAPP = '+992097594444'                    # EXACT format required by the owner - never reformat
HANDLE = '@ismoil.maydonov'
DISCLAIMER = 'Ин маълумот танҳо барои огоҳӣ аст ва маслиҳати духтурро иваз намекунад.'
DELIVERY_LINE = 'Расонидан: тамоми Тоҷикистон ва Русия'
ROWPAD = 0.3
CROPS = [(0, 0, 1, 1), (0.08, 0.06, 0.92, 0.9), (0, 0, 1, 1), (0.04, 0.12, 0.96, 0.96)]


def font(p, s): return ImageFont.truetype(p, s)


def cover(im, w, h):
    r = max(w / im.width, h / im.height)
    im = im.resize((int(im.width * r) + 1, int(im.height * r) + 1), Image.LANCZOS)
    x = (im.width - w) // 2; y = (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def brand(d, light=True):
    f = font(FX, 44); t = HANDLE; x, y = 80, 150
    if light:
        d.text((x + 2, y + 3), t, font=f, fill=(0, 0, 0)); d.text((x, y), t, font=f, fill=(225, 225, 225))
    else:
        d.text((x, y), t, font=f, fill=(110, 110, 110))


def bg_frame(path, crop):
    p = Image.open(path).convert('RGB')
    bw, bh = p.size
    c = (int(crop[0] * bw), int(crop[1] * bh), int(crop[2] * bw), int(crop[3] * bh))
    p = p.crop(c)
    bgim = cover(p, W, H).filter(ImageFilter.GaussianBlur(38))
    ov = Image.new('RGB', (W, H), (14, 40, 28)); bgim = Image.blend(bgim, ov, 0.45)
    r = min(940 / p.width, 1130 / p.height)
    p2 = p.resize((int(p.width * r), int(p.height * r)), Image.LANCZOS)
    x = (W - p2.width) // 2; y = 215 + (1130 - p2.height) // 2
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((x + 10, y + 24, x + p2.width + 10, y + p2.height + 24), radius=34, fill=(0, 0, 0, 150))
    sh = sh.filter(ImageFilter.GaussianBlur(22))
    bgim = Image.alpha_composite(bgim.convert('RGBA'), sh).convert('RGB')
    m = Image.new('L', p2.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, p2.width, p2.height), radius=30, fill=255)
    bgim.paste(p2, (x, y), m)
    brand(ImageDraw.Draw(bgim))
    return bgim


def sub_png(text, key):
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    f = font(FX, 64); words = text.split(); lines = []; cur = ''
    for w_ in words:
        t = (cur + ' ' + w_).strip()
        if d.textlength(t, font=f) > 900 and cur: lines.append(cur); cur = w_
        else: cur = t
    lines.append(cur)
    if len(lines) > 3: raise SystemExit('subtitle chunk needs more than 3 lines: ' + text)
    lh = 90; bh = lh * len(lines) + 52; y0 = 1430
    d.rounded_rectangle((50, y0, W - 50, y0 + bh), radius=40, fill=(14, 50, 34, 232))
    keys = [k.lower().strip('.') for k in key]
    for i, l in enumerate(lines):
        tw = sum(d.textlength(w_ + ' ', font=f) for w_ in l.split()) - d.textlength(' ', font=f); x = W / 2 - tw / 2
        for w_ in l.split():
            clean = w_.strip('.,!?:;«»—-').lower()
            col = GOLD if clean in keys else CREAM
            d.text((x, y0 + 26 + i * lh), w_, font=f, fill=col); x += d.textlength(w_ + ' ', font=f)
    return ov


def chunks(text):
    w = text.split(); n = max(1, math.ceil(len(w) / 4)); size = math.ceil(len(w) / n)
    return [' '.join(w[i:i + size]) for i in range(0, len(w), size)]


def final_png(name, img_path, lines, delivery, disclaimer):
    im = Image.new('RGB', (W, H), CREAM); d = ImageDraw.Draw(im); brand(d, False)
    p = Image.open(img_path).convert('RGB')
    r = min(600 / p.width, 640 / p.height); p = p.resize((int(p.width * r), int(p.height * r)), Image.LANCZOS)
    x = (W - p.width) // 2; y = 215
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((x + 8, y + 18, x + p.width + 8, y + p.height + 18), radius=28, fill=(20, 67, 46, 90))
    sh = sh.filter(ImageFilter.GaussianBlur(16)); im.paste(sh, (0, 0), sh)
    m = Image.new('L', p.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, p.width, p.height), radius=26, fill=255); im.paste(p, (x, y), m)
    yb = y + p.height + 40
    f = font(FX, 84)
    fs = 84
    while d.textlength(name, font=f) > 960 and fs > 40:
        fs -= 4; f = font(FX, fs)
    w = d.textlength(name, font=f); d.text((W / 2 - w / 2, yb), name, font=f, fill=GREEN)
    f2 = font(FB, 48)
    for i, t in enumerate(lines):
        w = d.textlength(t, font=f2); d.text((W / 2 - w / 2, yb + 120 + i * 66), t, font=f2, fill=GREEN)
    by = yb + 290
    d.rounded_rectangle((60, by, 1020, by + 210), radius=105, fill=(37, 211, 102))
    cx, cy = 200, by + 105
    d.ellipse((cx - 70, cy - 70, cx + 70, cy + 70), fill=(255, 255, 255)); d.ellipse((cx - 48, cy - 48, cx + 48, cy + 48), outline=(37, 211, 102), width=11)
    d.polygon([(cx - 48, cy + 48), (cx - 66, cy + 74), (cx - 28, cy + 60)], fill=(37, 211, 102)); d.arc((cx - 22, cy - 24, cx + 28, cy + 26), 20, 110, fill=(37, 211, 102), width=13)
    d.text((300, by + 34), 'Вотсап', font=font(FB, 38), fill=(236, 255, 240)); d.text((300, by + 88), WHATSAPP, font=font(FX, 64), fill=(255, 255, 255))
    y2 = by + 250
    if delivery:
        f3 = font(FB, 38); w = d.textlength(DELIVERY_LINE, font=f3); d.text((W / 2 - w / 2, y2), DELIVERY_LINE, font=f3, fill=GREEN); y2 += 80
    else:
        y2 += 20
    if disclaimer:
        f5 = font(FB, 30)
        for ln in textwrap.wrap(DISCLAIMER, 50):
            w = d.textlength(ln, font=f5); d.text((W / 2 - w / 2, y2), ln, font=f5, fill=GREEN); y2 += 44
    return im


def run(c):
    r = subprocess.run(c, shell=True, capture_output=True, text=True)
    if r.returncode:
        print(r.stderr[-2000:]); sys.exit(1)


def adur(f):
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f], capture_output=True, text=True).stdout)


def resolve(p):
    q = p if os.path.isabs(p) else os.path.join(ASSETS, p)
    if not os.path.exists(q): raise SystemExit('missing image: ' + p)
    return q


def make(spec, voices, out, work):
    k = spec['id']; os.makedirs(work, exist_ok=True); clips = []; durs = []; wavs = []
    for i, row in enumerate(spec['rows']):
        text = row['text']; key = row.get('kw', [])
        wav = os.path.join(voices, f'{k}_{i}.wav')
        if not os.path.exists(wav): raise SystemExit('missing voice: ' + wav)
        dur = max(2.4, adur(wav) + ROWPAD); durs.append(dur); wavs.append(wav)
        base = os.path.join(work, f'bg{i}.png')
        crop = row.get('crop') or CROPS[i % 4]
        bg_frame(resolve(row['img']), crop).save(base)
        cs = chunks(text); tot = sum(len(c) for c in cs); t = 0.05; ins = ''; n = int(dur * 30)
        flt = f"[0:v]scale=2160:-1,zoompan=z='min(1+0.0006*on,1.08)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s={W}x{H}:fps=30[v0];"; last = '[v0]'
        for j, c in enumerate(cs):
            d_ = (dur - 0.15) * len(c) / tot; sp = os.path.join(work, f's{i}_{j}.png'); sub_png(c, key).save(sp); ins += f' -i {sp}'
            flt += f"{last}[{j + 1}:v]overlay=0:0:enable='between(t,{t:.2f},{t + d_:.2f})'[v{j + 1}];"; last = f'[v{j + 1}]'; t += d_
        flt += f"{last}format=yuv420p[out]"; o = os.path.join(work, f'c{i}.mp4')
        run(f'ffmpeg -y -loglevel error -loop 1 -t {dur} -i {base}{ins} -filter_complex "{flt}" -map "[out]" -r 30 -t {dur} -c:v libx264 -preset veryfast -crf 20 {o}')
        clips.append(o); print(f'  row {i} {dur:.1f}s', flush=True)
    delivery = bool(spec.get('delivery', True))
    fw = os.path.join(ASSETS, 'voice', 'final_delivery.wav' if delivery else 'final_nodelivery.wav')
    if not os.path.exists(fw): raise SystemExit('missing final voice: ' + fw)
    fd = adur(fw) + 1.6; fp = os.path.join(work, 'final.png')
    final_png(spec['product_name'], resolve(spec['final_img']), spec.get('final_lines', ['Барои маълумот ва фармоиш', 'ба Вотсап нависед']), delivery, bool(spec.get('disclaimer', True))).save(fp)
    fo = os.path.join(work, 'final.mp4')
    run(f'ffmpeg -y -loglevel error -loop 1 -t {fd} -i {fp} -vf "fps=30,format=yuv420p" -c:v libx264 -preset veryfast -crf 20 {fo}')
    clips.append(fo); durs.append(fd); wavs.append(fw)
    X = 0.25; inp = ' '.join(f'-i {c}' for c in clips); flt = ''; off = 0; last = '[0:v]'; starts = [0]
    for q in range(1, len(clips)):
        off += durs[q - 1] - X; starts.append(off)
        flt += f"{last}[{q}:v]xfade=transition=fade:duration={X}:offset={off:.2f}[x{q}];"; last = f'[x{q}]'
    total = off + durs[-1]; flt += f"{last}null[vv]"
    vin = ' '.join(f'-i {w}' for w in wavs); n0 = len(clips); af = ''
    for q in range(len(wavs)):
        ms = int((starts[q] + (0.15 if q < len(wavs) - 1 else 0.4)) * 1000)
        af += f"[{n0 + 1 + q}:a]aresample=44100,volume=1.5,adelay={ms}|{ms}[a{q}];"
    af += ''.join(f'[a{q}]' for q in range(len(wavs))) + f"amix=inputs={len(wavs)}:normalize=0,asplit=2[v][vs];"
    af += (f"[{n0}:a]atrim=0:{total:.2f},volume=0.30,afade=t=in:d=1.5,afade=t=out:st={total - 2.0:.2f}:d=2.0[m];"
           f"[m][vs]sidechaincompress=threshold=0.02:ratio=10:attack=15:release=400[mm];[mm][v]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.89[aa]")
    music = os.path.join(ASSETS, 'music', spec.get('music', 'calm_dawn') + '.mp3')
    if not os.path.exists(music):
        cand = sorted(os.listdir(os.path.join(ASSETS, 'music')))
        music = os.path.join(ASSETS, 'music', cand[0])
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    run(f'ffmpeg -y -loglevel error {inp} -stream_loop -1 -i {music} {vin} -filter_complex "{flt};{af}" -map "[vv]" -map "[aa]" '
        f'-c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -c:a aac -b:a 160k -movflags +faststart {out}')
    json.dump({'id': k, 'total_seconds': round(total, 2), 'row_seconds': [round(x, 2) for x in durs], 'music': os.path.basename(music)},
              open(os.path.splitext(out)[0] + '.build.json', 'w'), ensure_ascii=False, indent=1)
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('spec'); ap.add_argument('--voices', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--work'); ap.add_argument('--keep', action='store_true')
    a = ap.parse_args()
    spec = json.load(open(a.spec, encoding='utf-8'))
    work = a.work or os.path.join('/tmp', 'reel_work_' + spec['id'])
    total = make(spec, a.voices, a.out, work)
    print(spec['id'], 'OK', round(total, 1), 's ->', a.out, flush=True)
    if not a.keep: shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    main()
