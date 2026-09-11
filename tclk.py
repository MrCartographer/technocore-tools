"""tclk/1 frame builder - canonical encoding per flop-labs/tclk src/frames.ts.

Deliberately independent of the TypeScript package. The id derivation is the one
thing both sides must agree on byte-for-byte, and a second implementation that
can be checked against live frames is worth more than trusting one.
"""
import hashlib, json, os

DOMAIN = "FLOP::tclk::v1"
MAX_FRAME_CHARS = 4096


def canonical(v):
    """Sorted keys, compact separators, undefined dropped (None means absent)."""
    if v is None or not isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False, separators=(",", ":"))
    if isinstance(v, list):
        return "[" + ",".join(canonical(x) for x in v) + "]"
    return "{" + ",".join(
        json.dumps(k, ensure_ascii=False) + ":" + canonical(v[k])
        for k in sorted(v) if v[k] is not None) + "}"


def to_ascii(s):
    """Escape every non-ASCII char the way JS does, surrogates included.

    frames.ts escapes with String.replace over a JS string, and JS strings are
    UTF-16: charCodeAt on an astral character yields two surrogate code units and
    emits two \\uXXXX escapes. Python iterates codepoints, so a naive port emits
    one escape and produces a different digest for exactly the non-ASCII payloads
    the spec added this escape for. Split astral chars manually to match.
    """
    out = []
    for ch in s:
        cp = ord(ch)
        if cp < 0x80:
            out.append(ch)
        elif cp <= 0xFFFF:
            out.append("\\u%04x" % cp)
        else:
            cp -= 0x10000
            out.append("\\u%04x\\u%04x" % (0xD800 + (cp >> 10), 0xDC00 + (cp & 0x3FF)))
    return "".join(out)


def domain_hash(tag, payload):
    msg = DOMAIN + "|" + tag + "|" + to_ascii(payload)
    return "0x" + hashlib.sha256(msg.encode()).hexdigest()


def offer_id(fields):
    """The offer id. `fields` must NOT contain `id`."""
    return domain_hash("offer", canonical(fields))


def contract_id(offer, accept_core):
    """Binds the full offer (id included) and the acceptance core."""
    return domain_hash("contract", canonical({"offer": offer, "accept": accept_core}))


def encode(frame):
    line = "tclk1 " + to_ascii(canonical(frame))
    if len(line) > MAX_FRAME_CHARS:
        raise SystemExit("frame is %d chars, cap is %d" % (len(line), MAX_FRAME_CHARS))
    return line


def new_hash_lock():
    """Mint a preimage and its statement. The preimage never leaves the payee."""
    p = os.urandom(32)
    return "0x" + p.hex(), "0x" + hashlib.sha256(p).hexdigest()


def nonce():
    return os.urandom(8).hex()
