# Meaning Map

A semantic-space navigation tool. You stand on a word, name a few "fields" you want to reach,
and the tool finds the shortest chain of meaning to each one, then shows whether each hop
actually moves you closer. It began as a tool for naming a website and has been rebuilt around
the mechanic that turned out to be the interesting part: triangulation between several meaning
fields at once.

Vanilla JS, no build step, no runtime framework. Runs entirely client-side against a static
vector file.

## Running it

```
cd app
python3 -m http.server
```

then open `meaning_map_v8.html` (documented, stable) or `meaning_map_v9.html` (in-progress —
adds a control panel for filtering/grouping/encoding words by dimension, see
[`app/HANDOVER.md`](app/HANDOVER.md) for the current design direction). On macOS you can also
just double-click `app/launch.command`.

Opening a file directly (double-click, no server) works too — the first open needs you to drop
`space.bin` onto the panel once, since browsers block `file://` fetches. After that the space is
cached in the browser (IndexedDB) and loads on its own, offline included.

## Layout

- `app/` — the tool itself: the HTML files, the semantic space (`space.bin`), and the Python
  reference implementation (`engine.py`, `refine.py`) the JS engine was validated against. See
  `app/HANDOVER.md` for the full write-up: how bidirectional search works, the scoring formulas,
  the `space.bin` file format, known limits, and recommended next steps.
- `archive/` — superseded iteration history (early hex-grid/gravity-field prototypes, old
  progress notes, stale backups), kept for reference but not part of the current tool.

## The idea, briefly

Rather than expanding one search frontier from the current word and watching it fan out, the
tool grows a small neighbourhood cloud from the current word *and* from each anchor word, and
lets them meet. The first raw overlap is junk (frequent hub words like "thing" sit in everyone's
neighbourhood), so candidates are scored for being genuinely *between* the two ends rather than
just close to one of them, and a walk through the nearest-neighbour graph reconstructs the
path. Full details, including why each part of the scoring is necessary, are in
`app/HANDOVER.md`.
