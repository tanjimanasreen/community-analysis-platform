#!/usr/bin/env bash
# Start both Text Embeddings Inference profiles used by the project.

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
SIMILARITY_PORT=${TEI_SIMILARITY_HOST_PORT:-${TEI_HOST_PORT:-8080}}
CLUSTERING_PORT=${TEI_CLUSTERING_HOST_PORT:-8081}
SIMILARITY_MODEL=${TEI_SIMILARITY_MODEL_ID:-${TEI_MODEL_ID:-sentence-transformers/paraphrase-MiniLM-L6-v2}}
CLUSTERING_MODEL=${TEI_CLUSTERING_MODEL_ID:-sentence-transformers/all-MiniLM-L6-v2}
SIMILARITY_REVISION=${TEI_SIMILARITY_REVISION:-c9a2bfebc254878aee8c3aca9e6844d5bbb102d1}
CLUSTERING_REVISION=${TEI_CLUSTERING_REVISION:-1110a243fdf4706b3f48f1d95db1a4f5529b4d41}
SIMILARITY_CONTAINER=${TEI_SIMILARITY_CONTAINER_NAME:-community-analysis-tei-similarity}
CLUSTERING_CONTAINER=${TEI_CLUSTERING_CONTAINER_NAME:-community-analysis-tei-clustering}

mkdir -p "$RUNTIME_DIR"

echo "Detected OS: $OS_NAME"
echo "Starting TEI similarity profile on port $SIMILARITY_PORT ($SIMILARITY_MODEL@$SIMILARITY_REVISION)"
echo "Starting TEI clustering profile on port $CLUSTERING_PORT ($CLUSTERING_MODEL@$CLUSTERING_REVISION)"

start_native() {
    local profile="$1" port="$2" model="$3" revision="$4" api_key="$5"
    local pid_file="$RUNTIME_DIR/${profile}.pid"
    local log_file="$RUNTIME_DIR/${profile}.log"

    if [[ -f "$pid_file" ]]; then
        local existing_pid
        existing_pid=$(cat "$pid_file" 2>/dev/null || true)
        if [[ -n "$existing_pid" ]] && kill -0 "$existing_pid" 2>/dev/null; then
            echo "TEI $profile profile already running (pid $existing_pid)."
            return
        fi
        rm -f "$pid_file"
    fi

    local args=(--model-id "$model" --port "$port")
    [[ -n "$revision" ]] && args+=(--revision "$revision")
    [[ -n "${TEI_TOKENIZATION_WORKERS:-}" ]] && args+=(--tokenization-workers "$TEI_TOKENIZATION_WORKERS")
    [[ -n "${TEI_MAX_CLIENT_BATCH_SIZE:-}" ]] && args+=(--max-client-batch-size "$TEI_MAX_CLIENT_BATCH_SIZE")
    [[ -n "${TEI_MAX_BATCH_TOKENS:-}" ]] && args+=(--max-batch-tokens "$TEI_MAX_BATCH_TOKENS")

    (
        [[ -n "$api_key" ]] && export API_KEY="$api_key"
        [[ -n "${TEI_HF_TOKEN:-}" ]] && export HF_TOKEN="$TEI_HF_TOKEN"
        nohup text-embeddings-router "${args[@]}" >"$log_file" 2>&1 &
        echo $! >"$pid_file"
    )
    echo "Started native TEI $profile profile (pid $(cat "$pid_file"))."
}

start_docker() {
    local profile="$1" port="$2" model="$3" revision="$4" api_key="$5" container="$6"
    local image
    local docker_args=(run -d --rm --name "$container" -p "${port}:80")
    image=${TEI_IMAGE:-}
    if command -v nvidia-smi >/dev/null 2>&1; then
        docker_args+=(--gpus all)
        if [[ -z "$image" ]]; then
            echo "Error: TEI_IMAGE environment variable must be explicitly provided for GPU deployments."
            exit 1
        fi
    else
        image=${image:-ghcr.io/huggingface/text-embeddings-inference:cpu-1.5}
    fi

    if docker ps --format '{{.Names}}' | grep -Fxq "$container"; then
        echo "TEI $profile profile already running in container $container."
        return
    fi
    if docker ps -a --format '{{.Names}}' | grep -Fxq "$container"; then
        docker rm -f "$container" >/dev/null
    fi

    if [[ -n "$api_key" ]]; then
        export API_KEY="$api_key"
        docker_args+=(-e API_KEY)
    fi
    if [[ -n "${TEI_HF_TOKEN:-}" ]]; then
        export HF_TOKEN="$TEI_HF_TOKEN"
        docker_args+=(-e HF_TOKEN)
    fi

    local args=(--model-id "$model")
    [[ -n "$revision" ]] && args+=(--revision "$revision")
    [[ -n "${TEI_TOKENIZATION_WORKERS:-}" ]] && args+=(--tokenization-workers "$TEI_TOKENIZATION_WORKERS")
    [[ -n "${TEI_MAX_CLIENT_BATCH_SIZE:-}" ]] && args+=(--max-client-batch-size "$TEI_MAX_CLIENT_BATCH_SIZE")
    [[ -n "${TEI_MAX_BATCH_TOKENS:-}" ]] && args+=(--max-batch-tokens "$TEI_MAX_BATCH_TOKENS")

    docker_args+=("$image")
    docker_args+=("${args[@]}")
    docker "${docker_args[@]}" >/dev/null
    echo "Started Docker TEI $profile profile in $container."
}

SIMILARITY_API_KEY=${TEI_SIMILARITY_API_KEY:-${TEI_API_KEY:-}}
CLUSTERING_API_KEY=${TEI_CLUSTERING_API_KEY:-${TEI_API_KEY:-}}

if [[ "$OS_NAME" == "Darwin" ]]; then
    if ! command -v text-embeddings-router >/dev/null 2>&1; then
        echo "Error: text-embeddings-router could not be found. Install TEI natively before running make tei-up."
        exit 1
    fi
    start_native similarity "$SIMILARITY_PORT" "$SIMILARITY_MODEL" "$SIMILARITY_REVISION" "$SIMILARITY_API_KEY"
    start_native clustering "$CLUSTERING_PORT" "$CLUSTERING_MODEL" "$CLUSTERING_REVISION" "$CLUSTERING_API_KEY"
else
    if ! command -v docker >/dev/null 2>&1; then
        echo "Error: docker could not be found."
        exit 1
    fi
    start_docker similarity "$SIMILARITY_PORT" "$SIMILARITY_MODEL" "$SIMILARITY_REVISION" "$SIMILARITY_API_KEY" "$SIMILARITY_CONTAINER"
    start_docker clustering "$CLUSTERING_PORT" "$CLUSTERING_MODEL" "$CLUSTERING_REVISION" "$CLUSTERING_API_KEY" "$CLUSTERING_CONTAINER"
fi

if [[ "${TEI_SKIP_HEALTHCHECK:-0}" != "1" ]]; then
    "${PYTHON:-python}" scripts/check_tei.py --wait
fi
