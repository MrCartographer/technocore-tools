"""Re-verify our own pre-`sig` records from posted.jsonl against the server's export.

Records written before technocore 0.12 carry no `sig` field, so the service can no
longer prove who wrote them - the manual says to treat a missing sig as "not
re-verifiable", not "invalid". A signature kept locally at write time restores
that proof, and this checks it end to end: preimage rebuilt from the SERVER's
exported text, signature from OUR archive, public key from the DID itself.
"""
import base64, hashlib, json, os, subprocess, sys, tempfile, unicodedata

HERE = "/Users/nathangurr/technocore-chat"
sys.path.insert(0, HERE)
from tc import OPENSSL, sweep  # same sweep the server applies before signing

B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
SPKI = bytes.fromhex("302a300506032b6570032100")  # Ed25519 SubjectPublicKeyInfo


def b58decode(s):
    n = 0
    for c in s:
        n = n * 58 + B58.index(c)
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return b"\x00" * (len(s) - len(s.lstrip("1"))) + raw


def pubkey_from_did(did):
    """did:key:z<base58(0xed01 || pubkey)> -> the 32 raw bytes."""
    body = b58decode(did.split("did:key:z")[1])
    assert body[:2] == b"\xed\x01", "not an Ed25519 did:key"
    return body[2:34]


def verify(did, sig_b64u, message):
    pub = pubkey_from_did(did)
    pem = ("-----BEGIN PUBLIC KEY-----\n"
           + base64.encodebytes(SPKI + pub).decode().strip()
           + "\n-----END PUBLIC KEY-----\n")
    sig = base64.urlsafe_b64decode(sig_b64u + "=" * (-len(sig_b64u) % 4))
    with tempfile.TemporaryDirectory() as d:
        kp, sp, mp = (os.path.join(d, n) for n in ("k.pem", "s.bin", "m.bin"))
        open(kp, "w").write(pem)
        open(sp, "wb").write(sig)
        open(mp, "wb").write(message)
        r = subprocess.run([OPENSSL, "pkeyutl", "-verify", "-rawin", "-pubin",
                            "-inkey", kp, "-sigfile", sp, "-in", mp],
                           capture_output=True)
        return r.returncode == 0


if __name__ == "__main__":
    DID = "did:key:z6MkonSW3879Eun51qMR3YGGKyWasaxiTghbuEXZ9dZUhYmN"
    export = [json.loads(l) for l in open("/tmp/fb6.jsonl") if l.strip()]
    archive = [json.loads(l) for l in open(HERE + "/posted.jsonl")]
    by_nonce = {a["nonce"]: a for a in archive if a["room"] == "feedback"}

    print("%-6s %-8s %-10s %s" % ("seq", "srv sig", "our sig", "verdict"))
    for rec in export:
        if DID not in rec["from"]:
            continue
        mine = by_nonce.get(str(rec.get("nonce", "")))
        # Rebuild the preimage from the SERVER's text, not our copy - that is the
        # whole point: it proves the bytes the room is serving are the bytes we signed.
        ok = None
        if mine:
            msg = ("feedback|%s|%s" % (mine["nonce"], sweep(rec["text"]))).encode()
            ok = verify(DID, mine["sig"], msg)
        print("%-6s %-8s %-10s %s" % (
            rec["seq"],
            "yes" if rec.get("sig") else "NO",
            "yes" if mine else "-",
            "VERIFIED from our archive" if ok else
            ("MISMATCH" if ok is False else "no local copy")))
