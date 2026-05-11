#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
[ -f .env ] || cp .env.example .env
python3 -m venv .venv 2>/dev/null || true
source .venv/bin/activate
pip install -q -r requirements.txt
python -m app
