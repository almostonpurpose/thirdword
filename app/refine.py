"""
Refinement: pick the meeting node that is genuinely BETWEEN (balanced
distance to both ends, not just sitting in the anchor's lap), then
reconstruct the actual two-leg path current -> bridge -> anchor through
the nearest-neighbour graph. That reconstructed path is the 'skeleton'
the graph view would draw once the first overlap collapses the problem.
"""
import numpy as np, heapq
V = np.load('vecs.npy'); words = open('words.txt').read().split('\n')
idx = {w:i for i,w in enumerate(words)}; N=len(words)
rank=np.arange(N); spec=np.clip(np.log1p(rank)/np.log1p(N),0.15,1.0)
STOP=set('the , . of to and in a " \'s for - ( ) on with as by is was at from that it one'.split())

def nbrs(i,k=40):
    s=V@V[i]; o=np.argpartition(-s,k+40)[:k+40]; o=o[np.argsort(-s[o])]
    r=[]
    for j in o:
        if j==i or words[j] in STOP: continue
        r.append((int(j),float(s[j])))
        if len(r)>=k: break
    return r

def expand(seed,hops=2,k=40):
    seen={seed:(1.0,0)}; cur=[seed]
    for h in range(1,hops+1):
        nx=[]
        for i in cur:
            for j,sc in nbrs(i,k):
                if j not in seen: seen[j]=(sc,h); nx.append(j)
        cur=nx
    return seen

def best_bridge(current,anchor,hops=2,k=40):
    ci,ai=idx[current],idx[anchor]
    cc,ac=expand(ci,hops,k),expand(ai,hops,k)
    cand=[]
    for n in set(cc)&set(ac):
        cs=cc[n][0]; as_=ac[n][0]
        conj=min(cs,as_); balance=1-abs(cs-as_)   # reward equidistant nodes
        score=conj*(0.5+0.5*balance)*spec[n]
        cand.append((score,n,cs,as_))
    cand.sort(reverse=True)
    return cand[:6], cc, ac

def greedy_path(a,b,k=40,maxlen=6):
    """walk from a toward b through neighbours, maximising step-similarity to b."""
    tgt=V[idx[b]]; cur=idx[a]; path=[a]; seen={cur}
    for _ in range(maxlen):
        if cur==idx[b]: break
        best=None;bw=-9
        for j,_ in nbrs(cur,k):
            if j in seen: continue
            w=float(V[j]@tgt)*(0.6+0.4*spec[j])
            if w>bw: bw=w;best=j
        if best is None: break
        cur=best; seen.add(cur); path.append(words[cur])
        if words[cur]==b: break
    if path[-1]!=b: path.append(b)
    return path

for cur,anc in [('assistant','biology'),('assistant','memory'),
                ('shadow','ocean'),('threshold','silence'),('memory','garden')]:
    cand,_,_=best_bridge(cur,anc)
    print(f"\n{cur:>10} → {anc:<9}")
    print("   balanced bridges:", ", ".join(f"{words[n]}({cs:.2f}/{as_:.2f})" for _,n,cs,as_ in cand))
    bridge=words[cand[0][1]] if cand else anc
    leg1=greedy_path(cur,bridge); leg2=greedy_path(bridge,anc)
    full=leg1+leg2[1:]
    print("   path skeleton:   ", " → ".join(full))
