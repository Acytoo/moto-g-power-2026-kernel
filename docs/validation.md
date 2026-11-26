# Handoff validation, 2026-11-25

Historical hardware results are recorded separately in
`evidence/tested-2026-11-25.json`. This repository update did not reflash or
reconfigure the phone.

Checks performed on the portable refactoring:

- 14 Python tests passed, including existing config/BTF gates plus rejection of
  overlapping subordinate ranges, placeholder/loosely protected device profiles,
  wrong-slot or ambiguous fastboot identity, changed tool-download digests, and
  a staged secret concealed by a clean working-tree file.
- Python compilation and shell syntax checks passed.
- The portable vendor checker passed on the existing private 399-file capture,
  original BTF and container artifacts, including the installed panel module.
- `tools/boot_image.py` reproduced the deployed 64 MiB container boot image
  byte-for-byte, SHA-256
  `580fc094c927593f7707f69b2bf8d89d22c5df656e0c83a18054190aa69d64fa`.
- `native/pack-init.py`, using the existing saved ramdisk/metadata, reproduced the
  deployed init_boot image byte-for-byte. All comparison inputs/outputs stayed
  local under ignored work/private directories.
- The Debian-default patch applied without fuzz to the pinned upstream revision;
  the resulting chooser/init.linux matched the source used for the installation.
  The chooser passed a host C syntax check. A fresh ARM64 chooser build was not
  performed during this publication task.
- Pinned official Android packaging tools matched their saved hashes. The pinned
  avbtool from Android's immutable release tag is identical to the earlier local
  tool. The pinned upstream archive and fastboot download checksums were verified.

The Docker service/config matches the tested arrangement. The generalized
installers and boot CLI have offline checks; their parameterization is not a
claim of a second fresh-phone provisioning run. The rootfs migration helper was
syntax-reviewed, not executed against a new root filesystem in this task.

The publication audit checks **Git index blobs**, so an unstaged clean file
cannot conceal a staged secret. A fixed tracked-file manifest, binary/key-pattern
rejection, explicit diff review and a private-value scan supplement one another.
The lightweight CI workflow repeats the audit, unit tests and syntax checks.
