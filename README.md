# Moto G Power 2026: native Debian and rootless Docker

A reproducible kernel recipe and operational handoff for the XT2617V (`vegas`,
MT6835). The tested phone runs native Debian 13 ARM64, a 64 GiB main root,
headless power management and rootless Docker under a systemd user service.
The kernel update preserved the filesystem; no wipe was needed.

**Tested:** firmware `W1WEOS36.48-22-3-3-4-3`, kernel 5.15.189, one phone.
Android boot with the container kernel and long-duration stability are **untested**.
The public tree contains source/configuration/docs, not firmware, vendor captures,
credentials, phone images or a universal ready-to-flash installer.

## Start here

- [Agent instructions](AGENTS.md) — required context for continuing the work.
- [Current state](docs/current-state.md) and [sanitized evidence](evidence/tested-2026-11-25.json).
- [Reproduction](docs/reproduction.md) — another laptop versus a stock replacement phone.
- [Kernel build and boot-only update](docs/kernel.md).
- [Docker installation and operation](docs/docker.md).
- [Native Debian configuration/chooser](native/README.md).
- [Private backups and recovery](docs/recovery.md).
- [Troubleshooting](docs/troubleshooting.md) and [validation of these portable tools](docs/validation.md).
- [Source attribution](NOTICE.md).

## What is here

`config/`, `patches/`, `scripts/` and the kernel workflow build stock, minimal Linux
and container variants from pinned public sources/compiler. The container variant
adds user/PID/IPC namespaces and a credited SYSVIPC reserved-space patch. Export
CRC and BTF checks reject unexplained incompatibility. CPU quotas and PID-count
limits remain disabled to preserve the stock vendor ABI.

`tools/` contains pinned public-tool downloads, a local vendor compatibility
checker, offline boot packaging and an exact-device boot-only CLI driven by an
ignored private profile. `native/` preserves the customized rootfs/chooser recipe.
`runtime/` contains Docker, tunnel/proxy, headless and panel-helper source/templates.
`examples/` contains placeholders only. No tool needs a hardcoded laptop home path.

For a laptop already managing the installed phone:

```sh
# Populate this privately from the owner's existing connection/recovery records.
mkdir -p private
chmod 700 private
cp examples/device.example.json private/device.json
chmod 600 private/device.json
# Edit the placeholders, then perform a read-only check:
python3 tools/phone.py --profile private/device.json status
```

## CI and reproducibility

Normal pushes/PRs run lightweight publication and helper checks. To rebuild the
kernels, use the kernel workflow's **Run workflow** action, push to `ci-build`, or
push a deliberate `kernel-build-*` tag. Three Ubuntu 24.04 jobs build independently;
a fourth compares their outputs. The successful container compile took about
59 minutes. Artifacts expire after **7 days**; preserve verified outputs privately.
Source/compiler pins and the historical tested commit remain available in Git.

A passing CI run is not a hardware compatibility guarantee. Complete local vendor
checks, exact-device identification, backups, image validation and staged hardware
tests still apply. Portable refactoring was validated offline; we did not repeat
stock-to-Debian provisioning just to publish this handoff.

## Publication boundary

Only explicitly allowlisted text files are tracked. The audit checks Git index
blobs during CI/publication, with an optional working-tree check before staging.
It detects common credentials and binaries; it is a backstop, not a replacement
for reviewing the diff. Device profiles, captures, backups and build outputs stay
under ignored private/work/artifacts/dist directories. CI receives no phone keys,
Wi-Fi/proxy credentials, vendor/NV files or device identifiers. Only selected
public kernel outputs are uploaded; generated signing keys remain on the runner.

A second laptop can reconstruct the tools from Git. Recovering this exact phone
also requires its separately protected private bundle; see the recovery document.
