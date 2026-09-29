#!/usr/bin/env python3
"""Build overlays.json: linguistic annotations for every word in space.bin's vocabulary.

Sources (all freely downloadable; fetched into a scratch folder, never committed):
  WordNet 3.1 dict files      https://wordnetcode.princeton.edu/wn3.1.dict.tar.gz
  CMU pronouncing dictionary  https://raw.githubusercontent.com/cmusphinx/cmudict/master/cmudict.dict
  Brysbaert concreteness      Concreteness_ratings_Brysbaert_et_al_BRM.txt
  Warriner valence/arousal    Ratings_Warriner_et_al.csv
  Kuperman age of acquisition Kuperman-BRM-data-2012.csv

Usage:  python3 build_overlays.py <data_dir> [space.bin] [overlays.json]

Output (JSON, arrays aligned to vocabulary index; 0 / -1 mean "no data"):
  pos    bitmask  1 noun · 2 verb · 4 adjective · 8 adverb (WordNet index, via morphy)
  conc   1..255   concreteness 1..5 rescaled;  0 = unrated
  val    1..255   valence 1..9 rescaled;       0 = unrated
  aro    1..255   arousal 1..9 rescaled;       0 = unrated
  aoa    tenths of a year (e.g. 47 = 4.7 years); 0 = unrated
  syl    syllable count from CMU; 0 = unknown
  rhyme  id into rhymeKeys, -1 = unknown. Key = phones from the last stressed vowel.
  lemma  index of the base form if this word is an inflection of another vocab word, else -1
  hyper  {index: [hypernym indexes]} direct hypernyms of the first two noun/verb senses
  anto   [[i, j], ...] antonym pairs (WordNet '!' pointers), i < j
  deriv  [[i, j], ...] derivationally related pairs (WordNet '+' pointers), i < j
"""
import json, os, struct, sys
from collections import defaultdict

data_dir = sys.argv[1]
space_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__), 'space.bin')
out_path = sys.argv[3] if len(sys.argv) > 3 else os.path.join(os.path.dirname(__file__), 'overlays.json')

# ── vocabulary, straight from space.bin so indexes line up exactly ──
with open(space_path, 'rb') as f:
    buf = f.read()
assert buf[:4] == b'MMAP'
dims, vocab, scale, wlen = struct.unpack_from('<HIfI', buf, 5)
words = buf[19:19 + wlen].decode('utf-8').split('\n')
assert len(words) == vocab, (len(words), vocab)
idx = {w: i for i, w in enumerate(words)}
N = vocab
print(f'vocab {N} · dims {dims}')

wn = os.path.join(data_dir, 'wn', 'dict')
POS = {'noun': 1, 'verb': 2, 'adj': 4, 'adv': 8}
POSCHAR = {'n': 'noun', 'v': 'verb', 'a': 'adj', 's': 'adj', 'r': 'adv'}

# ── WordNet index: lemma -> pos -> [synset offsets in sense order] ──
index = {p: {} for p in POS}
for p in POS:
    with open(os.path.join(wn, f'index.{p}'), encoding='utf-8') as f:
        for line in f:
            if line.startswith(' '):
                continue
            parts = line.split()
            lemma, pos, syn_cnt, p_cnt = parts[0], parts[1], int(parts[2]), int(parts[3])
            offs = parts[4 + p_cnt + 2:]
            index[p][lemma] = offs[:syn_cnt]

# exception lists (irregular inflections)
exc = {p: {} for p in POS}
for p in POS:
    with open(os.path.join(wn, f'{p}.exc'), encoding='utf-8') as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 2:
                exc[p].setdefault(parts[0], parts[1])

MORPHY = {
    'noun': [('s', ''), ('ses', 's'), ('xes', 'x'), ('zes', 'z'), ('ches', 'ch'), ('shes', 'sh'), ('men', 'man'), ('ies', 'y')],
    'verb': [('s', ''), ('ies', 'y'), ('es', 'e'), ('es', ''), ('ed', 'e'), ('ed', ''), ('ing', 'e'), ('ing', '')],
    'adj':  [('er', ''), ('est', ''), ('er', 'e'), ('est', 'e')],
    'adv':  [],
}

