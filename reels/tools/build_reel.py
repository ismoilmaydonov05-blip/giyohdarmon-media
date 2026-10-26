#!/usr/bin/env python3
"""Builds one vertical Instagram Reel (1080x1920) from a spec JSON + processed voice wavs.

  python3 build_reel.py SPEC.json --voices VOICE_DIR --out OUT.mp4 [--work WORKDIR] [--keep] [--style fast|classic]

SPEC.json (see ../README.md): id, product_name, final_img, final_lines, delivery, disclaimer, music, rows[{text,kw,img,img2?,crop?}], style?
VOICE_DIR must contain <id>_<i>.wav for every row (processed, see process_voice.py).

STYLES
  fast (default since 2026-10-26, owner's wish "cheerful music, pictures change faster"): the photo sits in a fixed rounded window;
       inside it the picture is re-framed every ~2-3 s (cut at a subtitle change, short "punch-in" settle at every cut, optional
       second photo `img2` of a row is alternated with `img`), rows are joined with 0.16 s slide/wipe transitions, upbeat music.
  classic: one slow zoom per row, 0.25 s fades, calm music (the look of 2026-10-25/26 videos).
The closing voice-over is the fixed pre-recorded clip assets/voice/final_delivery.wav or final_nodelivery.wav.
The WhatsApp number is hard-coded below on purpose: it must never be changed by a spec.
"""
import os, sys, json, math, textwrap, subprocess, argparse, shutil
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

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
STYLE_DEFAULT = 'fast'
FPS = 30
# ---- fast style ----
SHOT_LEN = 2.1        # target length of one framing (s): a row of 4.2 s gets 2 shots, 6.3 s gets 3
SHOT_MIN = 1.2        # no shot is shorter than this
POP = 0.10            # punch-in: every cut starts this much more zoomed-in and settles within ~0.2 s
DRIFT = 0.0005        # slow zoom-in per frame after the settle
MARGIN = 4            # the photo layer is this many px larger than the window on every side (hidden under the frame)
LOOKS = [             # (base zoom, anchor x, anchor y); wide and close shots alternate; anchors stay near the middle so the subject is not cut off
    (1.00, 0.50, 0.50), (1.50, 0.30, 0.35), (1.15, 0.62, 0.60), (1.60, 0.66, 0.32),
    (1.00, 0.50, 0.50), (1.45, 0.36, 0.68), (1.25, 0.64, 0.45), (1.55, 0.45, 0.30),
]
XFADE_FAST = 0.16
TRANSITIONS = ['slideleft', 'slideright', 'wipeleft', 'wiperight']


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


def card_geom(pw, ph):
    """Window (card) for a photo of pw x ph: fit into 940x1130, even sizes and even position (needed for yuv420 overlays)."""
    r = min(940 / pw, 1130 / ph)
    cw = int(pw * r) // 2 * 2; ch = int(ph * r) // 2 * 2
    x = (W - cw) // 2 // 2 * 2; y = (215 + (1130 - ch) // 2) // 2 * 2
    return cw, ch, x, y


def frame_rgba(p, geom, radius=30):
    """Static top layer of the fast style: blurred backdrop of the photo + shadow + handle, with a transparent rounded window."""
    cw, ch, x, y = geom
    bgim = cover(p, W, H).filter(ImageFilter.GaussianBlur(38))
    bgim = Image.blend(bgim, Image.new('RGB', (W, H), (14, 40, 28)), 0.45)
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((x + 10, y + 24, x + cw + 10, y + ch + 24), radius=radius + 4, fill=(0, 0, 0, 150))
    sh = sh.filter(ImageFilter.GaussianBlur(22))
    bgim = Image.alpha_composite(bgim.convert('RGBA'), sh).convert('RGB')
    brand(ImageDraw.Draw(bgim))
    S = 4                                           # supersampled mask = smooth corners
    m = Image.new('L', (cw * S, ch * S), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, cw * S - 1, ch * S - 1), radius=radius * S, fill=255)
    m = m.resize((cw, ch), Image.LANCZOS)
    alpha = Image.new('L', (W, H), 255); alpha.paste(ImageChops.invert(m), (x, y))
    out = bgim.convert('RGBA'); out.putalpha(alpha)
    return out


