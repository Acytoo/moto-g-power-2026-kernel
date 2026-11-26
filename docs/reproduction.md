# Reproducing or continuing the setup

There are two starting points. A second laptop managing the existing phone only
needs this repository, the owner's existing SSH credentials/profile, and USB or
forwarded SSH access. A stock replacement phone additionally needs its own
firmware, captures, backups and staged provisioning. Never clone another phone's
NV data, storage mapping, identity or keys into it.

## Another laptop, existing phone

1. Clone this repository and read AGENTS.md and docs/current-state.md.
2. Retrieve the encrypted private recovery bundle through the owner's chosen
   private channel. See docs/recovery.md. Keep plaintext under ignored `private/`.
3. Copy `examples/device.example.json` to `private/device.json`, populate it from
   the private records, and protect it with mode 600. Paths are relative to the
   profile unless absolute. Reuse the owner's normal login key. Do not invent a
   new key or SSH alias, or silently trust a new host key.
4. For USB Ethernet, the phone uses `172.16.42.1/24`. Configure the corresponding
   laptop interface as `172.16.42.2/24`, without a default route or DNS override.
   Interface names differ across laptops. Validate the USB serial first.
5. Run `python3 tools/phone.py --profile private/device.json status`. This is a
   read-only SSH check with a pinned known-hosts file. No relay shell is accessed.
6. As the ordinary account, check `docker info`, `systemctl --user status docker`
   and `journalctl --user -u docker`. Use the existing forwarded SSH command or
   USB address directly. See docs/docker.md for tests and port forwarding.

## Stock phone: checkpoints, not a blind flash sequence

The original port is pinned to commit
`308a30f948ac7664c5df1ad3ad98dcb99039b24b` of
[dingyifei/gpower26-cluster-pub](https://github.com/dingyifei/gpower26-cluster-pub).
`python3 tools/fetch-tools.py upstream` fetches that public tree into ignored
`work/upstream`. Its README, CONTRIBUTING.md, linux/README.md and
docs/linux-on-vegas.md contain the base procedures. Our tested -4-3 firmware and
5.15.189 source differ from its -4-2 / 5.15.180 recipe; do not reuse its build pins
or firmware-specific boot-image constants blindly.

The working sequence was:

1. Establish authorized ADB/root access and unlocked bootloader on the identified
   phone. Carrier unlocking/firmware downgrade is not necessary to repeat a
   kernel-only update. Stock activation, root and unlock prerequisites are in the
   upstream runbook; they are not automated by this repository.
2. Capture original boot/init_boot/vbmeta metadata, module files, live kernel
   config/BTF and required Android vendor runtime/Wi-Fi/gauge data **locally**.
   Record source/build and per-file hashes. Back up before writes; confirm a
   bootloader restore route. Preserve account/SSH state when migrating an existing
   Linux installation. None of these captures enter Git or CI.
3. Build stock and minimal Linux variants, compare config/export CRCs/BTF, then
   check against the phone's actual vendor modules. Upstream `linux/tools/modcrc.py`
   and this repo's `scripts/compare.py` are parts of that gate. Include
   module-to-module exports and collisions when inspecting unresolved symbols.
   See docs/kernel.md and the tested evidence; compiler success alone is insufficient.
4. Repackage using metadata from this phone's original images. Test a packaging
   control, original-image restore and minimal Linux kernel before adding Debian.
   The v4 boot image has no ramdisk; init_boot carries it separately. This phone
   requires **lz4 legacy** init_boot; gzip was silently ignored.
5. Build an ARM64 Debian trixie root using the pinned upstream Debian recipe and
   the captured vendor/runtime material. Stock `/lib/modules` alone is insufficient
   for the Android Wi-Fi/fuel-gauge userspace. Our configuration choices and exact
   migration details are in native/README.md. An ARM64 build VM was used locally;
   kernel cross-compilation runs on GitHub's x86-64 runners.
6. Verify fastbootd entry/exit without metadata changes. Create the new 3 GiB
   `linux` logical partition only after validating all copies of LP metadata,
   free extents and no OTA snapshot. Preserve every existing partition extent.
   Flash only that new partition and verify full readback. These provisioning
   operations are still upstream/manual stages, not covered by the boot-only CLI.
7. Build/test a dry chooser first. Apply `patches/debian-default.patch` to the
   pinned upstream tree for Debian-default behavior. `native/build-chooser.sh`
   packages the local base ramdisk plus an overlay; it performs no flashing.
   Stage the final chooser only after USB SSH and Debian boot are proven.
8. Expand storage using upstream `vegasdisk`: prove Android↔Debian pattern
   roundtrips on a disposable 256 MiB pinned-file mapping, including Android
   maintenance; then allocate 64 GiB plus Android free-space headroom. Verify
   extents, bounds, canaries and mapping identity. Copy the rescue root with
   `rsync -aHAXx --numeric-ids`, make ext4 with `-E nodiscard -O ^orphan_file`,
   install the main/rescue roles and boot-success/failure-counter logic, mask
   fstrim on both roots, then verify rescue/main roundtrip. Keep mapping metadata
   private. Do not format raw userdata or guess an anchor/UUID.
9. Add the container variant only after the minimal port is stable. Back up,
   verify against the current captures, package and flash boot only. Then follow
   docs/docker.md, validate the original services, reboot and retest.

The repository preserves the recipe, source changes and tested state. It does
not claim that a new phone can be provisioned unattended, or that a bare clone
contains the vendor captures and private recovery material required to do so.
