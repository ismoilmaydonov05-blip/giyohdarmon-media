#!/usr/bin/env python3
"""Search the licensed stock-photo bank.
  python3 find_images.py --list                       one line per image (id | tags | last used)
  python3 find_images.py walking park --date 2026-10-26   best matches first (unused recently first)
Restricted images (people shown in distress, worm-only, credit-required) are hidden unless --all."""
import sys, os, json, argparse, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
ap = argparse.ArgumentParser(); ap.add_argument('tags', nargs='*'); ap.add_argument('--list', action='store_true'); ap.add_argument('--all', action='store_true')
ap.add_argument('--date', default=str(dt.date.today())); ap.add_argument('--product', default='')
a = ap.parse_args()
idx = json.load(open(os.path.join(ROOT, 'assets', 'stock_index.json'), encoding='utf-8'))['images']
lp = os.path.join(ROOT, 'state', 'topics_log.json')
log = json.load(open(lp, encoding='utf-8')) if os.path.exists(lp) else {'videos': []}
last = {}; count = {}
for v in log['videos']:
    for im in v.get('images', []):
        d = dt.date.fromisoformat(v['date']); last[im] = max(last.get(im, d), d); count[im] = count.get(im, 0) + 1
day = dt.date.fromisoformat(a.date)
rows = []
for it in idx:
    r = it.get('restrictions', [])
    if not a.all:
        if any(x.startswith('avoid_') for x in r): continue
        if 'credit_required' in r: continue
        if 'worm_topics_only' in r and a.product != 'wormexit': continue
    f = it['file']; lu = last.get(f)
    age = (day - lu).days if lu else 999
    score = sum(1 for t in a.tags if t in it['tags'] or any(t in x for x in it['tags']))
    if a.tags and score == 0: continue
    rows.append((-score, -min(age, 999), it, lu, count.get(f, 0)))
rows.sort(key=lambda x: (x[0], x[1], x[2]['id']))
for s, ag, it, lu, c in rows:
    print(f"{it['file']:46s} {','.join(it['tags'])[:70]:70s} last={lu or '-'} n={c}")
print(f'# {len(rows)} images', file=sys.stderr)