def chunk_starts(text, dur):
    """Start time (s) of every subtitle chunk of a row - identical to the timing used for the overlays."""
    cs = chunks(text); tot = sum(len(c) for c in cs); t = 0.05; res = []
    for c in cs:
        res.append((t, (dur - 0.15) * len(c) / tot)); t += (dur - 0.15) * len(c) / tot
    return cs, res


def plan_shots(dur, starts):
    """Cut a row into shots of about SHOT_LEN s. Each cut is moved to the nearest subtitle change when one is within 0.45 s,
    so the picture and the subtitle change together. Returns the frame count of every shot."""
    N = max(1, int(round(dur / SHOT_LEN))); cuts = [0.0]
    for k in range(1, N):
        ideal = dur * k / N
        near = min(starts, key=lambda s: abs(s - ideal)) if starts else ideal
        t = near if abs(near - ideal) <= 0.45 else ideal
        if t - cuts[-1] >= SHOT_MIN and dur - t >= SHOT_MIN: cuts.append(t)
    edges = cuts + [dur]; n = int(round(dur * FPS)); fr = [int(round(e * FPS)) for e in edges[:-1]] + [n]
    return [fr[k + 1] - fr[k] for k in range(len(fr) - 1)]


def row_clip_fast(i, row, dur, work, shot_no):
    text = row['text']; key = row.get('kw', [])
    crop = row.get('crop') or CROPS[i % 4]
    p = Image.open(resolve(row['img'])).convert('RGB'); bw, bh = p.size
    p = p.crop((int(crop[0] * bw), int(crop[1] * bh), int(crop[2] * bw), int(crop[3] * bh)))
    cw, ch, x, y = card_geom(p.width, p.height)
    vw, vh = cw + 2 * MARGIN, ch + 2 * MARGIN
    frame_path = os.path.join(work, f'frame{i}.png'); frame_rgba(p, (cw, ch, x, y)).save(frame_path)
    srcs = [p]
    if row.get('img2'): srcs.append(Image.open(resolve(row['img2'])).convert('RGB'))
    zmax = 9.0; paths = []
    for k, s in enumerate(srcs):
        pe = min(s.width, s.height * vw / vh)                     # source width that really ends up in the window
        zmax = min(zmax, max(1.0, 1.6 * pe / vw))                 # never magnify the source more than ~1.6x (checked: 1000 px photos stay acceptable)
        q = os.path.join(work, f'ph{i}_{k}.png'); cover(s, 2 * vw, 2 * vh).save(q); paths.append(q)
    cs, st = chunk_starts(text, dur); frames = plan_shots(dur, [a for a, _ in st]); N = len(frames)
    ins = ''.join(f' -i {q}' for q in paths) + f' -i {frame_path}'
    fi = len(paths)                                               # input index of the frame png
    use = [k % len(paths) for k in range(N)]                      # which photo each shot uses
    flt = ''
    for k in range(len(paths)):
        cnt = use.count(k)
        if cnt == 1: flt += f"[{k}:v]null[p{k}_0];"
        elif cnt > 1: flt += f"[{k}:v]split={cnt}" + ''.join(f'[p{k}_{j}]' for j in range(cnt)) + ';'
    seen = [0] * len(paths); outs = ''
    for s_, n_ in enumerate(frames):
        k = use[s_]; j = seen[k]; seen[k] += 1
        zb, ax, ay = LOOKS[(shot_no + s_) % len(LOOKS)]; zb = min(zb, zmax)
        z = f"min({zmax:.3f},{zb:.3f}+{POP:.3f}*exp(-on/5)+{DRIFT}*on)"
        flt += f"[p{k}_{j}]zoompan=z='{z}':x='(iw-iw/zoom)*{ax}':y='(ih-ih/zoom)*{ay}':d={n_}:s={vw}x{vh}:fps={FPS}[z{s_}];"
        outs += f'[z{s_}]'
    flt += (f"{outs}concat=n={N}:v=1:a=0," if N > 1 else f"{outs}") + f"format=yuv420p,pad={W}:{H}:{x - MARGIN}:{y - MARGIN}:black[ph];"
    flt += f"[ph][{fi}:v]overlay=0:0[b0];"; last = '[b0]'
    for j, c in enumerate(cs):
        a_, d_ = st[j]; sp = os.path.join(work, f's{i}_{j}.png'); sub_png(c, key).save(sp); ins += f' -i {sp}'
        flt += f"{last}[{fi + 1 + j}:v]overlay=0:0:enable='between(t,{a_:.2f},{a_ + d_:.2f})'[b{j + 1}];"; last = f'[b{j + 1}]'
    flt += f"{last}format=yuv420p[out]"; o = os.path.join(work, f'c{i}.mp4')
    run(f'ffmpeg -y -loglevel error{ins} -filter_complex "{flt}" -map "[out]" -r {FPS} -t {dur:.3f} -c:v libx264 -preset veryfast -crf 20 {o}')
    return o, frames


