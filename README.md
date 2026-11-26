# Moto G Power 2026: 5.15.189 kernel experiment

Build a control kernel and a Linux-userspace variant from the exact public source
revision recorded by the W1WEOS36.48-22-3-3-4-3 kernel. This is **not a complete
Debian port, a flashable image, or a claim of compatibility**.

The stock target uses the extracted stock configuration. The Linux target adds
devtmpfs, file handles, autofs, tmpfs ACLs (including their xattr dependency), and disables export trimming and GKI
module signature protection, following the referenced port. Android's normal
hardware/driver behavior still needs verification with our firmware.

## Run in GitHub Actions

Create an empty public or private GitHub repository and push only this project.
No fork of the larger phone-management repository is necessary. In **Actions**,
select **Build 5.15.189 control and Linux kernels**, then **Run workflow**.
Alternatively, deliberately push to the `ci-build` branch (the retry lane, allowing
public input caches to be reused), or push a `kernel-build-<name>` tag to start one
build. Main/ordinary branch pushes do not start builds; nothing publishes to Releases.
A new deliberate build on the same branch supersedes its older unfinished run.

Two Ubuntu 24.04 x86-64 jobs cross-compile ARM64 kernels in parallel. They fetch
immutable public source/compiler revisions, install build dependencies, reject
unexpected configuration drift, and produce explicitly selected artifacts.
A third job compares BTF structure layouts and export CRCs. Artifacts expire
after seven days. Private repositories consume Actions allowance/billable time.

Standard runners have limited disk space. A source archive avoids a full repo
checkout, and variants build in separate jobs. If disk space or RAM runs out,
inspect the failed job before selecting a larger runner or tuning concurrency.
The runner removes unused preinstalled SDKs, reserves 32 GiB of swap, and uses
one compiler job and one linker thread. A systemd service limits the whole build
to 13 GiB RAM and 28 GiB swap, leaving RAM for the Actions agent and diagnostics.
The stock optimization/debug settings remain intact. vmstat and peak resource
usage are included with success/failure diagnostics; these limits apply only to
the disposable CI VM. An earlier Linux build took 27 minutes with two compiler
jobs; the stock runner lost communication, so that is not a reliable estimate
for both variants or the current resource limits.

## Confidentiality boundary

CI receives only these tracked text files: generic source pins, configuration,
scripts, workflow, tests, and documentation. The kernel config is reviewed and
contains no device identity. Username, hostname, kernel suffix, and timestamp are
generic/public firmware values. A tracked-file allowlist and common-key-pattern
check run before builds; neither replaces human review of future changes.

Do not put phone captures, IMEI/serial records, partitions, vendor/NV data, Wi-Fi
credentials, SSH private keys, or proxy credentials in this repository, its
secrets, caches, logs, or artifacts. Never copy the phone-management workspace
here. No GitHub secret is needed. No ADB/fastboot, VPS login, or flashing occurs.

Only kernel outputs are uploaded; generated module-signing private keys remain
in the ephemeral build workspace. Only downloaded public source/compiler trees
are cached, before compilation. No workspace-wide artifact upload or cache is
used. Artifacts in a public repository must be treated as public.

## What a passing build establishes

- Source and compiler are pinned; configuration changes are explicit.
- Stock/modified builds have comparable exported-symbol CRCs and selected BTF
  member layouts, with all common struct/union sizes compared.
- Output checksums, configs, compiler version, logs and vmlinux are available.

It does **not** establish stock binary reproducibility, complete ABI compatibility,
vendor module loadability, bootloader acceptance, hardware safety, or working
Wi-Fi/charging/thermal behavior. The stock export whitelist is reconstructed from
the pinned upstream GKI lists; any difference from the manufacturer's build must
be investigated locally. Tool-version-only config differences are reported.

## Local steps after CI

1. Verify downloaded SHA256SUMS; compare the control Image/config/BTF with stock.
2. Check the phone's original vendor module imports against both Module.symvers
   files, including module-to-module dependencies, signatures, and CFI constraints.
3. Derive boot image headers/footer placement from this firmware, not -4-2 constants.
4. Confirm fastboot and the exact restore procedure work before any experimental flash.
5. Test the kernel/initramfs independently before adding Debian or changing super.

Device captures and all final per-phone assembly remain on the laptop. A green
Actions run never authorizes flashing. Hardware has not been tested with this build.

See NOTICE.md for upstream sources and licensing.

## Container experiment

The `containers` branch adds a third build, based on the existing Linux variant:
PID/IPC/user namespaces, SysV IPC, POSIX message queues, and the iptables addrtype
match. Rootless Docker/Podman is the target; no hardware virtualization is used.
SYSVIPC fields occupy task_struct's reserved ABI slots 6-8. The comparison checks
all existing selected member offsets and types, allows only those two additions
inside the exact reserved space, and still rejects structure-size/export changes.
Local checks against this phone's actual vendor modules remain mandatory.

Memory control is present. CPU quotas (CFS_BANDWIDTH) and the pids controller are
intentionally absent: they change the vendor ABI. Do not advertise those limits
or force-load vendor modules. Runtime compatibility remains untested until a
successful phone boot and container tests. No wipe or root filesystem replacement
is planned; a boot_a-only trial preserves both Debian and Android data.
