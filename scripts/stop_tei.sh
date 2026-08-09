#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
fi

OS_NAME=$(uname -s)
RUNTIME_DIR=${TEI_RUNTIME_DIR:-.runtime/tei}
SIMILARITY_CONTAINER=${TEI_SIMILARITY_CONTAINER_NAME:-community-analysis-tei-similarity}
CLUSTERING_CONTAINER=${TEI_CLUSTERING_CONTAINER_NAME:-community-analysis-tei-clustering}

if [[ "$OS_NAME" == "Darwin" ]]; then
    for profile in similarity clustering; do
        pid_file="$RUNTIME_DIR/${profile}.pid"
        if [[ -f "$pid_file" ]]; then
            pid=$(cat "$pid_file" 2>/dev/null || true)
            if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
                kill "$pid"
                echo "Stopped TEI $profile profile (pid $pid)."
            fi
            rm -f "$pid_file"
        fi
    done
else
    if command -v docker >/dev/null 2>&1; then
        for container in "$SIMILARITY_CONTAINER" "$CLUSTERING_CONTAINER"; do
            if docker ps -a --format '{{.Names}}' | grep -Fxq "$container"; then
                docker rm -f "$container" >/dev/null
                echo "Stopped $container."
            fi
        done
    fi
fi