def row_clip_classic(i, row, dur, work):
    text = row['text']; key = row.get('kw', [])
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
    return o


# audio mix per style: (music gain, sidechain threshold, ratio, attack ms, release ms)
MIX = {'classic': (0.30, 0.02, 10, 15, 400), 'fast': (1.15, 0.05, 3, 15, 300)}   # fast: the upbeat track is clearly audible (about 19-20 dB under the voice)
LIMITER = {'classic': 'alimiter=limit=0.86:level=0', 'fast': 'alimiter=limit=0.86:level=0'}  # level=0: do NOT scale the peaks back up to 0 dBFS (QC wants a peak <= -0.5 dB)


def audio_graph(n0, nv, starts, total, style):
    """Filter graph for the sound track. Inputs: [n0:a] = music, [n0+1 .. n0+nv:a] = voice clips (row voices + closing voice).
    Labels: [v] = all voices, [mm] = ducked music, [aa] = final mix."""
    af = ''
    for q in range(nv):
        ms = int((starts[q] + (0.15 if q < nv - 1 else 0.4)) * 1000)
        af += f"[{n0 + 1 + q}:a]aresample=44100,volume=1.5,adelay={ms}|{ms}[a{q}];"
    af += ''.join(f'[a{q}]' for q in range(nv)) + f"amix=inputs={nv}:normalize=0,asplit=2[v][vs];"
    mg, th, ra, at, re_ = MIX[style]
    af += (f"[{n0}:a]atrim=0:{total:.2f},volume={mg},afade=t=in:d=1.5,afade=t=out:st={total - 2.0:.2f}:d=2.0[m];"
           f"[m][vs]sidechaincompress=threshold={th}:ratio={ra}:attack={at}:release={re_}[mm];[mm][v]amix=inputs=2:duration=first:normalize=0,{LIMITER[style]}[aa]")
    return af


