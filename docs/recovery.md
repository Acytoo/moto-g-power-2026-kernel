# Private recovery material and rollback

The public repository cannot recover device-specific data by itself. The
original local workspace contains verified root archives, boot/init_boot images,
mapping metadata and vendor captures. **This repository update does not upload
those files or create an off-laptop backup.** Choose an encrypted private storage
destination and verify a retrieval/decryption test separately.

## What the private bundle needs

Keep a manifest with filenames, lengths, SHA-256 hashes, capture dates, firmware
build and clear device association. Include:

- Current and previous known-good boot/init_boot images, original partition
  backups and acquisition/restore validation records.
- Main Debian root backup preserving numeric ownership, ACLs, xattrs, symlinks
  and setuid bits; the original small rescue-root backup; backup stderr/status.
- The private `vegasdisk.conf`, mapping allocation/extent records, original LP
  metadata and recovery scripts/notes. These are not transferable to another phone.
- Vendor module/config/BTF captures, Android runtime/property-shim inputs,
  Wi-Fi/gauge daemon inputs, and the exact tested kernel/module artifacts.
- Existing SSH host/login/tunnel keys and known_hosts, account/password-hash
  records, Wi-Fi and Xray/tunnel configuration. Keep decryption credentials
  separate from the encrypted bundle.
- The original private phone workspace and its historical stage scripts/logs
  where needed to reconstruct provisioning. Keep large compiler/source caches
  separately; they are downloadable and not substitutes for private captures.

Use an explicit list of inputs when archiving, then encrypt before storing off
the laptop, for example with `age`. Run from a directory containing a privately
reviewed `recovery/` tree; substitute the owner's actual recipient:

```sh
umask 077
set -o pipefail
tar --acls --xattrs --numeric-owner -cpf - recovery/ \
  | age -r AGE_RECIPIENT -o recovery.tar.age
sha256sum recovery.tar.age > recovery.tar.age.sha256
```

Do not upload a partial archive if tar/age failed. Avoid overwriting an existing
backup. Test decryption/listing privately and compare the manifest; an archive
existing on disk is not proof of a usable restore. Keep its hash beside the
ciphertext. Destination/upload credentials are supplied by the owner, not Git.

## Kernel failure, existing storage intact

Use the saved image from **this phone**, after verifying its hash. If Debian is
still reachable and the rollback kernel lacks container features, first stop
and disable its user Docker service. In the exact device's bootloader:

```sh
python3 tools/phone.py --profile private/device.json restore-boot \
  --image private/boot.before.img --sha256 VERIFIED_BACKUP_SHA256
```

This leaves init_boot and the root filesystem untouched. It sends no automatic
reboot; check that Writing boot_SLOT returned OKAY, then boot and verify. If
fastboot stalls, stop and inspect the partial output. The 37.0.3 `Fetching super`
problem was resolved with 37.0.1, not by wiping the phone.

## Main-root damage or a required wipe

First try the known-good kernel, then the existing small rescue Debian. A
one-shot `reboot-rescue` from the running main system selects it; it is not a
factory reset. Do not mount the same main filesystem writable twice.

Before extracting a root archive, boot rescue, verify the private mapping
identity, and mount the intended **offline main root**. Verify the archive and
available space; preserve ACLs/xattrs/numeric ownership during extraction. Check
fstab label, root-role, mapping config, SSH/account permissions, sudo setuid,
boot-success service and disabled fstrim before activating it. Run offline ext4
checks. These are operator checkpoints, not an automatic tar-to-`/` command.

If Android userdata has been wiped, `/data/vegas` and its old physical extents
are gone. Recreate/verify pinned files and a **new** mapping through the staged
storage procedure, then restore the filesystem and update the chooser/rescue
configuration. Restoring the old mapping file alone is unsafe. An Android reset
also does not restore the original boot/kernel images automatically.

The pre-container root archive was captured from a live system: tar reported a
changing journal file (exit 1). The archive structure, hash and critical account,
SSH/config files were validated. It is not an application-consistent database
snapshot. Stop stateful containers before taking future backups, or back up
their databases using their own consistent backup mechanism.
