# Tested installation and handoff

Last hardware verification: **2026-11-25**. Model XT2617V (`vegas`, MT6835),
firmware `W1WEOS36.48-22-3-3-4-3`. One phone has been tested; this is not a
universal image or a guarantee for other firmware/panel variants.

This record describes the test phone that was migrated to native Debian. Earlier
Android/chroot experiments and other phones in the owner's collection are separate
installations. Always select the target using private identity records. Native
Debian shares no Android userspace; rootless containers share the native Linux
kernel. No KVM or CPU emulation was added by this work.

## Boot and storage

- Unlocked bootloader; native Debian 13 ARM64 is the normal boot default.
- Kernel build [45735333885](https://github.com/Acytoo/moto-g-power-2026-kernel/actions/runs/45735333885),
  recipe commit `46154406457f3e38f5793709415840194748e54d`, containers variant.
- Kernel release stays `5.15.189-android13-8-00018-g9c82b71884fd-ab14885418` for
  vendor compatibility. This is a rebuilt kernel with added features, not a
  newer upstream kernel. See the public Image hash in the evidence manifest.
- The container upgrade wrote **boot_a only**, retained init_boot and all data,
  and passed boot-partition readback plus a second normal reboot.
- Main root: ext4 `/dev/mapper/vegas-disk`, label `vegas-root2`, approximately
  64 GiB reserved in pinned F2FS files under Android `/data/vegas`.
- Original 3 GiB `linux` logical partition remains the rescue filesystem. The
  installed `reboot-rescue` selects it for one boot; normal reboot returns main.
- The mapping anchor/UUID, boot images and capture manifests are private,
  per-device inputs. They cannot be reconstructed from this repository alone.
- Android factory reset removes the main Debian storage. fstrim is masked on
  both roots. Android's encrypted files are not normally browsable from Debian;
  the Debian filesystem itself is not encrypted.

## Runtime

Docker Engine 29.10.1 runs as an ordinary user (the tested account was `bz`, UID
60000), using a systemd **user** service, linger, cgroup v2, native overlay2,
RootlessKit/slirp4netns and iptables-legacy. System-wide Docker/containerd units
are masked. Run `systemctl --user status docker` and `docker` without sudo.
The original subordinate UID/GID range was `100000:65536`; new hosts must choose
and validate their own non-overlapping range.

Verified: ARM64 execution, PID isolation, DNS/HTTPS, memory limits, relative CPU
weights, loopback port publishing, named volumes, BuildKit, Compose and reboot
autostart before a user login. All disposable test containers/volumes were removed.
Hard CPU quotas and per-container process-count limits remain unavailable.
CPU affinity and block-I/O controls are not delegated in the tested user service.

SSH listens on 22 and 8022; key-only authentication is configured. The existing
remote path is a reverse SSH tunnel through local Xray SOCKS. The templates also
allow a direct tunnel. Xray is not configured as a transparent VPN for every
process/container; only explicitly proxied traffic uses it. Its
identity, hostname and ports belong in the private profile. No relay shell login
is needed to operate the phone. Wi-Fi power saving and suspend are disabled for
this headless server. Native Debian does not run Android Doze.

Charge target 70–80%, fuel-gauge and thermal services are enabled. A small local
module calls the bound Tianma ILI77600A panel driver's disable/unprepare methods;
the service leaves an attempt marker on failure to avoid automatic crash loops.
Backlight zero alone is not evidence that the whole panel is powered down.

## Evidence and remaining uncertainty

The build and local compatibility checks covered 399 vendor module files,
18,663 imports from the kernel, 10,509 common structure names, selected member
layouts and the panel helper's eight imports. No checked mismatch was found.
This is substantial evidence, not proof of every proprietary driver code path.
See [the sanitized manifest](../evidence/tested-2026-11-25.json).

The earlier minimal Linux kernel was tested with Android. **Android boot with
the new container kernel has not been tested.** Physical Volume-Up selection in
the final Debian-default chooser and long-duration/overnight reliability also
remain unverified. The Android branch of the chooser was previously tested with
its dry variant. Rescue/main roundtrip was tested before the container upgrade.

The Docker setup and boot-image helpers in this repository are portable
refactorings of the tested local scripts. Offline verification is recorded in
docs/validation.md; this repository update does not rerun destructive provisioning.
