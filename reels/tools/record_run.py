#!/usr/bin/env python3
"""Keeps state/topics_log.json (what was made, for non-repetition and product rotation).

  record_run.py add    --spec SPEC.json --slot 2026-10-26T08:00 --metricool-id N --uuid U [--status SCHEDULED]
  record_run.py status --id 2026-10-26_1 --status PUBLISHED [--url URL] [--metricool-id N] [--note TEXT]
  record_run.py show   [--date 2026-10-26]
"""
import sys, os, json, argparse
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
P = os.path.join(ROOT, 'state', 'topics_log.json')
def load():
    return json.load(open(P, encoding='utf-8')) if os.path.exists(P) else {'videos': []}
def save(d):
    os.makedirs(os.path.dirname(P), exist_ok=True)
    json.dump(d, open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest='cmd', required=True)
a1 = sp.add_parser('add'); a1.add_argument('--spec', required=True); a1.add_argument('--slot', required=True); a1.add_argument('--metricool-id'); a1.add_argument('--uuid'); a1.add_argument('--status', default='SCHEDULED')
a2 = sp.add_parser('status'); a2.add_argument('--id', required=True); a2.add_argument('--status', required=True); a2.add_argument('--url'); a2.add_argument('--metricool-id'); a2.add_argument('--note')
a3 = sp.add_parser('show'); a3.add_argument('--date')
a = ap.parse_args(); d = load()
if a.cmd == 'add':
    s = json.load(open(a.spec, encoding='utf-8'))
    d['videos'] = [v for v in d['videos'] if v['id'] != s['id']]
    d['videos'].append(dict(id=s['id'], date=s['date'] if 'date' in s else s['id'].split('_')[0], slot=a.slot, product=s['product'], topic=s['topic'], music=s['music'],
        rows=[r['text'] for r in s['rows']], images=[x for r in s['rows'] for x in (r['img'], r.get('img2')) if x and not x.startswith('products/')], metricool_id=a.metricool_id, uuid=a.uuid, status=a.status, url=None))
elif a.cmd == 'status':
    v = next(v for v in d['videos'] if v['id'] == a.id); v['status'] = a.status
    if a.url: v['url'] = a.url
    if a.metricool_id: v['metricool_id'] = a.metricool_id
    if a.note: v['note'] = a.note
else:
    for v in d['videos']:
        if not a.date or v['date'] == a.date: print(v['id'], v['slot'], v['product'], v['status'], v.get('url') or '', '|', v['topic'])
    sys.exit(0)
save(d); print('saved', len(d['videos']), 'videos')
