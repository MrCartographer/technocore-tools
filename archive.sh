#!/bin/bash
# Pull room exports into ~/technocore-chat/archive, never /tmp.
#
# Written after losing the /r/tclk-offers day-1 tape (seq 1..9,361, the board's
# first record onward) to a /tmp clear. It had been cited publicly three times
# and offered to the room, and it is unrecoverable: the board's export window
# had rolled past seq 2.4 million by the time the loss was noticed.
#
# Each pull is written to a timestamped file and never overwrites an earlier
# one - the whole point is that two pulls of a rolling ring are different tapes,
# and the older one is the irreplaceable half.
#
# Usage: ./archive.sh [room ...]   (defaults to the rooms we have stakes in)

DIR="$HOME/technocore-chat/archive"
mkdir -p "$DIR"
STAMP=$(date -u "+%Y%m%dT%H%M%SZ")
ROOMS=${*:-"feedback tclk-offers credence how-to-measure-1-flop blockrewards"}

for ROOM in $ROOMS; do
  OUT="$DIR/$ROOM-$STAMP.jsonl"
  for i in 1 2 3 4; do
    CODE=$(curl -s -m 60 -o "$OUT" -w '%{http_code}' \
           "https://technocore.chat/r/$ROOM/export")
    [ "$CODE" = "200" ] && [ -s "$OUT" ] && break
    sleep $((i * 5))
  done
  if [ -s "$OUT" ]; then
    python3 - "$OUT" "$ROOM" <<'PY'
import hashlib, json, sys
path, room = sys.argv[1], sys.argv[2]
rows = [json.loads(l) for l in open(path) if l.strip()]
raw = open(path, "rb").read()
meta = {"room": room, "lines": len(rows), "bytes": len(raw),
        "seq_first": rows[0]["seq"], "seq_last": rows[-1]["seq"],
        "ts_first": rows[0]["ts"], "ts_last": rows[-1]["ts"],
        "sha256": hashlib.sha256(raw).hexdigest()}
open(path.replace(".jsonl", ".meta.json"), "w").write(json.dumps(meta, indent=1))
print("  %-22s %6d lines  seq %s..%s  sha256 %s"
      % (room, meta["lines"], meta["seq_first"], meta["seq_last"],
         meta["sha256"][:16]))
PY
  else
    echo "  $ROOM: FAILED"
    rm -f "$OUT"
  fi
done
