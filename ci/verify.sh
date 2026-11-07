#!/usr/bin/env bash
# Запуск на доверенном self-hosted runner. Это не GitHub-hosted fallback.
# По умолчанию образ собирается из ci/Dockerfile.verify с frozen uv.lock.
# PLAYBOOK_VERIFY_IMAGE позволяет оператору указать уже принятый image.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
CONTAINER_RUNTIME="${CONTAINER_RUNTIME:-docker}"
IMAGE="${PLAYBOOK_VERIFY_IMAGE:-studio-ci-playbook-verify:local}"

command -v "$CONTAINER_RUNTIME" >/dev/null

if [[ -z "${PLAYBOOK_VERIFY_IMAGE:-}" ]]; then
  "$CONTAINER_RUNTIME" build --file "$ROOT/ci/Dockerfile.verify" --tag "$IMAGE" "$ROOT"
fi

"$CONTAINER_RUNTIME" run --rm \
  --network none \
  --read-only \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --user 65532:65532 \
  --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  --volume "$ROOT:/playbook:ro" \
  --workdir /playbook \
  "$IMAGE" \
  sh -eu -c '
    python3 scripts/check_playbook.py
    python3 -m unittest discover -s tests -v
  '

# Успех означает только статическую проверку документов. Он не подтверждает
# Gitea acceptance, Mermaid rendering, отсутствие секретов или production release.