def morphy(w, p):
    """Return (lemma, is_inflection) for word w under part of speech p, or None."""
    if w in index[p]:
        return w, False
    if w in exc[p] and exc[p][w] in index[p]:
        return exc[p][w], True
    for suf, rep in MORPHY[p]:
        if w.endswith(suf) and len(w) > len(suf) + 1:
            cand = w[:-len(suf)] + rep
            if cand in index[p]:
                return cand, True
    return None

pos = [0] * N
lemma = [-1] * N
senses = {}   # word index -> list of (pos, offset) in sense order across POS
for i, w in enumerate(words):
    if not w.isalpha():
        continue
    best_base = None
    for p in POS:
        m = morphy(w, p)
        if not m:
            continue
        base, infl = m
        pos[i] |= POS[p]
        senses.setdefault(i, []).extend((p, o) for o in index[p][base][:2])
        if infl and best_base is None and base in idx and idx[base] != i:
            best_base = idx[base]
    if best_base is not None:
        lemma[i] = best_base
print('pos tagged', sum(1 for x in pos if x), '· inflections linked', sum(1 for x in lemma if x >= 0))

# ── WordNet data: synset words + pointers ──
syn_words = {}          # (pos, offset) -> [lemma...]
hyper_of = {}           # (pos, offset) -> [(pos, offset)...]
anto = set()
deriv = set()
for p in POS:
    with open(os.path.join(wn, f'data.{p}'), encoding='utf-8') as f:
        for line in f:
            if line.startswith(' '):
                continue
            head = line.split('|', 1)[0].split()
            off, ss_type, w_cnt = head[0], head[2], int(head[3], 16)
            ws = [head[4 + 2 * k] for k in range(w_cnt)]
            key = (p, off)
            syn_words[key] = ws
            p_cnt = int(head[4 + 2 * w_cnt])
            ptrs = head[5 + 2 * w_cnt:]
            for k in range(p_cnt):
                sym, toff, tpos, st = ptrs[4 * k:4 * k + 4]
                tp = POSCHAR.get(tpos)
                if sym == '@' or sym == '@i':
                    hyper_of.setdefault(key, []).append((tp, toff))
                elif sym in ('!', '+') and st != '0000':
                    s, t = int(st[:2], 16), int(st[2:], 16)
                    sw = ws[s - 1] if 0 < s <= len(ws) else None
                    if sw and sw in idx:
                        # target word resolved after all files are read; stash raw
                        (anto if sym == '!' else deriv).add((sw, tp, toff, t))

def resolve_pairs(raw):
    out = set()
    for sw, tp, toff, t in raw:
        tws = syn_words.get((tp, toff))
        if not tws or not (0 < t <= len(tws)):
            continue
        tw = tws[t - 1]
        if tw in idx and tw != sw:
            a, b = sorted((idx[sw], idx[tw]))
            out.add((a, b))
    return sorted(out)

anto_pairs = resolve_pairs(anto)
deriv_pairs = resolve_pairs(deriv)
print('antonym pairs', len(anto_pairs), '· derivation pairs', len(deriv_pairs))

hyper = {}
for i, sl in senses.items():
    seen, hs = set(), []
    for (p, off) in sl:
        if p not in ('noun', 'verb'):
            continue
        for hk in hyper_of.get((p, off), []):
            # one representative in-vocabulary word per hypernym synset; if the
            # direct hypernym is only multiword ("natural_object"), climb once or twice
            frontier, found = [hk], None
            for _ in range(3):
                nxt = []
                for fk in frontier:
                    for hw in syn_words.get(fk, []):
                        if hw in idx and idx[hw] != i and idx[hw] not in seen:
                            found = idx[hw]; break
                    if found is not None: break
                    nxt.extend(hyper_of.get(fk, []))
                if found is not None or not nxt: break
                frontier = nxt
            if found is not None:
                seen.add(found); hs.append(found)
        if len(hs) >= 4:
            break
    if hs:
        hyper[i] = hs[:4]
print('words with hypernyms', len(hyper))

