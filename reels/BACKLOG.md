# Backlog (not part of the daily cloud run; the cloud agent does not need to read this)

Work that can only be done when the owner's computer is online (cloud has no access to Pexels, Telegram or Wikimedia).

## 1. Expand the photo bank (highest value)
Why: 63 stock images for ~45 image slots per day => visible repeats within 2–3 days; there are no suitable photos for perfumes, men's wellness, oral care and several herbs, so some rows get a weak picture.

How (Mac bridge + built-in browser / Chrome):
1. Search pexels.com (license: free for commercial use, no attribution needed). Take photos >= 1400 px wide, no brand logos or readable text, no children close-ups, no people in pain/distress (prefer back / partial / distant people or none).
2. Save as `assets/stock/<slug>_px<pexels_id>.jpg` (max 1400 px wide, JPEG quality ~85).
3. Add one entry per photo to `assets/stock_index.json`: id, file, tags (Tajik-neutral English tags like the existing ones), people (none/partial/back/distant/face), width, height, source "Pexels (https://www.pexels.com)", license "Pexels License - free for commercial use, attribution not required", author, pexels_id, url, notes, restrictions.
4. Look at every file (Read) before committing; `python3 tools/find_images.py --list` must show them. `git pull --rebase origin main`, commit, push.

Wanted categories (6–10 photos each):
- perfume / fragrance: glass bottles on a table, spray on a wrist (no face), gift box, flowers + bottle
- men's general wellness: man walking/jogging seen from behind, stretching, drinking water, healthy breakfast, sleeping calmly (no gym-bro or intimate imagery)
- sleep: dark bedroom, bedside lamp, curtains, warm tea at night, book
- oral care: mint leaves, floss, toothbrush in a glass, crisp apple, glass of water
- herbs and kitchen: mint, chamomile, thyme, ginger, lemon, garlic, cinnamon, fennel
- digestion: oatmeal, yogurt, soup, herbal tea, slow eating at a table
- energy / morning: sunrise, morning stretch, fruit, nuts, walk outdoors
- women's wellness (neutral): yoga mat, tea, calm kitchen, walk in a park

Also: more product photos from the Telegram channel (https://t.me/imaydon) for `assets/products/<id>/` if better ones exist.

## 2. Things only the owner can do
- Add the photo credit line to the first Wormexit caption in Instagram (CC BY 2.0): `Фото: SuSanA Secretariat, CC BY 2.0, via Wikimedia Commons`.
- Have a native Tajik speaker listen to a few Reels (the text is machine-written, the voice is synthetic Gemini «Charon») and send corrections; corrections go into `knowledge/tajik_style.md`.
- Keep Metricool's Instagram connection (Meta OAuth) valid; if it expires, publishing stops (the evening report will show FAILED / error text).
