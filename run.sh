#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
python3.12 -m streamlit run app.py --server.port 8501