def make(spec, voices, out, work, style=None):
    style = style or spec.get('style') or STYLE_DEFAULT
    if style not in ('fast', 'classic'): raise SystemExit('unknown style: ' + str(style))
    fast = style == 'fast'
    k = spec['id']; os.makedirs(work, exist_ok=True); clips = []; durs = []; wavs = []; shot_no = 0; shots_total = 0; shot_frames = []
    for i, row in enumerate(spec['rows']):
        wav = os.path.join(voices, f'{k}_{i}.wav')
        if not os.path.exists(wav): raise SystemExit('missing voice: ' + wav)
        dur = max(2.4, adur(wav) + ROWPAD); durs.append(dur); wavs.append(wav)
        if fast:
            o, fr = row_clip_fast(i, row, dur, work, shot_no); n_shots = len(fr); shot_no += n_shots; shots_total += n_shots; shot_frames.append(fr)
        else:
            o = row_clip_classic(i, row, dur, work); n_shots = 1; shot_frames.append([int(round(dur * FPS))])
        clips.append(o); print(f'  row {i} {dur:.1f}s ({n_shots} shot{"s" if n_shots != 1 else ""})', flush=True)
    delivery = bool(spec.get('delivery', True))
    fw = os.path.join(ASSETS, 'voice', 'final_delivery.wav' if delivery else 'final_nodelivery.wav')
    if not os.path.exists(fw): raise SystemExit('missing final voice: ' + fw)
    fd = adur(fw) + 1.6; fp = os.path.join(work, 'final.png')
    final_png(spec['product_name'], resolve(spec['final_img']), spec.get('final_lines', ['Барои маълумот ва фармоиш', 'ба Вотсап нависед']), delivery, bool(spec.get('disclaimer', True))).save(fp)
    fo = os.path.join(work, 'final.mp4')
    run(f'ffmpeg -y -loglevel error -loop 1 -t {fd} -i {fp} -vf "fps=30,format=yuv420p" -c:v libx264 -preset veryfast -crf 20 {fo}')
    clips.append(fo); durs.append(fd); wavs.append(fw)
    X = XFADE_FAST if fast else 0.25
    inp = ' '.join(f'-i {c}' for c in clips); flt = ''; off = 0; last = '[0:v]'; starts = [0]
    for q in range(1, len(clips)):
        off += durs[q - 1] - X; starts.append(off)
        tr = TRANSITIONS[(q - 1) % len(TRANSITIONS)] if fast else 'fade'
        flt += f"{last}[{q}:v]xfade=transition={tr}:duration={X}:offset={off:.2f}[x{q}];"; last = f'[x{q}]'
    total = off + durs[-1]; flt += f"{last}null[vv]"
    vin = ' '.join(f'-i {w}' for w in wavs); n0 = len(clips)
    af = audio_graph(n0, len(wavs), starts, total, style)
    default_music = 'upbeat_sunrise' if fast else 'calm_dawn'
    music = os.path.join(ASSETS, 'music', spec.get('music', default_music) + '.mp3')
    if not os.path.exists(music):
        cand = sorted(os.listdir(os.path.join(ASSETS, 'music')))
        music = os.path.join(ASSETS, 'music', cand[0])
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    run(f'ffmpeg -y -loglevel error {inp} -stream_loop -1 -i {music} {vin} -filter_complex "{flt};{af}" -map "[vv]" -map "[aa]" '
        f'-c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -c:a aac -b:a 160k -movflags +faststart {out}')
    mids = []                                   # absolute time (s) of the middle of every shot, for the QC "shots sheet"
    for q, fr in enumerate(shot_frames):
        acc = 0
        for n_ in fr:
            mids.append(round(starts[q] + (acc + n_ / 2) / FPS, 2)); acc += n_
    json.dump({'id': k, 'style': style, 'total_seconds': round(total, 2), 'row_seconds': [round(x, 2) for x in durs], 'shots': shots_total,
               'music': os.path.basename(music), 'shot_mid_times': mids}, open(os.path.splitext(out)[0] + '.build.json', 'w'), ensure_ascii=False, indent=1)
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('spec'); ap.add_argument('--voices', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--work'); ap.add_argument('--keep', action='store_true'); ap.add_argument('--style', choices=['fast', 'classic'])
    a = ap.parse_args()
    spec = json.load(open(a.spec, encoding='utf-8'))
    work = a.work or os.path.join('/tmp', 'reel_work_' + spec['id'])
    total = make(spec, a.voices, a.out, work, a.style)
    print(spec['id'], 'OK', round(total, 1), 's ->', a.out, flush=True)
    if not a.keep: shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    main()
