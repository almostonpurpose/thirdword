# Meaning Map — handover

A semantic-space navigation tool. You stand on a word, name a few "fields" you want to reach,
and the tool finds the shortest chain of meaning to each one, then shows whether each hop
actually moves you closer. It began as a tool for naming a website and has been rebuilt around
the mechanic that turned out to be the interesting part: triangulation between several meaning
fields at once.

Read this before touching the code. It records the decisions so they don't have to be
rediscovered.

## Files in this folder

- `meaning_map_v8.html` — the whole tool. Vanilla JS, no build step, no runtime framework.
- `space.bin` — the semantic space (one self-describing binary; see format below).
- `HANDOVER.md` — this file.

To run: serve the folder (`python3 -m http.server` then open the page) so the tool auto-fetches
`space.bin` from alongside itself. Opening the bare file by double-click works too, but the first
open needs you to drop `space.bin` onto the panel once — browsers block `file://` fetches. After
either route the space is cached in the browser (IndexedDB) and loads on its own thereafter,
offline included.

## What it does, mechanically

The core idea is bidirectional search (the user arrived at it independently; it is worth keeping
that framing). Rather than expanding one frontier from the current word and watching it fan out,
the tool grows a cloud from the current word *and* from each anchor word, and lets them meet.

1. **Cloud** — a word's neighbourhood is its k nearest neighbours by cosine similarity
   (`nn`, k≈36). `expand` runs this two hops to build a small cloud.
2. **Meeting node** — for current word C and anchor A, intersect the two clouds. The first naive
   overlap is junk (high-frequency hub words sit in everybody's neighbourhood), so candidates are
   scored and the best non-hub, genuinely-between word is chosen (`bridges`).
3. **Skeleton** — walk the kNN graph greedily from C to the chosen bridge, then bridge to A
   (`walk`). The two legs joined are the drawable path: C → … → bridge → … → A.
4. **Proximity gauge** — each anchor row shows the raw cosine similarity from the current word to
   that anchor, as a percentage. Step onto a word along a chain and the gauge moves. It measures
   real distance, so it cannot assert progress that isn't there. This is the signature element.
5. **Sense-split signal** — if a bridge word's own neighbourhood is incoherent (average pairwise
   cosine among its top neighbours below a threshold), the word is likely polysemous and the route
   may not mean what it reads. The tool flags this rather than hiding it.

### Scoring (the load-bearing formulas)

- Specificity / hub penalty, per word at frequency-rank `i` of `N`:
  `spec = clip(log1p(i)/log1p(N), 0.15, 1.0)`. Rare words score near 1, hubs near 0.15.
- Bridge score for candidate `n`, with `cs` = cosine(C,n), `as` = cosine(A,n):
  `min(cs,as) * (0.5 + 0.5*(1 - |cs-as|)) * spec[n]`.
  The `min` rewards being close to both ends; `1-|cs-as|` rewards sitting *between* them rather
  than in the anchor's lap; `spec` keeps hubs out.
- Greedy walk step toward target `b`: pick the neighbour maximising `cosine(j,b) * (0.6 + 0.4*spec[j])`.
- Sense-split: average pairwise cosine among the top 12 neighbours `< 0.34` → flag.

Both the hub penalty and the balance term are necessary, not decorative. Without the penalty the
first overlap collapses onto words like "thing"/"system"/"work"; without the balance term the
bridges pile up in the anchor's own backyard. This was checked against real data, not assumed.

## The space file format (`space.bin`)

One self-describing file. A "semantic space" is one such file, which is the unit you swap to change
vocabulary, dimensionality, or language.

```
offset  type        field
0       4 bytes     magic 'MMAP'
4       uint8       version (=1)
5       uint16 LE   dims
7       uint32 LE   vocab
11      float32 LE  scale          (int8 → float dequant factor)
15      uint32 LE   wlen           (byte length of the words block)
19      bytes[wlen] words          (UTF-8, newline-joined, vocab entries)
19+wlen int8[vocab*dims]  vectors  (row-major)
```

Vectors are L2-normalised, then quantised to int8 with a single global `scale`. Dequant in the
loader: `v = byte * scale / 127`, then re-normalise each row (quantisation perturbs the norm
slightly). Because rows are normalised, cosine similarity is a plain dot product.

The current space: GloVe 6B, 50 dimensions, the 40,000 most-frequent words (GloVe is
frequency-ordered, so "first N rows" = "N commonest words", which is also what `spec` relies on).
~2.3 MB.

### Regenerating or making a new space

`pack.py` (kept with the build notes, not shipped in the tool folder) builds `space.bin` from a
raw GloVe text file: parse the first N rows, L2-normalise, int8-quantise with one global scale,
write the header + words + vectors. To make a denser or larger or different-language space, point
the same packer at a different vector source and ship the resulting `space.bin`. No tool code
changes — the loader reads dims/vocab/scale from the header.

