# Source and recipe provenance

This is a kernel build experiment for Motorola XT2617V, firmware
W1WEOS36.48-22-3-3-4-3. The device-specific Debian approach and minimal configuration
changes follow dingyifei/gpower26-cluster-pub at commit
308a30f948ac7664c5df1ad3ad98dcb99039b24b:
https://github.com/dingyifei/gpower26-cluster-pub

The workflow and helpers here were written for this separate project. No vendor
binaries, calibration data, firmware dumps, or code from vegas-freedom are included.

Kernel source is fetched from Google's Android common kernel repository at the
revision in config/sources.env. The kernel's own GPL-2.0 and other source licenses
apply to that code and compiled outputs. Compiler prebuilts retain their upstream
licenses and notices. This project does not change those licenses.

The recorded stock configuration was extracted from this firmware. Its original
build-machine path for the symbol whitelist is normalized to abi_symbollist.raw;
no personal path or phone identifier is needed to compile the kernel.

SYSVIPC kABI padding patch: nullptr-t-oss, via Droidspaces-OSS commit
77e63323c937ae69e260aa8432d6f664997312c1, Documentation/resources/kernel-patches/GKI/
below-kernel-6.12/001.GKI-below-6.12-fix_sysvipc_kabi_6_7_8.patch.
https://github.com/ravindu644/Droidspaces-OSS
The patch retains its original authorship; upstream distributes it under GPL-3.0.
It uses Android's ABI reservation macros for slots 6-8 of task_struct.
