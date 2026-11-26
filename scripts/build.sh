#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
source "$ROOT/config/sources.env"
VARIANT=${1:?usage: build.sh stock|linux|containers}
[[ "$VARIANT" == stock || "$VARIANT" == linux || "$VARIANT" == containers ]] || exit 1
SRC="$ROOT/work/common"
OUT="$ROOT/work/out/$VARIANT"
DEST="$ROOT/dist/$VARIANT"
mkdir -p "$OUT" "$DEST"
export PATH="$ROOT/work/clang/bin:$PATH"
export KBUILD_BUILD_USER=build-user KBUILD_BUILD_HOST=build-host KBUILD_BUILD_VERSION=1
export KBUILD_BUILD_TIMESTAMP="$KERNEL_BUILD_TIMESTAMP"
export SOURCE_DATE_EPOCH=1770997568
# Prevent setlocalversion from discovering the wrapper repository above this
# source archive. Keep CONFIG_LOCALVERSION_AUTO unchanged from stock.
: > "$SRC/.scmversion"
# Pass the full known stock suffix explicitly.
export LOCALVERSION="$KERNEL_LOCALVERSION"
MK=(make -C "$SRC" O="$OUT" ARCH=arm64 LLVM=1 LLVM_IAS=1 CC=clang
    "LD=ld.lld --threads=${LINK_THREADS:-1}"
    HOSTCC=clang HOSTCXX=clang++ KCFLAGS=-D__ANDROID_COMMON_KERNEL__
    USERCFLAGS=--gcc-toolchain=/usr USERLDFLAGS=-fuse-ld=lld
    -j"${BUILD_JOBS:-$(nproc)}")
# Kconfig tests dynamic and static ARM64 userspace linking before enabling the
# UAPI header tests. These probes need the cross libc/GCC runtime, not just LLVM.
"$SRC/scripts/cc-can-link.sh" clang --target=aarch64-linux-gnu --gcc-toolchain=/usr -fuse-ld=lld || {
  echo 'ARM64 userspace linking failed: check the cross GCC/libc packages'; exit 1;
}
"$SRC/scripts/cc-can-link.sh" clang --target=aarch64-linux-gnu --gcc-toolchain=/usr -fuse-ld=lld -static || {
  echo 'Static ARM64 userspace linking failed: check libc6-dev-arm64-cross'; exit 1;
}
cp "$ROOT/work/abi_symbollist.raw" "$OUT/abi_symbollist.raw"
# gen_autoksyms.sh resolves relative whitelist paths against the source tree.
cp "$ROOT/work/abi_symbollist.raw" "$SRC/abi_symbollist.raw"
cp "$ROOT/config/stock.config" "$OUT/.config"
if [[ "$VARIANT" == linux || "$VARIANT" == containers ]]; then
  "$SRC/scripts/kconfig/merge_config.sh" -m -O "$OUT" "$OUT/.config" "$ROOT/config/linux.fragment"
fi
if [[ "$VARIANT" == containers ]]; then
  # Source cache is saved before mutation; every job has its own source tree.
  patch --batch --fuzz=0 -d "$SRC" -p1 < "$ROOT/patches/sysvipc-kabi.patch"
  "$SRC/scripts/kconfig/merge_config.sh" -m -O "$OUT" "$OUT/.config" "$ROOT/config/containers.fragment"
fi
"${MK[@]}" olddefconfig
python3 "$ROOT/scripts/prepare.py" check "$VARIANT" "$OUT/.config" "$DEST/config-drift.txt"
release=$("${MK[@]}" -s --no-print-directory kernelrelease)
[[ "$release" == "5.15.189$KERNEL_LOCALVERSION" && ${#release} -le 64 ]] || {
  printf 'Unexpected kernel release: %s\n' "$release"; exit 1;
}
printf 'Verified kernel release: %s\n' "$release"
vmstat -t 30 > "$DEST/vmstat.log" &
resource_pid=$!
stop_monitor() {
  if [[ -n ${resource_pid:-} ]]; then
    kill "$resource_pid" 2>/dev/null || true
    wait "$resource_pid" 2>/dev/null || true
    resource_pid=''
  fi
}
trap stop_monitor EXIT
/usr/bin/time -v -o "$DEST/resource-usage.txt" "${MK[@]}" Image.gz modules 2>&1 | tee "$DEST/build.log"
stop_monitor
cp "$OUT/arch/arm64/boot/Image" "$OUT/arch/arm64/boot/Image.gz" "$OUT/vmlinux" "$OUT/Module.symvers" "$DEST/"
cp "$OUT/.config" "$DEST/kernel.config"
cp "$ROOT/config/sources.env" "$DEST/sources.env"
cp "$OUT/abi_symbollist.raw" "$DEST/"
"$ROOT/work/clang/bin/clang" --version > "$DEST/compiler.txt"
pahole --version > "$DEST/pahole.txt"
cat "$OUT/include/config/kernel.release" > "$DEST/kernel.release"
# Explicit outputs only; never upload work/ (which includes generated signing keys).
find "$DEST" -maxdepth 1 -type f ! -name SHA256SUMS -printf '%f\n' | sort |
  while IFS= read -r name; do (cd "$DEST" && sha256sum "$name"); done > "$DEST/SHA256SUMS"
echo 'Build complete. This is a kernel artifact, NOT a flashable boot image.'
