#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
TEI_SCRIPT="$SCRIPT_DIR/scripts/start_tei.sh"

# We will create a temporary bin directory to mock commands
TEMP_BIN=$(mktemp -d)
trap 'rm -rf "$TEMP_BIN"' EXIT

export PATH="$TEMP_BIN:$PATH"

# Mock uname to control OS
cat << 'EOF' > "$TEMP_BIN/uname"
#!/usr/bin/env bash
if [[ -n "${MOCK_OS:-}" ]]; then
    echo "$MOCK_OS"
else
    /usr/bin/uname "$@"
fi
EOF
chmod +x "$TEMP_BIN/uname"

# Mock text-embeddings-router
cat << 'EOF' > "$TEMP_BIN/text-embeddings-router"
#!/usr/bin/env bash
echo "text-embeddings-router called with: $@"
EOF
chmod +x "$TEMP_BIN/text-embeddings-router"

# Mock docker
cat << 'EOF' > "$TEMP_BIN/docker"
#!/usr/bin/env bash
echo "docker called with: $@"
EOF
chmod +x "$TEMP_BIN/docker"

# Mock nvidia-smi will be created dynamically inside run_test based on MOCK_HAS_GPU

run_test() {
    local name="$1"
    local setup="$2"
    local expected="$3"
    local not_expected="${4:-}"

    echo "Running test: $name"

    # Run in a subshell so env vars don't leak
    local output
    output=$(bash -c "
        $setup
        if [[ \"\${MOCK_HAS_GPU:-}\" == \"1\" ]]; then
            cat << 'EOF_MOCK' > "$TEMP_BIN/nvidia-smi"
#!/usr/bin/env bash
exit 0
EOF_MOCK
            chmod +x "$TEMP_BIN/nvidia-smi"
        else
            rm -f "$TEMP_BIN/nvidia-smi"
        fi
        \"$TEI_SCRIPT\" 2>&1 || true
    ")

    if ! echo "$output" | grep -q "$expected"; then
        echo "FAIL: $name"
        echo "Expected output to contain: $expected"
        echo "Actual output:"
        echo "$output"
        exit 1
    fi

    if [[ -n "$not_expected" ]] && echo "$output" | grep -q -e "$not_expected"; then
        echo "FAIL: $name"
        echo "Expected output NOT to contain: $not_expected"
        echo "Actual output:"
        echo "$output"
        exit 1
    fi

    echo "PASS"
}

run_test "macOS native launch" \
    "export MOCK_OS=Darwin; export TEI_HOST_PORT=9000; export TEI_API_KEY=secret_mac" \
    "text-embeddings-router called with.*--port 9000"

run_test "macOS passes optional args" \
    "export MOCK_OS=Darwin; export TEI_REVISION=main" \
    "text-embeddings-router called with.*--revision main.*--port" \
    "--api-key"

run_test "Linux CPU launch uses default image" \
    "export MOCK_OS=Linux; export MOCK_HAS_GPU=0" \
    "docker called with: run -p 8080:80 ghcr.io/huggingface/text-embeddings-inference:cpu-1.5" \
    "--gpus all"

run_test "Linux GPU launch fails if image unset" \
    "export MOCK_OS=Linux; export MOCK_HAS_GPU=1" \
    "Error: TEI_IMAGE environment variable must be explicitly provided for GPU deployments."

run_test "Linux GPU launch succeeds if image set" \
    "export MOCK_OS=Linux; export MOCK_HAS_GPU=1; export TEI_IMAGE=ghcr.io/huggingface/text-embeddings-inference:turing-1.5" \
    "docker called with: run -p 8080:80 --gpus all ghcr.io/huggingface/text-embeddings-inference:turing-1.5"

run_test "Docker sets API_KEY correctly" \
    "export MOCK_OS=Linux; export MOCK_HAS_GPU=0; export TEI_API_KEY=super_secret_key" \
    "-e API_KEY" \
    "super_secret_key" # The mock just echoes the args, which shouldn't contain the secret value directly in CLI args

echo "All start_tei.sh launcher tests passed!"
