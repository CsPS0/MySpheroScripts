#!/usr/bin/env bash
cd "$(dirname "$0")/sphero-neu" && .venv/bin/python web/server.py --host 0.0.0.0 --port 8080 "$@"
