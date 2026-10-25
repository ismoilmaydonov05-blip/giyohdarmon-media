#!/usr/bin/env python3
"""Chooses the 5 products for a target day (deterministic rotation).

  python3 pick_products.py 2026-10-26

Rules: every product has a target gap (days) and an importance weight; the score is  days_since_last_featured / gap * weight.
Never-featured products count as 10 days since last. At most 1 adults-only product (Паҳлавон / Зан Зан), at most 1 perfume, at most 1 Wormexit per day.
Products that already have a video on the target date are skipped (idempotence).  Output: JSON list in slot order.
"""
import sys, os, json, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
WEIGHT = {'wormexit': 1.0, 'pahlavon': 1.25, 'zanzan': 0.9, 'zenvit': 1.0, 'zenslim': 1.0, 'memix': 1.0, 'secret_energy': 1.0, 'biofresh': 0.85, 'saliha': 0.55, 'sheikh_saloh': 0.55}
PERFUMES = {'saliha', 'sheikh_saloh'}
def main():
    day = dt.date.fromisoformat(sys.argv[1])
    prods = json.load(open(os.path.join(ROOT, 'products.json'), encoding='utf-8'))['products']
    log = json.load(open(os.path.join(ROOT, 'state', 'topics_log.json'), encoding='utf-8')) if os.path.exists(os.path.join(ROOT, 'state', 'topics_log.json')) else {'videos': []}
    last = {}; today_have = set()
    for v in log['videos']:
        d = dt.date.fromisoformat(v['date'])
        if d == day: today_have.add(v['product'])
        elif d < day: last[v['product']] = max(last.get(v['product'], d), d)
    cand = []
    for p in prods:
        if p['id'] in today_have: continue
        since = (day - last[p['id']]).days if p['id'] in last else 10
        score = since / p['gap_days'] * WEIGHT.get(p['id'], 1.0)
        cand.append((score, since, p))
    cand.sort(key=lambda x: (-x[0], x[2]['id']))
    chosen = []; adults = 0; perf = 0
    need = 5 - len(today_have)
    for score, since, p in cand:
        if len(chosen) >= need: break
        if p.get('adults_only') and adults >= 1: continue
        if p['id'] in PERFUMES and perf >= 1: continue
        chosen.append((score, since, p)); adults += 1 if p.get('adults_only') else 0; perf += 1 if p['id'] in PERFUMES else 0
    out = [dict(product=p['id'], name=p['name'], days_since_last=since, score=round(score, 2)) for score, since, p in chosen]
    print(json.dumps(dict(date=str(day), already_planned=sorted(today_have), pick=out), ensure_ascii=False, indent=1))
if __name__ == '__main__':
    main()
