#!/bin/zsh
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
"${ROOT_DIR}/tools/visual_validation/service.sh" start-open

echo ""
echo "Visual validation page:"
echo "http://127.0.0.1:8765"
echo ""
echo "You can close this terminal window after the page opens."
