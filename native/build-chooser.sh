#!/bin/bash
# Offline only. Run on ARM64 or supply an ARM64 cross compiler via CC.
set -euo pipefail
upstream=$(realpath "${1:?upstream checkout}")
base=$(realpath "${2:?base lz4-legacy ramdisk}")
busybox=$(realpath "${3:?static ARM64 busybox}")
out=$(realpath -m "${4:?new output directory}")
variant=${5:?dry|android-default|debian-default}
case "$variant" in dry|android-default|debian-default) ;; *) exit 2;; esac
[[ ! -e $out && -f $base && -x $busybox ]]
grep -q DEFAULT_LINUX "$upstream/linux/initramfs/chooser.c"
readelf -h "$busybox" | grep -q AArch64
! readelf -l "$busybox" | grep -q INTERP
mkdir -p "$out/overlay/linux" "$out/base"
work=$(realpath "$out")
python3 - "$base" <<'PY'
import sys
assert open(sys.argv[1],'rb').read(4)==bytes.fromhex('02214c18'),'Need lz4 legacy ramdisk'
PY
lz4 -dc "$base" | cpio -it --quiet > "$work/base.list"
grep -qx init "$work/base.list"
(cd "$work/base"; lz4 -dc "$base" | cpio --no-absolute-filenames -id --quiet init)
[[ -f $work/base/init && ! -L $work/base/init ]]
flags=(-static -Os -Wall -Wno-format-truncation)
[[ $variant != dry ]] || flags+=(-DDRY)
[[ $variant != debian-default ]] || flags+=(-DDEFAULT_LINUX)
"${CC:-gcc}" "${flags[@]}" -o "$work/overlay/init" "$upstream/linux/initramfs/chooser.c"
readelf -h "$work/overlay/init" | grep -q AArch64
! readelf -l "$work/overlay/init" | grep -q INTERP
cp "$work/base/init" "$work/overlay/init.next"
chmod 0750 "$work/overlay/init" "$work/overlay/init.next"
cp "$busybox" "$work/overlay/linux/busybox"
for name in lpmap rebootbl; do
 "${CC:-gcc}" -static -Os -Wall -o "$work/overlay/linux/$name" "$upstream/linux/initramfs/$name.c"
done
"${CC:-gcc}" -static -Os -Wall -Wno-format-truncation -o "$work/overlay/linux/vegasdisk" "$upstream/linux/tools/vegasdisk.c"
install -m0755 "$upstream/linux/initramfs/init.linux" "$work/overlay/linux/init.linux"
[[ $variant != debian-default ]] || touch "$work/overlay/linux/debian-default"
(cd "$work/overlay"; find . -mindepth 1 | sed 's#^./##' | LC_ALL=C sort | cpio -o -H newc --owner=0:0 --quiet | lz4 -l -12) > "$work/overlay.lz4"
cat "$base" "$work/overlay.lz4" > "$work/ramdisk.lz4"
cmp <(lz4 -dc "$work/ramdisk.lz4") <(lz4 -dc "$base"; lz4 -dc "$work/overlay.lz4")
cmp "$work/base/init" "$work/overlay/init.next"
sha256sum "$work/ramdisk.lz4"
echo 'Offline chooser built. No phone or partition accessed.'
