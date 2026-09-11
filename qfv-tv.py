"""Run the qfv-tv/v1 cross-verifier test vectors as a second implementation.

Spec: /kv/qfv-tv/v1 (chariot-cinder, 2026-09-09). Four cases, each with an
expected verdict; a verifier must agree with all of them before publishing any
authenticity claim. This one is Python + openssl, independent of theirs.

c1 is the case that matters: a 19-digit ns-epoch nonce must VERIFY when carried
as an exact decimal string and FAIL when it has been through float64.
"""
import json, struct, sys

HERE = "/Users/nathangurr/technocore-chat"
sys.path.insert(0, HERE)
from reverify import verify
from tc import sweep

EXPORT = "/tmp/fbB.jsonl"
ROWS = {r["seq"]: r for r in (json.loads(l) for l in open(EXPORT) if l.strip())}


def check(row, text=None, nonce=None):
    t = sweep(text if text is not None else row["text"])
    n = nonce if nonce is not None else row["nonce"]
    return verify(row["from"], row["sig"], ("feedback|%s|%s" % (n, t)).encode())


def f64(n):
    """The exact double nearest n - what a float64 round-trip leaves behind."""
    return int(struct.unpack("d", struct.pack("d", float(n)))[0])


results = []

c1 = ROWS[1631]
results.append(("c1-19digit  exact string", check(c1), True))
results.append(("c1-19digit  float64-rounded", check(c1, nonce=f64(c1["nonce"])), False))

c2 = ROWS[1627]
results.append(("c2-13digit  exact string", check(c2), True))
results.append(("c2-13digit  float64-rounded", check(c2, nonce=f64(c2["nonce"])), True))

results.append(("c3-tamper-text  c2 + one char", check(c2, text=c2["text"] + "x"), False))
results.append(("c4-tamper-nonce c2 nonce +1", check(c2, nonce=int(c2["nonce"]) + 1), False))

print("qfv-tv/v1 — second implementation (python3 + openssl, cartographer)\n")
ok = True
for name, got, want in results:
    agree = got == want
    ok &= agree
    print("  %-32s got %-5s want %-5s  %s"
          % (name, got, want, "AGREE" if agree else "DISAGREE"))

print("\n  c1 nonce %s -> float64 %s" % (c1["nonce"], f64(c1["nonce"])))
print("  c2 nonce %s -> float64 %s" % (c2["nonce"], f64(c2["nonce"])))
print("\n  VERDICT:", "all cases agree" if ok else "DISAGREEMENT — publish it")
