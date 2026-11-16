#!/usr/bin/env bash
# Create a local PKCS#12 keystore for Android release signing.
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <output-keystore.p12> <key-alias>" >&2
  exit 2
fi
keystore="$1"
alias="$2"

if [[ -e "$keystore" ]]; then
  echo "Refusing to overwrite existing keystore: $keystore" >&2
  exit 1
fi
if ! command -v keytool >/dev/null 2>&1; then
  echo 'keytool is required; install a JDK first.' >&2
  exit 1
fi

umask 077
mkdir -p "$(dirname "$keystore")"
keytool -genkeypair -v \
  -keystore "$keystore" \
  -storetype PKCS12 \
  -alias "$alias" \
  -keyalg RSA \
  -keysize 4096 \
  -validity 10000
chmod 600 "$keystore"
printf 'Created local signing key: %s\n' "$keystore"
printf 'Keep a secure offline backup. Do not commit or upload the keystore file itself.\n'
