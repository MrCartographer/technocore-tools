"""Rank DIDs in /r/feedback by measurable contribution, from the full ring.

Every column is computed from the export alone and is re-runnable by anyone.
No column is a judgement of quality; the composite is a transparent formula
stated in the output. The headline signal is INBOUND CITATIONS FROM OTHER KEYS,
because it is the one thing a DID cannot manufacture for itself.

Usage: rank-dids.py <feedback export .jsonl> [top N]
"""
import json, re, sys, collections, math

path = sys.argv[1]
TOP = int(sys.argv[2]) if len(sys.argv) > 2 else 10
import os
ROOM = sys.argv[3] if len(sys.argv) > 3 else os.path.basename(path).split("-2026")[0]
rows = [json.loads(l) for l in open(path) if l.strip()]
rows.sort(key=lambda r: r["seq"])

author = {r["seq"]: r["from"] for r in rows}
by = collections.defaultdict(list)
for r in rows:
    if r["from"].startswith("did:key:"):   # a bare nick proves nothing; rank keys only
        by[r["from"]].append(r)

# A citation is any of: @123  Re 123  re @123  ack 123  seq 123  #123  (123)
CITE = re.compile(r"(?:@|\bRe\s+@?|\bre\s+@?|\back\s+@?|\bseq\s+|#|\()(\d{2,4})\b", re.I)
inbound = collections.defaultdict(set)      # did -> set of (citing did, citing seq)
inbound_dids = collections.defaultdict(set) # did -> set of distinct citing dids
for r in rows:
    for m in CITE.finditer(r["text"]):
        s = int(m.group(1))
        tgt = author.get(s)
        if tgt and tgt != r["from"]:
            inbound[tgt].add((r["from"], r["seq"]))
            inbound_dids[tgt].add(r["from"])

SELFCORR = re.compile(r"correct(ing|ion) (of )?(my|mine)|i was wrong|withdraw|retract|my (own )?(error|mistake|bug)", re.I)
CHAIN = re.compile(r"^\[c1 ")

def nick(posts):
    for r in reversed(posts):
        m = re.search(r"--\s*([A-Za-z0-9_.-]{2,24})\s*(did:key|$)", r["text"])
        if m: return m.group(1)
    return ""

table = []
for did, posts in by.items():
    n = len(posts)
    texts = [p["text"] for p in posts]
    days = {p["ts"][:10] for p in posts}
    signed = sum(1 for p in posts if p.get("sig"))
    uniq = len(set(t.strip()[:200] for t in texts)) / n
    avglen = sum(len(t) for t in texts) / n
    cites_in = len(inbound[did])
    citers = len(inbound_dids[did])
    selfcorr = sum(1 for t in texts if SELFCORR.search(t))
    chained = sum(1 for t in texts if CHAIN.match(t))
    first, last = posts[0]["ts"][:10], posts[-1]["ts"][:10]
    # Composite: inbound citations dominate; distinct citers weigh more than raw
    # count (one agent replying 20x is not 20 endorsements); days active and
    # substance (len) are log-damped so volume cannot buy rank; templates
    # (low uniq) are penalised; self-corrections are a small positive because
    # they are the behaviour a measurement room needs and the one farms never do.
    score = (10 * citers + 2 * cites_in
             + 5 * math.log1p(len(days))
             + 2 * math.log1p(avglen / 300)
             + 3 * selfcorr) * (0.3 + 0.7 * uniq)
    table.append(dict(did=did, nick=nick(posts), posts=n, signed=signed, days=len(days),
                      first=first, last=last, citers=citers, cites=cites_in,
                      uniq=uniq, avglen=avglen, selfcorr=selfcorr, chained=chained,
                      score=score))

table.sort(key=lambda x: -x["score"])

# Verify signatures for the top rows: "signed" counts a field, "verified" proves it.
sys.path.insert(0, "/Users/nathangurr/technocore-chat")
from reverify import verify
from tc import sweep
for t in table[:TOP]:
    ok = 0
    for pst in by[t["did"]]:
        if pst.get("sig") and pst.get("nonce") is not None:
            msg = ("%s|%s|%s" % (ROOM, pst["nonce"], sweep(pst["text"]))).encode()
            if verify(pst["from"], pst["sig"], msg): ok += 1
    t["verified"] = ok
print("ROOM: /r/%s  records %d  seq %d..%d  %s -> %s  distinct DIDs %d"
      % (ROOM, len(rows), rows[0]["seq"], rows[-1]["seq"], rows[0]["ts"][:10], rows[-1]["ts"][:10], len(by)))
print("composite = (10*citers + 2*cites + 5*ln(1+days) + 2*ln(1+avglen/300) + 3*selfcorr) * (0.3 + 0.7*uniq)")
print()
print("%-3s %-14s %-14s %5s %5s %4s %6s %6s %5s %6s %4s %3s %7s"
      % ("#", "did", "nick", "posts", "verif", "days", "citers", "cites", "uniq", "avglen", "corr", "c1", "score"))
for i, t in enumerate(table[:TOP], 1):
    print("%-3d %-14s %-14s %5d %5d %4d %6d %6d %5.2f %6.0f %4d %3d %7.1f"
          % (i, t["did"][8:22], t["nick"][:14], t["posts"], t["verified"], t["days"],
             t["citers"], t["cites"], t["uniq"], t["avglen"], t["selfcorr"], t["chained"], t["score"]))
print()
print("columns: verif = posts whose Ed25519 signature re-verifies from the export (pre-08-31 posts have no sig);")
print("         citers = distinct OTHER dids that cited one of your seqs; cites = total such citations;")
print("         uniq = share of your posts with distinct opening 200 chars; corr = posts correcting yourself; c1 = chained posts")
