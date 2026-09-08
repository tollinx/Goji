#!/usr/bin/env bash
# Start the API using this project's venv whether or not it's activated.
# Anaconda on the PATH otherwise shadows it and uvicorn fails with
# ModuleNotFoundError: fastapi.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x venv/bin/uvicorn ]; then
  echo "venv is missing or incomplete. Create it with:" >&2
  echo "  python3 -m venv venv && ./venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

exec ./venv/bin/uvicorn app.main:app --reload "$@"
