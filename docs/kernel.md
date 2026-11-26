# Kernel build, verification and boot-only update

The kernel workflow builds **stock, linux and containers** and compares stock →
linux → containers. Sources/compiler are pinned in config/sources.env. Builds
run on public x86-64 Ubuntu runners, with one compiler/linker thread, 32 GiB swap
and a cgroup memory limit so the runner survives full LTO. The successful
container compile took approximately 59 minutes; queue/download/comparison add
time. Ordinary main/containers pushes do not trigger the expensive kernel build.
Use workflow_dispatch or a deliberate `kernel-build-*` tag.

Artifacts expire after **7 days**. Save verified Image, Image.gz, vmlinux,
Module.symvers, kernel.config, release, SHA256SUMS and comparison reports to the
private recovery archive. A Git tag preserves the recipe, not the artifacts.
Generated signing keys must never be uploaded. Rebuilding can depend on package
versions available to the runner; no byte-identical rebuilt kernel is promised.

## Local, offline checks

Install Python 3.12+, pahole/dwarves and ordinary archive utilities on the laptop.
Fetch the small pinned tools independently of the kernel compiler/source:

```sh
python3 tools/fetch-tools.py boot
python3 tools/fetch-tools.py fastboot
python3 tools/fetch-tools.py upstream
```

For GitHub artifacts, verify the ZIP SHA-256 reported by GitHub **before**
extracting, then verify SHA256SUMS inside it. Do not treat a random downloaded
kernel as the tested build. The known public Image digest is in evidence/.

Using a complete local vendor capture, its JSON mapping of relative file paths
to SHA-256, the original running `/sys/kernel/btf/vmlinux`, the control build's
Module.symvers and the candidate artifact directory:

```sh
python3 tools/verify-vendor.py \
  --capture-root private/capture \
  --capture-manifest private/module-capture-sha256.json \
  --original-btf private/running-vmlinux.btf \
  --baseline-symvers artifacts/CONTROL/stock/Module.symvers \
  --candidate artifacts/CANDIDATE/containers \
  --panel-module private/moto_panel_off.ko \
  --output private/compat.json
python3 tools/boot_image.py \
  --original private/boot.before.img \
  --kernel-dir artifacts/CANDIDATE/containers \
  --compat-report private/compat.json --output private/boot.candidate.img
```

Omit `--panel-module` only if that custom module is not installed. This verifier
is intentionally restricted to the tested firmware's complete 399-file vendor
capture. Capture hashes establish file consistency, not independent provenance;
keep the original acquisition/build records. The checker compares imported CRCs,
module-provided exports, collisions, common structure sizes and critical member
layouts. It explicitly permits only the two SYSVIPC additions in reserved slots.
It does not prove unused vendor code paths or every private structure access.

The packer uses the phone's boot metadata, preserves header/footer properties
and checks the payload with the official unpacker and AVB verifier. It produces
an unsigned modified boot image for an **already unlocked** bootloader. Matching
the embedded AVB hash does not mean green verified boot or a matching signed
top-level vbmeta. Never relock the bootloader with this image installed.

## Explicit boot-only write

Save and verify boot/init_boot backups first. Enter bootloader deliberately, then:
Before entering it, confirm live firmware, active slot and module/capture identity
still match the private records. A saved profile is not evidence that an OTA or
another operator has not changed the phone.

```sh
python3 tools/phone.py --profile private/device.json fastboot-check
python3 tools/phone.py --profile private/device.json flash-boot \
  --image private/boot.candidate.img --image-report private/boot.candidate.json \
  --compat-report private/compat.json --restore-image private/boot.before.img \
  --restore-sha256 VERIFIED_BACKUP_SHA256
```

The private profile binds the serial, product, SKU, active slot, boot size and
fastboot binary digest. `flash-boot` checks the image against the compatibility
report and requires the saved restore image. It writes only that slot's boot
partition and **does not erase, switch slots or reboot automatically**. Do not
use it for stock-to-Debian provisioning or init_boot/rootfs changes.

After a confirmed successful write, reboot from the bootloader and verify the
new boot ID, expected main root, boot-partition readback hash, unchanged
init_boot, enabled config features, failed units, Wi-Fi/SSH, charge/thermal
services and panel behavior. Then run container/reboot tests. If boot fails,
return to bootloader and follow docs/recovery.md. No factory reset is needed for
a kernel rollback.
