# Rootless Docker

Prerequisite: native ARM64 Debian 13 with systemd and a compatible container
kernel. A chroot/proot or an unmodified Android kernel is not equivalent.

Copy/clone the repository onto the phone. The following changes Debian services
and installs packages; it does not build or flash a kernel:

```sh
sudo bash runtime/docker/install-system.sh YOUR_USER
# Reconnect by SSH as YOUR_USER so PAM creates the normal user session.
bash runtime/docker/install-user.sh
docker info
systemctl --user status docker
```

The system installer refuses active rootful Docker/containerd, masks their system
units, installs from Docker's official Debian repository, selects iptables-legacy
and enables linger. The tested versions are in evidence/tested-2026-11-25.json;
apt installs currently available versions, not a frozen Debian snapshot. It
requires an existing non-root account and valid subordinate UID/GID ranges.
If those are missing, select unused ranges with your account-management tools
before retrying; never blindly append a range already allocated to someone else.

The user installer checks required namespaces, mappings and runtime directory,
refuses differing existing service/config files, and starts the standard rootless
daemon. It uses the same systemd service arrangement as Docker's installer.
Motorola's module package lacks `modules.builtin`, causing the upstream installer
to misdetect built-in iptables. Our service keeps iptables enabled; it does not
use `--skip-iptables` or ignore firewall errors. Native overlay2 worked on this
kernel; fuse-overlayfs is installed as a possible fallback, not silently selected.

`systemctl status docker` refers to the intentionally masked **root** service.
For the installed daemon use, without sudo:

```sh
systemctl --user status docker
systemctl --user restart docker
journalctl --user -u docker -n 50
docker run --rm --memory=128m alpine:3.22 uname -m
docker compose version
```

Linger starts the user manager at boot and keeps it alive after logout. The
socket is `/run/user/UID/docker.sock`; data is under
`~/.local/share/docker`. Use ARM64 images. No x86 emulation or KVM was configured.
Memory limits and CPU weights work. CPU quotas (`--cpus`, `--cpu-quota`) and
process-count limits (`--pids-limit`) are unavailable with this kernel configuration.

## Validation

Run as the ordinary account:

```sh
bash runtime/docker/test-containers.sh
bash runtime/docker/test-build-compose.sh
```

These download small official images. The first leaves **only** the named test
container/volume `moto-container-check` for reboot testing, on loopback port 18080.
It refuses an existing container or volume with that name. Before reboot, record
its container ID and boot ID privately. After reboot, check the following from
a root management session **before logging in as the Docker user**:

```sh
systemctl is-active user@UID.service
curl -fsS http://127.0.0.1:18080/
```

The marker must be `moto-container-persistent-ok`; then as the user verify the
same container ID and active Docker service. Remove only the test resources:

```sh
docker rm -f moto-container-check
docker volume rm moto-container-check
```

Build/Compose tests clean up their own image, project and temporary directory.
Do not run these tests against a pre-existing similarly named project.

## Accessing a container remotely

Publishing a port does not add it to the existing SSH tunnel automatically.
For a service listening on phone loopback port 18080, use your existing SSH key:

```sh
ssh -N -L 18080:127.0.0.1:18080 PHONE_USER@RELAY_HOST -p PHONE_FORWARD_PORT
```

Open `http://127.0.0.1:18080` on the laptop while SSH remains connected. The
destination SSH endpoint is the phone, not a shell on the relay.
