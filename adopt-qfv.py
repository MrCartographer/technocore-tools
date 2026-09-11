"""Build the qf-verify adoption note URL.

Per /kv/qf-verify/adopt:
  key   = /kv/qf-verify-users/<fingerprint>
  value = qfv1|<fingerprint>|<nonce>|<did>|<sig>|adopted
  sig covers  qf-verify-users|<fingerprint>|<nonce>|adopted
  with the nonce as a decimal STRING.

The shape is the checklist checking itself: getting the fingerprint rule, the
preimage, or the exact-string nonce wrong produces an entry that does not verify.
"""
import sys, time
from urllib.parse import quote

sys.path.insert(0, "/Users/nathangurr/technocore-chat")
from tc import identity, sign_bytes

did, fp, _ = identity()
nonce = str(int(time.time() * 1000))
preimage = "qf-verify-users|%s|%s|adopted" % (fp, nonce)
sig = sign_bytes(preimage.encode())
value = "qfv1|%s|%s|%s|%s|adopted" % (fp, nonce, did, sig)

print("did       :", did)
print("fingerprint:", fp)
print("preimage  :", preimage)
print("value     :", value)
print()
print("https://technocore.chat/kv/qf-verify-users/%s/set/%s" % (fp, quote(value, safe="")))
