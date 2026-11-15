#!/usr/bin/env bash
# Construit les zips des deux Lambdas : code de backend/<lambda> + backend/common
# + dépendances de backend/<lambda>/requirements.txt (installées pour arm64 /
# Python 3.12). Les zips sont factices tant que les handlers n'existent pas
# encore (WS4, WS5) : la copie se contente de ce qui existe.
#
# pandas, pyarrow et numpy sont exclus de la Lambda agents : fournis par la
# couche AWS SDK for pandas (variable pandas_layer_arn).
#
# Usage : infra/scripts/build_lambdas.sh [api|agents]   (aucun appel AWS)
#         sans argument : construit les deux zips ; avec un nom : celui-là seulement.

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

# Contrôle de fin de build api : la validation des tickers embarquée exige
# backend/api/tickers.json dans le zip (contrat : srv-api-light.rules, lecture
# S3 du seul fichier OU copie embarquée). Actif dès qu'il y a du code
# applicatif ; tant que les handlers n'existent pas (WS4), les zips factices
# passent avec un avertissement.
check_tickers_json() {
    local name="$1"
    local zip="$build_dir/$name.zip"
    if [ ! -f "$repo_root/backend/$name/app.py" ] && [ ! -f "$repo_root/backend/$name/requirements.txt" ]; then
        echo "  (handlers pas encore livrés : contrôle tickers.json reporté)"
        return 0
    fi
    # Listing capturé avant grep -q : sous pipefail, la fermeture anticipée du tube faisait échouer unzip (SIGPIPE).
    local listing
    listing="$(unzip -l "$zip")"
    if grep -qE "backend/api/tickers[.]json$" <<<"$listing"; then
        echo "  contrôle tickers.json : présent dans le zip"
    else
        echo "ERREUR : backend/api/tickers.json absent du zip de $name." >&2
        echo "        Régénère-le depuis universe.parquet si l'univers de WS3 a changé." >&2
        exit 1
    fi
}

build_lambda() {
    local name="$1"
    local stage="$staging/$name"
    echo "=== Construction de $name.zip ==="
    mkdir -p "$stage/backend"
    cp -r "$repo_root/backend/$name" "$stage/backend/$name"
    cp -r "$repo_root/backend/common" "$stage/backend/common"
    # Les tests (WS0/WS2) et caches n'appartiennent pas au zip de production.
    rm -rf "$stage/backend/common/tests" "$stage/backend/$name/tests"
    find "$stage" -type d -name "__pycache__" -prune -exec rm -rf {} +
    find "$stage" -name "*.pyc" -delete

    local req="$repo_root/backend/$name/requirements.txt"
    if [ -f "$req" ]; then
        # À la racine du stage (donc du zip) : la Lambda cherche les modules
        # dans /var/task, pas dans /var/task/backend.
        pip_install_arm "$stage" "$req"
        # Paquets fournis par la couche AWS SDK for pandas : retirés du zip.
        rm -rf "$stage/pandas" "$stage/pyarrow" "$stage/numpy"
        find "$stage" -maxdepth 1 \( -name "pandas*" -o -name "pyarrow*" -o -name "numpy*" \) -exec rm -rf {} +
        if [ "$name" = "agents" ]; then
            # Dépendances de strands-agents jamais importées par la Lambda (serveur MCP,
            # serveur HTTP, JWT) : environ 20 Mo de moins à côté de la couche pandas,
            # sous la limite de 250 Mo décompressés. Vérifié par un import bloquant (WS5).
            for pkg in mcp mcp_types starlette sse_starlette uvicorn cryptography jwt multipart python_multipart; do
                rm -rf "${stage:?}/$pkg"
                find "$stage" -maxdepth 1 -iname "${pkg}-*.dist-info" -exec rm -rf {} +
            done
        fi
    else
        echo "  (pas de requirements.txt dans backend/$name : zip factice)"
    fi
    # Le requirements.txt reste un artefact de build, il ne part pas en production.
    rm -f "$stage/backend/$name/requirements.txt"

    mkdir -p "$build_dir"
    rm -f "$build_dir/$name.zip"
    # Tout le contenu du stage : backend/ (code) et les dépendances à la racine.
    (cd "$stage" && python3 -m zipfile -c "$build_dir/$name.zip" .)
    ls -lh "$build_dir/$name.zip"
    if [ "$name" = "api" ]; then
        check_tickers_json "$name"
    fi
}

target="${1:-all}"
case "$target" in
    all) build_lambda api; build_lambda agents ;;
    api|agents) build_lambda "$target" ;;
    *) echo "Usage : $0 [api|agents]" >&2; exit 2 ;;
esac
echo "=== Zips prêts dans $build_dir ==="
