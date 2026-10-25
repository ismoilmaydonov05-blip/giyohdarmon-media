#!/usr/bin/env python3
"""Policy/format linter for a Reel spec JSON and its caption.

  python3 lint_spec.py SPEC.json [--caption CAPTION.txt] [--history ../state/topics_log.json]

Exit code 1 = at least one ERROR (must be fixed before building/publishing). Warnings should be read.
This catches policy and format problems only. It can NOT prove that the Tajik is grammatical - re-read every line yourself.
"""
import sys, os, re, json, argparse, difflib

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
WA = '+992097594444'
ALLOWED = set('абвгдеёжзийклмнопрстуфхцчшщъыьэюяғӣқӯҳҷАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯҒӢҚӮҲҶ' + ' .,!?:;«»—–-()" ')
FORBID_ERR = [  # (regex, why)
    (r'кафолат', 'guarantee wording'),
    (r'табобат\s+(мекунад|мекард|мешавад)|табобати\s+(кирм|бемор|гастрит|бехобӣ|депрессия)', 'treatment claim'),
    (r'шифо\s*(медиҳад|мебахшад|ёфт)', 'cure claim'),
    (r'(нест|аз\s+байн)\s+(мекунад|мебарад|менамояд)', 'eliminates claim'),
    (r'решакан', 'eradication claim'),
    (r'сад\s+фоиз|сад\s+дар\s+сад', '100 percent claim'),
    (r'(зуд|фавран)\s+(кам\s+мекунад|мебарад|нест)', 'fast-result claim'),
    (r'нарх|сомонӣ|рубл|доллар|тахфиф|арзон', 'price wording (prices are never shown)'),
    (r'миллиграмм|\bмг\b|қошуқ|қатра|ҳаб\b|капсул|табл[её]тка', 'dosage-like wording (never invent dosage)'),
    (r'(рӯзе|дар\s+рӯз)\s+(як|ду|се|чор|панҷ)\s+маротиба\s+(бинӯшед|қабул|истифода)', 'dosage instruction'),
    (r'простата|шаҳвонӣ|ҷинсӣ|ҳамхобагӣ|давомнокии', 'intimate/sexual wording (keep men\'s-health videos neutral)'),
    (r'депрессия\s+(табобат|шифо)|изтироб\s+(табобат|шифо)', 'mental-health treatment claim'),
]
FORBID_WARN = [
    (r'ҳатман|албатта', 'absolute wording - make sure it is advice, not a promise'),
    (r'кӯдак', 'children mentioned - no dosage/usage for children, no product claims'),
    (r'ташхис', 'diagnosis wording - must say symptoms do not confirm anything'),
    (r'100', 'digits'),
]

