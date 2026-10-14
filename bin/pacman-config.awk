# Preserve CachyOS/Arch repositories, replace an old Omarchy stanza, and give
# the matching Omarchy desktop packages priority over incompatible namesakes.
function omarchy() {
  print "[omarchy]"
  print "SigLevel = Required DatabaseOptional"
  print "Server = https://pkgs.omarchy.org/stable/$arch"
  print ""
  added=1
}
/^[[:space:]]*\[[^]]+\]/ {
  skip=($0 ~ /^[[:space:]]*\[omarchy\][[:space:]]*(#.*)?$/)
  if ($0 !~ /^[[:space:]]*\[options\]/ && !added) omarchy()
}
!skip { print }
END { if (!added) omarchy() }
