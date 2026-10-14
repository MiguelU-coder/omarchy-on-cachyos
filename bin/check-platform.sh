# Read distro identity without executing os-release as shell code. Arguments
# allow fixture tests; the installer always supplies the actual system paths.
omarchy_check_platform() {
  local release=$1 marker=$2 arch_marker=$3 kernel=$4 allow_arch=$5 os_id=unknown
  if [[ -r $release ]]; then
    os_id=$(awk -F= '$1 == "ID" {gsub(/["\047[:space:]]/, "", $2); print $2; exit}' "$release")
    os_id=${os_id:-unknown}
  fi
  if [[ $os_id == cachyos || -f $marker ]]; then
    echo "Detected CachyOS (ID=$os_id, kernel=$kernel)."
    return 0
  fi
  if [[ $allow_arch == 1 && $os_id == arch && -f $arch_marker && $kernel == *cachyos* ]]; then
    echo "Detected Arch with a CachyOS kernel. Using the experimental CachyOS desktop adapter."
    return 0
  fi
  echo "CachyOS not detected (ID=$os_id, kernel=$kernel)." >&2
  echo "If this is Arch with a CachyOS kernel, use --allow-arch-with-cachyos-kernel." >&2
  echo "That option requires ID=arch, /etc/arch-release and a running CachyOS kernel." >&2
  return 1
}