def words(s): return re.findall(r"[\wғӣқӯҳҷҒӢҚӮҲҶ]+", s, flags=re.U)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('spec'); ap.add_argument('--caption'); ap.add_argument('--history')
    a = ap.parse_args()
    spec = json.load(open(a.spec, encoding='utf-8'))
    prods = {p['id']: p for p in json.load(open(os.path.join(ROOT, 'products.json'), encoding='utf-8'))['products']}
    stock = {i['file']: i for i in json.load(open(os.path.join(ROOT, 'assets', 'stock_index.json'), encoding='utf-8'))['images']}
    err = []; warn = []
    E = lambda m: err.append(m); Wn = lambda m: warn.append(m)

    for k in ('id', 'product', 'product_name', 'final_img', 'music', 'rows', 'topic'):
        if k not in spec: E(f'missing key: {k}')
    if err: print('\n'.join('ERROR ' + e for e in err)); sys.exit(1)
    if not re.match(r'^\d{4}-\d{2}-\d{2}_\d$', spec['id']): E('id must look like 2026-10-26_1')
    p = prods.get(spec['product'])
    if not p: E('unknown product ' + spec['product']); print('\n'.join('ERROR ' + e for e in err)); sys.exit(1)
    if spec['product_name'] != p['name']: E(f"product_name must be exactly '{p['name']}'")
    if spec['final_img'] != p['photo'] and spec['final_img'] != p.get('photo_alt'): E('final_img must be the product photo from products.json')
    if bool(spec.get('delivery', True)) != bool(p['delivery']): E(f"delivery must be {p['delivery']} for this product")
    if bool(spec.get('disclaimer', True)) != bool(p['disclaimer']): E(f"disclaimer must be {p['disclaimer']} for this product")
    if not os.path.exists(os.path.join(ROOT, 'assets', 'music', spec['music'] + '.mp3')): E('unknown music ' + spec['music'])
    rows = spec['rows']
    if not (8 <= len(rows) <= 13): E(f'rows must be 8..13, got {len(rows)}')
    name_core = re.sub(r'\s+', '', p['name']).lower()
    first_prod_row = None
    used_imgs = []
    for i, r in enumerate(rows):
        t = r.get('text', '')
        tag = f'row {i}'
        if not t.strip(): E(tag + ': empty text'); continue
        bad = sorted({c for c in t if c not in ALLOWED})
        if bad: E(f"{tag}: characters not allowed {bad} (Tajik Cyrillic only; numbers must be written in words; product names in Cyrillic)")
        if re.search(r'\d', t): E(tag + ': digits in text - write numbers in words')
        if len(words(t)) > 22: E(f'{tag}: too long ({len(words(t))} words, max 22) - split the row')
        if len(t) > 150: E(f'{tag}: too long ({len(t)} chars, max 150)')
        for rx, why in FORBID_ERR:
            if re.search(rx, t, re.I): E(f'{tag}: {why}: "{t}"')
        for rx, why in FORBID_WARN:
            if re.search(rx, t, re.I): Wn(f'{tag}: {why}')
        img = r.get('img')
        if not img: E(tag + ': missing img')
        else:
            used_imgs.append(img)
            if not os.path.exists(os.path.join(ROOT, 'assets', img)): E(f'{tag}: image file not found: {img}')
            meta = stock.get(img)
            if meta:
                if meta.get('restrictions') and any(x.startswith('avoid_') for x in meta['restrictions']): E(f'{tag}: image {img} is restricted ({meta["restrictions"]})')
                if 'worm_topics_only' in meta.get('restrictions', []) and spec['product'] != 'wormexit': E(f'{tag}: image {img} is for intestinal-worm topics only')
                if 'credit_required' in meta.get('restrictions', []): Wn(f'{tag}: image {img} needs a credit line in the caption: {meta["license"]}')
            elif not img.startswith('products/'): Wn(f'{tag}: image {img} is not in stock_index.json')
            if img.startswith('products/') and i < len(rows) - 3: E(f'{tag}: product photo used before the product section')
        for kw in r.get('kw', []):
            if kw.lower().strip('.:,') not in [w.lower() for w in re.split(r'\s+', re.sub(r'[.,!?:;«»—-]', ' ', t)) if w]: Wn(f'{tag}: highlight word "{kw}" not found in text')
        if name_core in re.sub(r'\s+', '', t).lower() and first_prod_row is None: first_prod_row = i
    non_prod = [x for x in used_imgs if not x.startswith('products/')]
    if len(non_prod) != len(set(non_prod)): E('the same stock image is used twice inside one video')
    if first_prod_row is None: E('product name never appears in the rows')
    elif first_prod_row < len(rows) - 3: E(f'product is introduced in row {first_prod_row}; it may only appear in the LAST 3 rows (free advice first)')
    if '?' not in rows[0]['text']: Wn('first row is not a question - open with a question or a common concern')
    if not any(re.search(r'маслиҳат|ёрдам|кӯшиш|бояд|кунед|шавед|доред|нигоҳ|хӯред|нӯшед|бишӯед|шӯед', r['text']) for r in rows[1:-3]): Wn('no practical advice found in the free-advice rows')
    free = len(rows) - (len(rows) - first_prod_row if first_prod_row is not None else 3)
    if free < 4: E(f'only {free} free-advice rows before the product; need at least 4')
    if p['category'].startswith('hygiene') and not any('тасдиқ намекунанд' in r['text'] for r in rows): E('wormexit videos must say that symptoms alone do not confirm an infection ("...тасдиқ намекунанд")')
    if p['disclaimer'] and not any(re.search(r'духтур|мутахассис', r['text']) for r in rows): Wn('health video without any "see a doctor" line')
    # sentence quality heuristics
    for i, r in enumerate(rows):
        if re.search(r'\s{2,}', r['text']): Wn(f'row {i}: double spaces')
        if r['text'].strip()[-1] not in '.?!': Wn(f'row {i}: should end with . ? or !')
    # history similarity
    if a.history and os.path.exists(a.history):
        hist = json.load(open(a.history, encoding='utf-8'))
        prev = [(h['id'], x) for h in hist.get('videos', []) for x in h.get('rows', [])]
        for i, r in enumerate(rows[:-3]):
            for hid, x in prev:
                if difflib.SequenceMatcher(None, r['text'], x).ratio() > 0.85: Wn(f'row {i} is almost identical to a row of {hid}: "{x}"'); break
        for h in hist.get('videos', []):
            if h.get('product') == spec['product'] and difflib.SequenceMatcher(None, spec['topic'], h.get('topic', '')).ratio() > 0.8: E(f"topic repeats {h['id']}: {h.get('topic')}")
    # caption
    if a.caption:
        cap = open(a.caption, encoding='utf-8').read()
        nums = re.findall(r'\+?\d[\d\s\-()]{6,}\d', cap)
        if cap.count(WA) != 1: E(f'caption must contain {WA} exactly once (found {cap.count(WA)})')
        for n in nums:
            if n.strip() != WA: E(f'caption contains another/reformatted number: "{n.strip()}"')
        if p['disclaimer'] and 'Ин маълумот танҳо барои огоҳӣ аст ва маслиҳати духтурро иваз намекунад.' not in cap: E('caption lacks the standard disclaimer')
        for rx, why in FORBID_ERR:
            if re.search(rx, cap, re.I): E(f'caption: {why}')
        if p['delivery'] and 'Мо ба тамоми Тоҷикистон ва Русия маҳсулот мерасонем.' not in cap: E('caption lacks the delivery sentence')
        if not p['delivery'] and 'мерасонем' in cap: E('delivery must not be mentioned for this product')
        if '#' not in cap: Wn('no hashtags in caption')
        if p.get('adults_only') and 'калонсол' not in cap: Wn('adults-only product: caption should say it is for adults')
        if len(cap) > 2150: E('caption too long for Instagram (2200 chars)')
        for img in dict.fromkeys(used_imgs):  # credit-required images (CC BY): the credit line must be in the caption
            meta = stock.get(img) or {}
            if 'credit_required' in meta.get('restrictions', []):
                m = re.search(r'"([^"]+)"', meta.get('license', ''))
                credit = m.group(1) if m else (meta.get('author') or '')
                if credit and credit not in cap: E(f'caption must contain the photo credit line: "Фото: {credit}" (image {img})')
    print(f"spec {spec['id']} ({p['name']}): {len(err)} errors, {len(warn)} warnings")
    for w in warn: print('WARN  ', w)
    for e in err: print('ERROR ', e)
    sys.exit(1 if err else 0)

if __name__ == '__main__':
    main()
