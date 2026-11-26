# Agent handoff

Read README.md, docs/current-state.md and docs/reproduction.md first. The public
repository is a recipe and a sanitized record, not the phone's private workspace.

- Distinguish the tested 5.15.189 / firmware -4-3 setup from the original author's
  5.15.180 / -4-2 setup. An unchanged `uname -r` does not prove the old kernel is
  running; verify the boot payload/hash and enabled features.
- `evidence/tested-2026-11-25.json` records hardware tests of the original local
  implementation. Refactored portable tools are not automatically hardware-tested.
- Repository maintenance does not require connecting to or modifying the phone.
  For device work, use the user's existing authorization and private profile;
  never guess a serial, SSH key, active slot, partition size or recovery image.
- Do not log into a relay/VPS shell without an explicit request. A phone's
  forwarded SSH port and the relay's own SSH port are different destinations.
- Never publish private profiles, phone/SIM/network identifiers, credentials,
  captures, vendor binaries, boot images, root filesystems, or private logs.
  `private/`, `work/`, `artifacts/` and `dist/` stay ignored. Review staged content,
  not just filenames. No private inputs belong in CI secrets/caches/artifacts.
- Preserve compatibility gates. No forced module loads, silent config drift,
  guessed firmware downgrade, or bootloader relock with modified images.
- A kernel update writes only its explicitly selected boot partition. It does
  not require a wipe. Android factory reset destroys the pinned files backing
  the large Debian filesystem. Never discard/fstrim that mapping, or write NV,
  metadata, preloader, GPT or unrelated partitions as a recovery shortcut.
- Keep source attribution and license notices; the SYSVIPC patch is prior work.
- Validate changes with `python3 scripts/audit.py --working-tree`, Python unit
  tests, shell syntax checks and relevant offline checks. Never flash a phone
  merely to test documentation or refactoring. Record what was actually tested.
- Keep docs/current-state.md, evidence and troubleshooting consistent. Do not
  claim Android compatibility, another kernel/panel variant, or overnight
  stability based only on a short Debian boot test.

User instructions and authorization take precedence over repository workflow
preferences. Do not introduce repeated approval prompts for already authorized
steps. Publishing this repository is separate from uploading private recovery
material; the latter needs an explicitly chosen private destination.
