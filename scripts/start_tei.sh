#!/usr/bin/env bash
# Start Text Embeddings Inference (TEI) based on hardware/OS

set -euo pipefail

# Change to project root directory
cd "$(dirname "$0")/.."

# Load environment variables if .env exists. Never fallback to .env.example.
if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
fi

TEI_HOST_PORT=${TEI_HOST_PORT:-8080}

OS_NAME=$(uname -s)

echo "Detected OS: $OS_NAME"
echo "Preparing to start TEI..."

# Build common TEI arguments with a Bash array
common_tei_args=()

if [[ -n "${TEI_MODEL_ID:-}" ]]; then
    common_tei_args+=(--model-id "$TEI_MODEL_ID")
fi

if [[ -n "${TEI_REVISION:-}" ]]; then
    common_tei_args+=(--revision "$TEI_REVISION")
fi

if [[ -n "${TEI_TOKENIZATION_WORKERS:-}" ]]; then
    common_tei_args+=(--tokenization-workers "$TEI_TOKENIZATION_WORKERS")
fi

if [[ -n "${TEI_MAX_CLIENT_BATCH_SIZE:-}" ]]; then
    common_tei_args+=(--max-client-batch-size "$TEI_MAX_CLIENT_BATCH_SIZE")
fi

if [[ -n "${TEI_MAX_BATCH_TOKENS:-}" ]]; then
    common_tei_args+=(--max-batch-tokens "$TEI_MAX_BATCH_TOKENS")
fi

# Secret Handling (NEVER passed as arguments)
docker_env_args=()

if [[ -n "${TEI_API_KEY:-}" ]]; then
    export API_KEY="$TEI_API_KEY"
    docker_env_args+=(-e API_KEY)
fi

if [[ -n "${TEI_HF_TOKEN:-}" ]]; then
    export HF_TOKEN="$TEI_HF_TOKEN"
    docker_env_args+=(-e HF_TOKEN)
fi

if [ "$OS_NAME" = "Darwin" ]; then
    # Mac M-series natively using homebrew installation
    if ! command -v text-embeddings-router &> /dev/null; then
        echo "Error: text-embeddings-router could not be found. Please install via homebrew or cargo."
        exit 1
    fi
    echo "Running native TEI router on port $TEI_HOST_PORT..."
    
    # Native requires --port
    native_args=(${common_tei_args[@]+"${common_tei_args[@]}"} --port "$TEI_HOST_PORT")
    
    text-embeddings-router ${native_args[@]+"${native_args[@]}"}
else
    # Linux / AWS: Run via Docker
    if ! command -v docker &> /dev/null; then
        echo "Error: docker could not be found."
        exit 1
    fi
    
    GPU_ARG=()
    IMAGE="${TEI_IMAGE:-}"
    
    if command -v nvidia-smi &> /dev/null; then
        GPU_ARG=(--gpus all)
        echo "Running Dockerized TEI with GPU..."
        if [[ -z "$IMAGE" ]]; then
            echo "Error: TEI_IMAGE environment variable must be explicitly provided for GPU deployments."
            exit 1
        fi
    else
        echo "Running Dockerized TEI with CPU..."
        if [[ -z "$IMAGE" ]]; then
            IMAGE="ghcr.io/huggingface/text-embeddings-inference:cpu-1.5"
        fi
    fi

    # Docker publishes port but does not pass --port to container
    docker run -p "${TEI_HOST_PORT}:80" \
        ${GPU_ARG[@]+"${GPU_ARG[@]}"} \
        ${docker_env_args[@]+"${docker_env_args[@]}"} \
        "$IMAGE" \
        ${common_tei_args[@]+"${common_tei_args[@]}"}
fi
