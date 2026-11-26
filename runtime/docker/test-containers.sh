#!/bin/bash
set -euo pipefail
[[ -z ${DOCKER_HOST:-} && -z ${DOCKER_CONTEXT:-} ]] || { echo "Unset Docker endpoint overrides before proceeding" >&2; exit 1; }
[ "$(id -u)" -ne 0 ]
[ "$(docker context show)" = rootless ]
[ "$(docker context inspect rootless --format '{{.Endpoints.docker.Host}}')" = "unix:///run/user/$(id -u)/docker.sock" ]
docker info --format '{{json .SecurityOptions}}' | grep -q rootless
img=alpine:3.22
docker pull "$img"
[ "$(docker image inspect --format '{{.Architecture}}' "$img")" = arm64 ]
default_weight=$(docker run --rm --memory=128m --read-only "$img" cat /sys/fs/cgroup/cpu.weight)
# PID isolation, read-only root, effective memory cgroup, DNS and HTTPS.
docker run --rm --memory=128m --cpu-shares=512 --read-only -e DEFAULT_CPU_WEIGHT="$default_weight" "$img" sh -ec '
 test "$$" = 1
 test "$(cat /sys/fs/cgroup/memory.max)" = 134217728
 weight=$(cat /sys/fs/cgroup/cpu.weight)
 test "$weight" -gt 0
 test "$weight" -lt "$DEFAULT_CPU_WEIGHT"
 wget -q -O /dev/null https://example.com
 echo NATIVE_ARM64_NETWORK_MEMORY_CPU_WEIGHT_OK
'
# Keep a single disposable service across a reboot, to test persistence/startup.
! docker container inspect moto-container-check >/dev/null 2>&1
! docker volume inspect moto-container-check >/dev/null 2>&1
docker volume create moto-container-check
docker pull busybox:1.37
docker run -d --name moto-container-check --restart unless-stopped --memory=128m \
 -p 127.0.0.1:18080:8080 -v moto-container-check:/www busybox:1.37 sh -ec '
 test -e /www/index.html || echo moto-container-persistent-ok > /www/index.html
 exec httpd -f -p 8080 -h /www
'
for attempt in $(seq 1 20); do
 if curl -fsS http://127.0.0.1:18080/ | grep -qx moto-container-persistent-ok; then
  echo PORT_AND_VOLUME_OK
  exit 0
 fi
 sleep 1
done
exit 1
