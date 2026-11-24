#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
source "$ROOT/config/sources.env"
VARIANT=${1:?usage: build.sh stock|linux}
[[ "$VARIANT" == stock || "$VARIANT" == linux ]] || exit 1
SRC="$ROOT/work/common"
OUT="$ROOT/work/out/$VARIANT"
DEST="$ROOT/dist/$VARIANT"
mkdir -p "$OUT" "$DEST"
export PATH="$ROOT/work/clang/bin:$PATH"
export KBUILD_BUILD_USER=build-user KBUILD_BUILD_HOST=build-host KBUILD_BUILD_VERSION=1
export KBUILD_BUILD_TIMESTAMP="$KERNEL_BUILD_TIMESTAMP"
export SOURCE_DATE_EPOCH=1770997568
# A source archive has no git metadata: pass the full known stock suffix explicitly.
export LOCALVERSION="$KERNEL_LOCALVERSION"
MK=(make -C "$SRC" O="$OUT" ARCH=arm64 LLVM=1 LLVM_IAS=1 CC=clang
    HOSTCC=clang HOSTCXX=clang++ KCFLAGS=-D__ANDROID_COMMON_KERNEL__
    -j"${BUILD_JOBS:-$(nproc)}")
cp "$ROOT/work/abi_symbollist.raw" "$OUT/abi_symbollist.raw"
# gen_autoksyms.sh resolves relative whitelist paths against the source tree.
cp "$ROOT/work/abi_symbollist.raw" "$SRC/abi_symbollist.raw"
cp "$ROOT/config/stock.config" "$OUT/.config"
if [[ "$VARIANT" == linux ]]; then
  "$SRC/scripts/kconfig/merge_config.sh" -m -O "$OUT" "$OUT/.config" "$ROOT/config/linux.fragment"
fi
"${MK[@]}" olddefconfig
python3 "$ROOT/scripts/prepare.py" check "$VARIANT" "$OUT/.config" "$DEST/config-drift.txt"
"${MK[@]}" Image.gz modules 2>&1 | tee "$DEST/build.log"
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
