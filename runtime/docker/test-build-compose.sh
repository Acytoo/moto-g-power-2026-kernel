#!/bin/bash
set -euo pipefail
[[ -z ${DOCKER_HOST:-} && -z ${DOCKER_CONTEXT:-} ]] || { echo "Unset Docker endpoint overrides before proceeding" >&2; exit 1; }
[ "$(id -u)" -ne 0 ]
[ "$(docker context show)" = rootless ]
[ "$(docker context inspect rootless --format '{{.Endpoints.docker.Host}}')" = "unix:///run/user/$(id -u)/docker.sock" ]
[ -z "$(docker ps -aq --filter label=com.docker.compose.project=moto-build-check)" ]
! docker network inspect moto-build-check_default >/dev/null 2>&1
! docker image inspect moto-container-build-check:local >/dev/null 2>&1
mkdir -p "$HOME/.cache"
work=$(mktemp -d "$HOME/.cache/moto-build-check.XXXXXXXX")
cleanup() {
 docker compose -p moto-build-check -f "$work/compose.yaml" down >/dev/null 2>&1 || true
 docker image rm moto-container-build-check:local >/dev/null 2>&1 || true
 rm -rf -- "$work"
}
trap cleanup EXIT
cat > "$work/Dockerfile" <<'EOF'
FROM alpine:3.22
RUN printf '%s\n' moto-build-and-compose-ok > /build-marker
CMD ["cat", "/build-marker"]
EOF
cat > "$work/compose.yaml" <<'EOF'
services:
  check:
    image: moto-container-build-check:local
    read_only: true
    mem_limit: 128m
EOF
docker build --tag moto-container-build-check:local "$work"
docker compose -p moto-build-check -f "$work/compose.yaml" run --rm -T check </dev/null | grep -qx moto-build-and-compose-ok
echo BUILD_AND_COMPOSE_OK
