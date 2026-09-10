#!/usr/bin/env bash
venv_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.venv" && pwd)"
"$venv_dir"/bin/python -m pip install -e .