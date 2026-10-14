#!/usr/bin/env bash
set -eEuo pipefail
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/release.sh"
TARGET_DIR=${OMARCHY_SOURCE_DIR:-"$HOME/.cache/omarchy-on-cachyos/source-$OMARCHY_VERSION"}
REF=${1:-"v$OMARCHY_VERSION"}
[[ $REF == "v$OMARCHY_VERSION" ]] || {
  echo "Unsupported version: $REF. This adapter targets v$OMARCHY_VERSION; main/dev must be reviewed first." >&2
  exit 1
}
mkdir -p -- "$(dirname -- "$TARGET_DIR")"
if [[ -e $TARGET_DIR ]]; then
  [[ -d $TARGET_DIR/.git ]] || { echo "Not an Omarchy checkout: $TARGET_DIR" >&2; exit 1; }
  [[ $(git -C "$TARGET_DIR" rev-parse HEAD) == "$OMARCHY_COMMIT" ]] || {
    echo "Existing source is a different release. Move it aside: $TARGET_DIR" >&2; exit 1;
  }
  [[ -z $(git -C "$TARGET_DIR" status --porcelain) ]] || {
    echo "Existing source has local changes. Move it aside: $TARGET_DIR" >&2; exit 1;
  }
else
  git -c advice.detachedHead=false clone --depth 1 --branch "$REF" "$OMARCHY_REPO" "$TARGET_DIR"
fi
[[ $(git -C "$TARGET_DIR" rev-parse HEAD) == "$OMARCHY_COMMIT" ]] || {
  echo "Upstream tag no longer matches the reviewed commit. Stopping." >&2; exit 1;
}
for file in version install/omarchy-base.packages bin/omarchy-provision-user config/hypr/hyprland.lua; do
  [[ -f $TARGET_DIR/$file ]] || { echo "Missing upstream file: $file" >&2; exit 1; }
done
echo "Verified Omarchy v$OMARCHY_VERSION at $TARGET_DIR"
