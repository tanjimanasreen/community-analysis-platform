#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SCRIPT="$ROOT/scripts/start_tei.sh"
TEMP_BIN=$(mktemp -d)
LOG=$(mktemp)
NATIVE_LOG=$(mktemp)
RUNTIME_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_BIN" "$LOG" "$NATIVE_LOG" "$RUNTIME_DIR"' EXIT
export PATH="$TEMP_BIN:$PATH"
export MOCK_DOCKER_LOG="$LOG"
export TEI_SKIP_HEALTHCHECK=1

cat > "$TEMP_BIN/uname" <<'SH'
#!/usr/bin/env bash
echo "${MOCK_OS:-Linux}"
SH
cat > "$TEMP_BIN/docker" <<'SH'
#!/usr/bin/env bash
printf '%q ' "$@" >> "$MOCK_DOCKER_LOG"
printf '\n' >> "$MOCK_DOCKER_LOG"
# docker ps should report no pre-existing containers in launcher tests
if [[ "${1:-}" == "ps" ]]; then exit 0; fi
exit 0
SH
chmod +x "$TEMP_BIN/uname" "$TEMP_BIN/docker"

rm -f "$TEMP_BIN/nvidia-smi"
MOCK_OS=Linux \
TEI_SIMILARITY_HOST_PORT=8080 \
TEI_CLUSTERING_HOST_PORT=8081 \
TEI_SIMILARITY_MODEL_ID=sentence-transformers/paraphrase-MiniLM-L6-v2 \
TEI_CLUSTERING_MODEL_ID=sentence-transformers/all-MiniLM-L6-v2 \
  "$SCRIPT" >/tmp/tei-launch-test.out 2>&1

grep -q -- '--name community-analysis-tei-similarity' "$LOG"
grep -q -- '-p 8080:80' "$LOG"
grep -q -- '--model-id sentence-transformers/paraphrase-MiniLM-L6-v2' "$LOG"
grep -q -- '--revision c9a2bfebc254878aee8c3aca9e6844d5bbb102d1' "$LOG"
grep -q -- '--name community-analysis-tei-clustering' "$LOG"
grep -q -- '-p 8081:80' "$LOG"
grep -q -- '--model-id sentence-transformers/all-MiniLM-L6-v2' "$LOG"
grep -q -- '--revision 1110a243fdf4706b3f48f1d95db1a4f5529b4d41' "$LOG"

# Backward-compatible similarity variables remain honored; clustering stays independent.
: > "$LOG"
MOCK_OS=Linux TEI_HOST_PORT=9000 TEI_MODEL_ID=legacy/similarity-model \
  "$SCRIPT" >/tmp/tei-launch-test.out 2>&1
grep -q -- '-p 9000:80' "$LOG"
grep -q -- '--model-id legacy/similarity-model' "$LOG"
grep -q -- '-p 8081:80' "$LOG"


# macOS starts two native routers in the background with separate ports/models.
cat > "$TEMP_BIN/text-embeddings-router" <<'SH'
#!/usr/bin/env bash
printf '%q ' "$@" >> "$MOCK_NATIVE_LOG"
printf '\n' >> "$MOCK_NATIVE_LOG"
sleep 2
SH
chmod +x "$TEMP_BIN/text-embeddings-router"
export MOCK_NATIVE_LOG="$NATIVE_LOG"
: > "$NATIVE_LOG"
MOCK_OS=Darwin TEI_RUNTIME_DIR="$RUNTIME_DIR" "$SCRIPT" >/tmp/tei-launch-test.out 2>&1
grep -q -- '--model-id sentence-transformers/paraphrase-MiniLM-L6-v2 --port 8080 --revision c9a2bfebc254878aee8c3aca9e6844d5bbb102d1' "$NATIVE_LOG"
grep -q -- '--model-id sentence-transformers/all-MiniLM-L6-v2 --port 8081 --revision 1110a243fdf4706b3f48f1d95db1a4f5529b4d41' "$NATIVE_LOG"
MOCK_OS=Darwin TEI_RUNTIME_DIR="$RUNTIME_DIR" bash "$ROOT/scripts/stop_tei.sh" >/tmp/tei-stop-test.out 2>&1

# Secrets are passed only by environment name, never as a literal docker argument.
: > "$LOG"
MOCK_OS=Linux TEI_API_KEY=super_secret_key "$SCRIPT" >/tmp/tei-launch-test.out 2>&1
grep -q -- '-e API_KEY' "$LOG"
if grep -q 'super_secret_key' "$LOG"; then
  echo 'Secret value leaked into docker CLI arguments' >&2
  exit 1
fi

echo 'All dual-profile TEI launcher tests passed!'