## Loading and persistence

Load order, in `init`:
1. IndexedDB cache (`meaningmap` DB, `space` store, key `active`) — the remembered space.
2. Bundled sibling — `fetch('./space.bin')`. Works when served; blocked under `file://`.
3. File picker / drop zone — manual first load.

Whatever loads (fetched or dropped) is written to the cache, so first open is the only open. The
"space" settings panel shows the current space (name, word count, dimensions), lets you drop in a
different `space.bin` (which becomes the new cached default), and offers "forget & reload bundled".

`localStorage`/`sessionStorage` are deliberately not used — IndexedDB holds the binary and is the
right store for it.

## Rendering

- Hand-rolled force-directed layout on a small subgraph (current word + skeleton paths + local
  neighbours + small lit clusters around each anchor). Naive O(n²) repulsion is fine at this size.
  No d3, no external libraries at runtime.
- Current word pinned at centre; anchors pinned on a ring; everything else settles under the force.
- Skeleton edges are drawn in the anchor's colour and pull harder (shorter rest length) so the
  chain lays out between current and anchor.
- Pan (drag background), zoom (wheel), click any word to step onto it, breadcrumb trail of recent
  positions.

### Design tokens (matches the "general amr" system, not the dark industrial one)

- Background: warm linen `#f8f6f1` / `#f1ede4` / `#e8e2d6`; hairline rules `#d9d2c4`.
- Ink: `#1a1713` / `#6f665a` / `#a89e8e`.
- Accents, one per anchor field: plum `#8f84b8`, oxide `#b58f82`, sage `#9aa890`,
  bluegrey `#93a3b5`, amber `#cda867`, rose `#d4a0a8`.
- Type: Fraunces (display), Inter (body), JetBrains Mono (data/labels). Loaded from Google Fonts;
  offline they fall back to system faces — the one network dependency left, and a soft one.

## Validated findings (real data, Python + JS cross-checked)

The JS engine produces the same bridges as the reference Python. Examples:

- `shadow → planet → planets → earth → ocean` (astronomical bridge)
- `threshold → absolute → utter → disbelief → silence` (moral-abstraction register)
- `storm → thunderstorm → bursts → gunfire → fire` ("fire" splits flame/gunfire — sense flag fires)

Overlap is found within two hops in every case, with tens of shared words to choose from. So the
"clouds meet quickly, you don't need deep search" assumption held.

## Known limits (all backing-file or scope issues, not logic bugs)

1. **Resolution** — 50 dimensions is coarse. Very short hops can collapse to their endpoints. Fix
   is a denser space (100d), which is a file swap, not a code change.
2. **Vocabulary** — 40,000 commonest English words. Rare or technical terms won't resolve. Larger
   vocab = larger `space.bin`, same swap path.
3. **Polysemy / sense bias** — a word resolves to its dominant corpus sense. "memory" leans toward
   the computing sense in GloVe, so routes through it. The sense-split flag surfaces this but does
   not fix it; sense-aware embeddings would.
4. **Font dependency** — fonts come from Google Fonts at load; offline it degrades to system fonts.
   Inline/​self-host the fonts if full offline fidelity matters.
5. **First-load friction under `file://`** — one drop of `space.bin`, once. Serving the folder
   removes it.

## Recommended next steps, in order

1. **100d space.** Highest value, lowest risk. Build `space_100d.bin` with the same packer from a
   100d vector source and load it through the settings panel; judge whether chains gain resolution.
   `space.bin` roughly doubles in size. This does not need Cowork — it can be built standalone and
   loaded through the panel.
2. **Fold the old hex field back in** as a close-up lens on a single word's neighbourhood, with the
   graph as the wide-angle view. The original `tld_explorer_7.html` hex/gravity rendering is the
   source for this.
3. **Cross-linguistic fork.** A German or Arabic space is just `german.bin` / `arabic.bin` dropped
   into the same tool. The interesting output there is where the maps *fail* to overlap — the
   untranslatable residue between two languages' fields. This is a genuine fork in purpose, worth
   its own pass rather than bolting onto the English tool.
4. **Performance**, only if vocab grows a lot: `nn` is O(vocab·dims) per call, cached per word.
   Fine at 40k×50. A larger space may want an approximate-NN index or a typed-array hot loop.

## Provenance

GloVe 6B 50d, pulled as a gzipped text file from a GitHub raw mirror, subset to the 40k commonest
words, normalised, int8-quantised, packed into `space.bin`. Source vectors are Common Crawl /
Wikipedia GloVe (Pennington, Socher, Manning). The tool ships no model, only these static vectors.
