# Findings from this installation

| Symptom | Finding and next check |
|---|---|
| `systemctl status docker` says masked | Expected: that is the root system unit. As the Docker account use `systemctl --user status docker`. Linger supplies boot startup without login. |
| Kernel release looks unchanged | Intentional vendor-compatible release string. Check the boot payload/hash, `/proc/config.gz`, namespaces and build evidence. |
| fastboot flash stalls at `Fetching super` | Host upgrade to 37.0.3 introduced this behavior in our run before boot_a was sent. Google's 37.0.1 wrote the 64 MiB image in 1.7 s. This is an observed workaround, not proof of the underlying USB cause. |
| Fastboot device listed but getvar times out | USB enumeration alone does not prove command transport. Stop parallel commands; reconnect or restart into bootloader if needed, then repeat read-only gates. Never wipe as a USB fix. |
| Hello Moto remains/dark screen; no ADB | Native Debian does not run Android ADB. Check USB Ethernet/SSH. Low backlight is different from complete panel powerdown. |
| Kernel boots but init_boot overlay is ignored | This bootloader needs lz4 legacy; gzip init_boot was silently dropped. Preserve the base ramdisk and validate packing. |
| Docker installer reports missing ip_tables | Vendor module package lacks modules.builtin although iptables is built-in. Use the documented user unit with legacy iptables; do not disable networking to bypass the check. |
| Docker CPU weight differs from an old expected number | Runtime versions may map shares differently. Test effective relative weights, not a hardcoded conversion constant. Hard CPU quotas remain unsupported here. |
| Alpine HTTP test restarts | Alpine's default BusyBox lacked httpd. The verified HTTP/volume test uses the official BusyBox image. |
| A shell-fed Compose test skips following commands | Compose can consume its stdin. Use `-T` and redirect stdin from `/dev/null` in scripted one-shot tests. |
| `sudo` reports effective UID is not 0 | Verify actual native ext4 root, mount flags and root-owned 4755 sudo. A proot environment or nosuid mount cannot supply the same semantics. |
| Wi-Fi only returns after lighting Android's screen | Native Debian uses its own Wi-Fi/power policy, not Android Doze. The tested headless configuration disables Wi-Fi power saving and suspend; long-term soak remains pending. |

## Why some container features remain disabled

Naively enabling SYSVIPC adds fields to `task_struct`, changing what stock vendor
drivers expect. The credited Droidspaces patch uses reserved slots 6–8 instead;
we checked offsets, sizes, imports and real Debian boots. This does not establish
that every future firmware or panel uses those slots safely.

CFS_BANDWIDTH and CGROUP_PIDS change other shared kernel structures, so they were
left off. Rootless networking/storage solve userspace setup needs; they do not
magically add missing kernel isolation or resource-control features.
