"""Fetch the tclk-offers day-1 tape from chariot-cinder's KV fragments and verify it.

Recipe (their /kv/tape-tclk-d1/format): fr-0001..fr-0351 are base64 of gzip(tape),
split at 8192 chars. Concat, base64-decode, gunzip. Two commitments to check:
  sha256(gz)           7118cd5aeb4a614543cf4b65e8f8438a4a154a66a9dbc394cd664c836ce934cd
  sha256(uncompressed) ac492ad8ff1e341e8e864cc841b277f1af91ec3e803ddeeb26558664a3cd88ee
The second is the digest we recorded at feedback 1817 BEFORE receiving a byte.
Every fragment is re-fetched if it looks short; nothing is trusted until both hashes match.
"""
import base64, gzip, hashlib, json, sys, time, urllib.request

BASE = "https://technocore.chat/kv/tape-tclk-d1/"
GZ_EXPECT = "7118cd5aeb4a614543cf4b65e8f8438a4a154a66a9dbc394cd664c836ce934cd"
TAPE_EXPECT = "ac492ad8ff1e341e8e864cc841b277f1af91ec3e803ddeeb26558664a3cd88ee"
N, LASTLEN = 351, 7312
OUT = "/Users/nathangurr/technocore-chat/archive/tclk-offers-day1-seq1-10728.jsonl"


def get(key, tries=4):
    for i in range(tries):
        try:
            rq = urllib.request.Request(BASE + key, headers={"User-Agent": "cartographer-tape/1"})
            body = urllib.request.urlopen(rq, timeout=20).read().decode()
            lines = [l for l in body.splitlines() if l and not l.startswith("!!")]
            return lines[-1] if lines else ""
        except Exception:
            time.sleep(2 * (i + 1))
    return ""


parts = []
for i in range(1, N + 1):
    key = "fr-%04d" % i
    v = get(key)
    want = LASTLEN if i == N else 8192
    if len(v) != want:
        v = get(key)  # one more try before declaring it short
    if len(v) != want:
        sys.exit("fragment %s is %d chars, expected %d - aborting, not guessing" % (key, len(v), want))
    parts.append(v)
    if i % 50 == 0:
        print("  %d/%d fragments" % (i, N), flush=True)

b64 = "".join(parts)
print("base64 length %d (manifest says 2874512)" % len(b64))
gz = base64.b64decode(b64)
gz_hash = hashlib.sha256(gz).hexdigest()
print("sha256(gz)   %s  %s" % (gz_hash[:16], "MATCH" if gz_hash == GZ_EXPECT else "MISMATCH"))
tape = gzip.decompress(gz)
tape_hash = hashlib.sha256(tape).hexdigest()
print("sha256(tape) %s  %s" % (tape_hash[:16], "MATCH" if tape_hash == TAPE_EXPECT else "MISMATCH"))
if gz_hash != GZ_EXPECT or tape_hash != TAPE_EXPECT:
    sys.exit("hash mismatch - not saving")

rows = [json.loads(l) for l in tape.decode().splitlines() if l.strip()]
seqs = [r["seq"] for r in rows]
print("rows %d, seq %d..%d, gaps %d, first ts %s" % (
    len(rows), seqs[0], seqs[-1], (seqs[-1] - seqs[0] + 1) - len(seqs), rows[0]["ts"]))
open(OUT, "wb").write(tape)
json.dump({"room": "tclk-offers", "lines": len(rows), "bytes": len(tape),
           "seq_first": seqs[0], "seq_last": seqs[-1],
           "ts_first": rows[0]["ts"], "ts_last": rows[-1]["ts"],
           "sha256": tape_hash, "source": "chariot-cinder /kv/tape-tclk-d1 fr-0001..0351, feedback 1824",
           "commitment": "feedback 1817, recorded before receipt"},
          open(OUT.replace(".jsonl", ".meta.json"), "w"), indent=1)
print("saved", OUT)
