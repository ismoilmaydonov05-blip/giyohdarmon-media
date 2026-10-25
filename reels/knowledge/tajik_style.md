# Tajik script style guide (Cyrillic) for the voice-over and on-screen text

On-screen subtitles = spoken text, word for word. One idea per row, 6-16 words, ends with . ? or !
The voice is a synthetic confident, warm male narrator (Gemini TTS «Charon»).

## Alphabet and spelling
- Tajik Cyrillic only: а б в г ғ д е ё ж з и ӣ й к қ л м н о п р с т у ӯ ф х ҳ ч ҷ ш ъ э ю я.  No Latin letters, no digits.
- Typical letters people forget: ғ қ ӯ ҳ ҷ ӣ. Examples: хӯрок, ҳафта, ҷавидан, қувват, саломатӣ, ӯ, ҳамеша, дастҳо, ғизо.
- Product names are spoken and written in Cyrillic exactly as in products.json: ВормЭксит, Паҳлавон, Зан Зан, ЗенВит, ЗенСлим Про, МеМикс, СекретЭнерчи, БиоФреш, Салиҳа, Шайх Салоҳ.
- WhatsApp is «Вотсап» (voice and text). The number itself is never spoken and never typed in the rows (it appears on the final screen and in the caption as +992097594444).
- Numbers are words: ду, се, панҷ, ҳафт, бист, сӣ, сад ва панҷоҳ, нимкило.
- Ezafe: after a word ending in ӣ the linking vowel is written «и» (маҳсулоти табиии «Гиёҳдармон»), after consonants «и» as well (маҳсулоти гиёҳӣ).

## Sentence patterns that sound natural (copy these shapes)
- Hook question: «Баъд аз хӯрок шикам вазнин мешавад?» / «Тез-тез хаста мешавед ва қувват намерасад?» / «Мехоҳед вазнатонро бо роҳи солим идора кунед?»
- Tip (polite imperative, -ед): «Маслиҳати якум: оҳиста хӯред ва хуб биҷавед.» / «Дастҳоятонро бо собун бишӯед.» / «Шабона ҳафт соат ё бештар хоб кунед.»
- Reason (short): «Ин ба ҳозима ёрӣ мерасонад.» / «Хоби кофӣ қувватро барқарор мекунад.»
- Doctor line: «Агар нишонаҳо муддати дароз давом кунанд, ба духтур муроҷиат кунед.»
- Product intro (last 3 rows only): «<Ном> — маҳсулоти табиии «Гиёҳдармон».» / «Мувофиқи маълумоти истеҳсолкунанда, ... мусоидат мекунад.» / «Барои занон ва мардон мувофиқ аст.»
- Closing speech is a fixed pre-recorded clip (assets/voice/final_*.wav); do not write it.

## Do / don't
- Prefer simple Tajik words over Russian loans when a Tajik word exists (хӯрок, не «пища»; духтур is fine, духи → атр).
- Avoid long compound sentences (> 16 words) and avoid passive chains.
- Do not mix Persian/Dari-only forms or Russian grammar. If unsure of a word, choose a simpler word you are sure about.
- Never write medical promises (see safe_advice.md and products.json -> forbidden).
- Keep exclamation marks to the minimum; calm, helpful tone.

## Row blueprint (9-11 rows)
0 hook question → 1-5 free tips (at least 4 rows, each a concrete habit; a tip may take two rows) → 1 row "see a doctor if long/worrying" (health topics) →
product intro (row N-3) → manufacturer statement (row N-2) → who it is for / one more allowed phrase (row N-1) → fixed closing voice + final screen.
Highlight words (`kw`) = 1-3 key words per row in the exact spelling used in the row (they are shown in gold).
