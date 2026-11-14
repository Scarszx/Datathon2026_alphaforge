#!/usr/bin/env bash
# Construit les zips des deux Lambdas : code de backend/<lambda> + backend/common
# + dépendances de backend/<lambda>/requirements.txt (installées pour arm64 /
# Python 3.12). Les zips sont factices tant que les handlers n'existent pas
# encore (WS4, WS5) : la copie se contente de ce qui existe.
#
# pandas, pyarrow et numpy sont exclus de la Lambda agents : fournis par la
# couche AWS SDK for pandas (variable pandas_layer_arn).
#
# Usage : infra/scripts/build_lambdas.sh   (aucun appel AWS)

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
build_dir="$repo_root/infra/terraform/build"
staging="$(mktemp -d)"
trap 'rm -rf "$staging"' EXIT

# Dépendances installées pour arm64 + Python 3.12, même depuis un hôte x86_64
# (macOS/Linux) : le runtime des Lambdas est arm64.
pip_install_arm() {
    pip3 install --quiet --no-cache-dir --no-compile \
        --only-binary=:all: \
        --platform manylinux2014_aarch64 \
        --implementation cp --python-version 3.12 --abi cp312 \
        --target "$1" -r "$2"
}

build_lambda() {
    local name="$1"
    local stage="$staging/$name"
    echo "=== Construction de $name.zip ==="

    mkdir -p "$stage/backend"
    cp -r "$repo_root/backend/$name" "$stage/backend/$name"
    cp -r "$repo_root/backend/common" "$stage/backend/common"
    # Les tests (WS0/WS2) et caches n'appartiennent pas au zip de production.
    rm -rf "$stage/backend/common/tests"
    find "$stage" -type d -name "__pycache__" -prune -exec rm -rf {} +
    find "$stage" -name "*.pyc" -delete

    local req="$repo_root/backend/$name/requirements.txt"
    if [ -f "$req" ]; then
        pip_install_arm "$stage/backend" "$req"
        # Paquets fournis par la couche AWS SDK for pandas : retirés du zip.
        rm -rf "$stage/backend/pandas" "$stage/backend/pyarrow" "$stage/backend/numpy"
        find "$stage/backend" -maxdepth 1 \( -name "pandas*" -o -name "pyarrow*" -o -name "numpy*" \) -exec rm -rf {} +
    else
        echo "  (pas de requirements.txt dans backend/$name : zip factice)"
    fi

    mkdir -p "$build_dir"
    rm -f "$build_dir/$name.zip"
    (cd "$stage" && python3 -m zipfile -c "$build_dir/$name.zip" backend)
    ls -lh "$build_dir/$name.zip"
}

build_lambda api
build_lambda agents
echo "=== Zips prêts dans $build_dir ==="
