#!/usr/bin/env bash
# Create a local PKCS#12 signing keystore and upload its values to GitHub Actions.
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: $0 <output-keystore.p12> [OWNER/REPOSITORY]" >&2
  exit 2
fi

keystore="$1"
repo="${2:-}"
if [[ "$keystore" != /* ]]; then
  keystore="$PWD/$keystore"
fi
alias='android-release'
signing_password=''
signing_password_confirm=''
temporary_directory=''

cleanup() {
  [[ -z "$temporary_directory" ]] || rm -rf "$temporary_directory"
  unset signing_password signing_password_confirm ANDROID_SIGNING_PASSWORD
}
trap cleanup EXIT

command -v gh >/dev/null 2>&1 || { echo 'GitHub CLI (gh) is required.' >&2; exit 1; }
command -v keytool >/dev/null 2>&1 || { echo 'keytool is required; install a JDK first.' >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo 'python3 is required.' >&2; exit 1; }
[[ ! -e "$keystore" ]] || { echo "Refusing to overwrite existing keystore: $keystore" >&2; exit 1; }
gh auth status >/dev/null

if [[ -z "$repo" ]]; then
  repo="$(gh repo view --json nameWithOwner --jq .nameWithOwner)"
fi
if [[ ! "$repo" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]]; then
  echo 'Repository must be OWNER/REPOSITORY.' >&2
  exit 2
fi

read -r -p "Key alias [$alias]: " alias_input
alias="${alias_input:-$alias}"
read -r -s -p 'New keystore password (at least 6 characters): ' signing_password
echo
read -r -s -p 'Confirm keystore password: ' signing_password_confirm
echo
if [[ "$signing_password" != "$signing_password_confirm" || ${#signing_password} -lt 6 ]]; then
  echo 'Passwords must match and be at least 6 characters.' >&2
  exit 2
fi

# PKCS#12 Android signing keystores use one password for the store and key.
umask 077
keystore_directory="$(dirname "$keystore")"
mkdir -p "$keystore_directory"
temporary_directory="$(mktemp -d "$keystore_directory/.android-release.XXXXXX")"
temporary_keystore="$temporary_directory/release.p12"
ANDROID_SIGNING_PASSWORD="$signing_password" keytool -genkeypair -v \
  -keystore "$temporary_keystore" \
  -storetype PKCS12 \
  -alias "$alias" \
  -keyalg RSA \
  -keysize 4096 \
  -validity 10000 \
  -dname 'CN=DeepSeek Harness Android Release, OU=Release, O=DeepSeek Harness, C=US' \
  -storepass:env ANDROID_SIGNING_PASSWORD \
  -keypass:env ANDROID_SIGNING_PASSWORD
chmod 600 "$temporary_keystore"
ANDROID_SIGNING_PASSWORD="$signing_password" keytool -list \
  -keystore "$temporary_keystore" -storetype PKCS12 \
  -storepass:env ANDROID_SIGNING_PASSWORD -alias "$alias" >/dev/null
ln "$temporary_keystore" "$keystore"
printf 'Created and validated local keystore: %s\n' "$keystore"

# Create or retain the android-release environment, then check for existing values.
gh api --method PUT "repos/$repo/environments/android-release" --silent
existing_names="$(gh api "repos/$repo/environments/android-release/secrets" --jq '.secrets[].name')"
secrets=(ANDROID_KEYSTORE_BASE64 ANDROID_KEY_ALIAS ANDROID_STORE_PASSWORD ANDROID_KEY_PASSWORD)
found_existing=()
for name in "${secrets[@]}"; do
  if grep -Fqx "$name" <<<"$existing_names"; then
    found_existing+=("$name")
  fi
done
if ((${#found_existing[@]})); then
  printf 'These android-release secrets already exist and would be replaced:\n' >&2
  printf '  %s\n' "${found_existing[@]}" >&2
  read -r -p 'Replace them with this new signing key? [y/N] ' answer
  [[ "$answer" =~ ^[Yy]$ ]] || {
    echo "Cancelled; the new local keystore remains at $keystore and no secrets were changed." >&2
    exit 1
  }
fi

python3 -c 'import base64,pathlib,sys; sys.stdout.buffer.write(base64.b64encode(pathlib.Path(sys.argv[1]).read_bytes()))' "$keystore" \
  | gh secret set ANDROID_KEYSTORE_BASE64 --app actions --repo "$repo" --env android-release
printf '%s' "$alias" \
  | gh secret set ANDROID_KEY_ALIAS --app actions --repo "$repo" --env android-release
printf '%s' "$signing_password" \
  | gh secret set ANDROID_STORE_PASSWORD --app actions --repo "$repo" --env android-release
printf '%s' "$signing_password" \
  | gh secret set ANDROID_KEY_PASSWORD --app actions --repo "$repo" --env android-release

printf '\nCreated local keystore: %s\n' "$keystore"
printf 'Uploaded Android signing secrets to %s / android-release.\n' "$repo"
printf 'Keep a secure offline backup of the keystore. Configure required reviewers and deployment restrictions in GitHub Settings → Environments → android-release.\n'
