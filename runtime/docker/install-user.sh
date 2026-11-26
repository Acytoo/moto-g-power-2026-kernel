#!/bin/bash
set -euo pipefail
[[ -z ${DOCKER_HOST:-} && -z ${DOCKER_CONTEXT:-} ]] || { echo "Unset Docker endpoint overrides before proceeding" >&2; exit 1; }
here=$(cd "$(dirname "$0")" && pwd)
uid=$(id -u)
[[ $uid != 0 && ${XDG_RUNTIME_DIR:-} == "/run/user/$uid" ]]
[[ $(stat -c %u "$XDG_RUNTIME_DIR") == "$uid" ]]
[[ $(cat /proc/1/comm) == systemd && $(stat -fc %T /sys/fs/cgroup) == cgroup2fs ]]
unshare --user --map-root-user --pid --fork --ipc true
python3 "$here/subids.py" "$(id -un)"
for helper in /usr/bin/newuidmap /usr/bin/newgidmap; do
 [[ $(stat -c '%u:%a' "$helper") == 0:4755 ]]
done
/usr/sbin/iptables --version | grep -q legacy
systemctl --user show-environment >/dev/null
install -d -m0700 "$HOME/.config/systemd/user" "$HOME/.config/docker"
install_same() {
 local src=$1 dst=$2
 if [[ -e $dst || -L $dst ]]; then
  [[ ! -L $dst ]] && cmp -s "$src" "$dst" || {
   echo "Existing configuration differs; review before replacing: $dst" >&2; exit 1;
  }
 else install -m0600 "$src" "$dst"; fi
}
# Check both files before changing either.
for pair in 'docker.service .config/systemd/user/docker.service' 'daemon.json .config/docker/daemon.json'; do
 read -r src rel <<< "$pair"
 if [[ -e $HOME/$rel || -L $HOME/$rel ]]; then
  [[ ! -L $HOME/$rel ]] && cmp -s "$here/$src" "$HOME/$rel" || {
   echo "Existing configuration differs: $HOME/$rel" >&2; exit 1;
  }
 fi
done
install_same "$here/docker.service" "$HOME/.config/systemd/user/docker.service"
install_same "$here/daemon.json" "$HOME/.config/docker/daemon.json"
dockerd --validate --config-file "$HOME/.config/docker/daemon.json"
if docker context inspect rootless >/dev/null 2>&1; then
 [[ $(docker context inspect rootless --format '{{.Endpoints.docker.Host}}') == "unix://$XDG_RUNTIME_DIR/docker.sock" ]]
else
 docker context create rootless --docker "host=unix://$XDG_RUNTIME_DIR/docker.sock"
fi
systemctl --user daemon-reload
systemctl --user enable --now docker.service
docker context use rootless
docker info
