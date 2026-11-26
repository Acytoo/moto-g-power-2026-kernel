# Native Debian details retained from the local installation

Use the pinned original port for the vendor module loader, property shim,
fuel-gauge daemon integration, Wi-Fi, thermal/charge guard and `vegasdisk` sources.
Fetching it does not include git submodules, phone captures or built binaries.
All private material must come from the target phone/firmware.

## Offline root preparation

`configure-rootfs.py` is the local migration configuration, parameterized for a
build directory, hostname and account. It runs as root **inside a disposable
ARM64 build VM**, against `BUILD/debian-root`, not against the live phone or the
laptop root. First use debootstrap/upstream Debian build to populate trixie and
install its runtime dependencies (systemd, SSH, sudo, rsync, kmod, Wi-Fi/network
tools, autossh, netcat-openbsd, the account shell, etc.). It does not perform that
bootstrap or unlock/flash any device. It refuses an already completed root.

Expected local inputs under `BUILD/rootfs-input/`:

- `overlay/`: the pinned upstream `linux/debian/overlay` runtime files.
- `kernel.release`, `modules/vendor_dlkm/`, `modules/vendor_ramdisk00/`.
- `login-authorized_keys`: the owner's existing login public key(s).
- `capture/account.private.json`: `passwd` and `shadow` records for the account
  being migrated; `capture/user-home.private.tar`: its home tree with numeric IDs.
- `capture/ssh/`: existing host keys when preserving this phone's identity.
- `capture/runtime/apex/`, `capture/runtime/ld.config.android.txt`: the captured
  Android linker/runtime closure required by vendor daemons.
- `capture/nvcfg_fg/` and `capture/nvram/`: this phone's captured daemon inputs.
  They are copied into ordinary Debian files; never written to NV partitions.
- `capture/wpa_supplicant-wlan0.conf`: owner-supplied Wi-Fi configuration.
- `capture/server/`: existing Xray executable/config and tunnel inputs, using
  the migration layout shown in the script. Keep credentials private.
- `BUILD/out/libpropshim.so`: build from upstream propshim with a generated
  private property header for this phone; check that it has no unexpected shared
  library dependencies. Do not publish the generated property header.

```sh
sudo python3 native/configure-rootfs.py --build-dir /path/to/disposable/build --hostname moto-server
```

This migration helper expects existing account/server captures. A fresh phone
without those captures should use upstream's initial rootfs build and provision
new local accounts/configuration explicitly. Do not fill in another phone's data.
The new generalized helper has not been rerun as a complete provisioning job.

After copying the root to pinned-file storage: role `main` on the 64 GiB root,
role `rescue` and the private `vegasdisk.conf` on the 3 GiB root. Keep
`vegas-bootok.service` enabled and the chooser's boot-failure counter operational.
The original migration used two `rsync -aHAXx --numeric-ids` passes, checked key
account/config files and sudo's root ownership/setuid mode, then ran offline
`e2fsck -fn` before publishing the mapping as the default root.

## Debian-default chooser

```sh
python3 tools/fetch-tools.py upstream
patch --batch --fuzz=0 -d work/upstream -p1 < patches/debian-default.patch
CC=aarch64-linux-gnu-gcc bash native/build-chooser.sh \
  work/upstream private/base.ramdisk.lz4 private/busybox-arm64 \
  private/chooser-debian-default debian-default
python3 tools/fetch-tools.py boot
python3 native/pack-init.py --original private/init_boot.original.img \
  --ramdisk private/chooser-debian-default/ramdisk.lz4 \
  --name chooser-debian-default --output private/init_boot.debian.img
```

Use `dry` first to exercise selection while always taking Android. The base
ramdisk is preserved byte-for-byte, with an appended lz4 legacy cpio overlay.
Our deployed base contained Magisk; upstream's KSU and stock-base assumptions are
different. Never substitute a random init_boot base. Packing verifies the v4
header, payload, partition size, AVB metadata and hash, but does not prove boot.

`DEFAULT_LINUX` changes only normal boot: no key selects Debian, Volume Up selects
Android. If the keypad cannot be read, select Android. Recovery/non-normal boot
also selects Android's init. The small-root rescue is selected by the installed
one-shot flag/counter mechanism. A timed-out initramfs rescue enters bootloader
for the Debian-default variant, avoiding a repeated default-Linux rescue loop.

## Headless runtime

The installed system uses `multi-user.target`, masks suspend/hibernate/sleep and
the automatic brightness restore, and disables Wi-Fi power saving. Keep upstream
fuel-gauge/charge/thermal services; the Android HALs are not managing Debian.
Use `runtime/display/` for the separately gated Tianma panel helper and read its
README before any build/install. It is not a generic panel-off driver.

Service templates under `runtime/services` preserve the separate unprivileged
`xray` and `moto-tunnel` accounts. Supply local configurations from `examples/`,
validate Xray with `xray run -test -config ...`, pin the relay host key and protect
identity/config files. For direct tunneling, omit ProxyCommand and remove the
optional Xray dependency. The relay must already permit the selected remote
listen address/port; do not alter its policy or open a relay shell implicitly.
