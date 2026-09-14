#!/usr/bin/env bash
# Regenerates the >5MB fixture used by the "oversized attachment" Postman
# test. Not committed (see .gitignore) — regenerate before running the
# collection if fixtures/oversized.pdf is missing.
set -euo pipefail
cd "$(dirname "$0")"
head -c 6291456 /dev/urandom > oversized.pdf