# ── CMU: syllables + rhyme keys ──
syl = [0] * N
rhyme = [-1] * N
rhyme_keys, rk_idx = [], {}
with open(os.path.join(data_dir, 'cmudict.dict'), encoding='utf-8', errors='replace') as f:
    for line in f:
        parts = line.split()
        if not parts:
            continue
        w = parts[0]
        if '(' in w:     # alternate pronunciation; keep the first only
            continue
        if w not in idx:
            continue
        i = idx[w]
        phones = [p for p in parts[1:] if not p.startswith('#')]
        vowels = [k for k, p in enumerate(phones) if p[-1].isdigit()]
        if not vowels:
            continue
        syl[i] = len(vowels)
        stressed = [k for k in vowels if phones[k].endswith('1')] or [k for k in vowels if phones[k].endswith('2')] or vowels
        start = stressed[-1]
        key = ' '.join(p.rstrip('012') for p in phones[start:])
        if key not in rk_idx:
            rk_idx[key] = len(rhyme_keys); rhyme_keys.append(key)
        rhyme[i] = rk_idx[key]
print('pronounced', sum(1 for x in syl if x), '· rhyme keys', len(rhyme_keys))

# ── norms ──
def scale_to_byte(v, lo, hi):
    t = (float(v) - lo) / (hi - lo)
    return max(1, min(255, int(round(1 + t * 254))))

conc = [0] * N
with open(os.path.join(data_dir, 'concreteness.txt'), encoding='utf-8', errors='replace') as f:
    hdr = f.readline().rstrip('\n').split('\t')
    wi, ci = hdr.index('Word'), hdr.index('Conc.M')
    for line in f:
        parts = line.rstrip('\n').split('\t')
        if len(parts) <= ci:
            continue
        w = parts[wi].strip().lower()
        if w in idx:
            try: conc[idx[w]] = scale_to_byte(parts[ci], 1, 5)
            except ValueError: pass

val, aro = [0] * N, [0] * N
import csv
with open(os.path.join(data_dir, 'warriner.csv'), encoding='utf-8', errors='replace') as f:
    r = csv.DictReader(f)
    for row in r:
        w = (row.get('Word') or '').strip().lower()
        if w in idx:
            try:
                val[idx[w]] = scale_to_byte(row['V.Mean.Sum'], 1, 9)
                aro[idx[w]] = scale_to_byte(row['A.Mean.Sum'], 1, 9)
            except (ValueError, KeyError): pass

aoa = [0] * N
with open(os.path.join(data_dir, 'aoa.csv'), encoding='utf-8', errors='replace') as f:
    r = csv.DictReader(f)
    for row in r:
        w = (row.get('Word') or '').strip().lower()
        if w in idx:
            try:
                v = float(row['Rating.Mean'])
                aoa[idx[w]] = max(1, min(255, int(round(v * 10))))
            except (ValueError, KeyError): pass
print('concreteness', sum(1 for x in conc if x), '· valence', sum(1 for x in val if x), '· aoa', sum(1 for x in aoa if x))

out = {
    'v': 1, 'vocab': N,
    'sources': {
        'pos/lemma/hyper/anto/deriv': 'WordNet 3.1 (Princeton)',
        'syl/rhyme': 'CMU Pronouncing Dictionary',
        'conc': 'Brysbaert, Warriner & Kuperman 2014, concreteness ratings for 40k English lemmas',
        'val/aro': 'Warriner, Kuperman & Brysbaert 2013, valence/arousal/dominance norms for 13,915 lemmas',
        'aoa': 'Kuperman, Stadthagen-Gonzalez & Brysbaert 2012, age-of-acquisition ratings for 30k words',
    },
    'check': [[i, words[i]] for i in (0, 7, 100, 999, 5000, N - 1)],   # the loader verifies these against its vocabulary
    'pos': pos, 'conc': conc, 'val': val, 'aro': aro, 'aoa': aoa, 'syl': syl,
    'rhyme': rhyme, 'rhymeKeys': rhyme_keys, 'lemma': lemma,
    'hyper': {str(k): v for k, v in hyper.items()},
    'anto': anto_pairs, 'deriv': deriv_pairs,
}
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(out, f, separators=(',', ':'))
print('wrote', out_path, f'{os.path.getsize(out_path) / 1024:.0f} kB')
