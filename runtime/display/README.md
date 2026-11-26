# Tested headless panel helper

`moto_panel_off.c` calls the existing vendor driver's disable/unprepare callbacks
for **Tianma ILI77600A** (`tm_ili77600a_vid_1080_2388_fhd_120hz`). It does not
support other panel variants. The driver must already be bound. With the default
`poweroff=0` it only finds/checks the panel; `poweroff=1` requests shutdown.

Build against the exact matching configured kernel tree and Module.symvers:

```sh
make -C /path/to/matching/kernel/source O=/path/to/matching/output \
  ARCH=arm64 LLVM=1 LLVM_IAS=1 CC=clang HOSTCC=clang HOSTCXX=clang++ \
  KCFLAGS=-D__ANDROID_COMMON_KERNEL__ M="$PWD/runtime/display" modules
```

Use the pinned compiler and kernel release from config/sources.env. First prepare
the same config and generated headers, then install the exact candidate
Module.symvers into the output tree. Do not replace it with an empty symvers or
force-load the result. Verify ELF architecture, vermagic, imported CRCs and the
`drm_panel` layout against the candidate. Our existing module's eight imports
passed against the container kernel. The shared `uname -r` alone is insufficient.

On a supported, explicitly tested phone, install the built module under the
matching `/lib/modules/RELEASE/extra/`, run depmod, and install `moto-panel-off`
under `/usr/local/sbin/` and its service under `/etc/systemd/system/`. The wrapper
is intentionally restricted to the tested release and leaves an `attempting`
marker on failure. Do not automatically clear that marker or broaden the panel
match. First run an inspection-only module load, then perform a controlled
shutdown trial and reboot check before enabling the service.

The service orders after the existing `moto-headless` backlight-zero service.
The wrapper/service source here matches the deployed version. It was verified
after the container-kernel reboot; another panel/release remains untested.
Unloading the module does not restore the panel. Reboot restores its startup.
To stop future shutdown attempts, disable the service or create
`/etc/moto-panel-off.disabled`, then reboot.
