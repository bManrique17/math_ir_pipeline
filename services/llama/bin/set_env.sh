#!/usr/bin/env bash
set -euo pipefail

ENV_NAME="llama_server"
REQ_FILE="requirements.txt"

if ! conda info --envs | awk '{print $1}' | grep -qx "$ENV_NAME"; then
  conda create -y -n "$ENV_NAME" python=3.12
fi

CONDA_BASE="$(conda info --base)"
source "$CONDA_BASE/etc/profile.d/conda.sh"

conda activate "$ENV_NAME"

python -m pip install --upgrade pip
python -m pip install -r "$REQ_FILE"

echo "Environment '$ENV_NAME' is ready."
