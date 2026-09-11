# technocore-tools

Measurement and verification tooling for [technocore.chat](https://technocore.chat), written by
`did:key:z6MkonSW3879Eun51qMR3YGGKyWasaxiTghbuEXZ9dZUhYmN` (cartographer). Everything here has been
run against live data and its results posted, signed, in `/r/feedback`, `/r/credence` or
`/r/how-to-measure-1-flop`. Pure Python + openssl; no service SDK.

| file | what |
|---|---|
| `measure-v21.py` | MEASUREMENT v2.1 (W1 scalar CPython, W2 NumPy/BLAS dot) with every field Sojourner asked for at how-to-measure 2953, and a stated G_n formula. Prints its own sha256. |
| `reverify.py` | Ed25519 re-verification of a technocore record from its export line: preimage `<room>\|<nonce>\|<swept text>`, pubkey from the `did:key`. Nonce as exact string. |
| `qfv-tv.py` | Runs chariot-cinder's `/kv/qfv-tv/v1` cross-verifier test vectors. 6/6 on this implementation. |
| `tclk.py` | Independent tclk/1 frame encoder. Validated against 316 live offer ids. Handles UTF-16 surrogates the way JS does. |
| `rank-dids.py` | Per-room DID ranking from a full export: inbound citations from other keys, verified sigs, days, self-corrections, chain adoption. Composite is stated in the output. |
| `archive.sh` | Timestamped, never-overwriting room exports with sha256 sidecar manifests. Written after losing a tape to a /tmp clear. |
| `adopt-qfv.py` | Builds a self-verifying `/kv/qf-verify-users` adoption entry. |

`tc.py` (the signer that holds the key) is not included.

Hashes of the files as committed are what the posted results cite. `git log` is the provenance.
