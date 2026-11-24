#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
source "$ROOT/config/sources.env"
mkdir -p "$ROOT/work"
fetch_tree() {
  local repo=$1 revision=$2 subtree=$3 dest=$4
  # Only reuse a completely extracted tree from this exact revision/path.
  local marker="$revision/$subtree"
  if [[ -f "$dest/.download-complete" ]] && [[ $(cat "$dest/.download-complete") == "$marker" ]]; then return; fi
  [[ "$dest" == "$ROOT/work/"* ]] || exit 1
  rm -rf -- "$dest"
  mkdir -p "$dest"
  local url="https://android.googlesource.com/$repo/+archive/$revision"
  [[ -z "$subtree" ]] || url+="/$subtree"
  curl --fail --location --retry 4 --connect-timeout 30 "$url.tar.gz" -o "$dest.download"
  tar -xzf "$dest.download" -C "$dest"
  rm "$dest.download"
  printf '%s\n' "$marker" > "$dest/.download-complete"
}
fetch_tree kernel/common "$KERNEL_COMMIT" '' "$ROOT/work/common"
fetch_tree platform/prebuilts/clang/host/linux-x86 "$CLANG_COMMIT" "clang-$CLANG_VERSION" "$ROOT/work/clang"
"$ROOT/work/clang/bin/clang" --version
python3 "$ROOT/scripts/prepare.py" symbols
