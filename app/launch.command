#!/bin/bash
# Isthmus — double-click this in Finder to launch.
# Serves the folder over HTTP (needed: the page fetches local .bin files)
# and opens it in your default browser.

cd "$(dirname "$0")" || exit 1
PORT=8008

# Reuse an already-running server if there is one; otherwise start it.
if lsof -iTCP:$PORT -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Server already running on port $PORT — reusing it."
else
  python3 -m http.server "$PORT" --bind 127.0.0.1 >/dev/null 2>&1 &
  SERVER_PID=$!
  sleep 1
fi

open "http://127.0.0.1:$PORT/meaning_map_v9.html"

echo ""
echo "  Isthmus → http://127.0.0.1:$PORT/meaning_map_v9.html"
echo "  Close this window (or Ctrl-C) to stop the server."
echo ""

# Keep the server alive while this Terminal window is open.
[ -n "$SERVER_PID" ] && wait $SERVER_PID
