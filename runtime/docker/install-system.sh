#!/bin/bash
set -euo pipefail
account=${1:?Usage: sudo bash install-system.sh EXISTING_USER}
[[ $EUID == 0 && "$account" =~ ^[a-z_][a-z0-9_-]*$ ]]
uid=$(id -u "$account"); (( uid > 0 ))
[[ $(dpkg --print-architecture) == arm64 && $(cat /proc/1/comm) == systemd ]]
. /etc/os-release
[[ $ID == debian && $VERSION_CODENAME == trixie ]]
[[ $(stat -fc %T /sys/fs/cgroup) == cgroup2fs ]]
unshare --user --map-root-user --pid --fork --ipc true
for service in docker.service docker.socket containerd.service; do
 if systemctl is-active --quiet "$service"; then
  echo "Refusing to replace active system service: $service" >&2; exit 1
 fi
done
# Validate all ranges, including collisions with other accounts. Do not allocate
# ranges implicitly: changing an existing mapping changes file ownership meaning.
python3 "$(dirname "$0")/subids.py" "$account"
systemctl mask docker.service docker.socket containerd.service
install -d -m0755 /etc/apt/keyrings
key=$(mktemp); trap 'rm -f "$key"' EXIT
curl -fsSL --max-time 60 https://download.docker.com/linux/debian/gpg -o "$key"
install -m0644 "$key" /etc/apt/keyrings/docker.asc
cat > /etc/apt/sources.list.d/docker.sources <<'EOF'
Types: deb
URIs: https://download.docker.com/linux/debian
Suites: trixie
Components: stable
Architectures: arm64
Signed-By: /etc/apt/keyrings/docker.asc
EOF
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
 docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin \
 docker-ce-rootless-extras uidmap dbus-user-session slirp4netns fuse-overlayfs iptables
update-alternatives --set iptables /usr/sbin/iptables-legacy
update-alternatives --set ip6tables /usr/sbin/ip6tables-legacy
loginctl enable-linger "$account"
systemctl start "user@$uid.service"
echo 'System preparation complete. Reconnect by SSH as the target user and run install-user.sh.'
