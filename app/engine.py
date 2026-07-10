"""
Proof of concept for the meaning-map engine.

Implements Amr's bidirectional-overlap idea on real GloVe vectors:
  - a word's "cloud" = its k nearest neighbours by cosine similarity
  - expand a frontier from the CURRENT word and from EACH anchor word
  - the first overlap between current-front and an anchor-front is the "meeting node"
  - a hub penalty keeps the meeting node from collapsing onto junk words
    like "thing"/"system" that sit in everybody's neighbourhood

We compare three things so the hub problem is visible:
  (A) literal first overlap  (no penalty)  -> expected to be junky
  (B) overlap ranked by specificity penalty -> expected to be sensible
  (C) for reference, the straight embedding-interpolation chain
"""
import numpy as np

V = np.load('vecs.npy')                      # (N,50) L2-normalised
words = open('words.txt').read().split('\n')
idx = {w: i for i, w in enumerate(words)}
N = len(words)

# ---- hub / frequency penalty -------------------------------------------------
# rank 0 = most frequent. Common words are hubs. We turn rank into a mild
# specificity weight in [~0.15, 1.0]: rare words score higher.
rank = np.arange(N)
spec = np.clip(np.log1p(rank) / np.log1p(N), 0.15, 1.0)   # specificity per word

STOP = set('the , . of to and in a " \'s for - ( ) on with as by is was at from that it'.split())

def neighbours(i, k=40):
    """k nearest vocabulary words to row i, excluding self and stopwords."""
    sims = V @ V[i]
    order = np.argpartition(-sims, k + 30)[:k + 30]
    order = order[np.argsort(-sims[order])]
    out = []
    for j in order:
        if j == i: continue
        if words[j] in STOP: continue
        out.append((int(j), float(sims[j])))
        if len(out) >= k: break
    return out

def expand(seed_i, hops=2, k=40):
    """BFS cloud: dict node-> (best cosine to ANY seed-path, hop reached)."""
    frontier = {seed_i: (1.0, 0)}
    seen = dict(frontier)
    cur = [seed_i]
    for h in range(1, hops + 1):
        nxt = []
        for i in cur:
            for j, s in neighbours(i, k):
                if j not in seen:
                    seen[j] = (s, h); nxt.append(j)
        cur = nxt
    return seen   # node -> (sim, hop)

# ---- the core: bidirectional overlap ----------------------------------------
def bridges(current, anchors, hops=2, k=40):
    ci = idx[current]
    cur_cloud = expand(ci, hops, k)
    results = {}
    for a in anchors:
        if a not in idx:
            results[a] = []; continue
        ac = expand(idx[a], hops, k)
        overlap = set(cur_cloud) & set(ac)
        scored = []
        for node in overlap:
            cs, ch = cur_cloud[node]      # closeness to current, hop from current
            as_, ah = ac[node]            # closeness to anchor,  hop from anchor
            # a good meeting node is close to BOTH ends (conjunctive: min),
            # reached in few hops, and specific (not a hub).
            conj = min(cs, as_)
            hoppen = 1.0 / (1 + ch + ah)
            score = conj * (0.4 + 0.6 * hoppen) * spec[node]
            raw   = conj * (0.4 + 0.6 * hoppen)     # without hub penalty
            scored.append((node, score, raw, ch, ah))
        results[a] = scored
    return cur_cloud, results

def show(current, anchors, hops=2, k=40, top=6):
    print('=' * 70)
    print(f"FROM  '{current}'   TOWARD  {anchors}   (hops={hops}, k={k})")
    _, res = bridges(current, anchors, hops, k)
    for a, scored in res.items():
        print(f"\n  → anchor '{a}'   ({len(scored)} overlap words found)")
        if not scored:
            print("    (no overlap at this depth)"); continue
        no_pen = sorted(scored, key=lambda r: -r[2])[:top]
        with_pen = sorted(scored, key=lambda r: -r[1])[:top]
        print("    (A) literal first overlap, NO hub penalty:")
        print("        " + ", ".join(f"{words[n]}" for n,_,_,_,_ in no_pen))
        print("    (B) overlap WITH specificity penalty:")
        print("        " + ", ".join(f"{words[n]}" for n,_,_,_,_ in with_pen))

def interp_chain(current, anchor, steps=6):
    """Reference: snap points along the current->anchor line to nearest words."""
    if anchor not in idx: return []
    a, b = V[idx[current]], V[idx[anchor]]
    chain = []
    for t in np.linspace(0, 1, steps):
        p = (1 - t) * a + t * b
        p = p / (np.linalg.norm(p) or 1)
        sims = V @ p
        # penalise hubs here too, else it routes through 'the','one',...
        sims = sims * (0.5 + 0.5 * spec)
        j = int(np.argmax(sims))
        if not chain or chain[-1] != words[j]:
            chain.append(words[j])
    return chain

if __name__ == '__main__':
    # echoes the file's bio-naming preset: current 'assistant', bio anchors
    show('assistant', ['biology', 'memory', 'collaborator'])
    show('shadow',    ['ocean', 'machine', 'garden'])
    show('threshold', ['silence', 'pulse', 'crystal'])

    print('\n' + '=' * 70)
    print("REFERENCE — embedding-interpolation chains (with hub penalty):")
    for cur, anc in [('assistant','biology'), ('shadow','ocean'),
                     ('memory','archive'), ('threshold','silence')]:
        print(f"  {cur:>10}  →  {anc:<10}: " + "  ·  ".join(interp_chain(cur, anc)))
